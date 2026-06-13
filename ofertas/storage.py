"""Escritura a CSV (compatible con Excel: UTF-8 con BOM y separador ;)."""
import csv
import os
from .model import Oferta, CSV_FIELDS


def escribir_csv(ofertas: list[Oferta], path: str, sep: str = ";") -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Ordenar por tienda y mayor descuento primero
    ofertas = sorted(ofertas, key=lambda o: (o.tienda, -o.descuento_pct))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=sep)
        w.writeheader()
        for o in ofertas:
            w.writerow(o.row())
    return len(ofertas)
