# models/paquete.py
from pydantic import BaseModel
from typing import Optional

class Paquete(BaseModel):
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
    
    class Config:
        from_attributes = True
