from sparql_client import SparqlClient
from models.usuario import UsuarioRegistro, UsuarioLogin
from core.auth import get_password_hash
from datetime import datetime
from core.auth import verify_password, create_access_token
from fastapi import HTTPException

client = SparqlClient()

class UsuarioService:
    @staticmethod
    def registrar_turista(datos: UsuarioRegistro):
        # Creamos un ID único basado en el nombre (puedes usar UUID si prefieres)
        user_id = f"Turista_{datos.nombre.replace(' ', '_')}"
        password_hash = get_password_hash(datos.password)
        
        params = {
            "user_id": user_id,
            "nombre": datos.nombre,
            "email": datos.email,
            "password_hash": password_hash,
            "fecha_actual": datetime.now().isoformat()
        }
        
        # Ejecutamos el Update en Fuseki
        client.execute_update("registro_usuario", params)
        return {"message": "Usuario registrado con éxito", "id": user_id}

    def login(datos: UsuarioLogin):
        # 1. Buscamos el usuario en Fuseki
        params = {"email": datos.email}
        results = client.execute_query("buscar_usuario", params)

        if not results:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

        # 2. Extraemos los datos de la ontología
        user_data = results[0]
        stored_hash = user_data["passwordHash"]["value"]
        user_uri = user_data["userURI"]["value"]
        nombre = user_data["nombre"]["value"]

        # 3. Verificamos la contraseña
        if not verify_password(datos.password, stored_hash):
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

        # 4. Creamos el Token JWT
        token = create_access_token(data={"sub": user_uri, "nombre": nombre})
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"nombre": nombre, "id": user_uri}
        }