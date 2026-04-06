from SPARQLWrapper import SPARQLWrapper, JSON, POST
from config import settings
import os
import re

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
                # Reemplaza ${key} por el valor, escapando strings para evitar inyecciones
                placeholder = f"${{{key}}}"
                if isinstance(value, str):
                    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
                    quoted_placeholder = f"\"{placeholder}\""
                    if quoted_placeholder in query_str:
                        query_str = query_str.replace(quoted_placeholder, f"\"{escaped}\"")
                    else:
                        query_str = query_str.replace(placeholder, escaped)
                else:
                    query_str = query_str.replace(placeholder, str(value))

            # Paginacion: si hay limit/offset, reemplazamos valores numericos fijos
            if "limit" in params:
                limit_value = int(params["limit"])
                query_str = re.sub(r"(?im)^\s*LIMIT\s+\d+", f"LIMIT {limit_value}", query_str)
            if "offset" in params:
                offset_value = int(params["offset"])
                query_str = re.sub(r"(?im)^\s*OFFSET\s+\d+", f"OFFSET {offset_value}", query_str)
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
            raise

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
            raise
