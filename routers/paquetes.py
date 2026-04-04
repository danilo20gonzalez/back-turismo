# routers/paquetes.py
from fastapi import APIRouter
from services.paquete_service import PaqueteService

router = APIRouter(prefix="/paquetes", tags=["Paquetes"])

@router.get("/")
def listar_paquetes(perfil: str = "", max_precio: int = 1000000):
    return PaqueteService.buscar_paquetes(perfil, max_precio)