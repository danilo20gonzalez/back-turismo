from datetime import date

from fastapi import APIRouter, Depends, Query

from core.auth import get_current_user
from schemas.paquete import PaqueteWrite
from schemas.servicio import ServicioWrite
from schemas.reserva import ReservaEstadoUpdate
from services.paquete_service import PaqueteService
from services.reserva_service import ReservaService
from services.servicio_service import ServicioService


router = APIRouter(prefix="/operador", tags=["Operador"])


@router.get("/paquetes")
def listar_paquetes_operador(
    q: str | None = Query(default=None),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
    current_user=Depends(get_current_user),
):
    return PaqueteService.listar_operador_paquetes(
        current_user,
        busqueda=q or "",
        limit=limit,
        offset=offset,
    )


@router.get("/paquetes/propietarios")
def listar_propietarios_paquetes_operador(
    current_user=Depends(get_current_user),
):
    return PaqueteService.listar_propietarios(current_user)


@router.get("/paquetes/servicios")
def listar_servicios_paquetes_operador(
    limit: int = Query(default=300),
    current_user=Depends(get_current_user),
):
    return PaqueteService.listar_servicios_catalogo(current_user, limit=limit)


@router.get("/paquetes/{paquete_id}")
def obtener_paquete_operador(
    paquete_id: str,
    current_user=Depends(get_current_user),
):
    return PaqueteService.obtener_detalle_operador(current_user, paquete_id)


@router.post("/paquetes")
def crear_paquete_operador(
    payload: PaqueteWrite,
    current_user=Depends(get_current_user),
):
    return PaqueteService.crear_operador_paquete(current_user, payload)


@router.put("/paquetes/{paquete_id}")
def actualizar_paquete_operador(
    paquete_id: str,
    payload: PaqueteWrite,
    current_user=Depends(get_current_user),
):
    return PaqueteService.actualizar_operador_paquete(current_user, paquete_id, payload)


@router.get("/servicios")
def listar_servicios_operador(
    q: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    tipo_uri: str | None = Query(default=None),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
    current_user=Depends(get_current_user),
):
    return ServicioService.listar_servicios(
        current_user,
        busqueda=q or "",
        estado=estado,
        tipo_uri=tipo_uri,
        limit=limit,
        offset=offset,
    )


@router.get("/servicios/tipos")
def listar_tipos_servicio_operador(
    current_user=Depends(get_current_user),
):
    return ServicioService.listar_tipos_servicio(current_user)


@router.get("/servicios/propietarios")
def listar_propietarios_servicio_operador(
    current_user=Depends(get_current_user),
):
    return ServicioService.listar_propietarios(current_user)


@router.get("/servicios/{servicio_id}")
def obtener_servicio_operador(
    servicio_id: str,
    current_user=Depends(get_current_user),
):
    return ServicioService.obtener_detalle(current_user, servicio_id)


@router.post("/servicios")
def crear_servicio_operador(
    payload: ServicioWrite,
    current_user=Depends(get_current_user),
):
    return ServicioService.crear_servicio(current_user, payload)


@router.put("/servicios/{servicio_id}")
def actualizar_servicio_operador(
    servicio_id: str,
    payload: ServicioWrite,
    current_user=Depends(get_current_user),
):
    return ServicioService.actualizar_servicio(current_user, servicio_id, payload)


@router.delete("/servicios/{servicio_id}")
def eliminar_servicio_operador(
    servicio_id: str,
    current_user=Depends(get_current_user),
):
    return ServicioService.eliminar_servicio(current_user, servicio_id)


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
