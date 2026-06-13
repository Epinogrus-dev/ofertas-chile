import requests, json, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
H = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": "https://www.hites.com/",
    "Accept-Language": "es-CL,es;q=0.9",
}
s = requests.Session()
s.headers.update(H)

def try_get(url, label):
    try:
        r = s.get(url, timeout=30)
        ct = r.headers.get("content-type","")
        print(f"\n=== {label} ===")
        print("URL:", url)
        print("STATUS:", r.status_code, "CT:", ct, "LEN:", len(r.content))
        if r.status_code == 200 and ("json" in ct or r.text.strip().startswith(("{","["))):
            try:
                data = r.json()
                if isinstance(data, list):
                    print("LIST len:", len(data))
                    if data:
                        print("keys[0]:", list(data[0].keys())[:20] if isinstance(data[0],dict) else type(data[0]))
                elif isinstance(data, dict):
                    print("DICT keys:", list(data.keys())[:20])
                return data
            except Exception as e:
                print("JSON parse fail:", e)
                print(r.text[:300])
        else:
            print("BODY[:300]:", r.text[:300])
    except Exception as e:
        print(f"\n=== {label} ERROR: {e}")
    return None

# 1. VTEX Intelligent Search - product_search
d = try_get("https://www.hites.com/api/io/_v/api/intelligent-search/product_search/trade-policy/1?query=zapatilla&count=3", "IS product_search query")

# 2. VTEX Intelligent Search via /api/io/_v/api/intelligent-search/product_search/ (no trade-policy)
try_get("https://www.hites.com/api/io/_v/api/intelligent-search/product_search/?query=zapatilla&count=3", "IS product_search no-tp")

# 3. VTEX catalog_system search
try_get("https://www.hites.com/api/catalog_system/pub/products/search?ft=zapatilla&_from=0&_to=2", "catalog_system ft search")

# 4. facets / category listing
try_get("https://www.hites.com/api/catalog_system/pub/category/tree/3", "category tree")

if d:
    with open("captures/hites_is_raw.json","w",encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("\nSaved IS raw to captures/hites_is_raw.json")
