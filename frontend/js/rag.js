// All quick questions share the same safe answer presentation.
const q = document.querySelector('#q');
const qp = new URLSearchParams(location.search).get('q');
if (qp) q.value = qp;
document.querySelector('#ask').onsubmit = async event => {
    event.preventDefault();
    const question = q.value.trim();
    if (!question) { q.focus(); return; }
    const loading = document.querySelector('#load');
    if (loading.classList.contains('show')) return;
    const output = document.querySelector('#out');
    const error = document.querySelector('#err');
    const button = event.currentTarget.querySelector('button[type="submit"]');
    const label = button.textContent;
    button.disabled = true;
    button.textContent = 'Finding an answer…';
    loading.className = 'loading show';
    output.className = 'answer';
    error.className = 'error';
    try {
        const data = await apiPost('/api/rag/ask', {question});
        renderAnswer({...data, question: data.question || question}, output);
    } catch (failure) {
        error.textContent = failure.message || 'Unable to get an answer. Please try again.';
        error.className = 'error show';
    } finally {
        loading.className = 'loading';
        button.disabled = false;
        button.textContent = label;
    }
};
