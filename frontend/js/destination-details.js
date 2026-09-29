const destinationAssets = Promise.all([
    fetch('data/destination-guide.json?v=20260929-2').then(response => { if (!response.ok) throw Error(); return response.json(); }).catch(() => ({})),
    fetch('data/destination-photos.json?v=20260929-2').then(response => { if (!response.ok) throw Error(); return response.json(); }).catch(() => ({})),
]);

function decorateDestinationCard(card, destination) {
    const name = destination.name || destination.spot_name || 'Destination';
    const key = destinationAssetKey(destination);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'detailsButton';
    button.textContent = 'View details';
    card.querySelector('.destinationBody h3').after(button);
    destinationAssets.then(([guide, photos]) => {
        const photo = photos[key];
        if (photo) {
            const image = document.createElement('img');
            image.className = 'destinationPhoto';
            image.alt = name;
            image.loading = 'lazy';
            image.src = photo.url;
            const top = card.querySelector('.destinationTop');
            top.classList.add('hasDestinationPhoto');
            image.addEventListener('error', () => { image.remove(); top.classList.remove('hasDestinationPhoto'); card.querySelector('.photoCaption').hidden = true; });
            top.prepend(image);
            const caption = card.querySelector('.photoCaption');
            caption.hidden = false;
            caption.textContent = `${photo.author} · ${photo.license}`;
        }
        button.addEventListener('click', () => openDestinationDetails(destination, card, guide[key], photo, button));
    });
}

function destinationAssetKey(destination) {
    return `${String(destination.name || destination.spot_name || '').trim()}|${String(destination.district || '').trim()}`.toLowerCase();
}

function openDestinationDetails(destination, card, description, photo, trigger) {
    const name = destination.name || destination.spot_name || 'Destination';
    const dialog = document.createElement('dialog');
    dialog.className = 'destinationDialog';
    dialog.setAttribute('aria-labelledby', 'destinationDialogTitle');
    const fee = destination.entry_fee;
    const hasFee = fee !== null && fee !== undefined && fee !== '' && Number.isFinite(Number(fee));
    dialog.innerHTML = `<div class="dialogTop"><span class="eyebrow">Destination details</span><button type="button" class="iconButton" aria-label="Close destination details">${uiIcon('close')}</button></div>
        <h2 id="destinationDialogTitle">${esc(name)}</h2><p class="muted">${esc(destination.district || 'Telangana')} · ${esc(destination.category || 'Destination')}</p>
        <div class="dialogImage"></div><p>${esc(description || 'A detailed description is not yet available for this destination.')}</p>
        <div class="metrics"><div class="metric"><span class="muted">Recorded entry fee</span><b>${hasFee ? Number(fee) === 0 ? 'Free' : esc(money(fee)) : 'Not available'}</b></div><div class="metric"><span class="muted">Recorded rating</span><b>${destination.rating != null ? esc(destination.rating) + ' / 5' : 'Not available'}</b></div></div>
        <p class="resultFootnote">From destination records. Confirm opening hours, access and entry fees before visiting.</p>
        <div class="dialogActions"><button type="button" class="btn primary dialogAdd"></button><a class="btn secondary" href="planner.html">Open trip planner</a><a class="textLink" target="_blank" rel="noopener noreferrer" href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(name + ', ' + (destination.district || 'Telangana'))}">View on map ↗</a></div>`;
    if (photo) {
        const img = document.createElement('img');
        img.src = photo.url; img.alt = name;
        img.addEventListener('error', () => img.remove());
        const area = dialog.querySelector('.dialogImage'); area.append(img);
        const credits = document.createElement('p'); credits.className = 'photoCredits';
        const source = document.createElement('a'); source.href = photo.source; source.textContent = `${photo.title} — ${photo.author}`;
        const license = document.createElement('a'); license.href = photo.licenseUrl; license.textContent = photo.license;
        for (const link of [source, license]) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
        credits.append(source, ' · ', license, ' · Display cropped to fit'); area.append(credits);
    }
    const isSelected = () => {
        try { return JSON.parse(localStorage.getItem('aroundYouSelectedDestinations') || '[]').some(item => (item.name || item.spot_name) === name && item.district === destination.district); }
        catch { return false; }
    };
    const add = dialog.querySelector('.dialogAdd');
    const refresh = () => { add.textContent = isSelected() ? 'Remove from trip' : 'Add to trip'; };
    refresh();
    add.addEventListener('click', () => { card.querySelector('.destinationAddButton').click(); refresh(); });
    dialog.querySelector('.iconButton').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog && (event.clientX < dialog.getBoundingClientRect().left || event.clientX > dialog.getBoundingClientRect().right || event.clientY < dialog.getBoundingClientRect().top || event.clientY > dialog.getBoundingClientRect().bottom)) dialog.close(); });
    dialog.addEventListener('close', () => { dialog.remove(); if (trigger.isConnected) trigger.focus(); else document.querySelector('.detailsButton')?.focus(); });
    document.body.append(dialog); dialog.showModal();
}
