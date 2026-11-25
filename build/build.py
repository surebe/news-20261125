#!/usr/bin/env python3
"""
THE WHOLE WORLD — one-page news poster engine (news-image-20261125).

Pipeline: stories.json + art/*.webp  ->  page.html (HTML/CSS, Noto Serif/Sans)
          ->  WeasyPrint PDF @1024x1024  ->  PyMuPDF raster @2048
          ->  PIL downscale to 1024  ->  entry PNG file holding JPEG bytes
          (the gate tells PNG from JPEG by first bytes; the name stays
          entry.png either way).

Design: broadsheet front page. Black bars top/bottom, giant serif date
masthead, red italic deck, six-stat band, region strip, hero + rail of
illustrated leads, a wide illustrated lead + text leads, dot-matrix world
map with numbered pins on land, numbered briefs, DATE CHECK strip,
THE DAY IN UTC timeline, sources + certainty legend footer.

Map: dot grid sampled from Natural Earth country polygons
(assets/world.geo.json) rasterised to a mask — dots land on land only.
Projection: equirectangular, lon -180..180, lat 78..-42.
"""
import json, sys, math
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
ART = HERE / "art"
ASSETS = HERE / "assets"
BUILD.mkdir(exist_ok=True)
(BUILD / "art").mkdir(exist_ok=True)

INK = "#17181c"; PAPER = "#f5edd8"; RED = "#b3231b"; SLATE = "#46586a"
MAPBG = "#ece1c6"; DOT = "#3d4a57"

LAT_TOP, LAT_BOT = 77.0, -42.0
def proj(lon, lat, w, h):
    return (lon + 180.0) / 360.0 * w, (LAT_TOP - lat) / (LAT_TOP - LAT_BOT) * h

# ---------------------------------------------------------------- art prep
FOCUS = {  # (fx, fy) crop focus per art stem, 0..1
    "hero-cop31": (0.50, 0.50),
    "lead-factory": (0.50, 0.52),
    "lead-corvette": (0.50, 0.50),
    "lead-capitol": (0.50, 0.30),
    "hero-tariffs": (0.50, 0.62),
    "rail-iowa": (0.50, 0.48),
    "rail-hormuz": (0.50, 0.55),
    "wide-tiangong": (0.50, 0.32),
    "strip-houthi": (0.50, 0.45),
    "strip-solomon": (0.50, 0.45),
    "strip-cartagena": (0.50, 0.50),
    "strip-ramaphosa": (0.50, 0.45),
    "strip-energy": (0.50, 0.50),
    "strip-kospi": (0.50, 0.50),
}
def prep_art(stem, tw, th):
    """Centre-crop the generated webp to the slot aspect (at 2x) -> JPEG."""
    srcs = sorted(ART.glob(f"*{stem}*.webp")) or sorted(ART.glob(f"{stem}*.jpg"))
    if not srcs:
        raise SystemExit(f"art not found for {stem}")
    im = Image.open(srcs[0]).convert("RGB")
    W, H = im.size
    want = tw / th
    have = W / H
    fx, fy = FOCUS.get(stem, (0.5, 0.5))
    if have > want:  # too wide -> crop x
        nw = int(H * want); x0 = int(min(max(fx * W - nw / 2, 0), W - nw)); box = (x0, 0, x0 + nw, H)
    else:            # too tall -> crop y
        nh = int(W / want); y0 = int(min(max(fy * H - nh / 2, 0), H - nh)); box = (0, y0, W, y0 + nh)
    im = im.crop(box).resize((tw * 2, th * 2), Image.LANCZOS)
    out = BUILD / "art" / f"{stem}.jpg"
    im.save(out, quality=90)
    return out.name

# ---------------------------------------------------------------- dot map
def build_dotmap(w=452, h=160, step_deg=2.2, dot_r=2.3):
    W, H = w * 2, h * 2
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    data = json.loads((ASSETS / "world.geo.json").read_text())
    def ring(coords):
        return [proj(lon, lat, W, H) for lon, lat in coords]
    for feat in data["features"]:
        g = feat.get("geometry") or {}
        polys = []
        if g.get("type") == "Polygon":
            polys = [g["coordinates"]]
        elif g.get("type") == "MultiPolygon":
            polys = g["coordinates"]
        for poly in polys:
            for r in poly:
                if len(r) >= 3:
                    md.polygon(ring(r), fill=255)
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    px = mask.load()
    lat = LAT_TOP
    while lat > LAT_BOT:
        lon = -180.0
        while lon < 180.0:
            x, y = proj(lon, lat, W, H)
            xi, yi = int(x), int(y)
            if 0 <= xi < W and 0 <= yi < H and px[xi, yi] > 0:
                dd.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=DOT + "ff")
            lon += step_deg
        lat -= step_deg
    dots = dots.resize((w, h), Image.LANCZOS)
    out = BUILD / "dotmap.png"
    dots.save(out)
    return out.name

# ---------------------------------------------------------------- html bits
def chip(cert):
    return f'<span class="cert c-{cert.lower()}">{cert}</span>'

def kick(num, text):
    return f'<div class="kick"><span class="knum">{num}</span>{text}</div>'

def art_block(story, cls, tw, th, compact=False):
    img = prep_art(story["art"], tw, th)
    kc = 'kick sm' if compact else 'kick'
    cc = 'cert sm c-' + story["certainty"].lower()
    return (f'<div class="artwrap {cls}"><img src="art/{img}"/>'
            f'<div class="{kc}"><span class="knum">{story["num"]}</span>{story["kicker"]}</div>'
            f'<span class="{cc}">{story["certainty"]}</span></div>')

def build_html(d):
    hero = d["hero"]; wide = d["wide_lead"]
    stats = "".join(
        f'<div class="stat"><div class="snum">{s["n"]}</div><div class="slab">{s["label"]}</div></div>'
        for s in d["stats"])
    regions = " &nbsp;·&nbsp; ".join(
        f'{r["name"]}&nbsp;<b>{r["count"]}</b>' for r in d["regions"])
    rail = ""
    for s in d["rail"]:
        rail += f'''<div class="railcard">
          {art_block(s, "rail-art", 352, 100)}
          <div class="rhead">{s["headline"]}</div>
          <div class="rsum">{s["summary"]}</div>
          <div class="src">{s["source"]}</div></div>'''
    tleads = ""
    for s in d["text_leads"]:
        tleads += f'''<div class="tlead">
          <div class="tkick"><span class="knum">{s["num"]}</span>{s["kicker"]} {chip(s["certainty"])}</div>
          <div class="thead">{s["headline"]}</div>
          <div class="tsum">{s["summary"]}</div>
          <div class="src">{s["source"]}</div></div>'''
    briefs = ""
    for b in d["briefs"]:
        briefs += (f'<p class="brief"><span class="breg">{b["region"]}</span> '
                   f'<b>{b["headline"]}.</b> {b["text"]} <span class="bsrc">· {b["source"]}</span></p>')
    overflow = ""
    for o in d.get("overflow", []):
        overflow += (f'<p class="ovf"><span class="onum">{o["num"]}</span> '
                     f'<span class="oreg">{o["region"]}</span> {o["headline"]}</p>')
    strip = ""
    for s in d.get("strip", []):
        strip += f'''<div class="scard">
          {art_block(s, "strip-art", 158, 52, compact=True)}
          <div class="shead">{s["headline"]}</div>
          <div class="ssrc">{s["source"]}</div></div>'''
    timeline = ' <span class="tsep">·</span> '.join(
        f'<span class="titem"><b>{t["utc"]}</b> {t["text"]}</span>' for t in d["timeline"])
    pins = []
    for s in [hero, wide] + d["rail"] + d["text_leads"] + d.get("strip", []):
        if "pin" in s:
            pins.append((s["num"], s["pin"]["lon"], s["pin"]["lat"]))
    for p in d.get("extra_pins", []):
        pins.append((p["num"], p["lon"], p["lat"]))
    pin_html = ""
    for num, lon, lat in sorted(pins):
        x, y = proj(lon, lat, 100, 100)
        pin_html += f'<div class="pin" style="left:{x:.2f}%;top:{y:.2f}%">{num}</div>'
    dotmap = build_dotmap(452, 150)
    hero_img = prep_art(hero["art"], 628, 258)
    wide_img = prep_art(wide["art"], 196, 100)
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="topbar"><span>{d["paper"]} — DAILY NEWS IN ONE IMAGE</span><span>{d["tagline"]}</span></div>
<div class="masthead">
  <div class="dateline">{d["date_line"]}</div>
  <div class="deck">{d["deck"]}</div>
</div>
<div class="stats">{stats}</div>
<div class="regions">{regions} &nbsp;·&nbsp; <b>{d["total_stories"]} STORIES</b></div>
<div class="main">
  <div class="hero">
    <div class="artwrap hero-art"><img src="art/{hero_img}"/>{kick(hero["num"], hero["kicker"])}{chip(hero["certainty"])}</div>
    <div class="hhead">{hero["headline"]}</div>
    <div class="hsum">{hero["summary"]}</div>
    <div class="src">{hero["source"]}</div>
  </div>
  <div class="rail">{rail}</div>
</div>
<div class="leads2">
  <div class="wide">
    <div class="artwrap wide-art"><img src="art/{wide_img}"/>{kick(wide["num"], wide["kicker"])}</div>
    <div class="wtext"><div class="whead">{wide["headline"]} {chip(wide["certainty"])}</div>
    <div class="wsum">{wide["summary"]}</div><div class="src">{wide["source"]}</div></div>
  </div>
  {tleads}
</div>
<div class="strip">{strip}</div>
<div class="bottom">
  <div class="mapbox">
    <div class="boxtitle">WHERE IT HAPPENED — THE DAY ON THE MAP</div>
    <div class="mapwrap"><img src="{dotmap}"/>{pin_html}</div>
  </div>
  <div class="briefbox">
    <div class="boxtitle">THE REST OF THE DAY — IN BRIEF</div>
    <div class="briefs">{briefs}</div>
    <div class="ovftitle">ALSO ON WEDNESDAY 25 NOV — 24 MORE STORIES</div>
    <div class="ovfcols">{overflow}</div>
  </div>
</div>
<div class="datecheck"><b>DATE CHECK</b> &nbsp;{d["date_check"]}</div>
<div class="timeline"><span class="tlabel">THE DAY IN UTC</span> {timeline}</div>
<div class="footer"><span>Sources: {d["sources_line"]}</span>
<span class="legend">{chip("CONFIRMED")} as reported &nbsp;{chip("REPORTED")} single-source &nbsp;{chip("CLAIM")} one side's claim &nbsp;{chip("FORECAST")} still to happen</span></div>
</body></html>'''

CSS = """
@page { size: 1024px 1024px; margin: 0; }
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1024px; height:1024px; overflow:hidden; background:#f5edd8; color:#17181c;
  font-family:'Noto Serif', serif; display:flex; flex-direction:column; }
.topbar { height:22px; background:#17181c; color:#f5edd8; display:flex; justify-content:space-between;
  align-items:center; padding:0 14px; font-family:'Noto Sans'; font-size:9.5px; letter-spacing:2.2px; }
.masthead { height:96px; text-align:center; padding-top:6px; border-bottom:3px double #17181c; overflow:hidden; }
.dateline { font-weight:900; font-size:44px; letter-spacing:.2px; line-height:1.04; }
.deck { color:#b3231b; font-style:italic; font-size:14.8px; margin-top:5px; padding:0 46px; line-height:1.22; }
.stats { height:57px; display:flex; border-bottom:1.5px solid #17181c; padding:5px 8px 3px; }
.stat { flex:1; text-align:center; padding:0 6px; border-right:1px solid #c9bc96; }
.stat:last-child { border-right:none; }
.snum { font-weight:900; font-size:25px; line-height:1; }
.slab { font-family:'Noto Sans'; font-size:8.3px; letter-spacing:.4px; text-transform:uppercase;
  color:#4c4433; margin-top:3px; line-height:1.3; }
.regions { height:24px; background:#17181c; color:#f5edd8; font-family:'Noto Sans'; font-size:10.5px;
  letter-spacing:1.6px; display:flex; align-items:center; justify-content:center; }
.regions b { color:#e8b64c; }
.main { height:332px; display:flex; padding:10px 14px 4px; gap:14px; overflow:hidden; }
.hero { width:628px; overflow:hidden; }
.artwrap { position:relative; }
.artwrap img { display:block; width:100%; height:100%; object-fit:cover; }
.hero-art { height:202px; }
.hero-art img { height:202px; }
.kick { position:absolute; top:0; left:0; background:#b3231b; color:#fff; font-family:'Noto Sans';
  font-size:10px; font-weight:700; letter-spacing:1.4px; padding:4px 8px 4px 4px; display:flex; gap:6px; align-items:center; }
.kick.sm { font-size:8px; letter-spacing:1px; padding:2px 6px 2px 3px; gap:4px; }
.knum { background:#17181c; color:#f5edd8; font-size:10px; font-weight:900; padding:1px 5px; }
.kick.sm .knum { font-size:8px; padding:1px 4px; }
.cert { position:absolute; top:0; right:0; font-family:'Noto Sans'; font-size:8.5px; font-weight:900;
  letter-spacing:1px; padding:4px 7px; }
.cert.sm { font-size:7px; padding:2px 5px; letter-spacing:.6px; }
.c-confirmed { background:#17181c; color:#f5edd8; }
.c-reported { background:#46586a; color:#fff; }
.c-claim { background:#b3231b; color:#fff; }
.c-forecast { background:#f5edd8; color:#17181c; border:1.5px solid #17181c; }
.hhead { font-weight:900; font-size:26px; line-height:1.1; margin-top:8px; }
.hsum { font-size:12.2px; line-height:1.34; margin-top:5px; color:#26241f; }
.src { font-family:'Noto Sans'; font-size:8.5px; letter-spacing:1.2px; color:#7a6c4d; margin-top:2px; }
.rail { width:352px; display:flex; flex-direction:column; gap:8px; overflow:hidden; }
.railcard { overflow:hidden; }
.rail-art { height:78px; }
.rail-art img { height:78px; }
.rhead { font-weight:700; font-size:14.5px; line-height:1.18; margin-top:5px; }
.rsum { font-size:10px; line-height:1.28; color:#26241f; margin-top:2px; }
.leads2 { height:106px; display:flex; gap:14px; padding:2px 14px 0; border-top:1.5px solid #17181c; margin:0 0; padding-top:7px; overflow:hidden; }
.wide { width:500px; display:flex; gap:10px; }
.wide-art { width:196px; height:84px; flex:none; }
.wide-art img { width:196px; height:84px; }
.wtext { }
.whead { font-weight:700; font-size:15px; line-height:1.18; }
.whead .cert { position:static; margin-left:4px; }
.wsum { font-size:10px; line-height:1.28; color:#26241f; margin-top:3px; }
.tlead { flex:1; border-left:1px solid #c9bc96; padding-left:12px; overflow:hidden; }
.tkick { font-family:'Noto Sans'; font-size:9.5px; font-weight:700; letter-spacing:1.2px; color:#b3231b;
  display:flex; gap:6px; align-items:center; }
.tkick .cert { position:static; }
.tkick .knum { background:#b3231b; color:#fff; }
.thead { font-weight:700; font-size:15px; line-height:1.16; margin-top:4px; }
.tsum { font-size:10px; line-height:1.24; color:#26241f; margin-top:3px; }
.strip { height:98px; display:flex; gap:10px; padding:4px 14px 0; border-top:1.5px solid #17181c; margin-top:5px; overflow:hidden; }
.scard { flex:1; overflow:hidden; }
.strip-art { height:52px; }
.strip-art img { height:52px; }
.shead { font-weight:700; font-size:11.5px; line-height:1.15; margin-top:3px; }
.ssrc { font-family:'Noto Sans'; font-size:7.5px; letter-spacing:.8px; color:#7a6c4d; margin-top:1px; }
.bottom { height:212px; display:flex; gap:14px; padding:7px 14px 4px; border-top:3px double #17181c; margin-top:5px; overflow:hidden; }
.boxtitle { font-family:'Noto Sans'; font-size:9.5px; font-weight:900; letter-spacing:1.8px; margin-bottom:4px; }
.mapbox { width:452px; }
.mapwrap { position:relative; width:452px; height:150px; background:#ece1c6; border:1px solid #b8a87e; }
.mapwrap img { width:452px; height:150px; display:block; }
.pin { position:absolute; width:15px; height:15px; border-radius:50%; background:#17181c; color:#f5edd8;
  font-family:'Noto Sans'; font-size:8.5px; font-weight:900; text-align:center; line-height:13px;
  border:1.5px solid #f5edd8; transform:translate(-50%,-50%); }
.briefbox { flex:1; overflow:hidden; }
.briefs { columns:2; column-gap:18px; }
.brief { font-family:'Noto Sans'; font-size:9.0px; line-height:1.2; margin-bottom:1px; break-inside:avoid; }
.brief b { font-weight:700; }
.breg { color:#b3231b; font-weight:900; font-size:8px; letter-spacing:.8px; }
.bsrc { color:#7a6c4d; }
.ovftitle { font-family:'Noto Sans'; font-size:8.5px; font-weight:900; letter-spacing:1.4px; margin:5px 0 2px; border-top:1px solid #c9bc96; padding-top:3px; }
.ovfcols { columns:3; column-gap:8px; }
.ovf { font-family:'Noto Sans'; font-size:8px; line-height:1.2; margin-bottom:0; break-inside:avoid; white-space:nowrap; overflow:hidden; }
.onum { font-weight:900; color:#b3231b; }
.oreg { font-weight:900; color:#46586a; font-size:7px; }
.datecheck { height:30px; margin:2px 14px 0; background:#b3231b; color:#fff;
  font-family:'Noto Sans'; font-size:10.5px; font-weight:700; display:flex; align-items:center; padding:0 9px;
  white-space:nowrap; overflow:hidden; }
.datecheck b { color:#fff; letter-spacing:1.2px; }
.timeline { height:26px; margin:5px 14px 0; border-top:1.5px solid #17181c; padding-top:2px;
  font-family:'Noto Sans'; font-size:9px; line-height:1.3; overflow:hidden; }
.tlabel { font-weight:900; letter-spacing:1.6px; margin-right:6px; }
.titem b { color:#b3231b; }
.tsep { color:#b8a87e; }
.footer { height:21px; margin-top:auto; background:#17181c; color:#f5edd8; display:flex;
  justify-content:space-between; align-items:center; padding:0 14px; font-family:'Noto Sans'; font-size:9px; letter-spacing:.6px; }
.footer .cert { position:static; padding:1px 5px; font-size:7.5px; }
"""

def main():
    stories_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "stories-test.json"
    out_name = sys.argv[2] if len(sys.argv) > 2 else "entry-test.png"
    d = json.loads(stories_path.read_text())
    html = build_html(d)
    (BUILD / "page.html").write_text(html)
    from weasyprint import HTML
    pdf = BUILD / "page.pdf"
    HTML(filename=str(BUILD / "page.html"), base_url=str(BUILD)).write_pdf(str(pdf))
    import fitz
    doc = fitz.open(str(pdf))
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    im = im.resize((1024, 1024), Image.LANCZOS)
    import os
    out = HERE / out_name
    im.save(out, format="JPEG", quality=int(os.environ.get("MF_JPEG_Q", "88")), optimize=True)
    thumb = HERE / "thumb256.png"
    im.resize((256, 256), Image.LANCZOS).save(thumb)
    print(f"page: {im.size[0]}x{im.size[1]}  bytes: {out.stat().st_size} (cap 1048576)")
    print(f"wrote {out} and {thumb}")

if __name__ == "__main__":
    main()
