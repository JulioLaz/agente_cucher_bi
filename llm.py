# """
# llm.py — Llamadas a NVIDIA NIM con fallback automático entre modelos.
# """
# import requests
# from config import get_nvidia_key, NVIDIA_URL, MODELOS, TIMEOUT_NVIDIA


# def llamar_nvidia(messages: list,
#                   max_tokens: int = 1024,
#                   temperatura: float = 0.3) -> str:
#     """Llama a NVIDIA NIM con fallback automático."""
#     api_key = get_nvidia_key()
#     if not api_key:
#         return "❌ key_nvidia no encontrada en secrets"

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type":  "application/json"
#     }

#     for modelo in MODELOS:
#         try:
#             resp = requests.post(
#                 NVIDIA_URL,
#                 headers=headers,
#                 json={
#                     "model":       modelo,
#                     "messages":    messages,
#                     "temperature": temperatura,
#                     "max_tokens":  max_tokens,
#                 },
#                 timeout=TIMEOUT_NVIDIA
#             )
#             if resp.status_code == 200:
#                 return resp.json()["choices"][0]["message"]["content"]
#             print(f"   [llm] {modelo} → {resp.status_code}")
#         except requests.exceptions.Timeout:
#             print(f"   [llm] Timeout: {modelo}")
#         except Exception as e:
#             print(f"   [llm] Error {modelo}: {e}")

#     return "❌ Ningún modelo NVIDIA respondió. Intentá de nuevo."

"""
llm.py — Llamadas a LLM con fallback automático entre modelos.
Soporta múltiples proveedores (NVIDIA NIM, Groq) según PROVEEDOR_IA en config.py.
v1.1 — se agrega soporte Groq junto a NVIDIA NIM.
"""
import requests
from config import (
    get_nvidia_key, NVIDIA_URL, MODELOS, TIMEOUT_NVIDIA,
    get_groq_key, GROQ_URL, MODELOS_GROQ, TIMEOUT_GROQ,
    PROVEEDOR_IA,
)

_PROVEEDORES = {
    "nvidia": dict(url=NVIDIA_URL, modelos=MODELOS, key_fn=get_nvidia_key, timeout=TIMEOUT_NVIDIA),
    "groq":   dict(url=GROQ_URL,   modelos=MODELOS_GROQ, key_fn=get_groq_key, timeout=TIMEOUT_GROQ),
}


def llamar_nvidia(messages: list,
                  max_tokens: int = 1024,
                  temperatura: float = 0.3) -> str:
    """Llama al proveedor activo (PROVEEDOR_IA) con fallback automático entre sus modelos."""
    cfg = _PROVEEDORES.get(PROVEEDOR_IA, _PROVEEDORES["nvidia"])
    api_key = cfg["key_fn"]()
    if not api_key:
        return f"❌ key de {PROVEEDOR_IA} no encontrada en secrets"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json"
    }

    for modelo in cfg["modelos"]:
        try:
            resp = requests.post(
                cfg["url"],
                headers=headers,
                json={
                    "model":       modelo,
                    "messages":    messages,
                    "temperature": temperatura,
                    "max_tokens":  max_tokens,
                },
                timeout=cfg["timeout"]
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            print(f"   [llm:{PROVEEDOR_IA}] {modelo} → {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"   [llm:{PROVEEDOR_IA}] Timeout: {modelo}")
        except Exception as e:
            print(f"   [llm:{PROVEEDOR_IA}] Error {modelo}: {e}")

    return f"❌ Ningún modelo {PROVEEDOR_IA} respondió. Intentá de nuevo."