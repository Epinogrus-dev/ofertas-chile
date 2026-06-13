"""
Base comun para tiendas sobre la plataforma Instaleap "Moira Engine"
(Acuenta y Central Mayorista). GraphQL directo (sin navegador, sin WAF):

  POST https://nextgentheadless.instaleap.io/api/v3
  header dpl-api-key por tienda; payload array con operacion SearchProducts.

Oferta real = promotion.type == 'specialPrice' && isActive && conditions[0].price < price.
Se descartan promos condicionales (NxM "lleva N paga M"). Se busca por terminos
comunes de supermercado y se deduplica por sku.
"""
import logging
import time
import requests

from ..model import Oferta, num

API = "https://nextgentheadless.instaleap.io/api/v3"

_QUERY = ("query SearchProducts($i: SearchProductsInput!){ searchProducts(searchProductsInput:$i){ "
          "products{ sku name slug price isAvailable brand photosUrl "
          "promotion{ type isActive conditions{ price priceBeforeTaxes quantity } } "
          "categories{ name } } pagination{ page pages total{ value } } } }")

# Terminos de busqueda que cubren el surtido tipico de supermercado chileno.
TERMINOS = [
    "leche", "pan", "arroz", "aceite", "fideos", "azucar", "cafe", "te", "harina",
    "sal", "atun", "conserva", "mermelada", "cereal", "galleta", "chocolate", "snack",
    "bebida", "jugo", "agua", "cerveza", "vino", "pisco", "yogurt", "queso",
    "mantequilla", "huevo", "pollo", "carne", "cecina", "jamon", "detergente",
    "lavaloza", "cloro", "papel higienico", "toalla", "servilleta", "shampoo", "jabon",
    "pasta dental", "panal", "mascota", "perro", "gato", "fruta", "verdura",
    "congelado", "helado", "salsa", "mayonesa", "ketchup", "completo", "manjar",
]


def _headers(client_id: str, api_key: str, domain: str) -> dict:
    return {
        "content-type": "application/json", "dpl-api-key": api_key,
        "client-name": f"e-commerce Moira Engine {client_id}", "client-version": "0.19.46",
        "apollographql-client-name": f"e-commerce Moira Engine client {client_id}",
        "apollographql-client-version": "0.19.46",
        "origin": domain, "referer": domain + "/",
        "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    }


def _payload(client_id: str, store_ref: str, term: str, page: int, page_size: int) -> list:
    return [{
        "operationName": "SearchProducts",
        "variables": {"i": {"clientId": client_id, "storeReference": store_ref,
                            "pageSize": page_size, "currentPage": page,
                            "search": [{"query": term}]}},
        "query": _QUERY,
    }]


def _parse(p: dict, tienda: str, domain: str) -> Oferta | None:
    promo = p.get("promotion") or {}
    if promo.get("type") != "specialPrice" or not promo.get("isActive"):
        return None
    conds = promo.get("conditions") or []
    if not conds:
        return None
    precio = num(conds[0].get("price"))
    normal = num(p.get("price"))
    if precio <= 0 or normal <= 0 or precio >= normal:
        return None
    fotos = p.get("photosUrl") or []
    cats = p.get("categories") or []
    slug = p.get("slug") or ""
    return Oferta(
        tienda=tienda,
        nombre_producto=p.get("name") or "",
        precio_original=normal,
        precio_oferta=precio,
        marca=p.get("brand") or "",
        categoria=cats[0].get("name") if cats else "",
        sku=str(p.get("sku") or ""),
        url_producto=f"{domain}/p/{slug}" if slug else domain,
        imagen_url=fotos[0] if fotos else "",
    )


def fetch_instaleap(tienda: str, domain: str, client_id: str, store_ref: str,
                    api_key: str, *, max_paginas: int = 3, page_size: int = 40,
                    pausa: float = 0.15) -> list[Oferta]:
    log = logging.getLogger(tienda.lower().replace(" ", ""))
    headers = _headers(client_id, api_key, domain)
    sesion = requests.Session()
    sesion.headers.update(headers)
    ofertas, vistos = [], set()

    for term in TERMINOS:
        for page in range(1, max_paginas + 1):
            try:
                r = sesion.post(API, json=_payload(client_id, store_ref, term, page, page_size), timeout=30)
                d = r.json()
                node = d[0] if isinstance(d, list) else d
                sp = (node.get("data") or {}).get("searchProducts") or {}
                productos = sp.get("products") or []
                pages = (sp.get("pagination") or {}).get("pages") or 1
            except Exception as e:  # noqa: BLE001
                log.debug("%s term=%s p%d error: %s", tienda, term, page, e)
                break
            if not productos:
                break
            for p in productos:
                of = _parse(p, tienda, domain)
                if of is None:
                    continue
                if of.sku in vistos:
                    continue
                vistos.add(of.sku)
                ofertas.append(of)
            if page >= pages:
                break
            time.sleep(pausa)

    log.info("%s: %d ofertas", tienda, len(ofertas))
    return ofertas
