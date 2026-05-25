import os
import re

import httpx
from SPARQLWrapper import BASIC, JSON, POST, SPARQLWrapper

from config import settings


class SparqlClient:
    def __init__(self):
        self.query_url = settings.FUSEKI_QUERY
        self.update_url = settings.FUSEKI_UPDATE

    def _has_fuseki_auth(self) -> bool:
        return bool(settings.FUSEKI_USER and settings.FUSEKI_PASSWORD)

    def _configure_sparql_auth(self, sparql: SPARQLWrapper) -> None:
        if self._has_fuseki_auth():
            sparql.setHTTPAuth(BASIC)
            sparql.setCredentials(settings.FUSEKI_USER, settings.FUSEKI_PASSWORD)

    def _httpx_auth(self):
        if self._has_fuseki_auth():
            return httpx.BasicAuth(settings.FUSEKI_USER, settings.FUSEKI_PASSWORD)
        return None

    def _get_query_string(self, query_name: str, params: dict = None) -> str:
        """Lee archivos .sparql heredados y reemplaza variables."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "queries", f"{query_name}.sparql")
        with open(path, "r", encoding="utf-8") as f:
            query_str = f.read()

        if params:
            for key, value in params.items():
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

            if "limit" in params:
                limit = int(params["limit"])
                query_str = re.sub(r"(?im)^\s*LIMIT\s+\d+", f"LIMIT {limit}", query_str)
            if "offset" in params:
                offset = int(params["offset"])
                query_str = re.sub(r"(?im)^\s*OFFSET\s+\d+", f"OFFSET {offset}", query_str)
        return query_str

    # ─── métodos síncronos (legacy) ────────────────────────────────────────

    def execute_select(self, query_str: str):
        sparql = SPARQLWrapper(self.query_url)
        self._configure_sparql_auth(sparql)
        sparql.setQuery(query_str)
        sparql.setReturnFormat(JSON)

        try:
            results = sparql.query().convert()
            return results["results"]["bindings"]
        except Exception as e:
            print(f"Error en query SPARQL: {e}")
            raise

    def execute_query(self, query_name: str, params: dict = None):
        """Compatibilidad con archivos .sparql heredados."""
        query_str = self._get_query_string(query_name, params)
        return self.execute_select(query_str)

    def execute_sparql_update(self, query_str: str):
        sparql = SPARQLWrapper(self.update_url)
        self._configure_sparql_auth(sparql)
        sparql.setQuery(query_str)
        sparql.setMethod(POST)

        try:
            sparql.query()
            print(f"DEBUG: Triple enviado a {self.update_url}")
            return True
        except Exception as e:
            print(f"ERROR FUSEKI: {e}")
            raise

    def execute_update(self, query_name: str, params: dict = None):
        """Compatibilidad con archivos .sparql heredados."""
        query_str = self._get_query_string(query_name, params)
        return self.execute_sparql_update(query_str)

    # ─── métodos asíncronos (nuevos) ───────────────────────────────────────

    async def execute_select_async(self, query_str: str, timeout: float = 30.0):
        """Ejecuta una SELECT SPARQL usando httppx asíncrono."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    self.query_url,
                    data={"query": query_str},
                    headers={"Accept": "application/sparql-results+json"},
                    auth=self._httpx_auth(),
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", {}).get("bindings", [])
            except Exception as e:
                print(f"Error en query SPARQL async: {e}")
                raise

    async def execute_sparql_update_async(self, query_str: str, timeout: float = 30.0):
        """Ejecuta una UPDATE SPARQL usando httppx asíncrono."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    self.update_url,
                    data={"update": query_str},
                    headers={"Accept": "application/sparql-results+json"},
                    auth=self._httpx_auth(),
                )
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Error en UPDATE SPARQL async: {e}")
                raise
