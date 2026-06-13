import json, urllib.request

URL = "https://nextgentheadless.instaleap.io/api/v3"
H = {"content-type":"application/json","dpl-api-key":"aa401ae6-dee5-4435-a250-85b2122930d8","client-name":"e-commerce Moira Engine SUPER_BODEGA","client-version":"0.19.46","origin":"https://www.acuenta.cl","referer":"https://www.acuenta.cl/","user-agent":"Mozilla/5.0"}

def post(p):
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers=H, method="POST")
    try: return urllib.request.urlopen(r, timeout=40).read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.read().decode("utf-8","replace")

PRODUCT_FIELDS = "sku name slug price photosUrl isAvailable stock subUnit unit brand maxQty clickMultiplier formats nutritionalDetails type"

q = ("query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ "
     "products{ " + PRODUCT_FIELDS + " promotion{ type description conditions{ type value priceBeforeTaxes price } isActive } categories{ name reference slug } } "
     "pagination{ page pages total{ value relation } } } }")

inp = {"clientId":"SUPER_BODEGA","pageSize":10,"currentPage":1,"storeReference":"580","search":[{"query":"leche"}]}
body = post([{"operationName":"SearchProducts","variables":{"i":inp},"query":q}])
open("captures/_final_search.json","w",encoding="utf-8").write(body)
print("len", len(body))
print(body[:1500])
