from datetime import date

from fastapi import APIRouter, Depends, Query

from core.auth import get_current_user
from schemas.reserva import ReservaEstadoUpdate
from services.reserva_service import ReservaService


router = APIRouter(prefix="/operador", tags=["Operador"])


@router.get("/reservas")
def listar_reservas_operador(
    estado: str | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    paquete: str | None = Query(default=None),
    current_user=Depends(get_current_user),
):
    return ReservaService.obtener_operador_reservas(
        current_user,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        paquete=paquete,
    )


@router.patch("/reservas/{reserva_id}/estado")
def actualizar_estado_reserva_operador(
    reserva_id: str,
    payload: ReservaEstadoUpdate,
    current_user=Depends(get_current_user),
):
    return ReservaService.actualizar_estado_operador(
        current_user,
        reserva_id=reserva_id,
        estado=payload.estado,
    )
