# services/paquete_service.py
from sparql_client import SparqlClient
from models.paquete import Paquete

client = SparqlClient()

class PaqueteService:
    @staticmethod
    def buscar_paquetes(perfil: str, max_precio: int):
        params = {"perfil": perfil, "max_precio": max_precio}
        raw_results = client.execute_query("paquetes", params)
        
        paquetes = []
        for res in raw_results:
            # Extraemos los valores de los bindings de Fuseki
            paquetes.append(Paquete(
                id=res["paquete"]["value"],
                nombre=res["nombre"]["value"],
                precio=float(res["precio"]["value"]),
                descripcion=res["descripcion"]["value"],
                dirigidoA=perfil  # Opcional: puedes mapear esto a una propiedad real si existe
            ))
        return paquetes