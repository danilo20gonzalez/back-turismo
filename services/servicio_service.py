import uuid

from fastapi import HTTPException

from core.roles import is_admin, is_operator_or_admin
from sparql_builder import EX
from sparql_client import SparqlClient
from sparql_queries import paquetes as paquete_queries
from sparql_queries import servicios as servicio_queries
from schemas.paquete import PaqueteOwner
from schemas.servicio import Servicio, ServicioTipo, ServicioWrite


client = SparqlClient()


class ServicioService:
    @staticmethod
    def _assert_operator_or_admin(user):
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        if not is_operator_or_admin(role_name):
            raise HTTPException(status_code=403, detail="No autorizado para gestion de servicios")

    @staticmethod
    def _is_admin(user) -> bool:
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        return is_admin(role_name)

    @staticmethod
    def _resolve_operator_owner_uri(user) -> str | None:
        return (getattr(user, "agencia_uri", None) or "").strip() or None

    @staticmethod
    def _require_owner(user) -> str:
        owner_uri = ServicioService._resolve_operator_owner_uri(user)
        if not owner_uri:
            raise HTTPException(
                status_code=400,
                detail="El usuario operador no tiene agencia/prestador vinculado en ontologia",
            )
        return owner_uri

    @staticmethod
    def _parse_service_row(row) -> Servicio:
        return Servicio(
            id=row["servicio"]["value"],
            nombre=row["nombre"]["value"],
            descripcion=row["descripcion"]["value"],
            tipo_uri=row.get("tipo", {}).get("value"),
            tipo_nombre=row.get("tipoNombre", {}).get("value"),
            estado_publicacion=row.get("estadoPublicacion", {}).get("value") or "publicado",
            url_imagen=row.get("imagen", {}).get("value"),
            agencia_uri=row.get("agencia", {}).get("value"),
            agencia_nombre=row.get("agenciaNombre", {}).get("value"),
            paquetes_vinculados=int(row.get("paquetesVinculados", {}).get("value", 0)),
        )

    @staticmethod
    def _usage_map(servicio_ids: list[str]) -> dict[str, int]:
        if not servicio_ids:
            return {}
        rows = client.execute_select(servicio_queries.service_usage_counts(servicio_ids))
        usage: dict[str, int] = {}
        for row in rows:
            servicio_uri = row.get("servicio", {}).get("value")
            if not servicio_uri:
                continue
            usage[servicio_uri] = int(row.get("total", {}).get("value", 0))
        return usage

    @staticmethod
    def _assert_service_access(user, servicio_id: str):
        ServicioService._assert_operator_or_admin(user)
        if ServicioService._is_admin(user):
            if not client.execute_select(servicio_queries.service_exists(servicio_id)):
                raise HTTPException(status_code=404, detail="Servicio no encontrado")
            return

        owner_uri = ServicioService._require_owner(user)
        if not client.execute_select(servicio_queries.service_owned_by(servicio_id, owner_uri)):
            raise HTTPException(
                status_code=403,
                detail="No autorizado para modificar servicios fuera de tu agencia/prestador",
            )

    @staticmethod
    def listar_servicios(
        user,
        busqueda: str = "",
        estado: str | None = None,
        tipo_uri: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        ServicioService._assert_operator_or_admin(user)
        owner_uri = None if ServicioService._is_admin(user) else ServicioService._require_owner(user)

        if owner_uri:
            owner_rows = client.execute_select(servicio_queries.list_owner_service_ids(owner_uri))
            owner_service_ids = [row["servicio"]["value"] for row in owner_rows if row.get("servicio")]
            if not owner_service_ids:
                return []
            rows = client.execute_select(
                servicio_queries.list_services_by_ids(
                    servicio_ids=owner_service_ids,
                    busqueda=busqueda,
                    estado=estado,
                    tipo_uri=tipo_uri,
                    limit=limit,
                    offset=offset,
                )
            )
        else:
            rows = client.execute_select(
                servicio_queries.list_services_for_owner(
                    owner_uri=None,
                    busqueda=busqueda,
                    estado=estado,
                    tipo_uri=tipo_uri,
                    limit=limit,
                    offset=offset,
                )
            )

        servicios = [ServicioService._parse_service_row(row) for row in rows]
        usage = ServicioService._usage_map([servicio.id for servicio in servicios])
        for servicio in servicios:
            servicio.paquetes_vinculados = usage.get(servicio.id, 0)
        return servicios

    @staticmethod
    def listar_tipos_servicio(user):
        ServicioService._assert_operator_or_admin(user)
        rows = client.execute_select(servicio_queries.list_service_types())
        return [
            ServicioTipo(
                uri=row["tipo"]["value"],
                nombre=row.get("tipoNombre", {}).get("value", row["tipo"]["value"].split("#")[-1]),
            )
            for row in rows
        ]

    @staticmethod
    def listar_propietarios(user):
        ServicioService._assert_operator_or_admin(user)
        if not ServicioService._is_admin(user):
            owner_uri = ServicioService._require_owner(user)
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
    def obtener_detalle(user, servicio_id: str):
        ServicioService._assert_service_access(user, servicio_id)
        rows = client.execute_select(servicio_queries.detail_service(servicio_id))
        if not rows:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        servicio = ServicioService._parse_service_row(rows[0])
        usage_rows = client.execute_select(servicio_queries.service_usage_count(servicio_id))
        servicio.paquetes_vinculados = int(usage_rows[0].get("total", {}).get("value", 0)) if usage_rows else 0
        return servicio

    @staticmethod
    def crear_servicio(user, datos: ServicioWrite):
        ServicioService._assert_operator_or_admin(user)
        if ServicioService._is_admin(user):
            owner_uri = (datos.agencia_uri or "").strip() or ServicioService._resolve_operator_owner_uri(user)
            if not owner_uri:
                raise HTTPException(status_code=400, detail="Selecciona una agencia/prestador responsable")
        else:
            owner_uri = ServicioService._require_owner(user)

        if not client.execute_select(paquete_queries.owner_by_uri(owner_uri)):
            raise HTTPException(status_code=400, detail="Agencia/prestador responsable no existe en ontologia")

        local_id = f"servicio-panel-{uuid.uuid4().hex[:10]}"
        servicio_uri = f"{EX}{local_id}"
        client.execute_sparql_update(servicio_queries.insert_service(servicio_uri, owner_uri, datos))
        rows = client.execute_select(servicio_queries.detail_service(servicio_uri))
        if not rows:
            raise HTTPException(status_code=500, detail="No se pudo crear el servicio")
        return ServicioService._parse_service_row(rows[0])

    @staticmethod
    def actualizar_servicio(user, servicio_id: str, datos: ServicioWrite):
        ServicioService._assert_service_access(user, servicio_id)
        owner_uri = None
        if ServicioService._is_admin(user) and datos.agencia_uri:
            owner_uri = datos.agencia_uri.strip()
            if not client.execute_select(paquete_queries.owner_by_uri(owner_uri)):
                raise HTTPException(status_code=400, detail="Agencia/prestador responsable no existe en ontologia")

        client.execute_sparql_update(servicio_queries.update_service(servicio_id, datos, owner_uri))
        rows = client.execute_select(servicio_queries.detail_service(servicio_id))
        if not rows:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        return ServicioService._parse_service_row(rows[0])

    @staticmethod
    def eliminar_servicio(user, servicio_id: str):
        ServicioService._assert_service_access(user, servicio_id)
        usage_rows = client.execute_select(servicio_queries.service_usage_count(servicio_id))
        used_by = int(usage_rows[0].get("total", {}).get("value", 0)) if usage_rows else 0
        if used_by > 0:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede eliminar: el servicio esta vinculado a {used_by} paquete(s)",
            )
        client.execute_sparql_update(servicio_queries.delete_service(servicio_id))
        return {"ok": True}
