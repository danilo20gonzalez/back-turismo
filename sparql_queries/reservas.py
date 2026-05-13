from datetime import date, datetime

from sparql_builder import (
    EX,
    PREFIXES,
    date_literal,
    datetime_literal,
    int_value,
    literal,
    local_resource,
    resource,
)


STATE_LOCAL_IDS = {
    "confirmada": "estado-reserva-confirmada",
    "pendiente": "estado-reserva-pendiente",
    "cancelada": "estado-reserva-cancelada",
    "completada": "estado-reserva-completada",
    "expirada": "estado-reserva-expirada",
}


def state_resource(state: str) -> str:
    key = (state or "Confirmada").strip().lower()
    return local_resource(STATE_LOCAL_IDS.get(key, "estado-reserva-confirmada"))


def capacity_for_package(paquete_id: str, fecha_viaje: date | str) -> str:
    paquete = resource(paquete_id)
    fecha = date_literal(fecha_viaje)
    return f"""{PREFIXES}
SELECT ?capacidadMax (SUM(?viajerosValue) AS ?totalOcupado)
WHERE {{
  VALUES ?paquete {{ {paquete} }}
  ?paquete ex:capacidadMaxPersonas ?capacidadMax .

  OPTIONAL {{
    ?reserva rdf:type/rdfs:subClassOf* ex:Reserva ;
             ex:reservaPaquete ?paquete ;
             ex:fechaInicio {fecha} ;
             ex:numeroViajeros ?viajeros .

    OPTIONAL {{
      ?reserva ex:tieneEstado ?estadoTerm .
      OPTIONAL {{ ?estadoTerm rdfs:label ?estadoLabel . }}
      OPTIONAL {{ ?estadoTerm ex:nombre ?estadoNombre . }}
      BIND(
        IF(
          isIRI(?estadoTerm),
          COALESCE(?estadoLabel, ?estadoNombre, STRAFTER(STR(?estadoTerm), "#")),
          STR(?estadoTerm)
        ) AS ?estadoText
      )
    }}

    FILTER(!BOUND(?estadoText) || !CONTAINS(LCASE(STR(?estadoText)), "cancelad"))
  }}

  BIND(COALESCE(?viajeros, 0) AS ?viajerosValue)
}}
GROUP BY ?capacidadMax
"""


def insert_reservation(
    reserva_uri: str,
    user_uri: str,
    paquete_id: str,
    fecha_inicio: date | str,
    numero_viajeros: int,
    estado: str = "Confirmada",
    fecha_reserva: datetime | None = None,
) -> str:
    reserva = resource(reserva_uri)
    usuario = resource(user_uri)
    paquete = resource(paquete_id)
    estado_iri = state_resource(estado)
    viajeros = int_value(numero_viajeros, default=1, minimum=1)
    created_at = fecha_reserva or datetime.utcnow()
    reserva_label = reserva[1:-1].removeprefix(EX).replace("_", " ").replace("-", " ").title()

    return f"""{PREFIXES}
INSERT DATA {{
  {estado_iri} rdf:type ex:EstadoReserva ;
               rdfs:label {literal(estado, lang="es")} ;
               ex:nombre {literal(estado)} .

  {reserva} rdf:type ex:Reserva ;
            rdfs:label {literal(reserva_label, lang="es")} ;
            ex:nombre {literal(reserva_label)} ;
            ex:reservaPaquete {paquete} ;
            ex:fechaReserva {datetime_literal(created_at)} ;
            ex:fechaInicio {date_literal(fecha_inicio)} ;
            ex:numeroViajeros {viajeros} ;
            ex:tieneEstado {estado_iri} .

  {usuario} ex:realizaReserva {reserva} .
}}
"""


def user_reservations(user_uri: str) -> str:
    usuario = resource(user_uri)
    return f"""{PREFIXES}
SELECT ?reserva ?paquete ?paquete_id ?paquete_nombre ?fecha ?personas ?estado ?precio_unitario ?comunidad_nombre ?total_pagar ?paquete_imagen
WHERE {{
  VALUES ?usuario {{ {usuario} }}

  {{
    ?usuario ex:realizaReserva ?reserva .
  }}
  UNION
  {{
    ?reserva ex:realizaReserva ?usuario .
  }}

  ?reserva rdf:type/rdfs:subClassOf* ex:Reserva ;
           ex:reservaPaquete ?paquete ;
           ex:fechaInicio ?fecha ;
           ex:numeroViajeros ?personas .

  BIND(STRAFTER(STR(?paquete), "#") AS ?paquete_id)
  OPTIONAL {{ ?paquete ex:nombre ?paquete_nombre . }}

  OPTIONAL {{
    ?reserva ex:tieneEstado ?estadoTerm .
    OPTIONAL {{ ?estadoTerm rdfs:label ?estadoLabel . }}
    OPTIONAL {{ ?estadoTerm ex:nombre ?estadoNombre . }}
    BIND(
      IF(
        isIRI(?estadoTerm),
        COALESCE(?estadoLabel, ?estadoNombre, STRAFTER(STR(?estadoTerm), "#")),
        STR(?estadoTerm)
      ) AS ?estadoFromTerm
    )
  }}
  BIND(COALESCE(?estadoFromTerm, "Pendiente") AS ?estado)

  OPTIONAL {{ ?paquete ex:tienePrecio/ex:precioPorPersona ?precio_from_spec . }}
  OPTIONAL {{ ?paquete ex:precioPersona ?precio_legacy . }}
  OPTIONAL {{ ?paquete ex:urlImagen ?paquete_imagen . }}
  BIND(COALESCE(?precio_from_spec, ?precio_legacy, 0) AS ?precio_unitario)
  BIND(?precio_unitario * ?personas AS ?total_pagar)

  OPTIONAL {{
    ?paquete ex:ofrecidoPor ?comunidad .
    OPTIONAL {{ ?comunidad rdfs:label ?comunidadLabel . }}
    OPTIONAL {{ ?comunidad ex:nombre ?comunidadNombre . }}
    OPTIONAL {{ ?comunidad ex:nombreComunidad ?comunidadNombreLegacy . }}
    BIND(COALESCE(?comunidadLabel, ?comunidadNombre, ?comunidadNombreLegacy) AS ?comunidad_nombre)
  }}
}}
ORDER BY DESC(?fecha)
"""


def user_stats(user_uri: str) -> str:
    usuario = resource(user_uri)
    return f"""{PREFIXES}
SELECT (COUNT(DISTINCT ?reserva) AS ?total)
WHERE {{
  VALUES ?usuario {{ {usuario} }}
  {{
    ?usuario ex:realizaReserva ?reserva .
  }}
  UNION
  {{
    ?reserva ex:realizaReserva ?usuario .
  }}
  ?reserva rdf:type/rdfs:subClassOf* ex:Reserva .
}}
"""


def reservation_detail(user_uri: str, reserva_id: str) -> str:
    usuario = resource(user_uri)
    reserva = local_resource(reserva_id)
    return f"""{PREFIXES}
SELECT ?reserva ?paquete ?paquete_id ?paquete_nombre ?paquete_descripcion ?fecha ?fecha_reserva
       ?personas ?estado ?precio_unitario ?total_pagar ?paquete_imagen ?duracion ?comunidad_nombre
       ?destino_nombre ?municipio_nombre ?lat ?lon ?destino_imagen
WHERE {{
  VALUES ?usuario {{ {usuario} }}
  VALUES ?reserva {{ {reserva} }}

  {{
    ?usuario ex:realizaReserva ?reserva .
  }}
  UNION
  {{
    ?reserva ex:realizaReserva ?usuario .
  }}

  ?reserva rdf:type/rdfs:subClassOf* ex:Reserva ;
           ex:reservaPaquete ?paquete ;
           ex:fechaInicio ?fecha ;
           ex:numeroViajeros ?personas .

  OPTIONAL {{ ?reserva ex:fechaReserva ?fecha_reserva . }}

  OPTIONAL {{
    ?reserva ex:tieneEstado ?estadoTerm .
    OPTIONAL {{ ?estadoTerm rdfs:label ?estadoLabel . }}
    OPTIONAL {{ ?estadoTerm ex:nombre ?estadoNombre . }}
    BIND(
      IF(
        isIRI(?estadoTerm),
        COALESCE(?estadoLabel, ?estadoNombre, STRAFTER(STR(?estadoTerm), "#")),
        STR(?estadoTerm)
      ) AS ?estadoFromTerm
    )
  }}
  BIND(COALESCE(?estadoFromTerm, "Pendiente") AS ?estado)

  OPTIONAL {{ ?paquete ex:nombre ?paquete_nombre . }}
  OPTIONAL {{ ?paquete ex:descripcion ?paquete_descripcion . }}
  OPTIONAL {{ ?paquete ex:urlImagen ?paquete_imagen . }}
  OPTIONAL {{ ?paquete ex:duracionDias ?duracion . }}
  BIND(STRAFTER(STR(?paquete), "#") AS ?paquete_id)
  
  OPTIONAL {{
    ?paquete ex:visitaDestino ?destino .
    OPTIONAL {{ ?destino rdfs:label ?destino_label . }}
    OPTIONAL {{ ?destino ex:nombre ?destino_nombre_raw . }}
    BIND(COALESCE(?destino_label, ?destino_nombre_raw, STRAFTER(STR(?destino), "#")) AS ?destino_nombre)
    OPTIONAL {{
      ?destino ex:ubicadoEn ?municipio .
      OPTIONAL {{ ?municipio rdfs:label ?municipio_label . }}
      OPTIONAL {{ ?municipio ex:nombre ?municipio_nombre_raw . }}
      BIND(COALESCE(?municipio_label, ?municipio_nombre_raw, STRAFTER(STR(?municipio), "#")) AS ?municipio_nombre)
    }}
    OPTIONAL {{ ?destino ex:latitud ?lat . }}
    OPTIONAL {{ ?destino ex:longitud ?lon . }}
    OPTIONAL {{ ?destino ex:urlImagen ?destino_imagen . }}
  }}

  OPTIONAL {{ ?paquete ex:tienePrecio/ex:precioPorPersona ?precio_from_spec . }}
  OPTIONAL {{ ?paquete ex:precioPersona ?precio_legacy . }}
  BIND(COALESCE(?precio_from_spec, ?precio_legacy, 0) AS ?precio_unitario)
  BIND(?precio_unitario * ?personas AS ?total_pagar)

  OPTIONAL {{
    ?paquete ex:ofrecidoPor ?comunidad .
    OPTIONAL {{ ?comunidad rdfs:label ?comunidadLabel . }}
    OPTIONAL {{ ?comunidad ex:nombre ?comunidadNombre . }}
    OPTIONAL {{ ?comunidad ex:nombreComunidad ?comunidadNombreLegacy . }}
    BIND(COALESCE(?comunidadLabel, ?comunidadNombre, ?comunidadNombreLegacy) AS ?comunidad_nombre)
  }}
}}
LIMIT 1
"""


def cancel_reservation(user_uri: str, reserva_id: str) -> str:
    usuario = resource(user_uri)
    reserva = local_resource(reserva_id)
    estado_cancelada = state_resource("Cancelada")
    return f"""{PREFIXES}
DELETE {{
  {reserva} ex:tieneEstado ?oldEstado .
}}
INSERT {{
  {estado_cancelada} rdf:type ex:EstadoReserva ;
                     rdfs:label {literal("Cancelada", lang="es")} ;
                     ex:nombre {literal("Cancelada")} .
  {reserva} ex:tieneEstado {estado_cancelada} .
}}
WHERE {{
  VALUES ?usuario {{ {usuario} }}
  {{
    ?usuario ex:realizaReserva {reserva} .
  }}
  UNION
  {{
    {reserva} ex:realizaReserva ?usuario .
  }}
  {reserva} rdf:type/rdfs:subClassOf* ex:Reserva .
  OPTIONAL {{ {reserva} ex:tieneEstado ?oldEstado . }}
}}
"""


def operator_reservations() -> str:
    return f"""{PREFIXES}
SELECT ?reserva ?paquete ?paquete_id ?paquete_nombre ?paquete_imagen ?fecha ?fecha_reserva
       ?personas ?estado ?precio_unitario ?total_pagar ?comunidad_nombre
       ?turista_nombre ?turista_email
WHERE {{
  ?reserva rdf:type/rdfs:subClassOf* ex:Reserva ;
           ex:reservaPaquete ?paquete ;
           ex:fechaInicio ?fecha ;
           ex:numeroViajeros ?personas .

  BIND(STRAFTER(STR(?paquete), "#") AS ?paquete_id)

  OPTIONAL {{ ?reserva ex:fechaReserva ?fecha_reserva . }}
  OPTIONAL {{ ?paquete ex:nombre ?paquete_nombre . }}
  OPTIONAL {{ ?paquete ex:urlImagen ?paquete_imagen . }}

  OPTIONAL {{
    ?reserva ex:tieneEstado ?estadoTerm .
    OPTIONAL {{ ?estadoTerm rdfs:label ?estadoLabel . }}
    OPTIONAL {{ ?estadoTerm ex:nombre ?estadoNombre . }}
    BIND(
      IF(
        isIRI(?estadoTerm),
        COALESCE(?estadoLabel, ?estadoNombre, STRAFTER(STR(?estadoTerm), "#")),
        STR(?estadoTerm)
      ) AS ?estadoFromTerm
    )
  }}
  BIND(COALESCE(?estadoFromTerm, "Pendiente") AS ?estado)

  OPTIONAL {{ ?paquete ex:tienePrecio/ex:precioPorPersona ?precio_from_spec . }}
  OPTIONAL {{ ?paquete ex:precioPersona ?precio_legacy . }}
  BIND(COALESCE(?precio_from_spec, ?precio_legacy, 0) AS ?precio_unitario)
  BIND(?precio_unitario * ?personas AS ?total_pagar)

  OPTIONAL {{
    ?paquete ex:ofrecidoPor ?comunidad .
    OPTIONAL {{ ?comunidad rdfs:label ?comunidadLabel . }}
    OPTIONAL {{ ?comunidad ex:nombre ?comunidadNombre . }}
    OPTIONAL {{ ?comunidad ex:nombreComunidad ?comunidadNombreLegacy . }}
    BIND(COALESCE(?comunidadLabel, ?comunidadNombre, ?comunidadNombreLegacy) AS ?comunidad_nombre)
  }}

  OPTIONAL {{
    {{
      ?turista ex:realizaReserva ?reserva .
    }}
    UNION
    {{
      ?reserva ex:realizaReserva ?turista .
    }}
    OPTIONAL {{ ?turista ex:nombre ?turista_nombre_raw . }}
    OPTIONAL {{ ?turista rdfs:label ?turista_label . }}
    OPTIONAL {{ ?turista ex:email ?turista_email . }}
    BIND(COALESCE(?turista_nombre_raw, ?turista_label, STRAFTER(STR(?turista), "#")) AS ?turista_nombre)
  }}
}}
ORDER BY DESC(?fecha)
"""


def reservation_exists(reserva_id: str) -> str:
    reserva = local_resource(reserva_id)
    return f"""{PREFIXES}
SELECT ?reserva
WHERE {{
  VALUES ?reserva {{ {reserva} }}
  ?reserva rdf:type/rdfs:subClassOf* ex:Reserva .
}}
LIMIT 1
"""


def set_reservation_state(reserva_id: str, estado: str) -> str:
    reserva = local_resource(reserva_id)
    estado_recurso = state_resource(estado)
    estado_label = estado.capitalize()
    return f"""{PREFIXES}
DELETE {{
  {reserva} ex:tieneEstado ?oldEstado .
}}
INSERT {{
  {estado_recurso} rdf:type ex:EstadoReserva ;
                   rdfs:label {literal(estado_label, lang="es")} ;
                   ex:nombre {literal(estado_label)} .
  {reserva} ex:tieneEstado {estado_recurso} .
}}
WHERE {{
  {reserva} rdf:type/rdfs:subClassOf* ex:Reserva .
  OPTIONAL {{ {reserva} ex:tieneEstado ?oldEstado . }}
}}
"""
