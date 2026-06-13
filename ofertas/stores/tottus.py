"""
Scraper de Tottus.cl (grupo Falabella, Next.js SSR) -> sin API JSON XHR.
Los productos vienen renderizados en el HTML dentro de <script id="__NEXT_DATA__">.
Metodo: GET de la categoria de Promociones (lista dedicada de ofertas) con
User-Agent de navegador, extraer __NEXT_DATA__ -> props.pageProps.results.

prices[] trae type="internetPrice" (oferta) y type="normalPrice" (precio normal,
crossed=true cuando hay rebaja). Oferta real = normalPrice > internetPrice.
"""
import json
import logging
import re
import time
import requests

from ..model import Oferta, num

log = logging.getLogger("tottus")

BASE = "https://www.tottus.cl/tottus-cl/lista"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9",
}
# Categoria maestra de promociones (lista dedicada de ofertas).
CATEGORIAS = ["CATG10196/Promociones"]

_NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def _precio(prices: list, tipo: str) -> float:
    for pr in prices or []:
        if pr.get("type") == tipo:
            arr = pr.get("price") or []
            return num(arr[0]) if arr else 0.0
    return 0.0


def _parse(p: dict) -> Oferta | None:
    prices = p.get("prices") or []
    oferta = _precio(prices, "internetPrice")
    normal = _precio(prices, "normalPrice")
    # A veces el precio rebajado viene como "cmrPrice" o "eventPrice"; tomar el menor valido.
    if oferta <= 0:
        oferta = _precio(prices, "cmrPrice") or _precio(prices, "eventPrice")
    if oferta <= 0 or normal <= 0:
        return None
    medios = p.get("mediaUrls") or []
    return Oferta(
        tienda="Tottus",
        nombre_producto=p.get("displayName") or "",
        precio_original=normal,
        precio_oferta=oferta,
        marca=p.get("brand") or "",
        categoria="Promociones",
        sku=str(p.get("skuId") or p.get("productId") or ""),
        url_producto=p.get("url") or "",
        imagen_url=medios[0] if medios else "",
    )


def fetch_offers(max_paginas: int = 80, pausa: float = 0.4) -> list[Oferta]:
    ofertas: list[Oferta] = []
    sesion = requests.Session()
    sesion.headers.update(HEADERS)

    for cat in CATEGORIAS:
        recolectadas = 0
        for page in range(1, max_paginas + 1):
            url = f"{BASE}/{cat}?page={page}"
            try:
                r = sesion.get(url, timeout=40)
                if r.status_code != 200:
                    log.warning("Tottus %s p%d HTTP %s", cat, page, r.status_code)
                    break
                m = _NEXT.search(r.text)
                if not m:
                    break
                res = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("results", [])
            except Exception as e:  # noqa: BLE001
                log.warning("Tottus %s p%d error: %s", cat, page, e)
                break
            if not res:
                break
            con_oferta = 0
            for p in res:
                of = _parse(p)
                if of is not None:
                    ofertas.append(of)
                    con_oferta += 1
            recolectadas += con_oferta
            time.sleep(pausa)
        log.info("Tottus %-26s %d ofertas", cat, recolectadas)

    return ofertas
