# gateway/gateway.py
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

# Definimos las URLs y puertos de nuestras APIs normales
URL_API_PRODUCTOS = "http://localhost:9000"
URL_API_USUARIOS = "http://localhost:9100"

@app.get("/api/productos")
async def ruta_productos():
    # Usamos httpx para consultar la API normal de forma asíncrona
    async with httpx.AsyncClient() as client:
        try:
            # Redirigimos la petición al backend de productos
            response = await client.get(f"{URL_API_PRODUCTOS}/productos")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="El servicio de productos no está disponible")

@app.get("/api/usuarios")
async def ruta_usuarios():
    async with httpx.AsyncClient() as client:
        try:
            # Redirigimos la petición al backend de usuarios
            response = await client.get(f"{URL_API_USUARIOS}/usuarios")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="El servicio de usuarios no está disponible")