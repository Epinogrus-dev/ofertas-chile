"""
Orquestador del scraper de ofertas de supermercados chilenos (modo LOCAL -> CSV).

Uso:
    python run.py                      # todas las tiendas activas
    python run.py --store jumbo        # solo una tienda
    python run.py --out data/mis_ofertas.csv
"""
import argparse
import importlib
import logging
import os
import time

from ofertas.validate import filtrar
from ofertas.storage import escribir_csv, escribir_json, escribir_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run")

# Tiendas activas (se iran agregando a medida que se verifica cada API).
# El valor es el nombre del modulo en ofertas/stores/.
TIENDAS = [
    # supermercados
    "jumbo", "santaisabel", "unimarc", "tottus", "lider",
    "super10", "acuenta", "centralmayorista",
    # retail / tiendas por departamento
    "falabella", "paris", "ripley", "hites", "lapolar",
]

BASE = os.path.dirname(os.path.abspath(__file__))


def correr_tienda(nombre: str):
    try:
        mod = importlib.import_module(f"ofertas.stores.{nombre}")
    except ModuleNotFoundError:
        log.error("Tienda '%s' no encontrada (falta ofertas/stores/%s.py)", nombre, nombre)
        return []
    t0 = time.time()
    log.info("==> %s: iniciando...", nombre)
    try:
        ofertas = mod.fetch_offers()
    except Exception as e:  # noqa: BLE001
        log.error("%s fallo: %s", nombre, e)
        return []
    log.info("==> %s: %d ofertas crudas en %.1fs", nombre, len(ofertas), time.time() - t0)
    return ofertas


def main():
    ap = argparse.ArgumentParser(description="Scraper de ofertas supermercados Chile")
    ap.add_argument("--store", help="Ejecutar solo una tienda (ej. jumbo)")
    ap.add_argument("--out", default=os.path.join(BASE, "data", "ofertas.csv"),
                    help="Ruta del CSV de salida")
    args = ap.parse_args()

    tiendas = [args.store] if args.store else list(TIENDAS)

    # Tiendas "solo-local": se saltan en la nube (EXCLUIR_TIENDAS=paris,...).
    # La nube las preserva con su ultimo dato bueno del runner local. Util para
    # tiendas con verificacion pesada o IP-sensible (ej. Paris chequea stock por
    # producto, lento e inestable desde datacenter).
    excluir = {t.strip().lower() for t in os.environ.get("EXCLUIR_TIENDAS", "").split(",") if t.strip()}
    if excluir and not args.store:
        tiendas = [t for t in tiendas if t not in excluir]
        log.info("Excluyendo tiendas (EXCLUIR_TIENDAS): %s", ", ".join(sorted(excluir)))

    crudas = []
    for t in tiendas:
        crudas.extend(correr_tienda(t))

    validas, rechazos = filtrar(crudas)

    n = escribir_csv(validas, args.out)
    json_dir = os.path.join(BASE, "site", "data")
    nt_json = escribir_json(validas, json_dir)
    snap = escribir_snapshot(validas, os.path.join(BASE, "historia"))

    print("\n" + "=" * 56)
    print(f"  RESUMEN  ({len(crudas)} crudas -> {len(validas)} validas)")
    print("=" * 56)
    por_tienda = {}
    for o in validas:
        por_tienda[o.tienda] = por_tienda.get(o.tienda, 0) + 1
    for tienda, c in sorted(por_tienda.items()):
        print(f"  {tienda:16} {c:5} ofertas")
    if rechazos:
        print("  --- descartadas por consistencia ---")
        for motivo, c in sorted(rechazos.items(), key=lambda x: -x[1]):
            print(f"  {c:5}  {motivo}")
    print("=" * 56)
    print(f"  CSV:  {args.out}  ({n} filas)")
    print(f"  JSON: {json_dir}  ({nt_json} tiendas, para el sitio)")
    if snap:
        print(f"  SNAP: {snap}  (histórico inmutable)")
    else:
        print("  SNAP: conservado (ya existía un snapshot más completo del día)")
    print("=" * 56)


if __name__ == "__main__":
    main()
