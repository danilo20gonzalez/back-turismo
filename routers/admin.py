from datetime import date

from fastapi import APIRouter, Depends, Query

from core.auth import get_current_user
from services.reserva_service import ReservaService


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/reservas")
def listar_reservas_admin(
    estado: str | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user=Depends(get_current_user),
):
    return ReservaService.obtener_admin_reservas(
        current_user,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
    )


@router.get("/reservas/kpis")
def obtener_kpis_reservas_admin(
    estado: str | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user=Depends(get_current_user),
):
    return ReservaService.obtener_admin_kpis_reservas(
        current_user,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
    )

