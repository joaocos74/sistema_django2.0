document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    console.log("REDESIM JS v2 carregado");

    // =========================================================
    // ELEMENTO PRINCIPAL
    // =========================================================

    const app = document.getElementById("redesim-app");

    if (!app) {
        console.error("REDESIM: elemento #redesim-app não encontrado.");
        return;
    }

    // =========================================================
    // URLS GERADAS PELO DJANGO
    // =========================================================

    const urlBuscar = app.dataset.urlBuscar;
    const urlListar = app.dataset.urlListar;

    // =========================================================
    // ELEMENTOS
    // =========================================================

    const form = document.getElementById("form-redesim");

    const inputBusca = document.getElementById("buscar_documento");
    const btnBuscar = document.getElementById("btn-buscar");
    const btnSalvar = document.getElementById("btn-salvar");

    const statusBusca = document.getElementById("status-busca");



    const btnExportar =
        document.getElementById("btn-exportar");

    const resultados =
        document.getElementById("redesim_resultados");

    const corpoTabela =
        document.getElementById("corpo_redesim");

    const mensagemVazia =
        document.getElementById("redesim-vazio");

    // =========================================================
    // CAMPOS DO FORMULÁRIO
    // =========================================================

    const campos = {
        estabelecimentoId:
            document.getElementById("estabelecimento_id"),

        razaoSocial:
            document.getElementById("razao_social"),

        nomeFantasia:
            document.getElementById("nome_fantasia"),

        nivel:
            document.getElementById("nivel"),

        classe:
            document.getElementById("classe"),

        documento:
            document.getElementById("cnpj_ou_cpf"),

        cnaePrincipal:
            document.getElementById("cnae_principal"),

        alvara:
            document.getElementById("alvara"),

        fiscalResponsavel:
            document.getElementById("fiscal_responsavel"),

        observacoes:
            document.getElementById("observacoes"),
    };

    const camposEditaveis =
        document.querySelectorAll(".campo-editavel-redesim");

    // =========================================================
    // VERIFICAÇÃO
    // =========================================================

    if (
        !form ||
        !inputBusca ||
        !btnBuscar ||
        !btnSalvar ||
        !statusBusca ||
        !btnExportar
    ) {
        console.error(
            "REDESIM: existem elementos obrigatórios ausentes no HTML."
        );

        return;
    }

    // =========================================================
    // STATUS
    // =========================================================

    function definirStatus(mensagem, tipo) {
        statusBusca.textContent = mensagem || "";

        statusBusca.className = "search-status";

        if (tipo) {
            statusBusca.classList.add(
                "search-status--" + tipo
            );
        }
    }

    // =========================================================
    // HABILITAR / BLOQUEAR FORMULÁRIO
    // =========================================================

    function habilitarFormulario(habilitar) {
        camposEditaveis.forEach(function (campo) {
            campo.disabled = !habilitar;
        });

        btnSalvar.disabled = !habilitar;
    }

    // =========================================================
    // LIMPAR DADOS
    // =========================================================

    function limparFormulario() {
        campos.estabelecimentoId.value = "";
        campos.razaoSocial.value = "";
        campos.nomeFantasia.value = "";
        campos.nivel.value = "";
        campos.classe.value = "";
        campos.documento.value = "";
        campos.cnaePrincipal.value = "";
        campos.alvara.value = "";
        campos.fiscalResponsavel.value = "";
        campos.observacoes.value = "";

        habilitarFormulario(false);
    }

    // =========================================================
    // PREENCHER DADOS
    // =========================================================

    function preencherFormulario(dados) {
        campos.estabelecimentoId.value =
            dados.id || "";

        campos.razaoSocial.value =
            dados.razao_social || "";

        campos.nomeFantasia.value =
            dados.nome_fantasia || "";

        campos.nivel.value =
            dados.nivel || "";

        campos.classe.value =
            dados.classe || "";

        campos.documento.value =
            dados.cnpj_ou_cpf || "";

        campos.cnaePrincipal.value =
            dados.cnae_principal || "";

        campos.alvara.value =
            dados.alvara || "";

        campos.fiscalResponsavel.value =
            dados.fiscal_responsavel || "";

        campos.observacoes.value =
            dados.observacoes || "";

        habilitarFormulario(true);
    }

    // =========================================================
    // BUSCAR CNPJ / CPF
    // =========================================================

    async function buscarEstabelecimento() {
        const documento = inputBusca.value.trim();

        limparFormulario();

        if (!documento) {
            definirStatus(
                "Digite um CNPJ ou CPF.",
                "erro"
            );

            inputBusca.focus();

            return;
        }

        btnBuscar.disabled = true;

        definirStatus(
            "Buscando estabelecimento...",
            "info"
        );

        try {
            const parametros =
                new URLSearchParams();

            parametros.append(
                "documento",
                documento
            );

            const response = await fetch(
                urlBuscar + "?" + parametros.toString(),
                {
                    method: "GET",

                    headers: {
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },

                    credentials: "same-origin",
                }
            );

            if (!response.ok) {
                throw new Error(
                    "Erro HTTP: " + response.status
                );
            }

            const data = await response.json();

            // =================================================
            // NÃO ENCONTRADO
            // =================================================

            if (!data.existe) {
                limparFormulario();

                definirStatus(
                    data.mensagem ||
                    "Estabelecimento não encontrado.",
                    "erro"
                );

                return;
            }

            // =================================================
            // ENCONTRADO
            // =================================================

            preencherFormulario(
                data.dados
            );

            definirStatus(
                `Pasta ${data.dados.numero_pasta}: estabelecimento encontrado. Dados carregados.`,
                "sucesso"
            );

        } catch (erro) {
            console.error(
                "Erro na busca REDESIM:",
                erro
            );

            limparFormulario();

            definirStatus(
                "Não foi possível consultar o estabelecimento.",
                "erro"
            );

        } finally {
            btnBuscar.disabled = false;
        }
    }

    // =========================================================
    // CRIAR CÉLULA
    // =========================================================

    function criarCelula(linha, valor) {
        const td = document.createElement("td");

        td.textContent =
            valor === null || valor === undefined
                ? ""
                : valor;

        linha.appendChild(td);
    }

    // =========================================================
    // RENDERIZAR LIBERADOS
    // =========================================================

    function renderizarLiberados(dados) {
        corpoTabela.innerHTML = "";

        if (!Array.isArray(dados)) {
            dados = [];
        }

        dados.forEach(function (registro) {
            const linha =
                document.createElement("tr");

            criarCelula(
                linha,
                registro.numero_pasta
            );

            criarCelula(
                linha,
                registro.nivel
            );

            criarCelula(
                linha,
                registro.classe
            );

            criarCelula(
                linha,
                registro.razao_social
            );

            criarCelula(
                linha,
                registro.cnpj_ou_cpf
            );

            criarCelula(
                linha,
                registro.alvara
            );

            criarCelula(linha, registro.fiscal_liberacao);

            corpoTabela.appendChild(
                linha
            );
        });

        resultados.hidden = false;

        if (dados.length === 0) {
            mensagemVazia.hidden = false;

            mensagemVazia.textContent =
                "Nenhum registro REDESIM encontrado.";

            btnExportar.disabled = true;

        } else {
            mensagemVazia.hidden = true;
            btnExportar.disabled = false;
        }
    }

    // =========================================================
    // VER LIBERADOS
    // =========================================================

    async function verLiberados() {


        try {
            const response =
                await fetch(
                    urlListar,
                    {
                        method: "GET",

                        headers: {
                            "Accept": "application/json",
                            "X-Requested-With":
                                "XMLHttpRequest",
                        },

                        credentials:
                            "same-origin",
                    }
                );

            if (!response.ok) {
                throw new Error(
                    "Erro HTTP: " +
                    response.status
                );
            }

            const dados =
                await response.json();

            renderizarLiberados(
                dados
            );

        } catch (erro) {
            console.error(
                "Erro ao listar REDESIM:",
                erro
            );

            resultados.hidden = false;

            corpoTabela.innerHTML = "";

            mensagemVazia.hidden = false;

            mensagemVazia.textContent =
                "Não foi possível carregar os registros REDESIM.";

            btnExportar.disabled = true;

        }
    }

    // =========================================================
    // EXPORTAR EXCEL
    // =========================================================

    function exportarExcel() {
        const tabela =
            document.getElementById(
                "tabela_redesim"
            );

        if (
            !tabela ||
            corpoTabela.children.length === 0
        ) {
            return;
        }

        const copia = tabela.cloneNode(true);
        copia.querySelectorAll('td').forEach(celula => {
            celula.style.setProperty('mso-number-format', '"\\@"');
            if (/^[\s]*[=+@-]/.test(celula.textContent)) {
                celula.textContent = "'" + celula.textContent;
            }
        });
        const html =
            "\ufeff" +
            "<html>" +
            "<head>" +
            '<meta charset="UTF-8">' +
            "</head>" +
            "<body>" +
            copia.outerHTML +
            "</body>" +
            "</html>";

        const blob =
            new Blob(
                [html],
                {
                    type:
                        "application/vnd.ms-excel;charset=utf-8;",
                }
            );

        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = url;
        link.download = "redesim.xls";

        document.body.appendChild(link);

        link.click();

        document.body.removeChild(link);

        URL.revokeObjectURL(url);
    }

    // =========================================================
    // EVENTOS
    // =========================================================

    btnBuscar.addEventListener(
        "click",
        function () {
            buscarEstabelecimento();
        }
    );

    btnExportar.addEventListener(
        "click",
        function () {
            exportarExcel();
        }
    );

    // =========================================================
    // ENTER NO CAMPO CNPJ / CPF
    // =========================================================

    inputBusca.addEventListener(
        "keydown",
        function (event) {
            if (event.key === "Enter") {
                event.preventDefault();

                buscarEstabelecimento();
            }
        }
    );

    // =========================================================
    // ALTEROU O DOCUMENTO?
    // EXIGE NOVA PESQUISA
    // =========================================================

    inputBusca.addEventListener(
        "input",
        function () {
            if (
                campos.estabelecimentoId.value
            ) {
                limparFormulario();

                definirStatus(
                    "Documento alterado. Faça uma nova busca.",
                    "info"
                );
            }
        }
    );

    // =========================================================
    // VALIDAÇÃO ANTES DE SALVAR
    // =========================================================

    form.addEventListener(
        "submit",
        function (event) {
            if (
                !campos.estabelecimentoId.value ||
                !campos.documento.value
            ) {
                event.preventDefault();

                definirStatus(
                    "Pesquise um estabelecimento antes de salvar.",
                    "erro"
                );

                inputBusca.focus();

                return;
            }

            btnSalvar.disabled = true;
            btnSalvar.textContent = "Salvando...";
        }
    );

    // =========================================================
    // ESTADO INICIAL
    // =========================================================

    limparFormulario();
    verLiberados();

    console.log(
        "REDESIM: eventos dos botões registrados."
    );
});
