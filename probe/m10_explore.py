import json, os
OUT = os.path.join(os.path.dirname(__file__), "captures")
data = json.load(open(os.path.join(OUT, "m10_ofertas_next.json"), encoding="utf-8"))
pp = data["props"]["pageProps"]
nav = pp["navbar"]
print("=== NAV ITEMS ===")
def walk(items, depth=0):
    for it in items:
        if isinstance(it, dict):
            label = it.get("label") or it.get("nombre") or it.get("titulo")
            href = it.get("href") or it.get("url") or it.get("link") or it.get("path")
            print("  "*depth + f"- {label!r} -> {href!r}  keys={list(it.keys())}")
            for k in ("navItems","subItems","children","items"):
                if isinstance(it.get(k), list):
                    walk(it[k], depth+1)
walk(nav.get("navItems") or [])

# Home page next data: any product/ecommerce hints?
print("\n=== HOME pageProps ===")
home = json.load(open(os.path.join(OUT, "m10_home_next.json"), encoding="utf-8"))
hpp = home["props"]["pageProps"]
for k in hpp:
    v = hpp[k]
    n = len(v) if isinstance(v,(list,dict)) else v
    print(f"  {k}: {type(v).__name__} ({n if isinstance(v,(list,dict)) else repr(v)[:60]})")
# buildId & routes
print("\nbuildId:", data.get("buildId"))
print("page route:", data.get("page"))
