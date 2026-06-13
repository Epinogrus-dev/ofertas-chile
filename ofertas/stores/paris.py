"""
Scraper de Paris.cl (Cencosud) -> Constructor.io (catalogo/busqueda) directo.
No es VTEX. El listado se sirve por https://ac.cnstrc.com/browse/group_id/{group}
con una api-key publica. Soporta sort_by=best-discount -> las mayores rebajas primero.
Oferta real = data.discountPercentage > 0 (precio_oferta = data.displayedPrice;
precio_normal se deriva de displayedPrice / (1 - desc/100)).
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from ..model import Oferta, num

log = logging.getLogger("paris")

API = "https://ac.cnstrc.com/browse/group_id/{group}"
KEY = "key_8pjkPsSkEsJHKgxR"
# Stock real: el browse de Constructor.io indexa TODO el catalogo (incluye outlet,
# descontinuados y sin stock). El sitio resuelve disponibilidad con este endpoint:
# payload[].isServiceable + totalServiceableStockQty + shippingOptions. Si no es
# vendible/despachable (o el SKU ya no existe -> error 404), lo excluimos.
LEVEL = "https://be-paris-backend-cl-bff-browser.ccom.paris.cl/global/level-service/product"
LOCALIDAD = "13114"  # Santiago Centro; basta para saber si el producto es vendible.
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


_local = threading.local()


def _sesion_disp() -> requests.Session:
    """Sesion por hilo (requests.Session no es segura de compartir entre hilos)."""
    s = getattr(_local, "sesion", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        _local.sesion = s
    return s


def _disponible(sku_id) -> bool:
    """True solo si Paris confirma stock vendible y despachable para el SKU.
    Consulta level-service (variante -1). isServiceable False, sin stock o sin
    opciones de despacho (o SKU inexistente -> error) => no disponible."""
    if not sku_id:
        return False
    try:
        r = _sesion_disp().get(LEVEL, params={"sku": f"{sku_id}-1", "locality": LOCALIDAD}, timeout=15)
        if r.status_code != 200:
            return False
        payload = (r.json() or {}).get("payload") or []
    except Exception:  # noqa: BLE001
        return False
    if not payload:
        return False
    p = payload[0] or {}
    if p.get("error") or not p.get("isServiceable"):
        return False
    return (p.get("totalServiceableStockQty") or 0) > 0 and bool(p.get("shippingOptions"))


def fetch_offers(max_paginas: int = 12, page_size: int = 50, pausa: float = 0.25,
                 workers: int = 16) -> list[Oferta]:
    # Fase 1: recolectar candidatos (parse + dedup) sin chequear stock todavia.
    candidatas, vistos = [], set()
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    for grupo in GRUPOS:
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
            parseables = 0  # items con descuento real y SKU nuevo en esta pagina
            for it in results:
                of = _parse(it, grupo)
                if of is None or of.sku in vistos:
                    continue
                vistos.add(of.sku)
                parseables += 1
                candidatas.append(of)
            # cortar solo si la pagina no aporta NINGUN producto con descuento nuevo
            # (no si solo faltaba stock: las paginas altas son casi todo outlet sin stock).
            if parseables == 0:
                break
            time.sleep(pausa)

    # Fase 2: verificar disponibilidad en paralelo (1 request por SKU, ~miles).
    # Paralelo porque el chequeo secuencial tardaba ~20 min; con pool baja a ~1-2 min.
    log.info("Paris: %d candidatas, verificando stock (%d hilos)...", len(candidatas), workers)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        disp = list(ex.map(lambda of: _disponible(of.sku), candidatas))
    ofertas = [of for of, ok in zip(candidatas, disp) if ok]

    por_grupo: dict[str, int] = {}
    for of in ofertas:
        por_grupo[of.categoria] = por_grupo.get(of.categoria, 0) + 1
    for grupo in GRUPOS:
        log.info("Paris %-20s %d ofertas", grupo, por_grupo.get(grupo, 0))
    log.info("Paris descartadas por sin stock/no disponible: %d", len(candidatas) - len(ofertas))
    return ofertas
