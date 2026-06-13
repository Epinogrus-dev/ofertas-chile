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

# 1) Confirm GetCategoryTree works direct
cat_payload = [{
    "operationName": "GetCategoryTree",
    "variables": {"getCategoryInput": {"clientId": "SUPER_BODEGA", "storeReference": "580"}},
    "query": "fragment CategoryFields on CategoryModel {\n  active\n  boost\n  hasChildren\n  categoryNamesPath\n  isAvailableInHome\n  level\n  name\n  path\n  reference\n  slug\n  photoUrl\n  imageUrl\n  shortName\n  isFeatured\n  isAssociatedToCatalog\n  __typename\n}\n\nfragment CategoriesRecursive on CategoryModel {\n  subCategories {\n    ...CategoryFields\n    subCategories {\n      ...CategoryFields\n      subCategories {\n        ...CategoryFields\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CategoryModel on CategoryModel {\n  ...CategoryFields\n  ...CategoriesRecursive\n  __typename\n}\n\nquery GetCategoryTree($getCategoryInput: GetCategoryInput!) {\n  getCategory(getCategoryInput: $getCategoryInput) {\n    ...CategoryModel\n    __typename\n  }\n}"
}]
st, body = post(cat_payload)
print("GetCategoryTree DIRECT:", st, "bytes", len(body))
print(body[:300])
open("captures/_direct_cattree.json", "w", encoding="utf-8").write(body)
