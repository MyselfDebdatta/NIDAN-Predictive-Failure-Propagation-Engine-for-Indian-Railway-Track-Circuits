"""Generate construction layers for the brand sheet: rails + signal = mark."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nidantype import glyph_path, N_EM, signal_n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, "logo")
NAVY = "#0B2545"; TEAL = "#0E8F86"

def layers(size=200, stem=NAVY, signal=TEAL, uid="lay"):
    g = glyph_path("N", size, 600, 100)
    u = size
    s = N_EM
    def yA(x): return s["ay0"] + (s["ay1"] - s["ay0"]) * (x - s["ax0"]) / (s["ax1"] - s["ax0"])
    def yB(x): return s["by0"] + (s["by1"] - s["by0"]) * (x - s["bx0"]) / (s["bx1"] - s["bx0"])
    xl, xr = s["jx0"] * u, s["jx1"] * u
    pad = 0.08 * u
    def fy(v): return -v * u
    poly = (f"M{xl:.2f} {fy(yA(s['jx0'])) - pad:.2f} "
            f"L{xr:.2f} {fy(yA(s['jx1'])) - pad:.2f} "
            f"L{xr:.2f} {fy(yB(s['jx1'])) + pad:.2f} "
            f"L{xl:.2f} {fy(yB(s['jx0'])) + pad:.2f} Z")
    x0, y0, x1, y1 = g["bbox"]
    m = 0.10 * u
    W = (x1 - x0) + 2 * m
    H = (y1 - y0) + 2 * m
    tx, ty = m - x0, m - y0
    rails = (f'<g transform="translate({tx:.2f} {ty:.2f})">'
             f'<defs><mask id="cut-{uid}" maskUnits="userSpaceOnUse" '
             f'x="{-u} " y="{-u}" width="{3*u}" height="{2*u}">'
             f'<rect x="{-u}" y="{-u}" width="{3*u}" height="{2*u}" fill="#fff"/>'
             f'<path d="{poly}" fill="#000"/></mask></defs>'
             f'<g mask="url(#cut-{uid})"><path d="{g["d"]}" fill="{stem}"/></g></g>')
    sig = (f'<g transform="translate({tx:.2f} {ty:.2f})">'
           f'<defs><clipPath id="cl-{uid}"><path d="{g["d"]}"/></clipPath></defs>'
           f'<g clip-path="url(#cl-{uid})"><path d="{poly}" fill="{signal}"/></g></g>')
    return rails, sig, W, H

def svg(body, W, H):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" '
            f'width="{W:.1f}" height="{H:.1f}">{body}</svg>')

rails, sig, W, H = layers(200, NAVY, TEAL, "lay")
open(os.path.join(LOGO, "construction-rails.svg"), "w", encoding="utf-8").write(svg(rails, W, H))
open(os.path.join(LOGO, "construction-signal.svg"), "w", encoding="utf-8").write(svg(sig, W, H))

full, g = signal_n(200, NAVY, TEAL, 0, "full")
x0, y0, x1, y1 = g["bbox"]; m = 20
W2 = (x1 - x0) + 2 * m; H2 = (y1 - y0) + 2 * m
open(os.path.join(LOGO, "construction-full.svg"), "w", encoding="utf-8").write(
    svg(f'<g transform="translate({m - x0:.2f} {m - y0:.2f})">{full}</g>', W2, H2))
print("layers", W, H)
