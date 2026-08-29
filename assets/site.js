(() => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('#site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  document.querySelectorAll('.copy-code').forEach((button) => {
    button.addEventListener('click', async () => {
      const code = button.closest('.code-block')?.querySelector('code');
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.textContent || '');
        const original = button.textContent;
        button.textContent = 'Nusxalandi';
        button.classList.add('copied');
        window.setTimeout(() => {
          button.textContent = original;
          button.classList.remove('copied');
        }, 1600);
      } catch (_) {
        button.textContent = 'Xatolik';
      }
    });
  });

  document.querySelectorAll('[data-table-filter]').forEach((input) => {
    const table = document.getElementById(input.dataset.tableFilter || '');
    if (!table) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    input.addEventListener('input', () => {
      const query = input.value.trim().toLocaleLowerCase('uz');
      rows.forEach((row) => {
        row.hidden = query.length > 0 && !row.textContent.toLocaleLowerCase('uz').includes(query);
      });
    });
  });

  const tocLinks = Array.from(document.querySelectorAll('.toc-card a[href^="#"]'));
  if ('IntersectionObserver' in window && tocLinks.length) {
    const byId = new Map(tocLinks.map((link) => [decodeURIComponent(link.hash.slice(1)), link]));
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (!visible.length) return;
      tocLinks.forEach((link) => link.classList.remove('active'));
      byId.get(visible[0].target.id)?.classList.add('active');
    }, { rootMargin: '-90px 0px -70% 0px', threshold: [0, 1] });
    byId.forEach((_, id) => {
      const heading = document.getElementById(id);
      if (heading) observer.observe(heading);
    });
  }
})();
