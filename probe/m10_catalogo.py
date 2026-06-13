import json, os, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "captures")
B = "oENkwSusl0wmJGdkJJvw7"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def grab(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        return urllib.request.urlopen(req, timeout=20).read().decode("utf-8","replace")
    except Exception as e:
        return f"ERR {e}"

# catalogo + one marcapropia
for path in [f"https://www.mayorista10.cl/_next/data/{B}/catalogo.json",
             f"https://www.mayorista10.cl/_next/data/{B}/marcapropia/merkat.json?marca_propia=merkat"]:
    txt = grab(path)
    print("="*60)
    print(path[:90])
    if txt.startswith("ERR"):
        print(txt); continue
    try:
        d = json.loads(txt)
        pp = d.get("pageProps", {})
        print("pageProps keys:", list(pp.keys()))
        # search for any numeric price anywhere
        import re
        prices = re.findall(r'"(?:price|offer-price|precio|sellingPrice)"\s*:\s*"?(\d[\d.,]*)', txt)
        print("non-empty price values found:", prices[:10], "..." if len(prices)>10 else "")
        # productos block?
        pg = pp.get("page", {})
        if isinstance(pg, dict):
            print("page keys:", list(pg.keys()))
            prod = pg.get("productos")
            if isinstance(prod, dict):
                print("productos keys:", list(prod.keys()))
                offs = prod.get("offers") or prod.get("productos") or []
                print("items:", len(offs))
                if offs:
                    print("sample:", json.dumps(offs[0], ensure_ascii=False)[:400])
    except Exception as e:
        print("parse err", e, txt[:200])
