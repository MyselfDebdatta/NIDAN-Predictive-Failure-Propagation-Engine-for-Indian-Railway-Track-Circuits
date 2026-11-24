"""Rasterise the SVG asset kit to transparent PNGs at production sizes."""
import base64, json, os, pathlib, re, subprocess, sys, tempfile, time
import urllib.request
import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9335

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGO = ROOT / "logo"
OUT = ROOT / "png"

# name, target width in px
JOBS = [
    ("nidan-logo-primary", 2400),
    ("nidan-logo-primary-dark", 2400),
    ("nidan-logo-institutional", 2400),
    ("nidan-logo-vertical", 1400),
    ("nidan-logo-vertical-dark", 1400),
    ("nidan-logo-horizontal", 2000),
    ("nidan-logo-horizontal-dark", 2000),
    ("nidan-wordmark", 2000),
    ("nidan-logo-mono", 2400),
    ("nidan-logo-mono-tint", 2400),
    ("nidan-mark", 1024),
    ("nidan-mark-dark", 1024),
    ("nidan-mark-mono", 1024),
    ("nidan-app-icon", 1024),
    ("nidan-app-icon-compact", 1024),
]

ICON_SIZES = [512, 256, 180, 128, 64, 48, 32, 16]


def svg_size(path):
    head = path.read_text(encoding="utf-8")[:600]
    w = float(re.search(r'width="([\d.]+)"', head).group(1))
    h = float(re.search(r'height="([\d.]+)"', head).group(1))
    return w, h


def main():
    OUT.mkdir(exist_ok=True)
    profile = tempfile.mkdtemp(prefix="nidan-raster-")
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check",
        f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
        "about:blank"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                data = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=1))
                pages = [t for t in data if t.get("type") == "page"]
                if pages:
                    break
            except Exception:
                pass
            time.sleep(0.15)
        ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
        mid = [0]

        def send(method, params=None):
            mid[0] += 1
            ws.send(json.dumps({"id": mid[0], "method": method, "params": params or {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid[0]:
                    if "error" in msg:
                        raise RuntimeError(msg["error"])
                    return msg.get("result", {})

        send("Page.enable")
        send("Emulation.setDefaultBackgroundColorOverride",
             {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})

        def shoot(svg, width, out):
            sw, sh = svg_size(svg)
            height = round(width * sh / sw)
            html = (f'<!doctype html><style>html,body{{margin:0;background:transparent}}'
                    f'img{{display:block;width:{width}px;height:{height}px}}</style>'
                    f'<img src="{svg.as_uri()}">')
            tmp = pathlib.Path(tempfile.gettempdir()) / "nidan-raster.html"
            tmp.write_text(html, encoding="utf-8")
            send("Emulation.setDeviceMetricsOverride",
                 {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
            send("Page.navigate", {"url": tmp.as_uri()})
            deadline = time.time() + 20
            while time.time() < deadline:
                r = send("Runtime.evaluate", {"expression": "document.readyState",
                                              "returnByValue": True})
                if r.get("result", {}).get("value") == "complete":
                    break
                time.sleep(0.15)
            time.sleep(0.35)
            shot = send("Page.captureScreenshot",
                        {"format": "png", "captureBeyondViewport": True, "fromSurface": True})
            out.write_bytes(base64.b64decode(shot["data"]))
            print(f"{out.name:44s} {width}x{height}  {out.stat().st_size//1024} KB")

        for name, width in JOBS:
            shoot(LOGO / (name + ".svg"), width, OUT / (name + ".png"))

        fav = LOGO / "nidan-favicon.svg"
        for px in ICON_SIZES:
            shoot(fav, px, OUT / f"nidan-favicon-{px}.png")
        shoot(LOGO / "nidan-app-icon.svg", 512, OUT / "nidan-app-icon-512.png")
        shoot(LOGO / "nidan-app-icon.svg", 192, OUT / "nidan-app-icon-192.png")
        shoot(LOGO / "nidan-app-icon.svg", 64, OUT / "nidan-app-icon-64.png")
    finally:
        try:
            ws.close()
        except Exception:
            pass
        proc.terminate()


if __name__ == "__main__":
    main()
