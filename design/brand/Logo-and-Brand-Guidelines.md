# NIDAN — Logo and Brand Guidelines

**Version 1.0 · November 2026**
Applies to every NIDAN surface: pitch decks, government and PSU documents, letterheads, signage, the web and the field tablet.

The visual identity is intentionally narrow. Its restraint is what makes the same mark credible in a divisional office, an OEM review and a seed round.

---

## 1. The idea

Every track circuit is two rails and a current running between them. NIDAN adds nothing to the track — it listens to what the circuit already carries. The mark is built from exactly those three elements, and it is drawn from the letterform of the name itself:

> **Two rails (the N stems) + one diagnostic signal (the diagonal) = the first N of NIDAN.**

The diagonal is teal because it is the *live signal*, not a control. There are no arrows, switches, toggles or green-for-go semantics anywhere in the identity. NIDAN is an instrument: advisory, read-only and non-vital.

The shape is therefore not a badge placed next to a wordmark. It **is** the wordmark's first letter, split into rails and a signal. A separate "N + NIDAN" lockup would repeat the letter and was rejected during development.

---

## 2. Construction

The mark is the capital `N` of **Archivo 600, width 100**, with the diagonal replaced by a clipped polygon of the signal colour. No part is redrawn freehand, so the mark and the wordmark share one geometry.

Archivo 600 `N` metrics, in em units (1000 upem):

| Element | Value |
|---|---|
| Ink bounds | x 76 → 656; cap height 686 |
| Stem width | 125 |
| Advance | 732 |
| Diagonal band, edge A | (200, 686) → (493, 281) |
| Diagonal band, edge B | (239, 408) → (533, 0) |
| Signal clip range | x 201 → 531 |

The diagonal polygon is extended 0.06 em past the cap and clipped back to the letter, so the signal exits the silhouette cleanly. There is no gap around it: transparent "insulated channel" variants were tested at 0.010–0.018 em and all read as misregistration or a broken letter at small sizes.

Wordmark: `NIDAN`, Archivo 600 / 100, letter-spacing `0.06 em`. The first character is the signal N; `IDAN` is set from the same font.

Devanagari: `निदान`, Noto Sans Devanagari 500, set at `0.38 ×` the Latin size and centred beneath the wordmark, optically aligned and shaped with HarfBuzz (the shirorekha must be intact). At size 100 its ink box is roughly `(0, −89.6, 223.8, 6.6)`.

A three-layer construction sheet is provided:
`design/brand/logo/construction-rails.svg`, `construction-signal.svg`, `construction-full.svg`.

---

## 3. Colour

| Name | Hex | RGB | Role |
|---|---|---|---|
| Ink | `#0A121A` | 10 18 26 | Control-room ground, darkest surface |
| Navy | `#0B2545` | 11 37 69 | Primary brand, stems, wordmark, headings |
| Signal Teal | `#0E8F86` | 14 143 134 | The diagonal, live data, graphics on light |
| Bright Teal | `#2DD4BF` | 45 212 191 | Signal on dark surfaces only |
| Deep Teal | `#0B6B63` | 11 107 99 | Small teal text on light (6.1:1) |
| Gold | `#C8922F` | 200 146 47 | Caution and precedent; never decoration |
| Paper | `#F7FAFC` | 247 250 252 | Light ground, reversed lockups |
| Slate | `#5B7288` | 91 114 136 | Secondary text, descriptors |

Suggested coverage on presentation surfaces: **60 % navy/ink · 30 % paper · 10 % signal**.

Measured contrast ratios (WCAG):

| Pair | Ratio | Permitted use |
|---|---|---|
| Navy on Paper | 14.7 : 1 | Body, wordmark, headings |
| White on Navy | 15.4 : 1 | Dark lockups, signage |
| Paper on Ink | 18.0 : 1 | Control-room UI |
| Bright Teal on Navy | 8.3 : 1 | Signal on dark |
| Deep Teal on Paper | 6.1 : 1 | Small teal text |
| Signal Teal on Paper | 3.8 : 1 | **Graphics only** — not body text |

Red is reserved for the Critical state in the product. It never appears in the identity. Do not recolor the diagonal green or substitute a gradient.

---

## 4. Typography

| Face | Role |
|---|---|
| **Archivo** 600 / width 100 | Display, wordmark, the N geometry |
| **Inter** | Interface and body |
| **Noto Sans Devanagari** 500 | Hindi, always shaped with HarfBuzz |
| **JetBrains Mono** | Telemetry, identifiers, captions, numbers |

Type scale for decks and documents: Display 44/46 · H1 30/36 · H2 21/27 · Body 15/25 · Caption 10/14 (mono, uppercase, `0.1 em` tracking).

All delivered artwork is **outlined**. No font needs to be installed to use the SVG or PNG files; do not retype the wordmark.

---

## 5. Lockups

| Variant | File | Use |
|---|---|---|
| **Primary (light)** | `nidan-logo-primary.svg` | Default. Light grounds, decks, letters. |
| **Primary (dark)** | `nidan-logo-primary-dark.svg` | Dark grounds, badges, signage, inverted decks. |
| **Institutional** | `nidan-logo-institutional.svg` | Title pages and formal documents; adds `TRACK CIRCUIT INTELLIGENCE`. |
| **Vertical crest** | `nidan-logo-vertical.svg` | Square media, plaques, certificates, badges. |
| **Horizontal** | `nidan-logo-horizontal.svg` | Interface headers and height-constrained slots. |
| **UI (tight)** | `nidan-logo-ui.svg` | Product headers; reduced optical padding. |
| **Wordmark** | `nidan-wordmark.svg` | Where the mark is already present nearby. |
| **Mark** | `nidan-mark.svg` | Watermarks, patterns, avatars, favicon sources. |
| **Mono** | `nidan-logo-mono.svg` | One-colour print, engraving, embroidery, fax-grade copies. |
| **Mono tint** | `nidan-logo-mono-tint.svg` | One-colour print where a 45 % tint is available. |
| **App icon** | `nidan-app-icon.svg` | Store listing and home screen. The only asset with a filled ground. |
| **Favicon** | `nidan-favicon.svg` | 16–64 px browser icon; heavier N for legibility. |

Use the descriptor only on the institutional variant. Never add it to the primary or horizontal lockups.

---

## 6. Clear space and minimum sizes

**Clear space.** Let `x` be the cap height of the N.
- Mark: clear space on all sides = `0.5 × x`.
- Lockups: clear space on all sides = `1 × x`.
- The app icon is self-contained; keep one icon-width of surrounding space in layouts.

**Minimum sizes** (reproduced and visually checked in `design/brand/contact-sheet.png`):

| Asset | Digital | Print |
|---|---|---|
| Mark | 16 px | 10 mm |
| Primary / institutional lockup | 160 px wide | 30 mm wide |
| Horizontal / UI lockup | 120 px wide | 22 mm wide |
| App icon | 32 px | 12 mm |
| Favicon | 16 px | — |

Below 160 px, use the horizontal lockup; the Devanagari in the primary lockup becomes too small. Below 16 px, use the favicon.

---

## 7. Bilingual rules

1. `निदान` is the same name, not a translation or a tagline. Set it at 38 % of the Latin size, centred, never stretched to match the wordmark width.
2. Keep the shirorekha clear. Do not run a box, underline or tight rule through it.
3. In body copy, pair **NIDAN** with **निदान** on first mention only; do not repeat it in every heading.
4. In constrained product UI, the horizontal lockup plus a separate 10 px Devanagari line is acceptable — this is how `design/mockups/pages/index.html` and `field-tablet.html` are built.
5. The Devanagari may be navy on light or paper on dark. A teal Devanagari is reserved for digital/social variants; keep teal as a single accent in the primary lockup.

---

## 8. Misuse — do not

- Stretch, condense, rotate, skew or apply perspective to any asset.
- Change the diagonal colour to red, green or a gradient; add shadows, glows, bevels or outlines.
- Put the full lockup inside the app icon or favicon, or place a second mark beside the wordmark.
- Redraw the N in another typeface or retype the wordmark.
- Break the mark into separate rails and signal, add nodes, dots, apertures, ECG pulses or track ties — these were all explored and rejected because they read as defects, bullets or ladders.
- Place the mark on a busy photograph or a low-contrast ground. Use the mono or dark variant instead.
- Use green as a "go" signal, draw switches, or imply a write path to interlocking, signals, routes or track circuits.

---

## 9. Files and regeneration

```
brand/
├─ Logo-and-Brand-Guidelines.md   this document
├─ brand-sheet.html               full visual identity document
├─ brand-sheet.png                full-page render of the above
├─ contact-sheet.html/.png        real-size legibility check
├─ logo/                          final SVG asset kit
├─ png/                           raster exports (transparent)
├─ fonts/                         local WOFF2 faces for the sheets
└─ tools/
   ├─ nidantype.py                HarfBuzz shaping + signal_n()
   ├─ lockup.py                   lockup construction (source of truth)
   ├─ build_assets.py             writes logo/*.svg
   ├─ layers.py                   construction layers
   ├─ rasterize.py                writes png/*.png
   ├─ webfonts.py                 WOFF2 conversion
   └─ fullshot.py / shot.py       headless Chrome capture
```

Regenerate everything, from the project root, with:

```
python brand\tools\build_assets.py
python brand\tools\layers.py
python brand\tools\rasterize.py
python brand\tools\fullshot.py brand\brand-sheet.html brand\brand-sheet.png 1440 1
```

The two Python source tools require `fontTools` and `uharfbuzz`; the fonts they instance live in `%TEMP%\nidan-fonts` (`Archivo.ttf`, `NotoSansDevanagari.ttf`, plus `Inter.ttf` and `JetBrainsMono.ttf` for the sheets). The rendered SVG/PNG assets have no such dependency.

The final mark was also wired into the front-end mockups: `design/mockups/assets/brand/` holds the UI lockups injected into every screen header by `design/mockups/assets/app.js` (and used directly on the cover and field tablet), replacing the earlier placeholder ECG icon.

---

## 10. Governance

NIDAN is advisory and non-vital. Every application of the identity must be consistent with that boundary: it informs, explains and recommends; it never commands. If a proposed use could be read as a safety-critical control or a replacement for the interlocking or the technician, it is not an approved use of the brand.
