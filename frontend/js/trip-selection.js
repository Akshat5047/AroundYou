/* Shared selection state. Names are canonicalized without changing saved trip order. */
window.TripSelection = (() => {
    const storageKey = 'aroundYouSelectedDestinations';
    let memory = [];
    const key = item => `${String(item.name || item.spot_name || '').trim()}|${String(item.district || '').trim()}`.toLowerCase();
    function normalize(items) {
        const seen = new Set();
        return (Array.isArray(items) ? items : []).filter(item => item && typeof item === 'object').map(item => {
            const group = (window.TripAliases || []).find(group => [group.name, ...group.aliases].some(name => key({name,district:group.district}) === key(item)));
            return {...item, name: group?.name || String(item.name || item.spot_name || '').trim(), district: String(item.district || '').trim()};
        }).filter(item => { const id = key(item); if (!item.name || seen.has(id)) return false; seen.add(id); return true; });
    }
    function get() {
        try { memory = normalize(JSON.parse(localStorage.getItem(storageKey) || '[]')); } catch {}
        return memory.map(item => ({...item}));
    }
    function set(items) {
        memory = normalize(items);
        let persisted = true;
        try { localStorage.setItem(storageKey, JSON.stringify(memory)); } catch { persisted = false; }
        window.dispatchEvent(new CustomEvent('tripselectionchange', {detail:{items:getSafe(), persisted}}));
        return memory;
    }
    const getSafe = () => memory.map(item => ({...item}));
    window.addEventListener('storage', event => {
        if (event.key === storageKey || event.key === null) window.dispatchEvent(new CustomEvent('tripselectionchange', {detail:{items:get(), persisted:true}}));
    });
    return {get, set, normalize, key, remove(item) { return set(get().filter(current => key(current) !== key(item))); }};
})();

document.addEventListener('DOMContentLoaded', () => {
    if (!document.querySelector('#destinations, #destinationGrid')) return;
    const panel = document.createElement('aside');
    panel.className = 'myTripPanel';
    panel.setAttribute('aria-label', 'My trip');
    panel.innerHTML = '<div class="myTripBar"><button type="button" class="myTripToggle" aria-expanded="false" aria-controls="myTripContents">My trip <span class="myTripCount">0 places</span><span aria-hidden="true">⌃</span></button><a class="btn primary" href="planner.html?selected=1">Plan trip</a></div><div id="myTripContents" hidden><p class="myTripEmpty">Use + on a destination to add it to your trip.</p><ol class="myTripList"></ol></div><span class="srOnly tripSelectionStatus" role="status"></span>';
    document.body.append(panel);
    document.body.classList.add('hasTripPanel');
    const toggle = panel.querySelector('.myTripToggle');
    const contents = panel.querySelector('#myTripContents');
    function open(value) { toggle.setAttribute('aria-expanded',String(value)); contents.hidden = !value; }
    toggle.addEventListener('click', () => open(contents.hidden));
    panel.addEventListener('keydown', event => { if (event.key === 'Escape') { open(false); toggle.focus(); } });
    function render(event) {
        const items = event?.detail?.items || TripSelection.get();
        panel.querySelector('.myTripCount').textContent = `${items.length} ${items.length === 1 ? 'place' : 'places'}`;
        panel.querySelector('.myTripEmpty').hidden = items.length > 0;
        const list = panel.querySelector('.myTripList');
        list.replaceChildren();
        items.forEach(item => {
            const li = document.createElement('li');
            const text = document.createElement('div');
            const name = document.createElement('strong'); name.textContent = item.name;
            const district = document.createElement('span'); district.textContent = item.district;
            text.append(name,district);
            const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'tripRemove'; remove.textContent = '−'; remove.setAttribute('aria-label', `Remove ${item.name} from trip`);
            remove.addEventListener('click', () => { TripSelection.remove(item); toggle.focus(); });
            li.append(text,remove); list.append(li);
        });
        if (event) panel.querySelector('.tripSelectionStatus').textContent = event.detail.persisted ? `${items.length} places in your trip.` : 'Your selection is kept for this page. Browser storage is unavailable.';
    }
    window.addEventListener('tripselectionchange',render);
    render();
});
