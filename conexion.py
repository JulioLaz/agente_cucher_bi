"""
conexion.py — Conexión a MotherDuck SIN imports de streamlit.
"""
import duckdb
import os

_con = None


def get_con() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is not None:
        try:
            _con.execute("SELECT 1")
            return _con
        except Exception:
            _con = None

    token = os.environ.get("TOKEN_MATHERDUCK", "")
    if not token:
        raise ValueError("TOKEN_MATHERDUCK no encontrado")

    _con = duckdb.connect(f"md:?motherduck_token={token}")
    return _con