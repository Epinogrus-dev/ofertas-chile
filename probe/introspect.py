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

# Introspection: list query fields
q = {"query": "query{__schema{queryType{fields{name args{name type{name kind ofType{name kind ofType{name kind}}}}}}}}"}
st, body = post(q)
print("introspect status", st, "len", len(body))
open("captures/_introspect.json", "w", encoding="utf-8").write(body)
try:
    data = json.loads(body)
    fields = data["data"]["__schema"]["queryType"]["fields"]
    names = [f["name"] for f in fields]
    print("QUERY FIELDS:")
    for f in fields:
        args = ", ".join(a["name"] for a in f.get("args", []))
        print(f"  {f['name']}({args})")
except Exception as e:
    print("parse err", e)
    print(body[:500])
