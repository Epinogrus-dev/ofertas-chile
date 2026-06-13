import json, re
from playwright.sync_api import sync_playwright

SKIP=("google","facebook","maze.","storyly","segment","datadog","newrelic","/px/",
      "cookiebot","onetrust","hotjar","clarity","doubleclick","gstatic","braze","tiktok",
      "criteo","cm.everesttech","scene7","cloudinary","cencosud-media","cdn.","fonts.")
hits=[]
def keep(u):
    return not any(s in u for s in SKIP)

with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--disable-blink-features=AutomationControlled","--no-sandbox"])
    ctx=b.new_context(locale="es-CL",timezone_id="America/Santiago",viewport={"width":1366,"height":900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    pg=ctx.new_page()
    def on_req(req):
        u=req.url
        if req.resource_type in ("xhr","fetch") and keep(u):
            hits.append({"type":"req","method":req.method,"url":u,"rt":req.resource_type,
                         "post":(req.post_data or "")[:400],
                         "ct":req.headers.get("content-type","")})
    pg.on("request",on_req)
    print("goto category…")
    pg.goto("https://www.paris.cl/tecnologia/celulares/",timeout=60000,wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    for _ in range(10):
        pg.evaluate("window.scrollBy(0,1500)"); pg.wait_for_timeout(1000)
    # try clicking a product to see PDP fetches
    pg.wait_for_timeout(2000)
    b.close()

# dedupe by host+path
seen=set(); out=[]
for h in hits:
    host=re.sub(r"^https?://([^/?#]+).*",r"\1",h["url"])
    path=re.sub(r"^https?://[^/]+(/[^?#]*).*",r"\1",h["url"])
    k=(h["method"],host,path)
    if k in seen: continue
    seen.add(k); out.append({"host":host,"path":path,**h})
for o in out:
    print(o["method"], o["host"], o["path"], "| ct=",o["ct"][:30])
    if o["post"]: print("   POST:", o["post"][:200])
json.dump(out,open("captures/paris_net.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("TOTAL unique xhr/fetch:",len(out))
