"""
conexion.py — Conexión a MotherDuck.
Sin st.cache_resource para evitar conflictos con imports en Streamlit Cloud.
"""
import duckdb
import os

_con = None  # singleton de conexión


def get_con() -> duckdb.DuckDBPyConnection:
    """Conexión a MotherDuck — singleton simple sin Streamlit cache."""
    global _con
    if _con is not None:
        try:
            _con.execute("SELECT 1")  # verificar que sigue viva
            return _con
        except Exception:
            _con = None

    # Leer token — primero st.secrets, luego .env
    token = None
    try:
        import streamlit as st
        token = st.secrets.get("TOKEN_MATHERDUCK") or st.secrets["TOKEN_MATHERDUCK"]
    except Exception:
        pass
    if not token:
        token = os.getenv("TOKEN_MATHERDUCK", "")
    if not token:
        raise ValueError("❌ TOKEN_MATHERDUCK no encontrado en secrets")

    _con = duckdb.connect(f"md:?motherduck_token={token}")
    return _con