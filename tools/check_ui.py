"""Browser smoke checks. Uses local destination records; no AI responses are mocked."""
from pathlib import Path
import sys, json, sqlite3, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from playwright.sync_api import sync_playwright

server = ThreadingHTTPServer(('127.0.0.1', 5501), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
db = sqlite3.connect(f'file:{ROOT / "backend/data/smart_tourism.db"}?mode=ro', uri=True)
db.row_factory = sqlite3.Row
destinations = [dict(row) for row in db.execute('SELECT id,name,district,category,rating,popularity,entry_fee FROM other_spots ORDER BY popularity DESC LIMIT 24')]
db.close()
out = ROOT / '.ui-preview'
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/destinations**', lambda route: route.fulfill(json={'count':len(destinations),'destinations':destinations}))
    for width in [1440,390]:
        page.set_viewport_size({'width':width,'height':1000 if width == 1440 else 844})
        for name in ['index','explore','planner','ask','reviews','cleanliness']:
            page.goto(f'http://127.0.0.1:5501/{name}.html')
            page.wait_for_timeout(600)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow: {name} {width}'
            assert page.locator('[aria-current="page"]').count() == 1
            if width == 390:
                page.locator('.menu').click()
                assert page.locator('.links').is_visible()
                page.keyboard.press('Escape')
                assert not page.locator('.links').is_visible()
            if name in ['index','explore']:
                page.locator('.destinationAddButton').first.wait_for()
                page.locator('.destinationAddButton').first.click()
                assert page.locator('.destinationAddButton').first.inner_text() in ['✓ Added','+ Add to trip']
            if name == 'reviews':
                page.locator('#sampleReview').click()
                assert len(page.locator('#review').input_value()) > 30
            if name == 'cleanliness':
                assert page.locator('#cleanlinessEmpty').is_visible()
            page.screenshot(path=str(out / f'{name}-{width}.png'), full_page=True)
            print(f'PASS {name} at {width}px')
    assert not errors, errors
    browser.close()
server.shutdown()
print('All six pages passed desktop/mobile checks; no JavaScript runtime errors.')
