from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    
    # Relación para acceder a los usuarios de este rol
    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    nombre_completo = Column(String(200), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"))
    activo = Column(Boolean, default=True)
    fecha_registro = Column(TIMESTAMP, default=datetime.utcnow)
    uri_ontologia = Column(String(255), nullable=True)
    # Relación para acceder al nombre del rol fácilmente
    rol = relationship("Role", back_populates="usuarios")