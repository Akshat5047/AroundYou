function renderPlannerResults(data, output) {
    const tools = data.tool_results || {};
    const requirements = tools.requirements || {};
    const sources = tools.destination_search?.sources || [];
    const ml = tools.ml_predictions || {};
    const budget = tools.budget_evaluation || {};
    const costs = ml.budget?.status === 'success' ? ml.budget.prediction || {} : {};
    const fallback = tools.generation?.mode === 'fallback';
    const generationMessage = tools.generation?.message || 'The AI itinerary was not generated. This guide uses the available destination records.';
    const districts = [...new Set(sources.map(source => source.district).filter(Boolean))];
    const title = sources.length === 1 ? sources[0].spot_name : districts.length === 1 ? `Your ${districts[0]} trip` : 'Your Telangana trip';
    const metric = (label, value) => `<div class="tripMetric"><span>${escapeValue(label)}</span><strong>${escapeValue(value)}</strong></div>`;
    const available = value => value !== null && value !== undefined && value !== '';
    const amount = value => available(value) ? formatMoney(value) : 'Unavailable';
    const climate = ml.climate || {};
    const weather = climate.prediction || {};
    const climateParts = [];
    if (climate.status === 'success') {
        if (available(weather.Temperature_Max_C)) climateParts.push(`High ${Number(weather.Temperature_Max_C).toFixed(1)}°C`);
        if (available(weather.Temperature_Min_C)) climateParts.push(`Low ${Number(weather.Temperature_Min_C).toFixed(1)}°C`);
        if (available(weather.Rainfall_Percent)) climateParts.push(`Rainfall chance ${Number(weather.Rainfall_Percent).toFixed(1)}%`);
    }
    const crowd = ml.crowd || {};
    const transport = ml.transport || {};
    const over = budget.status === 'over_budget';
    output.innerHTML = `
        <header class="tripResultHeader">
            <span class="eyebrow">${fallback ? 'Destination guide · AI plan pending' : 'Your itinerary'}</span>
            <h2>${escapeValue(title)}</h2>
            <div class="tripFacts">
                <span>${escapeValue(requirements.duration_days || '—')} days</span>
                <span>${escapeValue(requirements.num_travelers || '—')} travelers</span>
                <span>${sources.length} stops</span>
                ${requirements.travel_date ? `<span>${escapeValue(requirements.travel_date)}</span>` : ''}
            </div>
            <a href="#planner">Edit preferences ↑</a>
        </header>
        <section class="resultCard tripStops">
            <div class="resultSectionHeading"><h3>Destinations in this trip</h3><span class="tag">${sources.length} stops</span></div>
            <ol>${sources.map(source => `<li><strong>${escapeValue(source.spot_name)}</strong><span>${escapeValue(source.district || '')}${source.knowledge_missing ? ' · Details unavailable' : ''}</span></li>`).join('')}</ol>
            ${!sources.length ? '<p class="muted">No matching destination details are available.</p>' : ''}
        </section>
        <section class="resultCard itineraryPanel">
            <div class="resultSectionHeading"><h3>${fallback ? 'Day-by-day destination guide' : 'Day-by-day itinerary'}</h3><span class="tag">${fallback ? 'From destination records' : 'AI assisted'}</span></div>
            ${fallback ? `<div class="resultContext" role="status"><strong>Personalized itinerary not generated</strong><p>${escapeValue(generationMessage)}</p><p>Your selected stops and available travel estimates are shown below.</p></div>` : ''}
            <div class="itineraryContent">${renderItineraryBlocks(data.plan)}</div>
        </section>
        <section class="resultCard budgetPanel">
            <div class="resultSectionHeading"><h3>Trip budget</h3><span class="tag ${over ? 'budgetOver' : ''}">${over ? 'Over budget' : budget.status === 'within_budget' ? 'Within budget' : 'Not available'}</span></div>
            <div class="tripMetricGrid">${metric('Your budget', amount(budget.budget_limit ?? requirements.budget_limit))}${metric('Estimated total', amount(budget.predicted_cost))}${metric(over ? 'Over budget by' : 'Remaining budget', amount(available(budget.difference) ? Math.abs(Number(budget.difference)) : null))}</div>
            <dl class="costRows">${[['Travel','travel_cost_est'],['Stay','stay_cost_est'],['Food','food_cost_est'],['Entry fees','entry_fees_est'],['Tolls & parking','tolls_and_parking_est']].map(([label,key]) => `<div><dt>${label}</dt><dd>${escapeValue(amount(costs[key]))}</dd></div>`).join('')}</dl>
            <p class="resultFootnote">Model estimates for planning; actual costs may vary.</p>
        </section>
        <section class="resultCard"><h3>Travel insights</h3><div class="travelInsights">
            <div><h4>Transport</h4><p>Selected: <strong>${escapeValue(transport.user_planned_mode || requirements.transport_mode || 'Not specified')}</strong></p><p class="muted">Model suggestion: ${escapeValue(transport.status === 'success' ? transport.prediction?.recommended_transport_mode || 'Unavailable' : 'Unavailable')}</p></div>
            <div><h4>Weather</h4><p>${escapeValue(climateParts.join(' · ') || 'Prediction unavailable')}</p><p class="muted">${escapeValue(climate.district || requirements.destination_or_district || 'Selected district')} · Model estimate</p></div>
            <div><h4>Crowd estimate</h4><p>${crowd.status === 'success' && available(crowd.prediction?.predicted_total_visitors) ? `${escapeValue(formatNumber(crowd.prediction.predicted_total_visitors))} predicted visitors` : 'Prediction unavailable'}</p><p class="muted">${escapeValue(crowd.destination || 'Selected destination')} · Applies to this destination only</p></div>
        </div></section>
        ${tools.storage?.request_saved && tools.storage?.result_saved ? `<p class="resultFootnote">${fallback ? 'Your destination guide has been saved.' : 'Your trip has been saved.'}</p>` : ''}
    `;
    output.className = 'result show';
    enhanceTripResults(output);
}

function enhanceTripResults(output) {
    const layout = document.querySelector('.plannerLayout');
    let preferences = document.querySelector('#tripPreferences');
    if (!preferences) {
        preferences = document.createElement('details');
        preferences.id = 'tripPreferences';
        const summary = document.createElement('summary');
        summary.textContent = 'Edit trip preferences';
        preferences.append(summary);
        const form = document.querySelector('#planner');
        form.before(preferences); preferences.append(form);
    }
    preferences.open = false;
    layout.classList.add('hasTrip');
    output.querySelector('a[href="#planner"]').addEventListener('click', event => {
        event.preventDefault(); preferences.open = true;
        preferences.scrollIntoView({behavior: 'smooth', block: 'start'});
        preferences.querySelector('input:not([type="hidden"]),select')?.focus({preventScroll: true});
    });
    const text = output.innerText;
    const actions = document.createElement('div'); actions.className = 'tripExportActions';
    actions.innerHTML = `<button type="button" class="btn secondary printTrip">${uiIcon('print')} Print / Save PDF</button><button type="button" class="btn secondary copyTrip">${uiIcon('copy')} Copy itinerary</button><span class="exportStatus" role="status"></span>`;
    output.querySelector('.tripResultHeader').append(actions);
    actions.querySelector('.printTrip').addEventListener('click', () => window.print());
    actions.querySelector('.copyTrip').addEventListener('click', async () => {
        const status = actions.querySelector('.exportStatus');
        try { await navigator.clipboard.writeText(text); status.textContent = 'Itinerary copied.'; }
        catch {
            status.textContent = 'Select and copy the itinerary below.';
            let field = actions.querySelector('textarea');
            if (!field) { field = document.createElement('textarea'); field.readOnly = true; field.setAttribute('aria-label', 'Itinerary to copy'); actions.append(field); }
            field.value = text; field.focus(); field.select();
        }
    });
}

// Build block-level markup after escaping text; never inject generated HTML.
function renderItineraryBlocks(markdown) {
    const inline = text => escapeValue(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    let html = '', dayOpen = false, listOpen = false;
    const closeList = () => { if (listOpen) { html += '</ul>'; listOpen = false; } };
    for (const raw of String(markdown || '').replace(/\r/g, '').split('\n')) {
        const line = raw.trim();
        if (!line) { closeList(); continue; }
        const heading = line.match(/^#{1,4}\s+(.+)/);
        if (heading) {
            closeList();
            if (dayOpen) { html += '</section>'; dayOpen = false; }
            if (/^Trip Itinerary$/i.test(heading[1])) continue;
            if (/^Day\s+\d+/i.test(heading[1])) {
                html += `<section class="itineraryDay"><h4>${inline(heading[1])}</h4>`;
                dayOpen = true;
            } else html += `<h4 class="itineraryNoteHeading">${inline(heading[1])}</h4>`;
        } else if (/^[•*-]\s+/.test(line)) {
            if (!listOpen) { html += '<ul>'; listOpen = true; }
            html += `<li>${inline(line.replace(/^[•*-]\s+/, ''))}</li>`;
        } else { closeList(); html += `<p>${inline(line)}</p>`; }
    }
    closeList();
    if (dayOpen) html += '</section>';
    return html || '<p class="muted">No itinerary text is available.</p>';
}
