'use strict';
const app = document.getElementById('cronograma-app');
const mensagem = document.getElementById('cronograma-mensagem');
app?.querySelectorAll('select[data-estabelecimento]').forEach((select) => {
    let anterior = select.value;
    select.addEventListener('change', async () => {
        select.disabled = true;
        mensagem.textContent = 'Salvando mês previsto…';
        try {
            const response = await fetch(app.dataset.urlAtualizar, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': app.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: JSON.stringify({estabelecimento_id: select.dataset.estabelecimento, mes_previsto: select.value}),
            });
            if (response.redirected) throw new Error('Sua sessão expirou. Entre novamente no sistema.');
            const data = await response.json();
            if (!response.ok || !data.sucesso) throw new Error(data.erro || 'Não foi possível salvar o mês.');
            anterior = select.value;
            window.location.reload();
        } catch (error) {
            select.value = anterior;
            select.disabled = false;
            mensagem.textContent = error instanceof SyntaxError ? 'Resposta inesperada do servidor.' : error.message;
        }
    });
});
