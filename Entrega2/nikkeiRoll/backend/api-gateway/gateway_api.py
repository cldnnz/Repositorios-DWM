"""
API Gateway de Borde (Puerto 8000) — Nikkei Roll (Caso 19)
Único punto de contacto con el navegador (localhost:3000).
Valida tokens con Auth Service (localhost:9000), limpia cabeceras falsificadas e inyecta X-Gateway-Secret hacia los microservicios (localhost:9001).
"""
import os
import uuid
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="Nikkei Roll - API Gateway Seguro (localhost:8000)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:9000")
CORE_BACKEND_URL = os.getenv("CORE_BACKEND_URL", "http://127.0.0.1:9001")
AUTH_INTROSPECTION_SECRET = os.getenv("AUTH_INTROSPECTION_SECRET", "auth-introspect-vault-2026")
INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET", "gw-secret-vault-2026")

async def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token requerido")
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(
            f"{AUTH_SERVICE_URL}/introspect",
            json={"token": credentials.credentials},
            headers={"X-Gateway-Auth-Secret": AUTH_INTROSPECTION_SECRET}
        )
    data = res.json()
    if not data.get("active"):
        raise HTTPException(status_code=401, detail="Token inválido o sesión expirada")
    return data

async def forward_to_backend(request: Request, internal_path: str, identity: dict = None):
    correlation_id = str(uuid.uuid4())
    # Header Stripping: jamás confía en cabeceras X-Authenticated-* enviadas desde el navegador
    headers = {
        "X-Gateway-Secret": INTERNAL_GATEWAY_SECRET,
        "X-Correlation-Id": correlation_id,
    }
    if identity:
        headers["X-Authenticated-User"] = identity["user_id"]
        headers["X-User-Role"] = identity["rol"]
    if "content-type" in request.headers:
        headers["Content-Type"] = request.headers["content-type"]

    body = await request.body()
    async with httpx.AsyncClient(timeout=8.0) as client:
        upstream = await client.request(
            method=request.method,
            url=f"{CORE_BACKEND_URL}{internal_path}",
            params=request.query_params,
            content=body,
            headers=headers
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={"Content-Type": upstream.headers.get("content-type", "application/json"), "X-Correlation-Id": correlation_id}
    )

# --- Rutas Externas Anónimas (S01, S02, S03, S06) ---
@app.get("/api/v1/products")
async def s01_products(request: Request):
    return await forward_to_backend(request, "/products")

@app.get("/api/v1/custom-roll/ingredients")
async def s02_ingredients(request: Request):
    return await forward_to_backend(request, "/custom-roll/ingredients")

@app.get("/api/v1/delivery-zones/check")
async def s03_delivery_zones(request: Request):
    return await forward_to_backend(request, "/delivery-zones/check")

@app.post("/api/v1/auth/login")
async def s06_login(request: Request):
    body = await request.body()
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(f"{AUTH_SERVICE_URL}/login", content=body, headers={"Content-Type": "application/json"})
    return Response(content=res.content, status_code=res.status_code, headers={"Content-Type": "application/json"})

# --- Rutas Externas Autenticadas y Protegidas por Rol (S07..S16) ---
@app.post("/api/v1/auth/logout")
async def s07_logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Token requerido")
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(
            f"{AUTH_SERVICE_URL}/logout",
            json={"token": credentials.credentials},
            headers={"X-Gateway-Auth-Secret": AUTH_INTROSPECTION_SECRET}
        )
    return Response(content=res.content, status_code=res.status_code, headers={"Content-Type": "application/json"})

@app.post("/api/v1/orders")
async def s09_create_order(request: Request, identity: dict = Depends(verify_bearer_token)):
    return await forward_to_backend(request, "/orders", identity)

@app.get("/api/v1/orders/{order_id}")
async def s11_get_order(order_id: str, request: Request, identity: dict = Depends(verify_bearer_token)):
    return await forward_to_backend(request, f"/orders/{order_id}", identity)

@app.post("/api/v1/orders/{order_id}/cancel")
async def s12_cancel_order(order_id: str, request: Request, identity: dict = Depends(verify_bearer_token)):
    return await forward_to_backend(request, f"/orders/{order_id}/cancel", identity)

@app.post("/api/v1/payments/initiate")
async def s10_initiate_payment(request: Request, identity: dict = Depends(verify_bearer_token)):
    return await forward_to_backend(request, "/payments/initiate", identity)

@app.patch("/api/v1/products/{product_id}/availability")
async def s13_patch_availability(product_id: str, request: Request, identity: dict = Depends(verify_bearer_token)):
    if identity["rol"] not in ("ADMINISTRADOR", "DUENO"):
        raise HTTPException(status_code=403, detail="Bloqueado en API Gateway: se requiere rol ADMINISTRADOR o DUENO")
    return await forward_to_backend(request, f"/products/{product_id}/availability", identity)

@app.get("/api/v1/reports/sales")
async def s16_sales_report(request: Request, identity: dict = Depends(verify_bearer_token)):
    if identity["rol"] not in ("DUENO", "ADMINISTRADOR"):
        raise HTTPException(status_code=403, detail="Bloqueado en API Gateway: exclusivo para DUENO o ADMINISTRADOR")
    return await forward_to_backend(request, "/reports/sales", identity)
