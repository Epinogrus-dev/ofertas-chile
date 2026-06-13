import json, os, re
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(OUT, exist_ok=True)

URLS = [
    "https://www.alvi.cl/",
    "https://www.alvi.cl/ofertas",
]

SKIP = ("google", "facebook", "segment", "datadog", "newrelic", "hotjar",
        "clarity", "doubleclick", "gstatic", "onetrust", "cookiebot", "/px/")

PRICE = re.compile(r'"(listPrice|sellingPrice|price|precio|offer-price|offerPrice)"\s*:')
NAMEK = re.compile(r'"(name|nombre|ProductName|productName|nameComplete)"\s*:')

def score(t):
    if not t or len(t) < 80:
        return 0
    return min(len(PRICE.findall(t)), len(NAMEK.findall(t)))

cands = []
results = {}

with sync_playwright() as p:
    br = p.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled", "--no-sandbox"])
    ctx = br.new_context(
        viewport={"width": 1366, "height": 900}, locale="es-CL",
        timezone_id="America/Santiago",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    page = ctx.new_page()

    def on_resp(resp):
        try:
            url = resp.url
            if any(s in url for s in SKIP):
                return
            ct = (resp.headers or {}).get("content-type", "").lower()
            if "json" not in ct:
                return
            body = resp.text()
            sc = score(body)
            if sc < 1:
                return
            req = resp.request
            cands.append({
                "url": url, "status": resp.status, "method": req.method,
                "score": sc, "bytes": len(body),
                "req_headers": dict(req.headers or {}),
                "post_data": req.post_data,
                "body": body,
            })
        except Exception:
            pass

    page.on("response", on_resp)

    for u in URLS:
        print("GOTO", u)
        try:
            resp = page.goto(u, timeout=60000, wait_until="domcontentloaded")
            print("  status", resp.status if resp else None)
        except Exception as e:
            print("  warn", e)
        page.wait_for_timeout(6000)
        for _ in range(8):
            try:
                page.evaluate("window.scrollBy(0,1400)")
            except Exception:
                pass
            page.wait_for_timeout(1200)
        # capture __NEXT_DATA__
        html = page.content()
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        key = "home" if u.endswith("/") else "ofertas"
        results[key] = {"url": u, "has_next": bool(m), "html_len": len(html)}
        if m:
            with open(os.path.join(OUT, f"alvi_{key}_next.json"), "w", encoding="utf-8") as f:
                f.write(m.group(1))
            print(f"  __NEXT_DATA__ saved ({len(m.group(1))} bytes)")
        else:
            with open(os.path.join(OUT, f"alvi_{key}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            print("  no __NEXT_DATA__, html saved")
    br.close()

cands.sort(key=lambda c: (c["score"], c["bytes"]), reverse=True)
print("\nCANDIDATES:", len(cands))
for c in cands[:12]:
    print(f"  {c['method']} {c['status']} score={c['score']} {c['bytes']}b {c['url'][:110]}")

with open(os.path.join(OUT, "alvi_best.json"), "w", encoding="utf-8") as f:
    json.dump({"found": bool(cands), "results": results,
               "best": cands[0] if cands else None,
               "all": [{k: c[k] for k in ("url","status","method","score","bytes","post_data")} for c in cands[:15]]},
              f, ensure_ascii=False, indent=2)
print("saved alvi_best.json")
