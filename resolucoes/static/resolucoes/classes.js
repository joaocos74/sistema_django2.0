document.querySelectorAll('[data-classificacao]').forEach((grupo) => {
    const seletor = grupo.querySelector('[data-classe-select]');
    const campo = grupo.querySelector('[data-nova-classe]');
    const entrada = campo.querySelector('input');
    function atualizar() {
        const nova = seletor.value === 'nova';
        campo.hidden = !nova;
        entrada.disabled = !nova;
        entrada.required = nova;
    }
    seletor.required = true;
    seletor.addEventListener('change', atualizar);
    atualizar();
});
