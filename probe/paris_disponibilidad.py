"""
Probe de disponibilidad para Paris (Constructor.io).
Hace la MISMA request que ofertas/stores/paris.py y vuelca la estructura
completa de varios items para buscar campos de stock/disponibilidad.
"""
import json
import sys
import requests

API = "https://ac.cnstrc.com/browse/group_id/{group}"
KEY = "key_8pjkPsSkEsJHKgxR"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Origin": "https://www.paris.cl", "Referer": "https://www.paris.cl/",
}


def fetch(group, page=1, page_size=50):
    params = {
        "key": KEY, "c": "ciojs-2.1429.16",
        "num_results_per_page": page_size, "page": page,
        "sort_by": "best-discount", "sort_order": "descending",
    }
    r = requests.get(API.format(group=group), params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    grupo = sys.argv[1] if len(sys.argv) > 1 else "tecnologia"
    j = fetch(grupo)
    resp = j.get("response") or {}
    results = resp.get("results") or []
    print(f"=== grupo={grupo}  total_results={resp.get('total_num_results')}  en_pagina={len(results)} ===")

    # Volcar la estructura completa del primer item
    if results:
        print("\n--- KEYS top-level item ---")
        print(sorted(results[0].keys()))
        print("\n--- KEYS data ---")
        print(sorted((results[0].get('data') or {}).keys()))
        print("\n--- item[0] COMPLETO ---")
        print(json.dumps(results[0], ensure_ascii=False, indent=2)[:4000])

    # Buscar campos candidatos de disponibilidad en todos los items
    cand = ["availability", "in_stock", "is_active", "sellable", "stock", "status",
            "available_quantity", "active", "deleted", "visible", "is_available",
            "outOfStock", "inStock", "available", "stockLevel", "isMarketplace",
            "marketplace", "seller", "sellerName", "fulfillment", "variations"]
    print("\n--- campos candidatos presentes (data) ---")
    seen = {}
    for it in results:
        d = it.get("data") or {}
        for c in cand:
            if c in d:
                seen.setdefault(c, []).append(d.get(c))
    for c, vals in seen.items():
        uniq = []
        for v in vals:
            sv = json.dumps(v, ensure_ascii=False)[:60]
            if sv not in uniq:
                uniq.append(sv)
        print(f"  {c}: presente en {len(vals)}/{len(results)}  valores_unicos(<=8)={uniq[:8]}")

    # facets
    facets = resp.get("facets") or []
    print("\n--- facets disponibles ---")
    for f in facets:
        print(f"  {f.get('name')} ({f.get('type')})")


if __name__ == "__main__":
    main()
