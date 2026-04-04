from sparql_client import SparqlClient
import uuid
from models.reserva import ReservaCreate
from datetime import date
from fastapi import HTTPException

client = SparqlClient()

class ReservaService:

    @staticmethod
    def crear_reserva(user_id: str, datos: ReservaCreate):
        # 1. Creamos las URIs completas (tu lógica actual)
        reserva_uuid = str(uuid.uuid4())[:8]
        reserva_uri = f"http://amaturis.org/ontology#Reserva_{reserva_uuid}"
        
        user_uri = user_id.replace("<", "").replace(">", "")
        
        paquete_uri = f"http://amaturis.org/ontology#{datos.paquete_id}"
        if datos.paquete_id.startswith("http"):
            paquete_uri = datos.paquete_id

        # --- INICIO VALIDACIÓN DE CAPACIDAD ---
        # Parámetros para la consulta de verificación
        check_params = {
            "paquete_id": paquete_uri,
            "fecha_viaje": datos.fecha_viaje.isoformat()
        }
        
        # Llamamos a la consulta que creamos antes en .sparql
        res_capacidad = client.execute_query("verificar_capacidad", check_params)
        
        if res_capacidad:
            # Extraemos capacidad máxima y lo ya reservado
            # Usamos el nombre exacto que encontraste: capacidadMaxPersonas (vía el SPARQL)
            cap_max = int(res_capacidad[0]["capacidadMax"]["value"])
            
            # totalOcupado puede no existir si es la primera reserva
            ocupado = int(res_capacidad[0]["totalOcupado"]["value"]) if "totalOcupado" in res_capacidad[0] and res_capacidad[0]["totalOcupado"]["value"] != "" else 0
            
            solicitados = datos.cantidad_personas
            
            if (ocupado + solicitados) > cap_max:
                cupos_libres = cap_max - ocupado
                raise HTTPException(
                    status_code=400, 
                    detail=f"Capacidad excedida para esta fecha. Cupos disponibles: {cupos_libres}. Solicitados: {solicitados}"
                )
        # --- FIN VALIDACIÓN DE CAPACIDAD ---

        # 2. Si pasó la validación, preparamos los parámetros del INSERT
        params = {
            "reserva_id": reserva_uri,
            "user_id": user_uri,
            "paquete_id": paquete_uri,
            "fecha_inicio": datos.fecha_viaje.isoformat(),
            "num_viajeros": datos.cantidad_personas,
            "estado": "Confirmada"
        }
        
        # 3. Ejecutamos el guardado en Fuseki
        client.execute_update("crear_reserva", params)
        
        return {
            "message": "Reserva creada exitosamente", 
            "reserva_id": reserva_uri.split("#")[-1]
        }

    @staticmethod
    def obtener_mis_reservas(user_id: str):
        params = {"user_id": user_id}
        results = client.execute_query("obtener_mis_reservas", params)
        
        mis_reservas = []
        for row in results:
            # .get() evita el KeyError si la propiedad no existe en esa fila
            # Si no hay comunidad, pondrá "Comunidad por asignar"
            comunidad = row.get("comunidad_nombre", {}).get("value", "Comunidad por asignar")
            
            # Si no hay precio, pondrá 0.0
            precio_t = row.get("total_pagar", {}).get("value", 0.0)

            mis_reservas.append({
                "reserva_id": row["reserva"]["value"].split("#")[-1],
                "paquete": row["paquete_id"]["value"].replace("_", " "),
                "fecha": row["fecha"]["value"],
                "viajeros": int(row["personas"]["value"]),
                "estado": row["estado"]["value"],
                "operado_por": comunidad,
                "precio_total": float(precio_t),
                "moneda": "COP"
            })
        return mis_reservas

    