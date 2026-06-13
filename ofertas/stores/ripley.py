"""
Scraper de Ripley.cl (simple.ripley.cl) -> Next.js SSR (__NEXT_DATA__).
Productos en props.pageProps.findabilityProps.data.products[].
Oferta real = oldPrice presente y priceNumber < oldPrice (NO usar ripleyPrice,
que es el precio con Tarjeta Ripley).
"""
import json
import logging
import re
import time
import requests

from ..model import Oferta, num

log = logging.getLogger("ripley")

BASE = "https://simple.ripley.cl"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9",
}
CATEGORIAS = ["tecno", "electrohogar", "dormitorio", "muebles",
              "moda-mujer", "moda-hombre", "belleza"]

_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(s):
    return _SLUG.sub("-", (s or "").lower()).strip("-")


def _parse(p, cat):
    oldp = p.get("oldPrice")
    if not oldp:  # sin rebaja
        return None
    oferta = num(p.get("priceNumber") or p.get("price"))
    normal = num(oldp)
    if oferta <= 0 or normal <= oferta:
        return None
    name = p.get("name") or ""
    sku = str(p.get("sku") or "")
    imgs = p.get("images") or []
    img = p.get("primaryImage") or (imgs[0] if imgs else "")
    return Oferta(
        tienda="Ripley",
        nombre_producto=name,
        precio_original=normal,
        precio_oferta=oferta,
        marca=p.get("brand") or "",
        categoria=cat,
        sku=sku,
        url_producto=f"{BASE}/{_slug(name)}-{sku}P" if sku and name else "",
        imagen_url=img,
    )


def fetch_offers(max_paginas: int = 12, pausa: float = 0.3) -> list[Oferta]:
    ofertas, vistos = [], set()
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    for cat in CATEGORIAS:
        recolectadas = 0
        for page in range(1, max_paginas + 1):
            try:
                r = sesion.get(f"{BASE}/{cat}?page={page}", timeout=40)
                if r.status_code != 200:
                    break
                m = _NEXT.search(r.text)
                if not m:
                    break
                fp = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("findabilityProps", {})
                productos = (fp.get("data") or {}).get("products") or []
            except Exception as e:  # noqa: BLE001
                log.warning("Ripley %s p%d error: %s", cat, page, e)
                break
            if not productos:
                break
            nuevos = 0
            for p in productos:
                of = _parse(p, cat)
                if of is None:
                    continue
                if of.sku in vistos:
                    continue
                vistos.add(of.sku)
                ofertas.append(of)
                recolectadas += 1
                nuevos += 1
            if nuevos == 0:
                break
            time.sleep(pausa)
        log.info("Ripley %-14s %d ofertas", cat, recolectadas)
    return ofertas
