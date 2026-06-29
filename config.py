"""
config.py — Configuración central del agente Cucher.
SIN imports de streamlit en nivel de módulo.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── TABLAS ───────────────────────────────────────────────────
T_TICKETS  = "my_db.tickets_all"
T_PROV     = "my_db.proveedores"
T_ALERT    = "my_db.result_final_alert_all"
T_PRECIOS  = "my_db.ultimos_precios"

# ─── NVIDIA ───────────────────────────────────────────────────
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELOS = [
    "deepseek-ai/deepseek-v4-flash",
    "mistralai/mistral-small-4-119b-2603",
    "z-ai/glm-5.1",
    "meta/llama-3.1-8b-instruct",
]

# ─── CONSTANTES ───────────────────────────────────────────────
TG_CHAT_ID     = "8107106288"
HISTORIAL_PATH = "chat_historial_cucher.json"
SUC_VENTAS     = ["hiper", "corrientes", "sabin", "formosa"]
SUC_DEPOSITOS  = ["tirol", "central"]
SUC_ESPECIAL   = ["express"]
SUC_TODAS      = SUC_VENTAS + SUC_DEPOSITOS + SUC_ESPECIAL
COLORES_SUC = {
    "corrientes": "#f59e0b", "sabin": "#10b981", "hiper": "#8b5cf6",
    "formosa": "#ef4444", "express": "#06b6d4",
    "tirol": "#6b7280", "central": "#374151",
}
MAX_TOKENS_SQL      = 800
MAX_TOKENS_ANALISIS = 1200
MAX_TOKENS_INTERP   = 400
TIMEOUT_NVIDIA      = 90
MAX_FILAS_RESULTADO = 50


def _get(key: str, default: str = "") -> str:
    """Lee secret en runtime — sin importar streamlit a nivel de módulo."""
    try:
        import streamlit as st
        v = st.secrets.get(key, None)
        if v is not None:
            return str(v)
    except Exception:
        pass
    return os.getenv(key, default)


def get_token_md()   -> str: return _get("TOKEN_MATHERDUCK")
def get_nvidia_key() -> str: return _get("key_nvidia")
def get_tg_token()   -> str: return _get("token_bot_telegram")


def get_usuarios() -> dict:
    try:
        import streamlit as st
        u = st.secrets.get("usuarios", None)
        if u:
            return dict(u)
    except Exception:
        pass
    return {
        "cristina": os.getenv("USER_CRISTINA", "vamos_argentina"),
        "horacio":  os.getenv("USER_HORACIO",  "vamos_argentina"),
        "julio":    os.getenv("USER_JULIO",    "vamos_argentina"),
    }