"""Capture the README image using the local app and an installed Edge browser."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true",
         "--server.address=127.0.0.1", f"--server.port={port}", "--browser.gatherUsageStats=false"],
        cwd=ROOT, stdout=subprocess.DEVNULL)
    try:
        with sync_playwright() as engine:
            browser = engine.chromium.launch(channel=os.getenv("BROWSER_CHANNEL", "msedge"))
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            for attempt in range(30):
                try:
                    page.goto(f"http://127.0.0.1:{port}")
                    break
                except Exception:
                    if attempt == 29:
                        raise
                    time.sleep(0.5)
            if page.get_by_role("link", name="Schema mapping", exact=True).count():
                page.get_by_role("link", name="Schema mapping", exact=True).click()
            page.get_by_role("heading", name="Schema mapping", exact=True).wait_for()
            page.get_by_text("Export mapping JSON", exact=True).wait_for()
            output = ROOT / "docs/schema-mapping.png"
            output.parent.mkdir(exist_ok=True)
            page.screenshot(path=output)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=15)


if __name__ == "__main__":
    main()
