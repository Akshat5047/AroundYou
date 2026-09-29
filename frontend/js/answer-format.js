/* Escape model text before adding a small, controlled set of formatting tags. */
function formatAnswer(text) {
    const inline = value => esc(value)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
    const normalized = String(text || '').replace(/\r\n?/g, '\n')
        .replace(/\\([*#_`])/g, '$1')
        .replace(/[ \t]+[*•-][ \t]+(?=\*\*)/g, '\n- ')
        .replace(/([:.!?])[ \t]+[*•][ \t]+/g, '$1\n- ');
    let html = '', paragraph = [], list = null;
    function flush() {
        if (paragraph.length) html += `<p>${inline(paragraph.join(' '))}</p>`;
        paragraph = [];
    }
    function closeList() { if (list) html += `</${list}>`; list = null; }
    for (const raw of normalized.split('\n')) {
        const line = raw.trim();
        if (!line) { flush(); closeList(); continue; }
        if (/^([-*_])\1{2,}$/.test(line)) { flush(); closeList(); html += '<hr>'; continue; }
        const heading = line.match(/^#{1,6}\s+(.+?)\s*#*$/);
        const bullet = line.match(/^(?:[-*•]\s+|\d+[.)]\s+)(.+)$/);
        if (heading) {
            flush(); closeList(); html += `<h3>${inline(heading[1])}</h3>`;
        } else if (bullet) {
            flush();
            const kind = /^\d/.test(line) ? 'ol' : 'ul';
            if (list !== kind) { closeList(); html += `<${kind}>`; list = kind; }
            html += `<li>${inline(bullet[1])}</li>`;
        } else if (/^>\s?/.test(line)) {
            flush(); closeList(); html += `<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>`;
        } else if (list && /^\s{2,}/.test(raw)) {
            html = html.replace(/<\/li>$/, `<br>${inline(line)}</li>`);
        } else { closeList(); paragraph.push(line); }
    }
    flush(); closeList();
    return html || '<p>No answer was returned. Please try another question.</p>';
}

function renderAnswer(data, output) {
    const sources = Array.isArray(data.sources) ? data.sources : [];
    output.innerHTML = `
        <header class="answerHeader"><span class="tag">Travel guidance</span><h2>${esc(data.question)}</h2></header>
        <div class="answerProse">${formatAnswer(data.answer)}</div>
        ${sources.length ? `<details class="answerSources"><summary>Based on ${sources.length} destination ${sources.length === 1 ? 'source' : 'sources'}<span>View details</span></summary>
            <div class="sources">${sources.map((source, index) => `<article class="answerSource"><span class="sourceNumber">${index + 1}</span><div><h4>${esc(source.spot_name || 'Destination information')}</h4><span class="muted">${esc(source.district || '')}</span><p>${esc(source.content || '')}</p></div></article>`).join('')}</div></details>` : ''}`;
    output.className = 'answer show askAnswer';
}
