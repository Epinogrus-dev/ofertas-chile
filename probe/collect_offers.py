import json, urllib.request

URL = "https://nextgentheadless.instaleap.io/api/v3"
H = {"content-type":"application/json","dpl-api-key":"aa401ae6-dee5-4435-a250-85b2122930d8","client-name":"e-commerce Moira Engine SUPER_BODEGA","client-version":"0.19.46","origin":"https://www.acuenta.cl","referer":"https://www.acuenta.cl/","user-agent":"Mozilla/5.0"}

def post(p):
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers=H, method="POST")
    try: return urllib.request.urlopen(r, timeout=40).read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.read().decode("utf-8","replace")

PFIELDS = ("sku name slug price isAvailable brand photosUrl "
           "promotion{ type description isActive conditions{ price priceBeforeTaxes quantity } } "
           "categories{ name }")

def search(term, page=1, size=40):
    q = ("query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ "
         "products{ " + PFIELDS + " } pagination{ page pages total{ value } } } }")
    inp = {"clientId":"SUPER_BODEGA","pageSize":size,"currentPage":page,"storeReference":"580","search":[{"query":term}]}
    body = post([{"operationName":"SearchProducts","variables":{"i":inp},"query":q}])
    return json.loads(body)[0]["data"]["searchProducts"]

terms = ["leche","aceite","cafe","arroz","detergente","yogurt","cerveza","shampoo","galletas","queso","atun","jugo"]
special = []
nx = []
seen = set()
for t in terms:
    try:
        sp = search(t)
    except Exception as e:
        print("err", t, e); continue
    for p in sp["products"]:
        if p["sku"] in seen: continue
        seen.add(p["sku"])
        promo = p.get("promotion") or {}
        if not (promo.get("isActive") and promo.get("conditions")): continue
        cond = promo["conditions"][0]
        cprice = cond.get("price")
        base = p.get("price")
        ptype = promo.get("type")
        if ptype == "specialPrice" and cprice and base and cprice < base:
            special.append({
                "name": p["name"], "list_price": base, "offer_price": cprice,
                "discount_pct": round((1-cprice/base)*100),
                "url": f"https://www.acuenta.cl/p/{p['slug']}",
            })
        elif ptype == "nx$":
            nx.append({"name": p["name"], "base": base, "bundle_price": cprice, "qty": cond.get("quantity")})

print("=== specialPrice OFFERS:", len(special))
for o in special[:12]:
    print(json.dumps(o, ensure_ascii=False))
print("\n=== nx$ examples:", len(nx))
for o in nx[:5]:
    print(json.dumps(o, ensure_ascii=False))
json.dump(special, open("captures/_offers_special.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
