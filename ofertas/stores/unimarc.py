"""
Scraper de Unimarc.cl -> BFF directo (sin navegador, pero exige fingerprint Akamai).
Contrato: POST https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search
  header set completo (sec-ch-ua + sec-fetch obligatorios por Akamai).
  payload {categories, from, to (strings), orderBy, promotionsOnly:true}
  -> availableProducts[] = {price:{price,listPrice,ppum...}, item:{nameComplete,slug,brand,images,sku}}

promotionsOnly=true entrega SOLO ofertas (markdown real listPrice>price).
"""
import logging
import time
import requests

from ..model import Oferta, num

log = logging.getLogger("unimarc")

API = "https://bff-unimarc-ecommerce.unimarc.cl/catalog/product/search"
DOMAIN = "https://www.unimarc.cl"

# Akamai exige el set completo de headers tipo navegador (probado: faltar uno -> 403).
HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/plain, */*",
    "accept-language": "es-CL",
    "channel": "UNIMARC", "source": "web", "version": "1.0.0",
    "origin": "https://www.unimarc.cl", "referer": "https://www.unimarc.cl/",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "sec-ch-ua": '"Not:A-Brand";v="99", "Chromium";v="131"',
    "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
}

CATEGORIAS = [
    "carnes", "lacteos-huevos-y-refrigerados", "quesos-y-fiambres",
    "frutas-y-verduras", "congelados", "despensa", "desayuno-y-dulces",
    "bebidas-y-licores", "panaderia-y-pasteleria", "limpieza", "perfumeria",
    "bebes-y-ninos", "mascotas", "hogar",
]


def _payload(categoria: str, frm: int, to: int) -> dict:
    return {
        "categories": categoria, "clusterId": "", "clusterNames": "",
        "from": str(frm), "to": str(to),
        "orderBy": "OrderByBestDiscountDESC", "promotionsOnly": True,
    }


def _parse(p: dict, categoria: str) -> Oferta | None:
    price = p.get("price") or {}
    item = p.get("item") or {}
    precio = num(price.get("price"))
    lista = num(price.get("listPrice") or price.get("priceWithoutDiscount"))
    if precio <= 0 or lista <= 0:
        return None
    slug = item.get("slug") or ""
    if slug and not slug.startswith("/"):
        slug = "/" + slug
    imgs = item.get("images") or []
    return Oferta(
        tienda="Unimarc",
        nombre_producto=item.get("nameComplete") or item.get("name") or "",
        precio_original=lista,
        precio_oferta=precio,
        marca=item.get("brand") or "",
        categoria=categoria.replace("-", " ").title(),
        precio_por_unidad=num(price.get("ppum")),
        unidad=item.get("measurementUnit") or "",
        sku=str(item.get("sku") or item.get("itemId") or ""),
        url_producto=f"{DOMAIN}{slug}" if slug else "",
        imagen_url=imgs[0] if imgs else "",
    )


def fetch_offers(page_size: int = 50, max_por_categoria: int = 2000,
                 max_paginas: int = 50, pausa: float = 0.25) -> list[Oferta]:
    ofertas: list[Oferta] = []
    sesion = requests.Session()
    sesion.headers.update(HEADERS)

    for cat in CATEGORIAS:
        recolectadas = 0
        frm = 0
        for _ in range(max_paginas):
            if recolectadas >= max_por_categoria:
                break
            try:
                r = sesion.post(API, json=_payload(cat, frm, frm + page_size - 1), timeout=30)
                if r.status_code != 200:
                    log.warning("Unimarc %s HTTP %s", cat, r.status_code)
                    break
                productos = r.json().get("availableProducts") or []
            except Exception as e:  # noqa: BLE001
                log.warning("Unimarc %s error: %s", cat, e)
                break
            if not productos:
                break
            for p in productos:
                of = _parse(p, cat)
                if of is not None:
                    ofertas.append(of)
                    recolectadas += 1
            if len(productos) < page_size:
                break
            frm += len(productos)
            time.sleep(pausa)
        log.info("Unimarc %-30s %d ofertas", cat, recolectadas)

    return ofertas
