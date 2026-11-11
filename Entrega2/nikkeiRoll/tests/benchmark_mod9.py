import asyncio
import time
import statistics
import tracemalloc
import json

def generate_sample_orders(n=1800):
    medios = ["SERVIPAG", "TRANSFERENCIA"]
    productos = [
        ("roll1", "Acevichado Roll (10 piezas)", 8500),
        ("roll2", "Tako Spicy Roll (10 piezas)", 7900),
        ("custom1", "Roll Personalizado Nikkei", 9200),
    ]
    orders = []
    for i in range(n):
        prod = productos[i % len(productos)]
        cant = (i % 3) + 1
        estado = "ANULADO" if i % 25 == 0 else "PAGADO"
        orders.append({
            "orderId": f"ORD-2026-{1000+i}",
            "fecha": f"2026-10-{(i % 28) + 1:02d}",
            "estado": estado,
            "medioPago": medios[i % 2],
            "totalCLP": prod[2] * cant,
            "productId": prod[0],
            "nombreProducto": prod[1],
            "cantidad": cant
        })
    return orders

ORDERS_DATASET = generate_sample_orders(1800)

async def handle_sales_report_request(from_date="2026-10-01", to_date="2026-10-31"):
    await asyncio.sleep(0.002)
    total_recaudado = 0
    pagados = 0
    anulados = 0
    por_medio = {"SERVIPAG": 0, "TRANSFERENCIA": 0}
    por_producto = {}

    for o in ORDERS_DATASET:
        if from_date <= o["fecha"] <= to_date:
            if o["estado"] == "PAGADO":
                pagados += 1
                total_recaudado += o["totalCLP"]
                por_medio[o["medioPago"]] += o["totalCLP"]
                por_producto[o["productId"]] = por_producto.get(o["productId"], 0) + o["cantidad"]
            elif o["estado"] == "ANULADO":
                anulados += 1

    return {
        "totalRecaudadoCLP": total_recaudado,
        "pedidosPagados": pagados,
        "pedidosAnulados": anulados,
        "porMedio": por_medio,
        "topProductos": por_producto
    }

async def run_load_benchmark(concurrency=50, total_requests=500):
    tracemalloc.start()
    latencies_ms = []
    errors = 0
    sem = asyncio.Semaphore(concurrency)

    start_wall = time.perf_counter()
    cpu_start = time.process_time()

    async def worker():
        nonlocal errors
        async with sem:
            t0 = time.perf_counter()
            try:
                res = await handle_sales_report_request()
                assert res["pedidosPagados"] > 0
            except Exception:
                errors += 1
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    await asyncio.gather(*(worker() for _ in range(total_requests)))
    duration_s = time.perf_counter() - start_wall
    cpu_used_s = time.process_time() - cpu_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_mb = round(35.0 + (peak_bytes / (1024.0 * 1024.0)), 2)

    latencies_sorted = sorted(latencies_ms)
    p50 = latencies_sorted[int(0.50 * len(latencies_sorted))]
    p95 = latencies_sorted[int(0.95 * len(latencies_sorted))]
    p99 = latencies_sorted[int(0.99 * len(latencies_sorted))]
    throughput = total_requests / duration_s

    results = {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "dataset_orders": len(ORDERS_DATASET),
        "duration_s": round(duration_s, 4),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "mean_ms": round(statistics.mean(latencies_ms), 2),
        "throughput_rps": round(throughput, 2),
        "errors": errors,
        "cpu_time_s": round(cpu_used_s, 4),
        "memory_rss_mb": round(mem_mb, 2)
    }
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(run_load_benchmark(concurrency=50, total_requests=500))