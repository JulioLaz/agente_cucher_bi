"""
llm.py — Llamadas a NVIDIA NIM con fallback automático entre modelos.
"""
import requests
from config import get_nvidia_key, NVIDIA_URL, MODELOS, TIMEOUT_NVIDIA


def llamar_nvidia(messages: list,
                  max_tokens: int = 1024,
                  temperatura: float = 0.3) -> str:
    """Llama a NVIDIA NIM con fallback automático."""
    api_key = get_nvidia_key()
    if not api_key:
        return "❌ key_nvidia no encontrada en secrets"

    headers = {
        "Authorization": f"Bearer {api_key}",
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
