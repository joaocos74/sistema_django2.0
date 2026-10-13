'use strict';
const root = document.getElementById("mini-agenda");
const diasPt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

async function api(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function fmtDia(iso) {
  const d = new Date(iso + "T00:00:00");
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}`;
}

function render(inicioIso, itens, dias) {
  if (!root) return;
  root.innerHTML = "";

  const inicio = new Date(inicioIso + "T00:00:00");

  for (let i = 0; i < 6; i++) {
    const d = new Date(inicio);
    d.setDate(inicio.getDate() + i);
    const iso = dias[i].dia;

    const col = document.createElement("div");
    col.className = "day-col day-col--mini";

    const head = document.createElement("div");
    head.className = "day-head";

    const title = document.createElement("div");
    title.className = "day-title";
    title.textContent = `${diasPt[i]} (${fmtDia(iso)})`;

    head.appendChild(title);

    const manha = document.createElement("div");
    manha.className = "slot slot--mini";
    manha.dataset.label = "07–11";

    const tarde = document.createElement("div");
    tarde.className = "slot slot--mini";
    tarde.dataset.label = "13–17";

    for (const it of itens.filter(x => x.dia === iso && (x.turno || "manha") === "manha")) {
      manha.appendChild(card(it));
    }
    for (const it of itens.filter(x => x.dia === iso && (x.turno || "manha") === "tarde")) {
      tarde.appendChild(card(it));
    }

    col.appendChild(head);
    col.appendChild(manha);
    col.appendChild(tarde);
    root.appendChild(col);
  }
}

function card(it) {
  const c = document.createElement("div");
  c.className = "postit postit--mini" + (it.feito ? " feito" : "");

  // A cor é sempre a do usuário que criou o post-it.
  // Não existe mais uma cor amarela padrão para a Mini Agenda.
  if (it.cor) {
    c.style.backgroundColor = it.cor;
  }

  const autor = document.createElement("div");
  autor.className = "autor-mini";
  autor.textContent = it.autor_nome ? `Por: ${it.autor_nome}` : "";

  const t = document.createElement("div");
  t.className = "texto";
  t.textContent = it.texto;

  if (autor.textContent) c.appendChild(autor);
  c.appendChild(t);

  return c;
}

async function refresh() {
  const data = await api(root.dataset.url);
  render(data.inicio, data.itens, data.dias);
  document.getElementById("mini-status").textContent = data.itens.length ? "" : "Nenhum lembrete seu ou com menção a você nesta semana.";
}

document.addEventListener("DOMContentLoaded", () => {
  async function atualizar() {
    if (document.hidden) return;
    try { await refresh(); }
    catch { document.getElementById('mini-status').textContent = 'Não foi possível carregar a agenda. Atualize a página ou entre novamente.'; }
  }
  atualizar();
  setInterval(atualizar, 60000);
});
