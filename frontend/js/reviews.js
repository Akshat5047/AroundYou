document.querySelector('#reviewForm').onsubmit = async event => {
    event.preventDefault();
    const loading = document.querySelector('#load'), output = document.querySelector('#out'), error = document.querySelector('#err');
    if (loading.classList.contains('show')) return;
    loading.className = 'loading show'; output.className = 'answer'; error.className = 'error';
    try {
        const data = await apiPost('/api/reviews/classify', {review: document.querySelector('#review').value.trim()});
        const raw = String(data.label || data.predicted_class || 'unverified').toLowerCase();
        const label = ['genuine', 'deceptive'].includes(raw) ? raw : 'unverified';
        const percentage = value => value == null || !Number.isFinite(Number(value)) ? 'Unavailable' : `${Math.round(Math.max(0, Math.min(1, Number(value))) * 100)}%`;
        const title = {genuine: 'Leans toward genuine', deceptive: 'Potentially deceptive', unverified: 'No clear trust signal'}[label];
        const description = {genuine: 'The wording resembles reviews the model classifies as genuine.', deceptive: 'The wording resembles reviews the model classifies as deceptive. Consider checking other sources.', unverified: 'There is not enough information here for a clear classification.'}[label];
        output.innerHTML = `<div class="analysisFinding"><span class="eyebrow">Review assessment</span><h2>${title}</h2><span class="trustBadge ${label}">AI trust signal</span><p>${description}</p><p class="resultFootnote">This prediction does not verify the review or prove deception.</p></div><details class="technicalDetails"><summary>Confidence & model details</summary><div class="metrics"><div class="metric">Model confidence<b>${percentage(data.confidence)}</b></div><div class="metric">Genuine class<b>${percentage(data.probabilities?.genuine)}</b></div><div class="metric">Deceptive class<b>${percentage(data.probabilities?.deceptive)}</b></div></div><p class="resultFootnote">Confidence reflects the model output, not the probability that the review is true.</p></details>`;
        output.className = 'answer show';
    } catch (failure) { error.textContent = failure.message || 'Unable to analyze this review.'; error.className = 'error show'; }
    finally { loading.className = 'loading'; }
};
