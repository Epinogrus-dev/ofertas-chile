# Plan: publicar la página gratis + mejoras

Objetivo: pasar del visor local (`visor.py`) a una página pública con costo **$0**,
manteniendo el principio del proyecto: datos verificados y consistentes.

## Por qué es fácil de publicar gratis

El visor actual ya separa datos de interfaz: las vistas HTML consumen `/api/ofertas`
(JSON generado desde `data/ofertas.csv`). No hay backend real — si el JSON se genera
**antes** de publicar, todo el sitio es estático (HTML + JSON), y los sitios estáticos
se hospedan gratis sin límites prácticos para este volumen.

```
[scraper run.py] -> ofertas.json (estático) -> [hosting estático gratis] -> navegador
     (cron)                                      (Cloudflare Pages / GitHub Pages)
```

---

## Fase 0 — Preparación (local, 1 sesión de trabajo)

1. **Git**: `git init` en `ofertas-super/`, con `.gitignore` (`__pycache__/`, `.venv/`,
   `data/_run.log`). El CSV/JSON de datos SÍ se versiona (es lo que se publica).
2. **Elegir la vista definitiva**: el manifest ya marca `dashboard-sidebar` como
   principal. Congelarla como `site/index.html` (las otras 4 quedan de archivo).
3. **Exportar JSON estático**: agregar a `ofertas/storage.py` una función
   `escribir_json(ofertas, ruta)` y llamarla desde `run.py` junto al CSV.
   Optimizaciones (el CSV de hoy son ~20.000 filas ≈ 8–10 MB de JSON crudo):
   - Quitar columnas que la vista no usa y acortar claves (`t`, `n`, `po`, `pn`, `d`…).
   - Partir por tienda: `data/ofertas-<tienda>.json` + un `index.json` con resumen
     (conteos, fecha de captura). La página carga el índice al tiro y las tiendas
     en paralelo / bajo demanda.
   - El hosting comprime con gzip/brotli automático → ~1–2 MB reales de transferencia.
4. **Adaptar la vista**: cambiar `fetch('/api/ofertas')` por los JSON estáticos y
   mostrar la `fecha_captura` visible ("Actualizado: 12-06-2026 08:00") — clave para
   la confianza en los datos.

## Fase 1 — Publicación gratuita

**Recomendado: Cloudflare Pages** (sobre GitHub Pages / Netlify / Vercel):
- Gratis sin límite de ancho de banda, brotli automático, repo puede ser privado.
- Dominio `*.pages.dev` gratis para partir; más adelante un dominio propio
  (ej. `ofertaschile.cl`, ~USD 10/año) se conecta gratis vía Cloudflare DNS.
- Alternativa igual de válida: **GitHub Pages** (requiere repo público).

Pasos:
1. Subir el repo a GitHub.
2. Conectar Cloudflare Pages al repo, carpeta de publicación: `site/` + `data/`.
3. **Actualización automática — GitHub Actions con cron** (gratis):
   ```yaml
   # .github/workflows/scrape.yml (esquema)
   on:
     schedule: [{cron: "0 11,23 * * *"}]   # 2 veces al día (UTC)
     workflow_dispatch:                     # botón manual
   jobs:
     scrape:
       runs-on: ubuntu-latest
       steps:
         - checkout, setup-python, pip install -r requirements.txt
         - python run.py            # genera CSV + JSON
         - commit & push de data/   # Pages redeploya solo
   ```
4. **Riesgo a validar (importante)**: los WAF (Akamai en Unimarc, PerimeterX en
   Líder) pueden bloquear IPs de datacenter (las de GitHub Actions). Validación:
   correr el workflow manual una vez y comparar conteos por tienda contra una
   corrida local.
   - Mitigación A: el workflow conserva el último dato bueno por tienda (si una
     tienda devuelve 0 o falla, no pisa su JSON anterior y lo marca como "del día X").
   - Mitigación B (plan de respaldo, siempre funciona): correr `run.py` local y que
     un script haga `git push` — la página se actualiza igual; solo pierde la
     automatización en la nube. Se puede programar con el Programador de tareas
     de Windows.

**Costo total fase 1: $0.** (Dominio propio opcional: ~USD 10/año, no necesario.)

## Fase 2 — Mejoras a la página (UX)

Ordenadas por impacto/esfuerzo:

1. **Búsqueda sin acentos** ("yogurt" debe encontrar "Yogurt" y "Yoghurt";
   normalizar con `String.normalize('NFD')`).
2. **Estado en la URL** (`?q=pañales&tienda=Lider&min=30`) para poder **compartir
   búsquedas** por WhatsApp — probablemente la feature que más difusión genera.
3. **Filtro por rango de precio** y **orden por precio por unidad** (el dato
   `precio_por_unidad` ya existe y es el comparador honesto entre formatos).
4. **Scroll infinito** en vez del botón "Ver más" (IntersectionObserver).
5. **Favoritos** en `localStorage` (lista "mi carrito de ofertas" con total estimado).
6. **PWA** (manifest + service worker): instalable en el teléfono y cachea el último
   JSON para abrir al instante.
7. **Dark mode** (media query + toggle).

## Fase 3 — Mejoras a los datos (la ventaja competitiva real)

1. **Historial de precios**: GitHub Actions ya corre 2×/día — guardar un snapshot
   diario `historia/AAAA-MM-DD.csv.gz` (o SQLite). Con 2–3 semanas de datos:
   - Detectar **ofertas infladas** (suben el "precio normal" antes de rebajar) —
     mostrar "precio más bajo de los últimos 30 días" como hace la ley europea.
   - Badge "**precio mínimo histórico**" — convierte la página de catálogo a
     herramienta de decisión. Encaja directo con la filosofía del proyecto
     (consistencia > cobertura).
2. **Matching entre tiendas**: detectar el mismo producto en 2+ supermercados
   (normalización de nombre + marca + gramaje; los SKU no sirven entre cadenas)
   y mostrar "este Nescafé 170g está más barato en X". Empezar solo con matches
   de alta confianza — mejor pocos y correctos que muchos dudosos.
3. **Categorías unificadas**: hoy cada tienda trae su taxonomía; mapear a ~15
   categorías comunes (Lácteos, Despensa, Aseo…) para que el filtro sirva de verdad.
4. **Verificación continua**: en cada corrida, muestrear N ofertas al azar y
   comparar contra la página real; alertar si la tasa de error sube.

## Fase 4 — Alcance y medición

- **SEO básico**: title/description/OG tags por defecto, `sitemap.xml`, página
  estática por tienda ("Ofertas Jumbo hoy") generada en el build.
- **Analytics gratis y sin cookies**: Cloudflare Web Analytics (incluido) o
  GoatCounter — para saber qué se busca y priorizar.
- **Canal de difusión**: bot de Telegram o feed RSS con las "ofertas del día"
  (descuento ≥ 50% verificado) — se genera en la misma corrida del scraper, $0.

## Fase 5 — Futuro (cuando haya tráfico)

- Links de afiliado donde exista programa (Falabella/Ripley/Paris tienen).
- Alertas por producto ("avísame si baja el aceite") — requiere backend mínimo;
  Cloudflare Workers free tier alcanza de sobra para empezar.

---

## Resumen ejecutivo

| Fase | Qué se logra | Costo |
|---|---|---|
| 0 | Repo git + JSON estático + vista definitiva | $0 |
| 1 | Página pública auto-actualizada 2×/día | $0 |
| 2 | UX: compartir búsquedas, favoritos, PWA | $0 |
| 3 | Historial → detectar ofertas falsas (diferenciador) | $0 |
| 4 | SEO + analytics + Telegram | $0 |
| 5 | Afiliados / alertas | $0 (Workers free) |

Riesgo principal: WAFs bloqueando GitHub Actions (validar en fase 1; el plan B
local-push siempre funciona). Todo lo demás es estático y no tiene punto de falla.
