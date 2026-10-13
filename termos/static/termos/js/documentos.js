'use strict';

const padraoSalvo = JSON.parse(document.getElementById('padrao-salvo').textContent);
const editaveisPadrao = [...document.querySelectorAll('textarea[name], input[type="checkbox"][name], [data-padrao]')];
for (const campo of editaveisPadrao) {
    const nome = campo.name || campo.dataset.padrao;
    if (!Object.hasOwn(padraoSalvo, nome)) continue;
    if (campo.type === 'checkbox') campo.checked = padraoSalvo[nome];
    else if (campo.dataset.padrao) campo.textContent = padraoSalvo[nome];
    else campo.value = padraoSalvo[nome];
}
const salvarPadrao = document.getElementById('salvar-padrao');
const statusPadrao = document.getElementById('padrao-status');
editaveisPadrao.forEach(campo => campo.addEventListener('input', () => {
    statusPadrao.textContent = 'Alterações ainda não salvas no padrão.';
}));
salvarPadrao?.addEventListener('click', async () => {
    const dados = new FormData();
    dados.set('csrfmiddlewaretoken', document.querySelector('[name="csrfmiddlewaretoken"]').value);
    const token = document.querySelector('[name="emissao_token"]');
    if (token) dados.set('emissao_token', token.value);
    dados.set('autoridades_extras', JSON.stringify([...document.querySelectorAll('#extra-authorities .sig-row, #extra-authorities tr')].map(row => {
        const valores = row.querySelectorAll('[contenteditable]');
        if (row.tagName === 'TR') return {nome: valores[0].innerText, matricula: valores[1].innerText, funcao: valores[2].innerText};
        return {nome: valores[0].innerText, funcao: valores[1].innerText};
    })));
    for (const campo of editaveisPadrao) {
        const nome = campo.name || campo.dataset.padrao;
        dados.set(nome, campo.type === 'checkbox' ? (campo.checked ? 'True' : 'False') :
            (campo.dataset.padrao ? campo.innerText : campo.value));
    }
    salvarPadrao.disabled = true;
    statusPadrao.textContent = salvarPadrao.dataset.gerar ? 'Gerando notificação…' : 'Salvando padrão…';
    try {
        const response = await fetch(window.location.pathname, {method: 'POST', body: dados, credentials: 'same-origin'});
        const resultado = await response.json();
        if (response.ok && resultado.url) { window.location.assign(resultado.url); return; }
        statusPadrao.textContent = response.ok ? resultado.mensagem : resultado.erro;
    } catch {
        statusPadrao.textContent = 'Não foi possível salvar. Verifique a conexão e tente novamente.';
    } finally {
        salvarPadrao.disabled = false;
    }
});

const campos = document.querySelectorAll('textarea.field-editable');
for (const campo of campos) {
    const impresso = document.createElement('div');
    impresso.className = 'print-value';
    campo.after(impresso);
    function atualizar() {
        impresso.textContent = campo.value;
        campo.style.height = 'auto';
        campo.style.height = `${campo.scrollHeight + 2}px`;
    }
    campo.addEventListener('input', atualizar);
    window.addEventListener('beforeprint', atualizar);
    atualizar();
}
document.getElementById('imprimir-auto')?.addEventListener('click', () => window.print());
function adicionarAutoridade(nome = '', funcao = 'Autoridade Sanitária', matricula = '') {
    if (document.getElementById('extra-authorities').tagName === 'TBODY') {
        const row = document.createElement('tr');
        for (const [index, texto] of [nome, matricula, funcao, ''].entries()) {
            const td = document.createElement('td');
            if (index < 3) {
                const campo = document.createElement('span');
                campo.className = 'field-value'; campo.contentEditable = 'true'; campo.textContent = texto;
                campo.setAttribute('aria-label', ['Nome da autoridade', 'Matrícula', 'Cargo / função'][index]);
                td.append(campo);
            }
            row.append(td);
        }
        document.getElementById('extra-authorities').append(row);
        return;
    }
    const row = document.createElement('div');
    row.className = 'sig-row';
    for (const [rotulo, texto, editavel] of [
        ['AUTORIDADE SANITÁRIA', nome, true], ['FUNÇÃO', funcao, true], ['ASSINATURA', '', false]
    ]) {
        const col = document.createElement('div'); col.className = 'sig-col';
        const campo = document.createElement('div'); campo.className = editavel ? 'sig-editable' : 'sig-line';
        if (editavel) { campo.contentEditable = 'true'; campo.setAttribute('aria-label', rotulo); }
        campo.textContent = texto;
        const label = document.createElement('span'); label.className = 'sig-label'; label.textContent = rotulo;
        col.append(campo, label); row.append(col);
    }
    document.getElementById('extra-authorities').append(row);
}
for (const autoridade of padraoSalvo.autoridades_extras || []) adicionarAutoridade(autoridade.nome, autoridade.funcao, autoridade.matricula);
document.getElementById('adicionar-autoridade')?.addEventListener('click', () => {
    if (document.getElementById('extra-authorities').children.length >= 20) {
        statusPadrao.textContent = 'Limite de 20 autoridades adicionais.';
        return;
    }
    adicionarAutoridade();
    statusPadrao.textContent = 'Alterações ainda não salvas no padrão.';
});
document.getElementById('extra-authorities').addEventListener('input', () => {
    statusPadrao.textContent = 'Alterações ainda não salvas no padrão.';
});
if (document.querySelector('[data-emitida]')) {
    document.querySelectorAll('[contenteditable]').forEach(el => el.contentEditable = 'false');
    document.querySelectorAll('textarea').forEach(el => el.readOnly = true);
    document.querySelectorAll('input[type="checkbox"]').forEach(el => el.disabled = true);
}
