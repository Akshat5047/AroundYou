"""Feature regression checks with explicit local API fixtures; no live AI calls."""
import base64, sys, threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
sys.path.insert(0, str(ROOT / 'backend'))
from playwright.sync_api import sync_playwright
from agent.itinerary import fallback_itinerary
from test_itinerary import SOURCES, SELECTED

server = ThreadingHTTPServer(('127.0.0.1', 5504), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
requirements = dict(duration_days=2, num_travelers=2, travel_date='2026-10-12', budget_limit=15000)
fixture = {'plan': fallback_itinerary(requirements, {'sources': SOURCES}), 'tool_results': {'requirements': requirements, 'destination_search': {'sources': SOURCES}, 'generation': {'mode': 'fallback'}}}
destinations = [dict(item, id=i, category='Heritage', entry_fee=50, rating=4.5) for i, item in enumerate(SELECTED, 1)]
destinations.append(dict(name='Old Fortress on Gutta', district='Nalgonda', id=999, category='Heritage', entry_fee=200, rating=4.2))
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/destinations**', lambda route: route.fulfill(json={'destinations': destinations, 'count': len(destinations)}))
    page.route('**/api/agent/plan-trip', lambda route: route.fulfill(json=fixture))
    page.route('**/api/rag/ask', lambda route: route.fulfill(json={'question': route.request.post_data_json['question'], 'answer': '**A helpful answer** with recorded destination information.', 'sources': []}))
    for width in [1440, 390]:
        page.set_viewport_size({'width': width, 'height': 1000})
        for name in ['index', 'explore']:
            page.goto(f'http://127.0.0.1:5504/{name}.html')
            page.locator('.detailsButton').first.wait_for()
            if name == 'explore':
                missing = page.locator('.destinationCard').filter(has_text='Old Fortress on Gutta')
                assert missing.locator('.destinationTop').evaluate('(el) => el.getBoundingClientRect().height') < 100
                assert 'Photo not yet available' not in missing.inner_text()
                assert missing.locator('.detailsButton').is_visible()
            page.wait_for_function('document.querySelector(".destinationPhoto")?.naturalWidth > 0')
            if name == 'index':
                assert page.locator('.destinationPhoto').count() == page.locator('.destinationCard').count()
                page.screenshot(path=str(ROOT / '.ui-preview' / f'featured-home-{width}.png'), full_page=True)
            page.locator('.detailsButton').first.click()
            page.locator('dialog[open]').wait_for()
            assert page.locator('.photoCredits').is_visible()
            page.locator('.dialogAdd').click()
            first = page.locator('.dialogAdd').inner_text()
            page.locator('.dialogAdd').click()
            assert first != page.locator('.dialogAdd').inner_text()
            page.keyboard.press('Escape')
            page.locator('dialog').wait_for(state='detached')
            assert page.locator('dialog').count() == 0
            assert page.locator('.detailsButton:focus').count() == 1
        page.goto('http://127.0.0.1:5504/planner.html')
        page.evaluate('(items) => localStorage.setItem("aroundYouSelectedDestinations", JSON.stringify(items))', SELECTED)
        page.reload()
        page.locator('#date').fill('2026-10-12')
        page.locator('#planner button[type="submit"]').click()
        page.locator('.copyTrip').wait_for()
        assert not page.locator('#planner').is_visible()
        page.locator('.copyTrip').click()
        page.wait_for_function('document.querySelector(".exportStatus").textContent === "Itinerary copied."')
        assert 'Birla Temple' in page.evaluate('navigator.clipboard.readText()')
        page.evaluate('window.print = () => { window.printCalled = true; }')
        page.locator('.printTrip').click()
        assert page.evaluate('window.printCalled')
        page.emulate_media(media='print')
        assert not page.locator('.nav').is_visible()
        assert page.locator('.itineraryPanel').is_visible()
        page.pdf(path=str(ROOT / '.ui-preview' / f'itinerary-{width}.pdf'), format='A4')
        page.emulate_media(media='screen')
        page.locator('.tripResultHeader > a').click()
        assert page.locator('#planner').is_visible()
        page.locator('#tripPreferences > summary').click()
        page.evaluate('window.scrollTo({top:0, behavior:"instant"})')
        page.screenshot(path=str(ROOT / '.ui-preview' / f'wide-results-{width}.png'), full_page=True)

        page.goto('http://127.0.0.1:5504/ask.html')
        for question in ['First question', 'Second question']:
            page.locator('#q').fill(question)
            page.locator('#ask button[type="submit"]').click()
            page.wait_for_function('(q) => document.querySelector(".answerHeader h2")?.textContent === q', arg=question)
        page.reload()
        page.locator('.answerHistory > summary').click()
        page.locator('.historyList button').last.click()
        assert page.locator('.answerHeader h2').inner_text() == 'First question'
        page.locator('.clearHistory').click()
        assert not page.locator('.answerHistory').is_visible()

        failures = [True]
        def review(route):
            if failures[0]:
                failures[0] = False
                route.fulfill(status=503, json={'detail': 'Service temporarily unavailable'})
            else:
                route.fulfill(json={'label': 'genuine', 'confidence': .86, 'probabilities': {'genuine': .86, 'deceptive': .14}})
        page.route('**/api/reviews/classify', review)
        page.goto('http://127.0.0.1:5504/reviews.html')
        page.locator('#sampleReview').click()
        page.locator('#reviewForm .primary').click()
        page.locator('.retryButton').click()
        page.locator('.analysisFinding').wait_for()
        assert not page.locator('#out .metrics').is_visible()
        page.locator('#out summary').click()
        assert page.locator('#out .metrics').is_visible()
        page.unroute('**/api/reviews/classify')

        picture = ROOT / 'frontend/assets/destinations/destination-1.jpg'
        response = dict(cleanliness_score=92, status='Clean', litter_count=0, litter_coverage_percent=0, average_confidence=0, annotated_image='data:image/jpeg;base64,' + base64.b64encode(picture.read_bytes()).decode(), disclaimer='Test fixture: visible litter only.', detections=[])
        page.route('**/api/cleanliness/analyze', lambda route: route.fulfill(json=response))
        page.goto('http://127.0.0.1:5504/cleanliness.html')
        page.locator('#cleanlinessImage').set_input_files(str(picture))
        page.locator('.analyzeButton').click()
        page.locator('#cleanlinessResult.show').wait_for()
        assert not page.locator('#detectionList').is_visible()
        page.locator('details').filter(has=page.locator('#detectionList')).locator('summary').click()
        assert page.locator('#detectionList').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        print(f'PASS {width}px: photos, details, selection, focus, exports/PDF, history, retry and analysis disclosure')
    assert not errors, errors
    browser.close()
server.shutdown()
