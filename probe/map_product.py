import json, urllib.request

URL = "https://nextgentheadless.instaleap.io/api/v3"
H = {"content-type":"application/json","dpl-api-key":"aa401ae6-dee5-4435-a250-85b2122930d8","client-name":"e-commerce Moira Engine SUPER_BODEGA","client-version":"0.19.46","origin":"https://www.acuenta.cl","referer":"https://www.acuenta.cl/","user-agent":"Mozilla/5.0"}

def post(p):
    r = urllib.request.Request(URL, data=json.dumps(p).encode(), headers=H, method="POST")
    try: return urllib.request.urlopen(r, timeout=40).read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.read().decode("utf-8","replace")

def err(body):
    try: return json.loads(body)[0]["errors"][0]["message"]
    except: return body[:120]

# 1) Required input fields for searchProducts (send empty, read missing required one-by-one)
inp = {}
for _ in range(15):
    q = "query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ products{ sku } } }"
    body = post([{"operationName":"SearchProducts","variables":{"i":inp},"query":q}])
    m = err(body)
    print("INPUT PROBE:", m[:160])
    import re
    mm = re.search(r'Field "(\w+)" of required type "([^"]+)" was not provided', m)
    if not mm:
        # maybe value type errors
        mm2 = re.search(r'Field "(\w+)" of required type "([^"]+)"', m)
        if mm2:
            name, typ = mm2.group(1), mm2.group(2)
        else:
            print("no more required missing OR success")
            print("BODY:", body[:300])
            break
    else:
        name, typ = mm.group(1), mm.group(2)
    # fill with a placeholder based on type
    base = typ.replace("!","")
    if base in ("Int","Float"): val = 1
    elif base in ("Boolean",): val = False
    elif base in ("ID","String"): val = "SUPER_BODEGA" if "client" in name.lower() else ("580" if "store" in name.lower() else "test")
    else: val = {}
    inp[name] = val
    print("  -> set", name, "=", val, "(type", typ, ")")

print("\nFINAL INPUT:", json.dumps(inp))
