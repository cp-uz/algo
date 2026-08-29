(() => {
  const input = document.querySelector('#article-review-search');
  const table = document.querySelector('#article-review-table');
  if (!input || !table) return;
  input.addEventListener('input', () => {
    const query = input.value.trim().toLocaleLowerCase('uz');
    table.querySelectorAll('tbody tr').forEach((row) => {
      row.hidden = query && !row.dataset.search.includes(query);
    });
  });
})();
