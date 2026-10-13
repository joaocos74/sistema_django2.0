'use strict';

// Expande os blocos antes da impressão e restaura a escolha do usuário depois.
let paineisParaImpressao = null;
window.addEventListener('beforeprint', () => {
    if (paineisParaImpressao) return;
    paineisParaImpressao = [...document.querySelectorAll('.analysis-panel')].map((painel) => [painel, painel.open]);
    paineisParaImpressao.forEach(([painel]) => { painel.open = true; });
});
window.addEventListener('afterprint', () => {
    paineisParaImpressao?.forEach(([painel, aberto]) => { painel.open = aberto; });
    paineisParaImpressao = null;
});
document.getElementById('imprimir')?.addEventListener('click', () => window.print());
document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
        if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
});

function abrirBlocos(elemento) {
    let painel = elemento.closest('details');
    while (painel) {
        painel.open = true;
        painel = painel.parentElement?.closest('details');
    }
}
// Campos inválidos não podem ficar escondidos durante a validação do navegador.
document.addEventListener('invalid', (event) => abrirBlocos(event.target), true);
document.querySelectorAll('.errorlist').forEach(abrirBlocos);

// Os mesmos pares são validados no servidor; o JS apenas orienta o preenchimento.
document.querySelectorAll('[data-status-target]').forEach((acao) => {
    const status = document.getElementById(acao.dataset.statusTarget);
    if (!status) return;
    const label = status.labels?.[0];
    const indicador = document.createElement('span');
    label?.append(indicador);
    function atualizarStatus() {
        const aplicado = acao.value === 'aplicado';
        status.disabled = !aplicado;
        status.required = aplicado;
        indicador.textContent = aplicado ? ' *' : '';
        if (!aplicado) status.value = '';
    }
    acao.addEventListener('change', atualizarStatus);
    atualizarStatus();
});
