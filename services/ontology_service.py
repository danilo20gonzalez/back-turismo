import asyncio

from sparql_client import SparqlClient
from sparql_queries import busqueda as busqueda_queries
from services.intent_detector import (
    detectar_intencion,
    generar_queries_segun_intencion,
)


QUERY_TIMEOUT = 25.0


# ─── mapeo nombre_query -> (función_query, parser_resultados) ──────────────

_QUERY_FUNCTIONS = {
    "paquetes": busqueda_queries.busqueda_paquetes,
    "destinos": busqueda_queries.busqueda_destinos,
    "sitios": busqueda_queries.busqueda_sitios,
    "servicios": busqueda_queries.busqueda_servicios,
    "servicios_aventura": busqueda_queries.busqueda_servicios_aventura,
}


def _parse_resultados(resultados: list, categoria: str) -> list[dict]:
    """Convierte bindings SPARQL a diccionarios limpios."""
    items = []
    for r in resultados:
        item = {
            "uri": r.get("sujeto", {}).get("value", ""),
            "nombre": r.get("nombre", {}).get("value", "Sin nombre"),
            "descripcion": r.get("descripcion", {}).get("value", ""),
        }

        if categoria == "paquetes":
            item["precio"] = r.get("precio", {}).get("value")
            item["moneda"] = r.get("moneda", {}).get("value", "COP")
            item["duracion"] = r.get("duracion", {}).get("value")
            item["capacidad"] = r.get("capacidad", {}).get("value")
            item["dificultad"] = r.get("dificultad", {}).get("value")
            item["destinos"] = r.get("destinos", {}).get("value", "")
            item["municipios"] = r.get("municipios", {}).get("value", "")

        elif categoria in ("destinos", "sitios"):
            item["municipio"] = r.get("municipio", {}).get("value", "")
            item["capacidad"] = r.get("capacidad", {}).get("value")
            item["tipos"] = r.get("tipos", {}).get("value", "")

        elif categoria in ("servicios", "servicios_aventura"):
            item["tipo"] = r.get("tipoNombre", {}).get("value", "")
            item["destinos"] = r.get("destinos", {}).get("value", "")

        items.append(item)
    return items


def _generar_resumen(intencion: dict, datos: dict) -> str:
    """Genera un resumen narrativo a partir de los datos estructurados."""
    partes = []

    paquetes = datos.get("paquetes", [])
    destinos = datos.get("destinos", [])
    sitios = datos.get("sitios", [])
    servicios = datos.get("servicios", [])

    if paquetes:
        partes.append("Paquetes turisticos disponibles:")
        for p in paquetes[:3]:
            linea = f"- {p['nombre']}"
            if p.get("precio"):
                linea += f": ${p['precio']} {p.get('moneda', 'COP')}"
            if p.get("duracion"):
                linea += f", {p['duracion']} dias"
            if p.get("dificultad"):
                linea += f", dificultad: {p['dificultad']}"
            partes.append(linea)

    if destinos:
        partes.append("Destinos encontrados:")
        for d in destinos[:3]:
            linea = f"- {d['nombre']}"
            if d.get("municipio"):
                linea += f" en {d['municipio']}"
            partes.append(linea)

    if sitios:
        partes.append("Sitios de interes:")
        for s in sitios[:3]:
            linea = f"- {s['nombre']}"
            if s.get("municipio"):
                linea += f" ({s['municipio']})"
            partes.append(linea)

    if servicios:
        partes.append("Servicios disponibles:")
        for s in servicios[:3]:
            linea = f"- {s['nombre']}"
            if s.get("tipo"):
                linea += f" ({s['tipo']})"
            partes.append(linea)

    if not partes:
        intencion_nombre = intencion.get("intencion", "general")
        if intencion_nombre == "consulta_paquetes":
            return ("No encontre paquetes exactamente como lo describes, "
                    "pero puedo sugerirte otras opciones turisticas del Caqueta.")
        elif intencion_nombre == "consulta_destinos":
            return ("No encontre destinos con ese nombre exacto, "
                    "pero el Caqueta tiene muchos lugares maravillosos por descubrir.")
        elif intencion_nombre == "consulta_actividades":
            return ("No hay actividades registradas exactamente con ese nombre, "
                    "pero la region ofrece ecoturismo, cultura y gastronomia unicos.")
        elif intencion_nombre == "consulta_servicios":
            return ("No encontre servicios especificos para esa busqueda, "
                    "pero hay hospedaje, alimentacion y guias disponibles en la region.")
        return ("Actualmente no contamos con registros especificos para esa solicitud "
                "en nuestra guia oficial, pero la Amazonia colombiana tiene mucho por ofrecer "
                "en ecoturismo, aventura y cultura local.")

    return " | ".join(partes)


async def obtener_contexto_desde_fuseki(mensaje_usuario: str) -> dict:
    """
    Analiza la intención del usuario, ejecuta queries SPARQL específicas
    en paralelo y devuelve un contexto estructurado.
    """
    if not mensaje_usuario or not mensaje_usuario.strip():
        return {
            "type": "structured",
            "intencion": "consulta_general",
            "consulta_original": mensaje_usuario,
            "resumen": "Por favor escribe un mensaje para poder ayudarte.",
            "datos": {},
            "total_resultados": 0,
            "fallback": True,
        }

    # 1. Detectar intención
    intencion = detectar_intencion(mensaje_usuario)
    queries_a_ejecutar = generar_queries_segun_intencion(intencion)

    # 2. Ejecutar queries en paralelo
    sparql = SparqlClient()
    resultados = {}

    async def _ejecutar_una(categoria: str):
        query_fn = _QUERY_FUNCTIONS.get(categoria)
        if not query_fn:
            return categoria, []
        try:
            query_str = query_fn(mensaje_usuario)
            bindings = await sparql.execute_select_async(query_str, timeout=QUERY_TIMEOUT)
            return categoria, _parse_resultados(bindings, categoria)
        except Exception as e:
            print(f"Error en query '{categoria}': {e}")
            return categoria, []

    tareas = [_ejecutar_una(cat) for cat in queries_a_ejecutar]
    for cat, items in await asyncio.gather(*tareas):
        resultados[cat] = items

    # 3. Normalizar nombres de categorías para la salida
    datos = {}
    mapeo_salida = {
        "paquetes": "paquetes",
        "destinos": "destinos",
        "sitios": "destinos",
        "servicios": "servicios",
        "servicios_aventura": "servicios",
    }
    for cat_interna, items in resultados.items():
        cat_salida = mapeo_salida.get(cat_interna, cat_interna)
        if cat_salida not in datos:
            datos[cat_salida] = []
        datos[cat_salida].extend(items)

    total = sum(len(v) for v in datos.values())

    # 4. Generar resumen narrativo
    resumen = _generar_resumen(intencion, datos)

    return {
        "type": "structured",
        "intencion": intencion["intencion"],
        "consulta_original": mensaje_usuario,
        "resumen": resumen,
        "datos": datos,
        "total_resultados": total,
        "fallback": total == 0,
    }
