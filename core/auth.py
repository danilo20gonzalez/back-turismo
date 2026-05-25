# core/auth.py
from datetime import datetime, timedelta
import hashlib
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
from sqlalchemy.orm import Session 
from core.database import get_db
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from models.user import Usuario


# Configuración para el hashing de contraseñas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema para extraer el token de la cabecera Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="usuarios/login")

def _secret_fingerprint() -> str:
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).hexdigest()[:10]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara una contraseña en texto plano con el hash guardado en Fuseki"""
    # Usamos [:72] por el límite de seguridad de bcrypt
    return pwd_context.verify(plain_password[:72], hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash seguro para guardar en la ontología"""
    # Usamos [:72] para evitar errores de longitud en bcrypt
    return pwd_context.hash(password[:72])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT firmado para el usuario"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    print(
        "AUTH DEBUG token_created",
        {
            "sub": to_encode.get("sub"),
            "role": to_encode.get("rol"),
            "exp": expire.isoformat(),
            "secret_fp": _secret_fingerprint(),
            "token_prefix": encoded_jwt[:12],
        },
    )
    return encoded_jwt

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print(
        "AUTH DEBUG token_received",
        {
            "path": request.url.path,
            "has_authorization": bool(request.headers.get("authorization")),
            "secret_fp": _secret_fingerprint(),
            "token_prefix": token[:12] if token else None,
        },
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            print("AUTH DEBUG missing_sub", {"path": request.url.path})
            raise credentials_exception
        
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if user is None:
            print("AUTH DEBUG user_not_found", {"path": request.url.path, "email": email})
            raise credentials_exception
        print(
            "AUTH DEBUG user_ok",
            {
                "path": request.url.path,
                "email": email,
                "role": getattr(getattr(user, "rol", None), "nombre", None),
                "user_id": getattr(user, "id", None),
            },
        )
        return user
    except JWTError as error:
        print(
            "AUTH DEBUG jwt_error",
            {
                "path": request.url.path,
                "error": repr(error),
                "secret_fp": _secret_fingerprint(),
                "token_prefix": token[:12] if token else None,
            },
        )
        raise credentials_exception
