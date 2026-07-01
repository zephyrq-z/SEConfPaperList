#!/usr/bin/env python3
"""Build a self-contained static SPA for browsing conference papers.

Reads data/papers.jsonl and generates docs/index.html — a single HTML file
with embedded data, sidebar navigation, search, keyboard shortcuts, and URL
hash routing. No web server needed; just open the file in a browser.

Usage:
    python build_site.py                             # default input -> output
    python build_site.py --input data/my_run.jsonl   # custom input
"""

import argparse
import html as _html
import json
import os

from lib.io import load_jsonl

DEFAULT_INPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "papers.jsonl")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "index.html")

PAGE_TITLE = "SE Conference Papers"
PAGE_DESC = "Browse research papers from ICSE, FSE, ASE, and ISSTA (2024\u20132026)."


def build(input_path: str, output_path: str) -> None:
    papers = load_jsonl(input_path)
    if not papers:
        print(f"Error: no papers in {input_path}")
        return

    # Group by conference, preserve order
    from collections import OrderedDict
    by_conf: OrderedDict = OrderedDict()
    conf_order: list[tuple[str, int]] = []
    for p in papers:
        conf = p.get("conf", "Unknown")
        if conf not in by_conf:
            by_conf[conf] = []
        idx = len(by_conf[conf])
        by_conf[conf].append(p)
        conf_order.append((conf, idx))

    confs = []
    global_idx = 0
    for conf_name, items in by_conf.items():
        tier = items[0].get("tier", "") if items else ""
        confs.append({"name": conf_name, "count": len(items), "start_idx": global_idx, "tier": tier})
        global_idx += len(items)

    flat = []
    for conf_name, idx_in_conf in conf_order:
        p = by_conf[conf_name][idx_in_conf]
        flat.append({
            "conf": conf_name,
            "idx": idx_in_conf,
            "tier": p.get("tier", ""),
            "title": p.get("title", ""),
            "authors": p.get("author", ""),
            "abstract": p.get("abstract", ""),
            "full_version_url": p.get("full_version_url", ""),
            "arxiv_url": p.get("arxiv_url", ""),
            "arxiv_pdf_url": p.get("arxiv_pdf_url", ""),
            "doi": p.get("doi", ""),
            "title_cn": p.get("title_cn", ""),
            "abstract_cn": p.get("abstract_cn", ""),
        })

    papers_json = json.dumps(flat, ensure_ascii=False)
    confs_json = json.dumps(confs, ensure_ascii=False)

    html = _build_html(papers_json, confs_json, len(flat))
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Built {output_path}")
    print(f"  {len(confs)} conferences, {len(flat)} papers")


def _build_html(papers_json: str, confs_json: str, total: int) -> str:
    t = _html.escape(PAGE_TITLE)
    d = _html.escape(PAGE_DESC)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t}</title>
<meta name="description" content="{d}">
<style>
:root{{--bg:#fafafa;--sb-bg:#1e1e2e;--sb-txt:#cdd6f4;--sb-ac:#89b4fa;--sb-hv:#313244;--card:#fff;--txt:#1e1e2e;--t2:#585b70;--ac:#89b4fa;--br:#e6e6e6;--tag-bg:#e6ebf5;--tag-txt:#1e66a0;--sh:0 1px 3px rgba(0,0,0,.08);--r:8px}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1e1e2e;--sb-bg:#181825;--card:#313244;--txt:#cdd6f4;--t2:#a6adc8;--br:#45475a;--tag-bg:#45475a;--tag-txt:#89b4fa;--sh:0 1px 3px rgba(0,0,0,.3)}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background:var(--bg);color:var(--txt);display:flex;min-height:100vh}}
.sb{{width:260px;min-width:260px;background:var(--sb-bg);color:var(--sb-txt);display:flex;flex-direction:column;height:100vh;position:sticky;top:0;overflow-y:auto;border-right:1px solid var(--br)}}
.sb-hd{{padding:20px 16px 12px;border-bottom:1px solid rgba(205,214,244,.15)}}
.sb-hd h1{{font-size:1.1rem;font-weight:700;color:#fff}}
.sb-hd .sub{{font-size:.75rem;color:#a6adc8;margin-top:4px}}
.srch{{padding:12px 16px}}
.srch input{{width:100%;padding:8px 12px;border-radius:6px;border:1px solid rgba(205,214,244,.2);background:#313244;color:#cdd6f4;font-size:.85rem;outline:none}}
.srch input::placeholder{{color:#6c7086}}
.srch input:focus{{border-color:var(--ac)}}
.cl{{flex:1;overflow-y:auto;padding:8px 0}}
.ci{{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;cursor:pointer;font-size:.85rem;transition:background .15s;border-left:3px solid transparent;user-select:none}}
.ci:hover{{background:var(--sb-hv)}}
.ci.act{{background:var(--sb-hv);border-left-color:var(--sb-ac);color:#fff}}
.ci .cnt{{font-size:.7rem;background:rgba(205,214,244,.15);padding:2px 8px;border-radius:10px;color:#a6adc8}}
.st{{font-size:.7rem;color:#6c7086;padding:8px 16px 4px;cursor:default;font-weight:600}}
.ci.act .cnt{{background:rgba(137,180,250,.2);color:var(--sb-ac)}}
.sb-ft{{padding:12px 16px;border-top:1px solid rgba(205,214,244,.15);font-size:.7rem;color:#6c7086;display:flex;justify-content:space-between;align-items:center}}
.main{{flex:1;display:flex;flex-direction:column;min-width:0;height:100vh;overflow:hidden}}
.tb{{padding:12px 24px;border-bottom:1px solid var(--br);display:flex;align-items:center;justify-content:space-between;background:var(--card);flex-shrink:0}}
.tb .clb{{font-size:.85rem;color:var(--t2);font-weight:500}}
.tb .plb{{font-size:.85rem;color:var(--t2)}}
.ct{{flex:1;overflow-y:auto;display:flex;flex-direction:column;align-items:center;padding:24px;justify-content:flex-start}}
.tier-A{{display:inline-block;font-size:.65rem;font-weight:700;padding:1px 6px;border-radius:3px;background:#dbeafe;color:#1e40af;margin-right:4px;vertical-align:middle}}
.tier-B{{display:inline-block;font-size:.65rem;font-weight:700;padding:1px 6px;border-radius:3px;background:#fef3c7;color:#92400e;margin-right:4px;vertical-align:middle}}
@media(prefers-color-scheme:dark){{.tier-A{{background:#1e3a5f;color:#93c5fd}}.tier-B{{background:#3d2e0a;color:#fcd34d}}}}
.card{{background:var(--card);border-radius:var(--r);box-shadow:var(--sh);border:1px solid var(--br);padding:32px;max-width:1100px;width:100%}}
.card .pi{{font-size:.75rem;color:var(--t2);margin-bottom:8px}}
.card .pt{{font-size:1.25rem;font-weight:700;line-height:1.45;margin-bottom:12px}}
.card .ptc{{font-size:1.1rem;color:var(--t2);margin-bottom:16px}}
.card .pa{{font-size:.9rem;color:var(--t2);margin-bottom:20px;line-height:1.5}}
.card .pab{{font-size:.9rem;line-height:1.65;margin-bottom:12px}}
.card .pac{{font-size:.85rem;line-height:1.65;color:var(--t2);margin-bottom:20px}}
.card .pl{{display:flex;gap:12px;flex-wrap:wrap}}
.card .pl a{{display:inline-flex;align-items:center;gap:4px;padding:6px 14px;border-radius:6px;font-size:.8rem;font-weight:500;text-decoration:none;transition:background .15s;background:var(--tag-bg);color:var(--tag-txt)}}
.card .pl a:hover{{opacity:.8}}
.card .pl a.ax{{background:#b31b1b1a;color:#b31b1b}}
.nb{{display:flex;align-items:center;gap:16px;padding:16px 24px;border-top:1px solid var(--br);background:var(--card);flex-shrink:0}}
.nb button{{padding:8px 20px;border-radius:6px;border:1px solid var(--br);background:var(--card);color:var(--txt);font-size:.85rem;cursor:pointer;transition:all .15s;font-weight:500}}
.nb button:hover:not(:disabled){{border-color:var(--ac);color:var(--ac)}}
.nb button:disabled{{opacity:.35;cursor:default}}
.nb .np{{font-size:.8rem;color:var(--t2);margin:0 auto}}
.emp{{text-align:center;color:var(--t2)}}
.emp h2{{font-size:1.5rem;margin-bottom:8px}}
.theme-btn{{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:4px;border:1px solid rgba(205,214,244,.2);background:rgba(205,214,244,.08);color:#a6adc8;font-size:.7rem;cursor:pointer;transition:all .15s}}
.theme-btn:hover{{background:rgba(205,214,244,.15);color:#fff}}
@media(max-width:700px){{body{{flex-direction:column}}.sb{{width:100%;min-width:0;height:auto;max-height:40vh;position:relative}}.main{{height:auto}}.card{{padding:20px}}.tb{{padding:10px 16px;flex-wrap:wrap;gap:4px;flex-shrink:0}}.nb{{padding:10px 16px;gap:8px;flex-shrink:0}}.nb button{{padding:8px 14px;font-size:.8rem}}}}
.rog-ambient,.rog-edge{{display:none}}
</style>
<style id="rog-css">
html.rog{{--bg:#08080d;--sb-bg:#0d0d15;--sb-txt:#a09ab8;--sb-ac:#ff2d95;--sb-hv:#1a1a2a;--card:#13131e;--txt:#e8e6f0;--t2:#a09ab8;--ac:#ff2d95;--br:rgba(255,255,255,.07);--tag-bg:rgba(255,45,149,.1);--tag-txt:#ff2d95;--sh:0 0 20px rgba(255,45,149,.1);--r:8px;font-family:"SF Mono","Cascadia Code","JetBrains Mono",Menlo,Monaco,monospace}}
html.rog body{{background:var(--bg);font-family:"SF Mono","Cascadia Code","JetBrains Mono",Menlo,Monaco,monospace}}
html.rog .sb{{background:var(--sb-bg);border-right-color:rgba(255,255,255,.06)}}
html.rog .sb-hd h1{{color:#ff2d95;text-shadow:0 0 12px rgba(255,45,149,.4);letter-spacing:1px;text-transform:uppercase}}
html.rog .sb-hd .sub{{color:#6e6a82}}
html.rog .srch input{{background:var(--sb-hv);border-color:rgba(255,255,255,.08);color:var(--txt);font-family:inherit}}
html.rog .srch input:focus{{border-color:var(--ac);box-shadow:0 0 12px rgba(255,45,149,.2)}}
html.rog .ci{{font-family:inherit;border-left-color:transparent}}
html.rog .ci:hover{{background:var(--sb-hv)}}
html.rog .ci.act{{background:var(--sb-hv);border-left-color:var(--ac);color:#fff;box-shadow:inset 0 0 12px rgba(255,45,149,.08)}}
html.rog .ci .cnt{{background:rgba(255,45,149,.12);color:var(--sb-ac)}}
html.rog .ci.act .cnt{{background:rgba(255,45,149,.2);color:#ff2d95}}
html.rog .sb-ft{{border-top-color:rgba(255,255,255,.06);color:#6e6a82}}
html.rog .tb{{border-bottom-color:rgba(255,255,255,.06);background:var(--card)}}
html.rog .card{{background:var(--card);border:1px solid rgba(255,45,149,.15);box-shadow:0 0 20px rgba(255,45,149,.08),0 0 40px rgba(255,45,149,.03)}}
html.rog .card .pt{{color:#fff;font-size:1.2rem;letter-spacing:.3px}}
html.rog .card .ptc{{color:#a09ab8;font-size:1rem}}
html.rog .card .pa{{color:var(--t2);border-bottom:1px solid rgba(255,255,255,.06);padding-bottom:16px;margin-bottom:16px}}
html.rog .card .pab{{color:#c8c4d8;line-height:1.7}}
html.rog .card .pac{{color:#a09ab8;line-height:1.7}}
html.rog .card .pl a{{background:rgba(255,45,149,.1);color:#ff2d95;border:1px solid rgba(255,45,149,.2);font-family:inherit}}
html.rog .card .pl a:hover{{background:rgba(255,45,149,.2);box-shadow:0 0 10px rgba(255,45,149,.2);opacity:1}}
html.rog .card .pl a.ax{{background:rgba(0,229,255,.08);color:#00e5ff;border-color:rgba(0,229,255,.2)}}
html.rog .card .pl a.ax:hover{{box-shadow:0 0 10px rgba(0,229,255,.2)}}
html.rog .nb{{border-top-color:rgba(255,255,255,.06);background:var(--card)}}
html.rog .nb button{{background:var(--sb-hv);border-color:rgba(255,255,255,.08);color:var(--txt);font-family:inherit}}
html.rog .nb button:hover:not(:disabled){{border-color:var(--ac);color:var(--ac);box-shadow:0 0 10px rgba(255,45,149,.15)}}
html.rog .nb .np{{color:var(--t2)}}
html.rog .nb .np input{{background:var(--sb-hv);border-color:rgba(255,255,255,.08);color:var(--txt);font-family:inherit}}
html.rog .tb .clb{{color:var(--t2)}}
html.rog .tb .plb{{color:var(--t2)}}
html.rog .card .pi{{color:#6e6a82}}
html.rog .emp{{color:var(--t2)}}
html.rog .sb-ft a{{color:#ff2d95;text-decoration:none}}
html.rog .sb-ft a:hover{{text-shadow:0 0 8px rgba(255,45,149,.5)}}
html.rog .theme-btn{{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:4px;border:1px solid rgba(255,45,149,.2);background:rgba(255,45,149,.08);color:#ff2d95;font-size:.7rem;font-family:inherit;cursor:pointer;transition:all .15s}}
html.rog .theme-btn:hover{{background:rgba(255,45,149,.15);box-shadow:0 0 10px rgba(255,45,149,.2)}}
html.rog::after{{content:"";position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.04) 2px,rgba(0,0,0,.04) 4px)}}
@keyframes rogGlow{{0%,100%{{border-color:rgba(255,45,149,.15);box-shadow:0 0 20px rgba(255,45,149,.08),0 0 40px rgba(255,45,149,.03)}}50%{{border-color:rgba(255,45,149,.25);box-shadow:0 0 25px rgba(255,45,149,.12),0 0 50px rgba(180,77,255,.05)}}}}
html.rog .card{{animation:rogGlow 3s ease-in-out infinite}}
@keyframes ambientBreathe{{0%,100%{{opacity:.7}}50%{{opacity:1}}}}
@keyframes edgeBreathe{{0%,100%{{opacity:.5}}50%{{opacity:.85}}}}
html.rog .rog-ambient{{display:block}}
html.rog .rog-edge{{display:block}}
@keyframes neonPulse{{0%,100%{{opacity:1}}50%{{opacity:.7}}}}
html.rog .rog-ambient{{position:fixed;inset:0;pointer-events:none;z-index:9998;background:radial-gradient(ellipse 500px 350px at 0% 0%,rgba(255,45,149,.35) 0%,transparent 55%),radial-gradient(ellipse 500px 350px at 100% 0%,rgba(180,77,255,.3) 0%,transparent 55%),radial-gradient(ellipse 500px 350px at 100% 100%,rgba(0,229,255,.25) 0%,transparent 55%),radial-gradient(ellipse 500px 350px at 0% 100%,rgba(57,255,20,.22) 0%,transparent 55%),radial-gradient(ellipse 250px 500px at 50% 0%,rgba(255,45,149,.35) 0%,transparent 65%),radial-gradient(ellipse 250px 500px at 100% 50%,rgba(180,77,255,.3) 0%,transparent 65%),radial-gradient(ellipse 250px 500px at 50% 100%,rgba(0,229,255,.25) 0%,transparent 65%),radial-gradient(ellipse 250px 500px at 0% 50%,rgba(57,255,20,.22) 0%,transparent 65%);animation:ambientBreathe 3s ease-in-out infinite}}
html.rog .rog-edge{{position:fixed;inset:0;pointer-events:none;z-index:9997;background:linear-gradient(to bottom,rgba(255,45,149,.22) 0%,transparent 150px),linear-gradient(to left,rgba(180,77,255,.2) 0%,transparent 150px),linear-gradient(to top,rgba(0,229,255,.17) 0%,transparent 150px),linear-gradient(to right,rgba(57,255,20,.14) 0%,transparent 150px);animation:edgeBreathe 4s ease-in-out infinite}}
html.rog::-webkit-scrollbar{{width:6px;height:6px}}
html.rog::-webkit-scrollbar-track{{background:transparent}}
html.rog::-webkit-scrollbar-thumb{{background:rgba(255,45,149,.2);border-radius:3px}}
html.rog::-webkit-scrollbar-thumb:hover{{background:rgba(255,45,149,.4)}}
html.rog::selection{{background:rgba(255,45,149,.3);color:#fff}}
</style>
</head>
<body>
<div class="rog-ambient"></div><div class="rog-edge"></div>
<aside class="sb">
  <div class="sb-hd"><h1>{t}</h1><div class="sub">{d}</div></div>
  <div class="srch"><input id="sch" placeholder="Search {total} papers\u2026" autocomplete="off"></div>
  <nav class="cl" id="cl"></nav>
  <div class="sb-ft"><span><span id="ft">{total} papers</span> &middot; <a href="https://github.com/zephyrq-z/SEConfPaperList" style="color:inherit">GitHub</a></span><button class="theme-btn" id="rog-toggle" onclick="toggleROG()" title="Toggle theme">&#9788;</button></div>
</aside>
<main class="main">
  <div class="tb"><span class="clb" id="tbc"></span><span class="plb" id="tbp"></span></div>
  <div class="ct" id="ct"></div>
  <div class="nb">
    <button id="bp" title="Previous (\u2190 / h)">\u2190 Prev</button>
    <span class="np"><input id="npin" type="number" min="1" value="1" style="width:60px;text-align:center;font-size:.8rem;border:1px solid var(--br);border-radius:4px;padding:4px 6px;background:var(--card);color:var(--txt)"> / <span id="npt"></span></span>
    <button id="bn" title="Next (\u2192 / l)">Next \u2192</button>
  </div>
</main>
<script>
var PAPERS={papers_json};
var CONFS={confs_json};
var ci=0,cc=null,sq="";
var cl=document.getElementById("cl");
var ai=document.createElement("div");
ai.className="ci act";
ai.innerHTML='<span>All Conferences</span><span class="cnt">{total}</span>';
ai.addEventListener("click",function(){{sc(null);}});
cl.appendChild(ai);
var tiers=[{{label:"CCF-A",key:"A"}},{{label:"CCF-B",key:"B"}}];
tiers.forEach(function(t){{var a=CONFS.filter(function(c){{return c.tier===t.key;}});if(!a.length)return;var h=document.createElement("div");h.className="st";h.textContent=t.label;cl.appendChild(h);a.forEach(function(c){{var e=document.createElement("div");e.className="ci";e.textContent=c.name;var b=document.createElement("span");b.className="cnt";b.textContent=c.count;e.appendChild(b);e.addEventListener("click",function(){{sc(c.name);}});cl.appendChild(e);}});}});
function fp(){{
  var l=PAPERS;
  if(cc)l=l.filter(function(p){{return p.conf===cc;}});
  if(sq){{var q=sq.toLowerCase();l=l.filter(function(p){{return(p.title&&p.title.toLowerCase().indexOf(q)!==-1)||(p.title_cn&&p.title_cn.toLowerCase().indexOf(q)!==-1)||(p.authors&&p.authors.toLowerCase().indexOf(q)!==-1)||(p.abstract&&p.abstract.toLowerCase().indexOf(q)!==-1);}});}}
  return l;
}}
function esc(s){{return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
function rd(){{
  var f=fp();if(f.length===0){{ci=0;}}else{{if(ci>=f.length)ci=f.length-1;if(ci<0)ci=0;}}
  var is=document.querySelectorAll(".ci");for(var i=0;i<is.length;i++)is[i].classList.remove("act");
  if(cc===null)cl.querySelector(".ci").classList.add("act");
  else{{var items=cl.querySelectorAll(".ci");for(var j=0;j<items.length;j++)if(items[j].textContent.startsWith(cc)){{items[j].classList.add("act");break;}}}}
  document.getElementById("tbc").textContent=cc||"All Conferences";
  if(f.length===0){{
    document.getElementById("tbp").textContent="No papers found";
    document.getElementById("npt").textContent="0";
    document.getElementById("npin").value=0;document.getElementById("npin").max=0;
    document.getElementById("bp").disabled=true;document.getElementById("bn").disabled=true;
    return;
  }}
  document.getElementById("tbp").textContent="#"+(ci+1)+" of "+f.length;
  var p=f[ci],ri=PAPERS.indexOf(p)+1;
  var h='<div class="card">';
  h+='<div class="pi">#'+ri+' &middot; <span class="tier-'+esc(p.tier||'')+'">CCF-'+esc(p.tier||'')+'</span> '+esc(p.conf)+'</div>';
  h+='<div class="pt">'+esc(p.title)+'</div>';
  if(p.title_cn)h+='<div class="ptc">'+esc(p.title_cn)+'</div>';
  h+='<div class="pa">'+esc(p.authors)+'</div>';
  if(p.abstract)h+='<div class="pab">'+esc(p.abstract)+'</div>';
  if(p.abstract_cn)h+='<div class="pac">'+esc(p.abstract_cn)+'</div>';
  var lks=[];
  if(p.full_version_url)lks.push('<a href="'+esc(p.full_version_url)+'" target="_blank">&#128279; Researchr</a>');
  if(p.doi)lks.push('<a class="dx" href="'+esc(p.doi)+'" target="_blank">DOI</a>');
  if(p.arxiv_url)lks.push('<a class="ax" href="'+esc(p.arxiv_url)+'" target="_blank">arXiv</a>');
  if(p.arxiv_pdf_url)lks.push('<a class="ax" href="'+esc(p.arxiv_pdf_url)+'" target="_blank">PDF</a>');
  if(lks.length)h+='<div class="pl">'+lks.join("")+'</div>';
  h+='</div>';
  document.getElementById("ct").innerHTML=h;
  document.getElementById("npin").value=ci+1;document.getElementById("npin").max=f.length;
  document.getElementById("npt").textContent=f.length;
  document.getElementById("bn").disabled=ci>=f.length-1;
  var cs=p.conf.replace(/\\s+/g,"-");
  var hh="#"+cs+"/"+(ci+1);
  if(window.location.hash!==hh)history.replaceState(null,"",hh);
}}
function sc(c){{cc=c;ci=0;sq="";document.getElementById("sch").value="";rd();}}
document.getElementById("bp").addEventListener("click",function(){{if(ci>0){{ci--;rd();}}}});
document.getElementById("bn").addEventListener("click",function(){{var f=fp();if(ci<f.length-1){{ci++;rd();}}}});
document.getElementById("sch").addEventListener("input",function(e){{sq=e.target.value.trim();ci=0;rd();}});
document.getElementById("npin").addEventListener("keydown",function(e){{if(e.key==="Enter"){{var v=parseInt(e.target.value,10);var f=fp();if(!isNaN(v)&&v>=1&&v<=f.length){{ci=v-1;rd();}}else{{e.target.value=ci+1;}}}}}});
document.addEventListener("keydown",function(e){{
  if(e.target.tagName==="INPUT")return;var f=fp();if(f.length===0)return;
  switch(e.key){{
    case"ArrowLeft":case"h":if(ci>0){{ci--;rd();}}break;
    case"ArrowRight":case"l":if(ci<f.length-1){{ci++;rd();}}break;
    case"ArrowUp":case"k":if(ci>0){{ci--;rd();}}break;
    case"ArrowDown":case"j":if(ci<f.length-1){{ci++;rd();}}break;
    case"g":ci=0;rd();break;
    case"G":ci=f.length-1;rd();break;
    case"/":e.preventDefault();document.getElementById("sch").focus();break;
    case"Escape":document.getElementById("sch").blur();break;
  }}
}});
(function(){{
  var h=window.location.hash.slice(1);if(!h)return;
  var ps=h.split("/");if(ps.length>=1)for(var i=0;i<CONFS.length;i++)if(CONFS[i].name.replace(/\\s+/g,"-")===ps[0]){{cc=CONFS[i].name;break;}}
  if(ps.length>=2){{var n=parseInt(ps[1],10);if(!isNaN(n)&&n>=1)ci=n-1;}}
}})();
rd();
function toggleROG(){{var h=document.documentElement;h.classList.toggle("rog");var b=document.getElementById("rog-toggle");b.innerHTML=h.classList.contains("rog")?"&#9789;":"&#9788;";localStorage.setItem("rog",""+(h.classList.contains("rog")?"1":"0"));}}
(function(){{if(localStorage.getItem("rog")==="1"){{document.documentElement.classList.add("rog");document.getElementById("rog-toggle").innerHTML="&#9789;";}}}})();
</script>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static paper browsing site")
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help=f"Input JSONL file (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=OUTPUT_PATH,
                        help=f"Output HTML file (default: {OUTPUT_PATH})")
    args = parser.parse_args()
    build(args.input, args.output)


if __name__ == "__main__":
    main()