import json, urllib.request, urllib.error

URL = "https://nextgentheadless.instaleap.io/api/v3"
H = {
    "content-type": "application/json",
    "dpl-api-key": "bc648ae6-3b18-4e35-8c3a-11e61074faa8",
    "client-name": "e-commerce Moira Engine CENTRAL_MAYORISTA",
    "client-version": "0.19.46",
    "apollographql-client-name": "e-commerce Moira Engine client CENTRAL_MAYORISTA",
    "apollographql-client-version": "0.19.46",
    "origin": "https://www.centralmayorista.cl",
    "referer": "https://www.centralmayorista.cl/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}
CLIENT = "CENTRAL_MAYORISTA"
STORE = "159"


def post(p):
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers=H, method="POST")
    try:
        return urllib.request.urlopen(r, timeout=40).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "HTTP%d %s" % (e.code, e.read().decode("utf-8", "replace")[:400])


PFIELDS = ("sku name slug price isAvailable brand photosUrl "
           "promotion{ type description isActive conditions{ price priceBeforeTaxes quantity } } "
           "categories{ name }")


def search(term, page=1, size=40):
    q = ("query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ "
         "products{ " + PFIELDS + " } pagination{ page pages total{ value } } } }")
    inp = {"clientId": CLIENT, "pageSize": size, "currentPage": page,
           "storeReference": STORE, "search": [{"query": term}]}
    body = post([{"operationName": "SearchProducts", "variables": {"i": inp}, "query": q}])
    return body


# first quick connectivity test with one term
raw = search("aceite")
print("RAW HEAD:", raw[:600])
print("=" * 60)

terms = ["leche", "aceite", "cafe", "arroz", "detergente", "yogurt", "cerveza",
         "shampoo", "galletas", "queso", "atun", "jugo", "azucar", "fideos", "papel"]
special = []
seen = set()
errs = 0
for t in terms:
    try:
        body = search(t)
        data = json.loads(body)[0]["data"]["searchProducts"]
    except Exception as e:
        errs += 1
        print("err", t, str(e)[:120], "| body:", body[:160])
        continue
    for p in data["products"]:
        if p["sku"] in seen:
            continue
        seen.add(p["sku"])
        promo = p.get("promotion") or {}
        if not (promo.get("isActive") and promo.get("conditions")):
            continue
        cond = promo["conditions"][0]
        cprice = cond.get("price")
        base = p.get("price")
        ptype = promo.get("type")
        if ptype == "specialPrice" and cprice and base and cprice < base:
            special.append({
                "name": p["name"], "list_price": base, "offer_price": cprice,
                "discount_pct": round((1 - cprice / base) * 100),
                "url": "https://www.centralmayorista.cl/p/%s" % p["slug"],
                "image": (p.get("photosUrl") or [None])[0],
                "category": (p.get("categories") or [{}])[0].get("name"),
            })

print("=== specialPrice OFFERS:", len(special), "errs:", errs)
for o in special[:12]:
    print(json.dumps(o, ensure_ascii=False))
json.dump(special, open("captures/cm_offers_special.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
