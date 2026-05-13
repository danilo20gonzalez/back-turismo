from sparql_builder import (
    PREFIXES,
    decimal_value,
    limit_value,
    literal,
    offset_value,
    order_by,
    resource,
)


def _package_projection() -> str:
    return """?paquete ?nombre ?descripcion ?precio ?dirigidoA ?duracion ?dificultad ?capacidad
  ?imagen ?galeria
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
    return "?paquete ?nombre ?descripcion ?precio ?dirigidoA ?duracion ?dificultad ?capacidad ?imagen ?galeria"


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
}}
GROUP BY {_package_group_by()}
ORDER BY ?nombre
LIMIT {safe_limit}
OFFSET {safe_offset}
"""


def detail_base(paquete_id: str) -> str:
    paquete = resource(paquete_id)
    return f"""{PREFIXES}
SELECT ?paquete ?nombre ?descripcion ?precio ?duracion ?dificultad ?capacidad ?incluye ?noIncluye ?agencia ?agenciaNombre ?imagen ?galeria
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
SELECT ?servicioNombre ?tipoLabel
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
SELECT ?titulo ?descripcion
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
"""
