from fastapi import APIRouter, HTTPException

from services.groq_service import GroqServiceError, generar_respuesta_con_groq
from services.ontology_service import obtener_contexto_desde_fuseki

router = APIRouter()


@router.post("/chat")
async def chat_with_amaturis(payload: dict):
    user_message = payload.get("message")

    if not user_message:
        raise HTTPException(status_code=400, detail="El mensaje es obligatorio")

    # Consultar ontología (Fuseki) con el nuevo sistema inteligente
    try:
        contexto = await obtener_contexto_desde_fuseki(user_message)
    except Exception as e:
        contexto = {
            "type": "structured",
            "intencion": "consulta_general",
            "consulta_original": user_message,
            "resumen": "Actualmente no contamos con registros específicos para esa solicitud en nuestra guía oficial, pero la Amazonia colombiana tiene mucho por ofrecer.",
            "datos": {},
            "total_resultados": 0,
            "fallback": True,
        }

    # Groq solo redacta con base en los datos devueltos por la ontología.
    # Si no hay API key, se alcanza un límite o falla el proveedor, el sistema
    # conserva una respuesta determinista y no inventa información turística.
    try:
        respuesta = await generar_respuesta_con_groq(user_message, contexto)
    except GroqServiceError as exc:
        print(f"Aviso del asistente Groq: {exc}")
        respuesta = None

    return {
        "output": respuesta or contexto["resumen"],
        "source": "groq" if respuesta else "ontology_fallback",
        "intencion": contexto.get("intencion", "consulta_general"),
        "total_resultados": contexto.get("total_resultados", 0),
    }
