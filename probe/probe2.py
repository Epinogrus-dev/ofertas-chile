import json, urllib.request

URL = "https://nextgentheadless.instaleap.io/api/v3"
HEADERS = {
    "content-type": "application/json",
    "dpl-api-key": "aa401ae6-dee5-4435-a250-85b2122930d8",
    "client-name": "e-commerce Moira Engine SUPER_BODEGA",
    "client-version": "0.19.46",
    "accept": "*/*",
    "origin": "https://www.acuenta.cl",
    "referer": "https://www.acuenta.cl/",
    "user-agent": "Mozilla/5.0",
}

def post(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers=HEADERS, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=40)
        return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")
    except Exception as e:
        return str(e)

vars_cat = {"i": {"clientId":"SUPER_BODEGA","storeReference":"580","categoryReference":"02","currentPage":1,"pageSize":20}}

# Try near-miss field names on ProductsByCategoryModel to trigger 'Did you mean'
for fld in ["product","products","item","items","result","results","data","total","totalProducts","pagination","page","aggregations","facets","categoryName","name"]:
    q = f"query GetProductsByCategory($i: GetProductsByCategoryInput!){{ getProductsByCategory(getProductsByCategoryInput:$i){{ {fld} }} }}"
    body = post([{"operationName":"GetProductsByCategory","variables":vars_cat,"query":q}])
    msg = ""
    try:
        msg = json.loads(body)[0]["errors"][0]["message"]
    except Exception:
        msg = body[:120]
    print(f"{fld:16} -> {msg[:150]}")
