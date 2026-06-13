"""
Scraper de Super10.cl (grupo SMU, supermercado de descuento).
Sus ofertas son un catalogo semanal curado en Contentful, embebido en la pagina
/ofertas dentro de <script id="__NEXT_DATA__"> -> pageProps.page.productos.offers.
Cada oferta: {name, description(tamano), price(normal), offer-price(oferta), category, ean}.
Las imagenes vienen aparte en pageProps.page.imagenesProductos (mapeadas por ean).
"""
import json
import logging
import re
import requests

from ..model import Oferta, num

log = logging.getLogger("super10")

URL = "https://www.super10.cl/ofertas"
HEADERS = {
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "es-CL,es;q=0.9",
}
_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def _mapa_imagenes(page: dict) -> dict:
    mapa = {}
    for it in page.get("imagenesProductos", []) or []:
        f = it.get("fields") or {}
        ean = str(f.get("ean") or "")
        url = (((f.get("imagen") or {}).get("fields") or {}).get("file") or {}).get("url") or ""
        if ean and url:
            mapa[ean] = "https:" + url if url.startswith("//") else url
    return mapa


def fetch_offers() -> list[Oferta]:
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        m = _NEXT.search(r.text)
        if not m:
            log.warning("Super10: sin __NEXT_DATA__ (HTTP %s)", r.status_code)
            return []
        page = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("page", {})
    except Exception as e:  # noqa: BLE001
        log.warning("Super10 error: %s", e)
        return []

    offers = (page.get("productos") or {}).get("offers", []) or []
    imgs = _mapa_imagenes(page)
    ofertas = []
    for o in offers:
        nombre = (o.get("name") or "").strip()
        desc = (o.get("description") or "").strip()
        if desc:
            nombre = f"{nombre} {desc}"
        precio = num(o.get("offer-price"))
        normal = num(o.get("price"))
        if precio <= 0 or normal <= 0:
            continue
        ean = str(o.get("ean") or "")
        ofertas.append(Oferta(
            tienda="Super10",
            nombre_producto=nombre,
            precio_original=normal,
            precio_oferta=precio,
            categoria=(o.get("category") or "").title(),
            sku=ean,
            url_producto=URL,
            imagen_url=imgs.get(ean, ""),
        ))
    log.info("Super10: %d ofertas", len(ofertas))
    return ofertas
