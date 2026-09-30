"""Check every district offline, request preservation, and live backend generation."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/destinations', lambda route: route.abort())
    page.goto('http://127.0.0.1:5500/planner.html')
    districts = page.locator('#district option').evaluate_all('(options) => options.map(option => option.value).filter(Boolean)')
    for district in districts:
        page.locator('#district').select_option(district)
        page.wait_for_function('''() => !document.querySelector('#districtDestination').disabled && document.querySelector('#districtDestination').options.length > 1''')
        names = page.locator('#districtDestination option').evaluate_all('(options) => options.map(option => option.value).filter(Boolean)')
        expected = page.evaluate('(district) => BundledDestinations.destinations.filter(item => item.district === district).map(item => item.name).sort()', district)
        assert sorted(names) == sorted(expected), district
    print(f'All {len(districts)} district dropdowns populated while destination API was blocked')
    page.locator('#district').select_option('Hyderabad')
    page.locator('#districtDestination').select_option(label='Charminar')
    page.locator('#date').fill('2026-10-12')
    page.locator('#days').fill('1')
    page.route('**/api/agent/plan-trip', lambda route: route.abort())
    page.locator('#planner button[type="submit"]').click()
    page.locator('#err.show').wait_for()
    assert 'Unable to connect' in page.locator('#err').inner_text()
    assert page.locator('#date').input_value() == '2026-10-12'
    assert 'Charminar' in page.locator('#planner').inner_text()
    assert page.locator('#planner button[type="submit"]').is_enabled()
    print('Network failure preserves selection, inputs, and retry ability')
    page.unroute('**/api/agent/plan-trip')
    page.locator('#planner button[type="submit"]').click()
    page.locator('#out.show').wait_for(timeout=150000)
    assert 'Charminar' in page.locator('#out').inner_text()
    print('Live trip endpoint returned and rendered a result')
    print('Result status: ' + page.locator('.tripResultHeader .eyebrow').inner_text())
    assert not errors, errors
    browser.close()
