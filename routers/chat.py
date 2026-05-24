from fastapi import APIRouter, HTTPException
import httpx
import os
from services.ontology_service import obtener_contexto_desde_fuseki

router = APIRouter()

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")


@router.post("/chat")
async def chat_with_n8n(payload: dict):
    user_message = payload.get("message")
    user_id = payload.get("user_id")

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

    # Construir payload enriquecido para n8n
    async with httpx.AsyncClient() as client:
        try:
            n8n_payload = {
                "chatInput": user_message,
                "context": contexto["resumen"],
                "context_structured": {
                    "intencion": contexto.get("intencion", "consulta_general"),
                    "datos": contexto.get("datos", {}),
                    "total_resultados": contexto.get("total_resultados", 0),
                    "es_fallback": contexto.get("fallback", False),
                },
                "user_id": user_id,
            }

            response = await client.post(
                N8N_WEBHOOK_URL,
                json=n8n_payload,
                timeout=60.0,
            )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Error en n8n")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")
