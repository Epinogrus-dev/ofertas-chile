"""
Validacion de consistencia de ofertas.

El problema de los scrapers anteriores era data inconsistente (precios mezclados,
descuentos falsos, ofertas sin descuento real). Aqui centralizamos TODAS las reglas
para que el CSV solo contenga ofertas reales y coherentes.
"""
from .model import Oferta

DESC_MIN = 1     # descuento minimo real (%)
DESC_MAX = 95    # sobre esto suele ser error de datos (precio/kg vs unidad)
PRECIO_MIN = 50  # CLP, precios menores son ruido
PRECIO_MAX = 30_000_000


def validar(of: Oferta) -> tuple[bool, str]:
    """Devuelve (es_valida, motivo_si_invalida)."""
    if not of.nombre_producto or len(of.nombre_producto) < 3:
        return False, "nombre vacio o muy corto"
    # nombre que es solo numeros/precio (basura de scraping HTML)
    if of.nombre_producto.replace(" ", "").replace("$", "").replace(".", "").isdigit():
        return False, "nombre es solo numeros"
    if of.precio_oferta < PRECIO_MIN or of.precio_oferta > PRECIO_MAX:
        return False, f"precio_oferta fuera de rango ({of.precio_oferta})"
    if of.precio_original < PRECIO_MIN or of.precio_original > PRECIO_MAX:
        return False, f"precio_original fuera de rango ({of.precio_original})"
    if of.precio_original < of.precio_oferta:
        return False, "precio invertido (original < oferta)"
    if of.precio_original == of.precio_oferta:
        return False, "sin descuento (original == oferta)"
    if of.descuento_pct < DESC_MIN:
        return False, f"descuento < {DESC_MIN}%"
    if of.descuento_pct > DESC_MAX:
        return False, f"descuento > {DESC_MAX}% (sospechoso, posible precio/kg)"
    if not of.url_producto.startswith("http"):
        return False, "url invalida"
    return True, ""


def filtrar(ofertas: list[Oferta], log=None) -> tuple[list[Oferta], dict]:
    """Filtra ofertas validas y devuelve (validas, conteo_de_rechazos_por_motivo)."""
    validas, rechazos = [], {}
    vistas = set()
    for of in ofertas:
        of.finalize()
        ok, motivo = validar(of)
        if not ok:
            rechazos[motivo] = rechazos.get(motivo, 0) + 1
            continue
        k = of.clave()
        if k in vistas:
            rechazos["duplicado"] = rechazos.get("duplicado", 0) + 1
            continue
        vistas.add(k)
        validas.append(of)
    return validas, rechazos
