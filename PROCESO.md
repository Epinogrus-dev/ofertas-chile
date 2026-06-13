# PROCESO — runbook diario de punta a punta

Cómo fluye el dato cada día, desde el scrape hasta el análisis, y cómo correr
cada pieza a mano. Principio del proyecto: **$0 de costo** y **consistencia de
datos** (mejor pocos datos correctos que muchos dudosos).

```
                    ┌──────────────── nube (GitHub Actions, 2×/día) ────────────────┐
                    │  8 tiendas que NO bloquean IPs de datacenter                   │
   scrape  ─────────┤                                                                ├─► validación ─► CSV + JSON + snapshot ─► Pages ─► análisis
                    │  5 tiendas con WAF (403 desde la nube) → runner local          │
                    └──────────────── self-hosted runner (PC local) ────────────────┘
```

---

## 1. Las dos vías de scraping (y por qué)

El scraper (`run.py`) llama las **APIs JSON internas** de cada sitio (no parsea
HTML a ciegas). Trae las 13 tiendas, pero **5 están protegidas por WAF** que
devuelven **HTTP 403 a las IPs de datacenter** de GitHub Actions:

| Vía | Dónde corre | Tiendas | Motivo |
|---|---|---|---|
| **Nube** | GitHub Actions (`ubuntu-latest`), cron 2×/día | Tottus, Super10, Acuenta, Central Mayorista, Falabella, Paris, Hites, La Polar (8) | IP de datacenter aceptada; gratis y desatendido |
| **Local** | self-hosted runner en el PC | Jumbo, Santa Isabel, Unimarc, Líder, Ripley (5) | WAF (Akamai / PerimeterX / etc.) bloquea IPs de nube → 403. La IP residencial pasa |

Ambas vías corren el **mismo `run.py`**. La diferencia es la IP de salida.

**Por qué no rompe la consistencia:** `escribir_json` (en `ofertas/storage.py`)
**preserva el último dato bueno por tienda**: si una corrida trae 0 ofertas para
una tienda (p.ej. la nube no scrapea las 5 bloqueadas), **no pisa** su JSON
anterior. El `index.json` se arma escaneando lo que hay en disco, así refleja
exactamente lo que se sirve. La corrida local rellena las 5 que faltan.

---

## 2. Cómo fluye el dato

1. **Scrape** — `run.py` ejecuta cada `ofertas/stores/<tienda>.py` y junta las
   ofertas crudas.
2. **Validación de consistencia** — `ofertas/validate.filtrar()` descarta
   ofertas mal capturadas (precios inválidos, descuentos imposibles, etc.). El
   resumen impreso muestra `crudas -> válidas` y los motivos de descarte.
3. **Persistencia (3 salidas, mismas filas válidas):**
   - `data/ofertas.csv` — CSV para Excel (UTF-8 con BOM, separador `;`).
   - `site/data/` — JSON estático para el sitio: un archivo por tienda +
     `index.json` (claves cortas, sin campos vacíos; ~20k ofertas livianas).
   - `historia/AAAA-MM-DD.csv.gz` — **snapshot inmutable del día** (Capa 1),
     vía `escribir_snapshot`. Append-only; un re-run **nunca degrada** el día:
     solo reescribe si la corrida nueva trae **más** filas (así la corrida local
     de 13 tiendas no es pisada por la de la nube con 8).
4. **Publicación** — GitHub Actions sube `site/` como artefacto y lo despliega
   en **GitHub Pages**. Guardarrail en el workflow: si el total de ofertas baja
   de 2000, **falla en vez de publicar** un sitio casi vacío.
5. **Análisis (Capa 2)** — `analisis/build.py` lee `historia/*.csv.gz` con
   DuckDB y deriva métricas por producto (mínimos, mínimo histórico, ofertas
   infladas, mayores bajas). Ver §4.

---

## 3. Correr el scraper a mano

```bash
pip install -r requirements.txt        # requests + playwright (liviano)
python run.py                          # las 13 tiendas activas
python run.py --store jumbo            # una sola tienda
```

Genera `data/ofertas.csv`, `site/data/` y `historia/AAAA-MM-DD.csv.gz`.

**Plan B (siempre funciona):** si la automatización en la nube falla, correr
`run.py` local y hacer `git push` de `site/` actualiza la página igual; solo se
pierde el desatendido. Programable con el Programador de tareas de Windows.

---

## 4. Correr el análisis a mano (Capa 2)

DuckDB lee los `.csv.gz` directo con SQL — **$0, sin servidor**.

```bash
pip install -r analisis/requirements.txt   # solo duckdb (NO toca el requirements raíz)
python analisis/build.py
```

Salidas en `analisis/salida/`:
- **`resumen.json`** — cobertura + métricas agregadas (mínimos históricos,
  ofertas infladas, mayores bajas, productos por tienda) y notas de estado.
- **`productos.json`** — una línea JSON por `(tienda, sku)` con los campos
  derivados pensados para **enriquecer el sitio más adelante**:
  `precio_min_30d`, `precio_min_90d`, `es_minimo_historico`, `oferta_inflada`,
  `precio_normal_ref_30d`. (El frontend **no** se toca todavía; solo se dejan
  los datos listos.)

El análisis es **idempotente y reconstruible**: se reconstruye entero desde la
Capa 1 en cada corrida; se puede borrar `analisis/salida/` sin perder nada.

### Qué calcula, por producto (clave = `tienda` + `sku`)

- **Serie de precios** (`precio_oferta` por fecha) — base de todo lo demás.
- **`precio_min_30d` / `precio_min_90d`** — mínimo de la oferta en la ventana
  (incluye hoy).
- **`es_minimo_historico`** — la oferta de hoy es la más baja jamás registrada
  para ese SKU.
- **`oferta_inflada`** — el `precio_original` declarado hoy supera la
  **mediana del precio_original de los últimos 30 días** (con 2% de margen) →
  la "rebaja" no es contra su precio habitual. Estilo "precio más bajo de los
  últimos 30 días" de la normativa europea.
- **Mayores bajas reales del día** — `precio_oferta` de hoy vs. su **mínimo real
  previo de 30 días** (línea base histórica), **no** vs. el `precio_original`
  declarado (que puede estar inflado).

### Degradación con elegancia (pocos días de histórico)

`build.py` tolera que hoy solo exista **1 día** de histórico:

- No explota. Reporta la cobertura real y marca como `"pendiente"` las métricas
  que necesitan ventana, indicando **cuántos días faltan** (umbral: ≥ 2 días
  para activar `precio_min_30d/90d` real, `oferta_inflada` y mayores bajas).
- Con 1 día, `es_minimo_historico` es trivialmente `true` para todos (no hay
  comparación previa); el JSON lo señala con `"trivial": true`.

Salida real con **1 día** (`historia/2026-06-11.csv.gz`, 20.230 filas):

```
Días de histórico  : 1 (2026-06-11 -> 2026-06-11)
Filas / productos  : 20230 / 20230
Tiendas            : 13
Ventana activa     : no (degradado)
Mínimos históricos : 20230 (trivial, 1 día)
Ofertas infladas   : 0 [pendiente]
Mayores bajas      : 0 [pendiente]
NOTA: Histórico con 1 día. Se necesitan >= 2 días (1 más) para activar...
```

Con **≥ 2 días** (validado con un segundo día sintético) las tres métricas de
ventana se activan: `oferta_inflada` y `mayores_bajas_reales` pasan a estado
`"activa"` y `es_minimo_historico` deja de ser trivial. Con **30+ días** las
ventanas de 30/90 días pasan a cubrir un mes/trimestre completo y
`precio_min_30d` se vuelve un comparador honesto para el badge del sitio.

---

## 5. Capas de datos

- **Capa 1 — histórico inmutable** (`historia/AAAA-MM-DD.csv.gz`).
  Append-only, una foto por día, 13 columnas, `;`, UTF-8. Es la **fuente de
  verdad**. No se edita ni se reprocesa.
- **Capa 2 — análisis derivado** (`analisis/salida/`).
  100% **reconstruible** desde la Capa 1. Si se corrompe o se borra, se
  regenera corriendo `analisis/build.py`. Nunca es fuente de verdad.

---

## 6. Checks de calidad recomendados

- **Conteo por tienda vs. promedio móvil:** comparar `productos_por_tienda`
  (en `resumen.json`) contra el promedio de los últimos días. Una caída brusca
  en una tienda = posible bloqueo WAF o cambio de API. (Hoy se revisa a ojo;
  automatizarlo es un próximo paso.)
- **Snapshot no vacío:** `escribir_snapshot` ya ignora corridas vacías y no
  degrada el día. Verificar que `historia/AAAA-MM-DD.csv.gz` existe y pesa lo
  esperado tras cada corrida.
- **Guardarrail de publicación:** el workflow falla si el total < 2000 ofertas
  (evita publicar un sitio casi vacío por bloqueo).
- **Las 13 tiendas presentes:** tras la corrida combinada nube+local, confirmar
  que `index.json` lista las 13 (las 5 con WAF dependen de la corrida local).
- **Sanidad de precios:** `precio_oferta > 0` y `precio_oferta <=
  precio_original`; `validate.filtrar()` ya los descarta, pero conviene vigilar
  el conteo de rechazos por consistencia.

---

## 7. Qué falta / próximos pasos (honesto)

- **Persistir la Capa 1 desde la nube.** Hoy el workflow sirve `site/` como
  artefacto de Pages y **no commitea** `historia/`. Para acumular histórico de
  verdad hay que decidir y montar la persistencia: que la corrida **local** sea
  la que versiona/commitea `historia/` (más simple y consistente con las 13
  tiendas), o que el workflow commitee los `.csv.gz`. **Sin esto, el histórico
  no crece y la Capa 2 se queda en 1 día.** Es el bloqueante real para activar
  las métricas de ventana.
- **Integrar la Capa 2 al sitio.** `productos.json` ya deja listos
  `precio_min_30d`, `es_minimo_historico`, `oferta_inflada`; falta consumirlos
  en el frontend (badges "precio mínimo histórico" / "oferta inflada"). No se
  toca `site/index.html` todavía, por diseño.
- **Correr `build.py` en el pipeline.** Hoy es manual; agregar un paso al
  workflow (o al cron local) para regenerar `analisis/salida/` tras cada
  scrape.
- **Automatizar el check de conteo vs. promedio móvil** y emitir una alerta
  (Telegram / log) cuando una tienda cae fuera de rango.
- **Matching entre tiendas y categorías unificadas** (PLAN.md fase 3): el mismo
  producto en 2+ cadenas y ~15 categorías comunes. Los SKU no sirven entre
  cadenas; requiere normalización de nombre+marca+gramaje, empezando solo por
  matches de alta confianza.
- **Afinar `oferta_inflada`** cuando haya más días: hoy usa la mediana del
  `precio_original` declarado de 30 días; con más historia conviene contrastar
  también contra el precio_oferta modal (precio "habitual" real) para no
  depender solo de lo que declara la tienda.
```
