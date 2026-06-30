"""
config.py — SIN imports de streamlit en nivel de módulo.
Los secrets se inyectan via variables de entorno desde app.py.
"""
import os
from dotenv import load_dotenv
load_dotenv()

T_TICKETS  = "my_db.tickets_all"
T_PROV     = "my_db.proveedores"
T_ALERT    = "my_db.result_final_alert_all"
T_PRECIOS  = "my_db.ultimos_precios"

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELOS = [
    "mistralai/mistral-small-4-119b-2603",   # más rápido y estable
    "z-ai/glm-5.1",
    "deepseek-ai/deepseek-v4-flash",
    "meta/llama-3.1-8b-instruct",
]

TG_CHAT_ID     = "8107106288"
HISTORIAL_PATH = "chat_historial_cucher.json"
SUC_VENTAS     = ["hiper", "corrientes", "sabin", "formosa"]
SUC_DEPOSITOS  = ["tirol", "central"]
SUC_ESPECIAL   = ["express"]
SUC_TODAS      = SUC_VENTAS + SUC_DEPOSITOS + SUC_ESPECIAL
COLORES_SUC    = {
    "corrientes": "#f59e0b", "sabin": "#10b981", "hiper": "#8b5cf6",
    "formosa": "#ef4444", "express": "#06b6d4",
    "tirol": "#6b7280", "central": "#374151",
}
MAX_TOKENS_SQL      = 800
MAX_TOKENS_ANALISIS = 1600
MAX_TOKENS_INTERP   = 400
TIMEOUT_NVIDIA      = 90
MAX_FILAS_RESULTADO = 50

# Getters simples — solo leen os.environ (seteado por app.py desde st.secrets)
def get_token_md()   -> str: return os.environ.get("TOKEN_MATHERDUCK", "")
def get_nvidia_key() -> str: return os.environ.get("key_nvidia", "")
def get_tg_token()   -> str: return os.environ.get("token_bot_telegram", "")
def get_usuarios() -> dict:
    """
    Lee usuarios SOLO desde st.secrets o USUARIOS_JSON en env.
    Sin fallback hardcodeado — si no hay secrets, retorna dict vacío
    y el login bloqueará el acceso.
    """
    import json
    # Primero: USUARIOS_JSON inyectado por app.py desde st.secrets
    raw = os.environ.get("USUARIOS_JSON", "")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    # Segundo: variables individuales inyectadas por app.py
    usuarios = {}
    for u in ["cristina", "horacio", "julio"]:
        pwd = os.environ.get(f"USR_{u.upper()}", "")
        if pwd:
            usuarios[u] = pwd
    return usuarios  # vacío si no hay secrets → nadie puede entrar
