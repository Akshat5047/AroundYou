/* Shared presentation and navigation. API and trip state stay in page scripts. */
(() => {
    const nav = document.querySelector('.navin');
    const links = nav?.querySelector('.links');
    if (links) {
        links.id = 'siteNavigation';
        const current = location.pathname.split('/').pop() || 'index.html';
        links.querySelectorAll('a').forEach(link => {
            const active = link.getAttribute('href') === current;
            link.classList.toggle('activeNav', active);
            if (active) link.setAttribute('aria-current', 'page');
        });
        let toggle = nav.querySelector('.menu');
        if (!toggle) {
            toggle = document.createElement('button');
            toggle.className = 'menu';
            nav.append(toggle);
        }
        toggle.type = 'button';
        toggle.textContent = '☰';
        toggle.setAttribute('aria-controls', links.id);
        function setOpen(open) {
            links.classList.toggle('isOpen', open);
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
            toggle.textContent = open ? '×' : '☰';
        }
        setOpen(false);
        toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
                setOpen(false);
                toggle.focus();
            }
        });
        document.addEventListener('click', event => {
            if (!nav.contains(event.target)) setOpen(false);
        });
        matchMedia('(min-width: 851px)').addEventListener('change', () => setOpen(false));
    }
    document.querySelectorAll('.field').forEach(field => {
        const label = field.querySelector('label');
        const input = field.querySelector('input:not([type="hidden"]), select, textarea');
        if (label && input?.id) label.htmlFor = input.id;
    });
    document.querySelectorAll('.error').forEach(element => element.setAttribute('role', 'alert'));
    document.querySelectorAll('.loading').forEach(element => element.setAttribute('role', 'status'));
    document.querySelectorAll('#out, #cleanlinessResult').forEach(element => element.setAttribute('aria-live', 'polite'));
    document.querySelectorAll('.feature h3').forEach((heading, index) => {
        const label = heading.textContent.replace(/^[^\p{L}\p{N}]+/u, '').trim();
        heading.innerHTML = uiIcon(['spark', 'wallet', 'sun', 'shield', 'image'][index]) + ' ' + esc(label);
    });
    document.querySelectorAll('.uploadIcon').forEach(element => element.innerHTML = uiIcon('image'));
    document.querySelectorAll('.searchIcon').forEach(element => element.innerHTML = uiIcon('search'));
    document.querySelector('#sampleReview')?.addEventListener('click', () => {
        const review = document.querySelector('#review');
        review.value = 'We visited on a Saturday morning. The entrance was busy, but the walk inside was peaceful. Bring water and allow about two hours to explore.';
        review.focus();
    });

    // Make existing analysis detail blocks collapsible without changing result IDs.
    const detection = document.querySelector('#detectionList')?.closest('.resultCard');
    if (detection) {
        const details = document.createElement('details'); details.className = 'resultCard technicalDetails';
        details.innerHTML = '<summary>Detection details</summary>';
        details.append(document.querySelector('#detectionList')); detection.replaceWith(details);
        const confidence = document.querySelector('#averageConfidence')?.closest('.metric');
        if (confidence) { const confidenceDetails = document.createElement('details'); confidenceDetails.className = 'technicalDetails'; confidenceDetails.innerHTML = '<summary>Model confidence</summary>'; confidence.before(confidenceDetails); confidenceDetails.append(confidence); }
    }
    const bindings = [
        ['#reviewForm', '#load', '#err'], ['#cleanlinessForm', '#cleanlinessLoading', '#cleanlinessError'],
        ['#ask', '#load', '#err'], ['#planner', '#load', '#err'],
    ];
    for (const [formSelector, loadSelector, errorSelector] of bindings) {
        const form = document.querySelector(formSelector);
        if (!form) continue;
        const loading = document.querySelector(loadSelector), error = document.querySelector(errorSelector);
        if (loading && !loading.querySelector('p')) { const message = document.createElement('p'); message.textContent = 'Working on your request…'; loading.append(message); }
        const submit = form.querySelector('button[type="submit"],button:not([type])');
        if (loading && submit) new MutationObserver(() => { const busy = loading.classList.contains('show'); submit.disabled = busy; form.setAttribute('aria-busy', String(busy)); }).observe(loading, {attributes: true, attributeFilter: ['class']});
        if (error) {
            const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'btn secondary retryButton'; retry.hidden = true; retry.innerHTML = `${uiIcon('retry')} Try again`;
            retry.addEventListener('click', () => form.requestSubmit()); error.after(retry);
            new MutationObserver(() => { retry.hidden = !error.classList.contains('show'); }).observe(error, {attributes: true, attributeFilter: ['class']});
        }
    }
    for (const [selector, retryAction] of [['#destinations', () => loadPopularDestinations()], ['#exploreStatus', () => loadDestinations()]]) {
        const container = document.querySelector(selector);
        if (!container) continue;
        new MutationObserver(() => {
            const state = container.querySelector('.exploreError,.emptyState');
            if (state && !state.querySelector('.retryButton')) {
                const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'btn secondary retryButton'; retry.innerHTML = `${uiIcon('retry')} Reload destinations`;
                retry.addEventListener('click', () => { retry.disabled = true; retryAction(); }); state.append(retry);
            }
        }).observe(container, {childList: true, subtree: true});
    }
})();

function destinationVisual(category) {
    return '<span class="photoCaption" hidden></span>';
}

function uiIcon(name) {
    const paths = {
        close: '<path d="m6 6 12 12M6 18 18 6"/>',
        pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
        copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
        print: '<path d="M6 8V3h12v5M6 17H3V8h18v9h-3"/><path d="M6 13h12v8H6z"/>',
        retry: '<path d="M20 7a9 9 0 1 0 1 8M20 3v5h-5"/>',
        check: '<path d="m5 12 4 4L19 6"/>',
        spark: '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>',
        wallet: '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 8V3h14v2M16 11h5v5h-5z"/>',
        sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
        shield: '<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z"/><path d="m8 12 3 3 5-6"/>',
        image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="2"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
        search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    };
    return `<svg class="uiIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.pin}</svg>`;
}
