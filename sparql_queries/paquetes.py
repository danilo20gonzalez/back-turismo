import re

from sparql_builder import (
    EX,
    PREFIXES,
    decimal_value,
    int_value,
    limit_value,
    literal,
    local_resource,
    offset_value,
    order_by,
    resource,
)
from rdflib.namespace import XSD


DIFFICULTY_LOCAL_IDS = {
    "facil": ("nivel-facil", "Fácil"),
    "fácil": ("nivel-facil", "Fácil"),
    "moderado": ("nivel-moderado", "Moderado"),
    "dificil": ("nivel-dificil", "Difícil"),
    "difícil": ("nivel-dificil", "Difícil"),
    "desafiante": ("nivel-dificil", "Difícil"),
    "extremo": ("nivel-extremo", "Extremo"),
}


def _package_projection() -> str:
    return """?paquete ?nombre ?descripcion ?precio ?dirigidoA ?duracion ?dificultad ?capacidad
  ?imagen ?galeria ?agencia ?agenciaNombre ?estadoPublicacion
  (COUNT(DISTINCT ?reserva) AS ?popularidad)
  (GROUP_CONCAT(DISTINCT ?destinoLabel; separator=" | ") AS ?destinos)
  (GROUP_CONCAT(DISTINCT ?municipioLabel; separator=" | ") AS ?municipios)
  (GROUP_CONCAT(DISTINCT ?categoriaLabel; separator=" | ") AS ?categorias)"""


def _package_core() -> str:
    return """?paquete rdf:type/rdfs:subClassOf* ex:PaqueteTuristico .
  ?paquete ex:nombre ?nombre .
  ?paquete ex:descripcion ?descripcion .
  ?paquete ex:tienePrecio ?precioSpec .
  ?precioSpec ex:precioPorPersona ?precio .

  OPTIONAL { ?paquete ex:duracionDias ?duracion . }
  OPTIONAL { ?paquete ex:capacidadMaxPersonas ?capacidad . }
  OPTIONAL { ?paquete ex:urlImagen ?imagen . }
  OPTIONAL { ?paquete ex:galeriaImagenes ?galeria . }
  OPTIONAL { ?paquete ex:estadoPublicacion ?estadoPublicacion . }

  OPTIONAL {
    ?agencia ex:armaPaqueteModificado ?paquete .
    OPTIONAL { ?agencia rdfs:label ?agenciaLabel . }
    OPTIONAL { ?agencia ex:nombre ?agenciaName . }
    BIND(COALESCE(?agenciaLabel, ?agenciaName, STRAFTER(STR(?agencia), "#")) AS ?agenciaNombre)
  }

  OPTIONAL {
    ?paquete ex:dirigidoA ?dirigido .
    OPTIONAL { ?dirigido rdfs:label ?dirigidoLabel . }
    BIND(COALESCE(?dirigidoLabel, STRAFTER(STR(?dirigido), "#")) AS ?dirigidoA)
  }

  OPTIONAL {
    ?paquete ex:tieneDificultad ?dif .
    OPTIONAL { ?dif rdfs:label ?difLabel . }
    BIND(COALESCE(?difLabel, STRAFTER(STR(?dif), "#"), STR(?dif)) AS ?dificultad)
  }

  OPTIONAL {
    ?paquete ex:visitaDestino ?destino .
    OPTIONAL { ?destino rdfs:label ?destinoLabelRaw . }
    OPTIONAL { ?destino ex:nombre ?destinoNombreRaw . }
    BIND(COALESCE(?destinoLabelRaw, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoLabel)

    OPTIONAL {
      ?destino ex:ubicadoEn ?municipio .
      OPTIONAL { ?municipio rdfs:label ?municipioLabelRaw . }
      OPTIONAL { ?municipio ex:nombre ?municipioNombreRaw . }
      BIND(COALESCE(?municipioLabelRaw, ?municipioNombreRaw, STRAFTER(STR(?municipio), "#")) AS ?municipioLabel)
    }

    OPTIONAL {
      ?destino rdf:type ?categoria .
      ?categoria rdfs:subClassOf* ex:DestinoTuristico .
      FILTER(?categoria != ex:DestinoTuristico)
      OPTIONAL { ?categoria rdfs:label ?categoriaLabelRaw . }
      BIND(COALESCE(?categoriaLabelRaw, STRAFTER(STR(?categoria), "#")) AS ?categoriaLabel)
    }
  }

  OPTIONAL {
    ?reserva rdf:type/rdfs:subClassOf* ex:Reserva ;
             ex:reservaPaquete ?paquete .
  }"""


def _package_group_by() -> str:
    return "?paquete ?nombre ?descripcion ?precio ?dirigidoA ?duracion ?dificultad ?capacidad ?imagen ?galeria ?agencia ?agenciaNombre ?estadoPublicacion"


def _public_status_filter() -> str:
    return 'FILTER(LCASE(STR(COALESCE(?estadoPublicacion, "publicado"))) = "publicado")'


def list_packages(
    busqueda: str,
    max_precio: int,
    orden: str,
    limit: int,
    offset: int,
) -> str:
    q = literal(busqueda or "")
    price = decimal_value(max_precio, default=1_000_000, minimum=0)
    safe_limit = limit_value(limit, default=50)
    safe_offset = offset_value(offset)
    order_clause = order_by(
        orden,
        {
            "popularidad": "DESC(?popularidad)",
            "nombre": "?nombre",
            "precio": "ASC(?precio)",
        },
        "nombre",
    )

    return f"""{PREFIXES}
SELECT
  {_package_projection()}
WHERE {{
  BIND({q} AS ?q)

  {_package_core()}

  {_public_status_filter()}
  FILTER(?precio <= {price})
  FILTER(
    ?q = "" ||
    CONTAINS(LCASE(STR(?descripcion)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(?nombre)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?destinoLabel, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?municipioLabel, ""))), LCASE(?q))
  )
}}
GROUP BY {_package_group_by()}
ORDER BY {order_clause} ?nombre
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def list_packages_for_owner(
    owner_uri: str | None,
    busqueda: str,
    limit: int,
    offset: int,
) -> str:
    q = literal(busqueda or "")
    safe_limit = limit_value(limit, default=100, maximum=500)
    safe_offset = offset_value(offset)
    owner_filter = ""
    if owner_uri:
        owner_filter = f"VALUES ?ownerFiltro {{ {resource(owner_uri)} }}\n  ?ownerFiltro ex:armaPaqueteModificado ?paquete ."

    return f"""{PREFIXES}
SELECT
  {_package_projection()}
WHERE {{
  BIND({q} AS ?q)

  {owner_filter}
  {_package_core()}

  FILTER(
    ?q = "" ||
    CONTAINS(LCASE(STR(?descripcion)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(?nombre)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?destinoLabel, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?municipioLabel, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?agenciaNombre, ""))), LCASE(?q))
  )
}}
GROUP BY {_package_group_by()}
ORDER BY ?nombre
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def package_exists(paquete_id: str) -> str:
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
SELECT ?paquete
WHERE {{
  {paquete} rdf:type/rdfs:subClassOf* ex:PaqueteTuristico .
}}
LIMIT 1
"""


def package_owned_by(paquete_id: str, owner_uri: str) -> str:
    paquete = resource(paquete_id)
    owner = resource(owner_uri)
    return f"""{PREFIXES}
SELECT ?paquete
WHERE {{
  {owner} ex:armaPaqueteModificado {paquete} .
}}
LIMIT 1
"""


def owners() -> str:
    return f"""{PREFIXES}
SELECT DISTINCT ?owner ?ownerName
WHERE {{
  ?owner rdf:type ?ownerType .
  FILTER(?ownerType IN (ex:AgenciaViajes, ex:PrestadorServicio))
  OPTIONAL {{ ?owner rdfs:label ?label . }}
  OPTIONAL {{ ?owner ex:nombre ?name . }}
  BIND(COALESCE(?label, ?name, STRAFTER(STR(?owner), "#")) AS ?ownerName)
}}
ORDER BY ?ownerName
"""


def owner_by_uri(owner_uri: str) -> str:
    owner = resource(owner_uri)
    return f"""{PREFIXES}
SELECT ?owner ?ownerName
WHERE {{
  VALUES ?owner {{ {owner} }}
  ?owner rdf:type ?ownerType .
  FILTER(?ownerType IN (ex:AgenciaViajes, ex:PrestadorServicio))
  OPTIONAL {{ ?owner rdfs:label ?label . }}
  OPTIONAL {{ ?owner ex:nombre ?name . }}
  BIND(COALESCE(?label, ?name, STRAFTER(STR(?owner), "#")) AS ?ownerName)
}}
LIMIT 1
"""


def list_services_catalog(limit: int = 300) -> str:
    safe_limit = limit_value(limit, default=300, maximum=1000)
    return f"""{PREFIXES}
SELECT ?servicio ?servicioNombre (SAMPLE(?tipoLabelCandidate) AS ?tipoLabel)
WHERE {{
  ?servicio rdf:type/rdfs:subClassOf* ex:ServicioTuristico .

  OPTIONAL {{ ?servicio rdfs:label ?servicioLabel . }}
  OPTIONAL {{ ?servicio ex:nombre ?servicioNombreRaw . }}
  BIND(COALESCE(?servicioLabel, ?servicioNombreRaw, STRAFTER(STR(?servicio), "#")) AS ?servicioNombre)

  OPTIONAL {{
    ?servicio rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipo != ex:ServicioTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabelRaw . }}
    BIND(COALESCE(?tipoLabelRaw, STRAFTER(STR(?tipo), "#")) AS ?tipoLabelCandidate)
  }}
}}
GROUP BY ?servicio ?servicioNombre
ORDER BY ?servicioNombre
LIMIT {safe_limit}
"""


def _difficulty_resource(value: str | None) -> tuple[str, str]:
    key = (value or "moderado").strip().lower()
    return DIFFICULTY_LOCAL_IDS.get(key, DIFFICULTY_LOCAL_IDS["moderado"])


def _optional_literal_triple(subject: str, predicate: str, value: str | None) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    return f"  {subject} {predicate} {literal(cleaned)} .\n"


def _optional_any_uri_triple(subject: str, predicate: str, value: str | None) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    return f"  {subject} {predicate} {literal(cleaned, datatype=XSD.anyURI)} .\n"


def _resource_suffix(value: str) -> str:
    text = str(value or "").strip().strip("<>")
    text = text.split("#")[-1].split("/")[-1]
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")
    return text[:80] or "paquete"


def _itinerary_triples(paquete: str, paquete_id: str, itinerarios) -> str:
    if not itinerarios:
        return ""

    suffix = _resource_suffix(paquete_id)
    triples: list[str] = []
    for index, item in enumerate(itinerarios, start=1):
        title = (getattr(item, "titulo", None) or "").strip()
        description = (getattr(item, "descripcion", None) or "").strip()
        if not title and not description:
            continue

        title = title or f"Dia {index}"
        description = description or title
        itinerary = local_resource(f"itinerario-{suffix}-{index:02d}")
        triples.append(
            "\n".join(
                [
                    f"  {itinerary} rdf:type ex:Itinerario .",
                    f"  {itinerary} rdfs:label {literal(title, lang='es')} .",
                    f"  {itinerary} ex:nombre {literal(title)} .",
                    f"  {itinerary} rdfs:comment {literal(description, lang='es')} .",
                    f"  {itinerary} ex:descripcion {literal(description)} .",
                    f"  {paquete} ex:tieneItinerario {itinerary} .",
                ]
            )
        )

    return "\n".join(triples)


def update_package(paquete_id: str, data, owner_uri: str | None = None) -> str:
    paquete = resource(paquete_id)
    owner = resource(owner_uri) if owner_uri else None
    dificultad_id, dificultad_label = _difficulty_resource(getattr(data, "dificultad", None))
    dificultad = local_resource(dificultad_id)
    precio = decimal_value(getattr(data, "precio", 0), default=0, minimum=0)
    duracion = int_value(getattr(data, "duracion_dias", None), default=1, minimum=1, maximum=60)
    capacidad = int_value(getattr(data, "capacidad_max_personas", None), default=1, minimum=1, maximum=500)
    estado = (getattr(data, "estado_publicacion", None) or "publicado").strip().lower()
    destinos = [resource(value) for value in getattr(data, "destino_ids", []) if value]
    destinos_insert = "\n".join(f"  {paquete} ex:visitaDestino {destino} ." for destino in destinos)
    servicios = getattr(data, "servicio_ids", None)
    should_update_services = servicios is not None
    servicios_insert = (
        "\n".join(
            f"  {paquete} ex:incluyeServicio {servicio} ."
            for servicio in [resource(value) for value in servicios if value]
        )
        if should_update_services
        else ""
    )
    servicios_delete = f"  {paquete} ex:incluyeServicio ?oldServicio .\n" if should_update_services else ""
    servicios_where = f"  OPTIONAL {{ {paquete} ex:incluyeServicio ?oldServicio . }}\n" if should_update_services else ""
    itinerarios = getattr(data, "itinerarios", None)
    should_update_itineraries = itinerarios is not None
    itinerary_delete = (
        f"""  {paquete} ex:tieneItinerario ?oldItinerario .
  ?oldItinerario rdf:type ex:Itinerario .
  ?oldItinerario rdfs:label ?oldItinerarioLabel .
  ?oldItinerario ex:nombre ?oldItinerarioNombre .
  ?oldItinerario rdfs:comment ?oldItinerarioComment .
  ?oldItinerario ex:descripcion ?oldItinerarioDescripcion .
"""
        if should_update_itineraries
        else ""
    )
    itinerary_insert = (
        _itinerary_triples(paquete, paquete_id, itinerarios)
        if should_update_itineraries
        else ""
    )
    itinerary_where = (
        f"""  OPTIONAL {{
    {paquete} ex:tieneItinerario ?oldItinerario .
    OPTIONAL {{ ?oldItinerario rdf:type ex:Itinerario . }}
    OPTIONAL {{ ?oldItinerario rdfs:label ?oldItinerarioLabel . }}
    OPTIONAL {{ ?oldItinerario ex:nombre ?oldItinerarioNombre . }}
    OPTIONAL {{ ?oldItinerario rdfs:comment ?oldItinerarioComment . }}
    OPTIONAL {{ ?oldItinerario ex:descripcion ?oldItinerarioDescripcion . }}
  }}
"""
        if should_update_itineraries
        else ""
    )
    owner_delete = f"  ?oldOwner ex:armaPaqueteModificado {paquete} .\n" if owner else ""
    owner_insert = f"  {owner} ex:armaPaqueteModificado {paquete} .\n" if owner else ""
    owner_where = f"  OPTIONAL {{ ?oldOwner ex:armaPaqueteModificado {paquete} . }}\n" if owner else ""

    return f"""{PREFIXES}
DELETE {{
  {paquete} rdfs:label ?oldLabel .
  {paquete} ex:nombre ?oldNombre .
  {paquete} ex:descripcion ?oldDescripcion .
  {paquete} ex:duracionDias ?oldDuracion .
  {paquete} ex:capacidadMaxPersonas ?oldCapacidad .
  {paquete} ex:incluyeDescripcion ?oldIncluye .
  {paquete} ex:noIncluye ?oldNoIncluye .
  {paquete} ex:urlImagen ?oldImagen .
  {paquete} ex:galeriaImagenes ?oldGaleria .
  {paquete} ex:estadoPublicacion ?oldEstado .
  {paquete} ex:tieneDificultad ?oldDificultad .
  {paquete} ex:visitaDestino ?oldDestino .
{servicios_delete}
{itinerary_delete}
{owner_delete}  ?precioSpec ex:precioPorPersona ?oldPrecio .
}}
INSERT {{
  {dificultad} rdf:type ex:NivelDificultad ;
               rdfs:label {literal(dificultad_label, lang="es")} ;
               ex:nombre {literal(dificultad_label)} .
  {paquete} rdfs:label {literal(data.nombre, lang="es")} .
  {paquete} ex:nombre {literal(data.nombre)} .
  {paquete} ex:descripcion {literal(data.descripcion)} .
  {paquete} ex:duracionDias {literal(duracion, datatype=XSD.integer)} .
  {paquete} ex:capacidadMaxPersonas {literal(capacidad, datatype=XSD.integer)} .
  {paquete} ex:tieneDificultad {dificultad} .
  {paquete} ex:estadoPublicacion {literal(estado)} .
  {_optional_literal_triple(paquete, "ex:incluyeDescripcion", getattr(data, "incluye_descripcion", None))}  {_optional_literal_triple(paquete, "ex:noIncluye", getattr(data, "no_incluye", None))}  {_optional_any_uri_triple(paquete, "ex:urlImagen", getattr(data, "url_imagen", None))}  {_optional_literal_triple(paquete, "ex:galeriaImagenes", getattr(data, "galeria_imagenes", None))}  ?precioSpec ex:precioPorPersona {literal(precio, datatype=XSD.decimal)} .
{destinos_insert}
{servicios_insert}
{itinerary_insert}
{owner_insert}
}}
WHERE {{
  {paquete} rdf:type/rdfs:subClassOf* ex:PaqueteTuristico ;
            ex:tienePrecio ?precioSpec .
  OPTIONAL {{ {paquete} rdfs:label ?oldLabel . }}
  OPTIONAL {{ {paquete} ex:nombre ?oldNombre . }}
  OPTIONAL {{ {paquete} ex:descripcion ?oldDescripcion . }}
  OPTIONAL {{ {paquete} ex:duracionDias ?oldDuracion . }}
  OPTIONAL {{ {paquete} ex:capacidadMaxPersonas ?oldCapacidad . }}
  OPTIONAL {{ {paquete} ex:incluyeDescripcion ?oldIncluye . }}
  OPTIONAL {{ {paquete} ex:noIncluye ?oldNoIncluye . }}
  OPTIONAL {{ {paquete} ex:urlImagen ?oldImagen . }}
  OPTIONAL {{ {paquete} ex:galeriaImagenes ?oldGaleria . }}
  OPTIONAL {{ {paquete} ex:estadoPublicacion ?oldEstado . }}
  OPTIONAL {{ {paquete} ex:tieneDificultad ?oldDificultad . }}
  OPTIONAL {{ {paquete} ex:visitaDestino ?oldDestino . }}
{servicios_where}
{itinerary_where}
{owner_where}  OPTIONAL {{ ?precioSpec ex:precioPorPersona ?oldPrecio . }}
}}
"""


def insert_package(paquete_uri: str, precio_uri: str, owner_uri: str, data) -> str:
    paquete = resource(paquete_uri)
    precio_spec = resource(precio_uri)
    owner = resource(owner_uri)
    dificultad_id, dificultad_label = _difficulty_resource(getattr(data, "dificultad", None))
    dificultad = local_resource(dificultad_id)
    precio = decimal_value(getattr(data, "precio", 0), default=0, minimum=0)
    duracion = int_value(getattr(data, "duracion_dias", None), default=1, minimum=1, maximum=60)
    capacidad = int_value(getattr(data, "capacidad_max_personas", None), default=1, minimum=1, maximum=500)
    estado = (getattr(data, "estado_publicacion", None) or "publicado").strip().lower()
    destinos = [resource(value) for value in getattr(data, "destino_ids", []) if value]
    destinos_insert = "\n".join(f"  {paquete} ex:visitaDestino {destino} ." for destino in destinos)
    servicios_insert = "\n".join(
        f"  {paquete} ex:incluyeServicio {servicio} ."
        for servicio in [resource(value) for value in (getattr(data, "servicio_ids", None) or []) if value]
    )
    itinerarios_insert = _itinerary_triples(
        paquete,
        paquete_uri,
        getattr(data, "itinerarios", None),
    )

    return f"""{PREFIXES}
INSERT DATA {{
  {dificultad} rdf:type ex:NivelDificultad ;
               rdfs:label {literal(dificultad_label, lang="es")} ;
               ex:nombre {literal(dificultad_label)} .
  {precio_spec} rdf:type ex:EspecificacionPrecio ;
                ex:precioPorPersona {literal(precio, datatype=XSD.decimal)} .
  {paquete} rdf:type ex:PaqueteTuristico ;
            rdfs:label {literal(data.nombre, lang="es")} ;
            ex:nombre {literal(data.nombre)} ;
            ex:descripcion {literal(data.descripcion)} ;
            ex:tienePrecio {precio_spec} ;
            ex:duracionDias {literal(duracion, datatype=XSD.integer)} ;
            ex:capacidadMaxPersonas {literal(capacidad, datatype=XSD.integer)} ;
            ex:tieneDificultad {dificultad} ;
            ex:estadoPublicacion {literal(estado)} .
  {_optional_literal_triple(paquete, "ex:incluyeDescripcion", getattr(data, "incluye_descripcion", None))}  {_optional_literal_triple(paquete, "ex:noIncluye", getattr(data, "no_incluye", None))}  {_optional_any_uri_triple(paquete, "ex:urlImagen", getattr(data, "url_imagen", None))}  {_optional_literal_triple(paquete, "ex:galeriaImagenes", getattr(data, "galeria_imagenes", None))}{destinos_insert}
{servicios_insert}
{itinerarios_insert}
  {owner} ex:armaPaqueteModificado {paquete} .
}}
"""


def list_packages_for_site(sitio_id: str, limit: int, offset: int) -> str:
    destino = resource(sitio_id)
    safe_limit = limit_value(limit, default=50)
    safe_offset = offset_value(offset)

    return f"""{PREFIXES}
SELECT
  {_package_projection()}
WHERE {{
  VALUES ?destinoFiltro {{ {destino} }}

  ?paquete ex:visitaDestino ?destinoFiltro .
  {_package_core()}

  {_public_status_filter()}
}}
GROUP BY {_package_group_by()}
ORDER BY ?nombre
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def detail_base(paquete_id: str) -> str:
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
SELECT ?paquete ?nombre ?descripcion ?precio ?duracion ?dificultad ?capacidad ?incluye ?noIncluye ?agencia ?agenciaNombre ?imagen ?galeria ?estadoPublicacion
WHERE {{
  VALUES ?paquete {{ {paquete} }}

  ?paquete rdf:type/rdfs:subClassOf* ex:PaqueteTuristico ;
           ex:nombre ?nombre ;
           ex:descripcion ?descripcion ;
           ex:tienePrecio ?precioSpec .
  ?precioSpec ex:precioPorPersona ?precio .

  OPTIONAL {{ ?paquete ex:duracionDias ?duracion . }}
  OPTIONAL {{ ?paquete ex:capacidadMaxPersonas ?capacidad . }}
  OPTIONAL {{ ?paquete ex:incluyeDescripcion ?incluye . }}
  OPTIONAL {{ ?paquete ex:noIncluye ?noIncluye . }}
  OPTIONAL {{ ?paquete ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?paquete ex:galeriaImagenes ?galeria . }}
  OPTIONAL {{ ?paquete ex:estadoPublicacion ?estadoPublicacion . }}
  OPTIONAL {{
    ?agencia ex:armaPaqueteModificado ?paquete .
    OPTIONAL {{ ?agencia rdfs:label ?agenciaLabel . }}
    OPTIONAL {{ ?agencia ex:nombre ?agenciaName . }}
    BIND(COALESCE(?agenciaLabel, ?agenciaName, STRAFTER(STR(?agencia), "#")) AS ?agenciaNombre)
  }}

  OPTIONAL {{
    ?paquete ex:tieneDificultad ?dif .
    OPTIONAL {{ ?dif rdfs:label ?difLabel . }}
    BIND(COALESCE(?difLabel, STRAFTER(STR(?dif), "#"), STR(?dif)) AS ?dificultad)
  }}
}}
"""


def detail_destinations(paquete_id: str) -> str:
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
SELECT ?destino ?destinoNombre ?municipioNombre ?lat ?lon ?categoriaLabel ?imagen ?galeria
WHERE {{
  VALUES ?paquete {{ {paquete} }}

  ?paquete ex:visitaDestino ?destino .

  OPTIONAL {{ ?destino rdfs:label ?destinoLabel . }}
  OPTIONAL {{ ?destino ex:nombre ?destinoNombreRaw . }}
  BIND(COALESCE(?destinoLabel, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoNombre)

  OPTIONAL {{
    ?destino ex:ubicadoEn ?municipio .
    OPTIONAL {{ ?municipio rdfs:label ?municipioLabel . }}
    OPTIONAL {{ ?municipio ex:nombre ?municipioNombreRaw . }}
    BIND(COALESCE(?municipioLabel, ?municipioNombreRaw, STRAFTER(STR(?municipio), "#")) AS ?municipioNombre)
  }}

  OPTIONAL {{ ?destino ex:latitud ?lat . }}
  OPTIONAL {{ ?destino ex:longitud ?lon . }}
  OPTIONAL {{ ?destino ex:urlImagen ?imagen . }}
  OPTIONAL {{ ?destino ex:galeriaImagenes ?galeria . }}

  OPTIONAL {{
    ?destino rdf:type ?categoria .
    ?categoria rdfs:subClassOf* ex:DestinoTuristico .
    FILTER(?categoria != ex:DestinoTuristico)
    OPTIONAL {{ ?categoria rdfs:label ?categoriaLabelRaw . }}
    BIND(COALESCE(?categoriaLabelRaw, STRAFTER(STR(?categoria), "#")) AS ?categoriaLabel)
  }}
}}
"""


def detail_services(paquete_id: str) -> str:
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
SELECT ?servicio ?servicioNombre ?tipoLabel
WHERE {{
  VALUES ?paquete {{ {paquete} }}

  ?paquete ex:incluyeServicio ?servicio .

  OPTIONAL {{ ?servicio rdfs:label ?servicioLabel . }}
  OPTIONAL {{ ?servicio ex:nombre ?servicioNombreRaw . }}
  BIND(COALESCE(?servicioLabel, ?servicioNombreRaw, STRAFTER(STR(?servicio), "#")) AS ?servicioNombre)

  OPTIONAL {{
    ?servicio rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipo != ex:ServicioTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabelRaw . }}
    BIND(COALESCE(?tipoLabelRaw, STRAFTER(STR(?tipo), "#")) AS ?tipoLabel)
  }}
}}
"""


def detail_itineraries(paquete_id: str) -> str:
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
SELECT ?it ?titulo ?descripcion
WHERE {{
  VALUES ?paquete {{ {paquete} }}

  ?paquete ex:tieneItinerario ?it .

  OPTIONAL {{ ?it rdfs:label ?itLabel . }}
  OPTIONAL {{ ?it ex:nombre ?itNombre . }}
  OPTIONAL {{ ?it rdfs:comment ?itDesc . }}
  OPTIONAL {{ ?it ex:descripcion ?itDescripcion . }}
  BIND(COALESCE(?itLabel, ?itNombre, STRAFTER(STR(?it), "#")) AS ?titulo)
  BIND(COALESCE(?itDescripcion, ?itDesc) AS ?descripcion)
}}
ORDER BY ?it
"""
