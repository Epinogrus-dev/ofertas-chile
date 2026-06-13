"""
Scraper de CentralMayorista.cl (mayorista) -> Instaleap directo.
Ofertas via promotion.type=='specialPrice' (ver _instaleap.py).
"""
from ._instaleap import fetch_instaleap


def fetch_offers():
    return fetch_instaleap(
        tienda="Central Mayorista", domain="https://www.centralmayorista.cl",
        client_id="CENTRAL_MAYORISTA", store_ref="159",
        api_key="bc648ae6-3b18-4e35-8c3a-11e61074faa8",
    )
