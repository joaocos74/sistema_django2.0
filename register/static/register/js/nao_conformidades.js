(() => {
  'use strict';
  const date = document.getElementById('id_data_realizacao');
  const fields = ['id_nc_total', 'id_nc_criticas', 'id_nc_maiores'].map(id => document.getElementById(id));
  if (date && fields.every(Boolean)) {
    const originalDate = date.value, originalValues = fields.map(field => field.value);
    let edited = false;
    const validate = () => {
      const any = fields.some(field => field.value !== '');
      fields.forEach(field => { field.required = any; });
      date.required = any;
      const [total, critical, major] = fields.map(field => field.valueAsNumber);
      fields[0].setCustomValidity(critical + major > total ? 'A soma de críticas e maiores não pode ultrapassar o total.' : '');
    };
    fields.forEach(field => field.addEventListener('input', () => { edited = true; validate(); }));
    date.addEventListener('change', () => {
      if (!edited) {
        fields.forEach((field, index) => { field.value = date.value === originalDate ? originalValues[index] : ''; });
        document.getElementById('nc-aviso-data').hidden = date.value === originalDate || originalValues.every(value => value === '');
      }
      validate();
    });
    validate();
  }
  const root = document.getElementById('nc-grafico');
  const source = document.getElementById('nc-dados');
  if (!root || !source) return;
  const data = JSON.parse(source.textContent);
  if (!data.length) return;
  function draw() {
    if (root.querySelector('svg')) return;
    const ns = 'http://www.w3.org/2000/svg';
    const node = (tag, attrs = {}, text = '') => {
      const el = document.createElementNS(ns, tag);
      Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
      if (text) el.textContent = text;
      return el;
    };
    const width = Math.max(640, root.clientWidth, data.length * 100 + 100);
    const height = 330, left = 90, right = width - 35, top = 38, bottom = 265;
    const maximum = data.reduce((max, row) => Math.max(max, row.criticas, row.maiores), 0);
    const step = Math.max(1, Math.ceil(maximum / 5)), ceiling = step * 5;
    const x = (index) => data.length === 1 ? (left + right) / 2 : left + index * (right - left) / (data.length - 1);
    const y = (value) => bottom - value * (bottom - top) / ceiling;
    const svg = node('svg', {viewBox: '0 0 ' + width + ' ' + height, width, height, role: 'img',
      'aria-labelledby': 'nc-svg-title nc-svg-desc'});
    svg.append(node('title', {id: 'nc-svg-title'}, 'Não conformidades críticas e maiores por inspeção'));
    svg.append(node('desc', {id: 'nc-svg-desc'}, 'Datas no eixo horizontal e quantidades no eixo vertical. Consulte os valores na tabela abaixo.'));
    svg.append(node('text', {x: left, y: 18}, 'Quantidade de não conformidades'));
    for (let tick = 0; tick <= 5; tick++) {
      const value = tick * step;
      svg.append(node('line', {x1: left, x2: right, y1: y(value), y2: y(value), class: 'nc-grade'}));
      svg.append(node('text', {x: left - 10, y: y(value) + 4, 'text-anchor': 'end'}, String(value)));
    }
    svg.append(node('line', {x1: left, x2: left, y1: top, y2: bottom, class: 'nc-eixo'}));
    svg.append(node('line', {x1: left, x2: right, y1: bottom, y2: bottom, class: 'nc-eixo'}));
    data.forEach((row, index) => svg.append(node('text', {x: x(index), y: bottom + 24, 'text-anchor': 'middle'}, row.data)));
    svg.append(node('text', {x: (left + right) / 2, y: height - 8, 'text-anchor': 'middle'}, 'Inspeção — data de realização'));
    for (const [key, label, color] of [['criticas', 'Críticas', '#dc3545'], ['maiores', 'Maiores', '#3563e9']]) {
      svg.append(node('polyline', {points: data.map((row, index) => x(index) + ',' + y(row[key])).join(' '),
        fill: 'none', stroke: color, 'stroke-width': 2.5, 'stroke-dasharray': key === 'maiores' ? '6 3' : 'none'}));
      data.forEach((row, index) => {
        const text = 'Inspeção #' + row.id + ' — ' + row.data + ': ' + label + ' ' + row[key] + '; total ' + row.total;
        const marker = key === 'criticas'
          ? node('circle', {cx: x(index), cy: y(row[key]), r: 5})
          : node('rect', {x: x(index) - 4, y: y(row[key]) - 4, width: 8, height: 8});
        marker.setAttribute('fill', color);
        marker.setAttribute('stroke', '#fff');
        marker.setAttribute('stroke-width', '1');
        marker.setAttribute('tabindex', '0');
        marker.setAttribute('class', 'nc-ponto');
        marker.setAttribute('aria-label', text);
        marker.append(node('title', {}, text));
        svg.append(marker);
      });
    }
    root.append(svg);
  }
  const panel = root.closest('details');
  if (!panel || panel.open) draw();
  panel?.addEventListener('toggle', () => { if (panel.open) draw(); });
  window.addEventListener('beforeprint', draw);
})();
