"""
Visor web LOCAL de ofertas. Lee data/ofertas.csv y sirve una pagina para
buscar / filtrar por tienda / ordenar por descuento, con imagen y link a comprar.

Soporta MULTIPLES disenos: el diseno "Clasico" viene incrustado, y cualquier
archivo en views/<name>.html listado en views/manifest.json aparece como una
opcion mas. Una barra fija arriba permite cambiar de diseno en vivo.

Uso:
    python visor.py            # abre http://localhost:8000 en el navegador
    python visor.py --port 9000
    python visor.py --csv data/otro.csv

No requiere dependencias extra (solo la libreria estandar de Python).
"""
import argparse
import csv
import json
import os
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
VIEWS = os.path.join(BASE, "views")

CLASSIC = r"""<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ofertas Supermercados Chile</title>
<style>
  :root{--bg:#f4f6f8;--card:#fff;--ink:#1a1f26;--muted:#6b7785;--line:#e6eaef;--accent:#e8202a;--green:#1fa02e}
  *{box-sizing:border-box}
  body{margin:0;padding-top:46px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
  header{position:sticky;top:46px;z-index:8;background:#fff;border-bottom:1px solid var(--line);padding:12px 18px;box-shadow:0 1px 6px rgba(0,0,0,.04)}
  .row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
  h1{font-size:18px;margin:0 14px 0 0;white-space:nowrap}
  h1 .em{color:var(--accent)}
  #total{color:var(--muted);font-size:13px;font-weight:600}
  input,select{font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:9px;background:#fff;color:inherit}
  input#q{min-width:230px;flex:1}
  .meta{color:var(--muted);font-size:12px;margin:10px 18px 0}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:14px;padding:14px 18px 40px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;transition:.12s;text-decoration:none;color:inherit}
  .card:hover{box-shadow:0 6px 20px rgba(0,0,0,.10);transform:translateY(-2px)}
  .imgwrap{aspect-ratio:1;background:#fafbfc;display:flex;align-items:center;justify-content:center;position:relative}
  .imgwrap img{width:100%;height:100%;object-fit:contain}
  .badge{position:absolute;top:8px;left:8px;background:var(--accent);color:#fff;font-weight:700;font-size:13px;padding:3px 8px;border-radius:8px}
  .tienda{position:absolute;top:8px;right:8px;font-size:10px;font-weight:700;color:#fff;padding:3px 7px;border-radius:7px;letter-spacing:.3px}
  .body{padding:10px 11px 12px;display:flex;flex-direction:column;gap:4px;flex:1}
  .marca{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
  .nombre{font-size:13px;line-height:1.25;font-weight:600;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:32px}
  .precios{margin-top:auto;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
  .of{font-size:18px;font-weight:800;color:var(--green)}
  .or{font-size:12px;color:var(--muted);text-decoration:line-through}
  .ppu{font-size:11px;color:var(--muted)}
  #more{display:block;margin:8px auto 50px;padding:11px 26px;border:none;border-radius:10px;background:var(--ink);color:#fff;font-weight:600;cursor:pointer}
  .empty{padding:50px;text-align:center;color:var(--muted)}
</style></head>
<body>
<header>
  <div class="row">
    <h1>🛒 Ofertas <span class="em">Chile</span></h1>
    <span id="total"></span>
    <input id="q" placeholder="Buscar producto o marca…">
    <select id="tienda"><option value="">Todas las tiendas</option></select>
    <select id="cat"><option value="">Todas las categorías</option></select>
    <select id="orden">
      <option value="desc">Mayor descuento</option>
      <option value="pasc">Menor precio</option>
      <option value="pdesc">Mayor precio</option>
    </select>
    <select id="mind">
      <option value="0">Cualquier %</option>
      <option value="10">≥ 10%</option>
      <option value="20">≥ 20%</option>
      <option value="30">≥ 30%</option>
      <option value="50">≥ 50%</option>
    </select>
  </div>
</header>
<div class="meta" id="info"></div>
<div class="grid" id="grid"></div>
<button id="more" style="display:none">Ver más</button>
<script>
const COLORS={Jumbo:'#1fa02e','Santa Isabel':'#d4213d',Unimarc:'#e31937',Tottus:'#e53935',Lider:'#0d6efd',Super10:'#f59e0b',Acuenta:'#0d47a1','Central Mayorista':'#7c3aed',Falabella:'#84bd00',Ripley:'#6b2d8b',Paris:'#111111',Hites:'#e2001a','La Polar':'#e6007e'};
let DATA=[],view=[],shown=0,BATCH=300;
const $=s=>document.querySelector(s);
const clp=n=>'$'+Number(n).toLocaleString('es-CL');
fetch('/api/ofertas').then(r=>r.json()).then(d=>{
  DATA=d;$('#total').textContent=d.length.toLocaleString('es-CL')+' ofertas';
  fill('#tienda',[...new Set(d.map(o=>o.tienda))].sort());
  fill('#cat',[...new Set(d.map(o=>o.categoria).filter(Boolean))].sort());
  ['#q','#tienda','#cat','#orden','#mind'].forEach(s=>$(s).addEventListener('input',apply));apply();
});
function fill(sel,arr){const e=$(sel);arr.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;e.appendChild(o);});}
function apply(){
  const q=$('#q').value.trim().toLowerCase(),t=$('#tienda').value,c=$('#cat').value,md=+$('#mind').value;
  view=DATA.filter(o=>(!t||o.tienda===t)&&(!c||o.categoria===c)&&(o.descuento_pct>=md)&&(!q||o.nombre_producto.toLowerCase().includes(q)||(o.marca||'').toLowerCase().includes(q)));
  const ord=$('#orden').value;
  view.sort(ord==='desc'?(a,b)=>b.descuento_pct-a.descuento_pct:ord==='pasc'?(a,b)=>a.precio_oferta-b.precio_oferta:(a,b)=>b.precio_oferta-a.precio_oferta);
  shown=0;$('#grid').innerHTML='';$('#info').textContent=view.length.toLocaleString('es-CL')+' ofertas encontradas';
  if(!view.length)$('#grid').innerHTML='<div class="empty">Sin resultados.</div>';more();
}
function more(){const f=document.createDocumentFragment();view.slice(shown,shown+BATCH).forEach(o=>f.appendChild(card(o)));$('#grid').appendChild(f);shown+=BATCH;$('#more').style.display=shown<view.length?'block':'none';}
$('#more').addEventListener('click',more);
function card(o){const a=document.createElement('a');a.className='card';a.href=o.url_producto;a.target='_blank';a.rel='noopener';const col=COLORS[o.tienda]||'#555';const ppu=o.precio_por_unidad>0?'<span class="ppu">'+clp(o.precio_por_unidad)+(o.unidad?' x '+o.unidad:'')+'</span>':'';a.innerHTML='<div class="imgwrap"><span class="badge">-'+o.descuento_pct+'%</span><span class="tienda" style="background:'+col+'">'+o.tienda+'</span>'+(o.imagen_url?'<img loading="lazy" src="'+o.imagen_url+'" onerror="this.style.display=\'none\'">':'')+'</div><div class="body"><div class="marca">'+(o.marca||'&nbsp;')+'</div><div class="nombre">'+o.nombre_producto+'</div><div class="precios"><span class="of">'+clp(o.precio_oferta)+'</span><span class="or">'+clp(o.precio_original)+'</span></div>'+ppu+'</div>';return a;}
</script>
</body></html>"""


def temas():
    """Lista de temas: los de views/ (el primero es el default) y 'Clásico' al final."""
    out = []
    man = os.path.join(VIEWS, "manifest.json")
    if os.path.exists(man):
        try:
            for t in json.load(open(man, encoding="utf-8")):
                if os.path.exists(os.path.join(VIEWS, t["name"] + ".html")):
                    out.append({"name": t["name"], "title": t.get("title", t["name"])})
        except Exception:
            pass
    out.append({"name": "clasico", "title": "Clásico"})
    return out


def html_tema(name):
    if name == "clasico":
        return CLASSIC
    path = os.path.join(VIEWS, name + ".html")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    return None


def barra(actual, lista):
    btns = []
    for t in lista:
        on = t["name"] == actual
        btns.append(
            '<a href="/view/' + t["name"] + '" style="padding:5px 12px;border-radius:7px;'
            'text-decoration:none;font-size:13px;font-weight:600;white-space:nowrap;'
            + ('background:#fff;color:#1a1f26;' if on else 'color:#cfd6de;')
            + '">' + t["title"] + '</a>')
    return (
        '<div style="position:fixed;top:0;left:0;right:0;height:46px;background:#11151b;'
        'display:flex;align-items:center;gap:6px;padding:0 12px;z-index:99999;overflow-x:auto;'
        'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.25)">'
        '<span style="color:#7b8794;font-size:12px;font-weight:700;margin-right:6px;white-space:nowrap">DISEÑO ▸</span>'
        + "".join(btns) + '</div>')


def inyectar(html, actual, lista):
    inj = "<style>body{padding-top:46px!important}</style>" + barra(actual, lista)
    i = html.rfind("</body>")
    return html[:i] + inj + html[i:] if i != -1 else html + inj


def cargar_ofertas(csv_path):
    if not os.path.exists(csv_path):
        return []
    out = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                r["precio_oferta"] = int(float(r.get("precio_oferta") or 0))
                r["precio_original"] = int(float(r.get("precio_original") or 0))
                r["precio_por_unidad"] = int(float(r.get("precio_por_unidad") or 0))
                r["descuento_pct"] = int(float(r.get("descuento_pct") or 0))
            except ValueError:
                continue
            out.append(r)
    return out


def make_handler(csv_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype, code=200):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _redir(self, location):
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def do_GET(self):
            lista = temas()
            if self.path.startswith("/api/ofertas"):
                data = json.dumps(cargar_ofertas(csv_path), ensure_ascii=False).encode("utf-8")
                self._send(data, "application/json; charset=utf-8")
            elif self.path.startswith("/view/"):
                name = self.path[len("/view/"):].split("?")[0]
                html = html_tema(name)
                if html is None:
                    self._redir("/view/clasico")
                    return
                self._send(inyectar(html, name, lista).encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._redir("/view/" + lista[0]["name"])
    return Handler


def puerto_libre(preferido):
    for p in [preferido] + list(range(preferido + 1, preferido + 20)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return preferido


def main():
    ap = argparse.ArgumentParser(description="Visor web local de ofertas")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--csv", default=os.path.join(BASE, "data", "ofertas.csv"))
    args = ap.parse_args()

    n = len(cargar_ofertas(args.csv))
    if n == 0:
        print("⚠  No encontré ofertas en", args.csv, "- corré primero:  python run.py")
        return

    port = puerto_libre(args.port)
    url = "http://localhost:" + str(port)
    nt = len(temas())
    print("=" * 52)
    print("  Visor de ofertas:", url)
    print("  " + str(n) + " ofertas  ·  " + str(nt) + " diseño(s) disponibles")
    print("  (Ctrl+C para detener)")
    print("=" * 52)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        ThreadingHTTPServer(("127.0.0.1", port), make_handler(args.csv)).serve_forever()
    except KeyboardInterrupt:
        print("\nVisor detenido.")


if __name__ == "__main__":
    main()
