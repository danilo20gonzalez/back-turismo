# services/paquete_service.py
from sparql_client import SparqlClient
from models.paquete import Paquete

client = SparqlClient()

class PaqueteService:
    @staticmethod
    def buscar_paquetes(busqueda: str, max_precio: int, limit: int, offset: int):
        # Normalizamos parametros para evitar limites extremos
        busqueda = busqueda or ""
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        params = {
            "busqueda": busqueda,
            "max_precio": max_precio,
            "limit": limit,
            "offset": offset,
        }
        raw_results = client.execute_query("paquetes", params)
        
        paquetes = []
        for res in raw_results:
            dirigido_a = res["dirigidoA"]["value"] if "dirigidoA" in res else None
            duracion_dias = int(res["duracion"]["value"]) if "duracion" in res else None
            dificultad = res["dificultad"]["value"] if "dificultad" in res else None
            destinos = res["destinos"]["value"] if "destinos" in res else None
            municipios = res["municipios"]["value"] if "municipios" in res else None
            categorias = res["categorias"]["value"] if "categorias" in res else None
            capacidad = (
                int(res["capacidad"]["value"]) if "capacidad" in res else None
            )

            # Extraemos los valores de los bindings de Fuseki
            paquetes.append(Paquete(
                id=res["paquete"]["value"],
                nombre=res["nombre"]["value"],
                precio=float(res["precio"]["value"]),
                descripcion=res["descripcion"]["value"],
                dirigidoA=dirigido_a,
                duracion_dias=duracion_dias,
                dificultad=dificultad,
                destinos=destinos,
                municipios=municipios,
                categorias=categorias,
                capacidad_max_personas=capacidad,
            ))
        return paquetes
