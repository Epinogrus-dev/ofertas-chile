import json, re
from playwright.sync_api import sync_playwright

posts = []

def main():
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

        def on_response(resp):
            req = resp.request
            if "instaleap.io" in resp.url and req.method == "POST":
                pd = req.post_data or ""
                ops = re.findall(r'"operationName"\s*:\s*"([^"]+)"', pd)
                try:
                    body = resp.body().decode("utf-8", "replace")
                except Exception:
                    body = ""
                if body.startswith("[") or body.startswith("{"):
                    posts.append({"ops": ops, "post_data": pd, "body": body,
                                  "req_headers": dict(req.headers or {})})
                    print(f"POST {ops} {resp.status} {len(body)}b")

        page.on("response", on_response)

        print("goto home")
        try:
            page.goto("https://www.acuenta.cl", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print("warn", e)
        page.wait_for_timeout(7000)

        # Click a category link in the menu to trigger SPA client navigation
        clicked = False
        for sel in ["a[href*='/ca/']"]:
            try:
                links = page.query_selector_all(sel)
                print("found", len(links), "category links")
                for l in links[:4]:
                    href = l.get_attribute("href")
                    try:
                        l.click(timeout=5000)
                        print("clicked", href)
                        clicked = True
                        page.wait_for_timeout(6000)
                        for _ in range(5):
                            page.evaluate("window.scrollBy(0,2000)")
                            page.wait_for_timeout(1200)
                        break
                    except Exception as e:
                        print("click warn", href, e)
            except Exception as e:
                print("sel warn", e)
        # also try clicking 'ver mas'/load more or pagination
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)
        except Exception:
            pass

        browser.close()

    with open("captures/acuenta_spa_posts.json","w",encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print("\nALL ops:")
    for c in posts:
        print(f"- {c['ops']} {len(c['body'])}b")

if __name__ == "__main__":
    main()
