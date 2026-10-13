'use strict';
// home/static/home/js/agenda.js
let usuariosDisponiveis = [];
let diasSemana = [];
const itensPorId = new Map();

const board = document.getElementById("agenda-grid");
const btnRecarregar = document.getElementById("btn-recarregar");
const diasPt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

async function api(url, opts = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
    ...(opts.headers || {})
  };

  const res = await fetch(url, { ...opts, headers, credentials: "same-origin" });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.erro || `Não foi possível concluir a operação (${res.status}).`);
  }

  if (res.redirected || !res.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Sua sessão expirou. Entre novamente.');
  }
  return res.json();
}

// Função que gerencia o Modal Customizado na tela
function pedirTextoModal(titulo, textoInicial = "", dia = "", turno = "manha", editar = false) {
  return new Promise((resolve) => {
    const modal = document.getElementById("modal-postit");
    const modalTitulo = document.getElementById("modal-titulo");
    const inputTexto = document.getElementById("modal-input-texto");
    const btnSalvar = document.getElementById("modal-btn-salvar");
    const btnCancelar = document.getElementById("modal-btn-cancelar");

    modalTitulo.textContent = titulo;
    inputTexto.value = textoInicial;
    document.getElementById('modal-dia').value = dia;
    document.getElementById('modal-turno').value = turno;
    document.getElementById('modal-agendamento').hidden = !editar;
    modal.showModal();
    inputTexto.focus();

    function fechar(resultado) {
      modal.close();
      modal.oncancel = null;
      btnSalvar.onclick = null;
      btnCancelar.onclick = null;
      resolve(resultado);
    }

    btnSalvar.onclick = () => {
      if (!document.getElementById('agenda-form').reportValidity()) return;
      fechar({texto: inputTexto.value.trim(), dia: document.getElementById('modal-dia').value, turno: document.getElementById('modal-turno').value});
    };
    modal.oncancel = (event) => { event.preventDefault(); fechar(null); };
    btnCancelar.onclick = () => fechar(null);
  });
}

function normaliza(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

async function carregarUsuarios() {
  try {
    usuariosDisponiveis = await api(board.dataset.usuariosUrl);
  } catch (err) {
    document.getElementById("agenda-status").textContent = "Não foi possível carregar os usuários para menções.";
  }
}

function extrairMencoesPrimeiroNome(texto) {
  const re = /@([\wÀ-ÿ.+-]+)/g;
  const out = new Set();
  let m;
  while ((m = re.exec(texto)) !== null) out.add(normaliza(m[1]));
  return Array.from(out);
}

function resolverPrimeirosNomesParaMatriculas(primeirosNomes) {
  if (primeirosNomes.includes("todos")) {
    return []; // O servidor resolve @todos com os usuários ativos.
  }

  const mapa = new Map();
  for (const u of usuariosDisponiveis) {
    const primeiro = normaliza((u.nome || "").split(" ")[0] || "");
    if (!primeiro) continue;
    if (!mapa.has(primeiro)) mapa.set(primeiro, []);
    mapa.get(primeiro).push(String(u.matricula));
  }

  const vinculados = new Set();
  const ambiguos = [];
  const naoEncontrados = [];

  for (const p of primeirosNomes) {
    const exatos = usuariosDisponiveis.filter(u => normaliza(u.matricula) === p);
    const mats = exatos.length ? exatos.map(u => u.matricula) : (mapa.get(p) || []);
    if (mats.length === 1) vinculados.add(mats[0]);
    else if (mats.length > 1) ambiguos.push(p);
    else naoEncontrados.push(p);
  }

  const avisos = [];
  if (ambiguos.length) {
    avisos.push("Nome repetido (não vinculado): " + ambiguos.map(x => `@${x}`).join(", "));
  }
  if (naoEncontrados.length) {
    avisos.push("Usuário não encontrado: " + naoEncontrados.map(x => `@${x}`).join(", "));
  }
  if (avisos.length) alert(avisos.join("\n"));

  return Array.from(vinculados);
}

function fmtDia(iso) {
  const d = new Date(iso + "T00:00:00");
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}`;
}

function getSlot(diaIso, turno) {
  return document.querySelector(`.slot[data-dia="${diaIso}"][data-turno="${turno}"]`);
}

function renderSemana(inicioIso, itens) {
  itensPorId.clear();
  itens.forEach(item => itensPorId.set(item.id, item));
  if (!board) return;
  board.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "week-grid";
  board.appendChild(wrap);

  const inicio = new Date(inicioIso + "T00:00:00");

  for (let i = 0; i < 6; i++) {
    const d = new Date(inicio);
    d.setDate(inicio.getDate() + i);
    const iso = diasSemana[i].dia;

    const col = document.createElement("div");
    col.className = "day-col";

    const head = document.createElement("div");
    head.className = "day-head";

    const title = document.createElement("div");
    title.className = "day-title";
    title.textContent = `${diasPt[i]} (${fmtDia(iso)})`;

    const actions = document.createElement("div");
    actions.className = "day-actions";

    const addBtn = document.createElement("button");
    addBtn.textContent = "+";
    addBtn.type = "button";
    addBtn.onclick = (e) => {
      e.preventDefault();
      criarPostit(iso, "manha");
    };

    const limparBtn = document.createElement("button");
    limparBtn.textContent = "Limpar";
    limparBtn.type = "button";
    limparBtn.onclick = (e) => {
      e.preventDefault();
      apagarDia(iso);
    };

    actions.appendChild(addBtn);
    actions.appendChild(limparBtn);

    head.appendChild(title);
    head.appendChild(actions);

    const slotManha = criarSlot(iso, "manha", "07:00–11:00");
    const slotTarde = criarSlot(iso, "tarde", "13:00–17:00");

    col.appendChild(head);
    col.appendChild(slotManha);
    col.appendChild(slotTarde);

    wrap.appendChild(col);
  }

  for (const it of itens) adicionarPostitNoDOM(it);
}

function criarSlot(diaIso, turno, label) {
  const slot = document.createElement("div");
  slot.className = "slot";
  slot.dataset.dia = diaIso;
  slot.dataset.turno = turno;
  slot.dataset.label = label;

  slot.addEventListener("dragover", ev => {
    ev.preventDefault();
    slot.classList.add("dragover");
    ev.dataTransfer.dropEffect = "move";
  });

  slot.addEventListener("dragleave", () => slot.classList.remove("dragover"));

  slot.addEventListener("drop", async ev => {
    ev.preventDefault();
    slot.classList.remove("dragover");

    const postitId = ev.dataTransfer.getData("text/plain");
    if (!postitId) return;

    const card = document.getElementById(`postit-${postitId}`);
    if (!card) return;

    const novoDia = slot.dataset.dia;
    const novoTurno = slot.dataset.turno;

    slot.appendChild(card);

    try {
      await api(itensPorId.get(Number(postitId)).url, {
        method: "PATCH",
        body: JSON.stringify({ dia: novoDia, turno: novoTurno })
      });
      await carregar();
    } catch (e) {
      console.error(e);
      alert("Erro ao mover post-it.");
      await carregar();
    }
  });

  const add = document.createElement("button");
  add.className = "btn";
  add.type = "button";
  add.style.margin = "6px 8px 0 0";
  add.style.background = "rgba(255,255,255,0.75)";
  add.textContent = `+ ${turno === "manha" ? "manhã" : "tarde"}`;
  add.onclick = (e) => {
    e.preventDefault();
    criarPostit(diaIso, turno);
  };

  const bar = document.createElement("div");
  bar.style.display = "flex";
  bar.style.justifyContent = "flex-end";
  bar.appendChild(add);

  slot.appendChild(bar);
  return slot;
}

function adicionarPostitNoDOM(it) {
  const slot = getSlot(it.dia, it.turno || "manha");
  if (!slot) return;

  const card = document.createElement("div");
  card.className = "postit" + (it.feito ? " feito" : "");
  card.id = `postit-${it.id}`;
  card.draggable = it.pode_editar;
  card.dataset.id = it.id;

  if (it.cor) card.style.background = it.cor;

  card.addEventListener("dragstart", ev => {
    ev.dataTransfer.setData("text/plain", String(it.id));
  });

  const top = document.createElement("div");
  top.className = "top";

  const left = document.createElement("div");
  const chk = document.createElement("input");
  chk.type = "checkbox";
  chk.checked = !!it.feito;
  chk.disabled = !it.pode_editar;
  chk.setAttribute("aria-label", "Marcar lembrete como concluído");
  chk.onchange = () => marcarFeito(it.id, chk.checked);
  left.appendChild(chk);

  const right = document.createElement("div");

  const editBtn = document.createElement("button");
  editBtn.className = "icon-btn";
  editBtn.type = "button";
  editBtn.textContent = "Editar";
  editBtn.onclick = () => editarPostit(it.id, it.texto);
  editBtn.disabled = !it.pode_editar;

  const delBtn = document.createElement("button");
  delBtn.className = "icon-btn";
  delBtn.type = "button";
  delBtn.textContent = "Apagar";
  delBtn.onclick = () => apagarPostit(it.id);
  delBtn.disabled = !it.pode_editar;

  right.appendChild(editBtn);
  right.appendChild(delBtn);

  top.appendChild(left);
  top.appendChild(right);

  const autor = document.createElement("div");
  autor.className = "autor";
  autor.textContent = it.autor_nome ? `Criado por: ${it.autor_nome}` : (it.matricula ? `Mat.: ${it.matricula}` : "");

  const texto = document.createElement("div");
  texto.className = "texto";
  texto.textContent = it.texto;

  card.appendChild(top);
  card.appendChild(autor);
  card.appendChild(texto);

  slot.appendChild(card);
}

async function carregar() {
  try {
    const data = await api(board.dataset.semanaUrl);
    diasSemana = data.dias;
    document.getElementById("agenda-status").textContent = "";
    renderSemana(data.inicio, data.itens);
  } catch (err) {
    document.getElementById("agenda-status").textContent = err.message;
  }
}

async function criarPostit(diaIso, turno) {
  try {
    const turnoTexto = turno === 'manha' ? 'Manhã' : 'Tarde';
    const valores = await pedirTextoModal(`Novo Post-it (${turnoTexto})`, "", diaIso, turno);
    const texto = valores?.texto;
    
    if (!texto || !texto.trim()) return;

    const mencoes = extrairMencoesPrimeiroNome(texto);
    const vinculados = resolverPrimeirosNomesParaMatriculas(mencoes);

    await api(board.dataset.criarUrl, {
      method: "POST",
      body: JSON.stringify({ ...valores, vinculados })
    });

    await carregar();
  } catch (err) {
    console.error("Erro ao criar post-it:", err);
    alert("Não foi possível criar o post-it: " + err.message);
  }
}

async function editarPostit(id, textoAtual) {
  try {
    const item = itensPorId.get(id);
    const valores = await pedirTextoModal("Editar Post-it", textoAtual, item.dia, item.turno, true);
    const novoTexto = valores?.texto;
    if (!novoTexto || !novoTexto.trim()) return;

    const mencoes = extrairMencoesPrimeiroNome(novoTexto);
    const vinculados = resolverPrimeirosNomesParaMatriculas(mencoes);

    await api(itensPorId.get(id).url, {
      method: "PATCH",
      body: JSON.stringify({ ...valores, vinculados })
    });

    await carregar();
  } catch (err) {
    console.error("Erro ao editar post-it:", err);
    alert("Erro ao editar: " + err.message);
  }
}

async function marcarFeito(id, feito) {
  try {
    await api(itensPorId.get(id).url, {
      method: "PATCH",
      body: JSON.stringify({ feito })
    });

    const card = document.getElementById(`postit-${id}`);
    if (card) card.classList.toggle("feito", !!feito);
  } catch (err) {
    alert(err.message);
    await carregar();
  }
}

async function apagarPostit(id) {
  if (!confirm("Apagar este post-it?")) return;

  try {
    await api(itensPorId.get(id).url, { method: "DELETE" });

    const card = document.getElementById(`postit-${id}`);
    if (card) card.remove();
  } catch (err) {
    alert(err.message);
  }
}

async function apagarDia(diaIso) {
  if (!confirm(board.dataset.admin === "true" ? "Apagar todos os lembretes deste dia?" : "Apagar os seus lembretes deste dia?")) return;

  try {
    await api(diasSemana.find(dia => dia.dia === diaIso).limpar_url, { method: "DELETE" });
    await carregar();
  } catch (err) {
    alert(err.message);
  }
}

if (btnRecarregar) {
  btnRecarregar.onclick = () => carregar();
}

document.addEventListener("DOMContentLoaded", async () => {
  await carregarUsuarios();
  await carregar();
});
document.getElementById("agenda-imprimir").addEventListener("click", () => window.print());

document.getElementById("agenda-form").addEventListener("submit", event => event.preventDefault());
