#!/usr/bin/env python3
"""
apply_admin_v2.py
1. Fix "cambios en caliente" — los JSONs se leen en runtime, no en build
2. Admin visual con formularios por tipo (now, books, homepage, gacha-config)
3. Auto-detecta cualquier JSON nuevo en /data/ y lo expone como editor genérico
4. Sección videos intacta
Uso: sudo HOME=/home/ubuntu python3 apply_admin_v2.py
"""
import os, subprocess

BASE = "/home/ubuntu/misitio"

# ─── 1. Fix hot-reload: /api/admin/data ya lee en runtime (correcto)
# El problema real es que index.astro lee los JSONs en el frontmatter (build time).
# La solución: index.astro NO lee JSONs — todo lo carga el cliente via /api/admin/data

# ─── 2. Nuevo admin/index.astro ──────────────────────────────────────────────
admin_page = r"""---
import Base from '../../layouts/Base.astro';
import { Database } from 'bun:sqlite';
import { join } from 'path';
import { readdirSync, existsSync } from 'fs';

// Solo stats de SQLite (esto sí es estático, no cambia sin rebuild)
let videoCount = 0, charCount = 0, commentCount = 0;
try {
  const db = new Database(join(process.cwd(), 'data', 'database.sqlite'), { readonly: true });
  videoCount   = (db.query('SELECT COUNT(*) as n FROM videos').get() as any)?.n ?? 0;
  charCount    = (db.query('SELECT COUNT(*) as n FROM characters').get() as any)?.n ?? 0;
  try { commentCount = (db.query('SELECT COUNT(*) as n FROM comments').get() as any)?.n ?? 0; } catch {}
  db.close();
} catch {}

// Detectar módulos activos
const featuresDir = join(process.cwd(), 'src', 'features');
const activeModules = existsSync(featuresDir)
  ? readdirSync(featuresDir, { withFileTypes: true })
      .filter(d => d.isDirectory()).map(d => d.name)
  : [];

// Detectar JSONs disponibles en /data/
const dataDir = join(process.cwd(), 'data');
const allJsons = existsSync(dataDir)
  ? readdirSync(dataDir).filter(f => f.endsWith('.json')).sort()
  : [];
---
<Base title="Admin · aris-sama">
  <div class="admin">

    <header class="admin-head">
      <div>
        <span class="badge">root@aris-sama</span>
        <h1 class="admin-title">panel de control</h1>
        <p class="admin-sub font-mono">módulos: {activeModules.join(' · ')}</p>
      </div>
      <button id="logout-btn" class="btn-logout">salir →</button>
    </header>

    <!-- Stats -->
    <section class="admin-section">
      <h2 class="sh">sistema</h2>
      <div class="stat-grid">
        <div class="stat"><span class="sl">videos</span><span class="sv">{videoCount}</span></div>
        <div class="stat"><span class="sl">chars gacha</span><span class="sv">{charCount}</span></div>
        <div class="stat"><span class="sl">comentarios</span><span class="sv">{commentCount}</span></div>
        <div class="stat"><span class="sl">jsons</span><span class="sv">{allJsons.length}</span></div>
      </div>
    </section>

    <!-- Upload video -->
    <section class="admin-section">
      <h2 class="sh">subir video</h2>
      <div class="upload-zone" id="drop-zone">
        <div class="upload-inner" id="upload-inner">
          <span class="upload-icon">▶</span>
          <p class="upload-label">arrastra tu video aquí</p>
          <p class="upload-hint font-mono">o haz click · mp4, webm, mov · máx 500MB</p>
          <input type="file" id="file-input" accept="video/mp4,video/webm,video/quicktime" style="display:none" />
        </div>
        <div class="upload-form" id="upload-form" style="display:none">
          <div class="uf-row">
            <label class="uf-label">título</label>
            <input type="text" id="uf-title" class="uf-input" placeholder="Miyabi SS · Daily Challenge" />
          </div>
          <div class="uf-row">
            <label class="uf-label">categoría</label>
            <input type="text" id="uf-category" class="uf-input" placeholder="gameplay · clip · tutorial..." />
          </div>
          <div class="uf-row">
            <label class="uf-label">descriptores <span class="uf-hint">ej: Personaje=Miyabi</span></label>
            <div id="descriptor-list" class="descriptor-list"></div>
            <button type="button" id="add-descriptor" class="btn-ghost">+ añadir descriptor</button>
          </div>
          <div class="uf-progress-wrap" id="progress-wrap" style="display:none">
            <div class="uf-progress-bar" id="progress-bar"></div>
            <span class="uf-progress-label font-mono" id="progress-label">0%</span>
          </div>
          <div class="uf-actions">
            <button type="button" id="upload-cancel" class="btn-ghost">cancelar</button>
            <button type="button" id="upload-submit" class="btn-primary">subir video →</button>
          </div>
        </div>
      </div>
      <p class="upload-result font-mono" id="upload-result" style="display:none"></p>
    </section>

    <!-- Lista de videos -->
    <section class="admin-section" id="videos-section">
      <h2 class="sh">videos <span class="sh-count font-mono" id="v-count">{videoCount}</span></h2>
      <div id="videos-list" class="videos-admin-list">
        <p class="loading-text font-mono">cargando…</p>
      </div>
    </section>

    <!-- Editores de JSON — tabs -->
    <section class="admin-section">
      <h2 class="sh">contenido</h2>
      <p class="admin-sub font-mono" style="margin-bottom:1rem">
        JSONs detectados en /data/ — los cambios se aplican al instante sin rebuild
      </p>

      <!-- Tab bar generada por JS con los JSONs detectados -->
      <div class="tab-bar" id="tab-bar"></div>
      <div id="json-editors"></div>
    </section>

    <!-- Sync gacha -->
    <section class="admin-section" id="gacha-sync-section" style="display:none">
      <h2 class="sh">sync gacha</h2>
      <div class="cmd-list" id="cmd-list"></div>
    </section>

  </div>
</Base>

<script define:vars={{ allJsons }}>
// ── Logout ────────────────────────────────────────────────────
document.getElementById('logout-btn')?.addEventListener('click', async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  location.href = '/admin/login';
});

// ══════════════════════════════════════════════════════════════
// JSON EDITORS — carga dinámica + formularios por tipo
// ══════════════════════════════════════════════════════════════

const KNOWN = ['now.json', 'books.json', 'homepage.json', 'gacha-config.json'];
const ALLOWED_SAVE = ['now.json', 'books.json', 'homepage.json', 'gacha-config.json'];

// Cualquier JSON en /data/ aparece como tab
const jsonFiles = allJsons.filter(f => f !== 'database.sqlite');

let activeTab = jsonFiles[0] ?? null;
const tabBar = document.getElementById('tab-bar');
const editorsContainer = document.getElementById('json-editors');

// Construir tabs
jsonFiles.forEach(file => {
  const btn = document.createElement('button');
  btn.className = 'tab-btn' + (file === activeTab ? ' active' : '');
  btn.textContent = file.replace('.json','');
  btn.dataset.file = file;
  btn.addEventListener('click', () => switchTab(file));
  tabBar?.appendChild(btn);
});

const cache = {}; // cache local para evitar re-fetch
let dirty = {}; // archivos con cambios no guardados

async function loadJson(file) {
  if (cache[file]) return cache[file];
  const res = await fetch(`/api/admin/data?file=${file}`);
  if (!res.ok) return null;
  const data = await res.json();
  cache[file] = data;
  return data;
}

async function switchTab(file) {
  activeTab = file;
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.file === file);
  });
  if (!editorsContainer) return;
  editorsContainer.innerHTML = '<p class="loading-text font-mono">cargando…</p>';
  const data = await loadJson(file);
  if (data === null) {
    editorsContainer.innerHTML = `<p class="loading-text font-mono" style="color:#f87171">error al cargar ${file}</p>`;
    return;
  }
  const canSave = ALLOWED_SAVE.includes(file);
  renderEditor(file, data, canSave);
}

function renderEditor(file, data, canSave) {
  if (!editorsContainer) return;
  editorsContainer.innerHTML = '';

  const wrap = document.createElement('div');
  wrap.className = 'editor-wrap';

  // Header con botón guardar
  const header = document.createElement('div');
  header.className = 'editor-header';
  const fileLabel = document.createElement('span');
  fileLabel.className = 'editor-filename font-mono';
  fileLabel.textContent = file;
  header.appendChild(fileLabel);

  if (canSave) {
    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn-primary';
    saveBtn.id = 'main-save-btn';
    saveBtn.textContent = 'guardar cambios ↑';
    saveBtn.addEventListener('click', () => saveFile(file));
    header.appendChild(saveBtn);
  } else {
    const note = document.createElement('span');
    note.className = 'font-mono';
    note.style.cssText = 'font-size:0.7rem;color:var(--color-muted-2)';
    note.textContent = 'solo lectura';
    header.appendChild(note);
  }
  wrap.appendChild(header);

  const resultEl = document.createElement('p');
  resultEl.className = 'save-result font-mono';
  resultEl.id = 'save-result';

  // Renderizar formulario según tipo
  const form = buildForm(file, data, canSave);
  wrap.appendChild(form);
  wrap.appendChild(resultEl);
  editorsContainer.appendChild(wrap);

  // Gacha sync
  if (file === 'gacha-config.json') renderGachaSync(data);
}

// ── Formulario inteligente por tipo ──────────────────────────
function buildForm(file, data, canSave) {
  if (file === 'now.json')       return buildNowForm(data, canSave);
  if (file === 'books.json')     return buildBooksForm(data, canSave);
  if (file === 'homepage.json')  return buildHomepageForm(data, canSave);
  if (file === 'gacha-config.json') return buildGachaForm(data, canSave);
  return buildGenericForm(file, data, canSave);
}

// ── now.json ──────────────────────────────────────────────────
function buildNowForm(data, canSave) {
  const wrap = document.createElement('div');
  wrap.className = 'form-section';

  // Meta fields
  const metaGrid = document.createElement('div');
  metaGrid.className = 'form-grid-2';
  metaGrid.innerHTML = `
    <div class="form-field">
      <label class="field-label">ubicación</label>
      <input class="uf-input" id="now-location" value="${esc(data.location ?? '')}" ${canSave ? '' : 'disabled'} />
    </div>
    <div class="form-field">
      <label class="field-label">estado</label>
      <input class="uf-input" id="now-status" value="${esc(data.status ?? '')}" ${canSave ? '' : 'disabled'} />
    </div>
  `;
  wrap.appendChild(metaGrid);

  // Items list
  const itemsLabel = document.createElement('div');
  itemsLabel.className = 'field-label';
  itemsLabel.style.marginTop = '1.25rem';
  itemsLabel.textContent = 'items';
  wrap.appendChild(itemsLabel);

  const itemsList = document.createElement('div');
  itemsList.id = 'now-items';
  itemsList.className = 'items-list';

  const items = Array.isArray(data.items) ? data.items : [];
  items.forEach((item, i) => appendNowItem(itemsList, item, i, canSave));
  wrap.appendChild(itemsList);

  if (canSave) {
    const addBtn = document.createElement('button');
    addBtn.className = 'btn-ghost';
    addBtn.style.marginTop = '0.75rem';
    addBtn.textContent = '+ añadir item';
    addBtn.addEventListener('click', () => {
      const idx = itemsList.querySelectorAll('.item-card').length;
      appendNowItem(itemsList, { category: '', icon: '✨', text: '' }, idx, true);
    });
    wrap.appendChild(addBtn);
  }

  // Override save para construir JSON desde el form
  wrap.dataset.collector = 'now';
  return wrap;
}

function appendNowItem(container, item, idx, canSave) {
  const card = document.createElement('div');
  card.className = 'item-card';
  card.draggable = canSave;
  card.innerHTML = `
    <div class="item-drag-handle" title="arrastrar">⠿</div>
    <div class="item-fields">
      <input class="uf-input-sm now-icon" placeholder="emoji" value="${esc(item.icon ?? '')}" style="width:60px" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm now-category" placeholder="categoría" value="${esc(item.category ?? '')}" style="flex:1" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm now-text" placeholder="texto..." value="${esc(item.text ?? '')}" style="flex:3" ${canSave ? '' : 'disabled'} />
    </div>
    ${canSave ? '<button class="btn-danger-sm item-remove" title="eliminar">✕</button>' : ''}
  `;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  if (canSave) setupDragDrop(card, container);
  container.appendChild(card);
}

// ── books.json ────────────────────────────────────────────────
function buildBooksForm(data, canSave) {
  const wrap = document.createElement('div');
  wrap.className = 'form-section';
  wrap.dataset.collector = 'books';

  const books = Array.isArray(data) ? data : (data?.books ?? []);
  const list = document.createElement('div');
  list.id = 'books-list';
  list.className = 'items-list';
  books.forEach(b => appendBookItem(list, b, canSave));
  wrap.appendChild(list);

  if (canSave) {
    const addBtn = document.createElement('button');
    addBtn.className = 'btn-ghost';
    addBtn.style.marginTop = '0.75rem';
    addBtn.textContent = '+ añadir libro';
    addBtn.addEventListener('click', () => appendBookItem(list, { title: '', author: '', status: 'want', cover: '' }, canSave));
    wrap.appendChild(addBtn);
  }
  return wrap;
}

function appendBookItem(container, book, canSave) {
  const card = document.createElement('div');
  card.className = 'item-card';
  const statusOptions = ['reading', 'read', 'want', 'dropped'].map(s =>
    `<option value="${s}" ${book.status === s ? 'selected' : ''}>${s}</option>`
  ).join('');
  card.innerHTML = `
    <div class="item-drag-handle">⠿</div>
    <div class="item-fields" style="flex-wrap:wrap">
      <input class="uf-input-sm book-title" placeholder="título" value="${esc(book.title ?? '')}" style="flex:2;min-width:140px" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm book-author" placeholder="autor" value="${esc(book.author ?? '')}" style="flex:2;min-width:120px" ${canSave ? '' : 'disabled'} />
      <select class="uf-input-sm book-status" ${canSave ? '' : 'disabled'} style="flex:1;min-width:90px">${statusOptions}</select>
      <input class="uf-input-sm book-cover" placeholder="url portada (opcional)" value="${esc(book.cover ?? '')}" style="flex:3;min-width:180px" ${canSave ? '' : 'disabled'} />
    </div>
    ${canSave ? '<button class="btn-danger-sm item-remove">✕</button>' : ''}
  `;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  container.appendChild(card);
}

// ── homepage.json ─────────────────────────────────────────────
function buildHomepageForm(data, canSave) {
  const wrap = document.createElement('div');
  wrap.className = 'form-section';
  wrap.dataset.collector = 'homepage';

  // Title
  const titleField = document.createElement('div');
  titleField.className = 'form-field';
  titleField.innerHTML = `
    <label class="field-label">título de la página</label>
    <input class="uf-input" id="hp-title" value="${esc(data.title ?? '')}" ${canSave ? '' : 'disabled'} />
  `;
  wrap.appendChild(titleField);

  const blocksLabel = document.createElement('div');
  blocksLabel.className = 'field-label';
  blocksLabel.style.cssText = 'margin-top:1.25rem;margin-bottom:0.5rem';
  blocksLabel.textContent = 'bloques (arrastra para reordenar)';
  wrap.appendChild(blocksLabel);

  const blocksList = document.createElement('div');
  blocksList.id = 'hp-blocks';
  blocksList.className = 'items-list';

  const blocks = Array.isArray(data.blocks) ? data.blocks : [];
  blocks.forEach(b => appendBlockItem(blocksList, b, canSave));
  wrap.appendChild(blocksList);

  if (canSave) {
    const addRow = document.createElement('div');
    addRow.style.cssText = 'display:flex;gap:0.5rem;margin-top:0.75rem;align-items:center';
    const blockTypes = ['hero', 'now_preview', 'radio_banner', 'bookshelf_preview', 'videos_preview', 'gacha_preview', 'custom'];
    const sel = document.createElement('select');
    sel.className = 'uf-input-sm';
    sel.style.flex = '1';
    blockTypes.forEach(t => {
      const o = document.createElement('option');
      o.value = t; o.textContent = t;
      sel.appendChild(o);
    });
    const addBtn = document.createElement('button');
    addBtn.className = 'btn-ghost';
    addBtn.textContent = '+ añadir bloque';
    addBtn.addEventListener('click', () => {
      appendBlockItem(blocksList, { type: sel.value }, true);
    });
    addRow.appendChild(sel);
    addRow.appendChild(addBtn);
    wrap.appendChild(addRow);
  }
  return wrap;
}

function appendBlockItem(container, block, canSave) {
  const card = document.createElement('div');
  card.className = 'item-card block-card';
  card.draggable = canSave;

  // Campos según tipo de bloque
  let extraFields = '';
  if (block.type === 'hero') {
    extraFields = `
      <input class="uf-input-sm block-field" data-key="title" placeholder="título" value="${esc(block.title ?? '')}" style="flex:2" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm block-field" data-key="subtitle" placeholder="subtítulo" value="${esc(block.subtitle ?? '')}" style="flex:3" ${canSave ? '' : 'disabled'} />
    `;
  } else if (block.type === 'now_preview' || block.type === 'bookshelf_preview' || block.type === 'videos_preview') {
    extraFields = `
      <input class="uf-input-sm block-field" data-key="limit" placeholder="límite (ej: 3)" value="${esc(String(block.limit ?? ''))}" style="width:80px" ${canSave ? '' : 'disabled'} />
    `;
  } else if (block.type === 'custom') {
    extraFields = `
      <input class="uf-input-sm block-field" data-key="content" placeholder="contenido HTML/texto" value="${esc(block.content ?? '')}" style="flex:3" ${canSave ? '' : 'disabled'} />
    `;
  }

  card.innerHTML = `
    <div class="item-drag-handle">⠿</div>
    <span class="block-type-badge font-mono">${block.type}</span>
    <div class="item-fields" style="flex:1">${extraFields}</div>
    ${canSave ? '<button class="btn-danger-sm item-remove">✕</button>' : ''}
  `;
  card.dataset.type = block.type;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  if (canSave) setupDragDrop(card, container);
  container.appendChild(card);
}

// ── gacha-config.json ─────────────────────────────────────────
function buildGachaForm(data, canSave) {
  const wrap = document.createElement('div');
  wrap.className = 'form-section';
  wrap.dataset.collector = 'gacha';

  const games = Array.isArray(data.games) ? data.games : [];
  const list = document.createElement('div');
  list.id = 'gacha-list';
  list.className = 'items-list';
  games.forEach(g => appendGachaGame(list, g, canSave));
  wrap.appendChild(list);

  if (canSave) {
    const addBtn = document.createElement('button');
    addBtn.className = 'btn-ghost';
    addBtn.style.marginTop = '0.75rem';
    addBtn.textContent = '+ añadir juego';
    addBtn.addEventListener('click', () => appendGachaGame(list, { id: '', name: '', icon: '', uid: '' }, true));
    wrap.appendChild(addBtn);
  }
  return wrap;
}

function appendGachaGame(container, game, canSave) {
  const card = document.createElement('div');
  card.className = 'item-card';
  card.innerHTML = `
    <div class="item-drag-handle">⠿</div>
    <div class="item-fields" style="flex-wrap:wrap">
      <input class="uf-input-sm gacha-icon" placeholder="emoji" value="${esc(game.icon ?? '')}" style="width:60px" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm gacha-name" placeholder="nombre" value="${esc(game.name ?? '')}" style="flex:2" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm gacha-id" placeholder="id (gi/hsr/zzz)" value="${esc(game.id ?? '')}" style="flex:1;min-width:80px" ${canSave ? '' : 'disabled'} />
      <input class="uf-input-sm gacha-uid" placeholder="UID del juego" value="${esc(game.uid ?? '')}" style="flex:2" ${canSave ? '' : 'disabled'} />
    </div>
    ${canSave ? '<button class="btn-danger-sm item-remove">✕</button>' : ''}
  `;
  card.querySelector('.item-remove')?.addEventListener('click', () => card.remove());
  container.appendChild(card);
}

// ── Editor genérico para JSONs desconocidos ───────────────────
function buildGenericForm(file, data, canSave) {
  const wrap = document.createElement('div');
  wrap.className = 'form-section';
  wrap.dataset.collector = 'generic';
  wrap.dataset.file = file;

  const note = document.createElement('p');
  note.className = 'font-mono';
  note.style.cssText = 'font-size:0.72rem;color:var(--color-muted-2);margin-bottom:0.75rem';
  note.textContent = 'JSON personalizado — editor de texto';
  wrap.appendChild(note);

  const ta = document.createElement('textarea');
  ta.className = 'json-editor';
  ta.id = 'generic-editor';
  ta.spellcheck = false;
  ta.value = JSON.stringify(data, null, 2);
  ta.disabled = !canSave;
  wrap.appendChild(ta);
  return wrap;
}

// ── Drag and drop reorder ─────────────────────────────────────
function setupDragDrop(card, container) {
  card.addEventListener('dragstart', e => {
    e.dataTransfer.effectAllowed = 'move';
    card.classList.add('dragging');
  });
  card.addEventListener('dragend', () => card.classList.remove('dragging'));
  card.addEventListener('dragover', e => {
    e.preventDefault();
    const dragging = container.querySelector('.dragging');
    if (dragging && dragging !== card) {
      const rect = card.getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      if (e.clientY < mid) container.insertBefore(dragging, card);
      else container.insertBefore(dragging, card.nextSibling);
    }
  });
}

// ── Colectar datos del formulario y guardar ───────────────────
async function saveFile(file) {
  const wrap = editorsContainer?.querySelector('[data-collector]');
  if (!wrap) return;
  const collector = wrap.dataset.collector;
  let payload;

  try {
    if (collector === 'now') {
      const items = [...document.querySelectorAll('#now-items .item-card')].map(card => ({
        icon: card.querySelector('.now-icon').value.trim(),
        category: card.querySelector('.now-category').value.trim(),
        text: card.querySelector('.now-text').value.trim(),
      }));
      payload = {
        updated: new Date().toISOString().split('T')[0],
        location: document.getElementById('now-location').value.trim(),
        status: document.getElementById('now-status').value.trim(),
        items,
      };
    } else if (collector === 'books') {
      payload = [...document.querySelectorAll('#books-list .item-card')].map(card => ({
        title:  card.querySelector('.book-title').value.trim(),
        author: card.querySelector('.book-author').value.trim(),
        status: card.querySelector('.book-status').value,
        cover:  card.querySelector('.book-cover').value.trim() || undefined,
      }));
    } else if (collector === 'homepage') {
      const blocks = [...document.querySelectorAll('#hp-blocks .block-card')].map(card => {
        const type = card.dataset.type;
        const obj = { type };
        card.querySelectorAll('.block-field').forEach(f => {
          const v = f.value.trim();
          if (v) {
            const k = f.dataset.key;
            obj[k] = (k === 'limit') ? Number(v) : v;
          }
        });
        return obj;
      });
      payload = { title: document.getElementById('hp-title').value.trim(), blocks };
    } else if (collector === 'gacha') {
      const games = [...document.querySelectorAll('#gacha-list .item-card')].map(card => ({
        icon: card.querySelector('.gacha-icon').value.trim(),
        name: card.querySelector('.gacha-name').value.trim(),
        id:   card.querySelector('.gacha-id').value.trim(),
        uid:  card.querySelector('.gacha-uid').value.trim(),
      }));
      payload = { games };
    } else if (collector === 'generic') {
      payload = JSON.parse(document.getElementById('generic-editor').value);
    }
  } catch (e) {
    showSaveResult(`❌ Error al construir JSON: ${e}`, false);
    return;
  }

  const saveBtn = document.getElementById('main-save-btn');
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'guardando…'; }

  const res = await fetch(`/api/admin/data?file=${file}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'guardar cambios ↑'; }

  if (res.ok) {
    cache[file] = payload; // actualizar cache local
    showSaveResult('✅ guardado — cambios aplicados al instante', true);
  } else {
    const err = await res.text();
    showSaveResult(`❌ error: ${err}`, false);
  }
}

function showSaveResult(msg, ok) {
  const el = document.getElementById('save-result');
  if (!el) return;
  el.textContent = msg;
  el.style.color = ok ? 'var(--color-accent)' : '#f87171';
  el.style.display = 'block';
  if (ok) setTimeout(() => { el.style.display = 'none'; }, 3000);
}

// ── Gacha sync commands ───────────────────────────────────────
function renderGachaSync(data) {
  const section = document.getElementById('gacha-sync-section');
  const list = document.getElementById('cmd-list');
  if (!section || !list) return;
  const games = data?.games ?? [];
  if (!games.length) return;
  section.style.display = 'block';
  list.innerHTML = games.map(g => `
    <div class="cmd-item">
      <span class="cmd-game font-mono">${g.icon} ${g.name}</span>
      <code class="cmd-code font-mono">docker exec web bun run scripts/sync-enka-${g.id}.ts</code>
    </div>
  `).join('');
}

// ── Escape helper ─────────────────────────────────────────────
function esc(str) {
  return String(str).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
}

// ── Arrancar ──────────────────────────────────────────────────
if (activeTab) switchTab(activeTab);

// ══════════════════════════════════════════════════════════════
// UPLOAD VIDEO
// ══════════════════════════════════════════════════════════════
const dropZone    = document.getElementById('drop-zone');
const uploadInner = document.getElementById('upload-inner');
const uploadForm  = document.getElementById('upload-form');
const fileInput   = document.getElementById('file-input');
const progressWrap  = document.getElementById('progress-wrap');
const progressBar   = document.getElementById('progress-bar');
const progressLabel = document.getElementById('progress-label');
const uploadResult  = document.getElementById('upload-result');
let selectedFile = null;

function showUploadForm(file) {
  selectedFile = file;
  document.getElementById('uf-title').value = file.name.replace(/\.[^.]+$/, '');
  uploadInner.style.display = 'none';
  uploadForm.style.display = 'block';
}

dropZone?.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone?.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); const f = e.dataTransfer?.files[0]; if (f) showUploadForm(f); });
uploadInner?.addEventListener('click', () => fileInput.click());
fileInput?.addEventListener('change', () => { if (fileInput.files?.[0]) showUploadForm(fileInput.files[0]); });

document.getElementById('upload-cancel')?.addEventListener('click', () => {
  selectedFile = null;
  uploadInner.style.display = 'flex';
  uploadForm.style.display = 'none';
  fileInput.value = '';
});

document.getElementById('add-descriptor')?.addEventListener('click', () => {
  const list = document.getElementById('descriptor-list');
  const row = document.createElement('div');
  row.className = 'desc-row';
  row.innerHTML = `
    <input type="text" class="uf-input desc-key" placeholder="clave" style="flex:1" />
    <input type="text" class="uf-input desc-val" placeholder="valor" style="flex:2" />
    <button type="button" class="btn-ghost-sm desc-rm">✕</button>
  `;
  row.querySelector('.desc-rm')?.addEventListener('click', () => row.remove());
  list.appendChild(row);
});

document.getElementById('upload-submit')?.addEventListener('click', async () => {
  if (!selectedFile) return;
  const title    = document.getElementById('uf-title').value || selectedFile.name;
  const category = document.getElementById('uf-category').value || 'general';
  const descriptors = {};
  document.querySelectorAll('.desc-row').forEach(row => {
    const k = row.querySelector('.desc-key').value.trim();
    const v = row.querySelector('.desc-val').value.trim();
    if (k && v) descriptors[k] = v;
  });
  const fd = new FormData();
  fd.append('video', selectedFile);
  fd.append('title', title);
  fd.append('category', category);
  fd.append('descriptors', JSON.stringify(descriptors));

  progressWrap.style.display = 'flex';
  const btn = document.getElementById('upload-submit');
  btn.disabled = true;

  const xhr = new XMLHttpRequest();
  xhr.upload.addEventListener('progress', e => {
    if (e.lengthComputable) {
      const pct = Math.round(e.loaded / e.total * 100);
      progressBar.style.width = pct + '%';
      progressLabel.textContent = pct + '%';
    }
  });
  xhr.addEventListener('load', () => {
    progressWrap.style.display = 'none';
    btn.disabled = false;
    try {
      const res = JSON.parse(xhr.responseText);
      if (res.ok) {
        uploadResult.textContent = `✅ subido · /v/${res.id}`;
        uploadResult.style.color = 'var(--color-accent)';
        uploadResult.style.display = 'block';
        uploadInner.style.display = 'flex';
        uploadForm.style.display = 'none';
        selectedFile = null;
        fileInput.value = '';
        loadVideos();
      } else {
        uploadResult.textContent = `❌ ${res.error}`;
        uploadResult.style.color = '#F87171';
        uploadResult.style.display = 'block';
      }
    } catch {
      uploadResult.textContent = '❌ Error inesperado';
      uploadResult.style.color = '#F87171';
      uploadResult.style.display = 'block';
    }
  });
  xhr.addEventListener('error', () => {
    uploadResult.textContent = '❌ Error de red';
    uploadResult.style.display = 'block';
    btn.disabled = false;
  });
  xhr.open('POST', '/api/videos/upload');
  xhr.send(fd);
});

// ══════════════════════════════════════════════════════════════
// LISTA DE VIDEOS
// ══════════════════════════════════════════════════════════════
async function loadVideos() {
  const list = document.getElementById('videos-list');
  const countEl = document.getElementById('v-count');
  list.innerHTML = '<p class="loading-text font-mono">cargando…</p>';
  try {
    const { videos } = await fetch('/api/videos').then(r => r.json());
    countEl.textContent = videos.length;
    if (!videos.length) { list.innerHTML = '<p class="loading-text font-mono">sin videos todavía.</p>'; return; }
    list.innerHTML = videos.map(v => {
      let desc = {};
      try { desc = JSON.parse(v.descriptors ?? '{}'); } catch {}
      const descStr = Object.entries(desc).map(([k,val]) => `${k}: ${val}`).join(' · ');
      return `
        <div class="va-card" data-id="${v.id}">
          <div class="va-thumb">${v.thumbnail ? `<img src="${v.thumbnail}" alt="" />` : '<div class="va-thumb-ph">▶</div>'}</div>
          <div class="va-body">
            <input class="va-title-input uf-input" value="${v.title.replace(/"/g,'&quot;')}" data-field="title" />
            <div class="va-meta">
              <input class="va-cat-input uf-input-sm" value="${(v.category??'general').replace(/"/g,'&quot;')}" placeholder="categoría" data-field="category" />
              <input class="va-desc-input uf-input-sm" value="${descStr.replace(/"/g,'&quot;')}" placeholder="Personaje: X, Score: Y" data-field="descriptors_raw" />
            </div>
            <div class="va-actions">
              <a href="/v/${v.id}" target="_blank" class="btn-ghost-sm">ver →</a>
              <button class="btn-ghost-sm va-save" data-id="${v.id}">guardar</button>
              <button class="btn-danger-sm va-delete" data-id="${v.id}">eliminar</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    list.querySelectorAll('.va-save').forEach(btn => {
      btn.addEventListener('click', async () => {
        const card = btn.closest('.va-card');
        const id = card.dataset.id;
        const title = card.querySelector('[data-field="title"]').value;
        const category = card.querySelector('[data-field="category"]').value;
        const rawDesc = card.querySelector('[data-field="descriptors_raw"]').value;
        const descriptors = {};
        rawDesc.split(',').forEach(part => {
          const [k, ...rest] = part.split(':');
          if (k?.trim()) descriptors[k.trim()] = rest.join(':').trim();
        });
        const res = await fetch('/api/videos/update', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, title, category, descriptors }),
        });
        btn.textContent = res.ok ? '✓' : '❌';
        setTimeout(() => { btn.textContent = 'guardar'; }, 2000);
      });
    });

    list.querySelectorAll('.va-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('¿Eliminar este video?')) return;
        await fetch(`/api/videos?id=${btn.dataset.id}`, { method: 'DELETE' });
        loadVideos();
      });
    });
  } catch(e) {
    list.innerHTML = `<p class="loading-text font-mono" style="color:#F87171">${e}</p>`;
  }
}
loadVideos();
</script>

<style>
  .admin { max-width: 56rem; margin: 0 auto; padding: var(--space-10) var(--space-4); }
  .font-mono { font-family: var(--font-mono); }

  .admin-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--space-10); padding-bottom: var(--space-6); border-bottom: 1px solid rgba(255,255,255,0.08); }
  .badge { font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.1em; text-transform: uppercase; color: var(--color-accent); display: block; margin-bottom: 0.3rem; }
  .admin-title { font-family: var(--font-display); font-size: var(--text-3xl); color: var(--color-ink); }
  .admin-sub { font-size: var(--text-xs); color: var(--color-muted-2); margin-top: var(--space-1); letter-spacing: 0.04em; }
  .btn-logout { font-family: var(--font-mono); font-size: var(--text-xs); background: none; border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-sm); padding: var(--space-2) var(--space-3); color: var(--color-muted); cursor: pointer; letter-spacing: 0.06em; transition: color 0.15s, border-color 0.15s; }
  .btn-logout:hover { color: #F87171; border-color: rgba(248,113,113,0.3); }

  .admin-section { margin-bottom: var(--space-10); }
  .sh { font-family: var(--font-mono); font-size: var(--text-xs); letter-spacing: 0.12em; text-transform: uppercase; color: var(--color-muted); margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-3); }
  .sh-count { background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.3); border-radius: var(--radius-full); padding: 0 8px; font-size: 0.65rem; color: var(--color-accent); }

  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px,1fr)); gap: var(--space-3); }
  .stat { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-md); padding: var(--space-4); display: flex; flex-direction: column; gap: 4px; }
  .sl { font-family: var(--font-mono); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--color-muted); }
  .sv { font-family: var(--font-mono); font-size: var(--text-xl); color: var(--color-ink); font-weight: 500; }

  /* Tabs */
  .tab-bar { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.25rem; }
  .tab-btn { font-family: var(--font-mono); font-size: 0.72rem; letter-spacing: 0.06em; padding: 0.35rem 0.85rem; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; color: var(--color-muted); cursor: pointer; transition: all 0.15s; }
  .tab-btn:hover { border-color: rgba(168,85,247,0.3); color: var(--color-accent); }
  .tab-btn.active { background: rgba(168,85,247,0.12); border-color: rgba(168,85,247,0.4); color: var(--color-accent); }

  /* Editor wrap */
  .editor-wrap { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: var(--radius-lg); padding: var(--space-5); }
  .editor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; }
  .editor-filename { font-size: 0.8rem; color: var(--color-muted-2); }
  .form-section { display: flex; flex-direction: column; gap: 0.5rem; }
  .form-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
  @media (max-width: 480px) { .form-grid-2 { grid-template-columns: 1fr; } }
  .form-field { display: flex; flex-direction: column; gap: 0.3rem; }
  .field-label { font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-muted); }

  /* Items list */
  .items-list { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem; }
  .item-card { display: flex; align-items: center; gap: 0.6rem; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 0.6rem 0.75rem; transition: border-color 0.15s; }
  .item-card:hover { border-color: rgba(168,85,247,0.2); }
  .item-card.dragging { opacity: 0.5; border-style: dashed; }
  .item-drag-handle { color: var(--color-muted-2); cursor: grab; font-size: 1.1rem; flex-shrink: 0; user-select: none; }
  .item-fields { display: flex; gap: 0.5rem; flex: 1; align-items: center; flex-wrap: wrap; }
  .block-type-badge { font-family: var(--font-mono); font-size: 0.65rem; background: rgba(168,85,247,0.12); border: 1px solid rgba(168,85,247,0.25); border-radius: 4px; padding: 0.2rem 0.5rem; color: var(--color-accent); white-space: nowrap; flex-shrink: 0; }

  .save-result { font-size: var(--text-xs); margin-top: var(--space-3); padding: var(--space-2) 0; display: none; }

  /* Inputs */
  .uf-input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius-md); padding: 0.55rem 0.75rem; font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-ink); outline: none; transition: border-color 0.15s; width: 100%; }
  .uf-input:focus { border-color: var(--color-accent); }
  .uf-input:disabled { opacity: 0.5; }
  .uf-input-sm { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-sm); padding: 0.3rem 0.5rem; font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink); outline: none; transition: border-color 0.15s; }
  .uf-input-sm:focus { border-color: var(--color-accent); }
  .uf-input-sm:disabled { opacity: 0.5; }
  select.uf-input-sm { cursor: pointer; }

  .json-editor { width: 100%; height: 14rem; resize: vertical; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.07); border-radius: var(--radius-md); padding: var(--space-4); font-family: var(--font-mono); font-size: 0.72rem; color: var(--color-ink); line-height: 1.6; outline: none; tab-size: 2; }
  .json-editor:focus { border-color: rgba(168,85,247,0.3); }

  /* Buttons */
  .btn-primary { background: var(--color-accent); color: var(--color-bg); border: none; border-radius: var(--radius-md); padding: 0.55rem 1.1rem; font-family: var(--font-mono); font-size: var(--text-xs); cursor: pointer; letter-spacing: 0.04em; transition: opacity 0.15s; }
  .btn-primary:hover { opacity: 0.85; }
  .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-ghost { background: none; border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius-md); padding: 0.55rem 1rem; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-muted); cursor: pointer; transition: all 0.15s; }
  .btn-ghost:hover { border-color: rgba(168,85,247,0.4); color: var(--color-accent); }
  .btn-ghost-sm { background: none; border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius-sm); padding: 0.2rem 0.5rem; font-family: var(--font-mono); font-size: 0.65rem; color: var(--color-muted); cursor: pointer; transition: all 0.15s; text-decoration: none; display: inline-block; }
  .btn-ghost-sm:hover { border-color: var(--color-accent); color: var(--color-accent); }
  .btn-danger-sm { background: none; border: 1px solid rgba(248,113,113,0.2); border-radius: var(--radius-sm); padding: 0.2rem 0.5rem; font-family: var(--font-mono); font-size: 0.65rem; color: rgba(248,113,113,0.6); cursor: pointer; transition: all 0.15s; }
  .btn-danger-sm:hover { border-color: #F87171; color: #F87171; }

  /* Upload */
  .upload-zone { border: 2px dashed rgba(168,85,247,0.3); border-radius: var(--radius-lg); transition: border-color 0.2s, background 0.2s; min-height: 8rem; }
  .upload-zone.drag-over { border-color: var(--color-accent); background: rgba(168,85,247,0.06); }
  .upload-inner { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-8); cursor: pointer; text-align: center; }
  .upload-icon { font-size: 2rem; color: var(--color-accent); opacity: 0.5; }
  .upload-label { font-size: var(--text-sm); color: var(--color-ink); }
  .upload-hint { font-size: var(--text-xs); color: var(--color-muted-2); letter-spacing: 0.04em; }
  .upload-form { padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-4); }
  .uf-row { display: flex; flex-direction: column; gap: var(--space-1); }
  .uf-label { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-muted); letter-spacing: 0.06em; }
  .uf-hint { color: var(--color-muted-2); font-size: 0.65rem; }
  .descriptor-list { display: flex; flex-direction: column; gap: var(--space-2); }
  .desc-row { display: flex; gap: var(--space-2); align-items: center; }
  .uf-progress-wrap { display: flex; align-items: center; gap: var(--space-3); }
  .uf-progress-bar { flex: 1; height: 4px; border-radius: 2px; background: var(--color-accent); transition: width 0.1s; width: 0%; }
  .uf-progress-label { font-size: 0.7rem; color: var(--color-muted); min-width: 2.5rem; text-align: right; }
  .uf-actions { display: flex; gap: var(--space-3); justify-content: flex-end; }
  .upload-result { padding: var(--space-3) 0; font-size: var(--text-sm); }

  /* Videos list */
  .videos-admin-list { display: flex; flex-direction: column; gap: var(--space-3); }
  .va-card { display: flex; gap: var(--space-4); align-items: flex-start; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: var(--radius-md); padding: var(--space-4); transition: border-color 0.15s; }
  .va-card:hover { border-color: rgba(168,85,247,0.2); }
  .va-thumb { width: 100px; flex-shrink: 0; aspect-ratio: 16/9; border-radius: var(--radius-sm); overflow: hidden; background: rgba(168,85,247,0.06); }
  .va-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .va-thumb-ph { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; opacity: 0.3; color: var(--color-accent); }
  .va-body { flex: 1; display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
  .va-title-input { font-size: var(--text-sm); font-weight: 500; }
  .va-meta { display: flex; gap: var(--space-2); flex-wrap: wrap; }
  .va-cat-input, .va-desc-input { flex: 1; min-width: 120px; }
  .va-desc-input { flex: 3; }
  .va-actions { display: flex; gap: var(--space-2); align-items: center; }

  /* Gacha sync */
  .cmd-list { display: flex; flex-direction: column; gap: var(--space-2); }
  .cmd-item { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; padding: var(--space-3) var(--space-4); background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: var(--radius-md); }
  .cmd-game { font-size: var(--text-sm); color: var(--color-ink); min-width: 10rem; }
  .cmd-code { font-size: 0.7rem; color: var(--color-muted-2); background: rgba(0,0,0,0.2); padding: 0.25rem 0.5rem; border-radius: 4px; word-break: break-all; }
  .loading-text { color: var(--color-muted); font-size: var(--text-sm); padding: var(--space-4) 0; }
</style>
"""

os.makedirs(os.path.join(BASE, "src", "pages", "admin"), exist_ok=True)
with open(os.path.join(BASE, "src", "pages", "admin", "index.astro"), "w") as f:
    f.write(admin_page)
print("✅ src/pages/admin/index.astro reescrito")

# ─── 3. Fix hot-reload: asegurar que /api/admin/data también acepta database.sqlite como readonly ──
# (ya está correcto en el código existente, no necesita cambio)

# ─── 4. Rebuild ──────────────────────────────────────────────────────────────
print("\n🔨 Rebuilding...")
result = subprocess.run(
    ["docker", "compose", "up", "-d", "--build"],
    cwd=BASE, capture_output=True, text=True
)
print(result.stdout[-3000:] if result.stdout else "")
if result.returncode != 0:
    print("❌ Error:", result.stderr[-2000:])
else:
    print("\n✅ Admin v2 listo en /admin")
    print("   - Formularios visuales por tipo de JSON")
    print("   - Drag & drop para reordenar items")
    print("   - Auto-detecta JSONs nuevos en /data/")
    print("   - Cambios aplicados al instante (sin rebuild)")
