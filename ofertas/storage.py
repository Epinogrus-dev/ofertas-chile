"""Escritura a CSV (compatible con Excel: UTF-8 con BOM y separador ;)
y a JSON estatico para el sitio publicado (site/data/)."""
import csv
import json
import os
import re
import unicodedata
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


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _item(o: Oferta) -> dict:
    # Claves cortas y sin campos vacios: ~20k ofertas viajan por la red en cada visita.
    # Precios siempre enteros (CLP no usa decimales).
    d = {"n": o.nombre_producto, "po": round(o.precio_original), "p": round(o.precio_oferta),
         "d": o.descuento_pct, "url": o.url_producto}
    if o.categoria:
        d["c"] = o.categoria
    if o.marca:
        d["m"] = o.marca
    if o.precio_por_unidad:
        d["pu"] = round(o.precio_por_unidad)
    if o.unidad:
        d["u"] = o.unidad
    if o.imagen_url:
        d["img"] = o.imagen_url
    return d


def escribir_json(ofertas: list[Oferta], dirpath: str) -> int:
    """Exporta el JSON estatico que consume el sitio: un archivo por tienda
    (site/data/tiendas/<slug>.json) mas un index.json con resumen y fecha.

    PRESERVA EL ULTIMO DATO BUENO: si una tienda viene con 0 ofertas en esta
    corrida (p.ej. bloqueada por WAF desde GitHub Actions), NO se pisa su archivo;
    se conserva el ultimo que se haya escrito (tipicamente desde una corrida
    local). El index.json se arma escaneando los archivos que existen en disco,
    asi refleja exactamente lo que se sirve. Devuelve la cantidad de tiendas
    con datos en el sitio.
    """
    tiendas_dir = os.path.join(dirpath, "tiendas")
    os.makedirs(tiendas_dir, exist_ok=True)

    por_tienda: dict[str, list[Oferta]] = {}
    for o in sorted(ofertas, key=lambda o: -o.descuento_pct):
        por_tienda.setdefault(o.tienda, []).append(o)

    # Escribir solo las tiendas que SI trajeron datos (las vacias se preservan).
    for tienda, items in por_tienda.items():
        if not items:
            continue
        slug = _slug(tienda)
        data = {
            "tienda": tienda,
            "actualizado": max((o.fecha_captura for o in items), default=""),
            "ofertas": [_item(o) for o in items],
        }
        with open(os.path.join(tiendas_dir, slug + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    # Armar el index escaneando lo que realmente quedo en disco (fresco + preservado).
    entradas, total = [], 0
    for fn in sorted(os.listdir(tiendas_dir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(tiendas_dir, fn), encoding="utf-8") as f:
            d = json.load(f)
        n = len(d.get("ofertas", []))
        if n == 0:
            continue
        total += n
        entradas.append({
            "nombre": d.get("tienda", fn[:-5]),
            "slug": fn[:-5],
            "ofertas": n,
            "actualizado": d.get("actualizado", ""),
        })

    entradas.sort(key=lambda e: e["nombre"])
    indice = {
        "actualizado": max((e["actualizado"] for e in entradas), default=""),
        "total": total,
        "tiendas": entradas,
    }
    with open(os.path.join(dirpath, "index.json"), "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, separators=(",", ":"))
    return len(entradas)
