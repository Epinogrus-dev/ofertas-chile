# -*- coding: utf-8 -*-
import requests, re, html as ihtml
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
s = requests.Session(); s.headers.update({"User-Agent":UA,"Referer":"https://www.hites.com/","Accept-Language":"es-CL,es;q=0.9"})

def cgid_from_slug(slug):
    r = s.get("https://www.hites.com"+slug, timeout=60)
    # cgid appears in Search-ShowAjax?cgid=XXX and data-catid="XXX"
    m = re.search(r'data-catid="([a-zA-Z0-9_]+)"', r.text)
    if not m:
        m = re.search(r'Search-(?:ShowAjax|UpdateGrid)\?cgid=([a-zA-Z0-9_]+)', r.text)
    return (m.group(1) if m else None), r.status_code, len(r.content)

for slug in ["/tecnologia/", "/electro-hogar/", "/dormitorio/", "/mujer/", "/zapatillas/"]:
    cgid, st, ln = cgid_from_slug(slug)
    print(f"{slug:20s} status={st} len={ln} cgid={cgid}")

# Now test UpdateGrid with discount-off on tecnologia cgid
cgid, _, _ = cgid_from_slug("/tecnologia/")
if cgid:
    u = f"https://www.hites.com/on/demandware.store/Sites-HITES-Site/default/Search-UpdateGrid?cgid={cgid}&srule=discount-off&start=0&sz=24"
    r = s.get(u, timeout=60)
    sales = len(re.findall(r'price-item sales', r.text))
    lst = len(re.findall(r'price-item list strike-through', r.text))
    disc = len(re.findall(r'discount-badge pruebaaa', r.text))
    # parse first offer
    m = re.search(r'discount-badge pruebaaa discount-price ">(\d+)%.*?content="(\d+)".*?price-item list strike-through[^>]*>\s*<span class="value" content="(\d+)"', r.text, re.S)
    print(f"\ntecnologia cgid={cgid} status={r.status_code} len={len(r.content)} sales={sales} list={lst} discountBadges={disc}")
    if m:
        print("first offer disc%=", m.group(1), "sale=", m.group(2), "list=", m.group(3))
