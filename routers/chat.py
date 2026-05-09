from fastapi import APIRouter, HTTPException
import httpx
import os
# Importamos la función que consulta tu ontología en Fuseki
from services.ontology_service import obtener_contexto_desde_fuseki

router = APIRouter()

# URL de n8n desde las variables de entorno
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

@router.post("/chat")
async def chat_with_n8n(payload: dict):
    # Extraemos los datos del frontend
    user_message = payload.get("message")
    user_id = payload.get("user_id")

    if not user_message:
        raise HTTPException(status_code=400, detail="El mensaje es obligatorio")

    # --- INTEGRACIÓN CON LA ONTOLOGÍA (CORREGIDO) ---
    # Llamamos a Fuseki usando el mensaje del usuario para obtener datos técnicos
    try:
        datos_contexto = await obtener_contexto_desde_fuseki(user_message)
        # Asegurar que sea un string limpio
        if not isinstance(datos_contexto, str):
            datos_contexto = str(datos_contexto)
        datos_contexto = datos_contexto.strip()
    except Exception as e:
        # Si falla Fuseki, enviamos un contexto vacío o genérico para no romper el chat
        datos_contexto = "Actualmente no contamos con registros específicos para esa solicitud en nuestra guía oficial, pero la Amazonia colombiana tiene mucho por ofrecer."

    # Configuración de la petición hacia n8n
    async with httpx.AsyncClient() as client:
        try:
            n8n_payload = {
                "chatInput": user_message,  # Lo recibe el AI Agent
                "context": datos_contexto,   # Lo recibe el System Message
                "user_id": user_id           # Lo recibe el Postgres Chat Memory
            }

            response = await client.post(
                N8N_WEBHOOK_URL,
                json=n8n_payload,
                timeout=60.0
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Error en n8n")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")