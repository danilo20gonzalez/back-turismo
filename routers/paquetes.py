# routers/paquetes.py
from fastapi import APIRouter, HTTPException
from services.paquete_service import PaqueteService

router = APIRouter(prefix="/paquetes", tags=["Paquetes"])

STATIC_FILE_SUFFIXES = (
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".map",
    ".png",
    ".svg",
    ".webp",
)


def _reject_asset_like_id(value: str):
    if value.lower().endswith(STATIC_FILE_SUFFIXES):
        raise HTTPException(status_code=404, detail="Paquete no encontrado")

@router.get("/")
def listar_paquetes(
    busqueda: str = "",
    max_precio: int = 1000000,
    orden: str = "nombre",
    limit: int = 50,
    offset: int = 0,
):
    return PaqueteService.buscar_paquetes(
        busqueda,
        max_precio,
        orden,
        limit,
        offset,
    )


@router.get("/{paquete_id}")
def obtener_detalle_paquete(paquete_id: str):
    _reject_asset_like_id(paquete_id)
    detalle = PaqueteService.obtener_detalle_publico(paquete_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    return detalle
