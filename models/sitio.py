# models/sitio.py
from pydantic import BaseModel, ConfigDict
from typing import Optional


class Sitio(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    descripcion: Optional[str] = None
    municipio: Optional[str] = None
    capacidad_diaria: Optional[int] = None
    tipos: Optional[str] = None
    popularidad: Optional[int] = None
