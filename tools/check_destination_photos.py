"""Validate local photo assets, attribution details, and both card layouts."""
import json
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from playwright.sync_api import sync_playwright

photos = json.loads((ROOT / 'frontend/data/destination-photos.json').read_text(encoding='utf-8'))
destinations = json.loads((ROOT / 'frontend/data/destinations.json').read_text(encoding='utf-8'))['destinations']
keys = {(d['name']+'|'+d['district']).lower() for d in destinations}
for key, photo in photos.items():
    assert key in keys, key
    assert (ROOT / 'frontend' / photo['url']).is_file(), key
    assert all(photo.get(field) for field in ['author','license','licenseUrl','source']), key

server = ThreadingHTTPServer(('127.0.0.1', 5508), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        for width in [1440, 390]:
            page = browser.new_page(viewport={'width':width,'height':1000})
            page.route('**/api/destinations', lambda route: route.abort())
            for name in ['index','explore']:
                page.goto(f'http://127.0.0.1:5508/{name}.html')
                page.locator('.destinationPhoto').first.wait_for()
                page.wait_for_function('document.querySelector(".destinationPhoto").naturalWidth > 0')
                assert page.locator('.photoCaption:visible').count() == 0
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                card = page.locator('.destinationCard').filter(has=page.locator('.destinationPhoto')).first
                card.locator('.detailsButton').click()
                page.locator('.photoCredits').wait_for()
                assert page.locator('.photoCredits a').count() == 2
                page.keyboard.press('Escape')
                page.screenshot(path=str(ROOT / '.ui-preview' / f'photos-{name}-{width}.png'), full_page=True)
            if width == 1440:
                results = page.evaluate('''async urls => Promise.all(urls.map(url => new Promise(resolve => {
                    const image = new Image(); image.onload = () => resolve({url, ok: image.naturalWidth > 0});
                    image.onerror = () => resolve({url, ok: false}); image.src = url;
                })))''', [photo['url'] for photo in photos.values()])
                assert all(item['ok'] for item in results), [item for item in results if not item['ok']]
            page.goto((ROOT / 'frontend/index.html').as_uri())
            page.wait_for_function('document.querySelector(".destinationPhoto")?.naturalWidth > 0')
            print(f'Photos, clean cards, credits in details, file preview: {width}px passed')
            page.close()
        browser.close()
finally:
    server.shutdown()
print(f'Validated {len(photos)} destination photo mappings')
