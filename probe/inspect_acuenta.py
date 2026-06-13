import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--disable-blink-features=AutomationControlled", "--no-sandbox"])
    ctx = browser.new_context(
        viewport={"width": 1366, "height": 900}, locale="es-CL",
        timezone_id="America/Santiago",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
    ctx.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    page = ctx.new_page()
    print("goto home...")
    try:
        page.goto("https://www.acuenta.cl", timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        print("goto warn:", e)
    page.wait_for_timeout(8000)
    print("TITLE:", page.title())
    print("URL:", page.url)
    # collect all anchors
    hrefs = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a => ({href:a.getAttribute('href'), text:(a.innerText||'').trim().slice(0,40)}))""")
    # filter likely categories
    seen = set()
    out = []
    for h in hrefs:
        href = h['href'] or ''
        if href in seen: continue
        seen.add(href)
        out.append(h)
    with open("captures/acuenta_links.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("total links:", len(out))
    for h in out[:80]:
        print(h['href'], "|", h['text'])
    # dump body snippet
    html = page.content()
    with open("captures/acuenta_home.html","w",encoding="utf-8") as f:
        f.write(html)
    print("HTML bytes:", len(html))
    browser.close()
