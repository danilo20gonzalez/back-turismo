# services/sitio_service.py
from typing import Optional
from sparql_client import SparqlClient
from models.sitio import Sitio
from models.sitio_filtros import SitioFiltros, SitioTipo, SitioMunicipio


client = SparqlClient()


class SitioService:
    @staticmethod
    def listar_sitios(
        busqueda: str,
        tipo: str,
        municipio: str,
        cap_min: Optional[int],
        cap_max: Optional[int],
        orden: str,
        limit: int,
        offset: int,
    ):
        busqueda = busqueda or ""
        tipo = tipo or ""
        municipio = municipio or ""
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        # Normalizamos rango de capacidad
        min_cap = cap_min if cap_min is not None else 0
        max_cap = cap_max if cap_max is not None else 999999999
        if max_cap < min_cap:
            max_cap = min_cap

        # Controlamos el orden para evitar inyecciones
        orden_map = {
            "popularidad": "DESC(?popularidad)",
            "nombre": "?nombre",
            "capacidad": "DESC(?capacidad)",
        }
        orden_clause = orden_map.get((orden or "popularidad").lower(), "DESC(?popularidad)")

        params = {
            "busqueda": busqueda,
            "tipo": tipo,
            "municipio": municipio,
            "cap_min": min_cap,
            "cap_max": max_cap,
            "orden": orden_clause,
            "limit": limit,
            "offset": offset,
        }

        raw_results = client.execute_query("sitios", params)
        sitios = []
        for res in raw_results:
            capacidad = int(res["capacidad"]["value"]) if "capacidad" in res else None
            popularidad = int(res["popularidad"]["value"]) if "popularidad" in res else None
            tipos = res["tipos"]["value"] if "tipos" in res else None

            sitios.append(
                Sitio(
                    id=res["destino"]["value"],
                    nombre=res["nombre"]["value"],
                    descripcion=res["descripcion"]["value"] if "descripcion" in res else None,
                    municipio=res["municipio"]["value"] if "municipio" in res else None,
                    capacidad_diaria=capacidad,
                    tipos=tipos,
                    popularidad=popularidad,
                )
            )

        return sitios

    @staticmethod
    def obtener_filtros():
        tipos_results = client.execute_query("sitios_tipos")
        municipios_results = client.execute_query("sitios_municipios")
        capacidad_results = client.execute_query("sitios_capacidad_rango")

        tipos = []
        for res in tipos_results:
            tipos.append(
                SitioTipo(
                    uri=res["tipo"]["value"],
                    nombre=res["nombre"]["value"],
                    total=int(res["total"]["value"]) if "total" in res else None,
                )
            )

        municipios = []
        for res in municipios_results:
            municipios.append(
                SitioMunicipio(
                    uri=res["municipio"]["value"],
                    nombre=res["nombre"]["value"],
                )
            )

        capacidad_min = None
        capacidad_max = None
        if capacidad_results:
            row = capacidad_results[0]
            capacidad_min = int(row["min_cap"]["value"]) if "min_cap" in row else None
            capacidad_max = int(row["max_cap"]["value"]) if "max_cap" in row else None

        return SitioFiltros(
            tipos=tipos,
            municipios=municipios,
            capacidad_min=capacidad_min,
            capacidad_max=capacidad_max,
        )
