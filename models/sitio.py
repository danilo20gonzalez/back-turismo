# models/sitio.py
from pydantic import BaseModel
from typing import Optional


class Sitio(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    municipio: Optional[str] = None
    capacidad_diaria: Optional[int] = None
    tipos: Optional[str] = None
    popularidad: Optional[int] = None

    class Config:
        from_attributes = True
