from fastapi import APIRouter, Depends, HTTPException
from schemas.reserva import ReservaCreate
from services.reserva_service import ReservaService
from core.auth import get_current_user 

router = APIRouter(prefix="/reservas", tags=["Reservas"])

@router.post("/crear")
def crear_nueva_reserva(
    datos: ReservaCreate, 
    current_user = Depends(get_current_user)
):
    try:
        return ReservaService.crear_reserva(current_user, datos)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/disponibilidad/{paquete_id}")
def disponibilidad_reserva_paquete(
    paquete_id: str,
    dias: int = 90,
    viajeros: int = 1,
):
    return ReservaService.disponibilidad_para_paquete(
        paquete_id=paquete_id,
        dias=dias,
        viajeros=viajeros,
    )

@router.get("/mis-reservas")
def listar_mis_reservas(current_user = Depends(get_current_user)):
    return ReservaService.obtener_mis_reservas(current_user)


@router.get("/mias")
def listar_mias_normalizado(current_user = Depends(get_current_user)):
    return ReservaService.obtener_mias_normalizado(current_user)


@router.get("/{reserva_id}")
def obtener_reserva(reserva_id: str, current_user = Depends(get_current_user)):
    return ReservaService.obtener_reserva_por_id(current_user, reserva_id)


@router.patch("/{reserva_id}/cancelar")
def cancelar_reserva(reserva_id: str, current_user = Depends(get_current_user)):
    return ReservaService.cancelar_reserva(current_user, reserva_id)
