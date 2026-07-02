"""
kpis.py — Funciones para cargar KPIs y datos del panel fijo.
Todas las queries están cacheadas con ttl=600 (10 min).
"""
import streamlit as st
import pandas as pd
import functools

# Cache simple sin Streamlit para compatibilidad
_cache = {}
from datetime import date, timedelta
from conexion import get_con
from config import T_TICKETS, T_ALERT


@st.cache_data(ttl=600)
def cargar_kpis_alertas() -> dict:
    """KPIs de alertas globales del sistema — siempre visibles."""
    q = """
        SELECT
            COUNT(*) AS total_articulos,
            SUM(CASE WHEN alerta_reabastecer = 'Sí' AND dias_cobertura = 0  THEN 1 ELSE 0 END) AS sin_stock,
            SUM(CASE WHEN alerta_reabastecer = 'Sí' AND dias_cobertura <= 3 AND dias_cobertura > 0 THEN 1 ELSE 0 END) AS criticos,
            SUM(CASE WHEN alerta_reabastecer = 'Sí' AND dias_cobertura <= 7 AND dias_cobertura > 3 THEN 1 ELSE 0 END) AS urgentes,
            SUM(CASE WHEN exceso_STK > 0 THEN 1 ELSE 0 END) AS exceso_stock,
            ROUND(SUM(valor_perdido_TOTAL)/1e6, 1) AS valor_perdido_m,
            ROUND(SUM(PRESUPUESTO)/1e6, 1) AS presupuesto_m
        FROM my_db.result_final_alert_all
    """
    try:
        return get_con().execute(q).df().iloc[0].to_dict()
    except Exception:
        return {}


@st.cache_data(ttl=600)
def cargar_mes_con_datos() -> date:
    """Devuelve la fecha del último mes con datos en tickets_all."""
    q = f"SELECT MAX(CAST(fecha_comprobante AS DATE)) AS ultima FROM {T_TICKETS}"
    try:
        ultima = get_con().execute(q).df().iloc[0]["ultima"]
        return ultima
    except Exception:
        return date.today()


@st.cache_data(ttl=600)
def cargar_kpis_header() -> dict:
    """KPIs del mes más reciente con datos vs mes anterior."""
    q = f"""
        WITH ultimo_mes AS (
            -- Mes más reciente con datos (puede diferir del mes calendario actual)
            SELECT
                EXTRACT(YEAR  FROM MAX(CAST(fecha_comprobante AS DATE))) AS anio,
                EXTRACT(MONTH FROM MAX(CAST(fecha_comprobante AS DATE))) AS mes
            FROM {T_TICKETS}
        ),
        actual AS (
            SELECT
                ROUND(SUM(precio_total)/1e6, 2)                                               AS venta_m,
                ROUND(SUM(precio_total-costo_total)/1e6, 2)                                   AS util_m,
                ROUND((SUM(precio_total)-SUM(costo_total))/NULLIF(SUM(precio_total),0)*100,1) AS margen_pct,
                COUNT(DISTINCT CAST(fecha_comprobante AS DATE))                               AS dias
            FROM {T_TICKETS}, ultimo_mes u
            WHERE EXTRACT(YEAR  FROM CAST(fecha_comprobante AS DATE)) = u.anio
              AND EXTRACT(MONTH FROM CAST(fecha_comprobante AS DATE)) = u.mes
              AND LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa','express')
        ),
        anterior AS (
            SELECT
                ROUND(SUM(precio_total)/1e6, 2)             AS venta_m_ant,
                ROUND(SUM(precio_total-costo_total)/1e6, 2) AS util_m_ant
            FROM {T_TICKETS}, ultimo_mes u
            WHERE (EXTRACT(YEAR FROM CAST(fecha_comprobante AS DATE)) * 12 +
                   EXTRACT(MONTH FROM CAST(fecha_comprobante AS DATE))) =
                  (u.anio * 12 + u.mes - 1)
              AND LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa','express')
        ),
        presup AS (
            SELECT ROUND(SUM(PRESUPUESTO)/1e6, 2) AS presu_m,
                   COUNT(DISTINCT idarticulo)      AS art_count
            FROM {T_ALERT}
        )
        SELECT a.*, ant.venta_m_ant, ant.util_m_ant, p.presu_m, p.art_count
        FROM actual a, anterior ant, presup p
    """
    try:
        return get_con().execute(q).df().iloc[0].to_dict()
    except Exception:
        return {}


@st.cache_data(ttl=600)
def cargar_ventas_sucursal_mes() -> pd.DataFrame:
    """Ventas del mes actual por sucursal para el panel derecho."""
    mes = date.today().strftime("%Y-%m")
    q = f"""
        SELECT sucursal,
               ROUND(SUM(precio_total)/1e6, 2)     AS ventas_m,
               ROUND(AVG(margen_porcentual)*100, 1) AS margen_pct
        FROM {T_TICKETS}
        WHERE strftime(CAST(fecha_comprobante AS DATE), '%Y-%m') = '{mes}'
          AND LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa','express')
        GROUP BY sucursal ORDER BY ventas_m DESC
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_utilidad_diaria() -> pd.DataFrame:
    """Utilidad diaria del mes actual."""
    mes = date.today().strftime("%Y-%m")
    q = f"""
        SELECT CAST(fecha_comprobante AS DATE) AS fecha,
               ROUND(SUM(precio_total-costo_total)/1e6, 2) AS utilidad_m
        FROM {T_TICKETS}
        WHERE strftime(CAST(fecha_comprobante AS DATE), '%Y-%m') = '{mes}'
          AND LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa','express')
        GROUP BY CAST(fecha_comprobante AS DATE)
        ORDER BY fecha
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_utilidad_mensual() -> pd.DataFrame:
    """Utilidad mensual por año (2024, 2025, 2026) para gráfico comparativo."""
    q = f"""
        SELECT EXTRACT(YEAR  FROM CAST(fecha_comprobante AS DATE)) AS anio,
               EXTRACT(MONTH FROM CAST(fecha_comprobante AS DATE)) AS mes,
               ROUND(SUM(precio_total-costo_total)/1e6, 3)         AS utilidad_m
        FROM {T_TICKETS}
        WHERE LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa','express')
          AND EXTRACT(YEAR FROM CAST(fecha_comprobante AS DATE)) IN (2024,2025,2026)
        GROUP BY anio, mes ORDER BY anio, mes
    """
    try:
        df = get_con().execute(q).df()
        df["anio"] = df["anio"].astype(int)
        df["mes"]  = df["mes"].astype(int)
        return df
    except Exception:
        return pd.DataFrame()




# ─── DETALLE DE ALERTAS (para tarjetas clickeables) ──────────

_COLS_STOCK = """stk_hiper, stk_corrientes, stk_sabin, stk_formosa,
               stk_express, stk_TIROL AS stk_tirol, stk_central,
               STK_TOTAL AS stock_total"""

_COLS_ABASTECER = """cor_abastecer, exp_abastecer, for_abastecer,
               sab_abastecer, hip_abastecer, total_abastecer"""


@st.cache_data(ttl=300)
def detalle_sin_stock(top_n: int = 50) -> pd.DataFrame:
    """Artículos sin stock con alerta de reabastecimiento activa."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, uxb,
               {_COLS_STOCK},
               {_COLS_ABASTECER},
               cant_total AS ventas_90d,
               PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE alerta_reabastecer = 'Sí' AND dias_cobertura = 0
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def detalle_stock_critico(top_n: int = 50) -> pd.DataFrame:
    """Artículos con stock crítico — cobertura entre 1 y 3 días."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, uxb,
               {_COLS_STOCK},
               {_COLS_ABASTECER},
               cant_total AS ventas_90d,
               PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE alerta_reabastecer = 'Sí' AND dias_cobertura BETWEEN 1 AND 3
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def detalle_stock_urgente(top_n: int = 50) -> pd.DataFrame:
    """Artículos urgentes — cobertura entre 4 y 7 días."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, uxb,
               {_COLS_STOCK},
               {_COLS_ABASTECER},
               cant_total AS ventas_90d,
               PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE alerta_reabastecer = 'Sí' AND dias_cobertura BETWEEN 4 AND 7
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def detalle_exceso_stock(top_n: int = 50) -> pd.DataFrame:
    """Artículos con exceso de stock — candidatos a traslado entre sucursales."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, uxb,
               exceso_STK AS exceso_stock,
               {_COLS_STOCK},
               {_COLS_ABASTECER},
               PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE exceso_STK > 0
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def detalle_valor_perdido(top_n: int = 50) -> pd.DataFrame:
    """Artículos con mayor valor perdido por quiebres de stock."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, uxb,
               valor_perdido_TOTAL AS valor_perdido,
               unidades_perdidas_TOTAL AS unidades_perdidas,
               {_COLS_STOCK},
               {_COLS_ABASTECER},
               PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE valor_perdido_TOTAL > 0
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def detalle_presupuesto_compra(top_n: int = 50) -> pd.DataFrame:
    """Detalle de presupuesto de compra próximos 30 días, por artículo."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, uxb,
               {_COLS_STOCK},
               {_COLS_ABASTECER},
               PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE PRESUPUESTO > 0
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_rango_tendencia_semanal() -> tuple[str, str]:
    """
    Devuelve (desde, hasta) como strings 'd mmm' en español para el período
    de 7 días usado en el análisis de tendencia semanal.
    """
    q = f"""
        SELECT
            (SELECT MAX(CAST(fecha_comprobante AS DATE)) FROM {T_TICKETS}) - INTERVAL 6 DAY AS desde,
            (SELECT MAX(CAST(fecha_comprobante AS DATE)) FROM {T_TICKETS}) AS hasta
    """
    meses_es = {1:"ene",2:"feb",3:"mar",4:"abr",5:"may",6:"jun",
                7:"jul",8:"ago",9:"sep",10:"oct",11:"nov",12:"dic"}
    try:
        row = get_con().execute(q).df().iloc[0]
        desde, hasta = row["desde"], row["hasta"]
        desde_str = f"{desde.day} {meses_es[desde.month]}"
        hasta_str = f"{hasta.day} {meses_es[hasta.month]}"
        return desde_str, hasta_str
    except Exception:
        return "", ""


@st.cache_data(ttl=600)
def cargar_tendencia_semanal_resumen() -> pd.DataFrame:
    """
    Resumen de tendencia de ventas (últimos 7 días) por sucursal, calculado
    con regresión lineal (regr_slope nativo de DuckDB) igual que el análisis
    de Cristina: alta / baja / estable según la pendiente de cantidad_total
    vendida día a día.
    """
    q = f"""
        WITH base AS (
            SELECT idarticulo, sucursal,
                   CAST(fecha_comprobante AS DATE) AS fecha,
                   SUM(cantidad_total) AS cantidad
            FROM {T_TICKETS}
            WHERE CAST(fecha_comprobante AS DATE) >=
                  (SELECT MAX(CAST(fecha_comprobante AS DATE)) FROM {T_TICKETS}) - INTERVAL 6 DAY
            GROUP BY idarticulo, sucursal, CAST(fecha_comprobante AS DATE)
        ),
        dias AS (
            SELECT *,
                   DATE_DIFF('day',
                       MIN(fecha) OVER (PARTITION BY idarticulo, sucursal), fecha
                   ) AS x_dia
            FROM base
        ),
        regresion AS (
            SELECT idarticulo, sucursal,
                   COUNT(*) AS puntos,
                   AVG(cantidad) AS promedio,
                   regr_slope(cantidad, x_dia) AS pendiente
            FROM dias
            GROUP BY idarticulo, sucursal
        ),
        clasif AS (
            SELECT idarticulo, sucursal,
                   CASE
                     WHEN puntos < 2 THEN 'estable'
                     WHEN pendiente > 0.1 THEN 'alta'
                     WHEN pendiente < -0.1 THEN 'baja'
                     ELSE 'estable'
                   END AS tendencia
            FROM regresion
        ),
        resumen AS (
            SELECT sucursal, tendencia, COUNT(*) AS cantidad_articulos
            FROM clasif
            GROUP BY sucursal, tendencia
        ),
        totales AS (
            SELECT sucursal, SUM(cantidad_articulos) AS total_articulos
            FROM resumen GROUP BY sucursal
        )
        SELECT r.sucursal, r.tendencia, r.cantidad_articulos, t.total_articulos,
               ROUND(r.cantidad_articulos * 100.0 / t.total_articulos) AS porcentaje
        FROM resumen r
        JOIN totales t ON r.sucursal = t.sucursal
        ORDER BY r.sucursal, r.tendencia
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def detalle_tendencia_articulos(sucursal: str, tendencia: str,
                                top_n: int = 100) -> pd.DataFrame:
    """
    Detalle de artículos para una sucursal + clasificación de tendencia
    específica (alta / baja / estable), con descripción, familia, proveedor,
    ventas/unidades del período y la pendiente calculada.
    """
    q = f"""
        WITH base AS (
            SELECT t.idarticulo, t.sucursal,
                   CAST(t.fecha_comprobante AS DATE) AS fecha,
                   SUM(t.cantidad_total) AS cantidad
            FROM {T_TICKETS} t
            WHERE CAST(t.fecha_comprobante AS DATE) >=
                  (SELECT MAX(CAST(fecha_comprobante AS DATE)) FROM {T_TICKETS}) - INTERVAL 6 DAY
              AND t.sucursal = '{sucursal}'
            GROUP BY t.idarticulo, t.sucursal, CAST(t.fecha_comprobante AS DATE)
        ),
        dias AS (
            SELECT *,
                   DATE_DIFF('day',
                       MIN(fecha) OVER (PARTITION BY idarticulo, sucursal), fecha
                   ) AS x_dia
            FROM base
        ),
        regresion AS (
            SELECT idarticulo, sucursal,
                   COUNT(*) AS puntos,
                   ROUND(AVG(cantidad),1) AS promedio_diario,
                   ROUND(SUM(cantidad),0) AS unidades_periodo,
                   ROUND(regr_slope(cantidad, x_dia),2) AS pendiente
            FROM dias
            GROUP BY idarticulo, sucursal
        ),
        clasif AS (
            SELECT *,
                   CASE
                     WHEN puntos < 2 THEN 'estable'
                     WHEN pendiente > 0.1 THEN 'alta'
                     WHEN pendiente < -0.1 THEN 'baja'
                     ELSE 'estable'
                   END AS tendencia
            FROM regresion
        )
        SELECT a.descripcion, a.familia, a.subfamilia, TRIM(a.proveedor) AS proveedor,
               c.unidades_periodo, c.promedio_diario, c.pendiente,
               a.dias_cobertura, a.STK_TOTAL AS stock_total,
               a.PRESUPUESTO AS presupuesto_compra
        FROM clasif c
        JOIN {T_ALERT} a ON c.idarticulo = a.idarticulo
        WHERE c.tendencia = '{tendencia}'
        ORDER BY c.unidades_periodo DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


def calcular_indice_urgencia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula un Índice de Urgencia de Reposición (IUR) en Python puro,
    sin consultar la base de nuevo, a partir del DataFrame ya traído por
    detalle_tendencia_articulos().

    Combina 3 señales normalizadas 0-1:
      - pendiente_norm:   crecimiento relativo al volumen propio del artículo
                          (pendiente / promedio_diario) — evita que solo
                          ganen los artículos de mayor volumen.
      - riesgo_stock:     1.0 = sin cobertura (0 días), 0.0 = cobertura >= 30 días.
      - presupuesto_norm: peso económico del artículo (mayor presupuesto
                          de compra pendiente = mayor prioridad).

    IUR = pendiente_norm*0.4 + riesgo_stock*0.4 + presupuesto_norm*0.2

    Devuelve el mismo DataFrame ordenado por indice_urgencia descendente,
    con las columnas intermedias visibles para trazabilidad.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    # Pendiente relativa al volumen propio (evita sesgo hacia artículos grandes)
    promedio_seguro = out["promedio_diario"].replace(0, 1)
    out["pendiente_rel"] = out["pendiente"] / promedio_seguro

    # Riesgo de stock: 0 días = 1.0 (máxima urgencia), 30+ días = 0.0
    out["riesgo_stock"] = (30 - out["dias_cobertura"].clip(upper=30)) / 30

    def _normalizar(serie: pd.Series) -> pd.Series:
        rango = serie.max() - serie.min()
        if rango == 0 or pd.isna(rango):
            return serie * 0
        return (serie - serie.min()) / rango

    out["pendiente_norm"]   = _normalizar(out["pendiente_rel"])
    out["presupuesto_norm"] = _normalizar(out["presupuesto_compra"])

    out["indice_urgencia"] = (
        out["pendiente_norm"]   * 0.4 +
        out["riesgo_stock"]     * 0.4 +
        out["presupuesto_norm"] * 0.2
    ).round(3)

    # Interpretación legible del índice
    def _nivel(iur: float) -> str:
        if iur >= 0.7:  return "🔴 Comprar ya"
        if iur >= 0.5:  return "🟠 OC próximos días"
        if iur >= 0.3:  return "🟡 Monitorear"
        return               "🟢 Sin urgencia"

    out["accion_sugerida"] = out["indice_urgencia"].apply(_nivel)

    # Limpiar columnas intermedias de normalización, dejar solo lo legible
    out = out.drop(columns=["pendiente_rel", "pendiente_norm", "presupuesto_norm"])

    # Reordenar: indice + accion primero, luego el resto
    cols_primero = ["indice_urgencia", "accion_sugerida"]
    resto = [c for c in out.columns if c not in cols_primero]
    out = out[cols_primero + resto]

    return out.sort_values("indice_urgencia", ascending=False).reset_index(drop=True)


# ─── CARGA DEL CATÁLOGO PARA SELECTORES ──────────────────────


@st.cache_data(ttl=3600)
def cargar_familias() -> list[str]:
    from config import T_PROV
    q = f"SELECT DISTINCT familia FROM {T_PROV} WHERE familia IS NOT NULL ORDER BY familia"
    try:
        return get_con().execute(q).df()["familia"].tolist()
    except Exception:
        return []


@st.cache_data(ttl=3600)
def cargar_subfamilias(familia: str = None) -> list[str]:
    from config import T_PROV
    filtro = f"AND familia='{familia}'" if familia and familia != "Todas" else ""
    q = f"SELECT DISTINCT subfamilia FROM {T_PROV} WHERE subfamilia IS NOT NULL {filtro} ORDER BY subfamilia"
    try:
        return get_con().execute(q).df()["subfamilia"].tolist()
    except Exception:
        return []


@st.cache_data(ttl=3600)
def cargar_proveedores(familia: str = None, subfamilia: str = None) -> list[str]:
    from config import T_PROV
    filtros = ["proveedor IS NOT NULL"]
    if familia    and familia    != "Todas": filtros.append(f"familia='{familia}'")
    if subfamilia and subfamilia != "Todas": filtros.append(f"subfamilia='{subfamilia}'")
    q = f"SELECT DISTINCT TRIM(proveedor) AS proveedor FROM {T_PROV} WHERE {' AND '.join(filtros)} ORDER BY proveedor"
    try:
        return get_con().execute(q).df()["proveedor"].tolist()
    except Exception:
        return []


@st.cache_data(ttl=3600)
def cargar_proveedores_agente() -> list[str]:
    """Lista completa de proveedores para contexto del agente."""
    from config import T_PROV
    q = f"SELECT DISTINCT TRIM(proveedor) AS proveedor FROM {T_PROV} WHERE proveedor IS NOT NULL ORDER BY proveedor"
    try:
        return get_con().execute(q).df()["proveedor"].tolist()
    except Exception:
        return []