import json, re
from playwright.sync_api import sync_playwright
hits=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--disable-blink-features=AutomationControlled","--no-sandbox"])
    ctx=b.new_context(locale="es-CL",timezone_id="America/Santiago",viewport={"width":1366,"height":900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    pg=ctx.new_page()
    def on_resp(resp):
        u=resp.url
        if "cnstrc.com" in u or "constructor" in u:
            try:
                ct=resp.headers.get("content-type","")
                body=resp.text() if "json" in ct else ""
                hits.append({"url":u,"status":resp.status,"method":resp.request.method,"ct":ct,
                             "len":len(body),"req_headers":dict(resp.request.headers),
                             "body_head": body[:300]})
                if "json" in ct and len(body)>2000:
                    fn="captures/paris_cnstrc_%d.json"%len(hits)
                    open(fn,"w",encoding="utf-8").write(body)
            except Exception as e:
                hits.append({"url":u,"err":str(e)})
    pg.on("response",on_resp)
    pg.goto("https://www.paris.cl/tecnologia/celulares/",timeout=60000,wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    for _ in range(6):
        pg.evaluate("window.scrollBy(0,1500)"); pg.wait_for_timeout(900)
    b.close()
for h in hits:
    print(h.get("method"),h.get("status"),h.get("ct","")[:25],h.get("len"),h["url"][:140])
json.dump(hits,open("captures/paris_cnstrc_meta.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
