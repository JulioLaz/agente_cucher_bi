"""
config.py — Configuración central del agente Cucher
Todas las constantes, paths, tokens y parámetros en un solo lugar.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── MOTHERDUCK ───────────────────────────────────────────────
TOKEN_MD   = os.getenv("TOKEN_MATHERDUCK")
T_TICKETS  = "my_db.tickets_all"
T_PROV     = "my_db.proveedores"
T_ALERT    = "my_db.result_final_alert_all"
T_PRECIOS  = "my_db.ultimos_precios"

# ─── NVIDIA NIM ───────────────────────────────────────────────
NVIDIA_API_KEY = os.getenv("key_nvidia")
NVIDIA_URL     = "https://integrate.api.nvidia.com/v1/chat/completions"

# Modelos en orden de prioridad (fallback automático)
MODELOS = [
    "deepseek-ai/deepseek-v4-flash",
    "mistralai/mistral-small-4-119b-2603",
    "z-ai/glm-5.1",
    "meta/llama-3.1-8b-instruct",
]

# ─── TELEGRAM ─────────────────────────────────────────────────
TG_TOKEN   = os.getenv("token_bot_telegram")
TG_CHAT_ID = "8107106288"

# ─── PATHS LOCALES ────────────────────────────────────────────
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
