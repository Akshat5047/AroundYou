const reviewForm = document.querySelector('#reviewForm');
const reviewInput = document.querySelector('#review');
const sampleReview = document.querySelector('#sampleReview');
sampleReview.addEventListener('click', () => {
    if (document.querySelector('#load').classList.contains('show')) return;
    reviewInput.value = 'We stayed at this hotel for two nights. Our room was clean and the bed was comfortable, but noise from the corridor woke us early. Check-in took about twenty minutes. The receptionist helped us arrange a taxi and breakfast had a reasonable selection.';
    reviewForm.requestSubmit();
});
reviewInput.addEventListener('input', () => {
    document.querySelector('#out').className = 'answer';
    document.querySelector('#err').className = 'error';
});
reviewForm.onsubmit = async event => {
    event.preventDefault();
    const loading = document.querySelector('#load'), output = document.querySelector('#out'), error = document.querySelector('#err');
    if (loading.classList.contains('show')) return;
    loading.className = 'loading show'; output.className = 'answer'; error.className = 'error';
    const submittedReview = reviewInput.value.trim();
    sampleReview.disabled = true;
    reviewInput.readOnly = true;
    try {
        if (submittedReview.length < 3) throw new Error('Please enter a review before analyzing.');
        const data = await apiPost('/api/reviews/classify', {review: submittedReview});
        const raw = String(data.label || data.predicted_class || 'unverified').toLowerCase();
        const label = ['genuine', 'deceptive'].includes(raw) ? raw : 'unverified';
        const percentage = value => value == null || !Number.isFinite(Number(value)) ? 'Unavailable' : `${Math.round(Math.max(0, Math.min(1, Number(value))) * 100)}%`;
        const title = {genuine: 'Leans toward genuine', deceptive: 'Potentially deceptive', unverified: 'No clear trust signal'}[label];
        const description = {genuine: 'The wording resembles reviews the model classifies as genuine.', deceptive: 'The wording resembles reviews the model classifies as deceptive. Consider checking other sources.', unverified: 'There is not enough information here for a clear classification.'}[label];
        const hasScores = data.confidence != null;
        output.innerHTML = `<div class="analysisFinding"><span class="eyebrow">Review assessment</span><h2>${title}</h2><p>${esc(data.reason || description)}</p></div>${hasScores ? `<div class="metrics"><div class="metric">Genuine wording score<b>${percentage(data.probabilities?.genuine)}</b></div><div class="metric">Deceptive wording score<b>${percentage(data.probabilities?.deceptive)}</b></div></div>` : ''}<details class="technicalDetails"><summary>How to interpret this result</summary><p>This model was trained on English hotel reviews. Other travel reviews may not match its training examples.</p><p>A class must reach ${percentage(data.threshold ?? 0.7)} before a label is shown. Scores reflect wording patterns, not the probability that a review is true. Positive or negative sentiment alone does not establish trustworthiness.</p></details><p class="resultFootnote">Compare other reviews and specific details before deciding. This assessment cannot verify a visit or prove deception.</p>`;
        output.className = 'answer show';
    } catch (failure) { error.textContent = failure.message || 'Unable to analyze this review.'; error.className = 'error show'; }
    finally { loading.className = 'loading'; sampleReview.disabled = false; reviewInput.readOnly = false; }
};
