"""
conexion.py — Conexión a MotherDuck con reconexión automática.
"""
import duckdb
import streamlit as st
from config import TOKEN_MD


@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    """Conexión a MotherDuck cacheada por sesión de Streamlit."""
    if not TOKEN_MD:
        raise ValueError("❌ TOKEN_MATHERDUCK no encontrado en .env")
    return duckdb.connect(f"md:?motherduck_token={TOKEN_MD}")


def get_con_local() -> duckdb.DuckDBPyConnection:
    """Conexión local DuckDB (sin MotherDuck) — para tests."""
    return duckdb.connect()
