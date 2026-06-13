"""
Scraper de Jumbo.cl -> API directa Cencosud (sin navegador).
Contrato: POST https://bff.jumbo.cl/catalog/plp (ver _cencosud.py).
"""
from ._cencosud import fetch_cencosud

DOMAIN = "https://www.jumbo.cl"
APIKEY = "be-reg-groceries-jumbo-catalog-w54byfvkmju5"
STORE_ID = "jumboclj512"

# Categorias de primer nivel verificadas (devuelven productos).
CATEGORIAS = [
    "/lacteos-huevos-y-congelados", "/despensa", "/frutas-y-verduras",
    "/panaderia-y-pasteleria", "/quesos-y-fiambres", "/chocolates-galletas-y-snacks",
    "/limpieza", "/mascotas", "/farmacia", "/catering",
    "/hogar-jugueteria-y-libreria", "/licores-bebidas-y-aguas",
]


def fetch_offers():
    return fetch_cencosud("Jumbo", DOMAIN, APIKEY, STORE_ID, CATEGORIAS)
