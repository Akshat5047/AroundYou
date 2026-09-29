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
        rememberAnswer({...data, question: data.question || question});
    } catch (failure) {
        error.textContent = failure.message || 'Unable to get an answer. Please try again.';
        error.className = 'error show';
    } finally {
        loading.className = 'loading';
        button.disabled = false;
        button.textContent = label;
    }
};

// History is stored only for this browser tab's session, never sent to the API.
let answerHistory = [];
try {
    const saved = JSON.parse(sessionStorage.getItem('aroundYouAnswers') || '[]');
    if (Array.isArray(saved)) answerHistory = saved.filter(item => typeof item.question === 'string' && typeof item.answer === 'string').slice(-20);
} catch { /* Storage can be unavailable in private browsers. */ }
const historyPanel = document.createElement('details');
historyPanel.className = 'answerHistory formCard';
historyPanel.innerHTML = '<summary>Recent questions <span class="historyCount"></span></summary><p class="muted">Saved in this tab for this session.</p><div class="historyList"></div><button type="button" class="btn secondary clearHistory">Clear history</button>';
document.querySelector('.askMain').append(historyPanel);
historyPanel.querySelector('.clearHistory').addEventListener('click', () => {
    answerHistory = []; try { sessionStorage.removeItem('aroundYouAnswers'); } catch {}
    refreshAnswerHistory();
});
function refreshAnswerHistory() {
    historyPanel.hidden = !answerHistory.length;
    historyPanel.querySelector('.historyCount').textContent = `(${answerHistory.length})`;
    const list = historyPanel.querySelector('.historyList'); list.replaceChildren();
    [...answerHistory].reverse().forEach(answer => {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'historyQuestion'; button.textContent = answer.question;
        button.addEventListener('click', () => {
            renderAnswer(answer, document.querySelector('#out'));
            document.querySelector('#err').classList.remove('show');
            document.querySelector('#out').scrollIntoView({behavior: 'smooth', block: 'start'});
        });
        list.append(button);
    });
}
function rememberAnswer(answer) {
    answerHistory.push({question: answer.question, answer: answer.answer, sources: answer.sources || []});
    answerHistory = answerHistory.slice(-20);
    try { sessionStorage.setItem('aroundYouAnswers', JSON.stringify(answerHistory)); } catch {}
    refreshAnswerHistory();
}
refreshAnswerHistory();
