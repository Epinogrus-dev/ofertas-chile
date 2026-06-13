"""Guardarrail post-scrape: confirma que site/data/index.json tiene datos
suficientes antes de publicar. Sale con código !=0 si algo falló (corta el
workflow). Uso: python tools/verificar_sitio.py [minimo]"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

idx = json.load(open(os.path.join(BASE, "site", "data", "index.json"), encoding="utf-8"))
print(f"Total ofertas: {idx['total']} en {len(idx['tiendas'])} tiendas")
for t in idx["tiendas"]:
    print(f"  {t['nombre']:18} {t['ofertas']:6}  {t.get('actualizado','')}")
if idx["total"] < MIN:
    sys.exit(f"Muy pocas ofertas ({idx['total']} < {MIN}): algo falló. No publico.")
print("OK")
