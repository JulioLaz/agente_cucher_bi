"""
notificaciones.py — Telegram e historial JSON local.
"""
import json
import os
import requests
from datetime import datetime
from config import TG_TOKEN, TG_CHAT_ID, HISTORIAL_PATH


def enviar_telegram(pregunta: str, respuesta: str,
                    modo: str = None, tiempo: float = None,
                    usuario: str = None):
    """Envía par pregunta/respuesta al bot de Telegram."""
    if not TG_TOKEN:
        return
    t_txt      = f"⏱ {tiempo:.1f}s" if tiempo else ""
    modo_txt   = f"🔧 `{modo}`\n" if modo else ""
    user_txt   = f"👤 *{usuario.capitalize()}*\n" if usuario else ""
    resp_corta = respuesta[:800] + "..." if len(respuesta) > 800 else respuesta

    texto = (
        f"🛒 *Cucher Agente BI* {t_txt}\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        f"{user_txt}\n"
        f"❓ *Pregunta:*\n{pregunta}\n\n"
        f"{modo_txt}"
        f"💬 *Respuesta:*\n{resp_corta}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": texto, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"   [telegram] Error: {e}")


def notificar_capacidad_faltante(pregunta: str, interpretacion: dict):
    """Notifica al bot cuando el agente no puede responder."""
    if not TG_TOKEN:
        return
    texto = (
        f"🤖 *CAPACIDAD FALTANTE — Cucher Agente*\n"
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"❓ *Pregunta:*\n{pregunta}\n\n"
        f"🔍 *Interpretación:*\n{interpretacion.get('reformulacion','')}\n\n"
        f"⛔ *Limitación:*\n{interpretacion.get('limitacion','')}\n\n"
        f"📋 *Datos necesarios:*\n{interpretacion.get('datos_faltantes','')}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": texto, "parse_mode": "Markdown"},
            timeout=10
        )
        print("   [telegram] Capacidad faltante notificada")
    except Exception as e:
        print(f"   [telegram] Error: {e}")


def guardar_historial(pregunta: str, respuesta: str,
                      modo: str = None, tiempo: float = None):
    """Agrega el par pregunta/respuesta al historial JSON local."""
    registro = {
        "timestamp": datetime.now().isoformat(),
        "pregunta":  pregunta,
        "respuesta": respuesta,
        "modo":      modo or "ninguno",
        "tiempo_seg": round(tiempo, 1) if tiempo else None
    }
    historial = []
    if os.path.exists(HISTORIAL_PATH):
        try:
            with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                historial = json.load(f)
        except Exception:
            pass
    historial.append(registro)
    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)