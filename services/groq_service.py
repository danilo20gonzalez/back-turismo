"""Cliente mínimo para generar respuestas del asistente con Groq.

Fuseki sigue siendo la fuente de verdad. Este servicio solo redacta una
respuesta a partir del contexto estructurado que ya produjo la ontología.
"""

import json
import os

import httpx


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_TIMEOUT = float(os.getenv("GROQ_TIMEOUT", "45"))
MAX_CONTEXT_CHARS = int(os.getenv("GROQ_CONTEXT_MAX_CHARS", "14000"))

SYSTEM_PROMPT = """Eres AmaTuris, el asistente turístico oficial del Caquetá.

Responde en español, con tono amable, claro y breve. Solo puedes afirmar datos
que aparezcan en el contexto oficial recibido desde la ontología. No inventes
precios, fechas, disponibilidad, ubicaciones, servicios ni características.
Si el contexto no contiene la respuesta, dilo claramente y sugiere que el
usuario pruebe otra búsqueda. No menciones Fuseki, SPARQL, Groq, n8n ni el
funcionamiento interno del sistema. No escribas consultas ni código.
"""


class GroqServiceError(RuntimeError):
    """Error controlado al generar una respuesta con Groq."""


def _serializar_contexto(contexto: dict) -> str:
    datos = {
        "consulta": contexto.get("consulta_original", ""),
        "intencion": contexto.get("intencion", "consulta_general"),
        "total_resultados": contexto.get("total_resultados", 0),
        "resumen": contexto.get("resumen", ""),
        "resultados": contexto.get("datos", {}),
    }
    contenido = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    return contenido[:MAX_CONTEXT_CHARS]


async def generar_respuesta_con_groq(mensaje_usuario: str, contexto: dict) -> str | None:
    """Genera una respuesta fundamentada en el resultado de la ontología.

    Devuelve ``None`` cuando Groq no está configurado para permitir que el
    router use el resumen determinista como fallback.
    """
    if not GROQ_API_KEY:
        return None

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Pregunta del usuario:\n{mensaje_usuario}\n\n"
                    f"Contexto oficial:\n{_serializar_contexto(contexto)}"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 512,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=GROQ_TIMEOUT) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 429:
            raise GroqServiceError("Se alcanzó temporalmente el límite gratuito de Groq") from exc
        raise GroqServiceError(f"Groq respondió con HTTP {status}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise GroqServiceError("No fue posible comunicarse con Groq") from exc

    try:
        contenido = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GroqServiceError("Groq devolvió una respuesta inesperada") from exc

    if not isinstance(contenido, str) or not contenido.strip():
        raise GroqServiceError("Groq devolvió una respuesta vacía")

    return contenido.strip()
