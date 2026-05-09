import httpx
from config import settings
from sparql_client import SparqlClient

# services/ontology_service.py
async def obtener_contexto_desde_fuseki(mensaje_usuario: str):
    """
    Realiza una búsqueda transversal en la ontología para encontrar paquetes, destinos, sitios y servicios
    relacionados con el mensaje del usuario. Combina los resultados en un string narrativo.
    """
    sparql_client = SparqlClient()

    try:
        # Ejecutar consulta transversal
        resultados = sparql_client.execute_query("busqueda_transversal", {"busqueda": mensaje_usuario})

        if not resultados:
            # Humanizar respuesta de fallback
            return "Actualmente no contamos con registros específicos para esa solicitud en nuestra guía oficial, pero la Amazonia colombiana tiene mucho por ofrecer en ecoturismo, aventura y cultura local."

        # Combinar resultados en un string narrativo
        contexto = "Información oficial de AmaTuris: "

        paquetes = [r for r in resultados if r.get('tipo', {}).get('value') == 'Paquete']
        destinos = [r for r in resultados if r.get('tipo', {}).get('value') == 'Destino']
        sitios = [r for r in resultados if r.get('tipo', {}).get('value') == 'Sitio']
        servicios = [r for r in resultados if r.get('tipo', {}).get('value') == 'Servicio']

        # Narrar paquetes
        if paquetes:
            contexto += "Encontramos los siguientes paquetes turísticos: "
            for p in paquetes[:3]:  # Limitar a 3 para no sobrecargar
                nombre = p.get('nombre', {}).get('value', 'Sin nombre')
                descripcion = p.get('descripcion', {}).get('value', '')
                precio = p.get('precio', {}).get('value', 'Consultar')
                destinos_p = p.get('destinos', {}).get('value', '')
                contexto += f"El paquete '{nombre}' con descripción '{descripcion}', precio aproximado {precio} por persona, visitando destinos como {destinos_p}. "
            contexto += " "

        # Narrar destinos
        if destinos:
            contexto += "Destinos destacados relacionados: "
            for d in destinos[:3]:
                nombre = d.get('nombre', {}).get('value', 'Sin nombre')
                descripcion = d.get('descripcion', {}).get('value', '')
                municipios = d.get('municipios', {}).get('value', '')
                contexto += f"El destino '{nombre}' en {municipios}, descrito como '{descripcion}'. "
            contexto += " "

        # Narrar sitios
        if sitios:
            contexto += "Sitios de interés: "
            for s in sitios[:3]:
                nombre = s.get('nombre', {}).get('value', 'Sin nombre')
                descripcion = s.get('descripcion', {}).get('value', '')
                destinos_s = s.get('destinos', {}).get('value', '')
                contexto += f"El sitio '{nombre}' ubicado en {destinos_s}, con descripción '{descripcion}'. "
            contexto += " "

        # Narrar servicios (actividades y gastronomía)
        if servicios:
            contexto += "Servicios disponibles: "
            for srv in servicios[:3]:
                nombre = srv.get('nombre', {}).get('value', 'Sin nombre')
                descripcion = srv.get('descripcion', {}).get('value', '')
                destinos_srv = srv.get('destinos', {}).get('value', '')
                contexto += f"El servicio '{nombre}' en {destinos_srv}, descrito como '{descripcion}'. "
            contexto += " "

        return contexto.strip()

    except Exception as e:
        # Humanizar error
        return "No encontré coincidencias exactas para ese plan, pero puedo sugerirte otras maravillas del Caquetá y la Amazonia colombiana."