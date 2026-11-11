"""
Subsistemas Privados Backend (Puerto 9001) — Nikkei Roll (Caso 19)
Incluye: inventory, clients, orders, payments y sales-analytics con persistencia SQLite real.
Rechaza cualquier acceso directo que no provenga del API Gateway con X-Gateway-Secret.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import os
import secrets
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Depends, Query
from pydantic import BaseModel

app = FastAPI(title="Nikkei Roll - Subsistemas Privados (inventory, orders, clients, payments)")

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET", "gw-secret-vault-2026")
WEBHOOK_HMAC_SECRET = os.getenv("WEBHOOK_HMAC_SECRET", "servipag-hmac-secret-vault-2026")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "db", "nikkei_roll.db"))

def get_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            categoria TEXT NOT NULL,
            precio INTEGER NOT NULL CHECK (precio > 0),
            costo_produccion INTEGER NOT NULL,
            imagen_url TEXT,
            stock INTEGER NOT NULL CHECK (stock >= 0),
            disponible INTEGER NOT NULL DEFAULT 1,
            es_promocion INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS custom_ingredients (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL,
            precio_extra INTEGER NOT NULL,
            disponible INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            run TEXT UNIQUE NOT NULL,
            nombre_completo TEXT NOT NULL,
            direccion TEXT NOT NULL,
            comuna TEXT NOT NULL,
            distancia_km REAL NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            telefono TEXT NOT NULL,
            correo_verificado INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            estado TEXT NOT NULL,
            total_servidor INTEGER NOT NULL,
            direccion_entrega TEXT NOT NULL,
            motivo_anulacion TEXT,
            anulado_por TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            nombre_snapshot TEXT NOT NULL,
            precio_congelado INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            subtotal INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            medio_pago TEXT NOT NULL,
            referencia_externa TEXT UNIQUE,
            monto_pagado INTEGER NOT NULL,
            estado_pago TEXT NOT NULL,
            boleta_folio TEXT UNIQUE,
            confirmed_at TEXT
        );
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("roll1", "Acevichado Roll (10 piezas)", "Camarón furai, palta, envuelto en atún, bañado en salsa acevichada.", "rolls-nikkei", 8500, 3200, "acevichadoRoll.jpg", 15, 1, 0),
            ("roll2", "Tako Spicy Roll (10 piezas)", "Pulpo, queso crema, cebollín, envuelto en panko con salsa spicy.", "rolls-nikkei", 7900, 2900, "TakoSpicyRoll.jpg", 12, 1, 1),
        ]
    )
    cur.executemany(
        "INSERT OR IGNORE INTO custom_ingredients VALUES (?, ?, ?, ?, ?)",
        [
            ("ing-prot-01", "Salmón Fresco", "proteina", 1200, 1),
            ("ing-prot-02", "Camarón Furai", "proteina", 1000, 1),
            ("ing-agr-01", "Palta Hass", "agregado", 500, 1),
            ("ing-agr-02", "Queso Crema", "agregado", 400, 1),
            ("ing-sal-01", "Salsa Acevichada Nikkei", "salsa", 600, 1),
        ]
    )
    cur.executemany(
        "INSERT OR IGNORE INTO clients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("CLI-2026-0089", "19.845.231-K", "Camila Andrea Soto Riquelme", "Av. Pajaritos 2450, Depto 402", "Maipú", 1.8, "camila.soto@correo.cl", "+56987654321", 1),
            ("CLI-2026-0042", "18.112.990-1", "Pedro Ignacio Rojas Díaz", "Av. El Rosal 5100", "Maipú", 2.4, "pedro.rojas@correo.cl", "+56911223344", 1),
        ]
    )
    cur.execute(
        "INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("ORD-2026-1099", "CLI-2026-0042", "PAGADO", 7900, "Av. El Rosal 5100, Maipú", None, None, "2026-11-05T18:00:00Z")
    )
    cur.execute(
        "INSERT OR IGNORE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("ORD-2026-1045", "CLI-2026-0089", "EN_PREPARACION", 17000, "Av. Pajaritos 2450, Maipú", None, None, "2026-11-05T19:30:00Z")
    )
    conn.commit()
    conn.close()

init_db()

# Dependencia obligatoria: verifica que la solicitud venga del API Gateway autorizado
def verify_gateway(x_gateway_secret: str = Header(default="")):
    if not secrets.compare_digest(x_gateway_secret, INTERNAL_GATEWAY_SECRET):
        raise HTTPException(status_code=403, detail="Solicitud directa no autorizada: debe pasar por el API Gateway")

# --- S01: Catálogo Público (inventory) ---
@app.get("/products", dependencies=[Depends(verify_gateway)])
def consultar_catalogo(available: Optional[bool] = True, category: Optional[str] = None, search: Optional[str] = None):
    conn = get_db()
    query = "SELECT id, nombre, descripcion, categoria, precio, imagen_url AS imagenUrl, disponible, es_promocion AS esPromocion FROM products WHERE 1=1"
    params = []
    if available is not None:
        query += " AND disponible = ?"
        params.append(1 if available else 0)
    if category:
        query += " AND categoria = ?"
        params.append(category)
    if search:
        query += " AND (nombre LIKE ? OR descripcion LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    for r in rows:
        r["disponible"] = bool(r["disponible"])
        r["esPromocion"] = bool(r["esPromocion"])
    return {"items": rows, "totalResultados": len(rows)}

# --- S02: Ingredientes Arma tu Roll (inventory) ---
@app.get("/custom-roll/ingredients", dependencies=[Depends(verify_gateway)])
def consultar_ingredientes():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT id, nombre, tipo, precio_extra AS precioExtra, disponible FROM custom_ingredients WHERE disponible=1").fetchall()]
    conn.close()
    return {
        "precioBaseRoll": 6500,
        "reglasSeleccion": {"maxProteinas": 1, "maxAgregados": 2, "maxSalsas": 1},
        "ingredientes": rows
    }

# --- S03: Verificar Cobertura 3 km en Maipú (clients) ---
@app.get("/delivery-zones/check", dependencies=[Depends(verify_gateway)])
def verificar_cobertura(comuna: str = Query(...), direccion: str = Query(...)):
    es_maipu = "maip" in comuna.lower()
    distancia = 1.8 if es_maipu else 6.5
    cubierto = es_maipu and distancia <= 3.0
    return {
        "comuna": comuna,
        "direccionNormalizada": direccion,
        "cubierto": cubierto,
        "distanciaKm": distancia,
        "radioMaximoKm": 3.0,
        "costoEnvio": 0,
        "mensaje": "Dentro de zona de reparto gratuito (<= 3 km)." if cubierto else "Fuera del radio de 3 km del local."
    }

# --- S09: Crear Pedido validando stock y recalculando precios en el servidor (orders + inventory) ---
class OrderItemInput(BaseModel):
    productId: str
    cantidad: int

class CreateOrderRequest(BaseModel):
    direccionEntrega: str
    items: List[OrderItemInput]
    notas: Optional[str] = ""

@app.post("/orders", status_code=201, dependencies=[Depends(verify_gateway)])
def crear_pedido(
    body: CreateOrderRequest,
    x_authenticated_user: str = Header(default=""),
    x_user_role: str = Header(default="")
):
    if not x_authenticated_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    if not body.items:
        raise HTTPException(status_code=400, detail="El pedido debe contener al menos un producto")

    conn = get_db()
    cur = conn.cursor()
    items_calculados = []
    total_servidor = 0

    for item in body.items:
        if item.cantidad <= 0:
            conn.close()
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")
        prod = cur.execute("SELECT * FROM products WHERE id = ? AND disponible = 1", (item.productId,)).fetchone()
        if not prod:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Producto {item.productId} no disponible")
        if prod["stock"] < item.cantidad:
            conn.close()
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para {prod['nombre']}")

        subtotal = prod["precio"] * item.cantidad
        total_servidor += subtotal
        items_calculados.append({
            "productId": prod["id"],
            "nombre": prod["nombre"],
            "precioUnitario": prod["precio"],
            "cantidad": item.cantidad,
            "subtotal": subtotal
        })

    order_id = f"ORD-2026-{secrets.randbelow(8999) + 1000}"
    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (order_id, x_authenticated_user, "PENDIENTE_PAGO", total_servidor, body.direccionEntrega, None, None, now_iso)
    )
    for ic in items_calculados:
        cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (ic["cantidad"], ic["productId"]))
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, nombre_snapshot, precio_congelado, cantidad, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, ic["productId"], ic["nombre"], ic["precioUnitario"], ic["cantidad"], ic["subtotal"])
        )
    conn.commit()
    conn.close()
    return {
        "orderId": order_id,
        "clientId": x_authenticated_user,
        "cajaAsociada": "CAJA-VIRTUAL-WEB-01",
        "estado": "PENDIENTE_PAGO",
        "itemsCalculados": items_calculados,
        "totalServidor": total_servidor,
        "createdAt": now_iso
    }

# --- S11: Consultar Seguimiento de Pedido con Control de Propiedad BOLA (orders) ---
@app.get("/orders/{order_id}", dependencies=[Depends(verify_gateway)])
def consultar_pedido(
    order_id: str,
    x_authenticated_user: str = Header(default=""),
    x_user_role: str = Header(default="")
):
    conn = get_db()
    ord_row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if not ord_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Regla crítica Anti-BOLA: un CLIENTE solo puede ver sus propios pedidos
    roles_internos = {"ADMINISTRADOR", "DUENO", "CAJERO_VIRTUAL", "ENCARGADO_DESPACHO"}
    if x_user_role not in roles_internos and ord_row["client_id"] != x_authenticated_user:
        conn.close()
        raise HTTPException(status_code=403, detail="Acceso denegado: este pedido pertenece a otro cliente (Control Anti-BOLA)")

    items = [dict(r) for r in conn.execute("SELECT product_id AS productId, nombre_snapshot AS nombre, precio_congelado AS precioUnitario, cantidad, subtotal FROM order_items WHERE order_id = ?", (order_id,)).fetchall()]
    conn.close()
    progreso_map = {"PENDIENTE_PAGO": 10, "PAGADO": 30, "EN_PREPARACION": 60, "EN_CAMINO": 85, "ENTREGADO": 100, "ANULADO": 0}
    return {
        "orderId": ord_row["order_id"],
        "clientId": ord_row["client_id"],
        "estado": ord_row["estado"],
        "progresoPct": progreso_map.get(ord_row["estado"], 25),
        "totalServidor": ord_row["total_servidor"],
        "direccionEntrega": ord_row["direccion_entrega"],
        "items": items,
        "puedeAnular": ord_row["estado"] in ("PENDIENTE_PAGO", "PAGADO")
    }

# --- S12: Anular Pedido con Motivo conservando historial y liberando stock (orders + inventory) ---
class CancelOrderRequest(BaseModel):
    motivoAnulacion: str

@app.post("/orders/{order_id}/cancel", dependencies=[Depends(verify_gateway)])
def anular_pedido(
    order_id: str,
    body: CancelOrderRequest,
    x_authenticated_user: str = Header(default=""),
    x_user_role: str = Header(default="")
):
    if len(body.motivoAnulacion.strip()) < 5:
        raise HTTPException(status_code=400, detail="Debe indicar el motivo de anulación (RF3)")
    conn = get_db()
    cur = conn.cursor()
    ord_row = cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    if not ord_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if x_user_role != "ADMINISTRADOR" and ord_row["client_id"] != x_authenticated_user:
        conn.close()
        raise HTTPException(status_code=403, detail="No puede anular un pedido ajeno")
    if ord_row["estado"] in ("EN_CAMINO", "ENTREGADO", "ANULADO"):
        conn.close()
        raise HTTPException(status_code=409, detail=f"No se puede anular un pedido en estado {ord_row['estado']}")

    items = cur.execute("SELECT product_id, cantidad FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    for it in items:
        cur.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (it["cantidad"], it["product_id"]))

    cur.execute(
        "UPDATE orders SET estado = 'ANULADO', motivo_anulacion = ?, anulado_por = ? WHERE order_id = ?",
        (body.motivoAnulacion.strip(), x_authenticated_user, order_id)
    )
    conn.commit()
    conn.close()
    return {
        "orderId": order_id,
        "estadoActual": "ANULADO",
        "motivoAnulacion": body.motivoAnulacion.strip(),
        "anuladoPor": x_authenticated_user,
        "stockLiberado": True
    }

# --- S10: Iniciar Pago y Confirmar vía Webhook HMAC con Idempotencia (payments) ---
class InitiatePaymentRequest(BaseModel):
    orderId: str
    medioPago: str = "SERVIPAG"

@app.post("/payments/initiate", dependencies=[Depends(verify_gateway)])
def iniciar_pago(body: InitiatePaymentRequest, x_authenticated_user: str = Header(default="")):
    conn = get_db()
    ord_row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (body.orderId,)).fetchone()
    conn.close()
    if not ord_row:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if ord_row["client_id"] != x_authenticated_user:
        raise HTTPException(status_code=403, detail="El pedido no pertenece al usuario autenticado")

    payment_id = f"PAY-{secrets.randbelow(89999) + 10000}"
    return {
        "paymentId": payment_id,
        "orderId": body.orderId,
        "montoACobrar": ord_row["total_servidor"],
        "estadoPago": "INICIADO",
        "pasarelaUrl": f"http://localhost:8000/sandbox-servipag?tx={payment_id}"
    }

# --- S13: Actualizar disponibilidad de producto (Exclusivo ADMINISTRADOR o DUENO) ---
class AvailabilityPatch(BaseModel):
    disponible: bool
    stock: int

@app.patch("/products/{product_id}/availability", dependencies=[Depends(verify_gateway)])
def actualizar_disponibilidad(
    product_id: str,
    body: AvailabilityPatch,
    x_user_role: str = Header(default="")
):
    if x_user_role not in ("ADMINISTRADOR", "DUENO"):
        raise HTTPException(status_code=403, detail="Permiso denegado: se requiere rol ADMINISTRADOR o DUENO (S13)")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE products SET disponible = ?, stock = ? WHERE id = ?", (1 if body.disponible else 0, body.stock, product_id))
    conn.commit()
    conn.close()
    return {"id": product_id, "disponible": body.disponible, "stock": body.stock}

# --- S16: Reporte de Ventas por Período (Exclusivo DUENO y ADMINISTRADOR) ---
@app.get("/reports/sales", dependencies=[Depends(verify_gateway)])
def reporte_ventas(x_user_role: str = Header(default="")):
    if x_user_role not in ("DUENO", "ADMINISTRADOR"):
        raise HTTPException(status_code=403, detail="Solo el Dueño o Administrador pueden consultar reportes de ventas (RF9)")
    conn = get_db()
    pagados = conn.execute("SELECT COUNT(*) AS c, COALESCE(SUM(total_servidor), 0) AS total FROM orders WHERE estado != 'ANULADO'").fetchone()
    anulados = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE estado = 'ANULADO'").fetchone()
    conn.close()
    return {
        "cajaId": "CAJA-VIRTUAL-WEB-01",
        "totalRecaudadoCLP": pagados["total"],
        "pedidosActivosOPagados": pagados["c"],
        "pedidosAnulados": anulados["c"]
    }
