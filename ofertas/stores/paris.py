"""
Scraper de Paris.cl (Cencosud) -> Constructor.io (catalogo/busqueda) directo.
No es VTEX. El listado se sirve por https://ac.cnstrc.com/browse/group_id/{group}
con una api-key publica. Soporta sort_by=best-discount -> las mayores rebajas primero.
Oferta real = data.discountPercentage > 0 (precio_oferta = data.displayedPrice;
precio_normal se deriva de displayedPrice / (1 - desc/100)).
"""
import logging
import time
import requests

from ..model import Oferta, num

log = logging.getLogger("paris")

API = "https://ac.cnstrc.com/browse/group_id/{group}"
KEY = "key_8pjkPsSkEsJHKgxR"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Origin": "https://www.paris.cl", "Referer": "https://www.paris.cl/",
}
# group_id de los principales departamentos.
GRUPOS = [
    "tecnologia", "electroLineaBlanca", "tvAudio", "tecCelulares",
    "muebles", "deco", "dormitorio", "belleza", "deportes", "juguetes",
    "mujModa", "homModa", "mujZapatos",
]


def _parse(d_item, grupo):
    data = d_item.get("data") or {}
    desc = data.get("discountPercentage") or 0
    oferta = num(data.get("displayedPrice"))
    if not desc or desc <= 0 or oferta <= 0:
        return None
    normal = round(oferta / (1 - desc / 100))
    if normal <= oferta:
        return None
    img = data.get("image_url") or ""
    if not img:
        imgs = data.get("image_urls") or []
        img = (imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else "") if imgs else ""
    return Oferta(
        tienda="Paris",
        nombre_producto=d_item.get("value") or "",
        precio_original=normal,
        precio_oferta=oferta,
        marca=data.get("brand") or "",
        categoria=grupo,
        sku=str(data.get("id") or ""),
        url_producto=data.get("url") or "",
        imagen_url=img,
    )


def fetch_offers(max_paginas: int = 12, page_size: int = 50, pausa: float = 0.25) -> list[Oferta]:
    ofertas, vistos = [], set()
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    for grupo in GRUPOS:
        recolectadas = 0
        for page in range(1, max_paginas + 1):
            params = {
                "key": KEY, "c": "ciojs-2.1429.16",
                "num_results_per_page": page_size, "page": page,
                "sort_by": "best-discount", "sort_order": "descending",
            }
            try:
                r = sesion.get(API.format(group=grupo), params=params, timeout=30)
                if r.status_code != 200:
                    break
                results = (r.json().get("response") or {}).get("results") or []
            except Exception as e:  # noqa: BLE001
                log.warning("Paris %s p%d error: %s", grupo, page, e)
                break
            if not results:
                break
            nuevos = 0
            for it in results:
                of = _parse(it, grupo)
                if of is None:
                    continue
                if of.sku in vistos:
                    continue
                vistos.add(of.sku)
                ofertas.append(of)
                recolectadas += 1
                nuevos += 1
            if nuevos == 0:  # ordenado por descuento: si una pagina no aporta, cortar
                break
            time.sleep(pausa)
        log.info("Paris %-20s %d ofertas", grupo, recolectadas)
    return ofertas
