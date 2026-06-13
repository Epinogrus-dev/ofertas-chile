"""Modelo de datos comun para una oferta de supermercado."""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

_NUM_RE = re.compile(r"\d[\d.]*(?:,\d+)?")


# Orden de columnas del CSV de salida
CSV_FIELDS = [
    "tienda", "categoria", "marca", "nombre_producto",
    "precio_original", "precio_oferta", "descuento_pct",
    "precio_por_unidad", "unidad", "sku",
    "url_producto", "imagen_url", "fecha_captura",
]


def num(v) -> float:
    """
    Convierte de forma segura a numero. Soporta:
      '3703' (Jumbo), '$1.000' / '$3.150' (Unimarc), '$1.333 x Kg' (ppum con sufijo),
      12890 (int). Toma el primer numero, quita separador de miles '.' y usa ',' decimal.
    """
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    m = _NUM_RE.search(str(v))
    if not m:
        return 0.0
    t = m.group(0).replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


@dataclass
class Oferta:
    tienda: str
    nombre_producto: str
    precio_original: float
    precio_oferta: float
    descuento_pct: int = 0
    marca: str = ""
    categoria: str = ""
    precio_por_unidad: float = 0.0
    unidad: str = ""
    sku: str = ""
    url_producto: str = ""
    imagen_url: str = ""
    fecha_captura: str = ""

    def finalize(self) -> "Oferta":
        """Calcula descuento y fecha; normaliza tipos. Llamar antes de validar."""
        self.precio_original = round(num(self.precio_original))
        self.precio_oferta = round(num(self.precio_oferta))
        self.precio_por_unidad = round(num(self.precio_por_unidad))
        if self.precio_original > 0 and self.precio_oferta > 0:
            self.descuento_pct = round((1 - self.precio_oferta / self.precio_original) * 100)
        self.nombre_producto = (self.nombre_producto or "").strip()[:200]
        self.marca = (self.marca or "").strip()
        if not self.fecha_captura:
            self.fecha_captura = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
        return self

    def clave(self) -> tuple:
        """Clave de deduplicacion."""
        return (self.tienda, self.sku or self.url_producto)

    def row(self) -> dict:
        return {k: getattr(self, k) for k in CSV_FIELDS}
