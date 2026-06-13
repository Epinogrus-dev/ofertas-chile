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
    "user-agent": "Mozilla/5.0",
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

def probe(opname, fieldpath_query, variables):
    st, body = post([{"operationName": opname, "variables": variables, "query": fieldpath_query}])
    return st, body

# 1) Find fields of ProductsByCategoryModel by asking a bogus field
q1 = "query GetProductsByCategory($i: GetProductsByCategoryInput!){ getProductsByCategory(getProductsByCategoryInput:$i){ __bogus__ } }"
vars_cat = {"i": {"clientId":"SUPER_BODEGA","storeReference":"580","categoryReference":"02","currentPage":1,"pageSize":20}}
print("--- ProductsByCategoryModel fields probe ---")
print(probe("GetProductsByCategory", q1, vars_cat)[1][:600])
print()

# 2) Find required input fields by sending empty input
q2 = "query GetProductsByCategory($i: GetProductsByCategoryInput!){ getProductsByCategory(getProductsByCategoryInput:$i){ __typename } }"
print("--- empty input probe ---")
print(probe("GetProductsByCategory", q2, {"i": {}})[1][:800])
print()

# 3) searchProducts input fields
q3 = "query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ __bogus__ } }"
print("--- searchProducts bogus field ---")
print(probe("SearchProducts", q3, {"i": {}})[1][:800])
