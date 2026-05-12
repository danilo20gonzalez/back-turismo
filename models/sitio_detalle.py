# models/sitio_detalle.py
from pydantic import BaseModel, ConfigDict
from typing import Optional


class SitioDetalle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    descripcion: Optional[str] = None
    municipio: Optional[str] = None
    capacidad_diaria: Optional[int] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    tipos: Optional[str] = None
