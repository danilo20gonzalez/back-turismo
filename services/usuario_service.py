from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.auth import create_access_token, get_password_hash, verify_password
from core.roles import ROLE_OPERADOR, normalize_role_name
from models.user import Role, Usuario
from schemas.paquete import Paquete
from schemas.usuario import ProfileUpdate, UsuarioLogin, UsuarioRegistro
from sparql_client import SparqlClient
from sparql_queries import usuarios as usuario_queries


client = SparqlClient()


def _package_from_row(row) -> Paquete:
    return Paquete(
        id=row["paquete"]["value"],
        nombre=row["nombre"]["value"],
        precio=float(row["precio"]["value"]),
        descripcion=row["descripcion"]["value"],
        dirigidoA=row.get("dirigidoA", {}).get("value"),
        duracion_dias=int(row["duracion"]["value"]) if "duracion" in row else None,
        dificultad=row.get("dificultad", {}).get("value"),
        destinos=row.get("destinos", {}).get("value"),
        municipios=row.get("municipios", {}).get("value"),
        categorias=row.get("categorias", {}).get("value"),
        capacidad_max_personas=int(row["capacidad"]["value"]) if "capacidad" in row else None,
        popularidad=int(row["popularidad"]["value"]) if "popularidad" in row else None,
        url_imagen=row.get("imagen", {}).get("value"),
        galeria_imagenes=row.get("galeria", {}).get("value"),
    )


def _packages_from_favorite_rows(rows) -> list[Paquete]:
    grouped: dict[str, dict] = {}

    for row in rows:
        package_id = row["paquete"]["value"]
        current = grouped.setdefault(
            package_id,
            {
                "row": row,
                "destinos": set(),
                "municipios": set(),
                "categorias": set(),
            },
        )

        for source, target in (
            ("destinoLabel", "destinos"),
            ("municipioLabel", "municipios"),
            ("categoriaLabel", "categorias"),
        ):
            value = row.get(source, {}).get("value")
            if value:
                current[target].add(value)

    packages = []
    for item in grouped.values():
        row = item["row"]
        packages.append(
            Paquete(
                id=row["paquete"]["value"],
                nombre=row["nombre"]["value"],
                precio=float(row["precio"]["value"]),
                descripcion=row["descripcion"]["value"],
                dirigidoA=row.get("dirigidoA", {}).get("value"),
                duracion_dias=int(row["duracion"]["value"]) if "duracion" in row else None,
                dificultad=row.get("dificultad", {}).get("value"),
                destinos=" | ".join(sorted(item["destinos"])) or None,
                municipios=" | ".join(sorted(item["municipios"])) or None,
                categorias=" | ".join(sorted(item["categorias"])) or None,
                capacidad_max_personas=int(row["capacidad"]["value"]) if "capacidad" in row else None,
                popularidad=int(row["popularidad"]["value"]) if "popularidad" in row else None,
                url_imagen=row.get("imagen", {}).get("value"),
                galeria_imagenes=row.get("galeria", {}).get("value"),
            )
        )

    return packages


class UsuarioService:
    @staticmethod
    def _resolve_operator_owner_uri(email: str, explicit_agencia_uri: str | None) -> str | None:
        explicit_value = (explicit_agencia_uri or "").strip()
        if explicit_value:
            try:
                found = client.execute_select(usuario_queries.owner_uri_by_uri(explicit_value))
                if found:
                    return found[0]["owner"]["value"]
            except Exception as e:
                print(f"No se pudo validar agencia_uri explicita: {e}")

        try:
            owner_by_email = client.execute_select(usuario_queries.owner_uri_by_email(email))
            if owner_by_email:
                return owner_by_email[0]["owner"]["value"]
        except Exception as e:
            print(f"No se pudo resolver agencia por email en ontologia: {e}")

        return None

    @staticmethod
    def registrar_usuario(datos: UsuarioRegistro, db: Session):
        user_exists = db.query(Usuario).filter(Usuario.email == datos.email).first()
        if user_exists:
            raise HTTPException(status_code=400, detail="El email ya esta registrado")

        password_hash = get_password_hash(datos.password)

        nuevo_usuario = Usuario(
            email=datos.email,
            password_hash=password_hash,
            nombre_completo=datos.nombre_completo,
            rol_id=datos.rol_id,
            activo=True,
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        rol_obj = db.query(Role).filter(Role.id == datos.rol_id).first()
        nombre_rol = rol_obj.nombre if rol_obj else "Turista"
        rol_normalizado = normalize_role_name(nombre_rol)
        user_uri_id = usuario_queries.user_local_id(nombre_rol, nuevo_usuario.id)
        full_uri = usuario_queries.user_uri(nombre_rol, nuevo_usuario.id)

        linked_owner_uri: str | None = None
        if rol_normalizado == ROLE_OPERADOR:
            linked_owner_uri = UsuarioService._resolve_operator_owner_uri(
                email=datos.email,
                explicit_agencia_uri=datos.agencia_uri,
            )
            nuevo_usuario.agencia_uri = linked_owner_uri or full_uri
            db.commit()
            db.refresh(nuevo_usuario)

        should_insert_in_ontology = not linked_owner_uri
        semantic_uri = linked_owner_uri or full_uri

        try:
            if should_insert_in_ontology:
                client.execute_sparql_update(
                    usuario_queries.insert_user(
                        user_id=user_uri_id,
                        role_name=nombre_rol,
                        nombre=datos.nombre_completo,
                        email=datos.email,
                        password_hash=password_hash,
                        fecha_actual=datetime.now(),
                    )
                )
            nuevo_usuario.uri_ontologia = semantic_uri
            db.commit()
        except Exception as e:
            print(f"Error al registrar en Fuseki: {e}")
            if rol_normalizado == ROLE_OPERADOR and linked_owner_uri:
                nuevo_usuario.uri_ontologia = linked_owner_uri
                db.commit()

        token_data = {
            "sub": nuevo_usuario.email,
            "rol": nombre_rol,
            "uri": nuevo_usuario.uri_ontologia,
        }
        token = create_access_token(data=token_data)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "nombre_completo": nuevo_usuario.nombre_completo,
                "email": nuevo_usuario.email,
                "rol": nombre_rol,
                "agencia_uri": nuevo_usuario.agencia_uri,
            },
        }

    @staticmethod
    def login(datos: UsuarioLogin, db: Session):
        usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()

        if not usuario:
            return None

        if not verify_password(datos.password, usuario.password_hash):
            return None

        nombre_rol = usuario.rol.nombre if usuario.rol else "Turista"
        token_data = {
            "sub": usuario.email,
            "rol": nombre_rol,
            "uri": usuario.uri_ontologia,
        }
        token = create_access_token(data=token_data)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "nombre_completo": usuario.nombre_completo,
                "email": usuario.email,
                "rol": nombre_rol,
                "agencia_uri": usuario.agencia_uri,
            },
        }

    @staticmethod
    def update_profile(db: Session, user: Usuario, data: ProfileUpdate):
        user.nombre_completo = data.name
        db.commit()
        db.refresh(user)

        try:
            client.execute_sparql_update(
                usuario_queries.update_profile(
                    user_uri_value=usuario_queries.resolve_user_uri(user),
                    name=data.name,
                    location=data.location,
                    bio=data.bio or "",
                )
            )
        except Exception as e:
            print(f"Error en persistencia semantica: {e}")

        return user

    @staticmethod
    def change_password(db: Session, user: Usuario, current_password: str, new_password: str):
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="La contrasena actual no es correcta")

        if current_password == new_password:
            raise HTTPException(
                status_code=400,
                detail="La nueva contrasena debe ser diferente a la actual",
            )

        password_hash = get_password_hash(new_password)
        user.password_hash = password_hash
        db.commit()
        db.refresh(user)

        try:
            client.execute_sparql_update(
                usuario_queries.update_password_hash(
                    user_uri_value=usuario_queries.resolve_user_uri(user),
                    password_hash=password_hash,
                )
            )
        except Exception as e:
            print(f"Error al sincronizar contrasena en Fuseki: {e}")

        return user

    @staticmethod
    def list_favorites(user: Usuario):
        favorite_rows = client.execute_select(
            usuario_queries.favorite_package_ids(usuario_queries.resolve_user_uri(user))
        )
        package_ids = [row["paquete"]["value"] for row in favorite_rows if "paquete" in row]
        if not package_ids:
            return []

        rows = client.execute_select(usuario_queries.favorite_packages(package_ids))
        return _packages_from_favorite_rows(rows)

    @staticmethod
    def add_favorite(user: Usuario, paquete_id: str):
        client.execute_sparql_update(
            usuario_queries.add_favorite(
                user_uri_value=usuario_queries.resolve_user_uri(user),
                paquete_id=paquete_id,
            )
        )

    @staticmethod
    def remove_favorite(user: Usuario, paquete_id: str):
        client.execute_sparql_update(
            usuario_queries.remove_favorite(
                user_uri_value=usuario_queries.resolve_user_uri(user),
                paquete_id=paquete_id,
            )
        )
