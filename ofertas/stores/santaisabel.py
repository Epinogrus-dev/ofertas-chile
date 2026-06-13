"""
Scraper de SantaIsabel.cl -> mismo BFF Cencosud que Jumbo.
Contrato: POST https://bff.santaisabel.cl/catalog/plp (ver _cencosud.py).
Incluye la categoria dedicada de ofertas '/santas-ofertas'.
"""
from ._cencosud import fetch_cencosud

DOMAIN = "https://www.santaisabel.cl"
APIKEY = "be-reg-groceries-sisa-catalog-wdhhq5a2fken"
STORE_ID = "pedrofontova"

CATEGORIAS = [
    "/santas-ofertas",  # categoria dedicada de ofertas
    "/lacteos-huevos-y-congelados", "/despensa", "/frutas-y-verduras",
    "/panaderia-y-pasteleria", "/quesos-y-fiambres", "/chocolates-galletas-y-snacks",
    "/limpieza", "/mascotas", "/carnes-y-pescados",
]


def fetch_offers():
    return fetch_cencosud("Santa Isabel", DOMAIN, APIKEY, STORE_ID, CATEGORIAS)
