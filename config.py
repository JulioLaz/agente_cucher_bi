"""
config.py — Configuración central del agente Cucher
Lee secrets desde st.secrets (Streamlit Cloud) o .env (local).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _secret(key: str, default: str = None) -> str:
    """Lee desde st.secrets primero, luego os.getenv."""
    try:
        import streamlit as st
        # st.secrets lanza KeyError si no existe — usar try/except
        return str(st.secrets[key])
    except (KeyError, FileNotFoundError):
        pass
    except Exception:
        pass
    return os.getenv(key, default)


# ─── TABLAS MOTHERDUCK ────────────────────────────────────────
T_TICKETS  = "my_db.tickets_all"
T_PROV     = "my_db.proveedores"
T_ALERT    = "my_db.result_final_alert_all"
T_PRECIOS  = "my_db.ultimos_precios"

# ─── NVIDIA NIM ───────────────────────────────────────────────
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELOS = [
    "deepseek-ai/deepseek-v4-flash",
    "mistralai/mistral-small-4-119b-2603",
    "z-ai/glm-5.1",
    "meta/llama-3.1-8b-instruct",
]

# ─── TOKENS (leídos en runtime, no en import) ─────────────────
# Usar estas funciones en vez de las constantes directas
def get_token_md()       -> str: return _secret("TOKEN_MATHERDUCK", "")
def get_nvidia_key()     -> str: return _secret("key_nvidia", "")
def get_tg_token()       -> str: return _secret("token_bot_telegram", "")

# Compatibilidad con código existente que usa las constantes
TOKEN_MD       = None  # se resuelve en runtime via get_token_md()
NVIDIA_API_KEY = None  # se resuelve en runtime via get_nvidia_key()
TG_TOKEN       = None  # se resuelve en runtime via get_tg_token()
TG_CHAT_ID     = "8107106288"
HISTORIAL_PATH = "chat_historial_cucher.json"

# ─── SUCURSALES ───────────────────────────────────────────────
SUC_VENTAS    = ["hiper", "corrientes", "sabin", "formosa"]
SUC_DEPOSITOS = ["tirol", "central"]
SUC_ESPECIAL  = ["express"]
SUC_TODAS     = SUC_VENTAS + SUC_DEPOSITOS + SUC_ESPECIAL

COLORES_SUC = {
    "corrientes": "#f59e0b",
    "sabin":      "#10b981",
    "hiper":      "#8b5cf6",
    "formosa":    "#ef4444",
    "express":    "#06b6d4",
    "tirol":      "#6b7280",
    "central":    "#374151",
}

# ─── LÍMITES ─────────────────────────────────────────────────
MAX_TOKENS_SQL      = 800
MAX_TOKENS_ANALISIS = 1200
MAX_TOKENS_INTERP   = 400
TIMEOUT_NVIDIA      = 90
MAX_FILAS_RESULTADO = 50