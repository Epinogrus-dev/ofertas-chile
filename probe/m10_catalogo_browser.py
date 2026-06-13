import json, os, re
from playwright.sync_api import sync_playwright
OUT = os.path.join(os.path.dirname(__file__), "captures")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
B = "oENkwSusl0wmJGdkJJvw7"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(user_agent=UA, locale="es-CL")
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    page = ctx.new_page()
    # fetch the catalogo data json via the browser (passes Akamai)
    js = """async (url) => { const r = await fetch(url, {credentials:'include'}); return {status:r.status, text: await r.text()}; }"""
    page.goto("https://www.mayorista10.cl/catalogo", wait_until="domcontentloaded", timeout=40000)
    page.wait_for_timeout(3500)
    html = page.content()
    # find catalog images / pdf links and any visible price-like text
    imgs = re.findall(r'(https://images\.ctfassets\.net/[^\s"\')]+)', html)
    pdfs = re.findall(r'(https?://[^\s"\')]+\.pdf)', html, re.I)
    prices_visible = re.findall(r'\$\s?\d[\d.\s]*', page.inner_text("body"))
    print("catalogo HTML len:", len(html))
    print("ctfassets images (first 5):", imgs[:5])
    print("PDF links:", pdfs[:5])
    print("visible $-prices on /catalogo:", prices_visible[:15])

    # also fetch catalogo.json through the browser context
    res = page.evaluate(js, f"https://www.mayorista10.cl/_next/data/{B}/catalogo.json")
    print("\ncatalogo.json status:", res["status"], "len:", len(res["text"]))
    nonempty = re.findall(r'"(?:price|offer-price|precio|sellingPrice)"\s*:\s*"?(\d[\d.,]*)', res["text"])
    print("non-empty structured prices in catalogo.json:", nonempty[:10])
    try:
        d = json.loads(res["text"])
        pg = d.get("pageProps",{}).get("page",{})
        print("catalogo page keys:", list(pg.keys()) if isinstance(pg,dict) else type(pg))
    except Exception as e:
        print("json parse:", e)
    browser.close()
