"""Captura TODOS los headers de request del endpoint BFF de Unimarc + body completo."""
import sys, json, os
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT_DIR, exist_ok=True)

HOST = "bff-unimarc-ecommerce.unimarc.cl/catalog/product/search"

def main():
    urls = sys.argv[1:] or ["https://www.unimarc.cl/ofertas"]
    captured = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1366, "height": 900}, locale="es-CL",
            timezone_id="America/Santiago",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = context.new_page()

        def on_response(resp):
            try:
                if HOST not in resp.url:
                    return
                req = resp.request
                body = ""
                try:
                    body = resp.text()
                except Exception:
                    pass
                captured.append({
                    "url": resp.url,
                    "status": resp.status,
                    "method": req.method,
                    "all_request_headers": dict(req.headers or {}),
                    "post_data": req.post_data,
                    "resp_bytes": len(body),
                    "body": body,
                })
            except Exception as e:
                print("err", e)

        page.on("response", on_response)
        for url in urls:
            print(f"[bff] navegando a {url}")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[bff] goto warn: {e}")
            page.wait_for_timeout(6000)
            for _ in range(6):
                page.evaluate("window.scrollBy(0, 1400)")
                page.wait_for_timeout(1500)
        browser.close()

    captured.sort(key=lambda x: -x["resp_bytes"])
    print(f"\n[bff] {len(captured)} respuestas de {HOST}")
    for i, c in enumerate(captured[:8]):
        print(f"\n#{i} {c['status']} {c['method']} {c['resp_bytes']}b")
        if c["post_data"]:
            print(f"   PAYLOAD: {c['post_data'][:400]}")
        print(f"   HEADERS: {json.dumps(c['all_request_headers'], ensure_ascii=False)}")

    out = os.path.join(OUT_DIR, "unimarc_bff_full.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print(f"\n[bff] guardado: {out}")

if __name__ == "__main__":
    main()
