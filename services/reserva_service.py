import uuid

from fastapi import HTTPException

from schemas.reserva import ReservaCreate
from sparql_builder import EX, resource_uri
from sparql_client import SparqlClient
from sparql_queries import reservas as reserva_queries
from sparql_queries.usuarios import resolve_user_uri


client = SparqlClient()


class ReservaService:
    @staticmethod
    def _user_uri(user_or_uri) -> str:
        if isinstance(user_or_uri, str):
            return user_or_uri
        return resolve_user_uri(user_or_uri)

    @staticmethod
    def _package_uri(paquete_id: str) -> str:
        return resource_uri(paquete_id)

    @staticmethod
    def crear_reserva(user, datos: ReservaCreate):
        reserva_uuid = str(uuid.uuid4())[:8]
        reserva_uri = f"{EX}Reserva_{reserva_uuid}"
        user_uri = ReservaService._user_uri(user)
        paquete_uri = ReservaService._package_uri(datos.paquete_id)

        res_capacidad = client.execute_select(
            reserva_queries.capacity_for_package(paquete_uri, datos.fecha_viaje)
        )

        if res_capacidad:
            cap_max = int(res_capacidad[0]["capacidadMax"]["value"])
            ocupado = (
                int(res_capacidad[0]["totalOcupado"]["value"])
                if "totalOcupado" in res_capacidad[0]
                and res_capacidad[0]["totalOcupado"]["value"] != ""
                else 0
            )

            solicitados = datos.cantidad_personas

            if (ocupado + solicitados) > cap_max:
                cupos_libres = cap_max - ocupado
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Capacidad excedida para esta fecha. "
                        f"Cupos disponibles: {cupos_libres}. Solicitados: {solicitados}"
                    ),
                )

        client.execute_sparql_update(
            reserva_queries.insert_reservation(
                reserva_uri=reserva_uri,
                user_uri=user_uri,
                paquete_id=paquete_uri,
                fecha_inicio=datos.fecha_viaje,
                numero_viajeros=datos.cantidad_personas,
                estado="Confirmada",
            )
        )

        return {
            "message": "Reserva creada exitosamente",
            "reserva_id": reserva_uri.split("#")[-1],
        }

    @staticmethod
    def obtener_mis_reservas(user):
        user_uri = ReservaService._user_uri(user)
        results = client.execute_select(reserva_queries.user_reservations(user_uri))

        mis_reservas = []
        for row in results:
            comunidad = row.get("comunidad_nombre", {}).get("value", "Comunidad por asignar")
            precio_t = row.get("total_pagar", {}).get("value", 0.0)

            mis_reservas.append(
                {
                    "reserva_id": row["reserva"]["value"].split("#")[-1],
                    "paquete": row["paquete_id"]["value"].replace("_", " "),
                    "fecha": row["fecha"]["value"],
                    "viajeros": int(row["personas"]["value"]),
                    "estado": row["estado"]["value"],
                    "operado_por": comunidad,
                    "precio_total": float(precio_t),
                    "moneda": "COP",
                }
            )
        return mis_reservas
