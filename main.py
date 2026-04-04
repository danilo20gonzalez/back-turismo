# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import paquetes  # Importamos el router que crearemos
from routers import usuarios
from routers import reservas

app = FastAPI(
    title="AmaTuris API",
    description="API para la gestión del conocimiento turístico del Caquetá",
    version="1.0.0"
)

# --- Configuración de CORS ---
# Esto es vital para que tu frontend en React pueda hacer peticiones al backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción cambia esto a la URL de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Inclusión de Routers ---
# Aquí registramos las rutas de paquetes. Luego registraremos reservas, usuarios, etc.
app.include_router(paquetes.router)
app.include_router(usuarios.router)
app.include_router(reservas.router)

@app.get("/")
async def root():
    return {
        "proyecto": "AmaTuris",
        "estado": "Online",
        "documentacion": "/docs"
    }

if __name__ == "__main__":
    # Ejecuta la aplicación usando Uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True  # El reload permite que el server se reinicie solo al guardar cambios
    )