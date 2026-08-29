(() => {
  const form = document.querySelector('[data-editor]');
  if (!form) return;
  const textarea = form.querySelector('#article-body');
  const preview = form.querySelector('#article-preview');
  const state = form.querySelector('#preview-state');
  const endpoint = form.dataset.previewUrl;
  const csrf = form.dataset.csrf;
  let timer = null;
  let controller = null;

  async function updatePreview() {
    if (controller) controller.abort();
    controller = new AbortController();
    state.textContent = 'Yangilanmoqda…';
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({body: textarea.value}),
        signal: controller.signal
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Preview xatosi');
      preview.innerHTML = data.html;
      state.textContent = 'Yangilandi';
      if (window.MathJax?.typesetPromise) window.MathJax.typesetPromise([preview]);
    } catch (error) {
      if (error.name === 'AbortError') return;
      state.textContent = error.message;
    }
  }
  textarea.addEventListener('input', () => {
    window.clearTimeout(timer);
    state.textContent = 'Kutilmoqda…';
    timer = window.setTimeout(updatePreview, 500);
  });
})();
