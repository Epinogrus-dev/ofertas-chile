"""
Scraper de Hites.com -> Salesforce Commerce Cloud (Demandware / SFRA).
No es VTEX. El grid se obtiene por Search-UpdateGrid (fragmento HTML, no JSON),
ordenado por descuento (srule=discount-off). Se parsea cada tile.

Oferta real = tiene precio "sales" Y precio "list strike-through" (sin
'only-normal-price') con sales < list.
"""
import html as _html
import logging
import re
import time
import requests

from ..model import Oferta, num

log = logging.getLogger("hites")

ENDPOINT = "https://www.hites.com/on/demandware.store/Sites-HITES-Site/default/Search-UpdateGrid"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,*/*;q=0.8", "Accept-Language": "es-CL,es;q=0.9",
}
CATEGORIAS = ["tecnologia", "electrohogar", "celulares", "dormitorio", "muebles",
              "hogar", "mujer", "hombre", "belleza", "zapatos", "deportes"]

_RE_NAME = re.compile(r'product-name--bundle"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_RE_BRAND = re.compile(r'product-brand">([^<]+)<')
_RE_SALES = re.compile(r'price-item sales\s*"[^>]*>.*?<span class="value" content="(\d+)"', re.S)
_RE_LIST = re.compile(r'price-item list strike-through\s*"[^>]*>.*?<span class="value" content="(\d+)"', re.S)
_RE_IMG = re.compile(r'<img[^>]+src="(https://www\.hites\.com/dw/image/[^"]+)"')
_RE_TAGS = re.compile(r"<[^>]+>")


def _parse_tile(t):
    mn = _RE_NAME.search(t)
    ms = _RE_SALES.search(t)
    ml = _RE_LIST.search(t)
    if not (mn and ms and ml):
        return None
    oferta = num(ms.group(1))
    normal = num(ml.group(1))
    if oferta <= 0 or normal <= oferta:
        return None
    href = mn.group(1)
    nombre = _html.unescape(_RE_TAGS.sub("", mn.group(2))).strip()
    if len(nombre) < 3:
        return None
    mb = _RE_BRAND.search(t)
    mi = _RE_IMG.search(t)
    pid = re.search(r"-(\d+)\.html", href)
    return Oferta(
        tienda="Hites",
        nombre_producto=nombre,
        precio_original=normal,
        precio_oferta=oferta,
        marca=(mb.group(1).strip() if mb else ""),
        categoria="",
        sku=pid.group(1) if pid else href,
        url_producto="https://www.hites.com" + href if href.startswith("/") else href,
        imagen_url=mi.group(1) if mi else "",
    )


def fetch_offers(max_paginas: int = 10, page_size: int = 24, pausa: float = 0.3) -> list[Oferta]:
    ofertas, vistos = [], set()
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    for cat in CATEGORIAS:
        recolectadas = 0
        for page in range(max_paginas):
            params = {"cgid": cat, "srule": "discount-off", "start": page * page_size, "sz": page_size}
            try:
                r = sesion.get(ENDPOINT, params=params, timeout=40)
                if r.status_code != 200:
                    break
                tiles = r.text.split("grid-tile")
            except Exception as e:  # noqa: BLE001
                log.warning("Hites %s p%d error: %s", cat, page, e)
                break
            if len(tiles) <= 1:
                break
            nuevos = 0
            for t in tiles[1:]:
                of = _parse_tile(t)
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
        log.info("Hites %-14s %d ofertas", cat, recolectadas)
    return ofertas
