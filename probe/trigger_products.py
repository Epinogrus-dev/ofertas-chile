import json, re
from playwright.sync_api import sync_playwright

posts = []

def main():
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

        store_map = {}

        def on_request(req):
            if "instaleap.io" in req.url and req.method == "POST":
                pd = req.post_data or ""
                ops = re.findall(r'"operationName"\s*:\s*"([^"]+)"', pd)
                store_map[id(req)] = (ops, pd, dict(req.headers or {}))

        def on_response(resp):
            req = resp.request
            if "instaleap.io" in resp.url and req.method == "POST":
                pd = req.post_data or ""
                ops = re.findall(r'"operationName"\s*:\s*"([^"]+)"', pd)
                try:
                    raw = resp.body()
                    body = raw.decode("utf-8", errors="replace")
                except Exception as e:
                    body = "<<err %s>>" % e
                # only keep non-binary json
                if body.startswith("[") or body.startswith("{"):
                    posts.append({
                        "ops": ops, "status": resp.status,
                        "post_data": pd, "body": body,
                        "req_headers": dict(req.headers or {}),
                    })
                    print(f"JSON POST {ops} {resp.status} {len(body)}b")

        page.on("request", on_request)
        page.on("response", on_response)

        print("goto home")
        try:
            page.goto("https://www.acuenta.cl", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print("warn", e)
        page.wait_for_timeout(7000)

        # Try using the search box to trigger product search
        try:
            # common search input
            page.fill("input[type='search'], input[name='search'], input[placeholder*='Busca'], input[placeholder*='busca']", "leche")
            page.keyboard.press("Enter")
            print("searched 'leche'")
        except Exception as e:
            print("search warn", e)
        page.wait_for_timeout(8000)
        for _ in range(5):
            page.evaluate("window.scrollBy(0,1500)")
            page.wait_for_timeout(1200)

        # Also try navigating to a search url pattern
        for u in ["https://www.acuenta.cl/search?q=leche",
                  "https://www.acuenta.cl/busqueda?q=leche"]:
            try:
                page.goto(u, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(6000)
                for _ in range(4):
                    page.evaluate("window.scrollBy(0,1500)")
                    page.wait_for_timeout(1000)
            except Exception as e:
                print("nav warn", u, e)

        browser.close()

    with open("captures/acuenta_posts.json","w",encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print("\nALL JSON POST ops:")
    for c in posts:
        print(f"- {c['ops']} {c['status']} {len(c['body'])}b")

if __name__ == "__main__":
    main()
