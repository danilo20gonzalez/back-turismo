from core.database import SessionLocal, Base, engine
from models.user import Role

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Crear sesión
db = SessionLocal()

# Verificar si ya existen roles
existing_roles = db.query(Role).count()
if existing_roles == 0:
    # Insertar roles básicos
    roles = [
        Role(id=1, nombre="Turista", descripcion="Usuario turista"),
        Role(id=2, nombre="Administrador", descripcion="Administrador del sistema"),
        Role(id=3, nombre="Operador", descripcion="Operador turístico"),
    ]
    for role in roles:
        db.add(role)
    db.commit()
    print("Roles creados exitosamente")
else:
    print("Los roles ya existen")

db.close()