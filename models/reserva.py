from pydantic import BaseModel
from datetime import date

class ReservaCreate(BaseModel):
    paquete_id: str  # El ID del paquete (ej: Paquete_Cascada_Fin_Mundo)
    fecha_viaje: date
    cantidad_personas: int