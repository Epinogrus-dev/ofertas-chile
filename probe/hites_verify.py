# -*- coding: utf-8 -*-
import requests, re, json, html as ihtml

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
H = {"User-Agent": UA, "Accept": "text/html,*/*", "Referer": "https://www.hites.com/", "Accept-Language": "es-CL,es;q=0.9"}
s = requests.Session(); s.headers.update(H)

BASE = "https://www.hites.com/on/demandware.store/Sites-HITES-Site/default/Search-UpdateGrid"
url = BASE + "?cgid=zapatillas_training&srule=discount-off&start=0&sz=24"
r = s.get(url, timeout=60)
print("UpdateGrid STATUS:", r.status_code, "LEN:", len(r.content))
txt = r.text

# Each tile is a <div ... class="... product-tile ..." data-pid="...">. Split by product tile blocks.
# We'll find product detail links + brand + image from JSON-LD if present, else from tile.
# Simpler: parse tiles by data-pid then within tile grab sales/list values, name(link), brand, img.

# Build tile blocks: split on 'data-pid="'
tiles = re.split(r'data-pid="', txt)
offers = []
for t in tiles[1:]:
    pid = t[:t.find('"')]
    block = t[:20000]  # window per tile
    # sale price
    msale = re.search(r'price-item sales[^>]*>.*?<span class="value" content="(\d+)"', block, re.S)
    mlist = re.search(r'price-item list strike-through[^>]*>\s*<span class="value" content="(\d+)"', block, re.S)
    # 'only-normal-price' means no offer
    only_normal = 'only-normal-price' in block[:block.find('prices-section')+3000] if 'prices-section' in block else False
    if not msale or not mlist:
        continue
    sale = int(msale.group(1)); listp = int(mlist.group(1))
    if sale >= listp:
        continue
    # name + url from pdp link: <a class="link product-name--bundle" href="/...-NNN.html" ...>NAME</a>
    mlink = re.search(r'<a class="link product-name--bundle" href="(/[^"]+?\.html)"[^>]*>(.*?)</a>', block, re.S)
    if mlink:
        url_p = "https://www.hites.com" + ihtml.unescape(mlink.group(1))
        name = ihtml.unescape(re.sub(r'<[^>]+>', '', mlink.group(2)).strip())
    else:
        url_p = ""; name = ""
    # brand
    mbrand = re.search(r'class="[^"]*brand[^"]*"[^>]*>\s*([^<]+?)\s*<', block, re.S)
    brand = ihtml.unescape(mbrand.group(1).strip()) if mbrand else ""
    # image
    mimg = re.search(r'<img[^>]+src="(https://www\.hites\.com/dw/image/[^"]+)"', block, re.S)
    img = ihtml.unescape(mimg.group(1)) if mimg else ""
    disc = round((1 - sale/listp)*100)
    offers.append({"pid":pid,"name":name,"brand":brand,"sale":sale,"list":listp,"disc":disc,"url":url_p,"img":img})

print("Total tiles parsed with offer (sale<list):", len(offers))
for o in offers[:6]:
    print(json.dumps(o, ensure_ascii=False))

# Save first 3 clean offers
with open("captures/hites_offers_verified.json","w",encoding="utf-8") as f:
    json.dump(offers[:10], f, ensure_ascii=False, indent=2)
print("saved captures/hites_offers_verified.json")
