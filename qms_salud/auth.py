from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_cambiar")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    return user

def get_permisos(db: Session, user) -> dict:
    ALL_MODULES = [
        "dashboard", "documentos", "auditorias", "mejora", "indicadores",
        "riesgos", "comites", "seguridad-paciente", "flujos",
        "sst", "ambiental", "ambiente-fisico",
        "tecnovigilancia", "sistemas", "ambulancias", "talento", "pqrs",
    ]
    FULL = {"puede_ver": True, "puede_crear": True, "puede_editar": True,
            "puede_aprobar": True, "puede_eliminar": True}
    if not user:
        return {}
    if user.rol.value == "admin":
        return {m: FULL for m in ALL_MODULES}
    registros = db.query(models.PermisoUsuario).filter_by(usuario_id=user.id).all()
    return {p.modulo: {"puede_ver": p.puede_ver, "puede_crear": p.puede_crear,
                       "puede_editar": p.puede_editar, "puede_aprobar": p.puede_aprobar,
                       "puede_eliminar": p.puede_eliminar} for p in registros}


def tiene_permiso(db: Session, user, modulo: str, accion: str = "puede_ver") -> bool:
    if not user:
        return False
    if user.rol.value == "admin":
        return True
    p = db.query(models.PermisoUsuario).filter_by(usuario_id=user.id, modulo=modulo).first()
    return bool(getattr(p, accion, False)) if p else False


async def require_user(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        from fastapi.responses import RedirectResponse
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user
