# services/paquete_service.py
from sparql_client import SparqlClient
from schemas.paquete import Paquete

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

    @staticmethod
    def obtener_detalle(paquete_id: str):
        params = {"id": paquete_id}
        base_results = client.execute_query("paquete_detalle_base", params)
        if not base_results:
            return None

        base = base_results[0]

        def get_value(res, key):
            return res[key]["value"] if key in res else None

        detalle = PaqueteDetalle(
            id=get_value(base, "paquete"),
            nombre=get_value(base, "nombre"),
            descripcion=get_value(base, "descripcion"),
            precio=float(get_value(base, "precio")),
            duracion_dias=int(get_value(base, "duracion")) if get_value(base, "duracion") else None,
            dificultad=get_value(base, "dificultad"),
            capacidad_max_personas=int(get_value(base, "capacidad")) if get_value(base, "capacidad") else None,
            incluye_descripcion=get_value(base, "incluye"),
            no_incluye=get_value(base, "noIncluye"),
        )

        destinos_results = client.execute_query("paquete_detalle_destinos", params)
        destinos = []
        destinos_seen = set()
        for res in destinos_results:
            nombre = get_value(res, "destinoNombre")
            if not nombre:
                continue
            municipio = get_value(res, "municipioNombre")
            lat_raw = get_value(res, "lat")
            lon_raw = get_value(res, "lon")
            categoria = get_value(res, "categoriaLabel")
            lat = float(lat_raw) if lat_raw else None
            lon = float(lon_raw) if lon_raw else None
            key = (nombre, municipio, lat, lon, categoria)
            if key in destinos_seen:
                continue
            destinos_seen.add(key)
            destinos.append(
                PaqueteDetalleDestino(
                    nombre=nombre,
                    municipio=municipio,
                    latitud=lat,
                    longitud=lon,
                    categoria=categoria,
                )
            )

        servicios_results = client.execute_query("paquete_detalle_servicios", params)
        servicios = []
        servicios_seen = set()
        for res in servicios_results:
            nombre = get_value(res, "servicioNombre")
            if not nombre:
                continue
            tipo = get_value(res, "tipoLabel")
            key = (nombre, tipo)
            if key in servicios_seen:
                continue
            servicios_seen.add(key)
            servicios.append(
                PaqueteDetalleServicio(
                    nombre=nombre,
                    tipo=tipo,
                )
            )

        itinerarios_results = client.execute_query("paquete_detalle_itinerarios", params)
        itinerarios = []
        itinerarios_seen = set()
        for res in itinerarios_results:
            titulo = get_value(res, "titulo")
            descripcion = get_value(res, "descripcion")
            if not titulo and not descripcion:
                continue
            key = (titulo, descripcion)
            if key in itinerarios_seen:
                continue
            itinerarios_seen.add(key)
            itinerarios.append(
                PaqueteDetalleItinerario(
                    titulo=titulo,
                    descripcion=descripcion,
                )
            )

        detalle.destinos = destinos or None
        detalle.servicios = servicios or None
        detalle.itinerarios = itinerarios or None

        return detalle
