# models/paquete.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class Paquete(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str           # El URI del paquete (ej: http://amaturis.org/ontology#Paquete_Ecoturismo_001)
    nombre: str       # ex:nombre
    precio: float     # ex:precioPorPersona
    descripcion: str  # ex:descripcion
    dirigidoA: Optional[str] = None  # ex:dirigidoA (label o URI)
    duracion_dias: Optional[int] = None  # ex:duracionDias
    dificultad: Optional[str] = None     # ex:tieneDificultad (label)
    destinos: Optional[str] = None       # Destinos concatenados
    municipios: Optional[str] = None     # Municipios concatenados
    categorias: Optional[str] = None     # Categorias concatenadas (tipo de destino)
    capacidad_max_personas: Optional[int] = None  # ex:capacidadMaxPersonas
    popularidad: Optional[int] = None
    url_imagen: Optional[str] = None
    galeria_imagenes: Optional[str] = None
    agencia_uri: Optional[str] = None
    agencia_nombre: Optional[str] = None
    estado_publicacion: Optional[str] = None


class PaqueteOwner(BaseModel):
    uri: str
    nombre: str


class PaqueteServicioCatalogo(BaseModel):
    id: str
    nombre: str
    tipo: Optional[str] = None


class PaqueteItinerarioWrite(BaseModel):
    titulo: str = Field(min_length=1, max_length=160)
    descripcion: Optional[str] = Field(default=None, max_length=1000)


class PaqueteWrite(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    descripcion: str = Field(min_length=10, max_length=2000)
    precio: float = Field(gt=0)
    duracion_dias: Optional[int] = Field(default=None, ge=1, le=60)
    dificultad: Optional[str] = Field(default="Moderado", max_length=40)
    capacidad_max_personas: Optional[int] = Field(default=None, ge=1, le=500)
    incluye_descripcion: Optional[str] = Field(default=None, max_length=1500)
    no_incluye: Optional[str] = Field(default=None, max_length=1500)
    url_imagen: Optional[str] = Field(default=None, max_length=1000)
    galeria_imagenes: Optional[str] = Field(default=None, max_length=2000)
    estado_publicacion: Optional[str] = Field(default="publicado", max_length=30)
    destino_ids: list[str] = Field(default_factory=list, max_length=6)
    servicio_ids: Optional[list[str]] = Field(default=None, max_length=25)
    itinerarios: Optional[list[PaqueteItinerarioWrite]] = Field(default=None, max_length=20)
    agencia_uri: Optional[str] = Field(default=None, max_length=255)
