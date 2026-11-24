"""Generate the NIDAN logo asset kit (SVG)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lockup import build, svg
from nidantype import signal_n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, "logo")
os.makedirs(LOGO, exist_ok=True)

NAVY = "#0B2545"
TEAL = "#0E8F86"
PAPER = "#F7FAFC"
WHITE = "#FFFFFF"
TEAL_B = "#2DD4BF"

def write(name, body, W, H, bg=None):
    with open(os.path.join(LOGO, name + ".svg"), "w", encoding="utf-8") as f:
        f.write(svg(body, W, H, bg))

S = 120

# Primary: integrated wordmark + centered Devanagari
write("nidan-logo-primary",
      *build(size=S, tracking=0.06, deva=0.38, deva_color=NAVY,
             deva_align="center", pad=36, uid="primary"))
write("nidan-logo-primary-dark",
      *build(size=S, tracking=0.06, deva=0.38, deva_color=PAPER,
             deva_align="center", stem=PAPER, signal=TEAL_B, pad=36, uid="primary-dark"))

# Horizontal, no Devanagari
write("nidan-logo-horizontal",
      *build(size=S, tracking=0.06, pad=36, uid="horiz"))
write("nidan-logo-horizontal-dark",
      *build(size=S, tracking=0.06, stem=PAPER, signal=TEAL_B, pad=36, uid="horiz-dark"))

# Tight horizontal for constrained UI headers (small optical padding)
write("nidan-logo-ui",
      *build(size=S, tracking=0.06, pad=12, uid="ui"))
write("nidan-logo-ui-dark",
      *build(size=S, tracking=0.06, stem=PAPER, signal=TEAL_B, pad=12, uid="ui-dark"))

# Institutional with descriptor
write("nidan-logo-institutional",
      *build(size=S, tracking=0.06, deva=0.38, deva_color=NAVY, deva_align="center",
             descriptor="TRACK CIRCUIT INTELLIGENCE", pad=36, uid="inst"))

# Vertical crest
write("nidan-logo-vertical",
      *build(size=S, tracking=0.06, layout="vertical", deva=0.36, pad=36, uid="vert"))
write("nidan-logo-vertical-dark",
      *build(size=S, tracking=0.06, layout="vertical", deva=0.36, stem=PAPER,
             signal=TEAL_B, deva_color=PAPER, pad=36, uid="vert-dark"))

# Mono
write("nidan-logo-mono",
      *build(size=S, tracking=0.06, deva=0.38, deva_color=NAVY, deva_align="center",
             stem=NAVY, signal=NAVY, pad=36, uid="mono"))
write("nidan-logo-mono-tint",
      *build(size=S, tracking=0.06, deva=0.38, deva_color=NAVY, deva_align="center",
             stem=NAVY, signal="#7C8B9B", pad=36, uid="monotint"))

# Wordmark only
write("nidan-wordmark",
      *build(size=S, tracking=0.06, stem=NAVY, signal=NAVY, pad=30, uid="wm"))

# Mark only
def mark_only(size, stem, signal, pad_ratio=0.10, uid="m"):
    n, g = signal_n(size, stem, signal, 0, uid)
    x0, y0, x1, y1 = g["bbox"]
    pad = pad_ratio * size
    W = (x1 - x0) + pad * 2
    H = (y1 - y0) + pad * 2
    body = f'<g transform="translate({pad - x0:.2f} {pad - y0:.2f})">{n}</g>'
    return body, W, H

write("nidan-mark", *mark_only(120, NAVY, TEAL, 0.10, "mark"))
write("nidan-mark-dark", *mark_only(120, PAPER, TEAL_B, 0.10, "mark-dark"))
write("nidan-mark-mono", *mark_only(120, NAVY, NAVY, 0.10, "mark-mono"))

# App icon
def app_icon(px=512, bg=NAVY, stem=WHITE, signal=TEAL_B, inset=0.545, rx=0.225, uid="app"):
    S = px * inset / 0.580
    n, g = signal_n(S, stem, signal, 0, uid)
    x0, y0, x1, y1 = g["bbox"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    body = (f'<rect width="{px}" height="{px}" rx="{px*rx:.1f}" fill="{bg}"/>'
            f'<g transform="translate({px/2 - cx:.2f} {px/2 - cy:.2f})">{n}</g>')
    return body, px, px

write("nidan-app-icon", *app_icon(512, uid="app"))
write("nidan-app-icon-compact", *app_icon(512, inset=0.60, uid="appc"))

# Favicon
def favicon(px=64):
    S = px * 0.68 / 0.580
    n, g = signal_n(S, WHITE, TEAL_B, 0, "fav")
    x0, y0, x1, y1 = g["bbox"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    body = (f'<rect width="{px}" height="{px}" rx="{px*0.22:.1f}" fill="{NAVY}"/>'
            f'<g transform="translate({px/2 - cx:.2f} {px/2 - cy:.2f})">{n}</g>')
    return body, px, px

write("nidan-favicon", *favicon(64))
print("wrote", LOGO)
