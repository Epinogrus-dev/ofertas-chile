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
                body = resp.text()
                captured.append({
                    "url": url,
                    "method": req.method,
                    "status": resp.status,
                    "req_headers": dict(req.headers or {}),
                    "post_data": req.post_data,
                    "body": body,
                })
                print(f"CAPTURED instaleap: {req.method} {resp.status} {len(body)}b")
            except Exception as e:
                print("err", e)

        page.on("response", on_response)
        url = "https://www.acuenta.cl/ca/bebidas-y-snacks/02"
        print("goto", url)
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print("goto warn:", e)
        page.wait_for_timeout(10000)
        for _ in range(4):
            page.evaluate("window.scrollBy(0,1500)")
            page.wait_for_timeout(1500)
        browser.close()

    # pick the biggest body with products
    captured.sort(key=lambda c: len(c["body"]), reverse=True)
    with open("captures/acuenta_instaleap.json","w",encoding="utf-8") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print("saved", len(captured), "instaleap captures")
    for c in captured:
        pd = c["post_data"] or ""
        # try to find operationName
        opn = re.findall(r'"operationName"\s*:\s*"([^"]+)"', pd)
        print(f"- {c['method']} {c['status']} {len(c['body'])}b op={opn} postlen={len(pd)}")

if __name__ == "__main__":
    main()
