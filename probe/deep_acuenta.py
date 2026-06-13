import json, re
from playwright.sync_api import sync_playwright

reqs = []

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
                ct = (resp.headers or {}).get("content-type", "").lower()
                # log everything that is xhr/fetch-ish or api-ish
                if url.startswith("data:"): return
                req = resp.request
                rt = req.resource_type
                if rt in ("image","font","stylesheet","media"): return
                body_snip = ""
                blen = 0
                try:
                    b = resp.text()
                    blen = len(b)
                    body_snip = b[:600]
                except Exception:
                    pass
                # detect product signals
                price_hits = len(re.findall(r'(listPrice|sellingPrice|"price"|precio|normalPrice|internetPrice)', body_snip, re.I))
                reqs.append({
                    "url": url,
                    "method": req.method,
                    "rtype": rt,
                    "status": resp.status,
                    "ct": ct,
                    "blen": blen,
                    "price_signals": price_hits,
                    "post_data": (req.post_data or "")[:300],
                    "req_headers": {k:v for k,v in (req.headers or {}).items() if k.lower() in ("content-type","authorization","apikey","x-api-key","ocp-apim-subscription-key","x-channel","x-commerce","x-cnc-locale","x-requested-with")},
                })
            except Exception as e:
                pass

        page.on("response", on_response)
        url = "https://www.acuenta.cl/ca/bebidas-y-snacks/02"
        print("goto", url)
        try:
            page.goto(url, timeout=60000, wait_until="networkidle")
        except Exception as e:
            print("goto warn:", e)
        page.wait_for_timeout(6000)
        for _ in range(6):
            page.evaluate("window.scrollBy(0,1500)")
            page.wait_for_timeout(1500)
        # Also check __NEXT_DATA__ / window state
        nextdata = page.evaluate("""() => { const el=document.getElementById('__NEXT_DATA__'); return el? el.textContent.slice(0,2000): null; }""")
        print("HAS __NEXT_DATA__:", bool(nextdata))
        if nextdata:
            print(nextdata[:1500])
        browser.close()

    # sort by interest
    reqs.sort(key=lambda r:(r["price_signals"], r["blen"]), reverse=True)
    with open("captures/acuenta_network.json","w",encoding="utf-8") as f:
        json.dump(reqs, f, ensure_ascii=False, indent=2)
    print("\n=== TOP NETWORK (by price signals / size) ===")
    for r in reqs[:30]:
        print(f"{r['method']} {r['status']} sig={r['price_signals']} {r['blen']}b {r['ct'][:30]} {r['url'][:110]}")

if __name__ == "__main__":
    main()
