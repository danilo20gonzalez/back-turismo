# models/paquete_detalle.py
from pydantic import BaseModel
from typing import Optional, List

class PaqueteDetalleDestino(BaseModel):
    nombre: str
    municipio: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    categoria: Optional[str] = None

class PaqueteDetalleServicio(BaseModel):
    nombre: str
    tipo: Optional[str] = None

class PaqueteDetalleItinerario(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None

class PaqueteDetalle(BaseModel):
    id: str
    nombre: str
    descripcion: str
    precio: float
    duracion_dias: Optional[int] = None
    dificultad: Optional[str] = None
    capacidad_max_personas: Optional[int] = None
    incluye_descripcion: Optional[str] = None
    no_incluye: Optional[str] = None
    destinos: Optional[List[PaqueteDetalleDestino]] = None
    servicios: Optional[List[PaqueteDetalleServicio]] = None
    itinerarios: Optional[List[PaqueteDetalleItinerario]] = None

    class Config:
        from_attributes = True
