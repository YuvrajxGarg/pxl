// PXL UI. Talks to Python through window.pywebview.api; Python pushes updates back
// by calling App.on(event, payload). Open index.html?demo in a browser for a preview.
(function () {
  const ICONS = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    download: '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M4 20h16"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    back: '<path d="m15 18-6-6 6-6"/>',
    arrowR: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    reveal: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    folder: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9L9.6 3.6A2 2 0 0 0 8.2 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/>',
    alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    bolt: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17v4M17 19h4"/>',
    github: '<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
  };
  const icon = (n) => `<svg class="i" viewBox="0 0 24 24">${ICONS[n] || ''}</svg>`;
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hydrate = (root) => root.querySelectorAll('[data-icon]').forEach((el) => {
    const svg = icon(el.dataset.icon);
    if (el.tagName === 'I') el.outerHTML = svg; else el.insertAdjacentHTML('afterbegin', svg);
  });
  hydrate(document);

  let api = null, info = {}, settings = {}, upd = null, modal = null;
  const apps = new Map();
  let view = 'discover', query = '', detailId = null, refreshing = false;

  // ---------- marks & tiles ----------
  const ARROW = '<svg class="arrow" viewBox="0 0 36 56"><path d="M11.9 25.8V6.1A6.1 6.1 0 0 1 24.1 6.1V25.8H36L18 56 0 25.8Z"/></svg>';
  function markHTML(m, size) {
    m = m || {};
    const text = esc(m.text || '');
    const glyph = m.glyph === 'strike' ? '<i class="strike"></i>' : m.glyph === 'arrow' ? ARROW :
      m.glyph === 'pixel' ? '<span class="px solo"></span>' : '';
    return `<span class="mark ${glyph ? '' : 'plain'}" style="--size:${size}">${text}${glyph}</span>`;
  }
  function tile(a, cls) {
    if (a.icon) return `<div class="tile ${cls || ''}"><img src="${esc(a.icon)}" alt=""></div>`;
    return `<div class="tile ${cls || ''}">${markHTML(a.mark, 'calc(var(--t) * .34)')}</div>`;
  }
  const pxlMark = (size) => `<span class="mark" style="--size:${size}"><span>pxl</span><span class="px solo"></span></span>`;
  const pxlTile = (cls) => `<div class="tile ${cls || ''}"><span class="mark" style="--size:calc(var(--t) * .34)"><span>pxl</span><span class="px solo"></span></span></div>`;

  // Logos are fitted to their tile by width, like the real app icons: a wide mark such
  // as "dwn↓" gets a smaller font than "tag", so every logo leaves the same margin.
  function fitMarks() {
    document.querySelectorAll('.tile > .mark:not([data-fit])').forEach((m) => {
      const t = m.parentElement.clientWidth;
      if (!t) return; // hidden, not laid out yet: the next pass picks it up
      m.style.setProperty('--size', '100px');
      const w = m.getBoundingClientRect().width;
      if (!w) return;
      // Small tiles need relatively more breathing room to read as an icon, not a label.
      const target = t <= 34 ? 0.5 : t <= 50 ? 0.56 : 0.62;
      m.style.setProperty('--size', Math.min(t * 0.34, (t * target * 100) / w).toFixed(2) + 'px');
      m.setAttribute('data-fit', '1');
    });
  }
  let fitQueued = false;
  new MutationObserver(() => {
    if (fitQueued) return;
    fitQueued = true;
    requestAnimationFrame(() => { fitQueued = false; fitMarks(); });
  }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => {
    document.querySelectorAll('.tile > .mark[data-fit]').forEach((m) => m.removeAttribute('data-fit'));
    fitMarks();
  });

  // ---------- action button ----------
  const PHASE = { queued: 'Waiting', closing: 'Closing', downloading: '', verifying: 'Verifying', installing: 'Installing', removing: 'Removing' };
  function actBtn(a, lg) {
    const L = lg ? ' lg' : '';
    if (a.job) {
      const p = a.job.phase;
      const pct = Math.round((a.job.progress || 0) * 100);
      const label = p === 'downloading' ? `${pct}%` : PHASE[p] || 'Working';
      const indet = p !== 'downloading';
      return `<button class="act job${L}${indet ? ' indet' : ''}" data-a="cancel"><i class="fill" style="width:${p === 'downloading' ? pct : 0}%"></i><span>${label}</span></button>`;
    }
    switch (a.status) {
      case 'get': return `<button class="act get${L}" data-a="install">Get</button>`;
      case 'update': return `<button class="act update${L}" data-a="install">${icon('download')}Update</button>`;
      case 'installed': return `<button class="act open${L}" data-a="open">Open</button>`;
      case 'soon': return `<button class="act off${L}" disabled>Soon</button>`;
      default: return `<button class="act off${L}" disabled title="${esc(a.reason || '')}">Unavailable</button>`;
    }
  }
  const verLine = (a) => a.status === 'update' ? `<span class="ver">${esc(a.installed_version)} ${icon('arrowR')} <b>${esc(a.latest)}</b></span>` :
    a.installed ? `<span class="ver">v${esc(a.installed_version)}</span>` : a.latest ? `<span class="ver">v${esc(a.latest)}${a.size ? ' · ' + esc(a.size) : ''}</span>` : '';

  // ---------- rendering ----------
  const list = () => [...apps.values()];
  const matches = (a) => !query || (a.name + ' ' + a.tagline + ' ' + a.category + ' ' + a.description).toLowerCase().includes(query);

  function render() {
    const all = list();
    const installed = all.filter((a) => a.installed);
    const updates = all.filter((a) => a.status === 'update' || (a.job && a.installed));
    $('#count-installed').textContent = installed.length || '';
    $('#count-updates').textContent = all.filter((a) => a.status === 'update').length || '';
    $('#update-all').classList.toggle('hidden', !(view === 'updates' && all.some((a) => a.status === 'update' && !a.job)));
    document.querySelectorAll('#nav button').forEach((b) => b.classList.toggle('on', b.dataset.view === view));
    renderLibrary(installed);
    const v = $('#view');
    const scroll = v.scrollTop;
    if (view === 'discover') v.innerHTML = discoverHTML(all.filter(matches));
    else if (view === 'installed') v.innerHTML = installedHTML(installed.filter(matches));
    else v.innerHTML = updatesHTML(updates.filter(matches));
    v.scrollTop = scroll;
    startHeroPixels();
    if (detailId) renderDetail();
  }

  // Patch just one app's buttons while a job runs, so progress doesn't rebuild the page.
  function patch(a) {
    document.querySelectorAll(`[data-id="${a.id}"] .act`).forEach((el) => {
      const lg = el.classList.contains('lg');
      el.outerHTML = actBtn(a, lg);
    });
  }

  function renderLibrary(installed) {
    const lib = $('#library');
    if (!installed.length) { lib.innerHTML = '<div class="lib-empty">Apps you install show up here, one click from opening.</div>'; return; }
    lib.innerHTML = installed.sort((x, y) => x.name.localeCompare(y.name)).map((a) => `
      <button class="lib-row" data-id="${esc(a.id)}" data-a="open-lib" title="Open ${esc(a.name)}">
        ${tile(a, 'sm')}<div class="t"><b>${esc(a.name)}</b><span>${a.job ? (PHASE[a.job.phase] || 'Updating') + '…' : 'v' + esc(a.installed_version)}</span></div>
        ${a.status === 'update' ? '<i class="dot-upd" title="Update available"></i>' : ''}<span class="go">Open</span>
      </button>`).join('');
  }

  function cardHTML(a, i) {
    return `<div class="app-card" data-id="${esc(a.id)}" data-a="detail" style="animation-delay:${i * 40}ms">
      <div class="top">${tile(a, 'md')}<div class="t"><h3>${esc(a.name)}${a.new ? '<span class="badge-new">New</span>' : ''}</h3><div class="cat">${esc(a.category)}</div></div></div>
      <p>${esc(a.tagline)}</p>
      <div class="bottom"><span class="v">${verLine(a)}</span>${actBtn(a)}</div>
    </div>`;
  }

  function featured(all) {
    if (!all.length) return null;
    const fresh = all.filter((a) => a.new);
    const pool = fresh.length ? fresh : all.filter((a) => !a.installed).length ? all.filter((a) => !a.installed) : all;
    return pool.slice().sort((x, y) => String(y.added || '').localeCompare(String(x.added || '')))[0];
  }

  function discoverHTML(all) {
    if (!apps.size) return `<div class="blank">${pxlTile('lg')}<h3>Loading apps</h3><p>Getting the list of apps from GitHub.</p></div>`;
    if (!all.length) return `<div class="blank">${pxlTile('lg')}<h3>Nothing called “${esc(query)}”</h3><p>Try another name. New apps arrive here as soon as they're released.</p></div>`;
    const f = query ? null : featured(all);
    const hero = f ? `<div class="hero" data-id="${esc(f.id)}" data-a="detail">
        <canvas id="hero-px"></canvas>
        ${tile(f, 'xl')}
        <div class="t"><div class="kick"><i></i>${f.new ? 'New in PXL' : f.installed ? 'Featured' : 'Featured · not installed yet'}</div>
          <h1>${esc(f.name)}</h1><p>${esc(f.tagline)} ${esc((f.description || '').split('. ')[0])}.</p>
          <div class="acts2">${actBtn(f, true)}<button class="btn-quiet" data-a="detail">Details</button><span class="meta2">${verLine(f)}</span></div></div>
      </div>` : '';
    return `${hero}
      <div class="sec-head"><h2>${query ? 'Results' : 'All apps'}</h2><span>${all.length} app${all.length === 1 ? '' : 's'}</span></div>
      <div class="grid">${all.map(cardHTML).join('')}
        ${query ? '' : `<div class="app-card soon-card">${'<div class="tile md ghost">' + icon('plus') + '</div>'}<b>More on the way</b><span style="font-size:12px">New apps appear here automatically.</span></div>`}
      </div>
      <div class="sync-note">${icon('github')}Apps and updates come straight from GitHub Releases</div>`;
  }

  function rowHTML(a, mode) {
    const sub = mode === 'updates'
      ? `<span class="notes1">${esc(firstNote(a.notes) || 'Bug fixes and improvements')}</span>`
      : `<span class="sub">${esc(a.category)}${a.path ? ' · ' + esc(tilde(a.path)) : ''}</span>`;
    return `<div class="app-row" data-id="${esc(a.id)}" data-a="detail">
      ${tile(a, 'md')}
      <div class="t"><b>${esc(a.name)} ${verLine(a)}</b>${sub}</div>
      <div class="acts">
        <button class="btn-icon" data-a="reveal" title="Show in ${info.os === 'mac' ? 'Finder' : 'Explorer'}">${icon('reveal')}</button>
        ${mode === 'installed' ? `<button class="btn-icon" data-a="uninstall" title="Uninstall">${icon('trash')}</button>` : ''}
      </div>
      ${mode === 'installed' && a.status === 'update' ? actBtn(a) : mode === 'installed' && !a.job ? `<button class="act open" data-a="open">Open</button>` : actBtn(a)}
    </div>`;
  }
  // "Dwn 1.1.0: Cloud on Windows, …" → "Cloud on Windows, …"
  const dropVersionPrefix = (l) => l.replace(/^[\w .-]{1,24}\bv?\d+(\.\d+)+\s*[:—–-]\s*/, '');
  const isBoilerplate = (l) => /^(what's changed|full changelog|new contributors)/i.test(l.replace(/^[#*\-\s]+/, '').trim());
  const firstNote = (n) => {
    const l = String(n || '').split('\n').map((x) => x.replace(/^[#*\-\s]+/, '').trim()).filter((x) => x && !isBoilerplate(x))[0] || '';
    return dropVersionPrefix(l);
  };

  // Release notes → HTML. Handles GitHub markdown and plain commit messages: a summary
  // line, short section names ("Windows"), "- " bullets with hard-wrapped continuation lines.
  function notesHTML(text) {
    const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '$1');
    const out = [];
    let list = null, para = null;
    const flush = () => {
      if (list) out.push(`<ul>${list.map((li) => `<li>${inline(li)}</li>`).join('')}</ul>`);
      if (para) out.push(`<p>${inline(para)}</p>`);
      list = para = null;
    };
    String(text || '').split(/\n\s*\n/).forEach((block) => {
      const lines = block.split('\n').filter((l) => l.trim() && !isBoilerplate(l));
      lines.forEach((raw, i) => {
        const l = raw.trim();
        const bullet = /^[-*•]\s+/.test(l);
        if (bullet) { if (para) flush(); (list = list || []).push(l.replace(/^[-*•]\s+/, '')); return; }
        if (list && /^\s/.test(raw)) { list[list.length - 1] += ' ' + l; return; } // wrapped bullet
        if (/^#{1,6}\s/.test(l) || (l.length <= 28 && !/[.:,]$/.test(l) && i < lines.length - 1)) {
          flush(); out.push(`<h5>${inline(l.replace(/^#+\s*/, ''))}</h5>`); return;
        }
        if (i === 0 && /\bv?\d+(\.\d+)+\s*[:—–-]/.test(l)) { flush(); out.push(`<h4>${inline(dropVersionPrefix(l))}</h4>`); return; }
        if (list) flush();
        para = para ? para + ' ' + l : l;
      });
      flush();
    });
    return out.join('') || `<p>${esc(String(text || '').trim())}</p>`;
  }
  const tilde = (p) => (info.home && p && p.startsWith(info.home) ? '~' + p.slice(info.home.length) : p);

  function installedHTML(rows) {
    if (!rows.length) return `<div class="blank">${pxlTile('lg')}<h3>${query ? 'No matches' : 'Nothing installed yet'}</h3><p>Pick something from Discover. It installs in one click and stays up to date.</p><button class="btn-quiet" data-goto="discover">${icon('grid')}Browse apps</button></div>`;
    return `<div class="sec-head"><h2>Installed</h2><span>${rows.length} app${rows.length === 1 ? '' : 's'}</span></div><div class="rows">${rows.map((a) => rowHTML(a, 'installed')).join('')}</div>`;
  }

  function updatesHTML(rows) {
    const pxlUpd = upd && ['available', 'downloading', 'ready'].includes(upd.phase);
    const pxlRow = pxlUpd ? `<div class="app-row" data-a="pxl-update">${pxlTile('md')}<div class="t"><b>PXL <span class="ver">${esc(upd.current)} ${icon('arrowR')} <b>${esc(upd.latest)}</b></span></b><span class="notes1">${esc(firstNote(upd.notes) || 'A new version of PXL')}</span></div>
      <button class="act update" data-a="pxl-update">${upd.phase === 'ready' ? 'Restart' : upd.phase === 'downloading' ? Math.round(upd.progress * 100) + '%' : 'Update'}</button></div>` : '';
    if (!rows.length && !pxlRow) {
      return `<div class="blank">${pxlTile('lg')}<h3>Everything's up to date</h3><p>${settings.auto_update_apps ? 'Updates install on their own while an app is closed.' : 'PXL checks for new versions every few hours.'} ${esc(lastChecked())}</p><button class="btn-quiet" data-a="refresh">${icon('refresh')}Check now</button></div>`;
    }
    return `<div class="sec-head"><h2>Updates</h2><span>${rows.length + (pxlRow ? 1 : 0)} available</span></div><div class="rows">${pxlRow}${rows.map((a) => rowHTML(a, 'updates')).join('')}</div>`;
  }

  function lastChecked() {
    const iso = settings._last || null;
    if (!iso) return '';
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    return s < 60 ? 'Checked just now.' : s < 3600 ? `Checked ${Math.round(s / 60)} min ago.` : `Checked ${Math.round(s / 3600)} h ago.`;
  }

  // ---------- detail ----------
  function openDetail(id) {
    detailId = id;
    const a = apps.get(id);
    if (a && a.new) { api.mark_seen(id); a.new = false; }
    $('#detail').classList.remove('hidden');
    renderDetail(true);
  }
  function closeDetail() { detailId = null; $('#detail').classList.add('hidden'); render(); }
  function renderDetail(first) {
    const a = apps.get(detailId);
    if (!a) return closeDetail();
    const d = $('#detail');
    const scroll = first ? 0 : d.scrollTop;
    const platforms = a.platforms.map((p) => p === 'mac' ? 'macOS' : p === 'windows' ? 'Windows' : p).join(' · ');
    const pub = a.published ? new Date(a.published).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '';
    d.innerHTML = `
      <div class="bar pywebview-drag-region"><button class="btn-quiet" data-a="back">${icon('back')}Back</button></div>
      <div class="inner" data-id="${esc(a.id)}">
        <div class="d-head">
          ${tile(a, 'xl')}
          <div class="t">
            <h1>${esc(a.name)}${a.new ? '<span class="badge-new">New</span>' : ''}</h1>
            <p>${esc(a.tagline)}</p>
            <div class="acts2">${actBtn(a, true)}
              ${a.installed && a.status === 'update' ? `<button class="btn-quiet" data-a="open">Open</button>` : ''}
              ${a.installed ? `<button class="btn-icon filled" data-a="reveal" title="Show in ${info.os === 'mac' ? 'Finder' : 'Explorer'}">${icon('reveal')}</button><button class="btn-icon filled" data-a="uninstall" title="Uninstall">${icon('trash')}</button>` : ''}
              ${a.reason && !a.installed ? `<span class="reason">${esc(a.reason)}</span>` : ''}
            </div>
          </div>
        </div>
        ${a.screenshots.length ? `<div class="shots">${a.screenshots.map((s) => `<img src="${esc(s)}" alt="" onerror="this.remove()">`).join('')}</div>` : ''}
        <div class="d-cols">
          <div class="card">
            <h4>About</h4>
            <div class="desc">${esc(a.description)}</div>
            ${a.highlights.length ? `<ul class="hl">${a.highlights.map((h) => `<li>${icon('check')}<span>${esc(h)}</span></li>`).join('')}</ul>` : ''}
          </div>
          <div class="card kv">
            <div><span class="k">Latest version</span><span class="v">${esc(a.latest || '—')}</span></div>
            ${a.installed ? `<div><span class="k">Installed</span><span class="v">${esc(a.installed_version || '?')}</span></div>` : ''}
            ${pub ? `<div><span class="k">Released</span><span class="v">${esc(pub)}</span></div>` : ''}
            ${a.size ? `<div><span class="k">Download</span><span class="v">${esc(a.size)}</span></div>` : ''}
            <div><span class="k">Category</span><span class="v">${esc(a.category || '—')}</span></div>
            <div><span class="k">Runs on</span><span class="v">${esc(platforms)}</span></div>
            ${a.path ? `<div><span class="k">Location</span><button class="v rtl" data-a="reveal" title="${esc(a.path)}"><bdi>${esc(tilde(a.path))}</bdi></button></div>` : ''}
            <div><span class="k">Source</span><button class="v" data-a="url" data-url="https://github.com/${esc(a.repo)}">${esc(a.repo)}</button></div>
          </div>
        </div>
        ${a.notes ? `<div class="d-notes"><div class="label" style="margin:22px 2px 8px">What's new in ${esc(a.latest)}</div><div class="notes rich">${notesHTML(a.notes)}</div></div>` : ''}
        ${a.error ? `<div class="label" style="margin-top:16px;color:var(--warn)">${esc(a.error)}</div>` : ''}
        <div class="d-links">
          <button class="link" data-a="url" data-url="${esc(a.page)}">${icon('github')} Release notes</button>
          ${a.site ? `<button class="link" data-a="url" data-url="${esc(a.site)}">Website</button>` : ''}
        </div>
      </div>`;
    hydrate(d);
    d.scrollTop = scroll;
  }

  // ---------- hero pixels: a slow field of lime pixels, brighter near the tile ----------
  let heroRAF = null;
  function startHeroPixels() {
    cancelAnimationFrame(heroRAF);
    const c = document.getElementById('hero-px');
    if (!c) return;
    const ctx = c.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const S = 9;
    let W, H, cells;
    const size = () => {
      W = c.clientWidth; H = c.clientHeight;
      c.width = W * dpr; c.height = H * dpr; ctx.scale(dpr, dpr);
      cells = [];
      for (let y = 0; y < H / S; y++) for (let x = 0; x < W / S; x++) cells.push({ x, y, p: Math.random() * 6.28, s: .3 + Math.random() * .9 });
    };
    size();
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const tick = (t) => {
      if (!document.body.contains(c)) return;
      ctx.clearRect(0, 0, W, H);
      for (const k of cells) {
        const xr = k.x * S / W;
        const a = Math.max(0, Math.sin(k.p + t / 1000 * k.s)) ** 6 * (0.06 + xr * .4);
        if (a < .02) continue;
        ctx.fillStyle = `rgba(204,255,77,${a.toFixed(3)})`;
        ctx.fillRect(k.x * S, k.y * S, S - 2, S - 2);
      }
      if (!reduce) heroRAF = requestAnimationFrame(tick);
    };
    heroRAF = requestAnimationFrame(tick);
  }

  // Splash: a pixel field that sparkles once behind the mark.
  function splashPixels() {
    const c = $('#splash-pixels');
    if (!c) return;
    const ctx = c.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const W = c.clientWidth, H = c.clientHeight, S = 12;
    c.width = W * dpr; c.height = H * dpr; ctx.scale(dpr, dpr);
    const cx = W / 2, cy = H / 2;
    const t0 = performance.now();
    const cells = [];
    for (let y = 0; y < H / S; y++) for (let x = 0; x < W / S; x++) {
      const d = Math.hypot(x * S - cx, y * S - cy);
      if (Math.random() < .5) cells.push({ x, y, d, r: Math.random() });
    }
    const tick = (now) => {
      if (!document.body.contains(c)) return;
      const t = (now - t0) / 1000;
      ctx.clearRect(0, 0, W, H);
      const wave = t * 520 - 120;
      for (const k of cells) {
        const near = Math.exp(-((k.d - wave) ** 2) / 4000);
        const a = near * (0.35 + k.r * .4) * Math.max(0, 1 - k.d / 700);
        if (a < .02) continue;
        ctx.fillStyle = `rgba(204,255,77,${a.toFixed(3)})`;
        ctx.fillRect(k.x * S, k.y * S, S - 3, S - 3);
      }
      if (t < 2.4) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // ---------- toasts & modals ----------
  function toast(text, err, action, app) {
    const t = document.createElement('div');
    t.className = 'toast' + (err ? ' err' : '');
    t.innerHTML = (app ? tile(app, 'sm') : icon(err ? 'alert' : 'check')) + `<span>${esc(text)}</span>`;
    if (action) {
      const b = document.createElement('button');
      b.textContent = action.label;
      b.onclick = () => { action.run(); t.remove(); };
      t.appendChild(b);
    }
    $('#toasts').appendChild(t);
    setTimeout(() => { t.style.transition = 'opacity .3s'; t.style.opacity = 0; setTimeout(() => t.remove(), 300); }, err ? 6500 : 4500);
  }

  function closeModal() { $('#modal-root').innerHTML = ''; modal = null; }
  function showModal(name, html, onClick, cls) {
    modal = name;
    $('#modal-root').innerHTML = `<div class="modal-back"><div class="modal ${cls || ''}">${html}</div></div>`;
    $('#modal-root .modal-back').onclick = (e) => {
      if (e.target.classList.contains('modal-back')) return closeModal();
      const el = e.target.closest('[data-m]');
      if (el) onClick(el.dataset.m, el);
    };
  }
  function confirmModal(title, body, okLabel, danger, a) {
    return new Promise((resolve) => {
      showModal('confirm', `${a ? tile(a, 'lg') : ''}<h2>${esc(title)}</h2><p>${body}</p>
        <div class="foot"><button class="btn-quiet" data-m="no">Cancel</button><button class="${danger ? 'btn-danger' : 'btn-primary inline'}" data-m="yes">${esc(okLabel)}</button></div>`,
        (m) => { closeModal(); resolve(m === 'yes'); }, 'confirm');
    });
  }

  const sw = (on) => `<span class="switch ${on ? 'on' : ''}"></span>`;
  const opt = (key, title, detail) => `<button class="opt" data-m="toggle" data-key="${key}"><div class="t"><b>${title}</b><span>${detail}</span></div>${sw(settings[key])}</button>`;
  async function toggle(el) {
    const k = el.dataset.key;
    settings = Object.assign(settings, await api.set_setting(k, !settings[k]));
    el.querySelector('.switch').classList.toggle('on', !!settings[k]);
  }

  function updateLine() {
    if (!upd) return ['', ''];
    switch (upd.phase) {
      case 'checking': return ['Checking for updates…', ''];
      case 'uptodate': return ["You're up to date", 'ok'];
      case 'available': return [`Version ${upd.latest} is available`, 'ok'];
      case 'downloading': return [`Downloading ${upd.latest}… ${Math.round(upd.progress * 100)}%`, ''];
      case 'ready': return [`Version ${upd.latest} is ready to install`, 'ok'];
      case 'installing': return ['Installing…', ''];
      case 'failed': return [upd.error || 'Update failed', 'bad'];
      default: return [upd.last_checked ? 'Checked ' + new Date(upd.last_checked).toLocaleString() : 'Never checked', ''];
    }
  }
  function renderUpdateRow() {
    const el = $('#upd-row');
    if (!el) return;
    const [line, cls] = updateLine();
    const has = upd && ['available', 'downloading', 'ready'].includes(upd.phase);
    el.innerHTML = `${pxlTile('sm')}<div class="t"><b>PXL ${esc(upd ? upd.current : info.version)}</b><span class="${cls}">${esc(line)}</span></div>
      ${has ? `<button class="btn-quiet" data-m="see-update">${icon('download')}See update</button>` : `<button class="btn-quiet" data-m="check" ${upd && upd.phase === 'checking' ? 'disabled' : ''}>${icon('refresh')}Check now</button>`}`;
  }
  function openSettings() {
    showModal('settings', `
      <div class="modal-title"><h2>Settings</h2><button class="btn-icon" data-m="close">${icon('x')}</button></div>
      <div class="label">Apps</div>
      <div class="group">
        ${opt('auto_check', 'Look for new apps and updates automatically', 'Checks GitHub at launch and every few hours')}
        ${opt('auto_update_apps', 'Update apps automatically', "Installs new versions in the background while the app isn't open")}
        ${opt('notify_new', 'Tell me when a new app arrives', 'Shows a note when an app joins PXL')}
      </div>
      <div class="label">PXL</div>
      <div class="group">
        <div class="ver-row" id="upd-row"></div>
        ${opt('auto_install', 'Download and install PXL updates automatically', 'Downloads in the background and installs when you quit')}
      </div>
      <div class="label">About</div>
      <div class="about">PXL keeps every PXLVZN app in one place. Apps install from their GitHub releases, checked against their published checksums, and run entirely on your computer. No account, no tracking.</div>
      <div class="foot"><button class="link" data-m="site">pxlvzn.in</button><button class="link" data-m="gh" style="margin-right:auto">GitHub</button><button class="link" data-m="welcome" style="margin-right:0">Replay the tour</button></div>`,
      async (m, el) => {
        if (m === 'close') closeModal();
        else if (m === 'toggle') { await toggle(el); render(); }
        else if (m === 'check') { upd = await api.check_updates(); renderUpdateRow(); renderPill(); }
        else if (m === 'see-update') openUpdate();
        else if (m === 'site') api.open_url('https://pxlvzn.in');
        else if (m === 'gh') api.open_url(upd ? upd.page : 'https://github.com/');
        else if (m === 'welcome') { closeModal(); showWelcome(true); }
      }, 'settings');
    hydrate($('#modal-root'));
    renderUpdateRow();
  }

  function renderPill() {
    const p = $('#update-pill');
    if (!upd || !['available', 'downloading', 'ready', 'installing'].includes(upd.phase)) { p.classList.add('hidden'); return; }
    p.classList.remove('hidden');
    p.innerHTML = upd.phase === 'ready' ? `${icon('refresh')}Restart to update` :
      upd.phase === 'downloading' ? `${icon('download')}Updating ${Math.round(upd.progress * 100)}%` :
      upd.phase === 'installing' ? `${icon('refresh')}Installing…` : `${icon('download')}Update to ${esc(upd.latest)}`;
  }
  function openUpdate() {
    if (!upd) return;
    const ph = upd.phase;
    const pct = Math.round((upd.progress || 0) * 100);
    const sub = ph === 'ready' ? 'Downloaded and ready. Restart now, or it installs the next time you quit.' :
      ph === 'downloading' ? `Downloading… ${pct}%` : ph === 'installing' ? 'Installing and restarting…' :
      ph === 'failed' ? (upd.error || 'Something went wrong.') : ph === 'uptodate' ? "You're on the newest version." :
      `You have ${esc(upd.current)}.` + (upd.can_install ? '' : ' This copy runs from source, so the download page opens instead.');
    const primary = ph === 'ready' ? `<button class="btn-primary inline" data-m="install">${icon('refresh')}Restart to update</button>` :
      ph === 'available' || ph === 'failed' ? `<button class="btn-primary inline" data-m="${upd.can_install ? 'download' : 'page'}">${icon('download')}${upd.can_install ? 'Download update' : 'Open download page'}</button>` : '';
    showModal('update', `
      <div class="update-hero">${pxlTile('lg')}<div><h2>${upd.latest ? 'PXL ' + esc(upd.latest) : 'Updates'}</h2><p>${sub}</p></div></div>
      ${ph === 'downloading' ? `<div class="progress"><div style="width:${pct}%"></div></div>` : ''}
      ${upd.notes ? `<div class="label">What's new</div><div class="notes rich">${notesHTML(upd.notes)}</div>` : ''}
      <div class="foot"><button class="link" data-m="page">View on GitHub</button><button class="btn-quiet" data-m="close">Later</button>${primary}</div>`,
      (m) => {
        if (m === 'close') closeModal();
        else if (m === 'install') api.install_update();
        else if (m === 'download') api.download_update();
        else if (m === 'page') api.open_url(upd.page);
      });
  }

  // ---------- actions ----------
  async function doInstall(a) {
    let r = await api.install(a.id, false);
    if (r && r.needs_quit) {
      const ok = await confirmModal(`Quit ${a.name} to update?`, `${esc(a.name)} is open. PXL will quit it, install ${esc(a.latest)} and you can open it again right after.`, `Quit and update`, false, a);
      if (ok) await api.install(a.id, true);
    }
  }
  async function doUninstall(a) {
    const where = info.os === 'mac' ? 'It moves to the Trash, so you can put it back.' : 'Its files are removed from this computer.';
    if (await confirmModal(`Uninstall ${a.name}?`, `${where} Your ${esc(a.name)} settings stay, in case you install it again.`, 'Uninstall', true, a)) api.uninstall(a.id);
  }

  function onAction(e) {
    const goto = e.target.closest('[data-goto]');
    if (goto) { setView(goto.dataset.goto); return; }
    const el = e.target.closest('[data-a]');
    if (!el) return;
    const holder = el.closest('[data-id]');
    const a = holder ? apps.get(holder.dataset.id) : null;
    const act = el.dataset.a;
    e.stopPropagation();
    if (act === 'detail' && a) openDetail(a.id);
    else if (act === 'back') closeDetail();
    else if (act === 'install' && a) doInstall(a);
    else if (act === 'open' && a) { api.open_app(a.id); toast(`Opening ${a.name}`, false, null, a); }
    else if (act === 'open-lib' && a) { api.open_app(a.id); toast(`Opening ${a.name}`, false, null, a); }
    else if (act === 'cancel' && a && a.job && a.job.phase === 'queued') api.cancel(a.id);
    else if (act === 'reveal' && a) api.reveal(a.id);
    else if (act === 'uninstall' && a) doUninstall(a);
    else if (act === 'url') api.open_url(el.dataset.url);
    else if (act === 'refresh') api.refresh(true);
    else if (act === 'pxl-update') upd && upd.phase === 'ready' ? api.install_update() : openUpdate();
  }
  $('#view').addEventListener('click', onAction);
  $('#detail').addEventListener('click', onAction);
  $('#library').addEventListener('click', onAction);

  function setView(v) {
    view = v;
    if (detailId) { detailId = null; $('#detail').classList.add('hidden'); }
    $('#view').scrollTop = 0;
    render();
  }
  $('#nav').onclick = (e) => { const b = e.target.closest('button'); if (b) setView(b.dataset.view); };
  $('#search').oninput = (e) => { query = e.target.value.trim().toLowerCase(); if (detailId) closeDetail(); else render(); };
  $('#refresh').onclick = () => api.refresh(true);
  $('#open-settings').onclick = () => openSettings();
  $('#update-pill').onclick = () => openUpdate();
  $('#update-all').onclick = async () => { const n = await api.update_all(); if (n) toast(`Updating ${n} app${n === 1 ? '' : 's'}`); };
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { if (modal) closeModal(); else if (detailId) closeDetail(); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') { e.preventDefault(); $('#search').focus(); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'r') { e.preventDefault(); api.refresh(true); }
  });

  // ---------- welcome tour (first launch) ----------
  function showWelcome(replay) {
    const w = $('#welcome');
    let page = 0;
    const picks = new Set();
    const avail = () => list().filter((a) => !a.reason || a.installed);
    const pages = [
      () => `${pxlTile('xl')}
        <h1>Welcome to PXL</h1>
        <p class="motto"><span>A technical creative suite</span> <b>for creatively technical people.</b></p>
        <p class="lead">Every PXLVZN app, installed, opened and kept up to date from one window.</p>
        <div class="facts">
          <div class="card fact">${icon('bolt')}<b>One click</b><span>Apps download, verify and install themselves. No zips, no dragging.</span></div>
          <div class="card fact">${icon('refresh')}<b>Always current</b><span>New apps and new versions show up the moment they're released.</span></div>
          <div class="card fact">${icon('lock')}<b>No account</b><span>Straight from GitHub to your computer. Nothing tracked, ever.</span></div>
        </div>`,
      () => `<div class="tile-row">${list().slice(0, 3).map((a) => `<div class="lbl">${tile(a, 'lg')}${esc(a.name)}</div>`).join('')}<div class="lbl"><div class="tile lg ghost">${icon('plus')}</div>Next</div></div>
        <h1>Small tools. One job each.</h1>
        <p class="lead">Every app does one thing, and does it well.<br>New ones show up here the moment they're released.</p>`,
      () => `<h1>Stay up to date</h1>
        <p class="lead">PXL keeps your apps current so you never download a zip again.</p>
        <div class="group">
          ${opt('auto_check', 'Look for new apps and updates automatically', 'Checks GitHub at launch and every few hours')}
          ${opt('auto_update_apps', 'Update apps automatically', "Installs new versions while the app isn't open")}
          ${opt('notify_new', 'Tell me when a new app arrives', 'Shows a note when an app joins PXL')}
          ${opt('auto_install', 'Keep PXL itself up to date', 'Downloads in the background and installs when you quit')}
        </div>`,
      () => `<h1>Pick your first apps</h1>
        <p class="lead">They install in the background while you look around.</p>
        <div class="pick">${avail().map((a) => `<button data-w="pick" data-id="${esc(a.id)}" class="${picks.has(a.id) ? 'on' : ''}" ${a.installed ? 'disabled' : ''}>
          ${tile(a, 'md')}<div class="t"><b>${esc(a.name)}</b><span>${esc(a.tagline)}</span></div>
          ${a.installed ? `<span class="done">${icon('check')}Installed</span>` : `<span class="check">${icon('check')}</span>`}</button>`).join('') || '<p class="faint">Apps are still loading. You can install them from Discover.</p>'}</div>`,
    ];
    const render = () => {
      const last = page === pages.length - 1;
      const label = last ? (picks.size ? `Install ${picks.size} & start` : 'Get started') : 'Continue';
      w.innerHTML = `<div class="glow"></div><div class="dots">${pages.map((_, i) => `<i class="${i <= page ? 'on' : ''} ${i === page ? 'cur' : ''}"></i>`).join('')}</div>
        <div class="page">${pages[page]()}</div>
        <div class="foot">${page ? '<button class="btn-quiet" data-w="back">Back</button>' : '<button class="link" data-w="skip">Skip</button>'}
          <button class="btn-primary" data-w="next">${label}</button></div>`;
    };
    const finish = async () => {
      w.classList.add('hidden');
      settings = Object.assign(settings, await api.set_setting('welcomed', true));
      await api.mark_seen(null);
      list().forEach((a) => { a.new = false; });
      for (const id of picks) { const a = apps.get(id); if (a) doInstall(a); }
      if (picks.size) toast(`Installing ${picks.size} app${picks.size === 1 ? '' : 's'}`);
      render0();
      if (!settings.toured || replay) setTimeout(startCoach, 450);
    };
    w.onclick = async (e) => {
      const t = e.target.closest('[data-w],[data-m]');
      if (!t) return;
      if (t.dataset.m === 'toggle') await toggle(t);
      else if (t.dataset.w === 'pick') { const id = t.dataset.id; picks.has(id) ? picks.delete(id) : picks.add(id); render(); }
      else if (t.dataset.w === 'back') { page--; render(); }
      else if (t.dataset.w === 'skip') finish();
      else if (t.dataset.w === 'next') { if (page < pages.length - 1) { page++; render(); } else finish(); }
    };
    // Preselect everything not installed yet on first launch.
    if (!replay) avail().forEach((a) => { if (!a.installed && a.status === 'get') picks.add(a.id); });
    render();
    w.classList.remove('hidden');
  }
  const render0 = () => render();

  // Coach marks: three quick pointers at the real interface.
  function startCoach() {
    const steps = [
      { el: '#nav', title: 'Everything lives here', text: 'Discover every app, see what you have installed, and catch updates. The lime badge counts what’s waiting.' },
      { el: '#library', title: 'Your apps, one click away', text: 'Installed apps line up in the sidebar. Click one to open it.' },
      { el: '#search-box', title: 'Find anything', text: 'Search by name or what it does. Press ⌘F / Ctrl+F from anywhere.' },
      { el: '.top-actions', title: 'Refresh and settings', text: 'Check for new apps right now, or change how updates work. PXL updates itself too, from the pill at the bottom left.' },
    ];
    let i = 0;
    const c = $('#coach');
    c.classList.remove('hidden');
    c.innerHTML = '<div class="hole"></div><div class="tip"></div>';
    const show = () => {
      const s = steps[i];
      const target = $(s.el);
      if (!target) return next();
      const r = target.getBoundingClientRect();
      const pad = 6;
      Object.assign(c.querySelector('.hole').style, { left: r.left - pad + 'px', top: r.top - pad + 'px', width: Math.max(r.width, 40) + pad * 2 + 'px', height: Math.max(r.height, 30) + pad * 2 + 'px' });
      const tip = c.querySelector('.tip');
      tip.innerHTML = `<b>${esc(s.title)}</b><p>${esc(s.text)}</p><div class="row3"><span class="step">${i + 1} of ${steps.length}</span>
        <button class="link" data-c="skip">Skip</button><button class="btn-primary" data-c="next">${i === steps.length - 1 ? 'Done' : 'Next'}</button></div>`;
      const right = r.right + 18 + 290 < innerWidth;
      const left = right ? r.right + 18 : Math.max(16, Math.min(innerWidth - 306, r.left + r.width - 290));
      const top = right ? Math.max(16, Math.min(innerHeight - 190, r.top)) : r.bottom + 16;
      Object.assign(tip.style, { left: left + 'px', top: top + 'px' });
    };
    const done = () => { c.classList.add('hidden'); c.innerHTML = ''; api.set_setting('toured', true); settings.toured = true; };
    const next = () => { i++; if (i >= steps.length) done(); else show(); };
    c.onclick = (e) => { const b = e.target.closest('[data-c]'); if (!b) return; b.dataset.c === 'skip' ? done() : next(); };
    show();
  }

  // ---------- events from Python ----------
  function setCheckLine() {
    const all = list();
    const n = all.length;
    $('#check-row .dot').classList.toggle('spin', refreshing);
    $('#check-line').textContent = refreshing ? 'Checking for apps and updates…' : n ? `${n} app${n === 1 ? '' : 's'} · ${(u => u ? u + ' update' + (u === 1 ? '' : 's') : 'all up to date')(all.filter((a) => a.status === 'update').length)}` : 'No apps yet';
    $('#refresh').classList.toggle('spinning', refreshing);
  }

  window.App = {
    on(event, p) {
      if (event === 'apps') {
        apps.clear();
        p.forEach((a) => apps.set(a.id, a));
        settings._last = new Date().toISOString();
        render(); setCheckLine();
      } else if (event === 'app') {
        apps.set(p.id, p); render(); setCheckLine();
      } else if (event === 'job') {
        const a = apps.get(p.id);
        if (a) { a.job = p.job; patch(a); renderLibrary(list().filter((x) => x.installed)); }
      } else if (event === 'installed') {
        const a = apps.get(p.id) || { name: p.name };
        toast(`${p.verb} ${p.name} ${p.version}`, false, { label: 'Open', run: () => api.open_app(p.id) }, a);
      } else if (event === 'new_app') {
        apps.set(p.id, p); render();
        toast(`New app: ${p.name}. ${p.tagline}`, false, { label: 'See it', run: () => openDetail(p.id) }, p);
      } else if (event === 'refreshing') {
        refreshing = p.on; setCheckLine();
      } else if (event === 'toast') toast(p.text, p.err);
      else if (event === 'update') {
        const prev = upd && upd.phase;
        upd = p;
        renderPill();
        if (modal === 'update') openUpdate();
        else if (modal === 'settings') renderUpdateRow();
        if (view === 'updates') render();
        if (prev !== 'ready' && p.phase === 'ready' && modal !== 'update')
          toast(`PXL ${p.latest} is ready`, false, { label: 'Restart', run: () => api.install_update() });
      }
    },
  };

  // ---------- start ----------
  async function start(a) {
    api = a;
    info = await api.info();
    document.body.classList.add(info.os === 'mac' ? 'mac' : info.os === 'windows' ? 'win' : 'other');
    $('#version').textContent = 'v' + info.version;
    settings = info.settings || {};
    upd = info.update;
    renderPill();
    splashPixels();
    const first = await api.apps();
    first.forEach((x) => apps.set(x.id, x));
    render(); setCheckLine();
    // ?still (demo only) skips the intro animation, for screenshots.
    const still = location.search.includes('still');
    if (still) document.documentElement.classList.add('still');
    const wait = still ? 0 : 1500;
    setTimeout(() => { $('#splash').classList.add('out'); $('#app').classList.add('in'); }, wait);
    setTimeout(() => { const s = $('#splash'); if (s) s.remove(); }, still ? 0 : 2100);
    if (!settings.welcomed) setTimeout(() => showWelcome(false), wait);
    else if (!settings.toured) setTimeout(startCoach, wait + 400);
  }

  // Demo data for previewing in a plain browser: index.html?demo (&welcome, &update, &new).
  function demoApi() {
    const q = location.search;
    const reg = [
      { id: 'dwn', name: 'Dwn', mark: { text: 'dwn', glyph: 'arrow' }, tagline: 'Download anything on the internet.', category: 'Download', repo: 'YuvrajxGarg/dwn', site: 'https://dwn.pxlvzn.in', added: '2026-11-08',
        description: 'Videos, songs, playlists and transcripts from YouTube, TikTok, Instagram, X, SoundCloud and over a thousand other sites, plus whole Google Drive and Dropbox folders without split zips. No accounts, no servers.',
        highlights: ['Paste a link, pick a format, done', 'Up to 4K and 8K, MP3, WAV or a transcript', 'Whole cloud folders, never split zips', 'Quick-download panel from any app'],
        screenshots: ['https://raw.githubusercontent.com/YuvrajxGarg/dwn/main/site/assets/links.png', 'https://raw.githubusercontent.com/YuvrajxGarg/dwn/main/site/assets/cloud.png'],
        platforms: ['mac', 'windows'], installed: true, installed_version: '1.0.9', latest: '1.1.0', size: '117.3 MB', status: 'update', path: '/Applications/Dwn.app',
        notes: 'Dwn 1.1.0: Cloud on Windows, download-finished panel, restart after updates\n\nWindows\n- Cloud tab, matching the Mac: accounts, Shared with me by person, Shared\n  links, two-pane drag and drop and transfers.\n- Installer ends on a "Dwn is installed" page; updates stay silent.\n\nBoth\n- "Download finished" panel with files you can drag into other apps,\n  and a finish sound.\n- Cloud step in the first-run tour.\n\nMac\n- Dwn reopens after every update and brings its window forward.', page: 'https://github.com/YuvrajxGarg/dwn/releases', published: '2026-11-11T18:44:11Z' },
      { id: 'tag', name: 'Tag', mark: { text: 'tag', glyph: 'strike' }, tagline: 'Take the AI tags off your photos and videos.', category: 'Photo & video', repo: 'YuvrajxGarg/tag', added: '2026-11-11',
        description: 'Strips C2PA Content Credentials, “made with AI” labels and generator metadata from photos and videos. Lossless: nothing is re-encoded and your originals are never touched.',
        highlights: ['Drop photos, videos or whole folders', 'See every AI and C2PA tag a file carries', 'Clean copies, every pixel untouched'],
        screenshots: ['https://raw.githubusercontent.com/YuvrajxGarg/tag/main/docs/screenshot-scan.png', 'https://raw.githubusercontent.com/YuvrajxGarg/tag/main/docs/screenshot-clean.png'],
        platforms: ['mac', 'windows'], installed: false, installed_version: '', latest: '1.0.0', size: '35.9 MB', status: 'get', new: q.includes('new'),
        notes: 'First release.', page: 'https://github.com/YuvrajxGarg/tag/releases', published: '2026-11-11T16:23:32Z' },
    ];
    reg.forEach((r) => { r.job = null; r.error = null; r.reason = null; r.new = !!r.new; });
    const pub = (r) => JSON.parse(JSON.stringify(r));
    const run = (id) => {
      const r = reg.find((x) => x.id === id);
      let f = 0;
      r.job = { phase: 'downloading', progress: 0 };
      App.on('app', pub(r));
      const t = setInterval(() => {
        f += 0.07;
        if (f < 1) { r.job.progress = f; App.on('job', { id, job: pub(r.job) }); return; }
        clearInterval(t);
        r.job = { phase: 'installing', progress: 1 }; App.on('job', { id, job: pub(r.job) });
        setTimeout(() => {
          const verb = r.installed ? 'Updated' : 'Installed';
          Object.assign(r, { job: null, installed: true, installed_version: r.latest, status: 'installed', path: '/Applications/' + r.name + '.app' });
          App.on('app', pub(r)); App.on('installed', { id, name: r.name, version: r.latest, verb });
        }, 900);
      }, 120);
    };
    return {
      info: async () => ({ version: '1.0.0', platform: 'darwin', os: 'mac', home: '/Users/demo',
        settings: { auto_check: true, auto_update_apps: true, auto_install: true, notify_new: true, welcomed: !q.includes('welcome'), toured: !q.includes('welcome') && !q.includes('tour') },
        update: { phase: q.includes('update') ? 'available' : 'uptodate', current: '1.0.0', latest: '1.1.0', progress: 0, can_install: true,
          notes: '- Faster installs\n- Category filters', page: 'https://github.com/YuvrajxGarg/pxl/releases', last_checked: new Date().toISOString() } }),
      apps: async () => reg.map(pub),
      set_setting: async (k, v) => { settings[k] = v; return Object.assign({}, settings); },
      mark_seen: async () => true,
      refresh: () => { App.on('refreshing', { on: true }); setTimeout(() => { App.on('apps', reg.map(pub)); App.on('refreshing', { on: false }); }, 900); },
      install: async (id, quit) => { const r = reg.find((x) => x.id === id); if (r.installed && !quit) return { needs_quit: true }; run(id); return { ok: true }; },
      update_all: async () => { const u = reg.filter((r) => r.status === 'update'); u.forEach((r) => run(r.id)); return u.length; },
      uninstall: (id) => { const r = reg.find((x) => x.id === id); Object.assign(r, { installed: false, installed_version: '', status: 'get', path: null }); App.on('app', pub(r)); App.on('toast', { text: r.name + ' was removed (moved to the Trash)' }); },
      cancel() {}, open_app() {}, reveal() {}, open_url() {},
      check_updates: async () => upd, download_update() {}, install_update() {},
    };
  }

  if (location.search.includes('demo')) {
    start(demoApi()).then(() => {
      const q = new URLSearchParams(location.search);
      if (q.get('view')) setView(q.get('view'));
      if (q.get('detail')) setTimeout(() => openDetail(q.get('detail')), 50);
    });
  }
  else if (window.pywebview && window.pywebview.api) start(window.pywebview.api);
  else window.addEventListener('pywebviewready', () => start(window.pywebview.api));
})();
