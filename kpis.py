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
def cargar_kpis_header() -> dict:
    """KPIs del mes actual vs mes anterior para el header."""
    mes_actual = date.today().strftime("%Y-%m")
    mes_ant    = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    q = f"""
        WITH actual AS (
            SELECT
                ROUND(SUM(precio_total)/1e6, 2)                                          AS venta_m,
                ROUND(SUM(precio_total-costo_total)/1e6, 2)                              AS util_m,
                ROUND((SUM(precio_total)-SUM(costo_total))/NULLIF(SUM(precio_total),0)*100,1) AS margen_pct,
                COUNT(DISTINCT fecha_comprobante)                                         AS dias
            FROM {T_TICKETS}
            WHERE strftime(CAST(fecha_comprobante AS DATE), '%Y-%m') = '{mes_actual}'
              AND LOWER(sucursal) IN ('hiper','corrientes','sabin','formosa','express')
        ),
        anterior AS (
            SELECT
                ROUND(SUM(precio_total)/1e6, 2)             AS venta_m_ant,
                ROUND(SUM(precio_total-costo_total)/1e6, 2) AS util_m_ant
            FROM {T_TICKETS}
            WHERE strftime(CAST(fecha_comprobante AS DATE), '%Y-%m') = '{mes_ant}'
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

@st.cache_data(ttl=300)
def detalle_sin_stock(top_n: int = 50) -> pd.DataFrame:
    """Artículos sin stock con alerta de reabastecimiento activa."""
    q = f"""
        SELECT descripcion, familia, subfamilia, TRIM(proveedor) AS proveedor,
               dias_cobertura, STK_TOTAL AS stock_total,
               stk_hiper, stk_corrientes, stk_sabin, stk_formosa,
               cant_total AS ventas_90d, PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE alerta_reabastecer = 'Sí' AND dias_cobertura = 0
        ORDER BY cant_total DESC
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
               dias_cobertura, STK_TOTAL AS stock_total,
               stk_hiper, stk_corrientes, stk_sabin, stk_formosa,
               cant_total AS ventas_90d, PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE alerta_reabastecer = 'Sí' AND dias_cobertura BETWEEN 1 AND 3
        ORDER BY cant_total DESC
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
               dias_cobertura, STK_TOTAL AS stock_total,
               stk_hiper, stk_corrientes, stk_sabin, stk_formosa,
               cant_total AS ventas_90d, PRESUPUESTO AS presupuesto_compra
        FROM {T_ALERT}
        WHERE alerta_reabastecer = 'Sí' AND dias_cobertura BETWEEN 4 AND 7
        ORDER BY cant_total DESC
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
        SELECT descripcion, familia, subfamilia,
               exceso_STK AS exceso_stock,
               stk_hiper, stk_corrientes, stk_sabin, stk_formosa,
               dias_cobertura
        FROM {T_ALERT}
        WHERE exceso_STK > 0
        ORDER BY exceso_STK DESC
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
               valor_perdido_TOTAL AS valor_perdido,
               unidades_perdidas_TOTAL AS unidades_perdidas,
               dias_cobertura, STK_TOTAL AS stock_total
        FROM {T_ALERT}
        WHERE valor_perdido_TOTAL > 0
        ORDER BY valor_perdido_TOTAL DESC
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
               PRESUPUESTO AS presupuesto_compra,
               total_abastecer AS unidades_a_pedir,
               dias_cobertura, STK_TOTAL AS stock_total
        FROM {T_ALERT}
        WHERE PRESUPUESTO > 0
        ORDER BY PRESUPUESTO DESC
        LIMIT {top_n}
    """
    try:
        return get_con().execute(q).df()
    except Exception:
        return pd.DataFrame()


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