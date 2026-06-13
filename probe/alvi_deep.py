import json, os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
BASE = "https://bff-alvi-web.alvi.cl/products/by-category/"

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

    def call(url):
        js = """async (url)=>{const r=await fetch(url,{headers:{'accept':'application/json, text/plain, */*'}});const t=await r.text();return {status:r.status,body:t};}"""
        return page.evaluate(js, url)

    report = {}

    # 1) Deep paginate each of the 14 top categories, count markdowns + sample priceSteps/promotion
    total_prods = 0
    total_md = 0
    md_samples = []
    promo_samples = []
    pricestep_samples = []
    for cid in range(1, 15):
        frm = 0
        seen = 0
        while frm < 600:
            url = f"{BASE}?from={frm}&to={frm+49}&fq=C:/{cid}/"
            try:
                res = call(url)
            except Exception:
                break
            if res["status"] != 200:
                break
            body = json.loads(res["body"])
            prods = body.get("products", [])
            if not prods:
                break
            for pr in prods:
                total_prods += 1
                s = (pr.get("sellers") or [{}])[0]
                price = s.get("price") or 0
                lp = s.get("listPrice") or 0
                promo = pr.get("promotion") or {}
                psteps = pr.get("priceSteps") or []
                if promo and len(promo_samples) < 5:
                    promo_samples.append({"name": pr.get("name"), "promotion": promo})
                if psteps and len(pricestep_samples) < 5:
                    pricestep_samples.append({"name": pr.get("name"), "price": price,
                                              "listPrice": lp, "priceSteps": psteps})
                if price and lp and price < lp:
                    total_md += 1
                    if len(md_samples) < 20:
                        md_samples.append({"name": pr.get("name"), "price": price,
                                           "listPrice": lp, "detailUrl": pr.get("detailUrl"),
                                           "cat": pr.get("categories")})
            seen += len(prods)
            if len(prods) < 50:
                break
            frm += 50
        print(f"cat /{cid}/ scanned {seen}")
    report["total_prods"] = total_prods
    report["total_markdowns"] = total_md
    report["md_samples"] = md_samples
    report["promo_samples"] = promo_samples
    report["pricestep_samples"] = pricestep_samples

    # 2) Try VTEX discount facet variations
    facet_tests = {
        "discount_true": f"{BASE}?from=0&to=23&fq=discountHighlight:true",
        "specification_offer": f"{BASE}?from=0&to=23&fq=B:true",
        "orderby_discount": f"{BASE}?from=0&to=23&fq=C:/1/&O=OrderByBestDiscountDESC",
        "ofertas_cluster_high": f"{BASE}?from=0&to=23&fq=productClusterIds:1",
    }
    facet_results = {}
    for k, url in facet_tests.items():
        try:
            res = call(url)
            if res["status"] == 200:
                b = json.loads(res["body"])
                ps = b.get("products", [])
                mds = sum(1 for pr in ps if (pr.get("sellers") or [{}])[0].get("price",0) < (pr.get("sellers") or [{}])[0].get("listPrice",0))
                facet_results[k] = {"status": 200, "n": len(ps), "markdowns": mds}
            else:
                facet_results[k] = {"status": res["status"]}
        except Exception as e:
            facet_results[k] = {"error": str(e)[:80]}
    report["facet_results"] = facet_results

    print("\n=== REPORT ===")
    print("total_prods:", total_prods, "total_markdowns:", total_md)
    print("promo_samples:", len(promo_samples), "pricestep_samples:", len(pricestep_samples))
    print("facets:", json.dumps(facet_results, ensure_ascii=False))
    with open(os.path.join(OUT, "alvi_deep.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    br.close()
