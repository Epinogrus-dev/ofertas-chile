"""Capa 2 - análisis diario sobre el histórico (Capa 1).

Lee historia/*.csv.gz directo con DuckDB (sin servidor, $0) y deriva, por
producto (clave = tienda + sku), la serie de precios, mínimos de 30/90 días,
mínimo histórico, ofertas infladas y las mayores bajas reales del día.

Es idempotente (reconstruye todo desde la Capa 1 en cada corrida) y degrada con
elegancia: si solo hay 1 día de histórico, las métricas que necesitan ventana
(min 30/90 d, bajas vs. línea base) se reportan como "pendientes" indicando
cuántos días faltan, en vez de explotar.

Uso:
    pip install -r analisis/requirements.txt
    python analisis/build.py

Salida: analisis/salida/resumen.json
"""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone

import duckdb

# --- Rutas (relativas a la raíz del proyecto, no al cwd) -------------------
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORIA_GLOB = os.path.join(RAIZ, "historia", "*.csv.gz")
SALIDA_DIR = os.path.join(RAIZ, "analisis", "salida")
SALIDA_JSON = os.path.join(SALIDA_DIR, "resumen.json")

# Ventanas de análisis y umbrales
VENTANA_30 = 30
VENTANA_90 = 90
DIAS_MIN_VENTANA = 2          # mínimo de días para que una ventana tenga sentido
TOP_BAJAS = 50                # cuántas "mayores bajas reales" reportar
TOP_INFLADAS = 50             # cuántas ofertas infladas listar como muestra
MARGEN_INFLADA = 0.02         # 2%: tolera redondeos; evita falsos positivos


# Columnas del histórico (Capa 1). Forzamos tipos para no depender de la
# auto-detección entre archivos (un sku numérico un día y alfanumérico otro
# rompería el merge si DuckDB infiere tipos distintos por archivo).
COLUMNS = {
    "tienda": "VARCHAR",
    "categoria": "VARCHAR",
    "marca": "VARCHAR",
    "nombre_producto": "VARCHAR",
    "precio_original": "DOUBLE",
    "precio_oferta": "DOUBLE",
    "descuento_pct": "INTEGER",
    "precio_por_unidad": "DOUBLE",
    "unidad": "VARCHAR",
    "sku": "VARCHAR",
    "url_producto": "VARCHAR",
    "imagen_url": "VARCHAR",
    "fecha_captura": "VARCHAR",
}


def _read_expr() -> str:
    """Expresión read_csv tipada y robusta para historia/*.csv.gz."""
    cols = ", ".join(f"'{k}': '{v}'" for k, v in COLUMNS.items())
    return (
        f"read_csv('{HISTORIA_GLOB.replace(os.sep, '/')}', "
        f"delim=';', header=true, columns={{{cols}}}, "
        f"ignore_errors=true, null_padding=true)"
    )


def cargar_historico(con: duckdb.DuckDBPyConnection) -> None:
    """Materializa una tabla `hist` con una fila por (tienda, sku, fecha).

    - `fecha` = día calendario derivado de fecha_captura.
    - Si un mismo (tienda, sku, fecha) aparece >1 vez (re-run), se queda la
      observación con menor precio_oferta (la oferta efectiva del día).
    """
    con.execute(
        f"""
        CREATE OR REPLACE TABLE hist AS
        WITH crudo AS (
            SELECT
                tienda,
                NULLIF(sku, '')        AS sku,
                categoria, marca, nombre_producto,
                precio_original, precio_oferta, descuento_pct,
                precio_por_unidad, unidad, url_producto, imagen_url,
                CAST(strptime(fecha_captura, '%Y-%m-%d %H:%M') AS DATE) AS fecha
            FROM {_read_expr()}
            WHERE sku IS NOT NULL AND sku <> ''
              AND precio_oferta > 0
        ),
        ranked AS (
            SELECT *,
                row_number() OVER (
                    PARTITION BY tienda, sku, fecha
                    ORDER BY precio_oferta ASC
                ) AS rn
            FROM crudo
        )
        SELECT tienda, sku, categoria, marca, nombre_producto,
               precio_original, precio_oferta, descuento_pct,
               precio_por_unidad, unidad, url_producto, imagen_url, fecha
        FROM ranked
        WHERE rn = 1
        """
    )


def cobertura(con: duckdb.DuckDBPyConnection) -> dict:
    row = con.execute(
        """
        SELECT
            count(*)                         AS filas,
            count(DISTINCT (tienda, sku))    AS productos,
            count(DISTINCT tienda)           AS tiendas,
            count(DISTINCT fecha)            AS dias,
            min(fecha)                       AS desde,
            max(fecha)                       AS hasta
        FROM hist
        """
    ).fetchone()
    return {
        "filas": row[0],
        "productos": row[1],
        "tiendas": row[2],
        "dias_historico": row[3],
        "fecha_desde": str(row[4]) if row[4] else None,
        "fecha_hasta": str(row[5]) if row[5] else None,
    }


def construir_metricas(con: duckdb.DuckDBPyConnection, fecha_hoy) -> None:
    """Tabla `metricas`: una fila por producto presente HOY, enriquecida con la
    historia previa. `hoy` = la fecha más reciente del histórico (no la del
    reloj: así el análisis es reproducible sobre cualquier corte de datos).
    """
    con.execute(
        f"""
        CREATE OR REPLACE TABLE metricas AS
        WITH hoy AS (
            SELECT * FROM hist WHERE fecha = DATE '{fecha_hoy}'
        ),
        -- Estadísticas de cada producto en la ventana, EXCLUYENDO hoy, para
        -- comparar la oferta de hoy contra su línea base previa.
        ventana AS (
            SELECT
                h.tienda, h.sku,
                min(h.precio_oferta) FILTER (
                    WHERE h.fecha >= DATE '{fecha_hoy}' - {VENTANA_30}
                      AND h.fecha <  DATE '{fecha_hoy}')          AS min_oferta_30d_prev,
                min(h.precio_oferta) FILTER (
                    WHERE h.fecha >= DATE '{fecha_hoy}' - {VENTANA_90}
                      AND h.fecha <  DATE '{fecha_hoy}')          AS min_oferta_90d_prev,
                -- mínimo de TODA la historia previa (para mínimo histórico)
                min(h.precio_oferta) FILTER (WHERE h.fecha < DATE '{fecha_hoy}')
                                                                  AS min_oferta_prev,
                -- "precio normal" de referencia: la mediana del precio_original
                -- declarado en los últimos 30 d (más estable que un solo punto).
                median(h.precio_original) FILTER (
                    WHERE h.fecha >= DATE '{fecha_hoy}' - {VENTANA_30}
                      AND h.fecha <  DATE '{fecha_hoy}'
                      AND h.precio_original > 0)                  AS ref_original_30d_prev,
                count(DISTINCT h.fecha) FILTER (
                    WHERE h.fecha >= DATE '{fecha_hoy}' - {VENTANA_30})  AS dias_obs_30d,
                count(DISTINCT h.fecha)                           AS dias_obs_total
            FROM hist h
            GROUP BY h.tienda, h.sku
        )
        SELECT
            o.tienda, o.sku, o.categoria, o.marca, o.nombre_producto,
            o.precio_original          AS precio_original_hoy,
            o.precio_oferta            AS precio_oferta_hoy,
            o.descuento_pct            AS descuento_pct_declarado,
            o.precio_por_unidad, o.unidad, o.url_producto, o.imagen_url,

            -- Mínimos de ventana INCLUYENDO hoy (lo que mostraría el sitio).
            least(o.precio_oferta, coalesce(v.min_oferta_30d_prev, o.precio_oferta))
                                       AS precio_min_30d,
            least(o.precio_oferta, coalesce(v.min_oferta_90d_prev, o.precio_oferta))
                                       AS precio_min_90d,

            v.min_oferta_prev          AS precio_min_prev,
            v.ref_original_30d_prev,
            coalesce(v.dias_obs_30d, 1)   AS dias_obs_30d,
            coalesce(v.dias_obs_total, 1) AS dias_obs_total,

            -- ¿La oferta de hoy es la más baja jamás registrada para este SKU?
            (v.min_oferta_prev IS NULL OR o.precio_oferta <= v.min_oferta_prev)
                                       AS es_minimo_historico,

            -- Oferta inflada: el precio_original declarado HOY supera la
            -- referencia real (precio normal previo) con margen → la "rebaja"
            -- no es contra su precio habitual. Requiere historia previa.
            (v.ref_original_30d_prev IS NOT NULL
                AND o.precio_original > v.ref_original_30d_prev * (1 + {MARGEN_INFLADA}))
                                       AS oferta_inflada,

            -- Baja real de hoy vs. su mínimo previo (negativo = más caro que antes).
            CASE WHEN v.min_oferta_30d_prev IS NULL THEN NULL
                 ELSE v.min_oferta_30d_prev - o.precio_oferta END
                                       AS baja_real_30d
        FROM hoy o
        LEFT JOIN ventana v USING (tienda, sku)
        """
    )


def _q(con, sql):
    return con.execute(sql).fetchall()


def _cols(con, sql):
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def construir_resumen(con, cob, hay_ventana) -> dict:
    fecha_hoy = cob["fecha_hasta"]

    # --- Métricas siempre disponibles (1 solo día basta) -------------------
    minimos_historicos = con.execute(
        "SELECT count(*) FROM metricas WHERE es_minimo_historico"
    ).fetchone()[0]

    resumen = {
        "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_analisis": fecha_hoy,
        "cobertura": cob,
        "ventana_activa": hay_ventana,
        "notas": [],
        "metricas": {},
    }

    # es_minimo_historico: con 1 día, todo producto es "mínimo histórico"
    # trivialmente (no hay historia previa). Lo señalamos para no confundir.
    resumen["metricas"]["minimos_historicos"] = {
        "total": minimos_historicos,
        "trivial": not hay_ventana,
        "detalle": (
            "Con historia previa: ofertas cuyo precio de hoy es el más bajo "
            "registrado para ese SKU."
            if hay_ventana else
            "Sólo 1 día de histórico: todos los productos figuran como mínimo "
            "histórico por falta de comparación previa. Se activa de verdad "
            "con >= 2 días."
        ),
    }

    # Productos del día (snapshot) por tienda — útil como check de consistencia.
    resumen["metricas"]["productos_por_tienda"] = {
        t: n for t, n in _q(con,
            "SELECT tienda, count(*) FROM metricas GROUP BY tienda ORDER BY 2 DESC")
    }

    # --- Métricas que requieren ventana (>= 2 días) ------------------------
    if not hay_ventana:
        faltan = DIAS_MIN_VENTANA - cob["dias_historico"]
        resumen["notas"].append(
            f"Histórico con {cob['dias_historico']} día(s). Se necesitan "
            f">= {DIAS_MIN_VENTANA} días ({faltan} más) para activar: "
            f"precio_min_30d/90d real, oferta_inflada y mayores bajas reales. "
            f"Métricas marcadas como 'pendientes'."
        )
        resumen["metricas"]["ofertas_infladas"] = {
            "estado": "pendiente",
            "total": 0,
            "requiere_dias": DIAS_MIN_VENTANA,
        }
        resumen["metricas"]["mayores_bajas_reales"] = {
            "estado": "pendiente",
            "items": [],
            "requiere_dias": DIAS_MIN_VENTANA,
        }
        return resumen

    # Ofertas infladas
    n_infladas = con.execute(
        "SELECT count(*) FROM metricas WHERE oferta_inflada"
    ).fetchone()[0]
    muestra_infladas = _cols(con, f"""
        SELECT tienda, sku, nombre_producto,
               precio_original_hoy, precio_oferta_hoy,
               round(ref_original_30d_prev) AS precio_normal_ref_30d,
               precio_min_30d
        FROM metricas
        WHERE oferta_inflada
        ORDER BY (precio_original_hoy - ref_original_30d_prev) DESC
        LIMIT {TOP_INFLADAS}
    """)
    resumen["metricas"]["ofertas_infladas"] = {
        "estado": "activa",
        "total": n_infladas,
        "criterio": (
            f"precio_original declarado hoy > mediana(precio_original) de los "
            f"últimos {VENTANA_30}d * (1+{MARGEN_INFLADA})"
        ),
        "muestra": muestra_infladas,
    }

    # Mayores bajas reales del día (vs. mínimo previo de 30 d, no vs. el
    # precio_original declarado).
    bajas = _cols(con, f"""
        SELECT tienda, sku, nombre_producto,
               precio_oferta_hoy, precio_min_30d,
               baja_real_30d AS baja_clp,
               round(100.0 * baja_real_30d /
                     nullif(precio_min_30d + baja_real_30d, 0), 1) AS baja_pct
        FROM metricas
        WHERE baja_real_30d IS NOT NULL AND baja_real_30d > 0
        ORDER BY baja_real_30d DESC
        LIMIT {TOP_BAJAS}
    """)
    resumen["metricas"]["mayores_bajas_reales"] = {
        "estado": "activa",
        "total": len(bajas),
        "criterio": "precio_oferta de hoy vs. mínimo real previo de 30 días",
        "items": bajas,
    }
    return resumen


def exportar_productos(con) -> str:
    """Exporta el detalle por producto (para enriquecer el sitio más adelante).

    NO modifica el frontend; sólo deja un JSON con los campos derivados clave
    por (tienda, sku): precio_min_30d, precio_min_90d, es_minimo_historico,
    oferta_inflada. Formato compacto.
    """
    path = os.path.join(SALIDA_DIR, "productos.json")
    con.execute(f"""
        COPY (
            SELECT
                tienda, sku,
                CAST(precio_oferta_hoy AS BIGINT)  AS precio_oferta,
                CAST(precio_min_30d AS BIGINT)     AS precio_min_30d,
                CAST(precio_min_90d AS BIGINT)     AS precio_min_90d,
                es_minimo_historico,
                oferta_inflada,
                CAST(round(ref_original_30d_prev) AS BIGINT) AS precio_normal_ref_30d,
                dias_obs_total
            FROM metricas
            ORDER BY tienda, sku
        ) TO '{path.replace(os.sep, '/')}'
        (FORMAT JSON, ARRAY false)
    """)
    return path


def main() -> int:
    os.makedirs(SALIDA_DIR, exist_ok=True)

    archivos = sorted(glob.glob(HISTORIA_GLOB))
    if not archivos:
        resumen = {
            "generado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "error": "Sin histórico: no hay archivos en historia/*.csv.gz.",
            "metricas": {},
        }
        with open(SALIDA_JSON, "w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)
        print("Sin histórico. Nada que analizar. Escrito:", SALIDA_JSON)
        return 0

    con = duckdb.connect()
    con.execute("PRAGMA threads=4")

    cargar_historico(con)
    cob = cobertura(con)
    hay_ventana = cob["dias_historico"] >= DIAS_MIN_VENTANA

    construir_metricas(con, cob["fecha_hasta"])
    resumen = construir_resumen(con, cob, hay_ventana)

    productos_path = exportar_productos(con)

    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2, default=str)

    # --- Reporte a consola -------------------------------------------------
    print("=" * 60)
    print("Análisis Capa 2 -", resumen["fecha_analisis"])
    print("=" * 60)
    print(f"  Archivos histórico : {len(archivos)}")
    print(f"  Días de histórico  : {cob['dias_historico']} "
          f"({cob['fecha_desde']} -> {cob['fecha_hasta']})")
    print(f"  Filas / productos  : {cob['filas']} / {cob['productos']}")
    print(f"  Tiendas            : {cob['tiendas']}")
    print(f"  Ventana activa     : {'sí' if hay_ventana else 'no (degradado)'}")
    m = resumen["metricas"]
    print(f"  Mínimos históricos : {m['minimos_historicos']['total']}"
          f"{' (trivial, 1 día)' if m['minimos_historicos']['trivial'] else ''}")
    print(f"  Ofertas infladas   : {m['ofertas_infladas'].get('total', 0)} "
          f"[{m['ofertas_infladas'].get('estado', m['ofertas_infladas'].get('requiere_dias'))}]")
    bajas = m["mayores_bajas_reales"]
    print(f"  Mayores bajas      : {len(bajas.get('items', []))} "
          f"[{bajas.get('estado', 'pendiente')}]")
    for n in resumen["notas"]:
        print("  NOTA:", n)
    print("-" * 60)
    print("Salida:")
    print("  ", SALIDA_JSON)
    print("  ", productos_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
