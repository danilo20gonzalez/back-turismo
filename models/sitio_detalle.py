# models/sitio_detalle.py
from pydantic import BaseModel
from typing import Optional


class SitioDetalle(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    municipio: Optional[str] = None
    capacidad_diaria: Optional[int] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    tipos: Optional[str] = None

    class Config:
        from_attributes = True
