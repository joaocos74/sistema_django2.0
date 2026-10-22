(() => {
  'use strict';
  const card = document.getElementById('lembretes');
  if (!card) return;
  const form = document.getElementById('lembrete-novo');
  const input = form.elements.texto;
  const list = document.getElementById('lembretes-lista');
  const feedback = document.getElementById('lembrete-retorno');
  const token = form.elements.csrfmiddlewaretoken.value;
  const say = (text, error = false) => {
    feedback.textContent = text;
    feedback.dataset.erro = String(error);
  };
  const count = () => {
    const total = list.children.length;
    document.getElementById('lembretes-total').textContent = String(total);
    document.getElementById('lembretes-vazio').hidden = total > 0;
  };
  async function post(target) {
    const response = await fetch(target.action, {
      method: 'POST', body: new FormData(target), credentials: 'same-origin',
      headers: {'X-Requested-With': 'XMLHttpRequest'},
    });
    if (response.redirected || !response.headers.get('content-type')?.includes('application/json')) {
      throw new Error('Sua sessão pode ter expirado. Recarregue a página para continuar.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.erro || 'Não foi possível salvar. Tente novamente.');
    return data;
  }
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (form.dataset.enviando === 'true') return;
    if (!input.value.trim()) { say('Digite um lembrete.', true); input.focus(); return; }
    form.dataset.enviando = 'true';
    const button = form.querySelector('button');
    button.disabled = true;
    input.readOnly = true;
    say('Salvando…');
    try {
      const data = await post(form);
      const item = document.createElement('li');
      item.className = 'lembrete-item';
      const complete = document.createElement('form');
      complete.method = 'post'; complete.action = data.concluir_url; complete.className = 'lembrete-concluir';
      const csrf = document.createElement('input');
      csrf.type = 'hidden'; csrf.name = 'csrfmiddlewaretoken'; csrf.value = token;
      const circle = document.createElement('button');
      circle.type = 'submit'; circle.className = 'lembrete-circulo';
      circle.setAttribute('aria-label', `Concluir lembrete: ${data.texto}`);
      const tick = document.createElement('span'); tick.textContent = '✓'; tick.setAttribute('aria-hidden', 'true');
      circle.append(tick); complete.append(csrf, circle);
      const text = document.createElement('span'); text.className = 'lembrete-texto'; text.textContent = data.texto;
      item.append(complete, text); list.append(item);
      input.value = ''; count(); say('Lembrete adicionado.');
      list.scrollTop = list.scrollHeight;
    } catch (error) { say(error.message || 'Falha de conexão. Tente novamente.', true); }
    finally { button.disabled = false; input.readOnly = false; form.dataset.enviando = 'false'; input.focus(); }
  });
  list.addEventListener('submit', async (event) => {
    const target = event.target.closest('.lembrete-concluir');
    if (!target) return;
    event.preventDefault();
    const button = target.querySelector('button');
    if (button.disabled) return;
    button.disabled = true;
    try {
      await post(target);
      const item = target.closest('li');
      const next = item.nextElementSibling?.querySelector('button') || item.previousElementSibling?.querySelector('button');
      item.remove(); count(); say('Lembrete concluído.'); (next || input).focus();
    } catch (error) { button.disabled = false; say(error.message || 'Falha de conexão. Tente novamente.', true); }
  });
})();
