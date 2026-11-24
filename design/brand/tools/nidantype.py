"""NIDAN type utilities: HarfBuzz-shaped outlines + a font-matched signal N."""
import os, tempfile
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

FONTS = os.path.join(os.environ["TEMP"], "nidan-fonts")
LATIN = os.path.join(FONTS, "Archivo.ttf")
DEVA = os.path.join(FONTS, "NotoSansDevanagari.ttf")

_cache = {}

def _instantiate(path, weight, width):
    key = (path, weight, width)
    if key in _cache:
        return _cache[key]
    f = TTFont(path)
    if "fvar" in f:
        tags = [a.axisTag for a in f["fvar"].axes]
        axes = {}
        if "wght" in tags: axes["wght"] = weight
        if "wdth" in tags: axes["wdth"] = width
        if axes:
            f = instantiateVariableFont(f, axes, inplace=False)
    _cache[key] = f
    return f

def shape(text, size, weight=600, width=100, tracking=0.0,
          font=LATIN, features=None):
    """Shape text and return path d, advance width, and ink bbox (x0,y0,x1,y1)."""
    f = _instantiate(font, weight, width)
    tmp = os.path.join(tempfile.gettempdir(),
                       f"nidan-{os.path.basename(font)}-{weight}-{width}.ttf")
    if not os.path.exists(tmp):
        f.save(tmp)
    face = hb.Face(open(tmp, "rb").read())
    hbf = hb.Font(face)
    upem = face.upem
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbf, buf, features or {})
    scale = size / upem
    track = tracking * size
    seen, nclusters = set(), len(set(i.cluster for i in buf.glyph_infos))
    pen = 0.0
    parts, bnds = [], []
    order = f.getGlyphOrder()
    gs = f.getGlyphSet()
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = order[info.codepoint]
        sp = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
        gs[g].draw(TransformPen(sp, Transform(scale, 0, 0, -scale,
                 pen + pos.x_offset * scale, -pos.y_offset * scale)))
        d = sp.getCommands()
        if d:
            parts.append(d)
        bp = BoundsPen(gs)
        gs[g].draw(TransformPen(bp, Transform(scale, 0, 0, -scale,
                 pen + pos.x_offset * scale, -pos.y_offset * scale)))
        if bp.bounds:
            bnds.append(bp.bounds)
        pen += pos.x_advance * scale
        if info.cluster not in seen:
            seen.add(info.cluster)
            if len(seen) < nclusters:
                pen += track
    if bnds:
        bbox = (min(b[0] for b in bnds), min(b[1] for b in bnds),
                max(b[2] for b in bnds), max(b[3] for b in bnds))
    else:
        bbox = (0, 0, 0, 0)
    return {"d": " ".join(parts), "advance": pen, "bbox": bbox}

def glyph_path(ch, size, weight=600, width=100, font=LATIN):
    f = _instantiate(font, weight, width)
    gs = f.getGlyphSet()
    name = f.getBestCmap()[ord(ch)]
    upem = f["head"].unitsPerEm
    scale = size / upem
    sp = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
    gs[name].draw(TransformPen(sp, Transform(scale, 0, 0, -scale, 0, 0)))
    bp = BoundsPen(gs)
    gs[name].draw(TransformPen(bp, Transform(scale, 0, 0, -scale, 0, 0)))
    return {"d": sp.getCommands(), "bbox": bp.bounds,
            "advance": f["hmtx"][name][0] * scale,
            "cap": f["OS/2"].sCapHeight * scale}

# Archivo 600 N geometry in em units (from the font):
# ink x 0.076..0.656, y 0..0.686; stems 0.125; diagonal band between
# edge A (0.200,0.686)->(0.493,0.281) and edge B (0.239,0.408)->(0.533,0.000)
N_EM = dict(x0=0.076, x1=0.656, cap=0.686, stem=0.125,
            jx0=0.201, jx1=0.531,
            ay0=0.686, ay1=0.281, ax0=0.200, ax1=0.493,
            by0=0.408, by1=0.000, bx0=0.239, bx1=0.533)

def signal_n(size, stem="#0B2545", signal="#0F766E", gap=0.0, uid="n",
             weight=600, width=100):
    """Archivo's N with its diagonal rendered as the diagnostic signal.
    gap is in em units (0 disables the insulated channel)."""
    g = glyph_path("N", size, weight, width)
    u = size  # em
    s = N_EM
    # diagonal polygon clipped to x in [jx0, jx1]
    def yA(x): return s["ay0"] + (s["ay1"] - s["ay0"]) * (x - s["ax0"]) / (s["ax1"] - s["ax0"])
    def yB(x): return s["by0"] + (s["by1"] - s["by0"]) * (x - s["bx0"]) / (s["bx1"] - s["bx0"])
    xl, xr = s["jx0"] * u, s["jx1"] * u
    # extend past the cap so the channel exits the silhouette cleanly
    yA_l, yA_r = yA(s["jx0"]) * u, yA(s["jx1"]) * u
    yB_l, yB_r = yB(s["jx0"]) * u, yB(s["jx1"]) * u
    pad = 0.06 * u
    poly = (f"M{xl:.2f} {yA_l - pad:.2f} L{xr:.2f} {yA_r - pad:.2f} "
            f"L{xr:.2f} {yB_r + pad:.2f} L{xl:.2f} {yB_l + pad:.2f} Z")
    # note y grows downward in SVG; font y=0 is baseline, cap is negative.
    def fy(v): return -v * u
    yA_l, yA_r = fy(yA(s["jx0"])), fy(yA(s["jx1"]))
    yB_l, yB_r = fy(yB(s["jx0"])), fy(yB(s["jx1"]))
    poly = (f"M{xl:.2f} {yA_l - pad:.2f} L{xr:.2f} {yA_r - pad:.2f} "
            f"L{xr:.2f} {yB_r + pad:.2f} L{xl:.2f} {yB_l + pad:.2f} Z")
    gp = f'<clipPath id="clip-{uid}"><path d="{g["d"]}"/></clipPath>'
    if gap > 0:
        mask = (f'<mask id="msk-{uid}" maskUnits="userSpaceOnUse" '
                f'x="{-u:.0f}" y="{-u:.0f}" width="{2*u:.0f}" height="{2*u:.0f}">'
                f'<rect x="{-u:.0f}" y="{-u:.0f}" width="{2*u:.0f}" height="{2*u:.0f}" fill="#fff"/>'
                f'<path d="{poly}" fill="none" stroke="#000" stroke-width="{2*gap*u:.2f}" '
                f'stroke-linejoin="round"/></mask>')
        navy = f'<g mask="url(#msk-{uid})"><path d="{g["d"]}" fill="{stem}"/></g>'
    else:
        mask = ""
        navy = f'<path d="{g["d"]}" fill="{stem}"/>'
    teal = f'<g clip-path="url(#clip-{uid})"><path d="{poly}" fill="{signal}"/></g>'
    return f'<defs>{gp}{mask}</defs>{navy}{teal}', g
