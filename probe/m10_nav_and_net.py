import json, os, re
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
data = json.load(open(os.path.join(OUT, "m10_ofertas_next.json"), encoding="utf-8"))
nav = data["props"]["pageProps"]["navbar"]
print("=== NAV (Contentful fields) ===")
for it in nav.get("navItems") or []:
    f = it.get("fields") or {}
    print(json.dumps(f, ensure_ascii=False)[:300])

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
SKIP = ("google","facebook","datadog","newrelic","hotjar","clarity","gstatic",
        "doubleclick","onetrust","cookiebot","analytics","gtm","fonts.")
seen = []
PRICE = re.compile(r'"(price|precio|sellingPrice|listPrice|offer-?price)"\s*:\s*"?\d', re.I)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled","--no-sandbox"])
    ctx = browser.new_context(viewport={"width":1366,"height":900}, locale="es-CL",
        timezone_id="America/Santiago", user_agent=UA)
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    page = ctx.new_page()

    def on_resp(r):
        u = r.url
        if any(s in u for s in SKIP):
            return
        ct = (r.headers or {}).get("content-type","").lower()
        rec = {"url": u, "status": r.status, "method": r.request.method, "ct": ct}
        is_api = ("json" in ct) or ("/api/" in u) or ("graphql" in u) or ("catalog" in u)
        if is_api:
            try:
                body = r.text()
                rec["has_price"] = bool(PRICE.search(body))
                rec["bytes"] = len(body)
            except Exception:
                rec["has_price"] = None
            seen.append(rec)

    page.on("response", on_resp)
    # Visit ofertas + try category routes that SMU sites use
    for u in ["https://www.mayorista10.cl/ofertas",
              "https://www.mayorista10.cl/",
              "https://www.mayorista10.cl/categoria",
              "https://www.mayorista10.cl/productos",
              "https://www.mayorista10.cl/tienda"]:
        try:
            resp = page.goto(u, timeout=40000, wait_until="domcontentloaded")
            print(f"\nGOTO {u} -> {resp.status if resp else '?'}")
        except Exception as e:
            print(f"\nGOTO {u} ERR {e}")
            continue
        page.wait_for_timeout(3500)
        for _ in range(4):
            try: page.evaluate("window.scrollBy(0,1400)")
            except: break
            page.wait_for_timeout(900)

    browser.close()

print("\n=== API-ish responses ===")
for r in seen:
    print(f"{r['status']} {r['method']} price={r.get('has_price')} {r.get('bytes','?')}b  {r['url'][:120]}")
json.dump(seen, open(os.path.join(OUT,"m10_network.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
