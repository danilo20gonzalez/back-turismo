from sparql_builder import (
    PREFIXES,
    int_value,
    limit_value,
    literal,
    offset_value,
    order_by,
    resource,
)


def list_sites(
    busqueda: str,
    tipo: str,
    municipio: str,
    cap_min: int | None,
    cap_max: int | None,
    orden: str,
    limit: int,
    offset: int,
) -> str:
    min_cap = int_value(cap_min, default=0, minimum=0)
    max_cap = int_value(cap_max, default=999_999_999, minimum=min_cap)
    order_clause = order_by(
        orden,
        {
            "popularidad": "DESC(?popularidad)",
            "nombre": "?nombre",
            "capacidad": "DESC(?capacidad)",
        },
        "popularidad",
    )

    return f"""{PREFIXES}
SELECT
  ?destino ?nombre ?descripcion ?municipio ?capacidad
  (GROUP_CONCAT(DISTINCT ?tipoLabel; separator=" | ") AS ?tipos)
  (COUNT(DISTINCT ?paquete) AS ?popularidad)
WHERE {{
  BIND({literal(busqueda or "")} AS ?q)
  BIND({literal(tipo or "")} AS ?tipoParam)
  BIND({literal(municipio or "")} AS ?muniParam)

  ?destino rdf:type/rdfs:subClassOf* ex:DestinoTuristico .

  OPTIONAL {{ ?destino rdfs:label ?nombreRaw . }}
  OPTIONAL {{ ?destino ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreRaw, ?nombreProp, STRAFTER(STR(?destino), "#")) AS ?nombre)

  OPTIONAL {{ ?destino ex:descripcion ?descripcion . }}

  OPTIONAL {{
    ?destino ex:ubicadoEn ?muni .
    OPTIONAL {{ ?muni rdfs:label ?muniLabel . }}
    OPTIONAL {{ ?muni ex:nombre ?muniNombre . }}
    BIND(COALESCE(?muniLabel, ?muniNombre, STRAFTER(STR(?muni), "#")) AS ?municipio)
  }}

  OPTIONAL {{ ?destino ex:capacidadCargaDiaria ?capacidad . }}

  OPTIONAL {{
    ?destino rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:DestinoTuristico .
    FILTER(?tipo != ex:DestinoTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabelRaw . }}
    BIND(COALESCE(?tipoLabelRaw, STRAFTER(STR(?tipo), "#")) AS ?tipoLabel)
  }}

  OPTIONAL {{
    ?paquete rdf:type/rdfs:subClassOf* ex:PaqueteTuristico ;
             ex:visitaDestino ?destino .
  }}

  FILTER(
    ?q = "" ||
    CONTAINS(LCASE(STR(?nombre)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?descripcion, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?municipio, ""))), LCASE(?q))
  )

  FILTER(
    ?tipoParam = "" ||
    EXISTS {{
      ?destino rdf:type ?tipoFilter .
      ?tipoFilter rdfs:subClassOf* ex:DestinoTuristico .
      FILTER(?tipoFilter != ex:DestinoTuristico)
      OPTIONAL {{ ?tipoFilter rdfs:label ?tipoFilterLabel . }}
      BIND(COALESCE(?tipoFilterLabel, STRAFTER(STR(?tipoFilter), "#")) AS ?tipoFilterName)
      FILTER(
        LCASE(STR(?tipoFilterName)) = LCASE(?tipoParam) ||
        STR(?tipoFilter) = ?tipoParam ||
        STRAFTER(STR(?tipoFilter), "#") = ?tipoParam
      )
    }}
  )

  FILTER(
    ?muniParam = "" ||
    EXISTS {{
      ?destino ex:ubicadoEn ?muniFilter .
      OPTIONAL {{ ?muniFilter rdfs:label ?muniFilterLabel . }}
      OPTIONAL {{ ?muniFilter ex:nombre ?muniFilterNombre . }}
      BIND(COALESCE(?muniFilterLabel, ?muniFilterNombre, STRAFTER(STR(?muniFilter), "#")) AS ?muniFilterName)
      FILTER(
        LCASE(STR(?muniFilterName)) = LCASE(?muniParam) ||
        STR(?muniFilter) = ?muniParam ||
        STRAFTER(STR(?muniFilter), "#") = ?muniParam
      )
    }}
  )

  FILTER(!BOUND(?capacidad) || (?capacidad >= {min_cap} && ?capacidad <= {max_cap}))
}}
GROUP BY ?destino ?nombre ?descripcion ?municipio ?capacidad
ORDER BY {order_clause}
LIMIT {limit_value(limit, default=50)}
OFFSET {offset_value(offset)}
"""


def filter_types() -> str:
    return f"""{PREFIXES}
SELECT ?tipo ?nombre (COUNT(DISTINCT ?destino) AS ?total)
WHERE {{
  ?destino rdf:type ?tipo .
  ?tipo rdfs:subClassOf+ ex:DestinoTuristico .

  OPTIONAL {{ ?tipo rdfs:label ?nombreRaw . }}
  BIND(COALESCE(?nombreRaw, STRAFTER(STR(?tipo), "#")) AS ?nombre)
}}
GROUP BY ?tipo ?nombre
ORDER BY DESC(?total) ?nombre
"""


def municipalities() -> str:
    return f"""{PREFIXES}
SELECT DISTINCT ?municipio ?nombre
WHERE {{
  ?municipio rdf:type/rdfs:subClassOf* ex:Municipio .
  OPTIONAL {{ ?municipio rdfs:label ?nombreRaw . }}
  OPTIONAL {{ ?municipio ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreRaw, ?nombreProp, STRAFTER(STR(?municipio), "#")) AS ?nombre)
}}
ORDER BY ?nombre
"""


def capacity_range() -> str:
    return f"""{PREFIXES}
SELECT (MIN(?cap) AS ?min_cap) (MAX(?cap) AS ?max_cap)
WHERE {{
  ?destino rdf:type/rdfs:subClassOf* ex:DestinoTuristico ;
           ex:capacidadCargaDiaria ?cap .
}}
"""


def detail(sitio_id: str) -> str:
    destino = resource(sitio_id)
    return f"""{PREFIXES}
SELECT ?destino ?nombre ?descripcion ?municipio ?capacidad ?lat ?lon
  (GROUP_CONCAT(DISTINCT ?tipoLabel; separator=" | ") AS ?tipos)
WHERE {{
  VALUES ?destino {{ {destino} }}

  ?destino rdf:type/rdfs:subClassOf* ex:DestinoTuristico .

  OPTIONAL {{ ?destino rdfs:label ?nombreRaw . }}
  OPTIONAL {{ ?destino ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreRaw, ?nombreProp, STRAFTER(STR(?destino), "#")) AS ?nombre)

  OPTIONAL {{ ?destino ex:descripcion ?descripcion . }}
  OPTIONAL {{ ?destino ex:capacidadCargaDiaria ?capacidad . }}
  OPTIONAL {{ ?destino ex:latitud ?lat . }}
  OPTIONAL {{ ?destino ex:longitud ?lon . }}

  OPTIONAL {{
    ?destino ex:ubicadoEn ?muni .
    OPTIONAL {{ ?muni rdfs:label ?muniLabel . }}
    OPTIONAL {{ ?muni ex:nombre ?muniNombre . }}
    BIND(COALESCE(?muniLabel, ?muniNombre, STRAFTER(STR(?muni), "#")) AS ?municipio)
  }}

  OPTIONAL {{
    ?destino rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:DestinoTuristico .
    FILTER(?tipo != ex:DestinoTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabelRaw . }}
    BIND(COALESCE(?tipoLabelRaw, STRAFTER(STR(?tipo), "#")) AS ?tipoLabel)
  }}
}}
GROUP BY ?destino ?nombre ?descripcion ?municipio ?capacidad ?lat ?lon
"""
