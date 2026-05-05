/**
 * md → Kobo EPUB Builder — frontend logic
 */

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  files: [],       // [{ name: string, path: string }]
  coverPath: null,
  coverName: null,
  cssPath: null,
  cssName: null,
};

// ── DOM refs ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const pandocBadge   = $('pandoc-status');
const mdInput       = $('md-file-input');
const zipInput      = $('zip-file-input');
const dropZone      = $('drop-zone');
const chapterList   = $('chapter-list');
const chapterCount  = $('chapter-count');
const importError   = $('import-error');

const metaTitle     = $('meta-title');
const metaAuthor    = $('meta-author');
const metaLanguage  = $('meta-language');
const metaFilename  = $('meta-filename');
const metaToc       = $('meta-toc');

const coverInput    = $('cover-input');
const coverName     = $('cover-name');
const coverClear    = $('cover-clear');
const cssInput      = $('css-input');
const cssName       = $('css-name');
const cssClear      = $('css-clear');

const buildBtn      = $('build-btn');
const buildSpinner  = $('build-spinner');
const buildResult   = $('build-result');
const buildLog      = $('build-log');
const buildOutput   = $('build-output');
const outputFilename= $('output-filename');
const downloadLink  = $('download-link');

const saveBtn       = $('save-btn');
const loadManifestInput = $('load-manifest-input');
const resetBtn      = $('reset-btn');
const projectMsg    = $('project-msg');

// ── Pandoc status ─────────────────────────────────────────────────────────────
async function checkPandoc() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const { installed, version } = data.pandoc;
    pandocBadge.className = `status-badge ${installed ? 'ok' : 'error'}`;
    pandocBadge.querySelector('.status-text').textContent = installed
      ? version
      : 'Pandoc not found — install from pandoc.org';
  } catch {
    pandocBadge.className = 'status-badge error';
    pandocBadge.querySelector('.status-text').textContent = 'Could not check Pandoc';
  }
}

// ── File upload ───────────────────────────────────────────────────────────────
async function uploadMarkdownFiles(fileList) {
  const form = new FormData();
  let count = 0;
  for (const f of fileList) {
    const ext = f.name.split('.').pop().toLowerCase();
    if (ext === 'md' || ext === 'markdown') {
      form.append('files', f);
      count++;
    }
  }
  if (count === 0) { showImportError('No Markdown files found in selection.'); return; }

  showImportError('');
  try {
    const res = await fetch('/api/files/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showImportError(data.error || 'Upload failed.'); return; }
    mergeFiles(data.files);
    renderChapters();
  } catch {
    showImportError('Network error during upload.');
  }
}

async function uploadZip(file) {
  const form = new FormData();
  form.append('file', file);
  showImportError('');
  try {
    const res = await fetch('/api/zip/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showImportError(data.error || 'ZIP import failed.'); return; }

    // Replace file list with ZIP contents
    state.files = data.files || [];

    // Apply cover
    if (data.cover) {
      state.coverPath = data.cover.path;
      state.coverName = data.cover.name;
    }
    // Apply CSS
    if (data.css) {
      state.cssPath = data.css.path;
      state.cssName = data.css.name;
    }
    // Apply manifest metadata
    if (data.manifest) {
      applyManifestToUI(data.manifest);
    }

    renderChapters();
    renderAssets();
  } catch {
    showImportError('Network error during ZIP import.');
  }
}

function mergeFiles(incoming) {
  // Add only new files (by path)
  const existing = new Set(state.files.map(f => f.path));
  for (const f of incoming) {
    if (!existing.has(f.path)) {
      state.files.push(f);
      existing.add(f.path);
    }
  }
}

// ── Cover upload ──────────────────────────────────────────────────────────────
async function uploadCover(file) {
  const form = new FormData();
  form.append('file', file);
  try {
    const res = await fetch('/api/assets/cover', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showImportError(data.error || 'Cover upload failed.'); return; }
    state.coverPath = data.path;
    state.coverName = data.name;
    renderAssets();
  } catch {
    showImportError('Network error uploading cover.');
  }
}

// ── CSS upload ────────────────────────────────────────────────────────────────
async function uploadCss(file) {
  const form = new FormData();
  form.append('file', file);
  try {
    const res = await fetch('/api/assets/css', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showImportError(data.error || 'CSS upload failed.'); return; }
    state.cssPath = data.path;
    state.cssName = data.name;
    renderAssets();
  } catch {
    showImportError('Network error uploading CSS.');
  }
}

// ── Chapter list render ───────────────────────────────────────────────────────
function renderChapters() {
  chapterList.innerHTML = '';
  chapterCount.textContent = state.files.length;

  if (state.files.length === 0) {
    const li = document.createElement('li');
    li.className = 'empty-hint';
    li.textContent = 'No files loaded. Import Markdown files or a ZIP project above.';
    chapterList.appendChild(li);
    return;
  }

  state.files.forEach((file, idx) => {
    const li = document.createElement('li');
    li.className = 'chapter-item';
    li.dataset.index = idx;
    li.draggable = true;

    li.innerHTML = `
      <span class="drag-handle" title="Drag to reorder">⠿</span>
      <span class="chapter-name" title="${escHtml(file.path)}">${escHtml(file.name)}</span>
      <span class="chapter-order">${idx + 1}</span>
      <div class="chapter-actions">
        <button class="up-btn" title="Move up" ${idx === 0 ? 'disabled' : ''}>↑</button>
        <button class="dn-btn" title="Move down" ${idx === state.files.length - 1 ? 'disabled' : ''}>↓</button>
        <button class="remove-btn" title="Remove">✕</button>
      </div>
    `;

    li.querySelector('.up-btn').addEventListener('click', () => moveChapter(idx, -1));
    li.querySelector('.dn-btn').addEventListener('click', () => moveChapter(idx, +1));
    li.querySelector('.remove-btn').addEventListener('click', () => removeChapter(idx));

    chapterList.appendChild(li);
  });

  initDragDrop();
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Chapter ordering ──────────────────────────────────────────────────────────
function moveChapter(idx, delta) {
  const newIdx = idx + delta;
  if (newIdx < 0 || newIdx >= state.files.length) return;
  [state.files[idx], state.files[newIdx]] = [state.files[newIdx], state.files[idx]];
  renderChapters();
}

function removeChapter(idx) {
  state.files.splice(idx, 1);
  renderChapters();
}

$('sort-az').addEventListener('click', () => {
  state.files.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));
  renderChapters();
});

$('sort-natural').addEventListener('click', () => {
  state.files.sort((a, b) => naturalCompare(a.name, b.name));
  renderChapters();
});

function naturalCompare(a, b) {
  const re = /(\d+)|(\D+)/g;
  const partsA = a.match(re) || [];
  const partsB = b.match(re) || [];
  for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
    const pa = partsA[i] || '';
    const pb = partsB[i] || '';
    const na = parseInt(pa, 10);
    const nb = parseInt(pb, 10);
    if (!isNaN(na) && !isNaN(nb)) {
      if (na !== nb) return na - nb;
    } else {
      const cmp = pa.toLowerCase().localeCompare(pb.toLowerCase());
      if (cmp !== 0) return cmp;
    }
  }
  return 0;
}

// ── Drag-and-drop reordering ──────────────────────────────────────────────────
let dragSrcIdx = null;

function initDragDrop() {
  const items = chapterList.querySelectorAll('.chapter-item');

  items.forEach(item => {
    item.addEventListener('dragstart', e => {
      dragSrcIdx = parseInt(item.dataset.index, 10);
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });

    item.addEventListener('dragend', () => {
      item.classList.remove('dragging');
      chapterList.querySelectorAll('.chapter-item').forEach(i => i.classList.remove('drag-target'));
    });

    item.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const targetIdx = parseInt(item.dataset.index, 10);
      if (targetIdx !== dragSrcIdx) {
        chapterList.querySelectorAll('.chapter-item').forEach(i => i.classList.remove('drag-target'));
        item.classList.add('drag-target');
      }
    });

    item.addEventListener('drop', e => {
      e.preventDefault();
      const targetIdx = parseInt(item.dataset.index, 10);
      if (dragSrcIdx === null || dragSrcIdx === targetIdx) return;
      const moved = state.files.splice(dragSrcIdx, 1)[0];
      state.files.splice(targetIdx, 0, moved);
      dragSrcIdx = null;
      renderChapters();
    });
  });
}

// ── Drop zone (file drag from OS) ─────────────────────────────────────────────
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const files = Array.from(e.dataTransfer.files);
  uploadMarkdownFiles(files);
});

// ── File input listeners ──────────────────────────────────────────────────────
mdInput.addEventListener('change', () => {
  if (mdInput.files.length) uploadMarkdownFiles(mdInput.files);
  mdInput.value = '';
});

zipInput.addEventListener('change', () => {
  if (zipInput.files.length) uploadZip(zipInput.files[0]);
  zipInput.value = '';
});

coverInput.addEventListener('change', () => {
  if (coverInput.files.length) uploadCover(coverInput.files[0]);
  coverInput.value = '';
});

cssInput.addEventListener('change', () => {
  if (cssInput.files.length) uploadCss(cssInput.files[0]);
  cssInput.value = '';
});

coverClear.addEventListener('click', () => {
  state.coverPath = null; state.coverName = null;
  renderAssets();
});
cssClear.addEventListener('click', () => {
  state.cssPath = null; state.cssName = null;
  renderAssets();
});

function renderAssets() {
  if (state.coverName) {
    coverName.textContent = state.coverName;
    coverName.classList.remove('muted');
    coverClear.style.display = 'inline-flex';
  } else {
    coverName.textContent = 'None';
    coverName.classList.add('muted');
    coverClear.style.display = 'none';
  }
  if (state.cssName) {
    cssName.textContent = state.cssName;
    cssName.classList.remove('muted');
    cssClear.style.display = 'inline-flex';
  } else {
    cssName.textContent = 'None';
    cssName.classList.add('muted');
    cssClear.style.display = 'none';
  }
}

// ── Build ─────────────────────────────────────────────────────────────────────
buildBtn.addEventListener('click', buildEpub);

async function buildEpub() {
  buildBtn.disabled = true;
  buildSpinner.style.display = 'block';
  buildResult.style.display = 'none';
  buildOutput.style.display = 'none';

  const body = {
    files: state.files.map(f => f.path),
    metadata: {
      title:    metaTitle.value.trim(),
      author:   metaAuthor.value.trim(),
      language: metaLanguage.value.trim() || 'en-US',
      toc:      metaToc.checked,
    },
    cover_path:      state.coverPath,
    css_path:        state.cssPath,
    output_filename: metaFilename.value.trim() || 'book.epub',
  };

  try {
    const res = await fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    buildSpinner.style.display = 'none';
    buildResult.style.display = 'block';
    buildLog.textContent = data.log || '';
    buildLog.className = `build-log ${data.success ? 'success' : 'failure'}`;

    if (data.success) {
      buildOutput.style.display = 'flex';
      outputFilename.textContent = data.output_filename;
      downloadLink.href = `/api/output/${encodeURIComponent(data.output_filename)}`;
    }
  } catch {
    buildSpinner.style.display = 'none';
    buildResult.style.display = 'block';
    buildLog.textContent = 'Network error during build.';
    buildLog.className = 'build-log failure';
  }

  buildBtn.disabled = false;
}

// ── Save project ──────────────────────────────────────────────────────────────
saveBtn.addEventListener('click', async () => {
  const manifest = buildManifest();
  try {
    const res = await fetch('/api/manifest/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manifest }),
    });
    const data = await res.json();
    showProjectMsg(data.success ? `Project saved to ${data.path}` : (data.error || 'Save failed.'), data.success ? 'success' : 'error');
  } catch {
    showProjectMsg('Network error while saving.', 'error');
  }
});

// ── Load project ──────────────────────────────────────────────────────────────
loadManifestInput.addEventListener('change', async () => {
  if (!loadManifestInput.files.length) return;
  const form = new FormData();
  form.append('file', loadManifestInput.files[0]);
  loadManifestInput.value = '';
  try {
    const res = await fetch('/api/manifest/load', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) { showProjectMsg(data.error || 'Load failed.', 'error'); return; }
    applyManifestToUI(data.manifest);
    showProjectMsg('Project loaded.', 'success');
  } catch {
    showProjectMsg('Network error while loading.', 'error');
  }
});

function buildManifest() {
  return {
    title:           metaTitle.value.trim(),
    author:          metaAuthor.value.trim(),
    language:        metaLanguage.value.trim() || 'en-US',
    toc:             metaToc.checked,
    cover_image:     state.coverName || null,
    css:             state.cssName || null,
    output_filename: metaFilename.value.trim() || 'book.epub',
    files:           state.files.map(f => f.name),
  };
}

function applyManifestToUI(manifest) {
  if (!manifest) return;
  if (manifest.title    !== undefined) metaTitle.value    = manifest.title;
  if (manifest.author   !== undefined) metaAuthor.value   = manifest.author;
  if (manifest.language !== undefined) metaLanguage.value = manifest.language;
  if (manifest.toc      !== undefined) metaToc.checked    = !!manifest.toc;
  if (manifest.output_filename)        metaFilename.value = manifest.output_filename;
  // Note: file paths in the manifest are just names; the actual paths are already
  // set from the ZIP import (state.files is already ordered by the caller).
  renderChapters();
}

// ── Reset ─────────────────────────────────────────────────────────────────────
resetBtn.addEventListener('click', async () => {
  if (!confirm('Reset workspace? This clears all uploaded files and current settings.')) return;

  state.files      = [];
  state.coverPath  = null;
  state.coverName  = null;
  state.cssPath    = null;
  state.cssName    = null;

  metaTitle.value    = '';
  metaAuthor.value   = '';
  metaLanguage.value = 'en-US';
  metaFilename.value = 'book.epub';
  metaToc.checked    = true;

  renderChapters();
  renderAssets();
  buildResult.style.display  = 'none';
  buildOutput.style.display  = 'none';
  importError.style.display  = 'none';
  showProjectMsg('', '');

  try {
    await fetch('/api/workspace/clear', { method: 'POST' });
  } catch { /* best-effort */ }
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function showImportError(msg) {
  if (msg) {
    importError.textContent = msg;
    importError.style.display = 'block';
  } else {
    importError.style.display = 'none';
  }
}

function showProjectMsg(msg, type) {
  if (!msg) { projectMsg.style.display = 'none'; return; }
  projectMsg.textContent = msg;
  projectMsg.className = `alert alert-${type}`;
  projectMsg.style.display = 'block';
  setTimeout(() => { projectMsg.style.display = 'none'; }, 4000);
}

// ── Init ──────────────────────────────────────────────────────────────────────
checkPandoc();
renderChapters();
renderAssets();
