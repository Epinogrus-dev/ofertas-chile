import json, urllib.request, re

URL = "https://nextgentheadless.instaleap.io/api/v3"
H = {"content-type":"application/json","dpl-api-key":"aa401ae6-dee5-4435-a250-85b2122930d8","client-name":"e-commerce Moira Engine SUPER_BODEGA","client-version":"0.19.46","origin":"https://www.acuenta.cl","referer":"https://www.acuenta.cl/","user-agent":"Mozilla/5.0"}

def post(p):
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers=H, method="POST")
    try: return urllib.request.urlopen(r, timeout=40).read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.read().decode("utf-8","replace")

def err(body):
    try: return json.loads(body)[0].get("errors",[{}])[0].get("message","")
    except: return body[:150]

# Discover CatalogProductModel fields by probing
inp = {"pageSize":5,"currentPage":1,"storeReference":"580","search":[{"query":"leche"}]}
# Start with minimal then add fields incrementally. First find valid product fields.
candidate_fields = ["sku","name","slug","price","listPrice","sellingPrice","currentPrice","priceWithDiscount",
    "promotion","promotions","photosUrl","photosUrls","photoUrl","imageUrl","images","stock","stockQuantity",
    "available","isAvailable","brand","categories","categoryReference","unit","format","description","ean",
    "discount","discounts","badges","tags","nutritionalInfo","maxQuantity","clickMultiplier","subUnit",
    "saleType","boost","searchScore","specialPrice","priceBeforeTaxes","barcodes"]
good=[]
for f in candidate_fields:
    q = "query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ products{ "+f+" } } }"
    body = post([{"operationName":"SearchProducts","variables":{"i":inp},"query":q}])
    m = err(body)
    if not m:
        good.append(f); status="OK"
    elif "must have a selection of subfields" in m:
        good.append(f+" {OBJECT}"); status="OBJ "+m[:60]
    elif "Did you mean" in m:
        status="SUGGEST: "+m[m.find("Did you mean"):m.find("Did you mean")+80]
    else:
        status="no"
    print(f"{f:20} -> {status}")

print("\nGOOD FIELDS:", good)
