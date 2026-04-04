from SPARQLWrapper import SPARQLWrapper, JSON, POST
from config import settings
import os

class SparqlClient:
    def __init__(self):
        self.query_url = settings.FUSEKI_QUERY
        self.update_url = settings.FUSEKI_UPDATE

    def _get_query_string(self, query_name: str, params: dict = None) -> str:
        """Lee el archivo .sparql y reemplaza variables"""
        path = os.path.join("queries", f"{query_name}.sparql")
        with open(path, "r", encoding="utf-8") as f:
            query_str = f.read()
        
        if params:
            for key, value in params.items():
                # Reemplaza ${key} por el valor (ej: ${perfil} -> 'aventura')
                query_str = query_str.replace(f"${{{key}}}", str(value))
        return query_str

    def execute_query(self, query_name: str, params: dict = None):
        """Para SELECT y ASK"""
        sparql = SPARQLWrapper(self.query_url)
        query_str = self._get_query_string(query_name, params)
        
        sparql.setQuery(query_str)
        sparql.setReturnFormat(JSON)
        
        try:
            results = sparql.query().convert()
            return results["results"]["bindings"]
        except Exception as e:
            print(f"Error en query SPARQL: {e}")
            return []

    def execute_update(self, query_name: str, params: dict = None):
        sparql = SPARQLWrapper(self.update_url)
        query_str = self._get_query_string(query_name, params)
        
        # Configuramos la petición para Fuseki
        sparql.setQuery(query_str)
        sparql.setMethod('POST') 
        
        try:
            # Enviamos y verificamos respuesta
            response = sparql.query()
            print(f"DEBUG: Triple enviado a {self.update_url}")
            return True
        except Exception as e:
            print(f"ERROR FUSEKI: {e}")
            return None