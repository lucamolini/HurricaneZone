# script.py
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import time

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import img2pdf

# ——— Configura qui ———
URL = "https://www.hurricanezone.org/"
VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768
DEVICE_SCALE = 1
TZ = "Europe/Rome"
OUT_ROOT = Path("output")
NAV_TIMEOUT_MS = 180_000     # timeout navigazione più ampio
RETRIES = 3                  # tentativi in caso di errore/timeout
BUFFER_AFTER_LOAD_SEC = 6    # attesa extra dopo il load
SCROLL_PAUSE_MS = 200        # pausa tra scroll
# ————————————————

def stable_capture(p):
    """Rende la navigazione/screenshot più robusta: UA custom, blocco analytics,
    attese ragionevoli e scroll progressivo."""
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        device_scale_factor=DEVICE_SCALE,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        java_script_enabled=True,
    )

    # Blocca richieste notoriamente “rumorose” (analytics/ads) che possono impedire network idle
    noisy_hosts = (
        "googletagmanager.com", "google-analytics.com", "doubleclick.net",
        "facebook.net", "hotjar.com", "segment.io", "mixpanel.com",
        "clarity.ms", "cloudflareinsights.com"
    )
    context.route("**/*", lambda route: route.abort()
                  if any(h in route.request.url for h in noisy_hosts) else route.continue_())

    page = context.new_page()
    page.set_default_timeout(NAV_TIMEOUT_MS)
    page.set_default_navigation_timeout(NAV_TIMEOUT_MS)

    # Naviga senza aspettare networkidle
    page.goto(URL, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    # Completa il caricamento base
    try:
        page.wait_for_load_state("load", timeout=60_000)
    except PWTimeout:
        pass  # va bene lo stesso

    # buffer per JS/css/lazy
    time.sleep(BUFFER_AFTER_LOAD_SEC)

    # Scroll progressivo fino in fondo per forzare il lazy-load
    page.evaluate(
        """async (pause) => {
            const sleep = (ms) => new Promise(r => setTimeout(r, ms));
            let lastY = -1;
            while (true) {
              window.scrollBy(0, Math.round(window.innerHeight * 0.8));
              await sleep(pause);
              const y = window.scrollY;
              if (y === lastY) break;
              lastY = y;
            }
            window.scrollTo(0, 0); // torna su prima dello screenshot
        }""",
        SCROLL_PAUSE_MS
    )

    return browser, context, page

def main():
    now_local = datetime.now(ZoneInfo(TZ))
    date_str = now_local.strftime("%Y-%m-%d")
    out_dir = OUT_ROOT / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "hurricanezone_full.png"
    pdf_path = out_dir / "hurricanezone_scroll.pdf"

    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            with sync_playwright() as p:
                browser, context, page = stable_capture(p)
                page.screenshot(path=str(png_path), full_page=True)
                browser.close()
            # PNG -> PDF a pagina singola (identico allo screenshot)
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(str(png_path)))
            print(f"Creati:\n- {png_path}\n- {pdf_path}")
            return
        except Exception as e:
            last_err = e
            print(f"[Tentativo {attempt}/{RETRIES}] fallito: {e}")
            # piccola pausa prima del retry
            time.sleep(3)

    # Se siamo qui, tutti i tentativi sono falliti
    raise SystemExit(f"Errore definitivo dopo {RETRIES} tentativi: {last_err}")

if __name__ == "__main__":
    main()
