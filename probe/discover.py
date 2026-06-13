"""
Descubridor universal de API de productos.
Carga paginas de categoria en un navegador real (Playwright), intercepta TODAS
las respuestas JSON, y guarda la que mas parece un listado de productos:
endpoint, metodo, payload, headers relevantes y el body COMPLETO.

Uso:
    python discover.py <store> <url1> [url2] [url3] ...
Salida:
    captures/<store>_best.json   -> contrato + body completo de la mejor respuesta
    captures/<store>_all.json    -> resumen de todas las respuestas JSON candidatas
"""
import sys, json, os, re

from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT, exist_ok=True)

SKIP_HOSTS = ("google", "facebook", "maze.", "storyly", "segment", "datadog",
              "newrelic", "/px/", "cookiebot", "onetrust", "hotjar", "clarity",
              "doubleclick", "gstatic", "cloudfront.net/atrk", "cdn.cookie")

PRICE_KEYS = ("price", "Price", "precio", "sellingPrice", "listPrice",
              "ProductName", "productName", "name", "nombre")


def product_score(text: str) -> int:
    """Heuristica: cuantos productos-con-precio parece tener la respuesta."""
    if not text or len(text) < 80:
        return 0
    # contar ocurrencias de claves tipicas de producto+precio
    price_hits = len(re.findall(r'"(listPrice|sellingPrice|price|precio)"\s*:', text))
    name_hits = len(re.findall(r'"(name|nombre|ProductName|productName)"\s*:', text))
    return min(price_hits, name_hits)


def main():
    store = sys.argv[1] if len(sys.argv) > 1 else "store"
    urls = sys.argv[2:] or ["https://example.com"]

    candidates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 900}, locale="es-CL",
            timezone_id="America/Santiago",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = ctx.new_page()

        def on_response(resp):
            try:
                url = resp.url
                if any(s in url for s in SKIP_HOSTS):
                    return
                ct = (resp.headers or {}).get("content-type", "").lower()
                if "json" not in ct:
                    return
                body = resp.text()
                score = product_score(body)
                if score < 1:
                    return
                req = resp.request
                candidates.append({
                    "store": store,
                    "url": url,
                    "host": re.sub(r"^https?://([^/]+).*", r"\1", url),
                    "status": resp.status,
                    "method": req.method,
                    "score": score,
                    "bytes": len(body),
                    "req_headers": {k: v for k, v in (req.headers or {}).items()
                                    if k.lower() in ("content-type", "authorization",
                                    "apikey", "x-api-key", "ocp-apim-subscription-key",
                                    "x-channel", "x-commerce", "x-cnc-locale")},
                    "post_data": req.post_data,
                    "body": body,
                })
            except Exception:
                pass

        page.on("response", on_response)

        for u in urls:
            print(f"[discover:{store}] -> {u}")
            try:
                page.goto(u, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"   goto warn: {e}")
            page.wait_for_timeout(5000)
            for _ in range(7):
                try:
                    page.evaluate("window.scrollBy(0, 1300)")
                except Exception:
                    pass
                page.wait_for_timeout(1200)
        browser.close()

    if not candidates:
        print(f"[discover:{store}] SIN candidatos JSON de productos. "
              f"Probablemente la pagina renderiza server-side o bloquea.")
        with open(os.path.join(OUT, f"{store}_best.json"), "w", encoding="utf-8") as f:
            json.dump({"store": store, "found": False}, f, ensure_ascii=False, indent=2)
        return

    # Mejor por score y luego por bytes
    candidates.sort(key=lambda c: (c["score"], c["bytes"]), reverse=True)
    best = candidates[0]

    print(f"\n[discover:{store}] MEJOR ENDPOINT:")
    print(f"   {best['method']} {best['status']}  score={best['score']} {best['bytes']}b")
    print(f"   {best['url'][:150]}")
    print(f"   headers: {best['req_headers']}")
    if best["post_data"]:
        print(f"   payload: {best['post_data'][:300]}")

    with open(os.path.join(OUT, f"{store}_best.json"), "w", encoding="utf-8") as f:
        json.dump({"found": True, **best}, f, ensure_ascii=False, indent=2)

    summary = [{k: c[k] for k in ("url", "host", "status", "method", "score", "bytes",
                                   "req_headers", "post_data")} for c in candidates[:15]]
    with open(os.path.join(OUT, f"{store}_all.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[discover:{store}] guardado captures/{store}_best.json")


if __name__ == "__main__":
    main()
