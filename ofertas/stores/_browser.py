"""
Base comun para tiendas protegidas por WAF (Lider/PerimeterX, Unimarc/Akamai),
donde NO se puede llamar la API directo con requests. Se usa un navegador real
(Playwright) que pasa el WAF y mantiene la sesion, y se INTERCEPTAN las respuestas
JSON de la API interna (no se parsea el HTML). Cada tienda aporta un parser que
recibe el JSON crudo y devuelve Ofertas.
"""
import logging
import time
from typing import Callable

from playwright.sync_api import sync_playwright

from ..model import Oferta

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fetch_via_browser(
    tienda: str,
    seed_urls: list[str],
    url_match: str | tuple[str, ...],
    parser: Callable[[dict], list[Oferta]],
    *,
    scrolls: int = 12,
    scroll_pausa: float = 1.2,
    espera_inicial: float = 5.0,
    headless: bool = True,
) -> list[Oferta]:
    """
    seed_urls   paginas de ofertas/categoria a visitar.
    url_match   substring(s) que identifican las respuestas de la API a interceptar.
    parser      funcion(json_body) -> list[Oferta]; se llama por cada respuesta capturada.
    """
    log = logging.getLogger(tienda.lower())
    matches = (url_match,) if isinstance(url_match, str) else tuple(url_match)
    ofertas: list[Oferta] = []
    capturas = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=[
            "--disable-blink-features=AutomationControlled", "--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 900}, locale="es-CL",
            timezone_id="America/Santiago", user_agent=UA)
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = ctx.new_page()

        def on_response(resp):
            nonlocal capturas
            try:
                if not any(m in resp.url for m in matches):
                    return
                ct = (resp.headers or {}).get("content-type", "").lower()
                if "json" not in ct:
                    return
                data = resp.json()
            except Exception:
                return
            try:
                nuevas = parser(data) or []
            except Exception as e:  # noqa: BLE001
                log.debug("%s parser error: %s", tienda, e)
                return
            if nuevas:
                capturas += 1
                ofertas.extend(nuevas)

        page.on("response", on_response)

        for url in seed_urls:
            log.info("%s -> %s", tienda, url)
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001
                log.warning("%s goto %s: %s", tienda, url, e)
                continue
            page.wait_for_timeout(int(espera_inicial * 1000))
            for _ in range(scrolls):
                try:
                    page.evaluate("window.scrollBy(0, 1400)")
                except Exception:
                    break
                page.wait_for_timeout(int(scroll_pausa * 1000))

        browser.close()

    log.info("%s: %d respuestas API capturadas, %d ofertas crudas", tienda, capturas, len(ofertas))
    return ofertas
