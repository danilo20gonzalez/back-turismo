import re
import unicodedata

from sparql_builder import PREFIXES, literal, limit_value


# ─── helpers de normalización ───────────────────────────────────────────────

_ACCENT_MAP = {
    "a": "aAáÁàÀâÂãÃäÄ",
    "e": "eEéÉèÈêÊëË",
    "i": "iIíÍìÌîÎïÏ",
    "o": "oOóÓòÒôÔõÕöÖ",
    "u": "uUúÚùÙûÛüÜ",
    "n": "nNñÑ",
}


def _extraer_palabras(texto: str) -> list[str]:
    texto = texto.lower().strip()
    sin_acentos = unicodedata.normalize("NFD", texto)
    sin_acentos = "".join(c for c in sin_acentos if unicodedata.category(c) != "Mn")
    return [w for w in re.findall(r"[a-zñ]+", sin_acentos) if len(w) > 1 or w in ("en", "de")]


def _to_char_class(palabra: str) -> str:
    """Convierte una palabra en una clase de caracteres insensible a acentos."""
    chars = []
    for c in palabra.lower():
        if c in _ACCENT_MAP:
            chars.append(f"[{_ACCENT_MAP[c]}]")
        else:
            chars.append(f"[{c}{c.upper()}]")
    return "".join(chars)


def _build_regex_pattern(busqueda: str) -> str:
    """Construye un patrón regex para SPARQL REGEX con matching insensible a acentos."""
    words = _extraer_palabras(busqueda)
    if not words:
        return ""
    patterns = [_to_char_class(w) for w in words]
    return "|".join(patterns)


def _filter_regex(patron_var: str, *campos: str) -> str:
    """Genera FILTER con REGEX para múltiples campos usando la variable del patrón."""
    if not campos:
        return ""
    condiciones = [
        f'REGEX(LCASE(COALESCE(STR({c}), "")), {patron_var})'
        for c in campos
    ]
    return f"FILTER({patron_var} = \"\" || {' || '.join(condiciones)})"


# ─── función transversal (legacy / fallback) ────────────────────────────────

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


# ─── queries especializadas por categoría ────────────────────────────────────

def busqueda_paquetes(busqueda: str, limit: int = 5) -> str:
    pattern = _build_regex_pattern(busqueda)
    safe_limit = limit_value(limit, default=5, maximum=20)
    return f"""{PREFIXES}
SELECT DISTINCT ?sujeto ?nombre ?descripcion ?precio ?moneda ?duracion ?capacidad ?dificultad
  (GROUP_CONCAT(DISTINCT ?destinoLabel; separator=" | ") AS ?destinos)
  (GROUP_CONCAT(DISTINCT ?municipioLabel; separator=" | ") AS ?municipios)
WHERE {{
  BIND({literal(pattern)} AS ?patron)

  ?sujeto rdf:type/rdfs:subClassOf* ex:PaqueteTuristico .

  OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
  OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
  OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}

  OPTIONAL {{
    ?sujeto ex:tienePrecio ?precioSpec .
    ?precioSpec ex:precioPorPersona ?precio .
    OPTIONAL {{ ?precioSpec ex:moneda ?moneda . }}
  }}
  OPTIONAL {{ ?sujeto ex:duracionDias ?duracion . }}
  OPTIONAL {{ ?sujeto ex:capacidadMaxPersonas ?capacidad . }}

  OPTIONAL {{
    ?sujeto ex:tieneDificultad ?dificultadRaw .
    OPTIONAL {{ ?dificultadRaw rdfs:label ?dificultadLabel . }}
    BIND(COALESCE(?dificultadLabel, STRAFTER(STR(?dificultadRaw), "#")) AS ?dificultad)
  }}

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

  {_filter_regex("?patron", "?nombre", "?descripcion", "?destinoLabel", "?municipioLabel")}
}}
GROUP BY ?sujeto ?nombre ?descripcion ?precio ?moneda ?duracion ?capacidad ?dificultad
ORDER BY ?nombre
LIMIT {safe_limit}
"""


def busqueda_destinos(busqueda: str, limit: int = 5) -> str:
    pattern = _build_regex_pattern(busqueda)
    safe_limit = limit_value(limit, default=5, maximum=20)
    return f"""{PREFIXES}
SELECT DISTINCT ?sujeto ?nombre ?descripcion ?municipio ?capacidad
  (GROUP_CONCAT(DISTINCT ?tipoLabel; separator=" | ") AS ?tipos)
WHERE {{
  BIND({literal(pattern)} AS ?patron)

  ?sujeto rdf:type/rdfs:subClassOf* ex:DestinoTuristico .

  OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
  OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
  OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}
  OPTIONAL {{ ?sujeto ex:capacidadCargaDiaria ?capacidad . }}

  OPTIONAL {{
    ?sujeto ex:ubicadoEn ?muni .
    OPTIONAL {{ ?muni rdfs:label ?muniLabel . }}
    OPTIONAL {{ ?muni ex:nombre ?muniNombre . }}
    BIND(COALESCE(?muniLabel, ?muniNombre, STRAFTER(STR(?muni), "#")) AS ?municipio)
  }}

  OPTIONAL {{
    ?sujeto rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:DestinoTuristico .
    FILTER(?tipo != ex:DestinoTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabelRaw . }}
    BIND(COALESCE(?tipoLabelRaw, STRAFTER(STR(?tipo), "#")) AS ?tipoLabel)
  }}

  {_filter_regex("?patron", "?nombre", "?descripcion", "?municipio", "?tipoLabel")}
}}
GROUP BY ?sujeto ?nombre ?descripcion ?municipio ?capacidad
ORDER BY ?nombre
LIMIT {safe_limit}
"""


def busqueda_sitios(busqueda: str, limit: int = 5) -> str:
    """Busca sitios de interés para el chatbot (usa la misma lógica que destinos)."""
    return busqueda_destinos(busqueda, limit)


def busqueda_servicios(busqueda: str, limit: int = 5) -> str:
    pattern = _build_regex_pattern(busqueda)
    safe_limit = limit_value(limit, default=5, maximum=20)
    return f"""{PREFIXES}
SELECT DISTINCT ?sujeto ?nombre ?descripcion ?tipoNombre
  (GROUP_CONCAT(DISTINCT ?destinoLabel; separator=" | ") AS ?destinos)
WHERE {{
  BIND({literal(pattern)} AS ?patron)

  ?sujeto rdf:type/rdfs:subClassOf* ex:ServicioTuristico .

  OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
  OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
  OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}

  OPTIONAL {{
    ?sujeto rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipo != ex:ServicioTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabel . }}
    BIND(COALESCE(?tipoLabel, STRAFTER(STR(?tipo), "#")) AS ?tipoNombre)
  }}

  OPTIONAL {{
    ?paquete ex:incluyeServicio ?sujeto ;
             ex:visitaDestino ?destino .
    OPTIONAL {{ ?destino rdfs:label ?destinoLabelRaw . }}
    OPTIONAL {{ ?destino ex:nombre ?destinoNombreRaw . }}
    BIND(COALESCE(?destinoLabelRaw, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoLabel)
  }}

  {_filter_regex("?patron", "?nombre", "?descripcion", "?tipoNombre", "?destinoLabel")}
}}
GROUP BY ?sujeto ?nombre ?descripcion ?tipoNombre
ORDER BY ?nombre
LIMIT {safe_limit}
"""


def busqueda_servicios_aventura(busqueda: str, limit: int = 5) -> str:
    """Similar a busqueda_servicios pero filtra por tipos de actividad/aventura."""
    pattern = _build_regex_pattern(busqueda)
    safe_limit = limit_value(limit, default=5, maximum=20)
    return f"""{PREFIXES}
SELECT DISTINCT ?sujeto ?nombre ?descripcion ?tipoNombre
  (GROUP_CONCAT(DISTINCT ?destinoLabel; separator=" | ") AS ?destinos)
WHERE {{
  BIND({literal(pattern)} AS ?patron)

  ?sujeto rdf:type/rdfs:subClassOf* ex:ServicioTuristico .

  OPTIONAL {{ ?sujeto rdfs:label ?nombreLabel . }}
  OPTIONAL {{ ?sujeto ex:nombre ?nombreProp . }}
  BIND(COALESCE(?nombreLabel, ?nombreProp, STRAFTER(STR(?sujeto), "#")) AS ?nombre)
  OPTIONAL {{ ?sujeto ex:descripcion ?descripcion . }}

  OPTIONAL {{
    ?sujeto rdf:type ?tipo .
    ?tipo rdfs:subClassOf* ex:ServicioTuristico .
    FILTER(?tipo != ex:ServicioTuristico)
    OPTIONAL {{ ?tipo rdfs:label ?tipoLabel . }}
    BIND(COALESCE(?tipoLabel, STRAFTER(STR(?tipo), "#")) AS ?tipoNombre)
  }}

  OPTIONAL {{
    ?paquete ex:incluyeServicio ?sujeto ;
             ex:visitaDestino ?destino .
    OPTIONAL {{ ?destino rdfs:label ?destinoLabelRaw . }}
    OPTIONAL {{ ?destino ex:nombre ?destinoNombreRaw . }}
    BIND(COALESCE(?destinoLabelRaw, ?destinoNombreRaw, STRAFTER(STR(?destino), "#")) AS ?destinoLabel)
  }}

  {_filter_regex("?patron", "?nombre", "?descripcion", "?tipoNombre", "?destinoLabel")}
}}
GROUP BY ?sujeto ?nombre ?descripcion ?tipoNombre
ORDER BY ?nombre
LIMIT {safe_limit}
"""
