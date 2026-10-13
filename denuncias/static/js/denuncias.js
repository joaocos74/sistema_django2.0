'use strict';
const denunciaForm = document.getElementById('form-denuncia');
const buscarDenuncia = document.getElementById('buscar-denuncia');
const documentoBusca = document.getElementById('buscar_cnpj_input');
let buscaAtual = 0;
if (buscarDenuncia) {
    buscarDenuncia.addEventListener('click', async () => {
        const versao = ++buscaAtual;
        const documento = documentoBusca.value.trim();
        const status = document.getElementById('busca-status');
        document.getElementById('id_cadastro_id').value = '';
        if (!documento) { status.textContent = 'Informe um CNPJ ou CPF.'; return; }
        buscarDenuncia.disabled = true;
        try {
            const response = await fetch(`${denunciaForm.dataset.buscarUrl}?cnpj=${encodeURIComponent(documento)}`, {credentials: 'same-origin'});
            if (response.redirected) throw new Error('Sua sessão expirou. Entre novamente.');
            const data = await response.json();
            if (versao !== buscaAtual) return;
            if (!response.ok) throw new Error(data.erro || 'Não foi possível consultar o cadastro.');
            const dados = data.existe ? data.dados : {cnpj: documento};
            for (const campo of ['cnpj', 'razao_social', 'nome_fantasia', 'endereco']) {
                const input = document.getElementById(`id_${campo}`);
                input.value = dados[campo] || '';
                input.disabled = false;
                input.readOnly = data.existe;
            }
            document.getElementById('id_cadastro_id').value = dados.id || '';
            status.textContent = data.existe ? `Estabelecimento encontrado: cadastro ${dados.id}. A denúncia será vinculada a ele.` : 'Local não cadastrado. Preencha os dados para registrar uma denúncia sem vínculo.';
        } catch (error) {
            if (versao === buscaAtual) status.textContent = error.message;
        } finally { buscarDenuncia.disabled = false; }
    });
    documentoBusca.addEventListener('keydown', event => {
        if (event.key === 'Enter') { event.preventDefault(); buscarDenuncia.click(); }
    });
    documentoBusca.addEventListener('input', () => { buscaAtual++; });
    document.getElementById('id_cnpj').addEventListener('input', () => {
        buscaAtual++;
        document.getElementById('id_cadastro_id').value = '';
    });
}
