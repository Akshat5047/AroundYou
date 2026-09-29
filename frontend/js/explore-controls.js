const destinationFilterFields = {q:'destinationSearch',district:'districtFilter',category:'categoryFilter',rating:'ratingFilter',sort:'sortDestinations',free:'freeEntryFilter'};
function restoreDestinationFilters() {
    const params = new URLSearchParams(location.search);
    for (const [key,id] of Object.entries(destinationFilterFields)) {
        const field = document.getElementById(id);
        if (field.type === 'checkbox') field.checked = params.get(key) === '1';
        else if (params.has(key)) {
            field.value = params.get(key);
            if (key === 'sort' && !field.value) field.value = 'popular';
        }
    }
}
function renderActiveDestinationFilters() {
    const area = document.getElementById('activeDestinationFilters');
    area.replaceChildren();
    const params = new URLSearchParams(location.search);
    for (const [key,id] of Object.entries(destinationFilterFields)) {
        const field = document.getElementById(id);
        const value = field.type === 'checkbox' ? field.checked ? '1' : '' : field.value;
        if (value && !(key === 'sort' && value === 'popular')) params.set(key,value); else params.delete(key);
        if (!value || key === 'sort') continue;
        const label = key === 'free' ? 'Free entry' : key === 'rating' ? `Rating ${value}+` : key === 'q' ? `Search: ${value}` : field.selectedOptions[0]?.textContent || value;
        const chip = document.createElement('button'); chip.type = 'button'; chip.className = 'filterChip';
        chip.textContent = label + ' ×'; chip.setAttribute('aria-label',`Remove filter: ${label}`);
        chip.addEventListener('click', () => {
            if (field.type === 'checkbox') field.checked = false; else field.value = '';
            applyFilters(); field.focus();
        });
        area.append(chip);
    }
    const clear = document.createElement('button'); clear.type = 'button'; clear.className = 'textLink clearFilters'; clear.textContent = 'Clear all';
    clear.addEventListener('click', () => {
        for (const [key,id] of Object.entries(destinationFilterFields)) {
            const field = document.getElementById(id);
            if (field.type === 'checkbox') field.checked = false; else field.value = key === 'sort' ? 'popular' : '';
        }
        applyFilters(); document.getElementById('destinationSearch').focus();
    });
    if (area.children.length || document.getElementById('sortDestinations').value !== 'popular') area.append(clear);
    try { history.replaceState(null,'', location.pathname + (params.size ? '?' + params.toString() : '') + location.hash); } catch {}
}
document.addEventListener('DOMContentLoaded', () => {
    ['freeEntryFilter','ratingFilter','sortDestinations'].forEach(id => document.getElementById(id).addEventListener('change',applyFilters));
});
