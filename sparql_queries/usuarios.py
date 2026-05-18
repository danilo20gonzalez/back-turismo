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


def profile_summary(user_uri_value: str) -> str:
    user = resource(user_uri_value)
    return f"""{PREFIXES}
SELECT ?nombre ?location ?avatar ?bio ?fechaRegistro
WHERE {{
  VALUES ?user {{ {user} }}
  OPTIONAL {{ ?user ex:nombreCompleto ?nombreCompleto . }}
  OPTIONAL {{ ?user ex:nombre ?nombreSimple . }}
  OPTIONAL {{ ?user rdfs:label ?label . }}
  OPTIONAL {{ ?user ex:viveEn ?location . }}
  OPTIONAL {{ ?user ex:tieneAvatar ?avatar . }}
  OPTIONAL {{ ?user ex:descripcion ?bio . }}
  OPTIONAL {{ ?user ex:fechaRegistro ?fechaRegistro . }}
  BIND(COALESCE(?nombreCompleto, ?nombreSimple, ?label) AS ?nombre)
}}
LIMIT 1
"""


def update_profile(user_uri_value: str, name: str, location: str, bio: str) -> str:
    user = resource(user_uri_value)
    return f"""{PREFIXES}
DELETE {{
  {user} ex:viveEn ?oldLocation .
  {user} ex:nombreCompleto ?oldFullName .
  {user} ex:nombre ?oldName .
  {user} rdfs:label ?oldLabel .
  {user} ex:descripcion ?oldBio .
}}
INSERT {{
  {user} ex:viveEn {literal(location or "")} .
  {user} ex:nombreCompleto {literal(name or "")} .
  {user} ex:nombre {literal(name or "")} .
  {user} rdfs:label {literal(name or "", lang="es")} .
  {user} ex:descripcion {literal(bio or "")} .
}}
WHERE {{
  OPTIONAL {{ {user} ex:viveEn ?oldLocation . }}
  OPTIONAL {{ {user} ex:nombreCompleto ?oldFullName . }}
  OPTIONAL {{ {user} ex:nombre ?oldName . }}
  OPTIONAL {{ {user} rdfs:label ?oldLabel . }}
  OPTIONAL {{ {user} ex:descripcion ?oldBio . }}
}}
"""


def update_password_hash(user_uri_value: str, password_hash: str) -> str:
    user = resource(user_uri_value)
    return f"""{PREFIXES}
DELETE {{
  {user} ex:contrasenaHash ?oldContrasenaHash .
  {user} ex:passwordHash ?oldPasswordHash .
}}
INSERT {{
  {user} ex:contrasenaHash {literal(password_hash)} .
  {user} ex:passwordHash {literal(password_hash)} .
}}
WHERE {{
  OPTIONAL {{ {user} ex:contrasenaHash ?oldContrasenaHash . }}
  OPTIONAL {{ {user} ex:passwordHash ?oldPasswordHash . }}
}}
"""


def favorite_package_ids(user_uri_value: str) -> str:
    user = resource(user_uri_value)
    return f"""{PREFIXES}
SELECT DISTINCT ?paquete
WHERE {{
  VALUES ?user {{ {user} }}
  ?user ex:tieneFavorito ?paquete .
}}
ORDER BY ?paquete
"""


def favorite_packages(package_ids: list[str]) -> str:
    package_values = " ".join(resource(package_id) for package_id in package_ids)
    return f"""{PREFIXES}
SELECT ?paquete ?nombre ?descripcion ?precio ?dirigidoA ?duracion ?dificultad ?capacidad
       ?imagen ?galeria ?destinoLabel ?municipioLabel ?categoriaLabel
WHERE {{
  VALUES ?paquete {{ {package_values} }}
  ?paquete rdf:type/rdfs:subClassOf* ex:PaqueteTuristico ;
           ex:nombre ?nombre ;
           ex:descripcion ?descripcion ;
           ex:tienePrecio ?precioSpec .
  ?precioSpec ex:precioPorPersona ?precio .

  OPTIONAL {{ ?paquete ex:duracionDias ?duracion . }}
  OPTIONAL {{ ?paquete ex:capacidadMaxPersonas ?capacidad . }}
  OPTIONAL {{ ?paquete ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?paquete ex:galeriaImagenes ?galeria . }}

  OPTIONAL {{
    ?paquete ex:dirigidoA ?dirigido .
    OPTIONAL {{ ?dirigido rdfs:label ?dirigidoLabel . }}
    BIND(COALESCE(?dirigidoLabel, STRAFTER(STR(?dirigido), "#")) AS ?dirigidoA)
  }}

  OPTIONAL {{
    ?paquete ex:tieneDificultad ?dif .
    OPTIONAL {{ ?dif rdfs:label ?difLabel . }}
    BIND(COALESCE(?difLabel, STRAFTER(STR(?dif), "#"), STR(?dif)) AS ?dificultad)
  }}

  OPTIONAL {{
    ?paquete ex:visitaDestino ?destino .
    OPTIONAL {{ ?destino rdfs:label ?destinoLabelRaw . }}
    OPTIONAL {{ ?destino ex:nombre ?destinoNombreRaw . }}
    BIND(COALESCE(?destinoLabelRaw, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoLabel)

    OPTIONAL {{
      ?destino ex:ubicadoEn ?municipio .
      OPTIONAL {{ ?municipio rdfs:label ?municipioLabelRaw . }}
      OPTIONAL {{ ?municipio ex:nombre ?municipioNombreRaw . }}
      BIND(COALESCE(?municipioLabelRaw, ?municipioNombreRaw, STRAFTER(STR(?municipio), "#")) AS ?municipioLabel)
    }}

    OPTIONAL {{
      ?destino rdf:type ?categoria .
      ?categoria rdfs:subClassOf* ex:DestinoTuristico .
      FILTER(?categoria != ex:DestinoTuristico)
      OPTIONAL {{ ?categoria rdfs:label ?categoriaLabelRaw . }}
      BIND(COALESCE(?categoriaLabelRaw, STRAFTER(STR(?categoria), "#")) AS ?categoriaLabel)
    }}
  }}

  OPTIONAL {{
    ?reserva rdf:type/rdfs:subClassOf* ex:Reserva ;
             ex:reservaPaquete ?paquete .
  }}
}}
ORDER BY ?nombre
"""


def add_favorite(user_uri_value: str, paquete_id: str) -> str:
    user = resource(user_uri_value)
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
INSERT {{
  {user} ex:tieneFavorito {paquete} .
}}
WHERE {{
  {paquete} rdf:type/rdfs:subClassOf* ex:PaqueteTuristico .
  FILTER NOT EXISTS {{ {user} ex:tieneFavorito {paquete} . }}
}}
"""


def remove_favorite(user_uri_value: str, paquete_id: str) -> str:
    user = resource(user_uri_value)
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
DELETE WHERE {{
  {user} ex:tieneFavorito {paquete} .
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
