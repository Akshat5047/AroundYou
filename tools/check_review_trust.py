"""Exercise review UI against the actual local classifier, without external APIs."""
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from services.review_service import classify_review
from playwright.sync_api import sync_playwright

assert classify_review('good')['confidence'] is None
assert classify_review('   ')['confidence'] is None
assert classify_review(' '.join(['qzxwvv'] * 15))['confidence'] is None

server = ThreadingHTTPServer(('127.0.0.1', 5506), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page()
        errors, requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        def classify(route):
            review = route.request.post_data_json['review']
            requests.append(review)
            route.fulfill(json=classify_review(review))
        page.route('**/api/reviews/classify', classify)
        for width in [1440, 390]:
            page.set_viewport_size({'width': width, 'height': 900})
            page.goto('http://127.0.0.1:5506/reviews.html')
            before = len(requests)
            page.locator('#sampleReview').click()
            page.locator('#out.show').wait_for()
            assert len(requests) == before + 1
            assert 'Genuine wording score' in page.locator('#out').inner_text()
            page.locator('#review').fill('good')
            assert not page.locator('#out').is_visible()
            page.locator('#reviewForm .primary').click()
            page.locator('#out.show').wait_for()
            assert 'at least 10 words' in page.locator('#out').inner_text()
            assert page.locator('#out .metric').count() == 0
            page.locator('#review').fill('The hotel room was dirty and the staff were rude. I waited an hour to check in and the bathroom was not cleaned.')
            page.locator('#reviewForm .primary').click()
            page.locator('#out.show').wait_for()
            assert '70% decision threshold' in page.locator('#out').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.route('**/api/reviews/classify', lambda route: route.fulfill(status=503, json={'detail': 'Service unavailable'}))
            page.locator('#sampleReview').click()
            page.locator('#err.show').wait_for()
            assert page.locator('#sampleReview').is_enabled()
            assert not page.locator('#review').get_attribute('readonly')
            page.unroute('**/api/reviews/classify')
            page.route('**/api/reviews/classify', classify)
            print(f'Review sample, real classifier, validation, stale results, error recovery: {width}px passed')
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
