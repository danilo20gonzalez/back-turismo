# models/paquete.py
from pydantic import BaseModel
from typing import Optional

class Paquete(BaseModel):
    id: str           # El URI del paquete (ej: http://amaturis.org/ontology#Paquete_Ecoturismo_001)
    nombre: str       # ex:nombre
    precio: float     # ex:precioPorPersona
    descripcion: str  # ex:descripcion
    
    class Config:
        from_attributes = True