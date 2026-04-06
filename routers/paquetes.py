# routers/paquetes.py
from fastapi import APIRouter
from services.paquete_service import PaqueteService

router = APIRouter(prefix="/paquetes", tags=["Paquetes"])

@router.get("/")
def listar_paquetes(
    busqueda: str = "",
    max_precio: int = 1000000,
    limit: int = 50,
    offset: int = 0,
):
    return PaqueteService.buscar_paquetes(busqueda, max_precio, limit, offset)
