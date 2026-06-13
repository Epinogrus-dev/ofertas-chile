"""
Scraper de Falabella.com/falabella-cl (grupo Falabella, Next.js "catalyst").
MISMO patron que Tottus: la coleccion /collection/ofertas es la lista dedicada de
rebajas; los productos vienen en <script id="__NEXT_DATA__"> -> props.pageProps.results.
prices[] trae type=internetPrice (oferta) y type=normalPrice (normal, crossed).

OJO: el HTML de Falabella es iso-8859-1 (no utf-8); hay que forzar encoding.
"""
import json
import logging
import re
import requests

from ..model import Oferta, num

log = logging.getLogger("falabella")

BASE = "https://www.falabella.com/falabella-cl/collection"
CATEGORIAS = ["ofertas"]
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9",
}
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def _precio(prices, tipo):
    for pr in prices or []:
        if pr.get("type") == tipo:
            arr = pr.get("price") or []
            return num(arr[0]) if arr else 0.0
    return 0.0


def _parse(p):
    prices = p.get("prices") or []
    oferta = _precio(prices, "internetPrice") or _precio(prices, "cmrPrice") or _precio(prices, "eventPrice")
    normal = _precio(prices, "normalPrice")
    if oferta <= 0 or normal <= 0:
        return None
    medios = p.get("mediaUrls") or []
    return Oferta(
        tienda="Falabella",
        nombre_producto=p.get("displayName") or "",
        precio_original=normal,
        precio_oferta=oferta,
        marca=p.get("brand") or "",
        categoria="",  # la coleccion de ofertas no trae nombre de categoria legible
        sku=str(p.get("skuId") or p.get("productId") or ""),
        url_producto=p.get("url") or "",
        imagen_url=medios[0] if medios else "",
    )


def fetch_offers(max_paginas: int = 30, pausa: float = 0.4) -> list[Oferta]:
    ofertas = []
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    for cat in CATEGORIAS:
        recolectadas = 0
        for page in range(1, max_paginas + 1):
            try:
                r = sesion.get(f"{BASE}/{cat}?page={page}", timeout=40)
                r.encoding = "iso-8859-1"  # CLAVE: acentos correctos
                if r.status_code != 200:
                    break
                m = _NEXT.search(r.text)
                if not m:
                    break
                res = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("results", [])
            except Exception as e:  # noqa: BLE001
                log.warning("Falabella %s p%d error: %s", cat, page, e)
                break
            if not res:
                break
            for p in res:
                of = _parse(p)
                if of is not None:
                    ofertas.append(of)
                    recolectadas += 1
            import time
            time.sleep(pausa)
        log.info("Falabella %-12s %d ofertas", cat, recolectadas)
    return ofertas
