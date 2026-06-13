import json, os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
BASE = "https://bff-alvi-web.alvi.cl/products/by-category/"

# VTEX-style category tree ids seen in product 'categoriesIds' like /9/76/.
# We'll browse top-level category trees 1..40 plus try a few cluster ids.
# Endpoint uses fq filter. For category browse VTEX uses fq=C:/<id>/ or categoryId.
# We'll test multiple fq forms and keep what returns markdowns.

FORMS = [
    "fq=C:/{cid}/",
    "fq=productClusterIds:{cid}",
]

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
    page.goto("https://www.alvi.cl/", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(7000)

    def call(qs):
        # use in-page fetch so Akamai cookies + session headers apply
        js = """
        async (url) => {
            const r = await fetch(url, {headers:{'accept':'application/json, text/plain, */*'}});
            const t = await r.text();
            return {status:r.status, body:t};
        }
        """
        return page.evaluate(js, qs)

    # First, discover the session/anonymous headers the app uses by reading sessionStorage/localStorage
    store = page.evaluate("() => ({ls:Object.keys(localStorage), ss:Object.keys(sessionStorage)})")
    print("storage keys:", store)

    markdowns = []
    scanned = {}
    # Browse top-level category trees /N/
    for cid in range(1, 41):
        url = f"{BASE}?from=0&to=49&fq=C:/{cid}/"
        try:
            res = call(url)
        except Exception as e:
            print("err", cid, e); continue
        if res["status"] != 200:
            scanned[cid] = res["status"]
            continue
        try:
            body = json.loads(res["body"])
        except Exception:
            scanned[cid] = "badjson"; continue
        prods = body.get("products", [])
        scanned[cid] = len(prods)
        md = 0
        for pr in prods:
            s = (pr.get("sellers") or [{}])[0]
            price = s.get("price") or 0
            lp = s.get("listPrice") or 0
            if price and lp and price < lp:
                md += 1
                if len(markdowns) < 60:
                    markdowns.append({
                        "name": pr.get("name"), "price": price, "listPrice": lp,
                        "pwd": s.get("priceWithoutDiscount"),
                        "detailUrl": pr.get("detailUrl"), "cat": pr.get("categories"),
                        "cid": cid,
                    })
        print(f"cat /{cid}/ -> {len(prods)} prods, {md} markdowns")
    print("\nSCANNED:", scanned)
    print("TOTAL MARKDOWN SAMPLES:", len(markdowns))
    with open(os.path.join(OUT, "alvi_markdowns.json"), "w", encoding="utf-8") as f:
        json.dump({"markdowns": markdowns, "scanned": scanned, "storage": store},
                  f, ensure_ascii=False, indent=2)
    br.close()
