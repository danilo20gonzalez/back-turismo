from pydantic import BaseModel, Field
from typing import Optional


class Servicio(BaseModel):
    id: str
    nombre: str
    descripcion: str
    tipo_uri: Optional[str] = None
    tipo_nombre: Optional[str] = None
    estado_publicacion: Optional[str] = None
    url_imagen: Optional[str] = None
    agencia_uri: Optional[str] = None
    agencia_nombre: Optional[str] = None
    paquetes_vinculados: int = 0


class ServicioWrite(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    descripcion: str = Field(min_length=10, max_length=2000)
    tipo_uri: Optional[str] = Field(default=None, max_length=255)
    estado_publicacion: Optional[str] = Field(default="publicado", max_length=30)
    url_imagen: Optional[str] = Field(default=None, max_length=1000)
    agencia_uri: Optional[str] = Field(default=None, max_length=255)


class ServicioTipo(BaseModel):
    uri: str
    nombre: str
