"""
Scraper de Lider.cl (Walmart Chile) -> GraphQL directo (sin navegador).
Host real: super.lider.cl. Plataforma Walmart Glass / Orchestra GraphQL.

  POST https://super.lider.cl/orchestra/graphql  (operacion 'Search', query persistida de 44KB)
  headers x-o-* obligatorios + correlation id aleatorio por request.
  El SPA usa PerimeterX, pero la API GraphQL NO requiere cookie PerimeterX.

Las ofertas (badge ROLLBACK) traen priceInfo.listPrice > priceInfo.currentPrice.
Se navegan los departamentos (catId) y se filtran los markdowns reales.
"""
import copy
import json
import logging
import os
import time
import uuid
import requests

from ..model import Oferta, num

log = logging.getLogger("lider")

ENDPOINT = "https://super.lider.cl/orchestra/graphql"
_DIR = os.path.dirname(os.path.abspath(__file__))
_QUERY = open(os.path.join(_DIR, "_lider_query.gql"), encoding="utf-8").read().strip()
_BASE_VARS = json.load(open(os.path.join(_DIR, "_lider_vars.json"), encoding="utf-8"))

# Departamentos descubiertos (seoPath|catId).
DEPARTAMENTOS = [
    "despensa|46589040", "lacteos-fiambreria-y-huevos|45669105",
    "carnes-y-pescados|21856785", "frutas-y-verduras|22884697",
    "congelados|13010356", "bebidas-y-snacks|13901022",
    "desayunos-y-dulces|23483116", "chocolates|29989562",
    "limpieza-y-aseo|43390617", "panaderia-y-pasteleria|73535247",
    "belleza|70159643", "la-boti|60338008", "mascotas|07089592",
    "mundo-bebe-y-jugueteria|11780484", "colaciones|49858221",
]


def _headers() -> dict:
    cid = str(uuid.uuid4())
    return {
        "content-type": "application/json", "accept": "application/json",
        "x-o-platform": "rweb", "x-o-bu": "LIDER-CL", "x-o-mart": "B2C",
        "x-o-segment": "oaoh", "x-o-vertical": "OD",
        "x-apollo-operation-name": "Search", "x-o-ccm": "server", "wm_mp": "true",
        "accept-language": "es-CL",
        "wm_qos.correlation_id": cid, "x-o-correlation-id": cid,
        "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        "origin": "https://super.lider.cl", "referer": "https://super.lider.cl/",
    }


def _vars(cat_id: str, seo_path: str, page: int) -> dict:
    v = copy.deepcopy(_BASE_VARS)
    v.update({"query": "", "catId": cat_id, "seoPath": seo_path, "page": page,
              "ps": 40, "limit": 40, "sort": "best_match"})
    return v


def _parse(p: dict) -> Oferta | None:
    pi = p.get("priceInfo") or {}
    cur = (pi.get("currentPrice") or {}).get("price")
    lst = (pi.get("listPrice") or {}).get("price") or (pi.get("wasPrice") or {}).get("price")
    precio = num(cur)
    lista = num(lst)
    if precio <= 0 or lista <= 0 or lista <= precio:
        return None
    canon = p.get("canonicalUrl") or ""
    img = (p.get("imageInfo") or {}).get("thumbnailUrl") or ""
    cat_path = (p.get("category") or {}).get("path") or []
    unit = (pi.get("unitPrice") or {}).get("priceString") or ""
    return Oferta(
        tienda="Lider",
        nombre_producto=p.get("name") or "",
        precio_original=lista,
        precio_oferta=precio,
        marca=p.get("brand") or "",
        categoria=cat_path[0].get("name") if cat_path else "",
        precio_por_unidad=num(unit),
        unidad=unit.split("x")[-1].strip() if "x" in unit else "",
        sku=str(p.get("id") or p.get("usItemId") or canon.rsplit("/", 1)[-1]),
        url_producto=f"https://super.lider.cl{canon}" if canon else "",
        imagen_url=img,
    )


def fetch_offers(max_paginas: int = 15, pausa: float = 0.2) -> list[Oferta]:
    ofertas: list[Oferta] = []
    sesion = requests.Session()

    for dep in DEPARTAMENTOS:
        seo_path, cat_id = dep.split("|")
        recolectadas = 0
        for page in range(1, max_paginas + 1):
            try:
                r = sesion.post(ENDPOINT, headers=_headers(),
                                json={"query": _QUERY, "variables": _vars(cat_id, seo_path, page)},
                                timeout=40)
                if r.status_code != 200:
                    log.warning("Lider %s p%d HTTP %s", seo_path, page, r.status_code)
                    break
                sr = (r.json().get("data") or {}).get("search", {}).get("searchResult", {})
                stacks = sr.get("itemStacks") or []
                items = (stacks[0].get("itemsV2") if stacks else []) or []
                max_page = (sr.get("paginationV2") or {}).get("maxPage") or max_paginas
            except Exception as e:  # noqa: BLE001
                log.warning("Lider %s p%d error: %s", seo_path, page, e)
                break
            if not items:
                break
            for p in items:
                of = _parse(p)
                if of is not None:
                    ofertas.append(of)
                    recolectadas += 1
            if page >= max_page:
                break
            time.sleep(pausa)
        log.info("Lider %-32s %d ofertas", seo_path, recolectadas)

    return ofertas
