from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm 
from models.usuario import UsuarioRegistro, UsuarioLogin
from services.usuario_service import UsuarioService

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.post("/registro")
def registrar(datos: UsuarioRegistro):
    try:
        return UsuarioService.registrar_turista(datos)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Convertimos lo que viene del formulario al formato que espera tu servicio
    datos = UsuarioLogin(email=form_data.username, password=form_data.password)
    return UsuarioService.login(datos)