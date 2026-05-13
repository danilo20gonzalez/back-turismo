from sparql_builder import PREFIXES, literal, limit_value


def transversal(busqueda: str, limit: int = 12) -> str:
    q = literal(busqueda or "")
    safe_limit = limit_value(limit, default=12, maximum=50)

    return f"""{PREFIXES}
SELECT ?tipo ?sujeto ?nombre ?descripcion ?precio ?moneda ?capacidad ?duracion
  (GROUP_CONCAT(DISTINCT ?municipioLabel; separator=" | ") AS ?municipios)
  (GROUP_CONCAT(DISTINCT ?destinoLabel; separator=" | ") AS ?destinos)
WHERE {{
  BIND({q} AS ?q)

  {{
    ?sujeto rdf:type/rdfs:subClassOf* ex:PaqueteTuristico .
    BIND("Paquete" AS ?tipo)
    OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
    OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
    BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
    OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}
    OPTIONAL {{
      ?sujeto ex:tienePrecio ?precioSpec .
      ?precioSpec ex:precioPorPersona ?precio .
      OPTIONAL {{ ?precioSpec ex:moneda ?moneda . }}
    }}
    OPTIONAL {{ ?sujeto ex:capacidadMaxPersonas ?capacidad . }}
    OPTIONAL {{ ?sujeto ex:duracionDias ?duracion . }}
    OPTIONAL {{
      ?sujeto ex:visitaDestino ?destino .
      OPTIONAL {{ ?destino rdfs:label ?destinoLabelRaw . }}
      OPTIONAL {{ ?destino ex:nombre ?destinoNombreRaw . }}
      BIND(COALESCE(?destinoLabelRaw, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoLabel)
      OPTIONAL {{
        ?destino ex:ubicadoEn ?municipio .
        OPTIONAL {{ ?municipio rdfs:label ?municipioLabelRaw . }}
        OPTIONAL {{ ?municipio ex:nombre ?municipioNombreRaw . }}
        BIND(COALESCE(?municipioLabelRaw, ?municipioNombreRaw, STRAFTER(STR(?municipio), "#")) AS ?municipioLabel)
      }}
    }}
  }}
  UNION
  {{
    ?sujeto rdf:type/rdfs:subClassOf* ex:DestinoTuristico .
    BIND("Destino" AS ?tipo)
    OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
    OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
    BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
    OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}
    OPTIONAL {{ ?sujeto ex:capacidadCargaDiaria ?capacidad . }}
    OPTIONAL {{
      ?sujeto ex:ubicadoEn ?municipio .
      OPTIONAL {{ ?municipio rdfs:label ?municipioLabelRaw . }}
      OPTIONAL {{ ?municipio ex:nombre ?municipioNombreRaw . }}
      BIND(COALESCE(?municipioLabelRaw, ?municipioNombreRaw, STRAFTER(STR(?municipio), "#")) AS ?municipioLabel)
    }}
  }}
  UNION
  {{
    ?sujeto rdf:type/rdfs:subClassOf* ex:ServicioTuristico .
    BIND("Servicio" AS ?tipo)
    OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
    OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
    BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
    OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}
    OPTIONAL {{
      ?paquete ex:incluyeServicio ?sujeto ;
               ex:visitaDestino ?destino .
      OPTIONAL {{ ?destino rdfs:label ?destinoLabelRaw . }}
      OPTIONAL {{ ?destino ex:nombre ?destinoNombreRaw . }}
      BIND(COALESCE(?destinoLabelRaw, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoLabel)
    }}
  }}

  FILTER(
    ?q = "" ||
    CONTAINS(LCASE(STR(?nombre)), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?descripcion, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?municipioLabel, ""))), LCASE(?q)) ||
    CONTAINS(LCASE(STR(COALESCE(?destinoLabel, ""))), LCASE(?q))
  )
}}
GROUP BY ?tipo ?sujeto ?nombre ?descripcion ?precio ?moneda ?capacidad ?duracion
ORDER BY ?tipo ?nombre
LIMIT {safe_limit}
"""
