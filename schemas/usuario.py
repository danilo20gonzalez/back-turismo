from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional

# Para el registro de nuevos usuarios
class UsuarioRegistro(BaseModel):
    nombre_completo: str
    email: EmailStr
    password: str
    rol_id: int

# Para la respuesta estándar de usuario (Post-Update o Auth)
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nombre_completo: str
    email: EmailStr
    uri_ontologia: Optional[str] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

# Esquemas para el Perfil Completo (Lectura)
class ProfileStats(BaseModel):
    totalTrips: int
    explorerLevel: str
    memberSince: str

class ProfileMap(BaseModel):
    title: str
    subtitle: str
    lat: float
    lng: float

class ProfileResponse(BaseModel):
    name: str
    location: str
    avatar: Optional[str] = None
    stats: ProfileStats
    bookings: List[dict] = []
    history: List[dict] = []
    map: ProfileMap

# Para la petición de actualización
class ProfileUpdate(BaseModel):
    name: str
    location: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
