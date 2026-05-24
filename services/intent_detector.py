import re
import unicodedata


SINONIMOS = {
    "aventura": ["aventura", "ecoturismo", "trekking", "senderismo", "caminata", "excursion", "expedicion", "exploracion", "naturaleza"],
    "cultura": ["cultura", "museo", "historia", "tradicion", "artesania", "folclor", "patrimonio", "costumbre"],
    "gastronomia": ["gastronomia", "comida", "restaurante", "plato", "cocina", "gourmet", "culinario"],
    "alojamiento": ["alojamiento", "hospedaje", "hotel", "cabin", "cabaña", "hostal", "alberge", "posada", "dormir"],
    "transporte": ["transporte", "bus", "taxi", "lancha", "vuelo", "traslado", "movilidad"],
    "guia": ["guia", "tour", "acompañante", "acompanante", "interpretacion", "interpretación"],
    "precio": ["precio", "cuesta", "costo", "valor", "tarifa", "pagar", "cobran", "economico", "economico", "barato", "caro"],
    "duracion": ["duracion", "dias", "semanas", "meses", "horas", "cuanto dura", "cuanto tiempo"],
    "dificultad": ["dificultad", "facil", "facil", "moderado", "dificil", "dificil", "extremo", "nivel"],
    "florencia": ["florencia"],
    "caqueta": ["caqueta", "caquetá"],
    "municipio": ["municipio", "pueblo", "localidad", "vereda", "corregimiento"],
}

INTENCIONES = {
    "consulta_paquetes": {
        "peso": 10,
        "palabras": [
            "paquete", "plan", "tour", "viaje", "viajar", "paquetes", "planes",
            "promocion", "oferta", "itinerario", "incluye", "incluye",
        ],
        "sinonimos": ["precio", "duracion", "dificultad", "aventura", "cultura", "gastronomia"],
    },
    "consulta_destinos": {
        "peso": 10,
        "palabras": [
            "destino", "destinos", "lugar", "lugares", "donde", "dónde", "sitio", "sitios",
            "municipio", "municipios", "pueblo", "pueblos", "ciudad", "ciudades",
            "visitar", "conocer", "recorrer",
            "florencia", "caqueta", "caquetá",
        ],
        "sinonimos": ["municipio", "florencia", "caqueta"],
    },
    "consulta_actividades": {
        "peso": 10,
        "palabras": [
            "actividad", "actividades", "que hacer", "qué hacer", "hacer",
            "experiencia", "experiencias", "recreacion", "diversion", "diversión",
            "paseo", "paseos", "recorrido", "recorridos",
            "ecoturismo", "aventura", "naturaleza", "cultura", "relajacion",
        ],
        "sinonimos": ["aventura", "cultura", "gastronomia"],
    },
    "consulta_servicios": {
        "peso": 10,
        "palabras": [
            "servicio", "servicios", "hospedaje", "alojamiento", "comida",
            "restaurante", "transporte", "guia", "guías", "guia turistico",
            "alquiler", "renta", "transporte",
        ],
        "sinonimos": ["alojamiento", "transporte", "guia", "gastronomia"],
    },
    "consulta_general": {
        "peso": 1,
        "palabras": [],
        "sinonimos": [],
        "fallback": True,
    },
}


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def _extraer_palabras(texto: str) -> list[str]:
    normalizado = _normalizar(texto)
    return re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]+", normalizado)


def _tiene_palabras(mensaje: str, palabras: list[str]) -> bool:
    msg_normalized = _normalizar(mensaje)
    for palabra in palabras:
        if palabra in msg_normalized:
            return True
    return False


def _tiene_sinonimos(mensaje: str, categorias: list[str]) -> bool:
    msg_normalized = _normalizar(mensaje)
    for cat in categorias:
        for sin in SINONIMOS.get(cat, []):
            sin_normalized = _normalizar(sin)
            if sin_normalized in msg_normalized:
                return True
    return False


def detectar_intencion(mensaje: str) -> dict:
    mensaje_normalized = _normalizar(mensaje)
    palabras = _extraer_palabras(mensaje)

    puntajes = {}
    entidades = []

    for nombre_intencion, config in INTENCIONES.items():
        if config.get("fallback"):
            continue

        score = 0

        for palabra_clave in config["palabras"]:
            pk_normalized = _normalizar(palabra_clave)
            if pk_normalized in mensaje_normalized:
                score += 2

        if _tiene_sinonimos(mensaje, config.get("sinonimos", [])):
            score += 1

        if score > 0:
            puntajes[nombre_intencion] = score

    # Detectar entidades específicas
    tipos_destino = ["ecoturistico", "cultural", "aventura", "naturaleza",
                     "playa", "rio", "rural", "urbano"]
    for tipo in tipos_destino:
        if _normalizar(tipo) in mensaje_normalized:
            entidades.append({"tipo": "tipo_destino", "valor": tipo})

    # Detectar menciones de precio
    precio_patterns = [
        (r"(\d[\d.]*)\s*(mil|pesos|cop|$)", "precio"),
        (r"(barato|economico|economico|caro|costoso|gratis)", "rango_precio"),
    ]
    for pattern, tipo in precio_patterns:
        if re.search(pattern, mensaje.lower()):
            if tipo == "precio":
                match = re.search(r"(\d[\d.]*)", mensaje)
                if match:
                    entidades.append({"tipo": tipo, "valor": match.group(1)})
            else:
                entidades.append({"tipo": tipo, "valor": re.search(pattern, mensaje.lower()).group(1)})

    # Detectar duración
    duracion_pattern = r"(\d+)\s*(dia|dias|día|días|noche|noches|semana|horas|hora)"
    match = re.search(duracion_pattern, mensaje.lower())
    if match:
        entidades.append({"tipo": "duracion", "valor": match.group(0)})

    # Detectar capacidad
    cap_pattern = r"(para|hasta|maximo)\s*(\d+)\s*(persona|personas|pax)"
    match = re.search(cap_pattern, mensaje.lower())
    if match:
        entidades.append({"tipo": "capacidad", "valor": match.group(2)})

    # Elegir mejor intención
    if not puntajes:
        intencion = "consulta_general"
    else:
        intencion = max(puntajes, key=puntajes.get)

    return {
        "intencion": intencion,
        "puntajes": puntajes,
        "entidades": entidades,
        "mensaje_normalizado": mensaje_normalized,
    }


def generar_queries_segun_intencion(intencion: dict) -> list[str]:
    mapping = {
        "consulta_paquetes": ["paquetes"],
        "consulta_destinos": ["destinos", "sitios"],
        "consulta_actividades": ["servicios_aventura", "destinos", "paquetes"],
        "consulta_servicios": ["servicios"],
        "consulta_general": ["paquetes", "destinos", "sitios", "servicios"],
    }
    return mapping.get(intencion["intencion"], ["paquetes", "destinos", "sitios", "servicios"])
