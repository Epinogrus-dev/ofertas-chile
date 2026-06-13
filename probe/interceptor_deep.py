"""
Probe profundo: captura el PAYLOAD del request y el BODY COMPLETO de respuestas
de los hosts de API (bff., api., apis.) para entender el contrato exacto.

Uso: python interceptor_deep.py <store> <url> <host_substr>
"""
import sys, json, os
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT_DIR, exist_ok=True)


def main():
    store = sys.argv[1] if len(sys.argv) > 1 else "jumbo"
    url = sys.argv[2] if len(sys.argv) > 2 else "https://www.jumbo.cl/almacen"
    host = sys.argv[3] if len(sys.argv) > 3 else "bff.jumbo.cl"

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
                if host not in resp.url:
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
                    "request_headers": {k: v for k, v in (req.headers or {}).items()
                                        if k.lower() in ("content-type", "authorization",
                                                         "x-api-key", "apikey", "ocp-apim-subscription-key",
                                                         "x-channel", "x-commerce")},
                    "post_data": req.post_data,
                    "resp_bytes": len(body),
                    "body": body,
                })
            except Exception as e:
                print("err", e)

        page.on("response", on_response)
        print(f"[deep] navegando a {url} (host={host})")
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"[deep] goto warn: {e}")
        page.wait_for_timeout(6000)
        for _ in range(6):
            page.evaluate("window.scrollBy(0, 1400)")
            page.wait_for_timeout(1500)
        browser.close()

    captured.sort(key=lambda x: -x["resp_bytes"])
    print(f"\n[deep] {len(captured)} respuestas de {host}")
    for i, c in enumerate(captured[:8]):
        print(f"\n#{i} {c['status']} {c['method']} {c['resp_bytes']}b  {c['url'][:140]}")
        if c["post_data"]:
            print(f"   PAYLOAD: {c['post_data'][:400]}")
        print(f"   HEADERS: {c['request_headers']}")

    out = os.path.join(OUT_DIR, f"{store}_deep.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print(f"\n[deep] guardado: {out}")


if __name__ == "__main__":
    main()
