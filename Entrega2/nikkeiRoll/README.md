# Proyecto Nikkei Roll (Caso 19) — Guía Rápida de Ejecución en Localhost
**Integrantes:** Leonardo Onetto y Claudio Núñez

## Puertos del Sistema en tu Computador
- **`http://localhost:3000/nikkei_roll_delivery.html`** -> Frontend Web responsivo.
- **`http://localhost:8000`** -> **API Gateway** (única puerta pública a la que llama el frontend)
- **`http://localhost:9000`** -> **Auth Service** (servicio interno de login y tokens).
- **`http://localhost:9001`** -> **Backend Privado** (`inventory`, `orders`, `clients`, `payments` con base de datos SQLite `backend/db/nikkei_roll.db`). Si intentas entrar directo a `http://localhost:9001/products` desde el navegador, te dará `403 Forbidden` porque exige pasar por el Gateway.

## Cómo Ejecutar Todo Paso a Paso

### 1. Instalar librerías de Python (una sola vez)
Abre una terminal (PowerShell / CMD en Windows) dentro de la carpeta `nikkeiRoll` y ejecuta:
```bash
pip install -r requirements.txt
```

### 2. Iniciar el sistema completo
- **En Windows:** Haz doble clic en `iniciar_todo.bat` (o ejecuta `.\iniciar_todo.bat` en la terminal).
- **En Mac / Linux:** Ejecuta `./iniciar_todo.sh`.  

### 3. Probar la aplicación en el navegador
1. Abre **`http://localhost:3000/nikkei_roll_delivery.html`**.
2. Haz clic arriba a la derecha en **"Perfil / Login"** e ingresa con una de las cuentas de prueba:
   - **Cliente Camila:** Correo `camila.soto@correo.cl` | Contraseña `1234`
   - **Cliente Pedro:** Correo `pedro.rojas@correo.cl` | Contraseña `5678`
   - **Administrador:** Correo `admin@nikkeiroll.cl` | Contraseña `admin123`
   - **Dueño:** Correo `dueno@nikkeiroll.cl` | Contraseña `dueno123`
3. Agrega rolls al carrito y pulsa **"Ir a Pagar"**: verás cómo el API Gateway valida tu token, el servidor calcula el total oficial en SQLite y te devuelve el número de orden y transacción de pago.

### 4. Ejecutar las Pruebas Automatizadas (Módulo 9 y Módulo 10)
```bash
python tests/test_suite_mod10.py
python tests/benchmark_mod9.py
```
