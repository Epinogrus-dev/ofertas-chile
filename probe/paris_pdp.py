import json
from playwright.sync_api import sync_playwright
hits=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--disable-blink-features=AutomationControlled","--no-sandbox"])
    ctx=b.new_context(locale="es-CL",timezone_id="America/Santiago",viewport={"width":1366,"height":900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36")
    pg=ctx.new_page()
    def on_resp(resp):
        u=resp.url
        if "ccom.paris.cl" in u or "cnstrc" in u or "price" in u.lower():
            try:
                ct=resp.headers.get("content-type","")
                body=resp.text() if "json" in ct else ""
                rec={"url":u,"status":resp.status,"method":resp.request.method,"ct":ct[:30],"len":len(body)}
                if "json" in ct and ("rice" in body or "normal" in body.lower() or "discount" in body.lower()):
                    rec["has_price"]=True
                    rec["head"]=body[:400]
                    fn="captures/paris_pdp_%d.json"%len(hits)
                    open(fn,"w",encoding="utf-8").write(body)
                    rec["saved"]=fn
                hits.append(rec)
            except Exception as e: hits.append({"url":u,"err":str(e)})
    pg.on("response",on_resp)
    pg.goto("https://www.paris.cl/xiaomi-poco-x8-pro-512gb-12gb-ram-5g-negro-MKQ74ERNK2.html",timeout=60000,wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.evaluate("window.scrollBy(0,1200)"); pg.wait_for_timeout(2000)
    b.close()
for h in hits:
    flag="<<PRICE" if h.get("has_price") else ""
    print(h.get("method"),h.get("status"),h.get("ct"),h.get("len"),h["url"][:120],flag)
json.dump(hits,open("captures/paris_pdp_meta.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
