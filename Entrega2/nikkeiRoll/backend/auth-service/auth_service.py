"""
Auth Service (Puerto 9000) — Nikkei Roll (Caso 19)
Emite tokens Bearer opacos (15 min), valida credenciales con hash y ejecuta introspección para el API Gateway.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI(title="Nikkei Roll - Auth Service (localhost:9000)")

AUTH_INTROSPECTION_SECRET = os.getenv("AUTH_INTROSPECTION_SECRET", "auth-introspect-vault-2026")
TOKEN_LIFETIME_MINUTES = 15

def _hash_pw(pw: str, salt: str = "nikkei_salt_2026") -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()

# Usuarios semilla del Caso 19 (Clientes y Roles Internos con contraseñas hasheadas con sal)
USERS = {
    "camila.soto@correo.cl": {
        "password_hash": _hash_pw("1234"),
        "user_id": "CLI-2026-0089",
        "nombre": "Camila Andrea Soto Riquelme",
        "rol": "CLIENTE",
        "correo_verificado": True
    },
    "pedro.rojas@correo.cl": {
        "password_hash": _hash_pw("5678"),
        "user_id": "CLI-2026-0042",
        "nombre": "Pedro Ignacio Rojas Díaz",
        "rol": "CLIENTE",
        "correo_verificado": True
    },
    "admin@nikkeiroll.cl": {
        "password_hash": _hash_pw("admin123"),
        "user_id": "USR-ADMIN-01",
        "nombre": "Leonardo Onetto (Administrador)",
        "rol": "ADMINISTRADOR",
        "correo_verificado": True
    },
    "dueno@nikkeiroll.cl": {
        "password_hash": _hash_pw("dueno123"),
        "user_id": "USR-DUENO-01",
        "nombre": "Claudio Núñez (Dueño)",
        "rol": "DUENO",
        "correo_verificado": True
    },
    "cajero@nikkeiroll.cl": {
        "password_hash": _hash_pw("caja123"),
        "user_id": "USR-CAJA-01",
        "nombre": "Cajero Virtual Web",
        "rol": "CAJERO_VIRTUAL",
        "correo_verificado": True
    },
    "despacho@nikkeiroll.cl": {
        "password_hash": _hash_pw("despacho123"),
        "user_id": "USR-DESP-01",
        "nombre": "Roberto Gómez (Despacho)",
        "rol": "ENCARGADO_DESPACHO",
        "correo_verificado": True
    }
}

SESSIONS = {}

class LoginRequest(BaseModel):
    correo: str
    password: str

class IntrospectionRequest(BaseModel):
    token: str

@app.post("/login")
def login(request: LoginRequest):
    user = USERS.get(request.correo.lower().strip())
    if user is None or not secrets.compare_digest(user["password_hash"], _hash_pw(request.password)):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not user.get("correo_verificado", False):
        raise HTTPException(status_code=403, detail="Correo electrónico pendiente de verificación (RF11)")

    access_token = secrets.token_urlsafe(32)
    expiration = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_LIFETIME_MINUTES)
    SESSIONS[access_token] = {
        "user_id": user["user_id"],
        "correo": request.correo,
        "nombre": user["nombre"],
        "rol": user["rol"],
        "expires_at": expiration
    }
    return {
        "accessToken": access_token,
        "tokenType": "Bearer",
        "expiresIn": TOKEN_LIFETIME_MINUTES * 60,
        "usuario": {
            "id": user["user_id"],
            "nombreCompleto": user["nombre"],
            "rol": user["rol"]
        }
    }

@app.post("/introspect")
def introspect(request: IntrospectionRequest, x_gateway_auth_secret: str = Header(default="")):
    if not secrets.compare_digest(x_gateway_auth_secret, AUTH_INTROSPECTION_SECRET):
        raise HTTPException(status_code=403, detail="Gateway no autorizado para introspección")

    session = SESSIONS.get(request.token)
    if session is None:
        return {"active": False}
    if datetime.now(timezone.utc) > session["expires_at"]:
        SESSIONS.pop(request.token, None)
        return {"active": False}

    return {
        "active": True,
        "user_id": session["user_id"],
        "correo": session["correo"],
        "nombre": session["nombre"],
        "rol": session["rol"],
        "expires_at": session["expires_at"].isoformat()
    }

@app.post("/logout")
def logout(request: IntrospectionRequest, x_gateway_auth_secret: str = Header(default="")):
    if not secrets.compare_digest(x_gateway_auth_secret, AUTH_INTROSPECTION_SECRET):
        raise HTTPException(status_code=403, detail="Gateway no autorizado")
    SESSIONS.pop(request.token, None)
    return {"mensaje": "Sesión finalizada correctamente"}
