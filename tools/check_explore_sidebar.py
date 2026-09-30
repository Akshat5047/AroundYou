"""Check responsive sidebar placement and existing filter interactions."""
import sys, threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from playwright.sync_api import sync_playwright

server = ThreadingHTTPServer(('127.0.0.1', 5509), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        for width in [1440,1024,768,390]:
            page = browser.new_page(viewport={'width':width,'height':1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/api/destinations', lambda route: route.abort())
            page.goto('http://127.0.0.1:5509/explore.html')
            page.locator('.destinationCard').first.wait_for()
            sidebar = page.locator('.exploreSidebar').bounding_box()
            heading = page.locator('.exploreResultsHead').bounding_box()
            if width > 900:
                assert sidebar['x'] + sidebar['width'] < heading['x']
                assert abs(sidebar['y'] - heading['y']) < 3
            else:
                assert not page.locator('#districtFilter').is_visible()
                page.locator('#exploreFilters summary').click()
            page.locator('#districtFilter').select_option('Hyderabad')
            page.locator('#freeEntryFilter').check()
            assert page.locator('.filterChip').count() == 2
            assert page.locator('.destinationCard').count() > 0
            assert 'free=1' in page.url
            page.locator('#sortDestinations').select_option('name')
            page.locator('.clearFilters').click()
            assert page.locator('#districtFilter').input_value() == ''
            assert not page.locator('#freeEntryFilter').is_checked()
            assert page.locator('#sortDestinations').input_value() == 'popular'
            assert page.locator('.filterChip').count() == 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            if width <= 900:
                page.locator('#exploreFilters summary').click()
            page.locator('.exploreLayout').scroll_into_view_if_needed()
            page.screenshot(path=str(ROOT / '.ui-preview' / f'explore-sidebar-{width}.png'))
            assert not errors, errors
            print(f'Sidebar placement, filters, clear all, overflow: {width}px passed')
            page.close()
        browser.close()
finally:
    server.shutdown()
