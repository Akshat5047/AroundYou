"""Browser checks using answer fixtures; no AI requests or quota usage."""
from pathlib import Path
import sys, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / '.ui-preview-deps'))
from playwright.sync_api import sync_playwright

answers = [
    'Based on the Around You knowledge base, here are some places you can visit in Telangana (all located in Hyderabad): * **Purana Haveli**: A tourist destination featuring local charm and plenty of photo spots (Entry fee: ~₹50). * **Telangana State Museum**: A heritage landmark (Entry fee: ~₹100). * **Public Gardens**: A leisure spot for unwinding (Entry fee: ~₹200).',
    '## Nature destinations\n\nChoose a relaxed visit.\n\n- **Lake:** Bring water.\n- **Park:** Check access.\n\nEnjoy your trip.',
    r'Heritage options: * \*\*Museum\*\*: Explore the exhibits. * \*\*Palace\*\*: Enjoy the architecture.',
    '### Hyderabad\n1. **Museum:** Explore the exhibits.\n2. **Gardens:** Take a walk.\n\n> Confirm opening hours.',
    'Choose **heritage** for architecture or *nature* for a quieter outing.\n\nKeep your budget and available time in mind.',
]
server = ThreadingHTTPServer(('127.0.0.1', 5503), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'frontend')))
threading.Thread(target=server.serve_forever, daemon=True).start()
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    current = [0]
    def respond(route):
        route.fulfill(json={'question': route.request.post_data_json['question'], 'answer': answers[current[0]], 'sources': [{'spot_name': 'Destination record', 'district': 'Hyderabad', 'content': 'Supporting destination information.'}]})
    page.route('**/api/rag/ask', respond)
    for width in [1440, 390]:
        page.set_viewport_size({'width': width, 'height': 1000})
        page.goto('http://127.0.0.1:5503/ask.html')
        for i in range(page.locator('.askQuestionList .askQuestion').count()):
            current[0] = i
            page.locator('.askQuestionList .askQuestion').nth(i).click()
            question = page.locator('#q').input_value()
            page.locator('#ask button[type="submit"]').click()
            page.wait_for_function('(question) => document.querySelector(".answerHeader h2")?.textContent === question', arg=question)
            text = page.locator('.answerProse').inner_text()
            assert '**' not in text and '\\*' not in text and '##' not in text
            assert page.locator('.answerProse strong').count() > 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            if i == 0:
                assert page.locator('.answerProse li').count() == 3
                page.locator('#out').screenshot(path=str(ROOT / '.ui-preview' / f'quick-answer-{width}.png'))
            page.locator('.answerSources summary').click()
            assert page.locator('.answerSource').is_visible()
        page.evaluate('''() => renderAnswer({question: '<img src=x>', answer: '**Safe** <img src=x onerror=alert(1)>', sources: []}, document.querySelector('#out'))''')
        assert page.locator('#out img').count() == 0
        assert page.locator('.answerSources').count() == 0
        print(f'PASS all 5 quick questions at {width}px, formatting, sources, overflow and HTML escaping')
    assert not errors, errors
    browser.close()
server.shutdown()
