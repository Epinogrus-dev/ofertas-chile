import json, urllib.request

URL = "https://nextgentheadless.instaleap.io/api/v3"
H = {"content-type":"application/json","dpl-api-key":"aa401ae6-dee5-4435-a250-85b2122930d8","client-name":"e-commerce Moira Engine SUPER_BODEGA","client-version":"0.19.46","origin":"https://www.acuenta.cl","referer":"https://www.acuenta.cl/","user-agent":"Mozilla/5.0"}

def post(p):
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers=H, method="POST")
    try: return urllib.request.urlopen(r, timeout=40).read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.read().decode("utf-8","replace")

PFIELDS = ("sku name slug price isAvailable stock brand photosUrl "
           "promotion{ type description isActive conditions{ price priceBeforeTaxes quantity } } "
           "categories{ name reference slug }")

q = ("query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ "
     "products{ " + PFIELDS + " } pagination{ page pages total{ value relation } } } }")

# search broad term to surface offers
inp = {"clientId":"SUPER_BODEGA","pageSize":40,"currentPage":1,"storeReference":"580","search":[{"query":"leche"}]}
body = post([{"operationName":"SearchProducts","variables":{"i":inp},"query":q}])
open("captures/_verify_offers.json","w",encoding="utf-8").write(body)
data = json.loads(body)
sp = data[0]["data"]["searchProducts"]
prods = sp["products"]
print("total products:", len(prods), "pagination:", sp["pagination"])
offers = []
for p in prods:
    base = p.get("price")
    promo = p.get("promotion") or {}
    promo_price = None
    if promo.get("isActive") and promo.get("conditions"):
        # lowest condition price
        pc = [c.get("price") for c in promo["conditions"] if c.get("price")]
        if pc:
            promo_price = min(pc)
    # an offer = promo price < base price
    if promo_price and base and promo_price < base:
        disc = round((1 - promo_price/base)*100)
        offers.append({
            "name": p["name"], "list_price": base, "offer_price": promo_price,
            "discount_pct": disc, "slug": p.get("slug"), "promo_desc": promo.get("description"),
            "promo_type": promo.get("type"),
        })
print("\nOFFERS (promo < base):", len(offers))
for o in offers[:10]:
    print(json.dumps(o, ensure_ascii=False))
# also print a few raw products to see structure
print("\nSAMPLE RAW PRODUCT:")
print(json.dumps(prods[0], ensure_ascii=False)[:800])
