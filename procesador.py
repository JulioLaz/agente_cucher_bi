"""
procesador.py — Orquesta el flujo completo del agente:
  1. Enriquecer pregunta (Python puro)
  2. Intentar template pre-verificado
  3. Si falla → LLM genera SQL
  4. DuckDB ejecuta → retry si hay error
  5. LLM analiza resultado
"""
import json
import re
from datetime import date
from typing import Optional
import pandas as pd

from enriquecedor import enriquecer, construir_hint, Contexto
from templates import resolver_con_template
from ejecutor import ejecutar_sql, limpiar_sql
from llm import llamar_nvidia
from config import (T_TICKETS, T_PROV, T_ALERT, T_PRECIOS,
                    MAX_TOKENS_SQL, MAX_TOKENS_ANALISIS)
from catalogo import CATEGORIAS


# ─── SCHEMA SQL PARA EL LLM ──────────────────────────────────
SCHEMA_SQL = f"""
=== TABLAS DISPONIBLES EN MOTHERDUCK ===

my_db.tickets_all (5.5M filas — ventas 2024-2026)
  fecha_comprobante VARCHAR  → CAST(fecha_comprobante AS DATE) para filtrar fechas
  idarticulo BIGINT, descripcion VARCHAR  ← MARCAS están aquí, buscar con LIKE
  costo_total DOUBLE, precio_total DOUBLE
  sucursal VARCHAR  ← valores: hiper, corrientes, sabin, formosa, express, tirol, central
  costo_unitario DOUBLE, precio_unitario DOUBLE
  margen_porcentual DOUBLE  ← decimal (0.30 = 30%)
  idartalfa BIGINT  ← clave de JOIN con proveedores y ultimos_precios
  familia VARCHAR   ← categoría principal (ej: "Bebidas", "Alimentos")
  subfamilia VARCHAR ← subcategoría (ej: "Cervezas", "Yerbas") ← FILTRAR AQUÍ por categoría
  cantidad_total DOUBLE

my_db.proveedores (39K filas — stock actual + proveedor + descripcion)
  idartalfa BIGINT, idarticulo FLOAT
  stk_hiper/corrientes/sabin/formosa/express/tirol/central DOUBLE ← stock por sucursal
  stk_total FLOAT
  descripcion VARCHAR, proveedor VARCHAR, subfamilia VARCHAR, familia VARCHAR
  uxb FLOAT  ← unidades por bulto

my_db.ultimos_precios (13.6K filas — ÚLTIMO precio OC, SIN filtro de fecha)
  idartalfa BIGINT  ← JOIN con tickets/proveedores
  ultimo_precio_compra DOUBLE
  fecha_ultima_oc TIMESTAMP  ← fecha de la OC, NO filtrar por esto
  proveedor_oc VARCHAR

my_db.result_final_alert_all (18K filas — artículos activos 90 días)
  idarticulo BIGINT, descripcion VARCHAR, familia VARCHAR, subfamilia VARCHAR
  cnt_hiper/corrientes/sabin/formosa/express BIGINT ← ventas 90d por sucursal
  stk_hiper/corrientes/sabin/formosa/express/TIROL/central/STK_TOTAL BIGINT
  nivel_riesgo VARCHAR, alerta_reabastecer VARCHAR
  dias_cobertura BIGINT  ← días de stock restante
  ranking_mes BIGINT     ← 1=mejor mes del año, 12=peor
  mes_actual DOUBLE      ← % contribución del mes actual
  meses_act_estac BIGINT ← meses activos (< 4 = muy estacional)
  clase_abc VARCHAR, prioridad BIGINT
  PRESUPUESTO BIGINT, total_abastecer BIGINT
  precio_actual DOUBLE, costo_unit DOUBLE
  idarticuloalfa BIGINT  ← equivale a idartalfa para JOINs

=== REGLAS CRÍTICAS ===

REGLA 1 — CATEGORÍAS: filtrar por SUBFAMILIA (no por familia)
  cervezas → LOWER(subfamilia) LIKE '%Cervezas%'
  yerbas   → LOWER(subfamilia) LIKE '%Yerbas%'
  NUNCA: WHERE familia LIKE '%cerveza%' ← incorrecto

REGLA 2 — MARCAS: filtrar por DESCRIPCION con LIKE
  Quilmes, Schneider → LOWER(descripcion) LIKE '%quilmes%'
  Múltiples marcas   → (LOWER(descripcion) LIKE '%clight%' OR LOWER(descripcion) LIKE '%tang%')

REGLA 3 — TAMAÑOS/VOLUMEN en DESCRIPCION
  más de 900cc → buscar: '940', '960', '1000', '1l', 'litro' en descripcion
  menos de 500ml → buscar: '330', '354', '355', '473' en descripcion

REGLA 4 — PRECIOS OC: NO filtrar ultimos_precios por fecha
  JOIN correcto: tickets_all.idartalfa = ultimos_precios.idartalfa
  JOIN correcto: result_final_alert_all.idarticuloalfa = ultimos_precios.idartalfa

REGLA 5 — MARGEN
  margen% = (precio_total - costo_total) / precio_total * 100
  margen real = (precio_actual - ultimo_precio_compra) / ultimo_precio_compra * 100

REGLA 6 — SUCURSALES VENTA PÚBLICA
  IN ('hiper','corrientes','sabin','formosa')

=== EJEMPLOS DE QUERIES CORRECTAS ===

-- Cervezas de más de 900cc más vendidas:
SELECT descripcion, sucursal,
  ROUND(SUM(precio_total),2) AS ventas,
  ROUND(SUM(cantidad_total),0) AS unidades
FROM my_db.tickets_all
WHERE LOWER(subfamilia) LIKE '%Cervezas%'
  AND (LOWER(descripcion) LIKE '%940%' OR LOWER(descripcion) LIKE '%960%'
    OR LOWER(descripcion) LIKE '%1000%' OR LOWER(descripcion) LIKE '%1l%'
    OR LOWER(descripcion) LIKE '%litro%')
  AND LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa')
GROUP BY descripcion, sucursal ORDER BY ventas DESC LIMIT 20;

-- Precios de compra de café 1kg:
SELECT TRIM(p.descripcion), TRIM(p.proveedor),
  ROUND(op.ultimo_precio_compra,2) AS precio_compra, op.proveedor_oc,
  CAST(op.fecha_ultima_oc AS DATE)
FROM my_db.proveedores p
JOIN my_db.ultimos_precios op ON p.idartalfa = op.idartalfa
WHERE LOWER(p.descripcion) LIKE '%caf%'
  AND (LOWER(p.descripcion) LIKE '%1 kg%' OR LOWER(p.descripcion) LIKE '%x1kg%')
ORDER BY precio_compra DESC;

-- ÚLTIMO PRECIO DE VENTA por artículo (SIEMPRE usar ROW_NUMBER por fecha DESC):
-- precio_unitario es el precio de venta unitario en tickets_all
-- NUNCA usar AVG(precio_unitario) — siempre el último registrado por fecha
WITH ultimo_precio AS (
    SELECT descripcion, precio_unitario,
           CAST(fecha_comprobante AS DATE) AS fecha,
           ROW_NUMBER() OVER (
               PARTITION BY descripcion
               ORDER BY CAST(fecha_comprobante AS DATE) DESC
           ) AS rn
    FROM my_db.tickets_all
    WHERE subfamilia = 'Cervezas' AND precio_unitario > 0
)
SELECT descripcion, fecha AS ultima_fecha,
       ROUND(precio_unitario,2) AS ultimo_precio_venta
FROM ultimo_precio WHERE rn = 1
ORDER BY descripcion;

-- COMPARAR precio de venta vs precio de compra OC:
WITH pv AS (
    SELECT t.descripcion, t.idartalfa,
           ROUND(t.precio_unitario, 2) AS precio_venta,
           CAST(t.fecha_comprobante AS DATE) AS fecha_venta,
           ROW_NUMBER() OVER (
               PARTITION BY t.descripcion
               ORDER BY CAST(t.fecha_comprobante AS DATE) DESC
           ) AS rn
    FROM my_db.tickets_all t
    WHERE t.subfamilia = 'Cervezas' AND t.precio_unitario > 0
)
SELECT pv.descripcion,
       pv.precio_venta                                              AS ultimo_precio_venta,
       pv.fecha_venta                                              AS fecha_ultimo_ticket,
       ROUND(op.ultimo_precio_compra, 2)                          AS precio_compra_oc,
       TRIM(op.proveedor_oc)                                      AS proveedor,
       CAST(op.fecha_ultima_oc AS DATE)                           AS fecha_ultima_oc,
       ROUND((pv.precio_venta - op.ultimo_precio_compra)
             / NULLIF(op.ultimo_precio_compra,0) * 100, 2)       AS margen_real_pct
FROM pv
JOIN my_db.ultimos_precios op ON pv.idartalfa = op.idartalfa
WHERE pv.rn = 1
ORDER BY margen_real_pct ASC;
"""

SYSTEM_SQL = f"""Sos un experto en DuckDB y SQL para retail. Generás SQL para MotherDuck.
Hoy: {{hoy}}. Mes: {{mes}}.

{SCHEMA_SQL}

INSTRUCCIÓN: Devolvé SOLO este JSON sin markdown:
{{"sql": "SELECT ..."}}

El SQL debe ser correcto para DuckDB, con LIMIT y sin filtros de fecha en ultimos_precios."""

SYSTEM_ANALISIS = """Analista de datos experto en retail argentino.
Respondés en español, conciso, orientado a decisiones.
Sabin abrió 6-jun-2026. Stock <7d = crítico, 7-14d = bajo.

REGLAS DE FORMATO:
- Saltos de línea entre cada ítem del ranking
- Formato: "1. **Artículo** — métrica1: valor | métrica2: valor"
- Máximo 8 ítems en rankings
- Terminá con "**Acciones:**" seguido de 2 puntos concretos
- NUNCA inventés datos — solo lo que está en los datos recibidos
- Sin código SQL en la respuesta"""


def procesar(pregunta: str, historial: list) -> tuple[str, Optional[pd.DataFrame], str]:
    """
    Flujo completo del agente.
    Retorna (respuesta_texto, dataframe_resultado, modo)
    modos: "template", "sql_libre", "sql_retry", "error_sql", "sql_vacio"
    """
    hoy = date.today()
    mes = hoy.strftime("%B")

    # ── PASO 1: Enriquecer pregunta con Python puro ───────────
    ctx  = enriquecer(pregunta)
    hint = construir_hint(ctx)
    pregunta_enr = pregunta + hint
    print(f"   [proc] ctx: cat={ctx.categoria_key} marcas={ctx.marcas} "
          f"precio={ctx.pide_precio} ranking={ctx.pide_ranking} "
          f"rango_cc={ctx.rango_min_cc} medida={ctx.medida_str!r}")

    # ── PASO 2: Intentar template pre-verificado ──────────────
    df = resolver_con_template(ctx)
    if df is not None and not df.empty:
        print(f"   [proc] Template resolvió → {len(df)} filas")
        analisis = _analizar(pregunta, df, hoy, mes, historial)
        return analisis, df, "template"

    # ── PASO 3: LLM genera SQL ────────────────────────────────
    system = SYSTEM_SQL.format(hoy=hoy, mes=mes)
    msgs   = [{"role": "system", "content": system}]
    for h in historial[-6:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": pregunta_enr})

    print(f"   [proc] Llamando LLM para SQL...")
    raw = llamar_nvidia(msgs, max_tokens=MAX_TOKENS_SQL)
    print(f"   [proc] RAW LLM respuesta: {repr(raw[:300])}")

    sql, df, error, modo = _extraer_y_ejecutar(raw)
    print(f"   [proc] SQL: {sql[:120] if sql else 'vacío'}")
    print(f"   [proc] Resultado: {len(df)} filas | Error: {error[:80] if error else 'ninguno'}")

    # ── PASO 4: Retry si hay error ────────────────────────────
    if error and not df.empty is False:
        print(f"   [proc] Retry con error: {error[:80]}")
        retry_msgs = msgs + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": (
                f"Error al ejecutar: {error}\n"
                f"Corregí el SQL. Recordá:\n"
                f"- Usar LOWER(subfamilia) LIKE para categorías\n"
                f"- Buscar tamaños en descripcion, no como número puro\n"
                f"- NO filtrar ultimos_precios por fecha\n"
                f"Devolvé solo el JSON corregido."
            )}
        ]
        raw2 = llamar_nvidia(retry_msgs, max_tokens=MAX_TOKENS_SQL)
        sql, df, error, modo = _extraer_y_ejecutar(raw2)
        if not error:
            modo = "sql_retry"
        print(f"   [proc] Retry resultado: {len(df)} filas | Error: {error[:60] if error else 'ok'}")

    # ── PASO 5: Analizar resultado ────────────────────────────
    if error:
        return (
            f"❌ No pude ejecutar la consulta: {error}\n\n"
            f"Intentá reformular la pregunta con más detalle.",
            None, "error_sql"
        )

    if df.empty:
        return _respuesta_vacio(pregunta, ctx), None, "sql_vacio"

    analisis = _analizar(pregunta, df, hoy, mes, historial)
    return analisis, df, modo


def _extraer_y_ejecutar(raw: str) -> tuple[str, pd.DataFrame, str, str]:
    """Extrae SQL del raw del LLM y lo ejecuta."""
    sql = ""

    # Limpiar markdown
    clean = raw.strip()
    for tag in ["```json", "```sql", "```"]:
        clean = clean.replace(tag, "")
    clean = clean.strip()

    # Intentar parsear JSON
    try:
        parsed = json.loads(clean)
        sql = parsed.get("sql", "")
        # El LLM a veces devuelve {"sql": "SELECT..."} con sql como string literal
        if sql in ('"', "'", "sql", "SQL", ""):
            sql = ""
    except Exception:
        pass

    # Si no se pudo parsear JSON, buscar SQL directamente
    if not sql:
        match = re.search(r'(WITH\s+|SELECT\s+).+',
                          clean, re.DOTALL | re.IGNORECASE)
        sql = match.group(0).strip() if match else ""

    # Limpiar el SQL extraído
    sql = sql.strip().strip('"').strip("'").strip()

    if not sql or len(sql) < 10:
        return "", pd.DataFrame(), "No se pudo extraer SQL válido de la respuesta", "error_sql"

    sql = limpiar_sql(sql)
    df, error = ejecutar_sql(sql)
    modo = "sql_libre"
    return sql, df, error, modo


def _analizar(pregunta: str, df: pd.DataFrame,
              hoy: date, mes: str, historial: list) -> str:
    """Llama al LLM para analizar el resultado."""
    datos_str = df.head(30).to_string(index=False)
    if len(datos_str) > 4000:
        datos_str = df.head(20).to_string(index=False) + f"\n... ({len(df)} filas totales)"

    msgs = [{"role": "system", "content": SYSTEM_ANALISIS}]
    for h in historial[-4:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": (
        f'Pregunta: "{pregunta}"\n\n'
        f'Datos reales de MotherDuck ({len(df)} filas):\n{datos_str}\n\n'
        f'Analizá con insights accionables. Respetá el formato indicado.'
    )})

    return llamar_nvidia(msgs, max_tokens=MAX_TOKENS_ANALISIS)


def _respuesta_vacio(pregunta: str, ctx: Contexto) -> str:
    """Genera respuesta útil cuando el DataFrame está vacío."""
    sugerencias = []

    if ctx.categoria_key and ctx.medida_str:
        sugerencias.append(
            f"Probá sin filtro de medida: solo '{ctx.categoria_key}' sin '{ctx.medida_str}'"
        )
    if ctx.rango_min_cc:
        sugerencias.append(
            f"El volumen buscado ({ctx.rango_min_cc}cc+) puede no estar disponible. "
            f"Probá sin ese filtro."
        )
    if ctx.marcas:
        sugerencias.append(
            f"Verificá que las marcas {ctx.marcas} estén en el catálogo. "
            f"Probá con variantes del nombre."
        )
    if ctx.fecha_desde:
        sugerencias.append(
            f"El período {ctx.fecha_desde}→{ctx.fecha_hasta} puede no tener datos. "
            f"Probá con un rango más amplio."
        )

    if not sugerencias:
        sugerencias.append("Probá reformular la pregunta con términos más generales.")

    sug_str = "\n".join(f"• {s}" for s in sugerencias)
    return (
        f"No encontré datos para tu consulta.\n\n"
        f"**Sugerencias:**\n{sug_str}"
    )