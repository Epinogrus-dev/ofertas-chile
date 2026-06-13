"""Probe Mayorista10 /ofertas -> __NEXT_DATA__ and inspect offer field names."""
import json, os, re
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

URLS = ["https://www.mayorista10.cl/ofertas", "https://www.mayorista10.cl/"]
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled", "--no-sandbox"])
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 900}, locale="es-CL",
        timezone_id="America/Santiago", user_agent=UA)
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    page = ctx.new_page()
    for u in URLS:
        print(f"== GOTO {u} ==")
        try:
            resp = page.goto(u, timeout=45000, wait_until="domcontentloaded")
            print("status:", resp.status if resp else None)
        except Exception as e:
            print("goto err:", e)
            continue
        page.wait_for_timeout(4000)
        html = page.content()
        m = _NEXT.search(html)
        tag = u.rstrip("/").split("/")[-1] or "home"
        with open(os.path.join(OUT, f"m10_{tag}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        if not m:
            print("  NO __NEXT_DATA__ found. html len:", len(html))
            continue
        data = json.loads(m.group(1))
        with open(os.path.join(OUT, f"m10_{tag}_next.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        pp = data.get("props", {}).get("pageProps", {})
        print("  pageProps keys:", list(pp.keys()))
        pagek = pp.get("page", {})
        if isinstance(pagek, dict):
            print("  page keys:", list(pagek.keys()))
            prod = pagek.get("productos")
            if isinstance(prod, dict):
                print("  productos keys:", list(prod.keys()))
                offers = prod.get("offers") or []
                print("  offers count:", len(offers))
                if offers:
                    print("  FIRST OFFER:")
                    print(json.dumps(offers[0], ensure_ascii=False, indent=2)[:1500])
                    print("  offer field names across first 5:")
                    keys = set()
                    for o in offers[:5]:
                        keys.update(o.keys())
                    print("  ", sorted(keys))
    browser.close()
