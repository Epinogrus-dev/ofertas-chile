"""
Probe interceptor: carga una pagina de ofertas en un navegador real (Playwright)
y captura TODAS las respuestas JSON que el sitio pide por XHR/fetch.
Asi descubrimos el endpoint real de la API interna y la estructura de los datos,
sin adivinar selectores HTML ni endpoints.

Uso:
    python interceptor_probe.py <store> <url>
Ejemplo:
    python interceptor_probe.py jumbo https://www.jumbo.cl/ofertas
"""
import sys
import json
import os
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT_DIR, exist_ok=True)

# Palabras que sugieren que una respuesta JSON trae productos/precios
PRODUCT_HINTS = ("price", "Price", "precio", "product", "Product", "items",
                 "sellingPrice", "listPrice", "ProductName", "Offer", "sku", "Sku")


def looks_like_products(text: str) -> bool:
    if not text or len(text) < 50:
        return False
    hits = sum(1 for h in PRODUCT_HINTS if h in text)
    return hits >= 2


def main():
    store = sys.argv[1] if len(sys.argv) > 1 else "jumbo"
    url = sys.argv[2] if len(sys.argv) > 2 else "https://www.jumbo.cl/ofertas"

    captured = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ])
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            locale="es-CL",
            timezone_id="America/Santiago",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"),
        )
        # Ocultar webdriver
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = context.new_page()

        def on_response(resp):
            try:
                ct = (resp.headers or {}).get("content-type", "")
                if "json" not in ct.lower():
                    return
                ru = resp.url
                # Ignorar telemetria / analytics
                if any(s in ru for s in ("google", "facebook", "maze", "storyly",
                                          "segment", "datadog", "newrelic", "px/")):
                    return
                body = resp.text()
                if looks_like_products(body):
                    captured.append({
                        "url": ru,
                        "status": resp.status,
                        "method": resp.request.method,
                        "bytes": len(body),
                        "body_head": body[:1500],
                    })
            except Exception:
                pass

        page.on("response", on_response)

        print(f"[probe] navegando a {url}")
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[probe] goto warn: {e}")
        page.wait_for_timeout(5000)
        # Scroll para disparar carga perezosa
        for _ in range(8):
            page.evaluate("window.scrollBy(0, 1200)")
            page.wait_for_timeout(1200)
        page.wait_for_timeout(2000)
        browser.close()

    # Resumen: endpoints unicos (sin querystring) ordenados por tamano
    print(f"\n[probe] {len(captured)} respuestas JSON con pinta de productos")
    seen = {}
    for c in captured:
        base = c["url"].split("?")[0]
        if base not in seen or c["bytes"] > seen[base]["bytes"]:
            seen[base] = c
    ranked = sorted(seen.values(), key=lambda x: -x["bytes"])
    for i, c in enumerate(ranked[:12]):
        print(f"\n#{i}  {c['status']} {c['method']}  {c['bytes']}b")
        print(f"    {c['url'][:160]}")

    out = os.path.join(OUT_DIR, f"{store}_captures.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)
    print(f"\n[probe] guardado: {out}")


if __name__ == "__main__":
    main()
