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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/mis-reservas")
def listar_mis_reservas(current_user = Depends(get_current_user)):
    return ReservaService.obtener_mis_reservas(current_user)
