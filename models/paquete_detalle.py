# models/paquete_detalle.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class PaqueteDetalleDestino(BaseModel):
    id: Optional[str] = None
    nombre: str
    municipio: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    categoria: Optional[str] = None
    url_imagen: Optional[str] = None
    galeria_imagenes: Optional[str] = None

class PaqueteDetalleServicio(BaseModel):
    id: Optional[str] = None
    nombre: str
    tipo: Optional[str] = None

class PaqueteDetalleItinerario(BaseModel):
    id: Optional[str] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None

class PaqueteDetalle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    descripcion: str
    precio: float
    duracion_dias: Optional[int] = None
    dificultad: Optional[str] = None
    capacidad_max_personas: Optional[int] = None
    incluye_descripcion: Optional[str] = None
    no_incluye: Optional[str] = None
    agencia_uri: Optional[str] = None
    agencia_nombre: Optional[str] = None
    url_imagen: Optional[str] = None
    galeria_imagenes: Optional[str] = None
    estado_publicacion: Optional[str] = None
    destinos: Optional[List[PaqueteDetalleDestino]] = None
    servicios: Optional[List[PaqueteDetalleServicio]] = None
    itinerarios: Optional[List[PaqueteDetalleItinerario]] = None
