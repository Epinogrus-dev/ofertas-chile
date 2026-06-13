"""Captura el valor exacto de 'categories' que el sitio envia al BFF al abrir
una categoria, y extrae el menu de categorias del DOM."""
import sys, json, os
from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "captures")
HOST = "bff-unimarc-ecommerce.unimarc.cl/catalog/product/search"

def main():
    urls = sys.argv[1:] or ["https://www.unimarc.cl/category/lacteos-huevos-y-refrigerados"]
    payloads = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = browser.new_context(locale="es-CL", timezone_id="America/Santiago",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        page.on("request", lambda req: payloads.append(req.post_data) if HOST in req.url and req.method=="POST" else None)
        cat_links = set()
        for u in urls:
            print(f"[cat] -> {u}")
            try:
                page.goto(u, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print("warn", e)
            page.wait_for_timeout(5000)
            try:
                hrefs = page.eval_on_selector_all("a[href*='/category/']", "els => els.map(e=>e.getAttribute('href'))")
                for h in hrefs:
                    if h: cat_links.add(h)
            except Exception:
                pass
        browser.close()
    print("\nPAYLOADS enviados al BFF:")
    for pd in payloads:
        if pd: print("  ", pd)
    print("\nCATEGORY LINKS encontrados:")
    for c in sorted(cat_links):
        print("  ", c)
    with open(os.path.join(OUT,"unimarc_cats.json"),"w",encoding="utf-8") as f:
        json.dump({"payloads":payloads,"category_links":sorted(cat_links)},f,ensure_ascii=False,indent=2)

if __name__ == "__main__":
    main()
