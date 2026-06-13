# Ofertas Supermercados Chile — Scraper local (CSV)

Scraper **local** que obtiene las ofertas reales de los principales supermercados
chilenos y las guarda en un **CSV** (compatible con Excel). Rediseñado desde cero
para resolver el problema de versiones anteriores: **datos inconsistentes / ofertas
mal capturadas**.

## Por qué este enfoque funciona (y el anterior no)

El scraper viejo **parseaba el HTML** de las páginas (regex sobre `$`, adivinar
precio por kg, detectar tachados). Eso es frágil e inconsistente. Además, las APIs
"legacy" de estos sitios ya están **bloqueadas** (Jumbo/Santa Isabel devuelven el HTML
del SPA, Unimarc tiene WAF Akamai, Líder tiene PerimeterX).

Este scraper llama directamente las **APIs JSON internas** que cada sitio usa (las
mismas que consume su propia web). Resultado: datos **estructurados y verificables**
(precio oferta, precio normal, % descuento, imagen, marca, link) sin adivinar nada.

| Tienda | Plataforma | Método | Notas |
|---|---|---|---|
| **Jumbo** | Cencosud BFF | API directa | `bff.jumbo.cl/catalog/plp` |
| **Santa Isabel** | Cencosud BFF | API directa | `bff.santaisabel.cl` + categoría `/santas-ofertas` |
| **Unimarc** | BFF propio | API directa | filtro nativo `promotionsOnly` (pasa Akamai con headers de navegador) |
| **Tottus** | Falabella / Next.js | HTML `__NEXT_DATA__` | categoría dedicada `Promociones` |
| **Líder** | Walmart Glass GraphQL | API directa | `super.lider.cl/orchestra/graphql` (ofertas = badge ROLLBACK) |
| **Super10** | SMU / Contentful | HTML `__NEXT_DATA__` | catálogo semanal de ofertas |
| **Acuenta** | Instaleap GraphQL | API directa | SuperBodega aCuenta (Walmart); ofertas `specialPrice` |
| **Central Mayorista** | Instaleap GraphQL | API directa | mayorista; ofertas `specialPrice` |

### Retail / tiendas por departamento

| Tienda | Plataforma | Método |
|---|---|---|
| **Falabella** | Next.js "catalyst" (igual que Tottus) | HTML `__NEXT_DATA__`, colección `/ofertas` (ojo: iso-8859-1) |
| **Paris** | Cencosud / Constructor.io | API directa, `sort_by=best-discount` |
| **Ripley** | Next.js propio | HTML `__NEXT_DATA__` (`findabilityProps`) |
| **Hites** | Salesforce Commerce Cloud | API HTML `Search-UpdateGrid` (`srule=discount-off`) |
| **La Polar** | Salesforce Commerce Cloud (abc.cl) | API HTML `Search-UpdateGrid`, categorías `*-en-oferta` |

### Tiendas investigadas y descartadas (sin ofertas estructuradas/consistentes)

| Tienda | Por qué |
|---|---|
| **Alvi** (SMU) | Tiene e-commerce (VTEX), pero **0 rebajas reales**: solo descuentos condicionales por volumen (mayorista). |
| **Mayorista 10** (SMU) | Sitio informativo; el catálogo es un PDF/imagen, sin precios estructurados. |
| **Montserrat** | Sin e-commerce (sitio WordPress informativo); el dominio ya no resuelve. |
| **Erbi** | El dominio `erbi.cl` no resuelve (delegación DNS rota). |

## Qué se considera "oferta"

Solo se guardan **rebajas reales y verificables**: productos donde el
**precio actual < precio normal/lista**. No se incluyen promociones condicionales
(ej. "lleva 3 paga 2", precio socio) porque no tienen un precio único verificable.
Esto garantiza que cada fila del CSV es una oferta real y consistente.

## Instalación

```bash
cd ofertas-super
pip install -r requirements.txt
python -m playwright install chromium   # solo se usa para herramientas de descubrimiento
```

> Las 5 tiendas activas funcionan con **API directa** (solo `requests`). Playwright
> únicamente se usa en `probe/` (herramientas de descubrimiento de APIs), no en la
> corrida normal.

## Uso

```bash
# Todas las tiendas -> data/ofertas.csv
python run.py

# Una sola tienda
python run.py --store jumbo

# CSV en otra ruta
python run.py --out data/ofertas_2026-06-11.csv
```

Al terminar muestra un resumen con la cantidad de ofertas por tienda y cuántas se
descartaron por las reglas de consistencia.

## Visor web local

Para **ver** las ofertas en el navegador (buscar, filtrar por tienda/categoría,
ordenar por descuento, con imagen y link a comprar):

```bash
python visor.py
```

Levanta un servidor local y abre `http://localhost:8000` automáticamente. Lee el
CSV de `data/ofertas.csv` (corré `python run.py` antes para generarlo/actualizarlo).
No requiere dependencias extra. Para detenerlo: `Ctrl+C`.

```bash
python visor.py --port 9000          # otro puerto
python visor.py --csv data/otro.csv  # otro archivo
```

## Salida (CSV)

Separador `;`, codificación UTF-8 con BOM (Excel lo abre directo). Columnas:

| Columna | Descripción |
|---|---|
| `tienda` | Jumbo, Santa Isabel, Unimarc, Tottus, Lider |
| `categoria` | categoría del producto |
| `marca` | marca |
| `nombre_producto` | nombre |
| `precio_original` | precio normal/lista (CLP) |
| `precio_oferta` | precio rebajado (CLP) |
| `descuento_pct` | % de descuento calculado |
| `precio_por_unidad` | precio por kg/lt (comparación) |
| `unidad` | unidad de medida |
| `sku` | identificador del producto |
| `url_producto` | link directo al producto |
| `imagen_url` | imagen |
| `fecha_captura` | fecha y hora de la corrida |

## Reglas de consistencia (`ofertas/validate.py`)

Cada oferta debe cumplir: nombre válido, `precio_oferta > 0`, `precio_original > precio_oferta`,
descuento entre 1% y 95% (sobre 95% suele ser error de datos), URL `http`. Las filas
que no cumplen se descartan y se reportan por motivo. También se deduplica por tienda+sku.

## Estructura

```
ofertas-super/
├── run.py                      # orquestador -> CSV
├── ofertas/
│   ├── model.py                # modelo Oferta + parseo de precios
│   ├── validate.py             # reglas de consistencia
│   ├── storage.py              # escritura CSV (Excel)
│   └── stores/
│       ├── _cencosud.py        # base Jumbo + Santa Isabel
│       ├── _browser.py         # base interceptación con navegador (reutilizable)
│       ├── jumbo.py  santaisabel.py  unimarc.py  tottus.py  lider.py
│       └── _lider_query.gql / _lider_vars.json   # query GraphQL persistida de Líder
├── data/                       # CSV de salida
└── probe/                      # herramientas de descubrimiento de APIs (Playwright)
```

## Agregar más categorías o tiendas

- **Más categorías:** edita la lista `CATEGORIAS`/`DEPARTAMENTOS` del módulo de la tienda.
- **Nueva tienda:** crea `ofertas/stores/<tienda>.py` con una función
  `fetch_offers() -> list[Oferta]` y agrégala a `TIENDAS` en `run.py`.
