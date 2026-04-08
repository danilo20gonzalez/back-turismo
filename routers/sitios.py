# routers/sitios.py
from fastapi import APIRouter, HTTPException
from typing import Optional
from services.sitio_service import SitioService


router = APIRouter(prefix="/sitios", tags=["Sitios"])


@router.get("/")
def listar_sitios(
    busqueda: str = "",
    tipo: str = "",
    municipio: str = "",
    cap_min: Optional[int] = None,
    cap_max: Optional[int] = None,
    orden: str = "popularidad",
    limit: int = 50,
    offset: int = 0,
):
    return SitioService.listar_sitios(
        busqueda,
        tipo,
        municipio,
        cap_min,
        cap_max,
        orden,
        limit,
        offset,
    )


@router.get("/filtros")
def obtener_filtros():
    return SitioService.obtener_filtros()


@router.get("/{sitio_id}")
def obtener_detalle_sitio(sitio_id: str):
    detalle = SitioService.obtener_detalle(sitio_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="Sitio no encontrado")
    return detalle


@router.get("/{sitio_id}/planes")
def obtener_planes_por_sitio(
    sitio_id: str,
    limit: int = 50,
    offset: int = 0,
):
    return SitioService.obtener_planes(sitio_id, limit, offset)
