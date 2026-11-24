"""NIDAN lockup construction: horizontal, stacked-bilingual, vertical."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nidantype import signal_n, shape, DEVA

CAP = 0.686
NAVY = "#0B2545"; TEAL = "#0E8F86"; MUTED = "#5B7288"

def _union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))

def _wordmark(size, tracking, stem, signal, use_mark=True, uid="w",
              weight=600, width=100):
    """Return (frags, bbox, word_left, word_right)."""
    frags, boxes = [], []
    if use_mark:
        n_svg, g = signal_n(size, stem, signal, 0, uid, weight, width)
        frags.append(n_svg)
        boxes.append((0.076 * size, -CAP * size, 0.656 * size, 0))
        x_idan = g["advance"] + tracking * size
        idan = shape("IDAN", size, weight, width, tracking)
        frags.append(f'<g transform="translate({x_idan:.2f} 0)">'
                     f'<path d="{idan["d"]}" fill="{stem}"/></g>')
        boxes.append((x_idan + idan["bbox"][0], idan["bbox"][1],
                      x_idan + idan["bbox"][2], idan["bbox"][3]))
        left = 0.076 * size
        right = x_idan + idan["bbox"][2]
    else:
        wm = shape("NIDAN", size, weight, width, tracking)
        frags.append(f'<path d="{wm["d"]}" fill="{stem}"/>')
        boxes.append(wm["bbox"])
        left, right = wm["bbox"][0], wm["bbox"][2]
    return frags, _union(boxes), left, right

def build(size=120, tracking=0.06, deva=0.0, deva_color=NAVY, deva_align="center",
          descriptor=None, stem=NAVY, signal=TEAL, layout="stack",
          uid="lk", pad=36, weight=600, width=100):
    frags, boxes = [], []

    if layout == "vertical":
        # mark above, wordmark below, then Devanagari / descriptor
        mark_size = size * 2.0
        n_svg, g = signal_n(mark_size, stem, signal, 0, uid + "m", weight, width)
        mb = (0.076 * mark_size, -CAP * mark_size, 0.656 * mark_size, 0)
        wm = shape("NIDAN", size, weight, width, tracking)
        wb = wm["bbox"]
        deva_shape = shape("निदान", size * (deva or 0.34), 500, 100, 0, DEVA) if deva is not False else None
        inner_w = max(mb[2] - mb[0], wb[2] - wb[0],
                      (deva_shape["bbox"][2] - deva_shape["bbox"][0]) if deva_shape else 0)
        cx = inner_w / 2
        # mark
        mx = cx - (mb[0] + mb[2]) / 2
        frags.append(f'<g transform="translate({mx:.2f} 0)">{n_svg}</g>')
        boxes.append((mx + mb[0], mb[1], mx + mb[2], mb[3]))
        # wordmark
        wy = CAP * size + size * 0.30
        wx = cx - (wb[0] + wb[2]) / 2
        frags.append(f'<g transform="translate({wx:.2f} {wy:.2f})">'
                     f'<path d="{wm["d"]}" fill="{stem}"/></g>')
        boxes.append((wx + wb[0], wy + wb[1], wx + wb[2], wy + wb[3]))
        bottom = wy + wb[3]
        if deva_shape:
            db = deva_shape["bbox"]
            dy = bottom + size * 0.10 + (-db[1])
            dx = cx - (db[0] + db[2]) / 2
            frags.append(f'<g transform="translate({dx:.2f} {dy:.2f})">'
                         f'<path d="{deva_shape["d"]}" fill="{deva_color}"/></g>')
            boxes.append((dx + db[0], dy + db[1], dx + db[2], dy + db[3]))
            bottom = dy + db[3]
        if descriptor:
            ds = shape(descriptor, size * 0.145, 500, 100, 0.20)
            sb = ds["bbox"]
            sy = bottom + size * 0.10 + (-sb[1])
            sx = cx - (sb[0] + sb[2]) / 2
            frags.append(f'<g transform="translate({sx:.2f} {sy:.2f})">'
                         f'<path d="{ds["d"]}" fill="{MUTED}"/></g>')
            boxes.append((sx + sb[0], sy + sb[1], sx + sb[2], sy + sb[3]))

    else:
        wf, wb, word_left, word_right = _wordmark(size, tracking, stem, signal,
                                                  True, uid, weight, width)
        frags.extend(wf)
        boxes.append(wb)
        word_w = word_right - word_left
        bottom = 0.0

        if deva:
            D = size * deva
            d = shape("निदान", D, 500, 100, 0, DEVA)
            db = d["bbox"]
            if deva_align == "center":
                dx = word_left + (word_w - (db[2] - db[0])) / 2
            else:
                dx = word_left
            dy = size * 0.12 + (-db[1])
            frags.append(f'<g transform="translate({dx:.2f} {dy:.2f})">'
                         f'<path d="{d["d"]}" fill="{deva_color}"/></g>')
            boxes.append((dx + db[0], dy + db[1], dx + db[2], dy + db[3]))
            bottom = dy + db[3]
            if descriptor:
                ds = shape(descriptor, size * 0.145, 500, 100, 0.20)
                sb = ds["bbox"]
                sy = bottom + size * 0.10 + (-sb[1])
                if deva_align == "center":
                    sx = word_left + (word_w - (sb[2] - sb[0])) / 2
                else:
                    sx = word_left
                frags.append(f'<g transform="translate({sx:.2f} {sy:.2f})">'
                             f'<path d="{ds["d"]}" fill="{MUTED}"/></g>')
                boxes.append((sx + sb[0], sy + sb[1], sx + sb[2], sy + sb[3]))
        elif descriptor:
            ds = shape(descriptor, size * 0.145, 500, 100, 0.20)
            sb = ds["bbox"]
            sy = size * 0.12 + (-sb[1])
            sx = word_left + (word_w - (sb[2] - sb[0])) / 2
            frags.append(f'<g transform="translate({sx:.2f} {sy:.2f})">'
                         f'<path d="{ds["d"]}" fill="{MUTED}"/></g>')
            boxes.append((sx + sb[0], sy + sb[1], sx + sb[2], sy + sb[3]))

    b = _union(boxes)
    W = (b[2] - b[0]) + pad * 2
    H = (b[3] - b[1]) + pad * 2
    body = (f'<g transform="translate({pad - b[0]:.2f} {pad - b[1]:.2f})">'
            + "".join(frags) + "</g>")
    return body, W, H

def svg(body, W, H, bg=None):
    r = f'<rect width="{W:.1f}" height="{H:.1f}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" '
            f'width="{W:.1f}" height="{H:.1f}">{r}{body}</svg>')
