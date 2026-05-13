from datetime import datetime

from sparql_builder import (
    EX,
    PREFIXES,
    bool_literal,
    class_resource,
    datetime_literal,
    literal,
    local_resource,
    local_resource_uri,
    normalize_lookup,
    resource,
)


ROLE_MAP = {
    "turista": ("Turista", "rol-turista", "RolTurista", "Turista"),
    "operador": ("AgenciaViajes", "rol-prestador", "RolPrestador", "Prestador de servicio"),
    "prestador": ("PrestadorServicio", "rol-prestador", "RolPrestador", "Prestador"),
    "prestador servicio": ("PrestadorServicio", "rol-prestador", "RolPrestador", "Prestador"),
    "prestador de servicio": ("PrestadorServicio", "rol-prestador", "RolPrestador", "Prestador"),
    "prestador de servicios": ("PrestadorServicio", "rol-prestador", "RolPrestador", "Prestador"),
    "agencia": ("AgenciaViajes", "rol-prestador", "RolPrestador", "Agencia de viajes"),
    "agencia de viajes": ("AgenciaViajes", "rol-prestador", "RolPrestador", "Agencia de viajes"),
    "comunidad": ("Comunidad", "rol-comunidad", "RolComunidad", "Comunidad"),
    "admin": ("Usuario", "rol-admin-general", "RolAdminGeneral", "Administrador"),
    "administrador": ("Usuario", "rol-admin-general", "RolAdminGeneral", "Administrador"),
    "administrador general": ("Usuario", "rol-admin-general", "RolAdminGeneral", "Administrador"),
}


def role_metadata(role_name: str | None) -> tuple[str, str, str, str]:
    return ROLE_MAP.get(normalize_lookup(role_name), ROLE_MAP["turista"])


def user_local_id(role_name: str | None, user_id: int | str) -> str:
    user_class, _, _, _ = role_metadata(role_name)
    return f"{user_class}_{user_id}"


def user_uri(role_name: str | None, user_id: int | str) -> str:
    return local_resource_uri(user_local_id(role_name, user_id))


def insert_user(
    user_id: str,
    role_name: str,
    nombre: str,
    email: str,
    password_hash: str,
    fecha_actual: datetime | str | None = None,
) -> str:
    user = local_resource(user_id)
    user_class, role_id, role_class, role_label = role_metadata(role_name)
    role = local_resource(role_id)
    fecha = fecha_actual or datetime.utcnow()
    type_objects = "ex:Usuario"
    if user_class != "Usuario":
        type_objects = f"{type_objects}, {class_resource(user_class)}"

    return f"""{PREFIXES}
INSERT DATA {{
  {role} rdf:type {class_resource(role_class)} ;
         rdfs:label {literal(role_label, lang="es")} ;
         ex:nombre {literal(role_label)} .

  {user} rdf:type {type_objects} ;
         rdfs:label {literal(nombre, lang="es")} ;
         ex:nombre {literal(nombre)} ;
         ex:nombreCompleto {literal(nombre)} ;
         ex:email {literal(email)} ;
         ex:contrasenaHash {literal(password_hash)} ;
         ex:passwordHash {literal(password_hash)} ;
         ex:suscripcionActiva {bool_literal(True)} ;
         ex:fechaRegistro {datetime_literal(fecha)} ;
         ex:tieneRol {role} .
}}
"""


def update_profile(user_uri_value: str, location: str, avatar: str) -> str:
    user = resource(user_uri_value)
    return f"""{PREFIXES}
DELETE {{
  {user} ex:viveEn ?oldLocation .
  {user} ex:tieneAvatar ?oldAvatar .
}}
INSERT {{
  {user} ex:viveEn {literal(location or "")} .
  {user} ex:tieneAvatar {literal(avatar or "https://www.gravatar.com/avatar/000?d=mp")} .
}}
WHERE {{
  OPTIONAL {{ {user} ex:viveEn ?oldLocation . }}
  OPTIONAL {{ {user} ex:tieneAvatar ?oldAvatar . }}
}}
"""


def resolve_user_uri(db_user) -> str:
    existing = getattr(db_user, "uri_ontologia", None)
    if existing:
        return existing
    role = getattr(getattr(db_user, "rol", None), "nombre", None)
    return f"{EX}{user_local_id(role, getattr(db_user, 'id'))}"


def owner_uri_by_email(email: str) -> str:
    return f"""{PREFIXES}
SELECT ?owner
WHERE {{
  ?owner rdf:type ?ownerType ;
         ex:email {literal(email)} .
  FILTER(?ownerType IN (ex:AgenciaViajes, ex:PrestadorServicio))
}}
LIMIT 1
"""


def owner_uri_by_uri(user_uri_value: str) -> str:
    user = resource(user_uri_value)
    return f"""{PREFIXES}
SELECT ?owner
WHERE {{
  VALUES ?owner {{ {user} }}
  ?owner rdf:type ?ownerType .
  FILTER(?ownerType IN (ex:AgenciaViajes, ex:PrestadorServicio))
}}
LIMIT 1
"""
