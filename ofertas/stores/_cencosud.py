"""
Base comun para tiendas Cencosud (Jumbo, Santa Isabel) que comparten el mismo
BFF: POST https://bff.<tienda>.cl/catalog/plp con header apikey y payload de PLP.
Respuesta: products[].items[0] = {price, listPrice, ppumPrice, images[], name, skuId}.

Las ofertas reales son markdowns (listPrice > price). Se ordena por mayor descuento
y se pagina mientras la pagina traiga markdowns; se corta cuando una pagina no tiene
ninguno (el orden por descuento garantiza que el resto tampoco).
"""
import logging
import time
import requests

from ..model import Oferta, num

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def _headers(apikey: str, domain: str) -> dict:
    return {
        "content-type": "application/json",
        "apikey": apikey,
        "origin": domain,
        "referer": domain + "/",
        "user-agent": UA,
    }


def _payload(store_id: str, categoria: str, frm: int, to: int) -> dict:
    return {
        "store": store_id, "collections": [], "fullText": "", "brands": [],
        "hideUnavailableItems": False, "from": frm, "to": to,
        "orderBy": "OrderByBestDiscountDESC",
        "selectedFacets": [{"key": "category1", "value": categoria}],
        "promotionalCards": False, "sponsoredProducts": False,
    }


def _parse(p: dict, tienda: str, domain: str) -> Oferta | None:
    items = p.get("items") or []
    if not items:
        return None
    it = items[0]
    precio = num(it.get("price"))
    lista = num(it.get("listPrice"))
    if precio <= 0 or lista <= 0:
        return None
    slug = p.get("slug") or ""
    imgs = it.get("images") or []
    cat_names = p.get("categoryNames") or []
    return Oferta(
        tienda=tienda,
        nombre_producto=it.get("name") or slug.replace("-", " "),
        precio_original=lista,
        precio_oferta=precio,
        marca=p.get("brand") or "",
        categoria=cat_names[0] if cat_names else "",
        precio_por_unidad=num(it.get("ppumPrice")),
        unidad=it.get("ppumMeasurementUnit") or it.get("measurementUnit") or "",
        sku=str(it.get("skuId") or p.get("productId") or ""),
        url_producto=f"{domain}/{slug}/p" if slug else "",
        imagen_url=imgs[0] if imgs else "",
    )


def fetch_cencosud(tienda: str, domain: str, apikey: str, store_id: str,
                   categorias: list[str], *, max_por_categoria: int = 2000,
                   page_size: int = 50, min_desc: int = 1, max_paginas: int = 40,
                   pausa: float = 0.25) -> list[Oferta]:
    log = logging.getLogger(tienda.lower())
    ofertas: list[Oferta] = []
    sesion = requests.Session()
    sesion.headers.update(_headers(apikey, domain))

    for cat in categorias:
        recolectadas = 0
        frm = 0
        paginas = 0
        while recolectadas < max_por_categoria and paginas < max_paginas:
            try:
                r = sesion.post(f"https://bff.{_host(domain)}/catalog/plp",
                                json=_payload(store_id, cat, frm, frm + page_size - 1),
                                timeout=30)
                if r.status_code != 200:
                    log.warning("%s %s HTTP %s", tienda, cat, r.status_code)
                    break
                productos = r.json().get("products", [])
            except Exception as e:  # noqa: BLE001
                log.warning("%s %s error: %s", tienda, cat, e)
                break
            if not productos:
                break

            markdowns = 0
            for p in productos:
                of = _parse(p, tienda, domain)
                if of is None:
                    continue
                of.finalize()
                if of.descuento_pct < min_desc:
                    continue
                markdowns += 1
                ofertas.append(of)
                recolectadas += 1

            paginas += 1
            if markdowns == 0:
                break
            frm += len(productos)
            time.sleep(pausa)

        log.info("%s %-36s %d ofertas", tienda, cat, recolectadas)

    return ofertas


def _host(domain: str) -> str:
    """https://www.jumbo.cl -> jumbo.cl"""
    return domain.split("//", 1)[-1].replace("www.", "")
