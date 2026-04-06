# routers/sitios.py
from fastapi import APIRouter
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
