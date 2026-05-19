from sparql_builder import (
    PREFIXES,
    limit_value,
    literal,
    offset_value,
    resource,
)
from rdflib.namespace import XSD


def list_services_for_owner(
    owner_uri: str | None,
    busqueda: str,
    estado: str | None,
    tipo_uri: str | None,
    limit: int,
    offset: int,
) -> str:
    q = literal(busqueda or "")
    safe_limit = limit_value(limit, default=100, maximum=500)
    safe_offset = offset_value(offset)
    owner_filter = ""
    if owner_uri:
        owner_filter = f"VALUES ?ownerFiltro {{ {resource(owner_uri)} }}\n  ?ownerFiltro ex:ofreceServicio ?servicio ."

    estado_filter = ""
    clean_estado = (estado or "").strip().lower()
    if clean_estado and clean_estado != "todos":
        estado_filter = f'FILTER(LCASE(STR(COALESCE(?estadoPublicacion, "publicado"))) = {literal(clean_estado)})'

    tipo_values = ""
    tipo_filter = ""
    if (tipo_uri or "").strip():
        tipo_values = f"VALUES ?tipoFiltro {{ {resource(tipo_uri)} }}"
        tipo_filter = "FILTER(?tipo = ?tipoFiltro)"

    return f"""{PREFIXES}
SELECT DISTINCT ?servicio ?nombre ?descripcion ?tipo ?tipoNombre ?estadoPublicacion ?imagen ?agencia ?agenciaNombre
WHERE {{
  BIND({q} AS ?q)

  {owner_filter}
  {tipo_values}
  ?servicio rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
  ?servicio ex:nombre ?nombre .
  ?servicio ex:descripcion ?descripcion .

  OPTIONAL {{ ?servicio rdfs:label ?label . }}
  OPTIONAL {{ ?servicio ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?servicio ex:estadoPublicacion ?estadoPublicacion . }}

  OPTIONAL {{
    ?servicio rdf:type ?tipoRaw .
    ?tipoRaw rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipoRaw != ex:ServicioTuristico)
    BIND(?tipoRaw AS ?tipo)
    OPTIONAL {{ ?tipoRaw rdfs:label ?tipoLabel . }}
    BIND(COALESCE(?tipoLabel, STRAFTER(STR(?tipoRaw), "#")) AS ?tipoNombre)
  }}

  OPTIONAL {{
    ?agencia ex:ofreceServicio ?servicio .
    OPTIONAL {{ ?agencia rdfs:label ?agenciaLabel . }}
    OPTIONAL {{ ?agencia ex:nombre ?agenciaName . }}
    BIND(COALESCE(?agenciaLabel, ?agenciaName, STRAFTER(STR(?agencia), "#")) AS ?agenciaNombre)
  }}

  FILTER(
    ?q = "" ||
    CONTAINS(LCASE(STR(?nombre)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(?descripcion)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?tipoNombre, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?agenciaNombre, ""))), LCASE(?q))
  )

  {estado_filter}
  {tipo_filter}
}}
ORDER BY ?nombre
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def list_owner_service_ids(owner_uri: str) -> str:
    owner = resource(owner_uri)
    return f"""{PREFIXES}
SELECT DISTINCT ?servicio
WHERE {{
  {owner} ex:ofreceServicio ?servicio .
  ?servicio rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
}}
"""


def list_services_by_ids(
    servicio_ids: list[str],
    busqueda: str,
    estado: str | None,
    tipo_uri: str | None,
    limit: int,
    offset: int,
) -> str:
    q = literal(busqueda or "")
    safe_limit = limit_value(limit, default=100, maximum=500)
    safe_offset = offset_value(offset)
    values = " ".join(resource(servicio_id) for servicio_id in servicio_ids if servicio_id)
    if not values:
        values = "ex:__none__"

    estado_filter = ""
    clean_estado = (estado or "").strip().lower()
    if clean_estado and clean_estado != "todos":
        estado_filter = f'FILTER(LCASE(STR(COALESCE(?estadoPublicacion, "publicado"))) = {literal(clean_estado)})'

    tipo_values = ""
    tipo_filter = ""
    if (tipo_uri or "").strip():
        tipo_values = f"VALUES ?tipoFiltro {{ {resource(tipo_uri)} }}"
        tipo_filter = "FILTER(?tipo = ?tipoFiltro)"

    return f"""{PREFIXES}
SELECT DISTINCT ?servicio ?nombre ?descripcion ?tipo ?tipoNombre ?estadoPublicacion ?imagen ?agencia ?agenciaNombre
WHERE {{
  BIND({q} AS ?q)
  VALUES ?servicio {{ {values} }}
  {tipo_values}

  ?servicio rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
  ?servicio ex:nombre ?nombre .
  ?servicio ex:descripcion ?descripcion .

  OPTIONAL {{ ?servicio ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?servicio ex:estadoPublicacion ?estadoPublicacion . }}

  OPTIONAL {{
    ?servicio rdf:type ?tipoRaw .
    ?tipoRaw rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipoRaw != ex:ServicioTuristico)
    BIND(?tipoRaw AS ?tipo)
    OPTIONAL {{ ?tipoRaw rdfs:label ?tipoLabel . }}
    BIND(COALESCE(?tipoLabel, STRAFTER(STR(?tipoRaw), "#")) AS ?tipoNombre)
  }}

  OPTIONAL {{
    ?agencia ex:ofreceServicio ?servicio .
    OPTIONAL {{ ?agencia rdfs:label ?agenciaLabel . }}
    OPTIONAL {{ ?agencia ex:nombre ?agenciaName . }}
    BIND(COALESCE(?agenciaLabel, ?agenciaName, STRAFTER(STR(?agencia), "#")) AS ?agenciaNombre)
  }}

  FILTER(
    ?q = "" ||
    CONTAINS(LCASE(STR(?nombre)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(?descripcion)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?tipoNombre, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?agenciaNombre, ""))), LCASE(?q))
  )

  {estado_filter}
  {tipo_filter}
}}
ORDER BY ?nombre
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def service_exists(servicio_id: str) -> str:
    servicio = resource(servicio_id)
    return f"""{PREFIXES}
SELECT ?servicio
WHERE {{
  {servicio} rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
}}
LIMIT 1
"""


def service_owned_by(servicio_id: str, owner_uri: str) -> str:
    servicio = resource(servicio_id)
    owner = resource(owner_uri)
    return f"""{PREFIXES}
SELECT ?servicio
WHERE {{
  {owner} ex:ofreceServicio {servicio} .
}}
LIMIT 1
"""


def detail_service(servicio_id: str) -> str:
    servicio = resource(servicio_id)
    return f"""{PREFIXES}
SELECT DISTINCT ?servicio ?nombre ?descripcion ?tipo ?tipoNombre ?estadoPublicacion ?imagen ?agencia ?agenciaNombre
WHERE {{
  VALUES ?servicio {{ {servicio} }}
  ?servicio rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
  ?servicio ex:nombre ?nombre .
  ?servicio ex:descripcion ?descripcion .

  OPTIONAL {{ ?servicio ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?servicio ex:estadoPublicacion ?estadoPublicacion . }}

  OPTIONAL {{
    ?servicio rdf:type ?tipoRaw .
    ?tipoRaw rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipoRaw != ex:ServicioTuristico)
    BIND(?tipoRaw AS ?tipo)
    OPTIONAL {{ ?tipoRaw rdfs:label ?tipoLabel . }}
    BIND(COALESCE(?tipoLabel, STRAFTER(STR(?tipoRaw), "#")) AS ?tipoNombre)
  }}

  OPTIONAL {{
    ?agencia ex:ofreceServicio ?servicio .
    OPTIONAL {{ ?agencia rdfs:label ?agenciaLabel . }}
    OPTIONAL {{ ?agencia ex:nombre ?agenciaName . }}
    BIND(COALESCE(?agenciaLabel, ?agenciaName, STRAFTER(STR(?agencia), "#")) AS ?agenciaNombre)
  }}

}}
LIMIT 1
"""


def list_service_types() -> str:
    return f"""{PREFIXES}
SELECT DISTINCT ?tipo ?tipoNombre
WHERE {{
  ?tipo rdfs:subClassOf* ex:ServicioTuristico .
  FILTER(?tipo != ex:ServicioTuristico)
  OPTIONAL {{ ?tipo rdfs:label ?tipoLabel . }}
  BIND(COALESCE(?tipoLabel, STRAFTER(STR(?tipo), "#")) AS ?tipoNombre)
}}
ORDER BY ?tipoNombre
"""


def service_usage_count(servicio_id: str) -> str:
    servicio = resource(servicio_id)
    return f"""{PREFIXES}
SELECT (COUNT(DISTINCT ?paquete) AS ?total)
WHERE {{
  OPTIONAL {{ ?paquete ex:incluyeServicio {servicio} . }}
}}
"""


def service_usage_counts(servicio_ids: list[str]) -> str:
    values = " ".join(resource(servicio_id) for servicio_id in servicio_ids if servicio_id)
    if not values:
        return f"""{PREFIXES}
SELECT ?servicio (0 AS ?total)
WHERE {{
  VALUES ?servicio {{ ex:__none__ }}
}}
LIMIT 0
"""

    return f"""{PREFIXES}
SELECT ?servicio (COUNT(DISTINCT ?paquete) AS ?total)
WHERE {{
  VALUES ?servicio {{ {values} }}
  OPTIONAL {{ ?paquete ex:incluyeServicio ?servicio . }}
}}
GROUP BY ?servicio
"""


def insert_service(servicio_uri: str, owner_uri: str, data) -> str:
    servicio = resource(servicio_uri)
    owner = resource(owner_uri)
    estado = (getattr(data, "estado_publicacion", None) or "publicado").strip().lower()
    tipo_uri = (getattr(data, "tipo_uri", None) or "").strip()
    tipo_line = f"  {servicio} rdf:type {resource(tipo_uri)} .\n" if tipo_uri else ""
    imagen = (getattr(data, "url_imagen", None) or "").strip()
    imagen_line = f"  {servicio} ex:urlImagen {literal(imagen, datatype=XSD.anyURI)} .\n" if imagen else ""

    return f"""{PREFIXES}
INSERT DATA {{
  {servicio} rdf:type ex:ServicioTuristico ;
             rdfs:label {literal(data.nombre, lang="es")} ;
             ex:nombre {literal(data.nombre)} ;
             ex:descripcion {literal(data.descripcion)} ;
             ex:estadoPublicacion {literal(estado)} .
{tipo_line}{imagen_line}  {owner} ex:ofreceServicio {servicio} .
}}
"""


def update_service(servicio_id: str, data, owner_uri: str | None = None) -> str:
    servicio = resource(servicio_id)
    owner = resource(owner_uri) if owner_uri else None
    estado = (getattr(data, "estado_publicacion", None) or "publicado").strip().lower()
    tipo_uri = (getattr(data, "tipo_uri", None) or "").strip()
    tipo_line = f"  {servicio} rdf:type {resource(tipo_uri)} .\n" if tipo_uri else ""
    imagen = (getattr(data, "url_imagen", None) or "").strip()
    imagen_line = f"  {servicio} ex:urlImagen {literal(imagen, datatype=XSD.anyURI)} .\n" if imagen else ""
    owner_delete = f"  ?oldOwner ex:ofreceServicio {servicio} .\n" if owner else ""
    owner_insert = f"  {owner} ex:ofreceServicio {servicio} .\n" if owner else ""
    owner_where = f"  OPTIONAL {{ ?oldOwner ex:ofreceServicio {servicio} . }}\n" if owner else ""

    return f"""{PREFIXES}
DELETE {{
  {servicio} rdfs:label ?oldLabel .
  {servicio} ex:nombre ?oldNombre .
  {servicio} ex:descripcion ?oldDescripcion .
  {servicio} ex:estadoPublicacion ?oldEstado .
  {servicio} ex:urlImagen ?oldImagen .
  {servicio} rdf:type ?oldSpecificType .
{owner_delete}}}
INSERT {{
  {servicio} rdfs:label {literal(data.nombre, lang="es")} .
  {servicio} ex:nombre {literal(data.nombre)} .
  {servicio} ex:descripcion {literal(data.descripcion)} .
  {servicio} ex:estadoPublicacion {literal(estado)} .
{tipo_line}{imagen_line}{owner_insert}}}
WHERE {{
  {servicio} rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
  OPTIONAL {{ {servicio} rdfs:label ?oldLabel . }}
  OPTIONAL {{ {servicio} ex:nombre ?oldNombre . }}
  OPTIONAL {{ {servicio} ex:descripcion ?oldDescripcion . }}
  OPTIONAL {{ {servicio} ex:estadoPublicacion ?oldEstado . }}
  OPTIONAL {{ {servicio} ex:urlImagen ?oldImagen . }}
  OPTIONAL {{
    {servicio} rdf:type ?oldSpecificType .
    ?oldSpecificType rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?oldSpecificType != ex:ServicioTuristico)
  }}
{owner_where}}}
"""


def delete_service(servicio_id: str) -> str:
    servicio = resource(servicio_id)
    return f"""{PREFIXES}
DELETE {{
  {servicio} rdf:type ?type .
  {servicio} rdfs:label ?label .
  {servicio} ex:nombre ?nombre .
  {servicio} ex:descripcion ?descripcion .
  {servicio} ex:estadoPublicacion ?estado .
  {servicio} ex:urlImagen ?imagen .
  ?owner ex:ofreceServicio {servicio} .
}}
WHERE {{
  {servicio} rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
  OPTIONAL {{ {servicio} rdf:type ?type . }}
  OPTIONAL {{ {servicio} rdfs:label ?label . }}
  OPTIONAL {{ {servicio} ex:nombre ?nombre . }}
  OPTIONAL {{ {servicio} ex:descripcion ?descripcion . }}
  OPTIONAL {{ {servicio} ex:estadoPublicacion ?estado . }}
  OPTIONAL {{ {servicio} ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?owner ex:ofreceServicio {servicio} . }}
}}
"""
