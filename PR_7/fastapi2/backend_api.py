# fastapi2/backend_api.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/usuarios")
async def obtener_usuarios():
    return [
        {"id": 1, "nombre": "Claudio Nuñez", "rol": "Admin"},
        {"id": 2, "nombre": "Ernesto Vivanco", "rol": "Profesor"}
    ]