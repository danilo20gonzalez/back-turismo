# services/sitio_service.py
from typing import Optional
from sparql_client import SparqlClient
from sparql_queries import paquetes as paquete_queries
from sparql_queries import sitios as sitio_queries
from models.sitio import Sitio
from models.sitio_filtros import SitioFiltros, SitioTipo, SitioMunicipio
from models.sitio_detalle import SitioDetalle
from models.paquete import Paquete


client = SparqlClient()


class SitioService:
    @staticmethod
    def _parse_paquetes(raw_results):
        paquetes = []
        for res in raw_results:
            dirigido_a = res["dirigidoA"]["value"] if "dirigidoA" in res else None
            duracion_dias = int(res["duracion"]["value"]) if "duracion" in res else None
            dificultad = res["dificultad"]["value"] if "dificultad" in res else None
            destinos = res["destinos"]["value"] if "destinos" in res else None
            municipios = res["municipios"]["value"] if "municipios" in res else None
            categorias = res["categorias"]["value"] if "categorias" in res else None
            capacidad = int(res["capacidad"]["value"]) if "capacidad" in res else None
            imagen = res["imagen"]["value"] if "imagen" in res else None
            galeria = res["galeria"]["value"] if "galeria" in res else None

            paquetes.append(
                Paquete(
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
                    url_imagen=imagen,
                    galeria_imagenes=galeria,
                )
            )
        return paquetes

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
        query = sitio_queries.list_sites(
            busqueda,
            tipo,
            municipio,
            cap_min,
            cap_max,
            orden,
            limit,
            offset,
        )
        raw_results = client.execute_select(query)
        sitios = []
        for res in raw_results:
            capacidad = int(res["capacidad"]["value"]) if "capacidad" in res else None
            popularidad = int(res["popularidad"]["value"]) if "popularidad" in res else None
            tipos = res["tipos"]["value"] if "tipos" in res else None
            imagen = res["imagen"]["value"] if "imagen" in res else None
            galeria = res["galeria"]["value"] if "galeria" in res else None

            sitios.append(
                Sitio(
                    id=res["destino"]["value"],
                    nombre=res["nombre"]["value"],
                    descripcion=res["descripcion"]["value"] if "descripcion" in res else None,
                    municipio=res["municipio"]["value"] if "municipio" in res else None,
                    capacidad_diaria=capacidad,
                    tipos=tipos,
                    popularidad=popularidad,
                    url_imagen=imagen,
                    galeria_imagenes=galeria,
                )
            )

        return sitios

    @staticmethod
    def obtener_filtros():
        tipos_results = client.execute_select(sitio_queries.filter_types())
        municipios_results = client.execute_select(sitio_queries.municipalities())
        capacidad_results = client.execute_select(sitio_queries.capacity_range())

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

    @staticmethod
    def obtener_detalle(sitio_id: str):
        resultados = client.execute_select(sitio_queries.detail(sitio_id))
        if not resultados:
            return None

        res = resultados[0]

        def get_value(key: str):
            return res[key]["value"] if key in res else None

        capacidad = get_value("capacidad")
        lat = get_value("lat")
        lon = get_value("lon")

        return SitioDetalle(
            id=get_value("destino"),
            nombre=get_value("nombre"),
            descripcion=get_value("descripcion"),
            municipio=get_value("municipio"),
            capacidad_diaria=int(capacidad) if capacidad else None,
            latitud=float(lat) if lat else None,
            longitud=float(lon) if lon else None,
            tipos=get_value("tipos"),
            url_imagen=get_value("imagen"),
            galeria_imagenes=get_value("galeria"),
        )

    @staticmethod
    def obtener_planes(sitio_id: str, limit: int, offset: int):
        raw_results = client.execute_select(
            paquete_queries.list_packages_for_site(sitio_id, limit, offset)
        )
        return SitioService._parse_paquetes(raw_results)
