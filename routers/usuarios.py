from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.database import get_db
from schemas.usuario import (
    ChangePasswordRequest,
    ProfileResponse,
    ProfileUpdate,
    UsuarioLogin,
    UsuarioRegistro,
    UserResponse,
)
from services.usuario_service import UsuarioService, client
from sparql_queries import reservas as reserva_queries
from sparql_queries import usuarios as usuario_queries


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registrar(datos: UsuarioRegistro, db: Session = Depends(get_db)):
    try:
        return UsuarioService.registrar_usuario(datos, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    datos = UsuarioLogin(email=form_data.username, password=form_data.password)
    usuario_autenticado = UsuarioService.login(datos, db)
    if not usuario_autenticado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario_autenticado


@router.get("/me/perfil", response_model=ProfileResponse)
def obtener_mi_perfil(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user_uri_completa = usuario_queries.resolve_user_uri(current_user)
    hoy = datetime.now().date()

    reservas_activas = []
    historial_viajes = []
    total_reservas = 0
    perfil_semantico = {}

    def semantic_value(key: str) -> str:
        return perfil_semantico.get(key, {}).get("value", "").strip()

    def format_member_since(value: str) -> str | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime("%B %Y")
        except ValueError:
            return value.split("T")[0]

    try:
        resultados_perfil = client.execute_select(
            usuario_queries.profile_summary(user_uri_completa)
        )
        if resultados_perfil:
            perfil_semantico = resultados_perfil[0]
    except Exception as e:
        print(f"Error al conectar con Fuseki (Perfil): {e}")

    try:
        resultados_stats = client.execute_select(reserva_queries.user_stats(user_uri_completa))
        if resultados_stats and "total" in resultados_stats[0]:
            total_reservas = int(resultados_stats[0]["total"]["value"])
    except Exception as e:
        print(f"Error al conectar con Fuseki (Stats): {e}")

    if total_reservas == 0:
        nivel = "Novato Amazonico"
    elif total_reservas < 5:
        nivel = "Explorador Bronce"
    elif total_reservas < 10:
        nivel = "Explorador Plata"
    else:
        nivel = "Guia de Oro"

    try:
        res_detalles = client.execute_select(reserva_queries.user_reservations(user_uri_completa))
        for r in res_detalles:
            f_inicio = r.get("fecha", {}).get("value", "")
            if not f_inicio:
                continue

            fecha_str = f_inicio.split("T")[0]
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            estado_reserva = r.get("estado", {}).get("value", "")
            estado_lower = estado_reserva.lower()
            reserva_id = r.get("reserva", {}).get("value", "").split("#")[-1]
            paquete_nombre = r.get("paquete_nombre", {}).get("value", "").strip()
            comunidad = r.get("comunidad_nombre", {}).get("value", "Agencia por asignar")

            reserva_item = {
                "id": reserva_id,
                "title": paquete_nombre if paquete_nombre else f"Reserva en {comunidad}",
                "date": fecha_str,
                "dateRange": f"{fecha_str} - {comunidad}",
                "status": "Confirmado" if "confirm" in estado_lower else "Pendiente de pago",
                "price": f"${r.get('total_pagar', {}).get('value', '0')}",
                "people": str(r.get("personas", {}).get("value", "1")),
                "image": r.get("paquete_imagen", {}).get("value", "")
                or "https://1qnmejprcdqaudae.public.blob.vercel-storage.com/amaturis/semillas/paisaje-amazonico-caqueta.jpg",
                "actionLabel": "Ver detalles",
                "href": f"/perfil/reservas/{reserva_id}",
            }

            if fecha_obj >= hoy and not any(term in estado_lower for term in ["cancel", "complet", "expir"]):
                reservas_activas.append(reserva_item)
            else:
                historial_viajes.append(reserva_item)

    except Exception as e:
        print(f"Error al obtener lista de reservas detallada: {e}")

    member_since = format_member_since(semantic_value("fechaRegistro"))
    if not member_since and hasattr(current_user, "fecha_registro"):
        member_since = current_user.fecha_registro.strftime("%B %Y")

    location = semantic_value("location") or "Florencia, Caqueta"

    return {
        "name": semantic_value("nombre") or current_user.nombre_completo,
        "location": location,
        "avatar": semantic_value("avatar") or "https://www.gravatar.com/avatar/000?d=mp",
        "bio": semantic_value("bio"),
        "stats": {
            "totalTrips": total_reservas,
            "explorerLevel": nivel,
            "memberSince": member_since or "Abril 2026",
        },
        "bookings": reservas_activas,
        "history": historial_viajes,
        "map": {
            "title": "Tu ubicacion",
            "subtitle": location,
            "lat": 1.61,
            "lng": -75.6,
        },
    }


@router.put("/me", response_model=UserResponse)
def update_user_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    updated_user = UsuarioService.update_profile(db, current_user, data)
    return updated_user


@router.put("/me/password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    UsuarioService.change_password(
        db=db,
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    return {"message": "Contrasena actualizada correctamente"}


@router.get("/me/favoritos")
def list_favorites(current_user=Depends(get_current_user)):
    return UsuarioService.list_favorites(current_user)


@router.post("/me/favoritos/{paquete_id}")
def add_favorite(paquete_id: str, current_user=Depends(get_current_user)):
    UsuarioService.add_favorite(current_user, paquete_id)
    return {"message": "Favorito agregado correctamente"}


@router.delete("/me/favoritos/{paquete_id}")
def remove_favorite(paquete_id: str, current_user=Depends(get_current_user)):
    UsuarioService.remove_favorite(current_user, paquete_id)
    return {"message": "Favorito eliminado correctamente"}
