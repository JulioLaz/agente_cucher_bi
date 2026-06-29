"""
conexion.py — Conexión a MotherDuck con reconexión automática.
"""
import duckdb
import streamlit as st
from config import get_token_md


@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    """Conexión a MotherDuck cacheada por sesión de Streamlit."""
    token = get_token_md()
    if not token:
        raise ValueError("❌ TOKEN_MATHERDUCK no encontrado en secrets")
    return duckdb.connect(f"md:?motherduck_token={token}")
