import uuid

from fastapi import HTTPException

from core.roles import is_admin, is_operator_or_admin
from sparql_builder import EX
from sparql_client import SparqlClient
from sparql_queries import paquetes as paquete_queries
from models.paquete_detalle import (
    PaqueteDetalle,
    PaqueteDetalleDestino,
    PaqueteDetalleItinerario,
    PaqueteDetalleServicio,
)
from schemas.paquete import (
    Paquete,
    PaqueteOwner,
    PaqueteServicioCatalogo,
    PaqueteWrite,
)

client = SparqlClient()

class PaqueteService:
    @staticmethod
    def _assert_operator_or_admin(user):
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        if not is_operator_or_admin(role_name):
            raise HTTPException(status_code=403, detail="No autorizado para gestion operativa de paquetes")

    @staticmethod
    def _is_admin(user) -> bool:
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        return is_admin(role_name)

    @staticmethod
    def _resolve_operator_owner_uri(user) -> str | None:
        return (getattr(user, "agencia_uri", None) or "").strip() or None

    @staticmethod
    def _parse_package_row(res) -> Paquete:
        dirigido_a = res["dirigidoA"]["value"] if "dirigidoA" in res else None
        duracion_dias = int(res["duracion"]["value"]) if "duracion" in res else None
        dificultad = res["dificultad"]["value"] if "dificultad" in res else None
        destinos = res["destinos"]["value"] if "destinos" in res else None
        municipios = res["municipios"]["value"] if "municipios" in res else None
        categorias = res["categorias"]["value"] if "categorias" in res else None
        capacidad = int(res["capacidad"]["value"]) if "capacidad" in res else None
        popularidad = int(res["popularidad"]["value"]) if "popularidad" in res else None
        imagen = res["imagen"]["value"] if "imagen" in res else None
        galeria = res["galeria"]["value"] if "galeria" in res else None
        agencia_uri = res["agencia"]["value"] if "agencia" in res else None
        agencia_nombre = res["agenciaNombre"]["value"] if "agenciaNombre" in res else None
        estado_publicacion = (
            res["estadoPublicacion"]["value"] if "estadoPublicacion" in res else "publicado"
        )

        return Paquete(
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
            popularidad=popularidad,
            url_imagen=imagen,
            galeria_imagenes=galeria,
            agencia_uri=agencia_uri,
            agencia_nombre=agencia_nombre,
            estado_publicacion=estado_publicacion,
        )

    @staticmethod
    def _is_public_status(value: str | None) -> bool:
        return (value or "publicado").strip().lower() == "publicado"

    @staticmethod
    def _require_owner(user) -> str:
        owner_uri = PaqueteService._resolve_operator_owner_uri(user)
        if not owner_uri:
            raise HTTPException(
                status_code=400,
                detail="El usuario operador no tiene agencia/prestador vinculado en ontologia",
            )
        return owner_uri

    @staticmethod
    def _assert_package_access(user, paquete_id: str):
        PaqueteService._assert_operator_or_admin(user)
        if PaqueteService._is_admin(user):
            if not client.execute_select(paquete_queries.package_exists(paquete_id)):
                raise HTTPException(status_code=404, detail="Paquete no encontrado")
            return

        owner_uri = PaqueteService._require_owner(user)
        if not client.execute_select(paquete_queries.package_owned_by(paquete_id, owner_uri)):
            raise HTTPException(
                status_code=403,
                detail="No autorizado para modificar paquetes fuera de tu agencia/prestador",
            )

    @staticmethod
    def buscar_paquetes(
        busqueda: str,
        max_precio: int,
        orden: str,
        limit: int,
        offset: int,
    ):
        query = paquete_queries.list_packages(
            busqueda,
            max_precio,
            orden,
            limit,
            offset,
        )
        raw_results = client.execute_select(query)
        return [PaqueteService._parse_package_row(res) for res in raw_results]

    @staticmethod
    def listar_operador_paquetes(user, busqueda: str = "", limit: int = 100, offset: int = 0):
        PaqueteService._assert_operator_or_admin(user)
        owner_uri = None if PaqueteService._is_admin(user) else PaqueteService._require_owner(user)
        raw_results = client.execute_select(
            paquete_queries.list_packages_for_owner(owner_uri, busqueda, limit, offset)
        )
        return [PaqueteService._parse_package_row(res) for res in raw_results]

    @staticmethod
    def listar_propietarios(user):
        PaqueteService._assert_operator_or_admin(user)
        if not PaqueteService._is_admin(user):
            owner_uri = PaqueteService._require_owner(user)
            rows = client.execute_select(paquete_queries.owner_by_uri(owner_uri))
        else:
            rows = client.execute_select(paquete_queries.owners())
        return [
            PaqueteOwner(
                uri=row["owner"]["value"],
                nombre=row.get("ownerName", {}).get("value", row["owner"]["value"].split("#")[-1]),
            )
            for row in rows
        ]

    @staticmethod
    def listar_servicios_catalogo(user, limit: int = 300):
        PaqueteService._assert_operator_or_admin(user)
        rows = client.execute_select(paquete_queries.list_services_catalog(limit=limit))
        servicios = []
        seen = set()
        for row in rows:
            servicio_id = row.get("servicio", {}).get("value")
            nombre = row.get("servicioNombre", {}).get("value")
            if not servicio_id or not nombre:
                continue
            tipo = row.get("tipoLabel", {}).get("value")
            key = (servicio_id, nombre, tipo)
            if key in seen:
                continue
            seen.add(key)
            servicios.append(
                PaqueteServicioCatalogo(
                    id=servicio_id,
                    nombre=nombre,
                    tipo=tipo,
                )
            )
        return servicios

    @staticmethod
    def obtener_detalle(paquete_id: str):
        base_results = client.execute_select(paquete_queries.detail_base(paquete_id))
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
            agencia_uri=get_value(base, "agencia"),
            agencia_nombre=get_value(base, "agenciaNombre"),
            url_imagen=get_value(base, "imagen"),
            galeria_imagenes=get_value(base, "galeria"),
            estado_publicacion=get_value(base, "estadoPublicacion") or "publicado",
        )

        destinos_results = client.execute_select(paquete_queries.detail_destinations(paquete_id))
        destinos = []
        destinos_seen = set()
        for res in destinos_results:
            destino_id = get_value(res, "destino")
            nombre = get_value(res, "destinoNombre")
            if not nombre:
                continue
            municipio = get_value(res, "municipioNombre")
            lat_raw = get_value(res, "lat")
            lon_raw = get_value(res, "lon")
            categoria = get_value(res, "categoriaLabel")
            imagen = get_value(res, "imagen")
            galeria = get_value(res, "galeria")
            lat = float(lat_raw) if lat_raw else None
            lon = float(lon_raw) if lon_raw else None
            key = (destino_id, nombre, municipio, lat, lon, categoria, imagen, galeria)
            if key in destinos_seen:
                continue
            destinos_seen.add(key)
            destinos.append(
                PaqueteDetalleDestino(
                    id=destino_id,
                    nombre=nombre,
                    municipio=municipio,
                    latitud=lat,
                    longitud=lon,
                    categoria=categoria,
                    url_imagen=imagen,
                    galeria_imagenes=galeria,
                )
            )

        servicios_results = client.execute_select(paquete_queries.detail_services(paquete_id))
        servicios = []
        servicios_seen = set()
        for res in servicios_results:
            servicio_id = get_value(res, "servicio")
            nombre = get_value(res, "servicioNombre")
            if not nombre:
                continue
            tipo = get_value(res, "tipoLabel")
            key = (servicio_id, nombre, tipo)
            if key in servicios_seen:
                continue
            servicios_seen.add(key)
            servicios.append(
                PaqueteDetalleServicio(
                    id=servicio_id,
                    nombre=nombre,
                    tipo=tipo,
                )
            )

        itinerarios_results = client.execute_select(paquete_queries.detail_itineraries(paquete_id))
        itinerarios = []
        itinerarios_seen = set()
        for res in itinerarios_results:
            itinerary_id = get_value(res, "it")
            titulo = get_value(res, "titulo")
            descripcion = get_value(res, "descripcion")
            if not titulo and not descripcion:
                continue
            key = (itinerary_id, titulo, descripcion)
            if key in itinerarios_seen:
                continue
            itinerarios_seen.add(key)
            itinerarios.append(
                PaqueteDetalleItinerario(
                    id=itinerary_id,
                    titulo=titulo,
                    descripcion=descripcion,
                )
            )

        detalle.destinos = destinos or None
        detalle.servicios = servicios or None
        detalle.itinerarios = itinerarios or None

        return detalle

    @staticmethod
    def obtener_detalle_publico(paquete_id: str):
        detalle = PaqueteService.obtener_detalle(paquete_id)
        if detalle is None:
            return None
        if not PaqueteService._is_public_status(detalle.estado_publicacion):
            return None
        return detalle

    @staticmethod
    def obtener_detalle_operador(user, paquete_id: str):
        PaqueteService._assert_package_access(user, paquete_id)
        detalle = PaqueteService.obtener_detalle(paquete_id)
        if detalle is None:
            raise HTTPException(status_code=404, detail="Paquete no encontrado")
        return detalle

    @staticmethod
    def actualizar_operador_paquete(user, paquete_id: str, datos: PaqueteWrite):
        PaqueteService._assert_package_access(user, paquete_id)
        owner_uri = None
        if PaqueteService._is_admin(user) and datos.agencia_uri:
            owner_uri = datos.agencia_uri.strip()
            if not client.execute_select(paquete_queries.owner_by_uri(owner_uri)):
                raise HTTPException(status_code=400, detail="Agencia/prestador responsable no existe en ontologia")

        client.execute_sparql_update(paquete_queries.update_package(paquete_id, datos, owner_uri))
        detalle = PaqueteService.obtener_detalle(paquete_id)
        if detalle is None:
            raise HTTPException(status_code=404, detail="Paquete no encontrado")
        return detalle

    @staticmethod
    def crear_operador_paquete(user, datos: PaqueteWrite):
        PaqueteService._assert_operator_or_admin(user)
        if PaqueteService._is_admin(user):
            owner_uri = (datos.agencia_uri or "").strip() or PaqueteService._resolve_operator_owner_uri(user)
            if not owner_uri:
                raise HTTPException(status_code=400, detail="Selecciona una agencia/prestador responsable")
        else:
            owner_uri = PaqueteService._require_owner(user)

        if not client.execute_select(paquete_queries.owner_by_uri(owner_uri)):
            raise HTTPException(status_code=400, detail="Agencia/prestador responsable no existe en ontologia")

        local_id = f"panel-{uuid.uuid4().hex[:10]}"
        paquete_uri = f"{EX}paquete-{local_id}"
        precio_uri = f"{EX}precio-{local_id}"
        client.execute_sparql_update(
            paquete_queries.insert_package(paquete_uri, precio_uri, owner_uri, datos)
        )
        detalle = PaqueteService.obtener_detalle(paquete_uri)
        if detalle is None:
            raise HTTPException(status_code=500, detail="No se pudo crear el paquete")
        return detalle
