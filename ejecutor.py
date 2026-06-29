"""
ejecutor.py — Ejecución SQL segura sobre MotherDuck.
Valida que sea SELECT, ejecuta y devuelve DataFrame + error.
"""
import re
import pandas as pd
from conexion import get_con
from config import MAX_FILAS_RESULTADO


# Tablas permitidas (whitelist de seguridad)
TABLAS_PERMITIDAS = {
    "my_db.tickets_all",
    "my_db.proveedores",
    "my_db.result_final_alert_all",
    "my_db.ultimos_precios",
}

# Palabras prohibidas en SQL
PALABRAS_PROHIBIDAS = [
    "drop", "delete", "truncate", "update", "insert",
    "alter", "create", "grant", "revoke", "exec",
]


def validar_sql(sql: str) -> tuple[bool, str]:
    """
    Valida que el SQL sea seguro para ejecutar.
    Retorna (es_valido, mensaje_error).
    """
    if not sql or not sql.strip():
        return False, "SQL vacío"

    sql_lower = sql.lower().strip()

    # Debe empezar con SELECT o WITH
    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        return False, "Solo se permiten consultas SELECT o WITH"

    # No puede contener palabras prohibidas
    for palabra in PALABRAS_PROHIBIDAS:
        if re.search(rf'\b{palabra}\b', sql_lower):
            return False, f"Palabra prohibida detectada: {palabra}"

    return True, ""


def limpiar_sql(raw: str) -> str:
    """Limpia el SQL generado por el LLM — quita markdown, comillas, etc."""
    # Quitar bloques de código markdown
    sql = re.sub(r'```(?:sql|python|duckdb)?\s*', '', raw, flags=re.IGNORECASE)
    sql = sql.replace('```', '').strip()

    # Quitar prefijos comunes del LLM
    for prefijo in ['sql:', 'query:', 'consulta:']: 
        if sql.lower().startswith(prefijo):
            sql = sql[len(prefijo):].strip()

    # Encontrar el inicio real del SQL
    match = re.search(r'(WITH\s+|SELECT\s+)', sql, re.IGNORECASE)
    if match:
        sql = sql[match.start():]

    # Quitar todo lo que venga después de un punto y coma
    # (el LLM a veces agrega explicaciones después del SQL)
    partes = sql.split(';')
    sql = partes[0].strip() + ';' if partes else sql

    return sql.strip()


def ejecutar_sql(sql: str) -> tuple[pd.DataFrame, str]:
    """
    Ejecuta SQL en MotherDuck de forma segura.
    Retorna (DataFrame, mensaje_error).
    """
    sql = limpiar_sql(sql)

    es_valido, msg_error = validar_sql(sql)
    if not es_valido:
        return pd.DataFrame(), f"SQL inválido: {msg_error}"

    try:
        con = get_con()
        df  = con.execute(sql).df()

        # Limitar filas si el resultado es muy grande
        if len(df) > MAX_FILAS_RESULTADO:
            df = df.head(MAX_FILAS_RESULTADO)

        return df, ""

    except Exception as e:
        error_msg = str(e)
        # Simplificar mensaje de error para el LLM
        if "Binder Error" in error_msg:
            # Extraer columna problemática
            match = re.search(r'"([^"]+)"', error_msg)
            col   = match.group(1) if match else "desconocida"
            return pd.DataFrame(), f"Columna no encontrada: '{col}'. {error_msg[:200]}"
        elif "Parser Error" in error_msg:
            return pd.DataFrame(), f"Error de sintaxis SQL: {error_msg[:200]}"
        elif "Catalog Error" in error_msg:
            return pd.DataFrame(), f"Tabla no encontrada: {error_msg[:200]}"
        else:
            return pd.DataFrame(), f"Error SQL: {error_msg[:300]}"
