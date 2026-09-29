import os
import secrets

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Depends
)

app = FastAPI(
    title="Backend API Nikkei Roll",
    description="API del servicio de delivery ubicada en localhost, enrutada por API Gateway"
)

INTERNAL_GATEWAY_SECRET = os.getenv(
    "INTERNAL_GATEWAY_SECRET"
)

if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError(
        "INTERNAL_GATEWAY_SECRET NO ESTÁ CONFIGURADO"
    )

def verify_gateway(
    x_gateway_secret: str = Header(default="")
):
    valid = secrets.compare_digest(
        x_gateway_secret,
        INTERNAL_GATEWAY_SECRET
    )
    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Solicitud no autorizada desde gateway"
        )

@app.get(
    "/health",
    dependencies=[Depends(verify_gateway)]
)
def health():
    return{
        "status": "OK",
        "service": "Backend API Nikkei Roll"
    }


@app.get(
        "/productos",
        dependencies=[Depends(verify_gateway)]      
)
def productos():
    return {
        "products": [
            {
                "id": 1,
                "nombre": "Acevichado Roll",
                "categoria": "Fusión",
                "descripcion": "Camarón furai, palta, cubierto en salmón y salsa acevichada",
                "precio": 8500
            },
            {
                "id": 2,
                "nombre": "Lomo Saltado Roll",
                "categoria": "Fusión",
                "descripcion": "Relleno de lomo saltado, envuelto en papas al hilo",
                "precio": 9200
            },
            {
                "id": 3,
                "nombre": "Maki Furai",
                "categoria": "Tradicional Caliente",
                "descripcion": "Salmón, queso crema y cebollín, frito en panko",
                "precio": 6500
            },
            {
                "id": 4,
                "nombre": "Tiradito de Salmón",
                "categoria": "Sashimi",
                "descripcion": "Finas láminas de salmón con salsa de maracuyá",
                "precio": 11000
            }
        ]   
    }

@app.get(
        "/pedidos",
        dependencies=[Depends(verify_gateway)]
)
def pedidos():
    return {
        "pedidos": [
            {"id": 5001, "status": "entregado", "total": 17700},
            {"id": 5002, "status": "preparando", "total": 8500}
        ]
    }