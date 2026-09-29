"""Planner browser regression with explicit test fixtures, never a production mock."""
from pathlib import Path
import sys, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
sys.path.insert(0, str(ROOT / 'backend'))
from playwright.sync_api import sync_playwright
from agent.itinerary import fallback_itinerary
from test_itinerary import SOURCES, SELECTED, NAMES

requirements = dict(duration_days=2, num_travelers=2, travel_date='2026-10-12', budget_limit=15000, transport_mode='bus', destination_or_district='Hyderabad')
response = dict(plan=fallback_itinerary(requirements, {'sources': SOURCES}), tool_results={
    'requirements': requirements, 'destination_search': {'sources': SOURCES}, 'generation': {'mode': 'fallback', 'reason': 'daily_quota', 'message': 'The AI service has reached its daily request allowance. A personalized itinerary was not generated.'},
    'budget_evaluation': {'status': 'within_budget', 'budget_limit': 15000, 'predicted_cost': 9000, 'difference': 6000},
    'ml_predictions': {'budget': {'status': 'success', 'prediction': dict(travel_cost_est=2000, stay_cost_est=4000, food_cost_est=2500, entry_fees_est=300, tolls_and_parking_est=200)}}})
server = ThreadingHTTPServer(('127.0.0.1', 5502), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page()
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    destinations = [dict(item, id=i + 1) for i, item in enumerate(SELECTED)]
    destinations.append(dict(name='A very long destination name that must stay inside the form border', district='Hyderabad', id=4))
    page.route('**/api/destinations**', lambda route: route.fulfill(json={'destinations': destinations}))
    def plan(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json=response)
    page.route('**/api/agent/plan-trip', plan)
    for width in [1440, 1100, 860, 390]:
        page.set_viewport_size({'width': width, 'height': 1000})
        page.goto('http://127.0.0.1:5502/planner.html')
        page.evaluate('(items) => localStorage.setItem("aroundYouSelectedDestinations", JSON.stringify(items))', SELECTED)
        page.reload()
        page.locator('#district').select_option('Hyderabad')
        page.locator('#districtDestination option').nth(4).wait_for(state='attached')
        page.locator('#date').fill('2026-10-12')
        page.locator('#planner button[type="submit"]').click()
        page.locator('.itineraryDay').first.wait_for()
        assert [item['name'] for item in requests[-1]['selected_destinations']] == NAMES
        assert page.locator('.tripStops li').count() == 3
        assert page.locator('.itineraryDay').count() == 2
        assert 'daily request allowance' in page.locator('.resultContext').inner_text()
        assert 'Suggested approach' in page.locator('.itineraryContent').inner_text()
        for name in NAMES:
            assert name in page.locator('.itineraryContent').inner_text()
        page.locator('#tripPreferences > summary').click()
        assert page.evaluate('''() => {
            const form = document.querySelector('#planner').getBoundingClientRect();
            return [...document.querySelectorAll('#planner input:not([type="hidden"]), #planner select, #planner textarea')].every(el => {
                const r = el.getBoundingClientRect();
                return r.left >= form.left && r.right <= form.right;
            }) && document.documentElement.scrollWidth <= innerWidth;
        }'''), f'Form overflow at {width}'
        page.locator('#tripPreferences > summary').click()
        page.evaluate('window.scrollTo({top: 0, behavior: "instant"})')
        page.screenshot(path=str(ROOT / '.ui-preview' / f'planner-results-{width}.png'), full_page=True)
        print(f'PASS {width}px: controls contained, request includes 3 stops, 2 day cards include all stops')
    page.evaluate(r'''() => {
        const rendered = renderItineraryBlocks('#### Day 1: Test\n• **Destination:** <img src=x onerror=alert(1)>');
        document.querySelector('.itineraryContent').innerHTML = rendered;
    }''')
    assert page.locator('.itineraryContent img').count() == 0
    assert not errors, errors
    browser.close()
server.shutdown()
