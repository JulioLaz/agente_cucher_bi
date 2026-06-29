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
