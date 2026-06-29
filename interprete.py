"""
interprete.py — Metacognición del agente.
Analiza la pregunta, determina si puede responderla y cómo.
"""
import json
from datetime import date
from llm import llamar_nvidia
from catalogo import CAPACIDADES_SI, CAPACIDADES_NO
from config import MAX_TOKENS_INTERP


SYSTEM_INTERPRETE = """Sos el agente de datos de Cucher Mercados (supermercados Argentina).
Tu tarea: analizar la pregunta del usuario y evaluar si podés responderla con los datos disponibles.

PODÉS RESPONDER (datos en MotherDuck):
{cap_si}

NO PODÉS RESPONDER:
{cap_no}

Devolvé SOLO este JSON sin markdown ni explicación:
{{
  "puede_responder": true/false,
  "reformulacion": "Lo que entendiste en 1-2 oraciones claras y concretas",
  "tablas_necesarias": ["tabla1"],
  "filtros_detectados": {{"categoria": "...", "marca": "...", "periodo": "...", "sucursal": "..."}},
  "limitacion": "Si no puede: explicación breve de por qué",
  "datos_faltantes": "Si no puede: qué necesitaría para poder responder"
}}"""


def interpretar(pregunta: str) -> dict:
    """
    Analiza la pregunta y devuelve dict con:
    - puede_responder: bool
    - reformulacion: str
    - tablas_necesarias: list
    - filtros_detectados: dict
    - limitacion: str
    - datos_faltantes: str
    """
    cap_si  = "\n".join(f"✅ {c}" for c in CAPACIDADES_SI)
    cap_no  = "\n".join(f"❌ {c}" for c in CAPACIDADES_NO)

    system = SYSTEM_INTERPRETE.format(cap_si=cap_si, cap_no=cap_no)

    msgs = [
        {"role": "system", "content": system},
        {"role": "user",   "content": f"Pregunta: {pregunta}"}
    ]

    raw = llamar_nvidia(msgs, max_tokens=MAX_TOKENS_INTERP, temperatura=0.1)

    try:
        clean = raw.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except Exception:
        # Fallback seguro si el LLM no devuelve JSON válido
        return {
            "puede_responder":   True,
            "reformulacion":     pregunta,
            "tablas_necesarias": [],
            "filtros_detectados":{},
            "limitacion":        "",
            "datos_faltantes":   ""
        }
