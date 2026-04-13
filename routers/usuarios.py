from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm 
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user
from schemas.usuario import UsuarioRegistro, UsuarioLogin, ProfileResponse, ProfileUpdate, UserResponse
from services.usuario_service import UsuarioService
from datetime import datetime

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registrar(datos: UsuarioRegistro, db: Session = Depends(get_db)):
    """
    Registra un usuario en Postgres y crea su perfil semántico en Fuseki.
    """
    try:
        # Ahora pasamos 'db' para que el servicio pueda guardar en Postgres
        return UsuarioService.registrar_usuario(datos, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Valida credenciales contra Postgres y devuelve un JWT.
    """
    # OAuth2PasswordRequestForm usa 'username' para el email
    datos = UsuarioLogin(email=form_data.username, password=form_data.password)
    
    usuario_autenticado = UsuarioService.login(datos, db)
    if not usuario_autenticado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario_autenticado

from services.usuario_service import client  # O donde tengas instanciado SparqlClient

@router.get("/me/perfil", response_model=ProfileResponse)
def obtener_mi_perfil(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Retorna los datos extendidos del perfil extrayendo conocimiento de Fuseki.
    """
    # 1. Identificadores para Fuseki
    # Usamos user_uri_id para el conteo y user_uri_completa para la consulta detallada
    user_uri_id = f"{current_user.rol.nombre}_{current_user.id}"
    user_uri_completa = f"http://amaturis.org/ontology#{user_uri_id}"
    ahora = datetime.now()

    # Inicializamos variables
    reservas_activas = []
    historial_viajes = []
    total_reservas = 0
    
    # 2. Consultar estadísticas reales (Conteo)
    try:
        resultados_stats = client.execute_query("obtener_estadisticas_usuario", {"user_id": user_uri_id})
        if resultados_stats and "total" in resultados_stats[0]:
            total_reservas = int(resultados_stats[0]["total"]["value"])
    except Exception as e:
        print(f"Error al conectar con Fuseki (Stats): {e}")

    # 3. Inferencia de nivel
    if total_reservas == 0:
        nivel = "Novato Amazónico"
    elif total_reservas < 5:
        nivel = "Explorador Bronce"
    elif total_reservas < 10:
        nivel = "Explorador Plata"
    else:
        nivel = "Guía de Oro"

    # 4. Obtener y clasificar lista de reservas (Activas vs Historial)
    try:
        res_detalles = client.execute_query("obtener_mis_reservas", {"user_id": user_uri_completa})
        
        for r in res_detalles:

            f_inicio = r.get("fecha", {}).get("value", "")
            print(f"Procesando reserva: {r.get('paquete_id', {}).get('value')} - Fecha: {f_inicio}")
            if not f_inicio:
                continue
            # Extraemos y parseamos la fecha para comparar
            fecha_str = r["fecha"]["value"].split("T")[0]
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
            
            reserva_item = {
                "id": str(r.get("paquete_id", {}).get("value", "0")),
                "title": f"Reserva en {r.get('comunidad_nombre', {}).get('value', 'Sitio Amazónico')}",
                "date": fecha_str,
                "dateRange": f"{fecha_str} - Evento", # El Front lo pide como string
                "status": "Confirmado" if r.get("estado", {}).get("value") == "Confirmada" else "Pendiente de pago",
                "price": f"${r.get('total_pagar', {}).get('value', '0')}",
                "people": str(r.get("personas", {}).get("value", "1")), # El Front espera STRING, no int
                "image": "https://images.unsplash.com/photo-1596401057633-54a8fe8ef647?q=80&w=500", # Imagen por defecto
                "actionLabel": "Ver detalles" # Lo pide el historial
            }

            # Clasificación lógica por fecha
            if fecha_obj >= ahora:
                reservas_activas.append(reserva_item)
            else:
                historial_viajes.append(reserva_item)
                
    except Exception as e:
        print(f"Error al obtener lista de reservas detallada: {e}")

    # 5. Respuesta dinámica al Front
    return {
        "name": current_user.nombre_completo,
        "location": "Florencia, Caquetá",
        "avatar": "https://www.gravatar.com/avatar/000?d=mp",
        "stats": {
            "totalTrips": total_reservas,
            "explorerLevel": nivel,
            "memberSince": current_user.fecha_registro.strftime("%B %Y") if hasattr(current_user, 'fecha_registro') else "Abril 2026"
        },
        "bookings": reservas_activas, # Se mostrarán en la pestaña principal
        "history": historial_viajes,  # Se mostrarán en la pestaña de historial
        "map": {
            "title": "Tu ubicación",
            "subtitle": "Florencia, Caquetá",
            "lat": 1.61,
            "lng": -75.6
        }
    }

@router.put("/me", response_model=UserResponse)
def update_user_profile(
    data: ProfileUpdate, 
    db: Session = Depends(get_db), 
    current_user = Depends(get_current_user)
):
    # Llamamos a la lógica que reside en el servicio
    updated_user = UsuarioService.update_profile(db, current_user, data)
    return updated_user