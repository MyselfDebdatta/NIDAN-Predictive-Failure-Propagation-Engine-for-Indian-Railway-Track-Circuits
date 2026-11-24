"""Headless Chrome screenshot helper.
Usage: python shot.py <html> <png> [width] [height] [scale]
"""
import os, subprocess, sys, pathlib

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def shot(html, png, w=1600, h=1200, scale=1, extra=None):
    html = pathlib.Path(html).resolve()
    png = pathlib.Path(png).resolve()
    png.parent.mkdir(parents=True, exist_ok=True)
    url = html.as_uri()
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--no-first-run", "--no-default-browser-check",
           f"--force-device-scale-factor={scale}",
           f"--window-size={w},{h}",
           "--virtual-time-budget=4000",
           f"--screenshot={png}", url]
    if extra:
        cmd[1:1] = extra
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not png.exists():
        print(r.stdout, r.stderr)
        raise SystemExit("screenshot failed")
    print(f"{png}  {png.stat().st_size//1024} KB")

if __name__ == "__main__":
    a = sys.argv[1:]
    shot(a[0], a[1], *(int(x) for x in a[2:]))
