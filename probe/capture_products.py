import json, re
from playwright.sync_api import sync_playwright

captured = []

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

        def on_response(resp):
            try:
                url = resp.url
                if "instaleap.io" not in url:
                    return
                req = resp.request
                pd = req.post_data or ""
                ops = re.findall(r'"operationName"\s*:\s*"([^"]+)"', pd)
                # use body() bytes then decode safely
                try:
                    raw = resp.body()
                    body = raw.decode("utf-8", errors="replace")
                except Exception as e:
                    body = "<<bodyerr %s>>" % e
                captured.append({
                    "ops": ops,
                    "url": url,
                    "method": req.method,
                    "status": resp.status,
                    "req_headers": dict(req.headers or {}),
                    "post_data": pd,
                    "body": body,
                })
                print(f"CAPTURED {ops} {resp.status} {len(body)}b")
            except Exception as e:
                print("err", e)

        page.on("response", on_response)
        # Navigate to category. Try a couple to trigger product listing
        for url in ["https://www.acuenta.cl/ca/bebidas-y-snacks/02"]:
            print("goto", url)
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print("goto warn:", e)
            page.wait_for_timeout(9000)
            for _ in range(8):
                page.evaluate("window.scrollBy(0,1800)")
                page.wait_for_timeout(1400)
        browser.close()

    with open("captures/acuenta_products_raw.json","w",encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print("\nSUMMARY ops captured:")
    for c in captured:
        print(f"- {c['ops']} {c['status']} {len(c['body'])}b postlen={len(c['post_data'])}")

if __name__ == "__main__":
    main()
