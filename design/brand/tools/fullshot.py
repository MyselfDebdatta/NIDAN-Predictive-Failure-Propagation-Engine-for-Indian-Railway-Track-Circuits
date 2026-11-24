"""Full-page screenshot via Chrome DevTools Protocol."""
import base64, json, os, pathlib, subprocess, sys, tempfile, time
import urllib.request
import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333

def fullshot(html, png, width=1440, scale=1):
    html = pathlib.Path(html).resolve()
    png = pathlib.Path(png).resolve()
    png.parent.mkdir(parents=True, exist_ok=True)
    profile = tempfile.mkdtemp(prefix="nidan-cdp-")
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
        else:
            raise SystemExit("chrome did not start")
        ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=30)
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
        send("Emulation.setDeviceMetricsOverride",
             {"width": width, "height": 1200, "deviceScaleFactor": scale, "mobile": False})
        send("Page.navigate", {"url": html.as_uri()})
        # wait for load + fonts
        deadline = time.time() + 25
        while time.time() < deadline:
            r = send("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
            if r.get("result", {}).get("value") == "complete":
                break
            time.sleep(0.2)
        send("Runtime.evaluate", {"expression": "document.fonts.ready", "awaitPromise": True})
        time.sleep(0.4)
        h = send("Runtime.evaluate", {
            "expression": "Math.ceil(Math.max(document.body.scrollHeight,document.documentElement.scrollHeight))",
            "returnByValue": True})["result"]["value"]
        send("Emulation.setDeviceMetricsOverride",
             {"width": width, "height": int(h), "deviceScaleFactor": scale, "mobile": False})
        time.sleep(0.3)
        shot = send("Page.captureScreenshot",
                    {"format": "png", "captureBeyondViewport": True, "fromSurface": True})
        png.write_bytes(base64.b64decode(shot["data"]))
        print(f"{png}  {png.stat().st_size//1024} KB  {width}x{int(h)} @{scale}x")
    finally:
        try:
            ws.close()
        except Exception:
            pass
        proc.terminate()

if __name__ == "__main__":
    a = sys.argv[1:]
    fullshot(a[0], a[1], int(a[2]) if len(a) > 2 else 1440,
             float(a[3]) if len(a) > 3 else 1)
