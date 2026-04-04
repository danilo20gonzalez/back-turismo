from fastapi import APIRouter, Depends, HTTPException
from models.reserva import ReservaCreate
from services.reserva_service import ReservaService
from core.auth import get_current_user 

router = APIRouter(prefix="/reservas", tags=["Reservas"])

@router.post("/crear")
def crear_nueva_reserva(
    datos: ReservaCreate, 
    current_user: dict = Depends(get_current_user)
):
    try:
        # Extraemos el ID del usuario del token decodificado
        user_id = current_user["sub"] 
        return ReservaService.crear_reserva(user_id, datos)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/mis-reservas")
def listar_mis_reservas(current_user: dict = Depends(get_current_user)):
    # current_user["sub"] trae el ID del usuario del token
    return ReservaService.obtener_mis_reservas(current_user["sub"])