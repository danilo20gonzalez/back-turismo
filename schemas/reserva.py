from pydantic import BaseModel
from datetime import date

class ReservaCreate(BaseModel):
    paquete_id: str  # El ID del paquete (ej: Paquete_Cascada_Fin_Mundo)
    fecha_viaje: date
    cantidad_personas: int


class ReservaEstadoUpdate(BaseModel):
    estado: str


class ReservaDisponibilidadDestino(BaseModel):
    id: str
    nombre: str
    capacidad_diaria: int | None = None


class ReservaDisponibilidadResponse(BaseModel):
    paquete_id: str
    fecha_minima: date
    dias: int
    viajeros: int
    capacidad_paquete: int | None = None
    destinos_limitados: list[ReservaDisponibilidadDestino] = []
    fechas_disponibles: list[date] = []
    fechas_no_disponibles: list[date] = []
