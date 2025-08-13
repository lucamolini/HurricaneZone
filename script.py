# script.py
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright
import img2pdf

# ——— Configura qui ———
URL = "https://www.hurricanezone.org/"          # pagina da catturare
VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768
DEVICE_SCALE = 1
TZ = "Europe/Rome"                               # timestamp locale per cartella output
OUT_ROOT = Path("output")
# ————————————————

def main():
    now_local = datetime.now(ZoneInfo(TZ))
    date_str = now_local.strftime("%Y-%m-%d")
    out_dir = OUT_ROOT / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "hurricanezone_full.png"
    pdf_path = out_dir / "hurricanezone_scroll.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT, "device_scale_factor": DEVICE_SCALE}
        )
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()

    # PNG -> PDF a pagina singola (identico allo screenshot)
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(str(png_path)))

    print(f"Creati:\n- {png_path}\n- {pdf_path}")

if __name__ == "__main__":
    main()
