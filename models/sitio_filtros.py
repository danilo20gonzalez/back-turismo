# models/sitio_filtros.py
from pydantic import BaseModel
from typing import List, Optional


class SitioTipo(BaseModel):
    uri: str
    nombre: str
    total: Optional[int] = None


class SitioMunicipio(BaseModel):
    uri: str
    nombre: str


class SitioFiltros(BaseModel):
    tipos: List[SitioTipo]
    municipios: List[SitioMunicipio]
    capacidad_min: Optional[int] = None
    capacidad_max: Optional[int] = None

    class Config:
        from_attributes = True
