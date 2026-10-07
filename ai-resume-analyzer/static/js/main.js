// Show a loading state while the (first) analysis runs.
const form = document.getElementById('analyze-form');
if (form) {
  form.addEventListener('submit', () => {
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = 'Analyzing... please wait';
  });
}
// Auto-hide flash messages
document.querySelectorAll('.flash').forEach(el => setTimeout(() => el.remove(), 6000));
