import uuid
from datetime import datetime, date

from fastapi import HTTPException

from core.roles import is_admin, is_operator_or_admin
from schemas.reserva import ReservaCreate
from sparql_builder import EX, resource_uri
from sparql_client import SparqlClient
from sparql_queries import paquetes as paquete_queries
from sparql_queries import reservas as reserva_queries
from sparql_queries.usuarios import resolve_user_uri


client = SparqlClient()


class ReservaService:
    @staticmethod
    def _normalize_status(raw_status: str) -> tuple[str, str]:
        estado_lower = (raw_status or "Pendiente").lower()
        if "cancel" in estado_lower:
            return "cancelada", "Cancelada"
        if "confirm" in estado_lower:
            return "confirmada", "Confirmada"
        if "complet" in estado_lower:
            return "completada", "Completada"
        return "pendiente", "Pendiente de pago"

    @staticmethod
    def _assert_operator_or_admin(user):
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        if not is_operator_or_admin(role_name):
            raise HTTPException(status_code=403, detail="No autorizado para gestion operativa de reservas")

    @staticmethod
    def _assert_admin(user):
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        if not is_admin(role_name):
            raise HTTPException(status_code=403, detail="No autorizado para administracion global de reservas")

    @staticmethod
    def _resolve_operator_owner_uri(user) -> str | None:
        # Regla estricta: operador solo trabaja con la agencia vinculada en BD.
        # Evita resolver por email/uri para no mezclar reservas entre agencias.
        explicit_owner = (getattr(user, "agencia_uri", None) or "").strip()
        return explicit_owner or None

    @staticmethod
    def _user_uri(user_or_uri) -> str:
        if isinstance(user_or_uri, str):
            return user_or_uri
        return resolve_user_uri(user_or_uri)

    @staticmethod
    def _package_uri(paquete_id: str) -> str:
        return resource_uri(paquete_id)

    @staticmethod
    def _build_itinerary(paquete_uri: str):
        itinerary_rows = client.execute_select(paquete_queries.detail_itineraries(paquete_uri))
        items = []
        for idx, row in enumerate(itinerary_rows, start=1):
            title = (row.get("titulo", {}).get("value", "") or "").strip() or f"Actividad {idx}"
            description = (row.get("descripcion", {}).get("value", "") or "").strip() or "Actividad del itinerario"
            items.append(
                {
                    "title": title,
                    "time": "",
                    "duration": "Segun itinerario",
                    "attraction": description,
                    "icon": "forest" if idx % 2 == 0 else "hiking",
                }
            )
        if items:
            return items
        return [
            {
                "title": "Actividad principal del paquete",
                "time": "",
                "duration": "Segun itinerario",
                "attraction": "Detalle no disponible",
                "icon": "forest",
            }
        ]

    @staticmethod
    def crear_reserva(user, datos: ReservaCreate):
        reserva_uuid = str(uuid.uuid4())[:8]
        reserva_uri = f"{EX}Reserva_{reserva_uuid}"
        user_uri = ReservaService._user_uri(user)
        paquete_uri = ReservaService._package_uri(datos.paquete_id)

        res_capacidad = client.execute_select(
            reserva_queries.capacity_for_package(paquete_uri, datos.fecha_viaje)
        )

        if res_capacidad:
            cap_max = int(res_capacidad[0]["capacidadMax"]["value"])
            ocupado = (
                int(res_capacidad[0]["totalOcupado"]["value"])
                if "totalOcupado" in res_capacidad[0]
                and res_capacidad[0]["totalOcupado"]["value"] != ""
                else 0
            )

            solicitados = datos.cantidad_personas

            if (ocupado + solicitados) > cap_max:
                cupos_libres = cap_max - ocupado
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Capacidad excedida para esta fecha. "
                        f"Cupos disponibles: {cupos_libres}. Solicitados: {solicitados}"
                    ),
                )

        client.execute_sparql_update(
            reserva_queries.insert_reservation(
                reserva_uri=reserva_uri,
                user_uri=user_uri,
                paquete_id=paquete_uri,
                fecha_inicio=datos.fecha_viaje,
                numero_viajeros=datos.cantidad_personas,
                estado="Confirmada",
            )
        )

        return {
            "message": "Reserva creada exitosamente",
            "reserva_id": reserva_uri.split("#")[-1],
        }

    @staticmethod
    def obtener_mis_reservas(user):
        user_uri = ReservaService._user_uri(user)
        stats = client.execute_select(reserva_queries.user_stats(user_uri))
        total = int(stats[0]["total"]["value"]) if stats else 0
        if total == 0:
            return []
        results = client.execute_select(reserva_queries.user_reservations(user_uri))

        mis_reservas = []
        for row in results:
            comunidad = row.get("comunidad_nombre", {}).get("value", "Agencia por asignar")
            precio_t = row.get("total_pagar", {}).get("value", 0.0)

            mis_reservas.append(
                {
                    "reserva_id": row["reserva"]["value"].split("#")[-1],
                    "paquete": row["paquete_id"]["value"].replace("_", " "),
                    "fecha": row["fecha"]["value"],
                    "viajeros": int(row["personas"]["value"]),
                    "estado": row["estado"]["value"],
                    "operado_por": comunidad,
                    "precio_total": float(precio_t),
                    "moneda": "COP",
                }
            )
        return mis_reservas

    @staticmethod
    def obtener_mias_normalizado(user):
        user_uri = ReservaService._user_uri(user)
        stats = client.execute_select(reserva_queries.user_stats(user_uri))
        total = int(stats[0]["total"]["value"]) if stats else 0
        if total == 0:
            return []
        results = client.execute_select(reserva_queries.user_reservations(user_uri))

        normalizadas = []
        for row in results:
            reserva_local_id = row["reserva"]["value"].split("#")[-1]
            status, status_label = ReservaService._normalize_status(
                row.get("estado", {}).get("value", "Pendiente")
            )

            fecha_iso = row.get("fecha", {}).get("value", "")
            fecha_ui = fecha_iso
            if fecha_iso:
                try:
                    fecha_ui = datetime.fromisoformat(fecha_iso).strftime("%d %b %Y")
                except ValueError:
                    pass

            personas = int(row.get("personas", {}).get("value", 1))
            comunidad = row.get("comunidad_nombre", {}).get("value", "Agencia por asignar")
            paquete_local_id = row.get("paquete_id", {}).get("value", "")
            precio_total = float(row.get("total_pagar", {}).get("value", 0) or 0)
            precio_formateado = "${:,.0f} COP".format(precio_total).replace(",", ".")
            paquete_imagen = row.get("paquete_imagen", {}).get("value", "")

            row_data = {
                "id": reserva_local_id,
                "title": f"Reserva en {comunidad}",
                "status": status,
                "statusLabel": status_label,
                "image": paquete_imagen
                or "https://1qnmejprcdqaudae.public.blob.vercel-storage.com/amaturis/semillas/paisaje-amazonico-caqueta.jpg",
                "imageAlt": f"Imagen de la reserva {reserva_local_id}",
                "details": [
                    {
                        "label": "Fecha de viaje",
                        "value": fecha_ui,
                        "icon": "calendar_today",
                        "tone": "primary" if status == "confirmada" else "tertiary",
                    },
                    {
                        "label": "Viajeros",
                        "value": f"{personas} Persona{'s' if personas != 1 else ''}",
                        "icon": "group",
                        "tone": "primary" if status == "confirmada" else "tertiary",
                    },
                    {
                        "label": "Agencia",
                        "value": comunidad,
                        "icon": "storefront",
                        "tone": "secondary",
                    },
                ],
                "totalLabel": "Total",
                "totalAmount": precio_formateado,
                "primaryAction": {
                    "label": "Ver detalles",
                    "variant": "primary" if status == "confirmada" else "dark",
                    "title": "Ver detalle de la reserva",
                    "href": f"/perfil/reservas/{reserva_local_id}",
                },
                "meta": {
                    "paquete_id": paquete_local_id,
                    "fecha_iso": fecha_iso,
                    "personas": personas,
                },
            }
            if status in {"confirmada", "pendiente"}:
                row_data["secondaryAction"] = {
                    "icon": "close",
                    "title": "Cancelar reserva",
                    "href": f"/perfil/reservas/{reserva_local_id}/cancelar",
                }
            normalizadas.append(row_data)
        return normalizadas

    @staticmethod
    def obtener_reserva_por_id(user, reserva_id: str):
        user_uri = ReservaService._user_uri(user)
        result = client.execute_select(reserva_queries.reservation_detail(user_uri, reserva_id))

        if not result:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        row = result[0]
        status, status_label = ReservaService._normalize_status(
            row.get("estado", {}).get("value", "Pendiente")
        )

        fecha_inicio = row.get("fecha", {}).get("value", "")
        fecha_reserva = row.get("fecha_reserva", {}).get("value", "")
        fecha_creacion = fecha_reserva or fecha_inicio
        created_label = "Realizada el " + fecha_creacion.split("T")[0] if fecha_creacion else ""

        personas = int(row.get("personas", {}).get("value", 1))
        precio_unitario = float(row.get("precio_unitario", {}).get("value", 0) or 0)
        total = float(row.get("total_pagar", {}).get("value", 0) or 0)
        paquete_imagen = row.get("paquete_imagen", {}).get("value", "")
        destino_imagen = row.get("destino_imagen", {}).get("value", "")
        destino_nombre = row.get("destino_nombre", {}).get("value", "")
        municipio_nombre = row.get("municipio_nombre", {}).get("value", "")
        lat = row.get("lat", {}).get("value", "")
        lon = row.get("lon", {}).get("value", "")
        imagen = (
            destino_imagen
            if destino_imagen
            else paquete_imagen
            if paquete_imagen
            else "https://1qnmejprcdqaudae.public.blob.vercel-storage.com/amaturis/semillas/paisaje-amazonico-caqueta.jpg"
        )
        location_label = (
            f"{municipio_nombre}, Caqueta, Colombia" if municipio_nombre else "Caqueta, Colombia"
        )
        map_query = (
            f"{lat},{lon}" if lat and lon else location_label.replace(" ", "%20").replace(",", "%2C")
        )
        itinerary = ReservaService._build_itinerary(row["paquete"]["value"])
        agencia_nombre = row.get("comunidad_nombre", {}).get("value", "Agencia por asignar")
        attraction_name = destino_nombre or agencia_nombre

        return {
            "id": reserva_id,
            "status": status,
            "statusLabel": status_label,
            "createdAt": created_label,
            "plan": {
                "title": row.get("paquete_nombre", {}).get("value", "Plan turistico"),
                "description": row.get("paquete_descripcion", {}).get("value", "Sin descripcion disponible."),
                "image": imagen,
                "imageAlt": f"Imagen del plan {row.get('paquete_nombre', {}).get('value', '')}",
                "pricePerPerson": "${:,.0f} COP".format(precio_unitario).replace(",", "."),
                "duration": f"{row.get('duracion', {}).get('value', '1')} dia(s)",
                "dates": fecha_inicio,
            },
            "itinerary": itinerary,
            "attraction": {
                "name": attraction_name,
                "location": location_label,
                "image": imagen,
                "imageAlt": f"Vista de {attraction_name}",
                "mapUrl": f"https://www.google.com/maps/search/?api=1&query={map_query}",
            },
            "payment": {
                "people": f"{personas} Persona{'s' if personas != 1 else ''}",
                "method": "Pago registrado",
                "total": "${:,.0f} COP".format(total).replace(",", "."),
            },
            "traveler": {
                "name": getattr(user, "nombre_completo", "Viajero"),
                "email": getattr(user, "email", ""),
                "initials": "".join(
                    [part[0].upper() for part in str(getattr(user, "nombre_completo", "Viajero")).split()[:2]]
                ),
            },
            "provider": {
                "name": agencia_nombre,
                "phone": "+57 300 000 0000",
                "email": "contacto@amaturis.com",
            },
            "trustNote": "Reserva validada sobre la ontologia de Amaturis.",
        }

    @staticmethod
    def cancelar_reserva(user, reserva_id: str):
        user_uri = ReservaService._user_uri(user)
        detail = client.execute_select(reserva_queries.reservation_detail(user_uri, reserva_id))
        if not detail:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        estado = detail[0].get("estado", {}).get("value", "").lower()
        if "cancel" in estado:
            raise HTTPException(status_code=400, detail="La reserva ya esta cancelada")

        client.execute_sparql_update(reserva_queries.cancel_reservation(user_uri, reserva_id))
        return {"message": "Reserva cancelada exitosamente", "reserva_id": reserva_id}

    @staticmethod
    def obtener_operador_reservas(
        user,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        paquete: str | None = None,
    ):
        ReservaService._assert_operator_or_admin(user)
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        owner_uri = None
        if not is_admin(role_name):
            owner_uri = ReservaService._resolve_operator_owner_uri(user)
            if not owner_uri:
                raise HTTPException(
                    status_code=400,
                    detail="El usuario operador no tiene agencia/prestador vinculado en ontologia",
                )

        results = client.execute_select(reserva_queries.operator_reservations(owner_uri=owner_uri))
        estado_filtro = (estado or "").strip().lower()
        paquete_filtro = (paquete or "").strip().lower()
        normalized = []
        seen_reservations: set[str] = set()

        for row in results:
            reserva_id = row.get("reserva", {}).get("value", "").split("#")[-1]
            fecha_raw = row.get("fecha", {}).get("value", "")
            if not reserva_id or not fecha_raw:
                continue
            if reserva_id in seen_reservations:
                continue

            fecha_iso = fecha_raw.split("T")[0]
            try:
                fecha_obj = datetime.strptime(fecha_iso, "%Y-%m-%d").date()
            except ValueError:
                continue

            if fecha_desde and fecha_obj < fecha_desde:
                continue
            if fecha_hasta and fecha_obj > fecha_hasta:
                continue

            status_key, status_label = ReservaService._normalize_status(
                row.get("estado", {}).get("value", "Pendiente")
            )
            if estado_filtro and status_key != estado_filtro:
                continue

            paquete_id = row.get("paquete_id", {}).get("value", "")
            paquete_nombre = row.get("paquete_nombre", {}).get("value", "") or paquete_id.replace("_", " ")
            if paquete_filtro and paquete_filtro not in paquete_id.lower() and paquete_filtro not in paquete_nombre.lower():
                continue

            personas = int(row.get("personas", {}).get("value", 1) or 1)
            total = float(row.get("total_pagar", {}).get("value", 0) or 0)
            precio_unitario = float(row.get("precio_unitario", {}).get("value", 0) or 0)
            turista_nombre = row.get("turista_nombre", {}).get("value", "").strip() or "Viajero"
            turista_email = row.get("turista_email", {}).get("value", "").strip() or "Sin correo"
            comunidad = row.get("comunidad_nombre", {}).get("value", "").strip() or "Agencia por asignar"
            imagen = row.get("paquete_imagen", {}).get("value", "").strip()

            normalized.append(
                {
                    "id": reserva_id,
                    "fecha": fecha_iso,
                    "estado": status_key,
                    "estado_label": status_label,
                    "personas": personas,
                    "total": total,
                    "total_label": "${:,.0f} COP".format(total).replace(",", "."),
                    "precio_unitario_label": "${:,.0f} COP".format(precio_unitario).replace(",", "."),
                    "paquete": {
                        "id": paquete_id,
                        "nombre": paquete_nombre,
                        "imagen": imagen
                        or "https://1qnmejprcdqaudae.public.blob.vercel-storage.com/amaturis/semillas/paisaje-amazonico-caqueta.jpg",
                    },
                    "turista": {
                        "nombre": turista_nombre,
                        "email": turista_email,
                    },
                    "proveedor": comunidad,
                    "fecha_reserva": row.get("fecha_reserva", {}).get("value", ""),
                }
            )
            seen_reservations.add(reserva_id)

        return normalized

    @staticmethod
    def actualizar_estado_operador(user, reserva_id: str, estado: str):
        ReservaService._assert_operator_or_admin(user)
        role_name = getattr(getattr(user, "rol", None), "nombre", None)
        estado_key = (estado or "").strip().lower()
        permitidos = {"confirmada", "pendiente", "cancelada", "completada"}
        if estado_key not in permitidos:
            raise HTTPException(status_code=400, detail="Estado no permitido para operador")

        exists = client.execute_select(reserva_queries.reservation_exists(reserva_id))
        if not exists:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        if not is_admin(role_name):
            owner_uri = ReservaService._resolve_operator_owner_uri(user)
            if not owner_uri:
                raise HTTPException(
                    status_code=400,
                    detail="El usuario operador no tiene agencia/prestador vinculado en ontologia",
                )
            owned = client.execute_select(reserva_queries.reservation_owned_by(reserva_id, owner_uri))
            if not owned:
                raise HTTPException(
                    status_code=403,
                    detail="No autorizado para modificar reservas fuera de tu agencia/prestador",
                )

        client.execute_sparql_update(reserva_queries.set_reservation_state(reserva_id, estado_key))
        return {
            "message": "Estado actualizado",
            "reserva_id": reserva_id,
            "estado": estado_key,
        }

    @staticmethod
    def obtener_admin_reservas(
        user,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        q: str | None = None,
    ):
        ReservaService._assert_admin(user)
        resultados = ReservaService.obtener_operador_reservas(
            user,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            paquete=None,
        )

        query = (q or "").strip().lower()
        if not query:
            return sorted(resultados, key=lambda item: item.get("fecha", ""), reverse=True)

        filtradas = []
        for row in resultados:
            searchable = " ".join(
                [
                    row.get("id", ""),
                    row.get("estado", ""),
                    row.get("estado_label", ""),
                    row.get("paquete", {}).get("id", ""),
                    row.get("paquete", {}).get("nombre", ""),
                    row.get("turista", {}).get("nombre", ""),
                    row.get("turista", {}).get("email", ""),
                    row.get("proveedor", ""),
                ]
            ).lower()
            if query in searchable:
                filtradas.append(row)

        return sorted(filtradas, key=lambda item: item.get("fecha", ""), reverse=True)

    @staticmethod
    def obtener_admin_kpis_reservas(
        user,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        q: str | None = None,
    ):
        ReservaService._assert_admin(user)
        reservas = ReservaService.obtener_admin_reservas(
            user,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            q=q,
        )

        total = len(reservas)
        confirmadas = sum(1 for item in reservas if item.get("estado") == "confirmada")
        canceladas = sum(1 for item in reservas if item.get("estado") == "cancelada")
        ingresos_estimados = sum(
            float(item.get("total", 0) or 0)
            for item in reservas
            if item.get("estado") in {"pendiente", "confirmada", "completada"}
        )
        ingresos_confirmados = sum(
            float(item.get("total", 0) or 0)
            for item in reservas
            if item.get("estado") in {"confirmada", "completada"}
        )

        return {
            "total_reservas": total,
            "confirmadas": confirmadas,
            "canceladas": canceladas,
            "ingresos_estimados": ingresos_estimados,
            "ingresos_estimados_label": "${:,.0f} COP".format(ingresos_estimados).replace(",", "."),
            "ingresos_confirmados": ingresos_confirmados,
            "ingresos_confirmados_label": "${:,.0f} COP".format(ingresos_confirmados).replace(",", "."),
        }
