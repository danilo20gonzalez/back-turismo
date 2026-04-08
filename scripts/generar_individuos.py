import os
import random
from datetime import date, datetime, timedelta

import httpx
from rdflib import Graph

# ---------------------------------------------
# Script de carga masiva (estricto con ontologia.owl)
# ---------------------------------------------
# Comentarios en espanol, codigo en ingles (convencion del proyecto)

FUSEKI_UPDATE = os.getenv("FUSEKI_UPDATE", "http://localhost:3030/amaturis/update")

PREFIXES = """\
PREFIX ex: <http://amaturis.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

TURTLE_PREFIXES = """\
@prefix ex: <http://amaturis.org/ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""

# Si se activa, crea individuos extra (EstadoReserva y EspecificacionPrecio).
INCLUIR_ESTADOS = True
INCLUIR_PRECIOS = True

# Si se activa, genera un archivo .owl con los individuos creados
GENERAR_OWL = True
OUTPUT_OWL = os.getenv("OUTPUT_OWL", "scripts/individuos_generados.owl")

# Cantidades base (ajustadas para incluir individuos extra)
CANT_COMUNIDADES = 50
CANT_PAQUETES = 300
CANT_TURISTAS = 200  # 300 - 100
CANT_RESERVAS = 230  # 330 - 100

# Municipios reales del Caquetá (sin tildes para mantener ASCII)
MUNICIPIOS_CAQUETA = [
    "Albania",
    "Belen de los Andaquies",
    "Cartagena del Chaira",
    "Curillo",
    "El Doncello",
    "El Paujil",
    "Florencia",
    "La Montanita",
    "Milan",
    "Morelia",
    "Puerto Rico",
    "San Jose del Fragua",
    "San Vicente del Caguan",
    "Solano",
    "Solita",
    "Valparaiso",
]

# Destinos base (puedes reemplazar por nombres oficiales si lo necesitas)
DESTINOS_CAQUETA = [
    {"nombre": "Rio Hacha", "tipo": "Rio", "municipio": "Florencia"},
    {"nombre": "Rio Orteguaza", "tipo": "Rio", "municipio": "Florencia"},
    {"nombre": "Cascada El Avispero", "tipo": "Cascada", "municipio": "Florencia"},
    {
        "nombre": "Reserva Natural El Danubio",
        "tipo": "ReservaNatural",
        "municipio": "Belen de los Andaquies",
    },
    {
        "nombre": "Parque Nacional Natural Alto Fragua Indi Wasi",
        "tipo": "ParqueNatural",
        "municipio": "San Jose del Fragua",
    },
    {
        "nombre": "Parque Nacional Natural Serrania de Chiribiquete",
        "tipo": "ParqueNatural",
        "municipio": "Solano",
    },
    {
        "nombre": "Parque Nacional Natural Cordillera de los Picachos",
        "tipo": "ParqueNatural",
        "municipio": "San Vicente del Caguan",
    },
    {"nombre": "Rio Caguan", "tipo": "Rio", "municipio": "San Vicente del Caguan"},
    {
        "nombre": "Reserva Natural El Paujil",
        "tipo": "ReservaNatural",
        "municipio": "El Paujil",
    },
    {
        "nombre": "Sendero Ecoturistico La Montanita",
        "tipo": "RecursoNatural",
        "municipio": "La Montanita",
    },
    {
        "nombre": "Mirador de Albania",
        "tipo": "RecursoNatural",
        "municipio": "Albania",
    },
    {
        "nombre": "Maloca Cultural del Chaira",
        "tipo": "RecursoCultural",
        "municipio": "Cartagena del Chaira",
    },
    {
        "nombre": "Reserva Natural Curillo",
        "tipo": "ReservaNatural",
        "municipio": "Curillo",
    },
    {
        "nombre": "Ruta Ecologica de Solita",
        "tipo": "RecursoNatural",
        "municipio": "Solita",
    },
    {
        "nombre": "Sendero Ecoturistico de Milan",
        "tipo": "RecursoNatural",
        "municipio": "Milan",
    },
    {
        "nombre": "Reserva Natural Morelia",
        "tipo": "ReservaNatural",
        "municipio": "Morelia",
    },
    {
        "nombre": "Parque Ecologico Valparaiso",
        "tipo": "RecursoNatural",
        "municipio": "Valparaiso",
    },
    {
        "nombre": "Sendero Ecoturistico El Doncello",
        "tipo": "RecursoNatural",
        "municipio": "El Doncello",
    },
]

CANT_MUNICIPIOS = len(MUNICIPIOS_CAQUETA)

SERVICIOS_TURISTICOS = [
    {
        "nombre": "Senderismo en la selva",
        "tipo": "ActividadTuristica",
        "descripcion": "Caminata guiada por senderos naturales.",
    },
    {
        "nombre": "Nado en el canon",
        "tipo": "ActividadTuristica",
        "descripcion": "Nado en pozos naturales y rios tranquilos.",
    },
    {
        "nombre": "Avistamiento de aves",
        "tipo": "ActividadTuristica",
        "descripcion": "Observacion de aves endemicas con guia.",
    },
    {
        "nombre": "Ruta en canoa",
        "tipo": "ActividadTuristica",
        "descripcion": "Recorrido fluvial en canoa tradicional.",
    },
    {
        "nombre": "Fotografia de naturaleza",
        "tipo": "ActividadTuristica",
        "descripcion": "Salida fotografica en ecosistemas del Caqueta.",
    },
    {
        "nombre": "Guia local certificado",
        "tipo": "GuiaTuristico",
        "descripcion": "Acompanamiento por guia local certificado.",
    },
    {
        "nombre": "Hospedaje eco lodge",
        "tipo": "Hospedaje",
        "descripcion": "Alojamiento en eco lodge con servicios basicos.",
    },
    {
        "nombre": "Hospedaje rural",
        "tipo": "Hospedaje",
        "descripcion": "Hospedaje rural con comunidad anfitriona.",
    },
    {
        "nombre": "Restaurante tipico",
        "tipo": "Restaurante",
        "descripcion": "Comidas tradicionales de la region.",
    },
    {
        "nombre": "Restaurante vegetariano",
        "tipo": "Restaurante",
        "descripcion": "Opciones vegetarianas y saludables.",
    },
    {
        "nombre": "Transporte fluvial",
        "tipo": "Transporte",
        "descripcion": "Traslado en lancha por rios principales.",
    },
    {
        "nombre": "Transporte terrestre",
        "tipo": "Transporte",
        "descripcion": "Traslado terrestre entre municipios.",
    },
]

# Rango aproximado de coordenadas para Caqueta (placeholder)
LAT_RANGE = (0.2, 2.6)
LON_RANGE = (-75.8, -71.0)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)


# --------------------------
# Helpers SPARQL
# --------------------------
def _escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def lit_str(value: str) -> str:
    return f"\"{_escape_literal(value)}\""


def lit_int(value: int) -> str:
    return f"\"{value}\"^^xsd:integer"


def lit_float(value: float) -> str:
    return f"\"{value:.2f}\"^^xsd:float"

def lit_decimal(value: float) -> str:
    return f"\"{value:.6f}\"^^xsd:decimal"


def lit_bool(value: bool) -> str:
    return f"\"{'true' if value else 'false'}\"^^xsd:boolean"


def lit_date(value: date) -> str:
    return f"\"{value.isoformat()}\"^^xsd:date"


def lit_datetime(value: datetime) -> str:
    return f"\"{value.isoformat()}\"^^xsd:dateTime"


def post_update(blocks: list[str]) -> None:
    if not blocks:
        return

    query = PREFIXES + "INSERT DATA {\n" + "\n".join(blocks) + "\n}"
    response = httpx.post(
        FUSEKI_UPDATE,
        content=query,
        headers={"Content-Type": "application/sparql-update"},
        timeout=60.0,
    )
    if response.status_code >= 300:
        raise RuntimeError(
            f"Fuseki error {response.status_code}: {response.text[:500]}"
        )


def insert_in_batches(blocks: list[str], batch_size: int = 100) -> None:
    buffer: list[str] = []
    for block in blocks:
        buffer.append(block)
        if len(buffer) >= batch_size:
            post_update(buffer)
            buffer = []
    if buffer:
        post_update(buffer)

def write_owl(blocks: list[str], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    turtle = TURTLE_PREFIXES + "\n" + "\n".join(blocks) + "\n"
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    graph.serialize(destination=output_path, format="xml")


# --------------------------
# Generadores de individuos
# --------------------------
def generar_departamento_caqueta() -> list[str]:
    return [
        "\n".join(
            [
                "ex:Departamento_Caqueta a ex:Departamento ;",
                f"  rdfs:label {lit_str('Caqueta')} ;",
                f"  rdfs:comment {lit_str('Departamento del Caqueta')} .",
            ]
        )
    ]


def generar_municipios(nombres: list[str]) -> tuple[list[str], dict[str, int]]:
    blocks: list[str] = []
    mapa: dict[str, int] = {}
    for i, nombre in enumerate(nombres, start=1):
        mapa[nombre] = i
        blocks.append(
            "\n".join(
                [
                    f"ex:Municipio_{i:03d} a ex:Municipio ;",
                    f"  rdfs:label {lit_str(nombre)} ;",
                    f"  rdfs:comment {lit_str(f'Municipio del Caqueta: {nombre}')} ;",
                    "  ex:ubicadoEn ex:Departamento_Caqueta .",
                ]
            )
        )
    return blocks, mapa


def generar_comunidades(cantidad: int = 50, municipios: int = 20) -> list[str]:
    blocks: list[str] = []
    for i in range(1, cantidad + 1):
        municipio_id = random.randint(1, municipios)
        blocks.append(
            "\n".join(
                [
                    f"ex:Comunidad_{i:03d} a ex:Comunidad ;",
                    f"  rdfs:label {lit_str(f'Comunidad {i}')} ;",
                    f"  rdfs:comment {lit_str(f'Comunidad generada {i}')} ;",
                    f"  ex:comunidadUbicadaEn ex:Municipio_{municipio_id:03d} .",
                ]
            )
        )
    return blocks


def generar_servicios(servicios: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    ids: list[str] = []
    for i, servicio in enumerate(servicios, start=1):
        servicio_id = f"ex:Servicio_{i:03d}"
        ids.append(servicio_id)
        nombre = servicio["nombre"]
        tipo = servicio["tipo"]
        descripcion = servicio["descripcion"]
        blocks.append(
            "\n".join(
                [
                    f"{servicio_id} a ex:ServicioTuristico , ex:{tipo} ;",
                    f"  ex:nombre {lit_str(nombre)} ;",
                    f"  ex:descripcion {lit_str(descripcion)} ;",
                    f"  rdfs:label {lit_str(nombre)} .",
                ]
            )
        )
    return blocks, ids


def generar_itinerarios(cantidad: int = 300) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    ids: list[str] = []
    for i in range(1, cantidad + 1):
        itinerario_id = f"ex:Itinerario_{i:04d}"
        ids.append(itinerario_id)
        blocks.append(
            "\n".join(
                [
                    f"{itinerario_id} a ex:Itinerario ;",
                    f"  rdfs:label {lit_str(f'Itinerario del paquete {i}')} ;",
                    f"  rdfs:comment {lit_str(f'Resumen del itinerario para el paquete {i}')} .",
                ]
            )
        )
    return blocks, ids


def generar_relaciones_itinerario(cantidad: int, itinerarios: list[str]) -> list[str]:
    blocks: list[str] = []
    for i in range(1, cantidad + 1):
        itinerario_id = itinerarios[i - 1]
        blocks.append(
            f"ex:Paquete_{i:04d} ex:tieneItinerario {itinerario_id} ."
        )
    return blocks


def generar_destinos(destinos: list[dict[str, str]], municipios: dict[str, int]) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    ids: list[str] = []
    for i, destino in enumerate(destinos, start=1):
        nombre = destino["nombre"]
        tipo = destino["tipo"]
        municipio_nombre = destino["municipio"]
        municipio_id = municipios.get(municipio_nombre)
        if not municipio_id:
            raise ValueError(f"Municipio no encontrado para destino: {nombre}")

        lat = random.uniform(*LAT_RANGE)
        lon = random.uniform(*LON_RANGE)

        destino_id = f"ex:Destino_{i:03d}"
        ids.append(destino_id)

        blocks.append(
            "\n".join(
                [
                    f"{destino_id} a ex:DestinoTuristico , ex:{tipo} ;",
                    f"  ex:nombre {lit_str(nombre)} ;",
                    f"  ex:descripcion {lit_str(f'Destino turistico en {municipio_nombre}')} ;",
                    f"  rdfs:label {lit_str(nombre)} ;",
                    f"  ex:capacidadCargaDiaria {lit_int(random.randint(50, 300))} ;",
                    f"  ex:latitud {lit_decimal(lat)} ;",
                    f"  ex:longitud {lit_decimal(lon)} ;",
                    f"  ex:ubicadoEn ex:Municipio_{municipio_id:03d} .",
                ]
            )
        )

    return blocks, ids


def generar_paquetes(
    cantidad: int = 300,
    destinos: list[str] | None = None,
    servicios: list[str] | None = None,
) -> list[str]:
    blocks: list[str] = []
    destinos = destinos or []
    servicios = servicios or []
    for i in range(1, cantidad + 1):
        duracion = random.randint(1, 7)
        capacidad = random.randint(5, 25)
        todo_incluido = random.choice([True, False])

        destinos_elegidos: list[str] = []
        if destinos:
            max_destinos = min(3, len(destinos))
            destinos_elegidos = random.sample(destinos, k=random.randint(1, max_destinos))

        servicios_elegidos: list[str] = []
        if servicios:
            max_servicios = min(3, len(servicios))
            servicios_elegidos = random.sample(servicios, k=random.randint(1, max_servicios))

        lines = [
            f"ex:Paquete_{i:04d} a ex:PaqueteTuristico ;",
            f"  ex:nombre {lit_str(f'Paquete {i}')} ;",
            f"  ex:descripcion {lit_str(f'Descripcion del paquete {i}')} ;",
            f"  ex:duracionDias {lit_int(duracion)} ;",
            f"  ex:capacidadMaxPersonas {lit_int(capacidad)} ;",
            f"  ex:esTodoIncluido {lit_bool(todo_incluido)} ;",
            f"  ex:incluyeDescripcion {lit_str('Servicios y actividades incluidas')} ;",
            f"  ex:noIncluye {lit_str('Gastos personales y transporte externo')} ;",
        ]

        for destino_id in destinos_elegidos:
            lines.append(f"  ex:visitaDestino {destino_id} ;")

        for servicio_id in servicios_elegidos:
            lines.append(f"  ex:incluyeServicio {servicio_id} ;")

        lines[-1] = lines[-1].rstrip(" ;") + " ."
        blocks.append("\n".join(lines))
    return blocks


def generar_precios(cantidad: int = 300) -> list[str]:
    blocks: list[str] = []
    for i in range(1, cantidad + 1):
        valor = random.randint(120000, 1800000)
        blocks.append(
            "\n".join(
                [
                    f"ex:Precio_{i:04d} a ex:EspecificacionPrecio ;",
                    f"  ex:precioPorPersona {lit_float(float(valor))} ;",
                    f"  ex:moneda {lit_str('COP')} .",
                    f"ex:Paquete_{i:04d} ex:tienePrecio ex:Precio_{i:04d} .",
                ]
            )
        )
    return blocks


def generar_turistas(cantidad: int = 300) -> list[str]:
    blocks: list[str] = []
    for i in range(1, cantidad + 1):
        blocks.append(
            "\n".join(
                [
                    f"ex:Turista_{i:04d} a ex:Turista ;",
                    f"  ex:nombre {lit_str(f'Turista {i}')} ;",
                    f"  ex:email {lit_str(f'turista{i}@mail.com')} ;",
                    f"  ex:nacionalidad {lit_str('CO')} .",
                ]
            )
        )
    return blocks


def generar_estados_reserva() -> list[str]:
    estados = ["Confirmada", "Pendiente", "Cancelada"]
    blocks: list[str] = []
    for estado in estados:
        blocks.append(
            "\n".join(
                [
                    f"ex:EstadoReserva_{estado} a ex:EstadoReserva ;",
                    f"  rdfs:label {lit_str(estado)} .",
                ]
            )
        )
    return blocks


def generar_reservas(cantidad: int = 330, paquetes: int = 300, turistas: int = 300) -> list[str]:
    blocks: list[str] = []
    base_date = date(2026, 1, 1)
    base_datetime = datetime(2026, 1, 1, 9, 0, 0)

    estados = ["Confirmada", "Pendiente", "Cancelada"]

    for i in range(1, cantidad + 1):
        paquete_id = random.randint(1, paquetes)
        turista_id = random.randint(1, turistas)

        inicio = base_date + timedelta(days=random.randint(1, 180))
        fin = inicio + timedelta(days=random.randint(0, 6))
        reserva_dt = base_datetime + timedelta(days=random.randint(0, 180), hours=random.randint(0, 6))

        viajeros = random.randint(1, 6)
        monto_pagado = float(random.randint(0, 2000000))
        monto_pendiente = max(0.0, float(random.randint(0, 2000000) - monto_pagado))

        estado = random.choice(estados)

        reserva_block = [
            f"ex:Reserva_{i:04d} a ex:Reserva ;",
            f"  ex:reservaPaquete ex:Paquete_{paquete_id:04d} ;",
            f"  ex:numeroViajeros {lit_int(viajeros)} ;",
            f"  ex:fechaInicio {lit_date(inicio)} ;",
            f"  ex:fechaFin {lit_date(fin)} ;",
            f"  ex:fechaReserva {lit_datetime(reserva_dt)} ;",
            f"  ex:montoPagado {lit_float(monto_pagado)} ;",
            f"  ex:montoPendiente {lit_float(monto_pendiente)} .",
            f"ex:Turista_{turista_id:04d} ex:realizaReserva ex:Reserva_{i:04d} .",
        ]

        if INCLUIR_ESTADOS:
            reserva_block.insert(
                -2,
                f"  ex:tieneEstado ex:EstadoReserva_{estado} ;",
            )

        blocks.append("\n".join(reserva_block))

    return blocks


def main() -> None:
    print("Generando individuos (estrictos con ontologia.owl)...")

    # 1) Territorio base, municipios y comunidades
    departamento = generar_departamento_caqueta()
    municipios, mapa_municipios = generar_municipios(MUNICIPIOS_CAQUETA)
    comunidades = generar_comunidades(CANT_COMUNIDADES, municipios=CANT_MUNICIPIOS)

    # 2) Destinos turisticos
    destinos, ids_destinos = generar_destinos(DESTINOS_CAQUETA, mapa_municipios)

    # 3) Servicios turisticos
    servicios, ids_servicios = generar_servicios(SERVICIOS_TURISTICOS)

    # 4) Paquetes (y precios opcionales)
    paquetes = generar_paquetes(
        CANT_PAQUETES, destinos=ids_destinos, servicios=ids_servicios
    )
    precios = generar_precios(CANT_PAQUETES) if INCLUIR_PRECIOS else []

    # 5) Turistas
    turistas = generar_turistas(CANT_TURISTAS)

    # 6) Itinerarios
    itinerarios, ids_itinerarios = generar_itinerarios(CANT_PAQUETES)
    relaciones_itinerario = generar_relaciones_itinerario(
        CANT_PAQUETES, ids_itinerarios
    )

    # 7) Estados y Reservas
    estados = generar_estados_reserva() if INCLUIR_ESTADOS else []
    reservas = generar_reservas(
        CANT_RESERVAS, paquetes=CANT_PAQUETES, turistas=CANT_TURISTAS
    )

    # Generar .owl local
    if GENERAR_OWL:
        write_owl(
            departamento
            + municipios
            + destinos
            + servicios
            + comunidades
            + paquetes
            + precios
            + turistas
            + itinerarios
            + relaciones_itinerario
            + estados
            + reservas,
            OUTPUT_OWL,
        )
        print(f"Archivo .owl generado en: {OUTPUT_OWL}")

    # Insertar en Fuseki
    insert_in_batches(departamento, batch_size=5)
    insert_in_batches(municipios, batch_size=50)
    insert_in_batches(destinos, batch_size=50)
    insert_in_batches(servicios, batch_size=50)
    insert_in_batches(comunidades, batch_size=50)
    insert_in_batches(paquetes, batch_size=75)
    if precios:
        insert_in_batches(precios, batch_size=75)
    insert_in_batches(turistas, batch_size=75)
    insert_in_batches(itinerarios, batch_size=75)
    insert_in_batches(relaciones_itinerario, batch_size=75)
    if estados:
        insert_in_batches(estados, batch_size=10)
    insert_in_batches(reservas, batch_size=60)

    print("Carga finalizada.")


if __name__ == "__main__":
    main()
