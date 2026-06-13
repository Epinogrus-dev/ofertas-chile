import json, os
OUT = os.path.join(os.path.dirname(__file__), "captures")
data = json.load(open(os.path.join(OUT, "m10_ofertas_next.json"), encoding="utf-8"))
pp = data["props"]["pageProps"]
page = pp["page"]
offers = page["productos"]["offers"]
print("TOTAL offers:", len(offers))
for i, o in enumerate(offers):
    print(f"[{i}] name={o.get('name')!r} price={o.get('price')!r} offer-price={o.get('offer-price')!r} cat={o.get('category')!r}")
# Any offer with non-empty prices?
withprice = [o for o in offers if str(o.get("price")).strip() and str(o.get("offer-price")).strip()]
print("\nOffers with BOTH prices filled:", len(withprice))
# imagenesProductos sample
ip = page.get("imagenesProductos") or []
print("\nimagenesProductos count:", len(ip))
if ip:
    print(json.dumps(ip[0], ensure_ascii=False, indent=2)[:800])
# Look at navbar / categories for a real product catalog with prices
nav = pp.get("navbar")
print("\nnavbar type:", type(nav).__name__)
if isinstance(nav, dict):
    print("navbar keys:", list(nav.keys()))
