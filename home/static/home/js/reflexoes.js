(() => {
  'use strict';
  const widget = document.getElementById('reflexoes');
  if (!widget) return;
  const button = document.getElementById('reflexao-abrir');
  const panel = document.getElementById('reflexao-balao');
  const title = document.getElementById('reflexao-titulo');
  const body = document.getElementById('reflexao-texto');
  const source = document.getElementById('reflexao-fonte');
  const status = document.getElementById('reflexao-status');
  let lastId = '', controller = null, version = 0;
  widget.hidden = false;

  function position() {
    if (panel.hidden) return;
    const anchor = button.getBoundingClientRect();
    const viewport = window.visualViewport;
    const width = viewport?.width || window.innerWidth;
    const height = viewport?.height || window.innerHeight;
    const offsetX = viewport?.offsetLeft || 0;
    const offsetY = viewport?.offsetTop || 0;
    const top = Math.max(offsetY + 12, Math.min(anchor.bottom + 10, offsetY + height - 260));
    panel.style.width = Math.min(440, width - 24) + 'px';
    panel.style.left = Math.max(offsetX + 12, Math.min(anchor.right - panel.offsetWidth, offsetX + width - panel.offsetWidth - 12)) + 'px';
    panel.style.top = top + 'px';
    panel.style.maxHeight = Math.min(560, offsetY + height - top - 12) + 'px';
  }

  function close(restoreFocus = false) {
    version++;
    controller?.abort();
    panel.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    if (restoreFocus) button.focus();
  }

  button.addEventListener('click', async () => {
    controller?.abort();
    controller = new AbortController();
    const current = ++version;
    panel.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    title.textContent = 'A arte de viver';
    body.replaceChildren();
    source.textContent = '';
    status.textContent = 'Buscando uma reflexão…';
    panel.setAttribute('aria-busy', 'true');
    position();
    panel.focus({preventScroll: true});
    try {
      const url = new URL(button.dataset.url, window.location.origin);
      if (lastId) url.searchParams.set('anterior', lastId);
      const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin', cache: 'no-store'});
      if (response.redirected) throw new Error('Sua sessão expirou. Entre novamente no sistema para continuar.');
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Não foi possível carregar a reflexão. Clique no ícone para tentar novamente.');
      }
      const data = await response.json();
      if (current !== version || panel.hidden) return;
      title.textContent = data.titulo;
      body.replaceChildren(...data.paragrafos.map(text => {
        const paragraph = document.createElement('p');
        paragraph.textContent = text;
        return paragraph;
      }));
      source.textContent = data.fonte + ' ' + data.paginas + '.';
      lastId = String(data.id);
      status.textContent = '';
      body.scrollTop = 0;
      position();
    } catch (error) {
      if (current !== version || error.name === 'AbortError') return;
      status.textContent = error.message || 'Falha de conexão. Clique no ícone para tentar novamente.';
    } finally {
      if (current === version) panel.setAttribute('aria-busy', 'false');
    }
  });
  document.getElementById('reflexao-fechar').addEventListener('click', () => close(true));
  document.addEventListener('pointerdown', event => {
    if (!panel.hidden && !widget.contains(event.target)) close(panel.contains(document.activeElement));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) { event.preventDefault(); close(true); }
  });
  window.addEventListener('resize', position);
  window.addEventListener('scroll', position, {passive: true});
  window.visualViewport?.addEventListener('resize', position);
  window.visualViewport?.addEventListener('scroll', position);
})();
