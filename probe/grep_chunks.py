import re, urllib.request, concurrent.futures

chunks = [l.strip() for l in open("captures/_chunks.txt") if l.strip()]
base = "https://www.acuenta.cl"
hits = {}

KW = ["operationName", "sellingPrice", "GetProducts", "SearchProducts",
      "getProductsByCategory", "ProductsByCategory", "GetSearchProducts",
      "search(", "products(", "shelf", "Shelf", "fragment Product",
      "ProductModel", "stockUnlimited", "promotion", "boostNew"]

def fetch(path):
    url = base + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        ops = set(re.findall(r'operationName:\s*"([^"]+)"', data))
        ops |= set(re.findall(r'"operationName":"([^"]+)"', data))
        found = {kw: data.count(kw) for kw in KW if kw in data}
        return path, ops, found, data
    except Exception as e:
        return path, set(), {"ERR": str(e)}, ""

allops = set()
product_chunk = None
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for path, ops, found, data in ex.map(fetch, chunks):
        if ops or found:
            allops |= ops
            line = f"{path}\n   ops={sorted(ops)}\n   found={found}"
            print(line)
            if "sellingPrice" in found or "GetProducts" in str(ops) or "SearchProducts" in str(ops):
                product_chunk = (path, data)

print("\nALL OPS:", sorted(allops))
if product_chunk:
    open("captures/_product_chunk.js", "w", encoding="utf-8").write(product_chunk[1])
    print("saved product chunk:", product_chunk[0])
