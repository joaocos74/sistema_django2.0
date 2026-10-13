'use strict';
// Os valores vêm de json_script; os rótulos são inseridos como texto.
function dados(id) {
    const element = document.getElementById(id);
    return element ? JSON.parse(element.textContent) : null;
}
function barrasDuplas(id, itens, titulo, positivo, pendente) {
    barrasAgrupadas(id, itens, titulo, [
        {chave: 'feito', nome: positivo, cor: '#169b5b'},
        {chave: 'pendente', nome: pendente, cor: '#b45309'},
    ]);
}
function barrasAgrupadas(id, itens, titulo, series) {
    const root = document.getElementById(id);
    if (!root) return;
    const pageSize = 6;
    const pages = [];
    const maximum = itens.reduce((max, item) => Math.max(max, ...series.map(serie => item[serie.chave])), 0);
    for (let offset = 0; offset < Math.max(1, itens.length); offset += pageSize) {
        const page = document.createElement('div');
        page.id = `${id}-grupo-${pages.length}`;
        page.className = 'chart-batch';
        page.hidden = pages.length > 0;
        root.append(page);
        desenharBarras(page.id, itens.slice(offset, offset + pageSize), titulo, series, maximum);
        pages.push(page);
    }
    root.classList.add('chart-paged');
    if (pages.length < 2) return;
    let current = 0;
    const controls = document.createElement('div');
    controls.className = 'chart-navigation';
    const previous = document.createElement('button');
    const next = document.createElement('button');
    const status = document.createElement('span');
    status.setAttribute('aria-live', 'polite');
    for (const button of [previous, next]) {
        button.type = 'button';
        button.className = 'btn btn-secundary';
    }
    previous.textContent = 'Anterior';
    next.textContent = 'Próximo';
    function update() {
        pages.forEach((page, index) => { page.hidden = index !== current; });
        status.textContent = `Grupo ${current + 1} de ${pages.length}`;
        previous.disabled = current === 0;
        next.disabled = current === pages.length - 1;
    }
    previous.addEventListener('click', () => { current--; update(); });
    next.addEventListener('click', () => { current++; update(); });
    controls.append(previous, status, next);
    root.append(controls);
    update();
}
function desenharBarras(id, itens, titulo, series, maiorValor) {
    const root = document.getElementById(id);
    if (!root) return;
    root.classList.add('chart-columns');
    const heading = document.createElement('h3');
    heading.textContent = titulo;
    root.append(heading);
    const legend = document.createElement('div');
    legend.className = 'columns-legend';
    series.forEach(serie => {
        const label = document.createElement('span');
        const swatch = document.createElement('span');
        swatch.className = 'chart-swatch';
        swatch.style.backgroundColor = serie.cor;
        label.append(swatch, document.createTextNode(serie.nome));
        legend.append(label);
    });
    root.append(legend);
    if (!itens.length) {
        root.append(document.createTextNode('Sem dados para o gráfico.'));
        return;
    }
    const ns = 'http://www.w3.org/2000/svg';
    function node(tag, attrs, text) {
        const element = document.createElementNS(ns, tag);
        Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
        if (text !== undefined) element.textContent = text;
        return element;
    }
    const width = Math.max(420, itens.length * 120 + 60);
    const step = Math.max(1, Math.ceil(maiorValor / 4));
    const maximum = step * 4;
    const svg = node('svg', {viewBox: `0 0 ${width} 285`, width, height: 285, role: 'img', 'aria-label': titulo});
    svg.append(node('title', {}, titulo));
    const baseline = 215;
    const height = 180;
    for (let tick = 0; tick <= 4; tick++) {
        const y = baseline - tick * height / 4;
        svg.append(node('line', {x1: 42, x2: width - 12, y1: y, y2: y, stroke: '#e2e8f0'}));
        svg.append(node('text', {x: 35, y: y + 4, 'text-anchor': 'end'}, (tick * step).toLocaleString('pt-BR')));
    }
    const groupWidth = (width - 60) / itens.length;
    itens.forEach((item, index) => {
        const center = 48 + groupWidth * (index + .5);
        series.forEach((serie, serieIndex) => {
            const value = item[serie.chave];
            const barHeight = value / maximum * height;
            const x = center - (series.length * 34 - 8) / 2 + serieIndex * 34;
            const description = `${item.rotulo}: ${serie.nome}, ${value}`;
            const bar = node('rect', {x, y: baseline - barHeight, width: 26, height: barHeight, fill: serie.cor, rx: 3});
            bar.append(node('title', {}, description));
            svg.append(bar);
            const label = node('text', {x: x + 13, y: baseline - barHeight - 7, 'text-anchor': 'middle', 'aria-label': description}, value.toLocaleString('pt-BR'));
            svg.append(label);
        });
        const label = node('text', {x: center, y: 235, 'text-anchor': 'middle'});
        label.append(node('title', {}, item.rotulo));
        const lines = [''];
        const shortLabel = item.rotulo.length > 42 ? item.rotulo.slice(0, 39) + '…' : item.rotulo;
        (shortLabel.match(/.{1,16}(?:\s|$)|.{1,16}/g) || []).forEach(word => {
            const last = lines.length - 1;
            if (lines[last] && (lines[last] + ' ' + word).length > 16) lines.push(word);
            else lines[last] += (lines[last] ? ' ' : '') + word;
        });
        lines.slice(0, 3).forEach((line, i) => label.append(node('tspan', {x: center, dy: i === 0 ? 0 : 14}, line)));
        svg.append(label);
    });
    const scroll = document.createElement('div');
    scroll.className = 'columns-scroll';
    scroll.tabIndex = 0;
    scroll.setAttribute('role', 'region');
    scroll.setAttribute('aria-label', `${titulo}: role horizontalmente para ver todas as categorias`);
    scroll.append(svg);
    root.append(scroll);
}
const ano = dados('js-metricas-ano');
function pizza(id, itens, titulo) {
    const root = document.getElementById(id);
    if (!root) return;
    const heading = document.createElement('h3');
    heading.textContent = titulo;
    root.append(heading);
    const total = itens.reduce((sum, item) => sum + item.valor, 0);
    if (!total) {
        const empty = document.createElement('p');
        empty.textContent = 'Sem dados para o gráfico.';
        root.append(empty);
        return;
    }
    const colors = ['#169b5b', '#d97706', '#2563eb', '#9333ea', '#dc2626'];
    const layout = document.createElement('div');
    layout.className = 'pie-layout';
    const pie = document.createElement('div');
    pie.className = 'pie-chart';
    pie.setAttribute('aria-hidden', 'true');
    const legend = document.createElement('ul');
    legend.className = 'pie-legend';
    let offset = 0;
    const slices = itens.map((item, index) => {
        const percent = item.valor / total * 100;
        const color = colors[index % colors.length];
        const slice = `${color} ${offset}% ${offset + percent}%`;
        offset += percent;
        const li = document.createElement('li');
        const swatch = document.createElement('span');
        swatch.className = 'chart-swatch';
        swatch.style.backgroundColor = color;
        const text = document.createElement('span');
        text.textContent = `${item.rotulo}: ${item.valor.toLocaleString('pt-BR')} (${percent.toLocaleString('pt-BR', {maximumFractionDigits: 1})}%)`;
        li.append(swatch, text);
        legend.append(li);
        return slice;
    });
    pie.style.background = `conic-gradient(${slices.join(', ')})`;
    layout.append(pie, legend);
    root.append(layout);
}
if (ano) pizza('chartAno', [
    {rotulo: 'Inspecionados', valor: ano.inspecionados},
    {rotulo: 'Não inspecionados', valor: ano.nao_inspecionados},
], 'Inspeções no ano');
pizza('chartRisco', (dados('js-metricas-risco') || []).map((item) => ({rotulo: `Risco ${item.risco}`, valor: item.inspecionados})), 'Distribuição dos inspecionados por risco');
for (const [id, fonte, titulo, campo] of [
    ['chartQuad', 'js-chart-quad', 'Inspeções por quadrimestre', 'quadrimestre'],
    ['chartMes', 'js-chart-mes', 'Inspeções por mês', 'mes'],
]) {
    barrasDuplas(id, (dados(fonte) || []).map(item => ({
        rotulo: item[campo], feito: item.total_feito, pendente: item.total_afazer,
    })), titulo, 'Feito', 'A fazer');
}
barrasDuplas('chartClasse', (dados('js-metricas-classe') || []).map(item => ({
    rotulo: item.classe, feito: item.inspecionados, pendente: Math.max(0, item.total - item.inspecionados),
})), 'Estabelecimentos por classe', 'Inspecionados', 'Não inspecionados');


barrasAgrupadas('chartPendencias', (dados('js-metricas-pendencias') || []).map(item => ({
    rotulo: item.acao, historico: item.pendentes, concluidos: item.concluidos, sem_conclusao: item.sem_conclusao,
})), 'Pendências por estabelecimento', [
    {chave: 'historico', nome: 'Com pendência no histórico', cor: '#b45309'},
    {chave: 'concluidos', nome: 'Com conclusão posterior', cor: '#169b5b'},
    {chave: 'sem_conclusao', nome: 'Sem conclusão posterior', cor: '#dc2626'},
]);

// O relatório usa as seleções com que os dados foram carregados, não alterações ainda não enviadas.
document.querySelectorAll('.metric-card .filter-form').forEach(form => {
    const summary = document.createElement('p');
    summary.className = 'report-filters';
    summary.textContent = [...form.querySelectorAll('select')].map(select => {
        const label = select.closest('.form-group')?.querySelector('label')?.textContent.trim() || select.name;
        return `${label}: ${select.selectedOptions[0]?.textContent.trim() || '—'}`;
    }).join(' · ');
    form.after(summary);
});
let originalTitle;
let reportDetails;
window.addEventListener('beforeprint', () => {
    originalTitle ??= document.title;
    reportDetails ??= [...document.querySelectorAll('.metric-help')].map(element => [element, element.open]);
    reportDetails.forEach(([element]) => { element.open = true; });
    document.title = `Consolidado-estatisticas-${ano?.ano || ''}`;
    document.getElementById('report-date').textContent = `Emitido em ${new Date().toLocaleString('pt-BR')}`;
});
window.addEventListener('afterprint', () => {
    if (originalTitle !== undefined) document.title = originalTitle;
    originalTitle = undefined;
    reportDetails?.forEach(([element, open]) => { element.open = open; });
    reportDetails = undefined;
});
document.getElementById('exportar-pdf')?.addEventListener('click', () => window.print());
