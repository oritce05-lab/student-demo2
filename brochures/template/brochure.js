// בונה את הידיעון מתוך window.COURSE (קובץ course.json של הקורס)
(function () {
  const C = window.COURSE;
  const BASE = window.COURSE_BASE || '';

  // ---------- helpers ----------
  const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // **מודגש**, *נטוי*, ושורה חדשה עם \n
  const md = (s) => esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
  const img = (src) => (/^(https?:|\/|\.\.\/|assets\/)/.test(src) ? src : BASE + src);
  const bg = (src, pos) => `style="background-image:url('${img(src)}');${pos ? `background-position:${pos};` : ''}"`;
  const lines = (v) => (Array.isArray(v) ? v.map(md).join('<br>') : md(v));
  const pad2 = (n) => String(n).padStart(2, '0');

  const ICONS = {
    refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    chat: '<path d="M14 9a2 2 0 0 1-2 2H6l-4 4V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2z"/><path d="M18 9h2a2 2 0 0 1 2 2v11l-4-4h-6a2 2 0 0 1-2-2v-1"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    map: '<path d="M14.1 5.55a2 2 0 0 0 1.8 0l3.66-1.83A1 1 0 0 1 21 4.62v12.76a1 1 0 0 1-.55.9l-4.55 2.27a2 2 0 0 1-1.8 0l-4.2-2.1a2 2 0 0 0-1.8 0l-3.66 1.83A1 1 0 0 1 3 19.38V6.62a1 1 0 0 1 .55-.9L8.1 3.45a2 2 0 0 1 1.8 0z"/><path d="M15 5.76v15"/><path d="M9 3.24v15"/>',
    clipboard: '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>',
    question: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M9.5 8.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5"/><path d="M12 14.5h.01"/>',
    layers: '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    stairs: '<path d="M3 20h4v-4h4v-4h4V8h4V4h2"/>',
    wind: '<path d="M12.8 19.6A2 2 0 1 0 14 16H2"/><path d="M17.5 8a2.5 2.5 0 1 1 2 4H2"/><path d="M9.8 4.4A2 2 0 1 1 11 8H2"/>',
    leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    briefcase: '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
    eye: '<path d="M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-19.88 0"/><circle cx="12" cy="12" r="3"/>',
    stop: '<path d="M2.59 16.73A2 2 0 0 1 2 15.31V8.69a2 2 0 0 1 .59-1.41l4.69-4.69A2 2 0 0 1 8.69 2h6.62a2 2 0 0 1 1.41.59l4.69 4.69A2 2 0 0 1 22 8.69v6.62a2 2 0 0 1-.59 1.41l-4.69 4.69a2 2 0 0 1-1.41.59H8.69a2 2 0 0 1-1.41-.59z"/><path d="M8 12h8"/>',
    arrow: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    network: '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="18" r="2.5"/><circle cx="19" cy="18" r="2.5"/><path d="M10.8 7.2 6.2 15.8M13.2 7.2l4.6 8.6M7.5 18h9"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    mic: '<path d="M12 19v3"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><rect x="9" y="2" width="6" height="13" rx="3"/>',
    replay: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="m10 9 5 3-5 3z"/>',
    presentation: '<path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/>',
    play: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="m10 8 6 4-6 4z"/>',
    book: '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/><path d="M2 10h20"/>',
    file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    home: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .71-1.53l7-6a2 2 0 0 1 2.58 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    heart: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    building: '<rect width="16" height="20" x="4" y="2" rx="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/>',
    award: '<path d="m15.48 12.89 1.51 8.53a.5.5 0 0 1-.81.47l-3.58-2.69a1 1 0 0 0-1.2 0l-3.59 2.69a.5.5 0 0 1-.81-.47l1.51-8.53"/><circle cx="12" cy="8" r="6"/>',
    bulb: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
    cap: '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    chart: '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="m19 9-5 5-4-4-3 3"/>',
    camera: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/>',
    hardhat: '<path d="M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5"/><path d="M14 6a6 6 0 0 1 6 6v3"/><path d="M4 15v-3a6 6 0 0 1 6-6"/><rect x="2" y="15" width="20" height="4" rx="1"/>',
    crane: '<path d="M6 21V3"/><path d="M2 21h8"/><path d="M6 3h15"/><path d="M6 3 2 7"/><path d="M18 3v6"/><rect x="16" y="9" width="4" height="3"/><path d="M6 7h4"/>',
    fence: '<path d="M4 3 2 5v15c0 .6.4 1 1 1h2c.6 0 1-.4 1-1V5Z"/><path d="M6 8h4"/><path d="M6 18h4"/><path d="m12 3-2 2v15c0 .6.4 1 1 1h2c.6 0 1-.4 1-1V5Z"/><path d="M14 8h4"/><path d="M14 18h4"/><path d="m20 3-2 2v15c0 .6.4 1 1 1h2c.6 0 1-.4 1-1V5Z"/>',
    key: '<path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4"/><path d="m21 2-9.6 9.6"/><circle cx="7.5" cy="15.5" r="5.5"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    settings: '<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>',
    bell: '<path d="M10.27 21a2 2 0 0 0 3.46 0"/><path d="M3.26 15.33A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.67C19.41 13.96 18 12.5 18 8A6 6 0 0 0 6 8c0 4.5-1.41 5.96-2.74 7.33"/>',
    gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    report: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 18v-2"/><path d="M12 18v-5"/><path d="M16 18v-3"/>',
    radio: '<path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/>',
    lock: '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    flag: '<path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.33 2q2 0 3.67-1.33a1 1 0 0 1 1.6.8V14a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.53"/>',
    drone: '<circle cx="5" cy="5" r="3"/><circle cx="19" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="m7 7 2 2M17 7l-2 2M7 17l2-2M17 17l-2-2"/>',
  };
  const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ICONS.check}</svg>`;

  // ---------- blocks ----------
  const B = {};

  B.heading = (b) => `<div class="${b.cls || ''}">
      ${b.eyebrow ? `<div class="eyebrow">${md(b.eyebrow)}</div>` : ''}
      <div class="h1 ${b.size || ''}">${lines(b.title)}</div>
      ${b.lead ? `<div class="lead">${md(b.lead)}</div>` : ''}
    </div>`;

  B.text = (b) => `<div class="p ${b.cls || ''}">${md(b.text)}</div>`;
  B.note = (b) => `<div class="note ${b.cls || ''}">${md(b.text)}</div>`;
  B.small = (b) => `<div class="small ${b.cls || ''}">${md(b.text)}</div>`;
  B.subheading = (b) => `<div class="h3 ${b.badge ? 'with-badge' : ''} ${b.cls || ''}">${b.badge ? `<span class="badge">${md(b.badge)}</span>` : ''}${md(b.text)}${b.aside ? ` <span class="small" style="font-weight:400;margin-inline-start:3mm">${md(b.aside)}</span>` : ''}</div>`;

  // כרטיסים עם קו עליון (רגעים / עקרונות ממוספרים)
  B.lined = (b) => `<div class="${b.cls || ''}">
      ${b.title ? `<div class="h3" style="margin-bottom:3mm">${md(b.title)}</div>` : ''}
      <div class="lined" style="grid-template-columns:repeat(${b.columns || 3},1fr)">
        ${b.items.map((it, i) => `<div class="item">
          ${b.numbered ? `<span class="num">${it.num ?? i + 1}</span>` : ''}
          <b>${md(it.title)}</b><p>${md(it.text)}</p></div>`).join('')}
      </div></div>`;

  // פס כהה ברוחב מלא: הסבר + תרשים זרימה
  B.darkBand = (b) => `<div class="band-dark ${b.cls || ''}">
      <div>
        ${b.eyebrow ? `<div class="eyebrow">${md(b.eyebrow)}</div>` : ''}
        <div class="h1">${lines(b.title)}</div>
        <div class="p">${md(b.text)}</div>
      </div>
      <div>
        ${b.flow ? `${b.flow.eyebrow ? `<div class="eyebrow">${md(b.flow.eyebrow)}</div>` : ''}
        <div class="flow">${b.flow.steps.map((s, i) => `${i ? '<div class="arrow"></div>' : ''}
          <div class="row"><span class="chip c${s.color ?? i % 5}">${md(s.label)}</span><span>${md(s.text)}</span></div>`).join('')}
        </div>
        ${b.flow.callout ? `<div class="callout">${md(b.flow.callout)}</div>` : ''}` : ''}
      </div></div>`;

  B.checks = (b) => `<div class="checks">${b.items.map((t) => `<div class="check">${icon('check')}<span>${md(t)}</span></div>`).join('')}</div>`;

  B.infoBox = (b) => `<div class="box-dark ${b.cls || ''}">${b.title ? `<div class="t">${md(b.title)}</div>` : ''}<div class="p">${md(b.text)}</div></div>`;

  // טבלת תוכנית לימודים. hours אופציונלי: עם שעות מוצגים פסים
  B.curriculum = (b) => {
    const max = Math.max(...b.rows.map((r) => r.hours || 0));
    const withHours = max > 0;
    return `<div class="ctable">
      <div class="head"><span>${md(b.colNum || 'מודול')}</span><span></span><span>${md(b.colMeta || (withHours ? 'שעות' : ''))}</span></div>
      ${b.rows.map((r, i) => `<div class="row">
        <span class="n">${r.num ?? i + 1}</span>
        <div>${withHours ? `<div style="display:grid;grid-template-columns:1fr 62mm;gap:4mm;align-items:center">
            <div class="title">${md(r.title)}</div>
            <div class="bar ${r.highlight ? 'hl' : ''}" style="width:${(r.hours / max) * 100}%"></div></div>`
          : `<div class="title">${md(r.title)}</div>`}
          ${r.sub ? `<div class="sub">${md(r.sub)}</div>` : ''}</div>
        <span class="meta">${r.hours ? r.hours : md(r.meta || '')}</span>
      </div>`).join('')}
      ${b.totals ? `<div class="totals">${b.totals.map((t, i) => `${i ? `<span class="op">${i === b.totals.length - 1 ? '=' : '+'}</span>` : ''}
        <span class="${i === b.totals.length - 1 ? 'tot' : ''}"><b>${esc(t.value)}</b> ${md(t.label)}</span>`).join('')}</div>` : ''}
    </div>`;
  };

  B.iconCards = (b) => `<div class="${b.cls || ''}">
      ${b.title ? `<div class="h3" style="margin-bottom:3mm">${md(b.title)}</div>` : ''}
      <div class="icards" style="grid-template-columns:repeat(${b.columns || 3},1fr)">
        ${b.items.map((it) => `<div class="icard ${b.style || ''}">${it.icon ? icon(it.icon) : ''}<div><b>${md(it.title)}</b>${it.text ? `<p>${md(it.text)}</p>` : ''}</div></div>`).join('')}
      </div></div>`;

  // ראש עמוד מודולים: תווית + שבבי ניווט + כותרת + תמונה בפינה
  B.moduleHead = (b) => {
    const total = b.total || C.moduleCount || 0;
    const chips = Array.from({ length: total }, (_, i) => i + 1)
      .map((n) => `<span class="${b.active.includes(n) ? 'on' : ''}">${n}</span>`).join('');
    return `<div class="mod-head ${b.photo ? 'with-photo' : ''}">
      <div class="txt">
        <div class="bar-line"><span class="lbl">${md(b.label)}</span>${total ? `<div class="navchips">${chips}</div>` : ''}</div>
        <div class="h2">${md(b.title)}</div>
      </div>
      ${b.photo ? `<div class="photo" ${bg(b.photo, b.photoPos)}></div>` : ''}
    </div>`;
  };

  B.banner = (b) => `<div class="banner" style="background-image:url('${img(b.src)}');background-position:${b.pos || 'center'};height:${b.height || '42mm'}"></div>`;

  // כרטיס מודול מלא (מה תלמדו / בסיום תוכלו / שיטות / הערכה)
  B.module = (b) => {
    const L = C.labels || {};
    return `<div class="mcard">
      <div class="top">
        <span class="bign">${b.num}</span>
        <span class="ico">${b.icon ? icon(b.icon) : ''}</span>
        <div><div class="t">${md(b.headline)}</div>
          <div class="st">${md(b.subtitle)}</div>
          ${b.note ? `<div class="nt">${md(b.note)}</div>` : ''}</div>
        ${b.hours ? `<div class="hrs"><b>${b.hours}</b><span>${md(L.hours || 'שעות')}</span></div>` : '<span></span>'}
      </div>
      ${b.quote ? `<div class="quote">${md(b.quote)}</div>` : ''}
      ${b.text ? `<div class="text">${md(b.text)}</div>` : ''}
      ${b.learn || b.outcomes ? `<div class="cols">
        <div>${b.learn ? `<div class="ch">${md(L.learn || 'מה תלמדו')}</div><ul>${b.learn.map((x) => `<li>${md(x)}</li>`).join('')}</ul>` : ''}</div>
        <div class="out">${b.outcomes ? `<div class="ch">${md(L.outcomes || 'בסיום המודול תוכלו')}</div><ul class="out">${b.outcomes.map((x) => `<li style="--sq:1">${md(x)}</li>`).join('')}</ul>` : ''}</div>
      </div>` : ''}
      ${b.methods || b.assessment ? `<div class="foot">
        <div>${b.methods ? `<div class="ch">${md(L.methods || 'שיטות לימוד')}</div>${md(b.methods)}` : ''}</div>
        <div>${b.assessment ? `<div class="ch">${md(L.assessment || 'הערכה')}</div>${md(b.assessment)}` : ''}</div>
      </div>` : ''}
    </div>`;
  };

  // כרטיסי נושא קומפקטיים: מספר, אייקון, כותרת, פסקה
  B.topics = (b) => `<div class="tcards ${b.columns ? 'cols' : ''}" style="${b.columns ? `display:grid;grid-template-columns:repeat(${b.columns},1fr)` : ''}">${b.items.map((t, i) => `<div class="tcard">
      <span class="bign">${t.num ?? pad2(i + 1)}</span>
      <div><div class="t">${t.icon ? icon(t.icon) : ''}${md(t.title)}</div>
        <p>${md(t.text)}</p>${t.tag ? `<span class="tag">${md(t.tag)}</span>` : ''}</div>
    </div>`).join('')}</div>`;

  B.statement = (b) => `<div class="statement">
      <div class="big">${lines(b.big)}</div>
      <div class="rows">${b.rows.map((r) => `<div class="r">${icon(r.icon)}<b>${md(r.label)}</b><span>${md(r.text)}</span></div>`).join('')}</div>
    </div>`;

  B.bandNumber = (b) => `<div class="band-num"><span class="n">${esc(b.number)}</span><span class="l">${lines(b.label)}</span><span class="p">${md(b.text)}</span></div>`;

  B.kv = (b) => `<div>${b.title ? `<div class="h3" style="margin-bottom:2mm">${md(b.title)}</div>` : ''}
      <div class="kv">${b.rows.map((r) => `<div class="row ${r[2] ? 'hl' : ''}" style="${b.keyWidth ? `grid-template-columns:${b.keyWidth} 1fr` : ''}"><span class="k">${md(r[0])}</span><span>${md(r[1])}</span></div>`).join('')}</div></div>`;

  B.certificate = (b) => `<div class="cert" style="margin:0 calc(-1 * var(--page-pad))">
      <div class="body" style="padding-inline-start:var(--page-pad)">
        <div class="t">${icon('award')}${md(b.title)}</div>
        ${(b.paragraphs || []).map((p) => `<div class="p">${md(p)}</div>`).join('')}
        ${b.small ? `<div class="small" style="color:var(--primary-2)">${md(b.small)}</div>` : ''}
        ${b.list ? `<div class="lt">${md(b.listTitle || '')}</div><div class="grid">${b.list.map((x) => `<span>${md(x)}</span>`).join('')}</div>` : ''}
      </div>
      ${b.photo ? `<div class="img" ${bg(b.photo, b.photoPos)}></div>` : ''}
    </div>`;

  B.stats = (b) => `<div class="stats" style="grid-template-columns:repeat(${b.items.length},1fr)">${b.items.map((s) => `<div class="s"><b>${esc(s.value)}</b><span>${md(s.label)}</span></div>`).join('')}</div>`;

  // טבלת נתונים. תא בצורה {pill:"red", text:"..."} מוצג כתגית צבעונית
  const cell = (c) => (c && typeof c === 'object' ? `<span class="pill ${c.pill}">${md(c.text)}</span>` : md(c));
  B.table = (b) => `<div>${b.title ? `<div class="h3" style="margin-bottom:2mm">${md(b.title)}</div>` : ''}
      <table class="dtable"><thead><tr>${b.columns.map((c, i) => `<th style="${b.widths && b.widths[i] ? `width:${b.widths[i]}` : ''}">${md(c)}</th>`).join('')}</tr></thead>
      <tbody>${b.rows.map((r) => `<tr>${r.map((c) => `<td>${cell(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>
      ${b.caption ? `<div class="small" style="margin-top:1.5mm">${md(b.caption)}</div>` : ''}</div>`;

  B.steps = (b) => `<div>${b.title ? `<div class="h3" style="margin-bottom:2mm">${md(b.title)}</div>` : ''}
      <div class="steps" style="grid-template-columns:repeat(${b.items.length},1fr)">${b.items.map((s, i) => `<div class="st ${i === b.items.length - 1 ? 'last' : ''}"><b>${i + 1}</b><span>${md(s)}</span></div>`).join('')}</div>
      ${b.text ? `<div class="p" style="margin-top:2.5mm">${md(b.text)}</div>` : ''}</div>`;

  B.image = (b) => `<div class="figure"><div class="frame"><img src="${img(b.src)}" style="${b.height ? `height:${b.height};object-fit:cover;object-position:${b.pos || 'center'}` : ''}"></div>${b.caption ? `<div class="cap">${md(b.caption)}</div>` : ''}</div>`;

  B.reading = (b) => `<div>
      <div class="h3" style="font-size:19px;margin-bottom:3mm">${md(b.title)} ${b.note ? `<span class="small" style="font-weight:400;margin-inline-start:3mm">${md(b.note)}</span>` : ''}</div>
      <div class="reading">${b.columns.map((col) => `<div>${col.map((g) => `<div class="g"><div class="h3">${md(g.title)}</div>${g.items.map((x) => `<p>${md(x)}</p>`).join('')}</div>`).join('')}</div>`).join('')}</div></div>`;

  B.split = (b) => `<div style="display:grid;grid-template-columns:${b.ratio || '1fr 1fr'};gap:${b.gap || '8mm'};align-items:${b.align || 'start'}">
      ${b.columns.map((col) => `<div style="display:flex;flex-direction:column;gap:5mm">${col.map(block).join('')}</div>`).join('')}</div>`;

  B.audienceTop = (b) => `<div class="split-photo">
      <div class="txt">${B.heading(b)}${b.text ? `<div class="lead">${md(b.text)}</div>` : ''}</div>
      <div class="img" ${bg(b.photo, b.photoPos)}></div></div>`;

  B.spacer = (b) => `<div style="height:${b.height || '4mm'}"></div>`;

  function block(b) {
    const fn = B[b.type];
    if (!fn) return `<div style="color:red">סוג בלוק לא מוכר: ${esc(b.type)}</div>`;
    const html = fn(b);
    return b.bottom ? `<div class="push-bottom">${html}</div>` : html;
  }

  // ---------- pages ----------
  const LOGO = C.logo ? img(C.logo) : 'assets/logo-full.png';
  const logoDark = () => C.logo ? `<div class="logo-plate"><img src="${LOGO}"></div>` : `<div class="logo-dark"><img src="assets/logo.png"><div class="w"><b>היחידה ללימודי חוץ</b><span>OASIS CAPITAL ISRAEL</span></div></div>`;

  function cover(p) {
    const c = C.cover;
    const long = c.titleLong ? 'long' : '';
    return `<section class="page"><div class="cover">
      <div class="cover-panel">
        <img class="logo ${C.logo ? 'wide' : ''}" src="${LOGO}">
        <div class="cover-eyebrow">${md(c.eyebrow)}</div>
        <div class="cover-title ${long}">${lines(c.title)}</div>
        <div class="cover-sub">${lines(c.subtitle)}</div>
        ${c.tag ? `<div class="cover-tag">${md(c.tag)}</div>` : ''}
        <div class="cover-intro">${md(c.intro)}</div>
        ${c.big ? `<div class="cover-big"><div class="n">${esc(c.big.value)}</div><div class="l">${md(c.big.label)}</div></div>` : ''}
      </div>
      <div class="cover-photo">
        <div class="img" ${bg(c.photo, c.photoPos)}></div>
        <div class="cover-bar">${c.bar.stats ? c.bar.stats.map((s, i) => `${i ? `<span class="op">${esc(c.bar.op || '+')}</span>` : ''}<div class="stat"><b>${esc(s.value)}</b><span>${md(s.label)}</span></div>`).join('') : `<div class="text">${md(c.bar.text)}</div>`}</div>
      </div>
    </div></section>`;
  }

  function back(p) {
    const k = C.back;
    return `<section class="page"><div class="back">
      <div class="img" ${bg(k.photo, k.photoPos)}></div>
      <div class="content">
        <div><div class="eyebrow-big">${md(C.cover.eyebrow)}</div>
          <div class="title ${C.cover.titleLong ? 'long' : ''}">${lines(C.cover.title)}</div>
          <div class="sub">${lines(C.cover.subtitle)}</div></div>
        <div><div class="cta">${lines(k.cta)}</div>
          <div class="cta-p">${md(k.text)}</div>
          <div class="phone">${esc(k.phone)}</div></div>
      </div>
      <div class="bottom">
        ${k.line ? `<div class="line">${k.line.map((t, i) => `${i ? `<span class="op">${i === k.line.length - 1 && k.lineTotal ? '=' : esc(k.lineOp || '+')}</span>` : ''}<span><b>${esc(t.value)}</b> ${md(t.label)}</span>`).join('')}</div>` : ''}
        ${logoDark()}
      </div>
    </div></section>`;
  }

  function content(p, n) {
    return `<section class="page" style="${p.background ? `background:${p.background}` : ''}">
      <div class="page-body" style="${p.gap ? `gap:${p.gap}` : ''}">${p.blocks.map(block).join('')}</div>
      <div class="footer">
        <span>${md(C.footer)}<span class="num">${n}</span></span>
        <img src="${LOGO}">
      </div></section>`;
  }

  document.title = C.title;
  if (C.style) document.body.classList.add(...C.style.split(' '));
  document.getElementById('root').innerHTML = C.pages.map((p, i) => {
    if (p.type === 'cover') return cover(p);
    if (p.type === 'back') return back(p);
    return content(p, i + 1);
  }).join('');

  // סימון עמודים שהתוכן בהם גולש (נבדק גם בסקריפט ההפקה)
  window.checkOverflow = () => [...document.querySelectorAll('.page')].map((pg, i) => {
    const body = pg.querySelector('.page-body');
    if (!body) return null;
    const over = body.scrollHeight - body.clientHeight;
    if (over > 1) { pg.classList.add('overflow'); return { page: i + 1, overflowPx: over }; }
    return null;
  }).filter(Boolean);
})();
