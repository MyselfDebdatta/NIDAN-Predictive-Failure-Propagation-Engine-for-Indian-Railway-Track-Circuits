import os
from fontTools.ttLib import TTFont

SRC = os.path.join(os.environ["TEMP"], "nidan-fonts")
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
os.makedirs(DST, exist_ok=True)

for src, out in (("Archivo.ttf", "Archivo.woff2"),
                 ("Inter.ttf", "Inter.woff2"),
                 ("NotoSansDevanagari.ttf", "NotoSansDevanagari.woff2"),
                 ("JetBrainsMono.ttf", "JetBrainsMono.woff2")):
    f = TTFont(os.path.join(SRC, src))
    f.flavor = "woff2"
    f.save(os.path.join(DST, out))
    print(out, os.path.getsize(os.path.join(DST, out)) // 1024, "KB")
