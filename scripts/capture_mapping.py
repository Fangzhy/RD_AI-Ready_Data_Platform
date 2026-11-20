"""Verify the walkthrough and capture the README images using the local app and an installed Edge browser."""
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
            page.get_by_role("heading", name="Schema mapping", exact=True).wait_for()
            output = ROOT / "docs"
            output.mkdir(exist_ok=True)
            page.get_by_text("Export mapping JSON", exact=True).wait_for()
            page.screenshot(path=output/"schema-mapping.png")
            page.get_by_role("button",name="Publish batch to the shared model").click()
            page.get_by_text("Published Alpha batch.",exact=False).wait_for()
            for label, heading in [
                ("Overview","Research data overview"), ("Data modeling studio","Data modeling studio"),
                ("Data quality","Data quality"), ("Metadata and lineage","Metadata and lineage"),
                ("Taxonomy and ontology","Taxonomy and ontology"), ("AI-ready data explorer","AI-ready data explorer"),
                ("RAG assistant","RAG assistant"),
            ]:
                page.get_by_role("link",name=label,exact=True).click()
                page.get_by_role("heading",name=heading,exact=True).wait_for()
                page.locator('[data-testid="stApp"][data-test-script-state="notRunning"]').wait_for()
                if page.locator('[data-testid="stException"]').count():
                    raise RuntimeError(f"{label} rendered a Streamlit exception")
            page.get_by_role("link",name="DOC-A001/v2/Measurement",exact=True).wait_for()
            page.screenshot(path=output/"rag-assistant.png")
            page.get_by_role("tab",name="Retrieval evaluation").click()
            page.get_by_role("button",name="Evaluate seeded demonstration").click()
            page.get_by_role("tabpanel",name="Retrieval evaluation").locator('[data-testid="stDataFrame"]').first.wait_for()
            page.get_by_role("link", name="Data modeling studio", exact=True).click()
            page.get_by_role("combobox", name="Scientific requirement").click()
            page.get_by_role("option", name="Trace a measurement to the sample actually tested.").click()
            page.get_by_text("The registered sample measured in this assay run.", exact=False).first.wait_for()
            page.get_by_text("Quality rule", exact=True).wait_for()

            page.get_by_role("link", name="Schema mapping", exact=True).click()
            page.locator('input[type="file"]').first.set_input_files(ROOT / "data/synthetic_raw/alpha.csv")
            page.get_by_text("alpha.csv", exact=True).first.wait_for()
            page.get_by_role("heading", name="Row decisions").wait_for()
            page.get_by_role("button", name="Publish batch to the shared model").click()
            page.get_by_text("Published Alpha batch. Decisions: {'accepted': 1, 'corrected': 1, 'rejected': 2}", exact=True).wait_for()
            page.get_by_role("button", name="Find this batch in RAG").click()
            page.get_by_text("2 published measurements", exact=True).wait_for()
            page.get_by_role("textbox", name="Result ID", exact=True).fill("RES-Alpha-UPLOAD-02")
            page.get_by_role("textbox", name="Result ID", exact=True).press("Enter")
            page.get_by_text("RES-Alpha-UPLOAD-02 recorded 78 nM", exact=False).first.wait_for()
            page.get_by_text("Original CSV evidence", exact=True).wait_for()
            page.get_by_role("button", name="Open cited mapping and lineage").click()
            page.get_by_role("heading", name="Alpha · corrected", exact=True).wait_for()
            if page.get_by_role("textbox", name="Result or source record ID").input_value() == "RES-Alpha-0001":
                raise AssertionError("Citation opened the default record")
            print("Verified the eight pages, requirement view, evaluation, upload decisions, batch search and cited lineage.")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=15)


if __name__ == "__main__":
    main()
