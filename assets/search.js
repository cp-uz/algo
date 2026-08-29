(() => {
  const input = document.querySelector('#article-search');
  const output = document.querySelector('#search-results');
  if (!input || !output) return;

  let articles = [];
  fetch('assets/articles.json', { credentials: 'same-origin' })
    .then((response) => {
      if (!response.ok) throw new Error('search index unavailable');
      return response.json();
    })
    .then((data) => { articles = Array.isArray(data) ? data : []; })
    .catch(() => { articles = []; });

  const escapeHtml = (value) => String(value).replace(/[&<>"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
  input.addEventListener('input', () => {
    const query = input.value.trim().toLocaleLowerCase('uz');
    if (query.length < 2) {
      output.hidden = true;
      output.innerHTML = '';
      return;
    }
    const tokens = query.split(/\s+/).filter(Boolean);
    const matches = articles
      .map((article) => {
        const haystack = `${article.title} ${article.source_title} ${article.category} ${article.summary}`.toLocaleLowerCase('uz');
        const score = tokens.reduce((total, token) => total + (haystack.includes(token) ? 1 : 0), 0);
        return { article, score };
      })
      .filter((item) => item.score === tokens.length)
      .slice(0, 12);
    output.innerHTML = matches.length
      ? `<ul>${matches.map(({article}) => `<li><a href="${encodeURI(article.url)}"><span>${escapeHtml(article.title)}</span><small>${escapeHtml(article.category)} · ${escapeHtml(article.source_title)}</small></a></li>`).join('')}</ul>`
      : '<p>Hech narsa topilmadi.</p>';
    output.hidden = false;
  });
})();
