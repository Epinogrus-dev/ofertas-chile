"""
Scraper de La Polar -> su e-commerce vive en abc.cl (lapolar.cl redirige a abc.cl).
Plataforma Salesforce Commerce Cloud (Demandware). Grid via Search-UpdateGrid
(fragmento HTML). Categorias dedicadas de oferta: '{rubro}-en-oferta'.

Cada tile trae 3 precios: js-tlp-price (tarjeta La Polar, NO usar), js-internet-price
(oferta para todos) y js-normal-price (normal). Oferta real = internet < normal.
Los data-value son float "139990.0" -> parsear con float() directo (no con num()).
"""
import html as _html
import json
import logging
import re
import time
import requests

from ..model import Oferta

log = logging.getLogger("lapolar")

ENDPOINT = "https://www.abc.cl/on/demandware.store/Sites-Abc-Site/es_CL/Search-UpdateGrid"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,*/*;q=0.8", "Accept-Language": "es-CL,es;q=0.9",
}
CATEGORIAS = [
    # categorias dedicadas de oferta (las que devuelven productos)
    "tecnologia-en-oferta", "electrohogar-en-oferta", "hogar-en-oferta",
    "calzado-en-oferta", "moda-mujer-en-oferta", "mundo-infantil-en-oferta",
    "belleza-en-oferta",
    # departamentos generales: el parser conserva solo los markdown reales
    "tecnologia", "hogar", "dormitorio", "muebles",
]

_RE_GTM = re.compile(r'data-gtm-click="([^"]+)"')
_RE_INET = re.compile(r'js-internet-price\b.*?data-value="([\d.]+)"', re.S)
_RE_NORM = re.compile(r'js-normal-price\b.*?data-value="([\d.]+)"', re.S)
_RE_IMG = re.compile(r'<img[^>]+(?:src|data-src)="(https://www\.abc\.cl/dw/image/[^"]+)"')
_RE_HREF = re.compile(r'href="(/[^"]+?\.html)"')


def _f(s):
    try:
        return round(float(s))
    except (TypeError, ValueError):
        return 0


def _parse_tile(t):
    mi = _RE_INET.search(t)
    mn = _RE_NORM.search(t)
    if not (mi and mn):
        return None
    oferta = _f(mi.group(1))
    normal = _f(mn.group(1))
    if oferta <= 0 or normal <= oferta:
        return None
    nombre = marca = sku = ""
    mg = _RE_GTM.search(t)
    if mg:
        try:
            prod = json.loads(_html.unescape(mg.group(1)))["ecommerce"]["click"]["products"][0]
            nombre = prod.get("name") or ""
            marca = prod.get("brand") or ""
            sku = str(prod.get("id") or "")
        except Exception:  # noqa: BLE001
            pass
    if len(nombre) < 3:
        return None
    mh = _RE_HREF.search(t)
    mimg = _RE_IMG.search(t)
    return Oferta(
        tienda="La Polar",
        nombre_producto=nombre,
        precio_original=normal,
        precio_oferta=oferta,
        marca=marca,
        categoria="",
        sku=sku,
        url_producto=("https://www.abc.cl" + mh.group(1)) if mh else "",
        imagen_url=_html.unescape(mimg.group(1)) if mimg else "",
    )


def fetch_offers(max_paginas: int = 10, page_size: int = 24, pausa: float = 0.3) -> list[Oferta]:
    ofertas, vistos = [], set()
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    for cat in CATEGORIAS:
        recolectadas = 0
        for page in range(max_paginas):
            params = {"cgid": cat, "start": page * page_size, "sz": page_size}
            try:
                r = sesion.get(ENDPOINT, params=params, timeout=40)
                if r.status_code != 200:
                    break
                tiles = r.text.split("product-tile__item")
            except Exception as e:  # noqa: BLE001
                log.warning("La Polar %s p%d error: %s", cat, page, e)
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
        log.info("La Polar %-26s %d ofertas", cat, recolectadas)
    return ofertas
