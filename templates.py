"""
templates.py — Queries pre-verificadas directamente en MotherDuck.
Resuelven casos frecuentes sin pasar por el LLM para generar SQL.
Cada template incluye su condición de activación y la query parametrizada.
"""
import re
import pandas as pd
from typing import Optional
from config import T_TICKETS, T_PROV, T_PRECIOS, T_ALERT
from ejecutor import ejecutar_sql
from enriquecedor import Contexto


# ─── TEMPLATES ────────────────────────────────────────────────

def tpl_precio_compra_simple(ctx: Contexto) -> Optional[pd.DataFrame]:
    """
    Precios de compra de artículos de una categoría/marca (sin ranking de ventas).
    Verificado en MD: funciona con JOIN proveedores ↔ ultimos_precios via idartalfa.
    """
    filtros = ["op.ultimo_precio_compra IS NOT NULL"]

    if ctx.subfamilia:
        filtros.append(f"LOWER(p.subfamilia) LIKE LOWER('%{ctx.subfamilia}%')")
    elif ctx.familia and not ctx.marcas:
        filtros.append(f"p.familia = '{ctx.familia}'")
    elif ctx.marcas:
        f_marcas = " OR ".join(f"LOWER(p.descripcion) LIKE '%{m}%'" for m in ctx.marcas)
        filtros.append(f"({f_marcas})")

    # Filtro de medida
    if ctx.medida_str:
        filtros.append(_filtro_medida("p.descripcion", ctx.medida_str))

    # Filtro de rango de volumen (ej: más de 900cc)
    if ctx.rango_min_cc:
        filtros.append(_filtro_rango_volumen_mayor("p.descripcion", ctx.rango_min_cc))
    if ctx.rango_max_cc:
        filtros.append(_filtro_rango_volumen_menor("p.descripcion", ctx.rango_max_cc))

    if len(filtros) == 1:  # Solo el filtro base — muy amplio
        return None

    where = "WHERE " + " AND ".join(filtros)
    sql = f"""
        SELECT TRIM(p.descripcion)              AS descripcion,
               p.familia,
               p.subfamilia,
               TRIM(p.proveedor)                AS proveedor,
               ROUND(op.ultimo_precio_compra,2) AS precio_compra,
               TRIM(op.proveedor_oc)            AS proveedor_oc,
               CAST(op.fecha_ultima_oc AS DATE) AS fecha_ultima_oc,
               p.stk_total                      AS stock_total
        FROM {T_PROV} p
        JOIN {T_PRECIOS} op ON p.idartalfa = op.idartalfa
        {where}
        ORDER BY op.ultimo_precio_compra DESC
        LIMIT {ctx.top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template precio_simple] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_precio_con_ventas(ctx: Contexto) -> Optional[pd.DataFrame]:
    """
    Top N más vendidos de una categoría CON su precio de compra OC.
    Verificado en MD: JOIN tickets_all ↔ ultimos_precios via idartalfa.
    """
    filtros_t = []

    if ctx.subfamilia:
        filtros_t.append(f"LOWER(t.subfamilia) LIKE LOWER('%{ctx.subfamilia}%')")
    elif ctx.marcas:
        f_marcas = " OR ".join(f"LOWER(t.descripcion) LIKE '%{m}%'" for m in ctx.marcas)
        filtros_t.append(f"({f_marcas})")

    if ctx.medida_str:
        filtros_t.append(_filtro_medida("t.descripcion", ctx.medida_str))

    if ctx.rango_min_cc:
        filtros_t.append(_filtro_rango_volumen_mayor("t.descripcion", ctx.rango_min_cc))

    if ctx.fecha_desde:
        filtros_t.append(
            f"CAST(t.fecha_comprobante AS DATE) BETWEEN '{ctx.fecha_desde}' AND '{ctx.fecha_hasta}'"
        )
    else:
        from datetime import date
        filtros_t.append(f"CAST(t.fecha_comprobante AS DATE) >= '2026-01-01'")

    if ctx.sucursales:
        suc_str = ", ".join(f"'{s}'" for s in ctx.sucursales)
        filtros_t.append(f"LOWER(t.sucursal) IN ({suc_str})")

    if not filtros_t:
        return None

    where = "WHERE " + " AND ".join(filtros_t)
    sql = f"""
        WITH top AS (
            SELECT t.idartalfa, t.descripcion,
                   ROUND(SUM(t.cantidad_total),0) AS unidades,
                   ROUND(SUM(t.precio_total),2)   AS ventas,
                   ROUND(AVG(t.margen_porcentual)*100,1) AS margen_pct
            FROM {T_TICKETS} t
            {where}
            GROUP BY t.idartalfa, t.descripcion
            ORDER BY unidades DESC
            LIMIT {ctx.top_n}
        )
        SELECT top.descripcion,
               top.unidades,
               top.ventas,
               top.margen_pct,
               ROUND(op.ultimo_precio_compra,2) AS precio_compra,
               TRIM(op.proveedor_oc)            AS proveedor_oc,
               CAST(op.fecha_ultima_oc AS DATE) AS fecha_ultima_oc
        FROM top
        LEFT JOIN {T_PRECIOS} op ON top.idartalfa = op.idartalfa
        ORDER BY top.unidades DESC
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template precio_con_ventas] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_top_ventas(ctx: Contexto) -> Optional[pd.DataFrame]:
    """Top artículos más vendidos de una categoría/marca/sucursal."""
    filtros = []

    if ctx.subfamilia:
        filtros.append(f"LOWER(subfamilia) LIKE LOWER('%{ctx.subfamilia}%')")
    elif ctx.familia:
        # Categoría general sin subfamilia específica — usar nombre exacto
        filtros.append(f"familia = '{ctx.familia}'")
    elif ctx.marcas:
        f_marcas = " OR ".join(f"LOWER(descripcion) LIKE '%{m}%'" for m in ctx.marcas)
        filtros.append(f"({f_marcas})")

    if ctx.medida_str:
        filtros.append(_filtro_medida("descripcion", ctx.medida_str))

    if ctx.rango_min_cc:
        filtros.append(_filtro_rango_volumen_mayor("descripcion", ctx.rango_min_cc))
    if ctx.rango_max_cc:
        filtros.append(_filtro_rango_volumen_menor("descripcion", ctx.rango_max_cc))

    if ctx.fecha_desde:
        filtros.append(
            f"CAST(fecha_comprobante AS DATE) BETWEEN '{ctx.fecha_desde}' AND '{ctx.fecha_hasta}'"
        )

    if ctx.sucursales:
        suc_str = ", ".join(f"'{s}'" for s in ctx.sucursales)
        filtros.append(f"LOWER(sucursal) IN ({suc_str})")
    else:
        from config import SUC_VENTAS
        suc_str = ", ".join(f"'{s}'" for s in SUC_VENTAS)
        filtros.append(f"LOWER(sucursal) IN ({suc_str})")

    if not filtros:
        return None

    where = "WHERE " + " AND ".join(filtros)
    sql = f"""
        SELECT descripcion,
               sucursal,
               ROUND(SUM(precio_total),2)             AS ventas,
               ROUND(SUM(precio_total-costo_total),2) AS utilidad,
               ROUND(SUM(cantidad_total),0)           AS unidades,
               ROUND(AVG(margen_porcentual)*100,1)    AS margen_pct
        FROM {T_TICKETS}
        {where}
        GROUP BY descripcion, sucursal
        ORDER BY ventas DESC
        LIMIT {ctx.top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template top_ventas] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_stock_categoria(ctx: Contexto) -> Optional[pd.DataFrame]:
    """Stock actual de artículos de una categoría."""
    filtros = []

    if ctx.subfamilia:
        filtros.append(f"LOWER(p.subfamilia) LIKE LOWER('%{ctx.subfamilia}%')")
    elif ctx.marcas:
        f_marcas = " OR ".join(f"LOWER(p.descripcion) LIKE '%{m}%'" for m in ctx.marcas)
        filtros.append(f"({f_marcas})")

    if not filtros:
        return None

    where = "WHERE " + " AND ".join(filtros)
    sql = f"""
        SELECT TRIM(p.descripcion) AS descripcion,
               p.subfamilia,
               TRIM(p.proveedor)   AS proveedor,
               p.stk_hiper, p.stk_corrientes, p.stk_sabin,
               p.stk_formosa, p.stk_express, p.stk_total
        FROM {T_PROV} p
        {where}
        ORDER BY p.stk_total DESC
        LIMIT {ctx.top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template stock] Error: {err}")
        return None
    return df if not df.empty else None




def tpl_comparar_precio_venta_compra(ctx: Contexto) -> pd.DataFrame | None:
    """
    Compara último precio de venta (tickets_all) vs último precio de compra (ultimos_precios).
    Usa ROW_NUMBER para obtener el precio_unitario más reciente por artículo.
    Verificado en MD.
    """
    filtros_t = []
    if ctx.subfamilia:
        filtros_t.append(f"t.subfamilia = '{ctx.subfamilia}'")
    elif ctx.marcas:
        f_marcas = " OR ".join(f"LOWER(t.descripcion) LIKE '%{m}%'" for m in ctx.marcas)
        filtros_t.append(f"({f_marcas})")
    if ctx.medida_str:
        from templates import _filtro_medida
        filtros_t.append(_filtro_medida("t.descripcion", ctx.medida_str).replace("descripcion","t.descripcion"))

    filtros_t.append("t.precio_unitario > 0")
    where = "WHERE " + " AND ".join(filtros_t)

    sql = f"""
        WITH pv AS (
            SELECT t.descripcion, t.idartalfa,
                   ROUND(t.precio_unitario, 2) AS precio_venta,
                   CAST(t.fecha_comprobante AS DATE) AS fecha_venta,
                   ROW_NUMBER() OVER (
                       PARTITION BY t.descripcion
                       ORDER BY CAST(t.fecha_comprobante AS DATE) DESC
                   ) AS rn
            FROM {T_TICKETS} t
            {where}
        )
        SELECT pv.descripcion,
               pv.precio_venta                                        AS ultimo_precio_venta,
               pv.fecha_venta                                         AS fecha_ultimo_ticket,
               ROUND(op.ultimo_precio_compra, 2)                     AS precio_compra_oc,
               TRIM(op.proveedor_oc)                                  AS proveedor_oc,
               CAST(op.fecha_ultima_oc AS DATE)                      AS fecha_ultima_oc,
               ROUND((pv.precio_venta - op.ultimo_precio_compra)
                     / NULLIF(op.ultimo_precio_compra,0) * 100, 2)  AS margen_real_pct
        FROM pv
        JOIN {T_PRECIOS} op ON pv.idartalfa = op.idartalfa
        WHERE pv.rn = 1
        ORDER BY margen_real_pct ASC
        LIMIT {ctx.top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template precio_venta_compra] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_mas_vendidos_riesgo_quiebre(ctx: Contexto, top_n: int = 20) -> pd.DataFrame | None:
    """
    Artículos más vendidos que tienen riesgo de quiebre de stock.
    Usa result_final_alert_all con alerta_reabastecer = 'Sí' (con tilde).
    Ordenado por ventas 90d DESC para mostrar los más importantes primero.
    """
    filtros = ["alerta_reabastecer = \'Sí\'", "cant_total > 0"]

    if ctx.subfamilia:
        filtros.append(f"LOWER(subfamilia) LIKE LOWER(\'%{ctx.subfamilia}%\')")
    elif ctx.familia:
        filtros.append(f"familia = \'{ctx.familia}\'")
    elif ctx.marcas:
        f_m = " OR ".join(f"LOWER(descripcion) LIKE \'%{m}%\'" for m in ctx.marcas)
        filtros.append(f"({f_m})")

    # Filtro de dias_cobertura según urgencia
    if ctx.pide_alerta:
        filtros.append("dias_cobertura <= 7")   # crítico/urgente
    else:
        filtros.append("dias_cobertura <= 30")  # riesgo general

    where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        SELECT
            descripcion,
            familia,
            subfamilia,
            TRIM(proveedor)     AS proveedor,
            cant_total          AS ventas_90d,
            STK_TOTAL           AS stock_total,
            dias_cobertura,
            nivel_riesgo,
            clase_abc,
            PRESUPUESTO         AS presupuesto_30d,
            total_abastecer     AS unidades_a_pedir,
            valor_perdido_TOTAL AS valor_perdido,
            CASE
                WHEN dias_cobertura = 0  THEN '🔴 SIN STOCK'
                WHEN dias_cobertura <= 3 THEN '🔴 CRÍTICO'
                WHEN dias_cobertura <= 7 THEN '🟠 URGENTE'
                WHEN dias_cobertura <= 14 THEN '🟡 BAJO'
                ELSE '🟡 PRECAUCIÓN'
            END AS alerta
        FROM {T_ALERT}
        {where}
        ORDER BY cant_total DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template mas_vendidos_riesgo] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_criticos_con_ventas(ctx: Contexto, top_n: int = 20) -> pd.DataFrame | None:
    """
    Artículos críticos de stock cruzados con sus ventas mensuales.
    Para consultas como: "clasificar productos críticos según venta mensual"
    """
    from datetime import date
    mes_desde = date.today().replace(day=1).isoformat()

    filtros = ["r.dias_cobertura >= 0", "r.dias_cobertura <= 14"]
    if ctx.subfamilia:
        filtros.append(f"LOWER(r.subfamilia) LIKE LOWER('%{ctx.subfamilia}%')")
    if ctx.marcas:
        f_m = " OR ".join(f"LOWER(r.descripcion) LIKE '%{m}%'" for m in ctx.marcas)
        filtros.append(f"({f_m})")
    where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        WITH ventas_mes AS (
            SELECT idartalfa,
                   ROUND(SUM(precio_total),2)   AS ventas_mes,
                   ROUND(SUM(cantidad_total),0) AS unidades_mes
            FROM {T_TICKETS}
            WHERE CAST(fecha_comprobante AS DATE) >= '{mes_desde}'
            GROUP BY idartalfa
        )
        SELECT
            r.descripcion,
            r.familia,
            r.subfamilia,
            r.proveedor,
            r.dias_cobertura,
            r.nivel_riesgo,
            r.STK_TOTAL      AS stock_total,
            r.stk_hiper, r.stk_corrientes, r.stk_sabin,
            r.clase_abc,
            COALESCE(v.ventas_mes, 0)   AS ventas_mes,
            COALESCE(v.unidades_mes, 0) AS unidades_mes,
            CASE
                WHEN r.dias_cobertura <= 3  THEN '🔴 CRÍTICO'
                WHEN r.dias_cobertura <= 7  THEN '🟠 URGENTE'
                WHEN r.dias_cobertura <= 14 THEN '🟡 BAJO'
                ELSE '🟢 OK'
            END AS nivel
        FROM {T_ALERT} r
        LEFT JOIN ventas_mes v ON CAST(r.idarticuloalfa AS BIGINT) = v.idartalfa
        {where}
        ORDER BY r.dias_cobertura ASC, ventas_mes DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template criticos_ventas] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_valor_perdido_quiebre(ctx: Contexto, top_n: int = 15) -> pd.DataFrame | None:
    """
    Valor perdido en $ por quiebres de stock — '¿cuánto perdí este mes?'
    Usa valor_perdido_TOTAL de result_final_alert_all.
    """
    filtros = ["valor_perdido_TOTAL > 0"]
    if ctx.subfamilia:
        filtros.append(f"LOWER(subfamilia) LIKE LOWER(\'%{ctx.subfamilia}%\')")
    elif ctx.familia:
        filtros.append(f"familia = \'{ctx.familia}\'")
    where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               valor_perdido_TOTAL  AS valor_perdido,
               unidades_perdidas_TOTAL AS unidades_perdidas,
               dias_cobertura, STK_TOTAL AS stock_total,
               nivel_riesgo
        FROM {T_ALERT}
        {where}
        ORDER BY valor_perdido_TOTAL DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template valor_perdido] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_precio_bajo_costo(ctx: Contexto, top_n: int = 15) -> pd.DataFrame | None:
    """
    Artículos vendiéndose por debajo del costo actual — pérdida directa por venta.
    Usa precio_bajo_costo = true de result_final_alert_all.
    """
    filtros = ["precio_bajo_costo = true"]
    if ctx.subfamilia:
        filtros.append(f"LOWER(subfamilia) LIKE LOWER(\'%{ctx.subfamilia}%\')")
    elif ctx.familia:
        filtros.append(f"familia = \'{ctx.familia}\'")
    elif ctx.marcas:
        f_m = " OR ".join(f"LOWER(descripcion) LIKE \'%{m}%\'" for m in ctx.marcas)
        filtros.append(f"({f_m})")
    where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               ROUND(precio_actual,2)  AS precio_venta,
               ROUND(costo_unit,2)     AS costo_actual,
               ROUND((precio_actual-costo_unit)/costo_unit*100,1) AS margen_ticket_pct,
               cant_total AS ventas_90d
        FROM {T_ALERT}
        {where}
        ORDER BY cant_total DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template precio_bajo_costo] Error: {err}")
        return None
    return df if not df.empty else None



def tpl_presupuesto_por_proveedor(ctx: Contexto, top_n: int = 15) -> pd.DataFrame | None:
    """
    Presupuesto de compra de los próximos 30 días agrupado por proveedor.
    """
    filtros = ["PRESUPUESTO > 0"]
    if ctx.subfamilia:
        filtros.append(f"LOWER(subfamilia) LIKE LOWER(\'%{ctx.subfamilia}%\')")
    elif ctx.familia:
        filtros.append(f"familia = \'{ctx.familia}\'")
    where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        SELECT TRIM(proveedor) AS proveedor,
               COUNT(*)                       AS articulos,
               ROUND(SUM(PRESUPUESTO),2)       AS presupuesto_total,
               ROUND(AVG(dias_cobertura),1)    AS dias_cobertura_prom
        FROM {T_ALERT}
        {where}
        GROUP BY proveedor
        ORDER BY presupuesto_total DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template presupuesto_proveedor] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_exceso_stock_traslado(ctx: Contexto, top_n: int = 15) -> pd.DataFrame | None:
    """
    Artículos con exceso de stock, mostrando desbalance entre sucursales
    para identificar oportunidades de traslado en vez de comprar más.
    """
    filtros = ["exceso_STK > 0"]
    if ctx.subfamilia:
        filtros.append(f"LOWER(subfamilia) LIKE LOWER(\'%{ctx.subfamilia}%\')")
    elif ctx.familia:
        filtros.append(f"familia = \'{ctx.familia}\'")
    elif ctx.marcas:
        f_m = " OR ".join(f"LOWER(descripcion) LIKE \'%{m}%\'" for m in ctx.marcas)
        filtros.append(f"({f_m})")
    where = "WHERE " + " AND ".join(filtros)

    sql = f"""
        SELECT descripcion, familia, subfamilia,
               exceso_STK AS exceso_stock,
               stk_hiper, stk_corrientes, stk_sabin, stk_formosa,
               dias_cobertura
        FROM {T_ALERT}
        {where}
        ORDER BY exceso_STK DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template exceso_traslado] Error: {err}")
        return None
    return df if not df.empty else None


def tpl_alta_venta_bajo_margen(ctx: Contexto, top_n: int = 15) -> pd.DataFrame | None:
    """
    'Pregunta trampa': productos que generan mucha plata en ventas
    pero tienen margen real muy bajo (precio venta vs último costo OC).
    """
    filtros_t = ["t.precio_unitario > 0"]
    if ctx.subfamilia:
        filtros_t.append(f"t.subfamilia = \'{ctx.subfamilia}\'")
    elif ctx.marcas:
        f_m = " OR ".join(f"LOWER(t.descripcion) LIKE \'%{m}%\'" for m in ctx.marcas)
        filtros_t.append(f"({f_m})")
    where_t = "WHERE " + " AND ".join(filtros_t)

    sql = f"""
        WITH ultimo_precio AS (
            SELECT t.descripcion, t.idartalfa,
                   ROUND(t.precio_unitario,2) AS precio_venta,
                   ROW_NUMBER() OVER (
                       PARTITION BY t.descripcion
                       ORDER BY CAST(t.fecha_comprobante AS DATE) DESC
                   ) AS rn
            FROM {T_TICKETS} t
            {where_t}
        ),
        ventas_tot AS (
            SELECT idartalfa, descripcion,
                   ROUND(SUM(precio_total),2) AS ventas_totales,
                   ROUND(SUM(cantidad_total),0) AS unidades
            FROM {T_TICKETS}
            GROUP BY idartalfa, descripcion
        )
        SELECT vt.descripcion, vt.ventas_totales, vt.unidades,
               up.precio_venta,
               ROUND(op.ultimo_precio_compra,2) AS precio_compra,
               ROUND((up.precio_venta-op.ultimo_precio_compra)
                     /NULLIF(op.ultimo_precio_compra,0)*100,1) AS margen_real_pct
        FROM ventas_tot vt
        JOIN ultimo_precio up ON vt.idartalfa = up.idartalfa AND up.rn = 1
        JOIN {T_PRECIOS} op ON vt.idartalfa = op.idartalfa
        WHERE op.ultimo_precio_compra > 0
        ORDER BY vt.ventas_totales DESC
        LIMIT {top_n}
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template alta_venta_bajo_margen] Error: {err}")
        return None
    return df if not df.empty else None



def tpl_impacto_apertura_sabin(ctx: Contexto) -> pd.DataFrame | None:
    """
    Compara ventas promedio diarias de Hiper antes/después de la apertura
    de Sabin (6-jun-2026) para medir canibalización vs mercado nuevo.
    """
    sql = f"""
        WITH datos AS (
            SELECT
                sucursal,
                CASE WHEN CAST(fecha_comprobante AS DATE) < \'2026-06-06\'
                     THEN \'antes_sabin\' ELSE \'despues_sabin\' END AS periodo,
                CAST(fecha_comprobante AS DATE) AS fecha,
                precio_total
            FROM {T_TICKETS}
            WHERE sucursal IN (\'hiper\',\'sabin\',\'corrientes\')
              AND CAST(fecha_comprobante AS DATE) BETWEEN \'2026-05-01\' AND CURRENT_DATE
        )
        SELECT sucursal, periodo,
               ROUND(SUM(precio_total)/1e6,1)                       AS ventas_totales_m,
               COUNT(DISTINCT fecha)                                AS dias,
               ROUND(SUM(precio_total)/1e6/COUNT(DISTINCT fecha),2) AS venta_promedio_diaria_m
        FROM datos
        GROUP BY sucursal, periodo
        ORDER BY sucursal, periodo
    """
    df, err = ejecutar_sql(sql)
    if err:
        print(f"   [template impacto_sabin] Error: {err}")
        return None
    return df if not df.empty else None


# ─── ROUTER DE TEMPLATES ──────────────────────────────────────

def resolver_con_template(ctx: Contexto) -> Optional[pd.DataFrame]:
    """
    Elige y ejecuta el template más apropiado según el contexto.
    Retorna DataFrame o None si no hay template aplicable.
    """
    # Necesita al menos categoría o marcas
    if not ctx.categoria_key and not ctx.marcas and not ctx.rango_min_cc:
        return None

    p_lower = ctx.texto_libre.lower()

    # Detectar si pide comparación precio venta vs compra
    pide_comparar = any(x in p_lower for x in [
        "comparar precio", "precio venta vs", "venta vs compra",
        "precio de venta vs", "comparar precios de venta",
        "precio venta y compra", "precio de compra vs",
        "compra con precio", "compra con venta", "precios de compra con",
        "precios de venta", "precio de compra con",
        "precio de compra y venta", "compra y venta"])

    print(f"   [template] cat={ctx.categoria_key!r} marcas={ctx.marcas} "
          f"precio={ctx.pide_precio} comparar={pide_comparar} "
          f"ranking={ctx.pide_ranking} stock={ctx.pide_stock}")

    # -2d. IMPACTO APERTURA SABIN (canibalización vs mercado nuevo)
    pide_sabin_impacto = any(x in p_lower for x in [
        "sabin.*quito", "sabin.*quitó", "sabin.*hiper", "canibaliz",
        "sabin.*mercado nuevo", "sabin le quito", "sabin le quitó",
        "impacto.*sabin", "apertura.*sabin.*hiper"])
    if pide_sabin_impacto:
        print(f"   [router] → tpl_impacto_apertura_sabin")
        df = tpl_impacto_apertura_sabin(ctx)
        if df is not None:
            return df

    # -2. PRESUPUESTO POR PROVEEDOR
    pide_presu_prov = any(x in p_lower for x in [
        "presupuesto de compra", "presupuesto total", "presupuesto por proveedor",
        "presupuesto.*proveedor", "cuanto tengo que comprar", "cuánto tengo que comprar",
        "presupuesto.*30 dias", "presupuesto.*30 días"])
    if pide_presu_prov:
        print(f"   [router] → tpl_presupuesto_por_proveedor")
        df = tpl_presupuesto_por_proveedor(ctx)
        if df is not None:
            return df

    # -2b. EXCESO DE STOCK PARA TRASLADO
    pide_traslado = any(x in p_lower for x in [
        "exceso de stock", "sobrestock", "trasladar", "traslado entre sucursales",
        "stock para trasladar", "exceso.*sucursal"])
    if pide_traslado:
        print(f"   [router] → tpl_exceso_stock_traslado")
        df = tpl_exceso_stock_traslado(ctx)
        if df is not None:
            return df

    # -2c. ALTA VENTA / BAJO MARGEN (pregunta trampa del dueño)
    pide_trampa = any(x in p_lower for x in [
        "genera mas plata", "genera más plata", "mas plata pero", "más plata pero",
        "casi no me deja", "casi no deja ganancia", "vende mucho pero",
        "alta venta.*bajo margen", "mucha plata.*poco margen"])
    if pide_trampa:
        print(f"   [router] → tpl_alta_venta_bajo_margen")
        df = tpl_alta_venta_bajo_margen(ctx)
        if df is not None:
            return df

    # -1. VALOR PERDIDO POR QUIEBRES (cuánto perdí)
    pide_perdida = any(x in p_lower for x in [
        "cuanto perdi", "cuánto perdí", "cuanto se perdio", "cuánto se perdió",
        "valor perdido", "perdida por quiebre", "pérdida por quiebre",
        "dinero perdido", "ventas perdidas", "cuanto dinero perdi"])
    if pide_perdida:
        print(f"   [router] → tpl_valor_perdido_quiebre")
        df = tpl_valor_perdido_quiebre(ctx)
        if df is not None:
            return df

    # -1b. PRECIO BAJO COSTO (vendiendo a pérdida)
    pide_bajo_costo = any(x in p_lower for x in [
        "bajo costo", "bajo el costo", "debajo del costo", "por debajo del costo",
        "vendiendo a perdida", "vendiendo a pérdida", "costo de reposicion",
        "costo de reposición", "menor al costo"])
    if pide_bajo_costo:
        print(f"   [router] → tpl_precio_bajo_costo")
        df = tpl_precio_bajo_costo(ctx)
        if df is not None:
            return df

    # 0. CRÍTICOS CON VENTAS — cuando pide clasificar o alertas
    pide_criticos = any(x in p_lower for x in [
        "clasificar", "clasificacion", "clasificación critico",
        "productos criticos", "productos críticos", "criticos segun",
        "críticos según venta", "necesitan stock", "bajo stock"])
    if pide_criticos or (ctx.pide_alerta and ctx.pide_stock):
        print(f"   [router] → tpl_criticos_con_ventas")
        df = tpl_criticos_con_ventas(ctx)
        if df is not None:
            return df

    # 1. COMPARAR precio venta vs compra — PRIMERA PRIORIDAD
    if pide_comparar and ctx.categoria_key:
        print(f"   [router] → tpl_comparar_precio_venta_compra")
        df = tpl_comparar_precio_venta_compra(ctx)
        if df is not None:
            return df

    # 2. Precio + ranking → top vendidos con precio compra
    if ctx.pide_precio and ctx.pide_ranking:
        print(f"   [router] → tpl_precio_con_ventas")
        df = tpl_precio_con_ventas(ctx)
        if df is not None:
            return df

    # 3. Solo precio de compra (sin ventas ni comparación)
    if ctx.pide_precio and not ctx.pide_ranking and not pide_comparar:
        print(f"   [router] → tpl_precio_compra_simple")
        df = tpl_precio_compra_simple(ctx)
        if df is not None:
            return df

    # 4. Más vendidos con riesgo de quiebre
    pide_riesgo = any(x in p_lower for x in [
        "riesgo de quiebre", "riesgo quiebre", "quiebre de stock",
        "pueden quedar sin stock", "pueden faltar", "van a faltar",
        "mas vendidos.*stock", "riesgo.*stock", "stock.*riesgo",
        "articulos mas vendidos.*stock", "necesitan reposicion",
        "necesitan reabastecimiento"])
    if pide_riesgo or (ctx.pide_ranking and ctx.pide_stock):
        print(f"   [router] → tpl_mas_vendidos_riesgo_quiebre")
        df = tpl_mas_vendidos_riesgo_quiebre(ctx)
        if df is not None:
            return df

    # Stock general
    if ctx.pide_stock:
        print(f"   [router] → tpl_stock_categoria")
        df = tpl_stock_categoria(ctx)
        if df is not None:
            return df

    # 5. Ranking de ventas
    if ctx.pide_ranking or ctx.rango_min_cc or ctx.medida_str:
        print(f"   [router] → tpl_top_ventas")
        df = tpl_top_ventas(ctx)
        if df is not None:
            return df

    # 6. Categoría sin intención clara → top ventas por defecto
    if ctx.categoria_key:
        print(f"   [router] → tpl_top_ventas (default)")
        df = tpl_top_ventas(ctx)
        if df is not None:
            return df

    return None


# ─── HELPERS ─────────────────────────────────────────────────

def _filtro_medida(col: str, medida: str) -> str:
    """Genera filtro LIKE robusto para una medida."""
    variantes = [medida]
    # Agregar variantes comunes
    if medida == "1 kg":
        variantes = ["1 kg", "x1kg", "x 1kg", "1kg", " 1 kg", "x1 kg"]
    elif medida == "500g":
        variantes = ["500g", "500 g", "x500", "x500g", "500gr"]
    elif medida == "1kg":
        variantes = ["1kg", "1 kg", "x1kg"]

    likes = " OR ".join(f"LOWER({col}) LIKE '%{v}%'" for v in variantes)
    return f"({likes})"


def _filtro_rango_volumen_mayor(col: str, min_cc: int) -> str:
    """Genera filtro para volumen mayor a X cc buscando en descripcion."""
    # Mapeo de cc → etiquetas en descripcion
    etiquetas = []
    rangos = [
        (473,  []),           # personal — excluir si min > 473
        (940,  ["940", "940cc", "940 cc"]),
        (960,  ["960", "960cc"]),
        (1000, ["1000", "1l", "1 l", "1000ml", "litro", "x1l", "x 1l", "1lt"]),
        (1500, ["1.5l", "1,5l", "1.5 l", "1500ml"]),
        (2000, ["2l", "2 l", "2000ml", "x2l", "2lt", "2 lt"]),
        (3000, ["3l", "3 l", "3000ml"]),
    ]
    for cc, labels in rangos:
        if cc >= min_cc and labels:
            etiquetas.extend(labels)

    if not etiquetas:
        return f"LOWER({col}) LIKE '%{min_cc}%'"

    likes = " OR ".join(f"LOWER({col}) LIKE '%{e}%'" for e in etiquetas)
    return f"({likes})"


def _filtro_rango_volumen_menor(col: str, max_cc: int) -> str:
    """Genera filtro para volumen menor a X cc buscando en descripcion."""
    etiquetas = []
    rangos = [
        (220,  ["220cc", "x220"]),
        (250,  ["250cc", "x250", "250ml"]),
        (330,  ["330cc", "330ml", "x330"]),
        (354,  ["354cc", "354ml", "x354"]),
        (355,  ["355cc", "355ml", "x355"]),
        (473,  ["473cc", "473ml", "x473"]),
    ]
    for cc, labels in rangos:
        if cc < max_cc:
            etiquetas.extend(labels)

    if not etiquetas:
        return f"LOWER({col}) LIKE '%{max_cc}%'"

    likes = " OR ".join(f"LOWER({col}) LIKE '%{e}%'" for e in etiquetas)
    return f"({likes})"