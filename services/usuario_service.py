from sqlalchemy.orm import Session
from sparql_client import SparqlClient
from models.user import Usuario, Role  # Tus modelos de Postgres
from schemas.usuario import UsuarioRegistro, UsuarioLogin, ProfileUpdate
from core.auth import get_password_hash, verify_password, create_access_token
from datetime import datetime
from fastapi import HTTPException

client = SparqlClient()

class UsuarioService:
    @staticmethod
    def registrar_usuario(datos: UsuarioRegistro, db: Session):
        # 1. Verificar si existe
        user_exists = db.query(Usuario).filter(Usuario.email == datos.email).first()
        if user_exists:
            raise HTTPException(status_code=400, detail="El email ya está registrado")

        # 2. Hash
        password_hash = get_password_hash(datos.password)

        # 3. Guardar en Postgres
        nuevo_usuario = Usuario(
            email=datos.email,
            password_hash=password_hash,
            nombre_completo=datos.nombre_completo,
            rol_id=datos.rol_id,
            activo=True
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        # 4. Ontología (Fuseki) - DEBE IR ANTES DEL RETURN
        rol_obj = db.query(Role).filter(Role.id == datos.rol_id).first()
        nombre_rol = rol_obj.nombre if rol_obj else "Turista"
        user_uri_id = f"{nombre_rol}_{nuevo_usuario.id}"
        full_uri = f"http://amaturis.org/ontology#{user_uri_id}"

        params_fuseki = {
            "user_id": user_uri_id,
            "rol_type": nombre_rol,
            "nombre": datos.nombre_completo,
            "email": datos.email,
            "password_hash": password_hash,
            "fecha_actual": datetime.now().isoformat()
        }

        try:
            client.execute_update("registro_usuario", params_fuseki)
            # Actualizamos el vínculo en Postgres
            nuevo_usuario.uri_ontologia = full_uri
            db.commit()
        except Exception as e:
            print(f"Error al registrar en Fuseki: {e}")
            # El usuario sigue creado en Postgres, pero sin URI semántica

        # 5. Generar token y respuesta (AL FINAL)
        token_data = {
            "sub": nuevo_usuario.email, 
            "rol": nombre_rol,
            "uri": nuevo_usuario.uri_ontologia
        }
        token = create_access_token(data=token_data)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "nombre_completo": nuevo_usuario.nombre_completo, 
                "email": nuevo_usuario.email,
                "rol": nombre_rol
            }
        }

    @staticmethod
    def login(datos: UsuarioLogin, db: Session):
        # 1. Buscamos el usuario en PostgreSQL (es mucho más rápido y seguro)
        usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()

        if not usuario:
            return None # El router lanzará el 401

        # 2. Verificamos la contraseña
        if not verify_password(datos.password, usuario.password_hash):
            return None

        # 3. Creamos el Token JWT
        # Usamos el email como 'sub' y el rol para que el frontend sepa qué mostrar
        nombre_rol = usuario.rol.nombre if usuario.rol else "Turista"
        token_data = {
            "sub": usuario.email, 
            "rol": nombre_rol,
            "uri": usuario.uri_ontologia
        }
        token = create_access_token(data=token_data)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "nombre_completo": usuario.nombre_completo, 
                "email": usuario.email,
                "rol": nombre_rol
            }
        }
    
    @staticmethod
    def update_profile(db: Session, user: Usuario, data: ProfileUpdate):
        # 1. Lógica SQL
        user.nombre_completo = data.name    
        db.commit()
        db.refresh(user)

        # 2. Lógica Fuseki (Semántica): Actualizamos datos de perfil
        # Construimos la URI igual que en el registro
        nombre_rol = user.rol.nombre if user.rol else "Turista"
        user_uri_id = f"{nombre_rol}_{user.id}"
        full_uri = f"http://amaturis.org/ontology#{user_uri_id}"

        try:
            client.execute_update("actualizar_perfil", {
                "user_uri": full_uri,
                "location": data.location,
                "avatar": data.avatar or "https://www.gravatar.com/avatar/000?d=mp"
            })
        except Exception as e:
            print(f"Error en persistencia semántica: {e}")
            # Aquí podrías decidir si lanzar una excepción o solo loguear
        
        return user