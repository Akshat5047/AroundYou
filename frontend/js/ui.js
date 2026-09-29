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
    document.querySelector('#sampleReview')?.addEventListener('click', () => {
        const review = document.querySelector('#review');
        review.value = 'We visited on a Saturday morning. The entrance was busy, but the walk inside was peaceful. Bring water and allow about two hours to explore.';
        review.focus();
    });
})();

// These are category inspiration photos, not verified photographs of each place.
function destinationVisual(category) {
    const nature = /nature|water|lake|forest|park|wildlife/i.test(category);
    const photo = nature ? 'photo-1441974231531-c6227db76b6e' : 'photo-1599661046289-e31897846e41';
    return `<img class="destinationPhoto" src="https://images.unsplash.com/${photo}?auto=format&fit=crop&w=720&q=75" alt="" loading="lazy" onerror="this.hidden=true"><span class="photoCaption">${nature ? 'Nature' : 'Travel'} inspiration</span>`;
}
