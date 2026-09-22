# fastapi/backend_api.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/productos")
async def obtener_productos():
    return [
        {"id": 1, "nombre": "Notebook", "precio": 900000},
        {"id": 2, "nombre": "Monitor", "precio": 250000}
    ]