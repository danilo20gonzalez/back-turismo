import bcrypt

def generar_mi_hash(password_plana: str):
    # Convertir a bytes y truncar a 72 bytes si es necesario
    password_bytes = password_plana.encode('utf-8')
    
    if len(password_bytes) > 72:
        print(f"⚠️ Advertencia: Contraseña tiene {len(password_bytes)} bytes, truncando a 72 bytes")
        password_bytes = password_bytes[:72]
    
    # Generar salt y hash
    salt = bcrypt.gensalt()
    hash_resultado = bcrypt.hashpw(password_bytes, salt)
    
    # Convertir el hash a string para mostrarlo
    hash_str = hash_resultado.decode('utf-8')
    
    print(f"--- RESULTADOS ---")
    print(f"Contraseña original: {password_plana}")
    if len(password_plana.encode('utf-8')) > 72:
        print(f"Contraseña truncada a: {password_bytes.decode('utf-8', errors='ignore')}")
    print(f"Hash generado (Esto es lo que va a la Ontología):")
    print(f"{hash_str}")
    print(f"------------------")
    
    return hash_str

# --- PRUEBA AQUÍ ---
mi_clave = "123456"
generar_mi_hash(mi_clave)