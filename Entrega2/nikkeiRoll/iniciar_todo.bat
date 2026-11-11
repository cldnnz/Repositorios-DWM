@echo off
echo ====================================================================
echo   INICIANDO PROYECTO NIKKEI ROLL (CASO 19) EN LOCALHOST
echo   Equipo: Leonardo Onetto y Claudio Nunez
echo ====================================================================

echo [0/4] Verificando librerias necesarias...
python -m pip install -r requirements.txt

echo [1/4] Iniciando Auth Service en http://localhost:9000 ...
start "Nikkei Auth Service (9000)" cmd /k "python -m uvicorn auth_service:app --app-dir backend/auth-service --host 127.0.0.1 --port 9000"

echo [2/4] Iniciando Microservicios Backend Privados en http://localhost:9001 ...
start "Nikkei Core Backend (9001)" cmd /k "python -m uvicorn backend_nikkei:app --app-dir backend/core-services --host 127.0.0.1 --port 9001"

echo [3/4] Iniciando API Gateway Seguro en http://localhost:8000 ...
start "Nikkei API Gateway (8000)" cmd /k "python -m uvicorn gateway_api:app --app-dir backend/api-gateway --host 127.0.0.1 --port 8000"

echo [4/4] Iniciando Servidor Web del Frontend en http://localhost:3000 ...
start "Nikkei Frontend Web (3000)" cmd /k "python -m http.server 3000 --directory frontend"

echo.
echo Listo! Abre tu navegador en: http://localhost:3000/nikkei_roll_delivery.html
pause