"""
llm.py — Llamadas a NVIDIA NIM con fallback automático entre modelos.
"""
import requests
from config import NVIDIA_API_KEY, NVIDIA_URL, MODELOS, TIMEOUT_NVIDIA


def llamar_nvidia(messages: list[dict],
                  max_tokens: int = 1024,
                  temperatura: float = 0.3) -> str:
    """
    Llama a NVIDIA NIM con fallback automático.
    Retorna el texto de la respuesta o mensaje de error.
    """
    if not NVIDIA_API_KEY:
        return "❌ key_nvidia no encontrada en .env"

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type":  "application/json"
    }

    for modelo in MODELOS:
        try:
            resp = requests.post(
                NVIDIA_URL,
                headers=headers,
                json={
                    "model":       modelo,
                    "messages":    messages,
                    "temperature": temperatura,
                    "max_tokens":  max_tokens,
                },
                timeout=TIMEOUT_NVIDIA
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            print(f"   [llm] {modelo} → {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"   [llm] Timeout: {modelo}")
        except Exception as e:
            print(f"   [llm] Error {modelo}: {e}")

    return "❌ Ningún modelo NVIDIA respondió. Intentá de nuevo."
