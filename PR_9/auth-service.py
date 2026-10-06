from datetime import datetime, timedelta, timezone
import os
import secrets

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI(
    title="Auth Service API",
    description="Servicio centralizado de autenticación"
)

USER_DB = {
    "carlos": {
        "password": "pass_carlos",
        "id_usuario": "USR-101",
        "permisos": ["user"]
    },
    "maria": {
        "password": "pass_maria",
        "id_usuario": "USR-102",
        "permisos": ["user"]
    },
    "admin": {
        "password": "admin_secure",
        "id_usuario": "USR-103",
        "permisos": ["user", "admin"]
    }
}

ACTIVE_SESSIONS = {}
EXPIRATION_TIME_MINUTES = 15

GATEWAY_SECRET = os.getenv(
    "AUTH_INTROSPECTION_SECRET",
    "demo-introspection-secret"
)

class AuthRequest(BaseModel):
    username: str
    password: str

class TokenRequest(BaseModel):
    token: str

@app.post("/login")
def authenticate_user(request: AuthRequest):
    user_data = USER_DB.get(request.username)
    
    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="El usuario ingresado no existe"
        )
        
    if user_data["password"] != request.password:
        raise HTTPException(
            status_code=401,
            detail="La contraseña es inválida"
        )
    
    new_token = secrets.token_urlsafe(32)
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=EXPIRATION_TIME_MINUTES)
    
    ACTIVE_SESSIONS[new_token] = {
        "id_usuario": user_data["id_usuario"],
        "username": request.username,
        "permisos": user_data["permisos"],
        "expires_at": expire_time
    }
    
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": EXPIRATION_TIME_MINUTES * 60
    }

@app.post("/introspect")
def verify_token(
    request: TokenRequest,
    x_gateway_auth_secret: str = Header(default="")
):
    if not secrets.compare_digest(x_gateway_auth_secret, GATEWAY_SECRET):
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado al Gateway"
        )
    
    current_session = ACTIVE_SESSIONS.get(request.token)
    
    if not current_session:
        return {"active": False}
    
    if datetime.now(timezone.utc) > current_session["expires_at"]:
        ACTIVE_SESSIONS.pop(request.token, None)
        return {"active": False}
        
    return {
        "active": True,
        "user_id": current_session["id_usuario"],
        "username": current_session["username"],
        "roles": current_session["permisos"],
        "expires_at": current_session["expires_at"].isoformat()
    }

@app.post("/logout")
def terminate_session(
    request: TokenRequest,
    x_gateway_auth_secret: str = Header(default="")
):
    if not secrets.compare_digest(x_gateway_auth_secret, GATEWAY_SECRET):
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado al Gateway"
        )
        
    ACTIVE_SESSIONS.pop(request.token, None)
    return {"message": "La sesión ha sido cerrada correctamente"}

@app.get("/health")
def health_check(x_gateway_auth_secret: str = Header(default="")):
    if not secrets.compare_digest(x_gateway_auth_secret, GATEWAY_SECRET):
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado al Gateway"
        )
        
    return {
        "status": "OPERATIONAL",
        "service": "Auth Service API"
    }