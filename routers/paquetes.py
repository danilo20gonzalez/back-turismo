# routers/paquetes.py
from fastapi import APIRouter, HTTPException
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


@router.get("/{paquete_id}")
def obtener_detalle_paquete(paquete_id: str):
    detalle = PaqueteService.obtener_detalle(paquete_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    return detalle
