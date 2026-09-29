/* Render the bundled catalogue immediately; refresh the shared cache in the background. */
window.DestinationCatalogue = (() => {
    const key = 'aroundYouCatalogue-v1';
    const ttl = 15 * 60 * 1000;
    let pending;
    const valid = data => Array.isArray(data?.destinations) && data.destinations.length > 0 &&
        data.destinations.every(item => item && typeof item.name === 'string' && typeof item.district === 'string');
    async function request(url) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 8000);
        try {
            const response = await fetch(url, {signal: controller.signal});
            if (!response.ok) throw new Error('Unable to load destinations');
            const data = await response.json();
            if (!valid(data)) throw new Error('Invalid destination catalogue');
            return data;
        } finally { clearTimeout(timer); }
    }
    function refresh(url) {
        return request(url).then(data => {
            try { localStorage.setItem(key, JSON.stringify({saved: Date.now(), data})); } catch {}
            return data;
        });
    }
    async function load(url) {
        let cached;
        try { cached = JSON.parse(localStorage.getItem(key)); } catch {}
        if (valid(cached?.data)) {
            if (Date.now() - cached.saved > ttl) void refresh(url).catch(() => {});
            return cached.data;
        }
        // Start both requests together, but never make rendering wait for the remote server.
        const remote = refresh(url).catch(() => null);
        try {
            if (valid(window.BundledDestinations)) return window.BundledDestinations;
            return await request('data/destinations.json?v=20260929-1');
        }
        catch {
            const data = await remote;
            if (data) return data;
            throw new Error('Unable to load destinations');
        }
    }
    return {load(url) { return pending ||= load(url).catch(error => { pending = null; throw error; }); }};
})();
