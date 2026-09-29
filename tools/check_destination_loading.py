"""Verify destination cards render while the remote API is stalled."""
import sys
import threading
import time
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from playwright.sync_api import sync_playwright

server = ThreadingHTTPServer(('127.0.0.1', 5507), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        for width in [1440, 390]:
            context = browser.new_context(viewport={'width': width, 'height': 900})
            page = context.new_page()
            errors = []
            stalled = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/api/destinations', lambda route: stalled.append(route))
            page.route('**/data/destinations.json*', lambda route: route.abort())
            page.route('**/js/destination-catalogue.js*', lambda route: route.abort())
            for name in ['index', 'explore']:
                start = time.perf_counter()
                page.goto(f'http://127.0.0.1:5507/{name}.html', wait_until='domcontentloaded')
                page.locator('.destinationAddButton').first.wait_for(timeout=3000)
                elapsed = time.perf_counter() - start
                assert elapsed < 3, elapsed
                button = page.locator('.destinationAddButton').first
                previous = button.inner_text()
                button.click()
                assert button.inner_text() != previous
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                print(f'{name} {width}px: cards ready in {elapsed:.2f}s with API stalled')
                for route in stalled:
                    route.abort()
                stalled.clear()
            assert not errors, errors
            context.close()
        page = browser.new_page()
        page.route('**/api/destinations', lambda route: route.abort())
        for name in ['index', 'explore']:
            page.goto((ROOT / 'frontend' / f'{name}.html').as_uri())
            page.locator('.destinationAddButton').first.wait_for(timeout=3000)
            print(f'{name}: direct file opening passed')
        browser.close()
finally:
    server.shutdown()
