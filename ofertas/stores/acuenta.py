"""
Scraper de Acuenta.cl (SuperBodega aCuenta, Walmart) -> Instaleap directo.
Ofertas via promotion.type=='specialPrice' (ver _instaleap.py).
"""
from ._instaleap import fetch_instaleap


def fetch_offers():
    return fetch_instaleap(
        tienda="Acuenta", domain="https://www.acuenta.cl",
        client_id="SUPER_BODEGA", store_ref="580",
        api_key="aa401ae6-dee5-4435-a250-85b2122930d8",
    )
