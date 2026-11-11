#!/usr/bin/env bash
echo "===================================================================="
echo "  INICIANDO PROYECTO NIKKEI ROLL (CASO 19) EN LOCALHOST"
echo "  Equipo: Leonardo Onetto y Claudio Núñez"
echo "===================================================================="

uvicorn backend.auth-service.auth_service:app --host 127.0.0.1 --port 9000 &
PID_AUTH=$!
uvicorn backend.core-services.backend_nikkei:app --host 127.0.0.1 --port 9001 &
PID_CORE=$!
uvicorn backend.api-gateway.gateway_api:app --host 127.0.0.1 --port 8000 &
PID_GW=$!
python3 -m http.server 3000 --directory frontend &
PID_FE=$!

echo ""
echo " Todos los servicios están corriendo en el computador:"
echo "   • Frontend Web:          http://localhost:3000/nikkei_roll_delivery.html"
echo "   • API Gateway (Swagger): http://localhost:8000/docs"
echo "   • Auth Service Interno:  http://localhost:9000"
echo "   • Backend Privado:       http://localhost:9001"
echo ""
echo "Presiona Ctrl+C para detener todos los servicios."
trap "kill $PID_AUTH $PID_CORE $PID_GW $PID_FE 2>/dev/null; exit 0" SIGINT SIGTERM
wait
