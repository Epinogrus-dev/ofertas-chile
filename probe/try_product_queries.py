import json, urllib.request

URL = "https://nextgentheadless.instaleap.io/api/v3"
HEADERS = {
    "content-type": "application/json",
    "dpl-api-key": "aa401ae6-dee5-4435-a250-85b2122930d8",
    "apollographql-client-name": "e-commerce Moira Engine client SUPER_BODEGA",
    "apollographql-client-version": "0.19.46",
    "client-name": "e-commerce Moira Engine SUPER_BODEGA",
    "client-version": "0.19.46",
    "accept": "*/*",
    "origin": "https://www.acuenta.cl",
    "referer": "https://www.acuenta.cl/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

def post(payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers=HEADERS, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=40)
        return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)

# Instaleap standard: GetProductsByCategory(searchProductsByCategoryInput)
candidates = []

# Candidate A: GetProductsByCategory
candidates.append(("GetProductsByCategory", {
    "operationName": "GetProductsByCategory",
    "variables": {
        "getProductsByCategoryInput": {
            "clientId": "SUPER_BODEGA",
            "storeReference": "580",
            "categoryReference": "02",
            "currentPage": 1,
            "pageSize": 20
        }
    },
    "query": "query GetProductsByCategory($getProductsByCategoryInput: GetProductsByCategoryInput!) { getProductsByCategory(getProductsByCategoryInput: $getProductsByCategoryInput) { products { sku name slug price } } }"
}))

# Candidate B: searchProductsByCategory
candidates.append(("searchProductsByCategory", {
    "operationName": "SearchProductsByCategory",
    "variables": {
        "input": {
            "clientId": "SUPER_BODEGA",
            "storeReference": "580",
            "categoryReference": "02",
            "page": 1,
            "size": 20
        }
    },
    "query": "query SearchProductsByCategory($input: SearchProductsByCategoryInput!) { searchProductsByCategory(input: $input) { products { sku name price } } }"
}))

for name, payload in candidates:
    st, body = post([payload])
    print(f"=== {name}: {st} {len(body)}b")
    print(body[:400])
    print()
