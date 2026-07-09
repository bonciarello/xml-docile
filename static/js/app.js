/**
 * XML Docile — Frontend logic
 * Drag-and-drop, validazione, visualizzazione risultati
 */

(function () {
  'use strict';

  // ── DOM refs ───────────────────────────────────────────────────────────
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const xmlInput = document.getElementById('xml-input');
  const dtdInput = document.getElementById('dtd-input');
  const charCount = document.getElementById('char-count');
  const btnValidate = document.getElementById('btn-validate');
  const btnClear = document.getElementById('btn-clear');
  const btnSample = document.getElementById('btn-sample');
  const resultsPanel = document.getElementById('results-panel');
  const statusArea = document.getElementById('status-area');
  const errorsSection = document.getElementById('errors-section');
  const errorList = document.getElementById('error-list');
  const warningsSection = document.getElementById('warnings-section');
  const warningList = document.getElementById('warning-list');
  const structureSection = document.getElementById('structure-section');
  const structureTree = document.getElementById('structure-tree');
  const structureStats = document.getElementById('structure-stats');

  // ── Sample XML ────────────────────────────────────────────────────────
  const SAMPLE_XML = `<?xml version="1.0" encoding="UTF-8"?>
<libri>
  <libro id="1">
    <titolo>Il nome della rosa</titolo>
    <autore>Umberto Eco</autore>
    <anno>1980</anno>
    <editore>Bompiani</editore>
  </libro>
  <libro id="2">
    <titolo>Se questo è un uomo</titolo>
    <autore>Primo Levi</autore>
    <anno>1947</anno>
  </libro>
</libri>`;

  const SAMPLE_DTD = `<!ELEMENT libri (libro+)>
<!ELEMENT libro (titolo, autore, anno, editore?)>
<!ELEMENT titolo (#PCDATA)>
<!ELEMENT autore (#PCDATA)>
<!ELEMENT anno (#PCDATA)>
<!ELEMENT editore (#PCDATA)>
<!ATTLIST libro id CDATA #REQUIRED>`;

  // ── Character count ───────────────────────────────────────────────────
  function updateCharCount() {
    const len = xmlInput.value.length;
    charCount.textContent = len === 1 ? '1 carattere' : len + ' caratteri';
  }

  xmlInput.addEventListener('input', updateCharCount);

  // ── Drag & drop ───────────────────────────────────────────────────────
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evtName => {
    dropZone.addEventListener(evtName, preventDefaults, false);
    document.body.addEventListener(evtName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(evtName => {
    dropZone.addEventListener(evtName, () => dropZone.classList.add('drag-over'), false);
  });

  ['dragleave', 'drop'].forEach(evtName => {
    dropZone.addEventListener(evtName, () => dropZone.classList.remove('drag-over'), false);
  });

  dropZone.addEventListener('drop', handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      readFile(files[0]);
    }
  }

  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      readFile(fileInput.files[0]);
      fileInput.value = '';
    }
  });

  function readFile(file) {
    if (!file.name.toLowerCase().endsWith('.xml') && 
        !file.name.toLowerCase().endsWith('.txt') &&
        !file.name.toLowerCase().endsWith('.dtd')) {
      const ext = file.name.split('.').pop();
      if (!['xml', 'txt', 'dtd'].includes(ext.toLowerCase())) {
        // Still try to read it
      }
    }
    const reader = new FileReader();
    reader.onload = function (e) {
      const content = e.target.result;
      if (file.name.toLowerCase().endsWith('.dtd')) {
        dtdInput.value = content;
        // Open DTD section
        const dtdSection = document.getElementById('dtd-section');
        if (dtdSection) dtdSection.open = true;
      } else {
        xmlInput.value = content;
        updateCharCount();
      }
    };
    reader.onerror = function () {
      showToast('Impossibile leggere il file. Riprova con un altro file.');
    };
    reader.readAsText(file);
  }

  // ── Clear ─────────────────────────────────────────────────────────────
  btnClear.addEventListener('click', () => {
    xmlInput.value = '';
    dtdInput.value = '';
    updateCharCount();
    resultsPanel.hidden = true;
    errorsSection.hidden = true;
    warningsSection.hidden = true;
    structureSection.hidden = true;
    btnValidate.disabled = false;
    btnValidate.querySelector('.btn-label') && (btnValidate.querySelector('.btn-label').textContent = 'Valida');
  });

  // ── Sample ────────────────────────────────────────────────────────────
  btnSample.addEventListener('click', () => {
    xmlInput.value = SAMPLE_XML;
    dtdInput.value = SAMPLE_DTD;
    updateCharCount();
    const dtdSection = document.getElementById('dtd-section');
    if (dtdSection) dtdSection.open = true;
  });

  // ── Validate ──────────────────────────────────────────────────────────
  btnValidate.addEventListener('click', performValidation);

  // Also validate on Ctrl+Enter / Cmd+Enter
  xmlInput.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      performValidation();
    }
  });

  async function performValidation() {
    const xml = xmlInput.value;
    if (!xml.trim()) {
      showResults({
        is_valid: false,
        is_well_formed: false,
        is_structurally_valid: false,
        is_dtd_valid: null,
        errors: [{
          type: 'input',
          line: 0,
          column: 0,
          title: 'Nessun testo XML inserito',
          message: 'Non hai ancora inserito alcun testo XML da validare. Incolla il tuo XML o trascina un file.',
          suggestion: 'Copia e incolla il tuo documento XML nell\'area di testo oppure trascina un file .xml.',
        }],
        warnings: [],
        structure: null,
        stats: {},
      });
      return;
    }

    // Loading state
    btnValidate.disabled = true;
    const originalHTML = btnValidate.innerHTML;
    btnValidate.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="spin">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"/>
      </svg>
      Validazione in corso...
    `;

    // Add spin animation inline
    const spinEl = btnValidate.querySelector('.spin');
    if (spinEl) {
      spinEl.style.animation = 'spin 0.8s linear infinite';
    }

    try {
      const payload = { xml: xml };
      if (dtdInput.value.trim()) {
        payload.dtd = dtdInput.value;
      }

      const response = await fetch('api/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Errore del server: ' + response.status);
      }

      const result = await response.json();
      showResults(result);
    } catch (err) {
      showResults({
        is_valid: false,
        is_well_formed: false,
        is_structurally_valid: false,
        is_dtd_valid: null,
        errors: [{
          type: 'system',
          line: 0,
          column: 0,
          title: 'Errore di comunicazione',
          message: 'Non è stato possibile contattare il server di validazione: ' + err.message,
          suggestion: 'Verifica che il server sia in esecuzione e riprova.',
        }],
        warnings: [],
        structure: null,
        stats: {},
      });
    } finally {
      btnValidate.disabled = false;
      btnValidate.innerHTML = originalHTML;
    }
  }

  // ── Render results ────────────────────────────────────────────────────
  function showResults(result) {
    resultsPanel.hidden = false;

    // Status badge
    renderStatus(result);

    // Errors
    const syntaxStructureErrors = result.errors.filter(
      e => e.type === 'syntax' || e.type === 'structure' || e.type === 'input' || e.type === 'system'
    );
    const dtdErrors = result.errors.filter(e => e.type === 'dtd');

    if (syntaxStructureErrors.length > 0) {
      errorsSection.hidden = false;
      errorList.innerHTML = syntaxStructureErrors.map(renderErrorItem).join('');
    } else if (dtdErrors.length > 0) {
      errorsSection.hidden = false;
      errorList.innerHTML = dtdErrors.map(renderErrorItem).join('');
    } else {
      errorsSection.hidden = true;
    }

    // Warnings (if any)
    if (result.warnings && result.warnings.length > 0) {
      warningsSection.hidden = false;
      warningList.innerHTML = result.warnings.map(renderWarningItem).join('');
    } else {
      warningsSection.hidden = true;
    }

    // Structure tree
    if (result.is_well_formed && result.structure) {
      structureSection.hidden = false;
      renderStructure(result.structure, result.stats);
    } else {
      structureSection.hidden = true;
    }

    // Scroll to results on mobile
    if (window.innerWidth < 800) {
      resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // ── Status badge ──────────────────────────────────────────────────────
  function renderStatus(result) {
    const hasErrors = result.errors.some(
      e => e.type === 'syntax' || e.type === 'structure' || e.type === 'input' || e.type === 'system'
    );
    const hasDtdErrors = result.errors.some(e => e.type === 'dtd');
    const isFullyValid = result.is_valid;

    let badgeClass, iconSvg, title, description;

    if (isFullyValid) {
      badgeClass = 'status-badge--valid';
      iconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="16 10 10.5 15 8 12"/></svg>`;
      title = 'XML valido!';
      description = 'Il documento è sintatticamente corretto e ben formato.';
      if (result.is_dtd_valid) {
        description += ' Inoltre, rispetta la DTD fornita.';
      }
    } else if (!result.is_well_formed) {
      badgeClass = 'status-badge--invalid';
      iconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
      title = 'XML non valido — errori di sintassi';
      description = 'Il documento non rispetta le regole base dell\'XML. Correggi gli errori elencati sotto.';
    } else if (hasDtdErrors) {
      badgeClass = 'status-badge--partial';
      iconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
      title = 'XML ben formato, ma non valido per la DTD';
      description = 'La sintassi XML è corretta, ma il documento non rispetta le regole della DTD.';
    } else {
      badgeClass = 'status-badge--invalid';
      iconSvg = `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
      title = 'XML non valido';
      description = 'Sono stati trovati errori nel documento.';
    }

    // Build checks list
    let checksHTML = '';
    checksHTML += `<li class="check-item">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="${result.is_well_formed ? 'check-pass' : 'check-fail'}">
        ${result.is_well_formed 
          ? '<polyline points="20 6 9 17 4 12"/>' 
          : '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'}
      </svg>
      Sintassi XML (well-formed)
    </li>`;
    checksHTML += `<li class="check-item">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="${result.is_structurally_valid ? 'check-pass' : 'check-fail'}">
        ${result.is_structurally_valid 
          ? '<polyline points="20 6 9 17 4 12"/>' 
          : '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'}
      </svg>
      Struttura (tag bilanciati)
    </li>`;
    if (result.is_dtd_valid !== null) {
      checksHTML += `<li class="check-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="${result.is_dtd_valid ? 'check-pass' : 'check-fail'}">
          ${result.is_dtd_valid 
            ? '<polyline points="20 6 9 17 4 12"/>' 
            : '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'}
        </svg>
        Validità DTD
      </li>`;
    }

    statusArea.innerHTML = `
      <div class="status-badge ${badgeClass} animate-fade-in">
        <span class="status-icon">${iconSvg}</span>
        <div class="status-text">
          <h3>${title}</h3>
          <p>${description}</p>
          <ul class="checks-list">${checksHTML}</ul>
        </div>
      </div>
    `;
  }

  // ── Error item ────────────────────────────────────────────────────────
  function renderErrorItem(err) {
    const locationHTML = err.line > 0
      ? `<span class="error-location">
           <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 2L2 22h20L12 2z"/><line x1="12" y1="11" x2="12" y2="17"/><circle cx="12" cy="20.5" r="0.6" fill="currentColor" stroke="none"/></svg>
           Riga&nbsp;${err.line}, Col&nbsp;${err.column}
         </span>`
      : '';

    return `
      <li class="error-item animate-fade-in">
        <div class="error-item-header">
          ${locationHTML}
          <span class="error-title">${escapeHTML(err.title)}</span>
        </div>
        <div class="error-item-body">
          <p class="error-message">${escapeHTML(err.message)}</p>
          ${err.suggestion ? `<p class="error-suggestion">${escapeHTML(err.suggestion)}</p>` : ''}
        </div>
      </li>
    `;
  }

  function renderWarningItem(warn) {
    return `
      <li class="warning-item animate-fade-in">
        <div class="error-item-header">
          <span class="error-title">${escapeHTML(warn.title || warn.message)}</span>
        </div>
        <div class="error-item-body">
          <p class="error-message">${escapeHTML(warn.message)}</p>
          ${warn.suggestion ? `<p class="error-suggestion">${escapeHTML(warn.suggestion)}</p>` : ''}
        </div>
      </li>
    `;
  }

  // ── Structure tree ────────────────────────────────────────────────────
  function renderStructure(structure, stats) {
    // Stats
    if (stats && (stats.total_elements || stats.max_depth)) {
      structureStats.innerHTML = `
        <span class="stat-item">Elementi totali: <span class="stat-value">${stats.total_elements || '—'}</span></span>
        <span class="stat-item">Profondità massima: <span class="stat-value">${stats.max_depth || '—'}</span></span>
      `;
    } else {
      structureStats.innerHTML = '';
    }

    // Tree
    structureTree.innerHTML = buildTreeHTML(structure, 0);
  }

  function buildTreeHTML(node, depth) {
    const depthClass = 'tree-depth-' + Math.min(depth, 9);
    const indent = '  '.repeat(depth);

    let html = `<div class="tree-node ${depthClass}">`;

    // Opening tag
    const attrs = node.attributes || {};
    const attrStr = Object.entries(attrs)
      .map(([k, v]) => ` <span class="tree-attr">${escapeHTML(k)}</span>=<span class="tree-value">"${escapeHTML(v)}"</span>`)
      .join('');

    const hasChildren = node.children && node.children.length > 0;
    const hasText = node.text && node.text.trim();

    if (hasChildren || hasText) {
      html += `<span class="tree-tag">&lt;${escapeHTML(node.tag)}</span>${attrStr}<span class="tree-tag">&gt;</span>`;
    } else {
      html += `<span class="tree-tag">&lt;${escapeHTML(node.tag)}</span>${attrStr}<span class="tree-tag">/&gt;</span>`;
    }

    // Text content
    if (hasText && !hasChildren) {
      html += `<span class="tree-text">${escapeHTML(node.text)}</span>`;
    } else if (hasText && hasChildren) {
      html += `\n${indent}  <span class="tree-text">${escapeHTML(node.text)}</span>`;
    }

    // Children
    if (hasChildren) {
      html += '\n';
      for (const child of node.children) {
        html += buildTreeHTML(child, depth + 1);
      }
      // Closing tag
      html += `${indent}<span class="tree-tag">&lt;/${escapeHTML(node.tag)}&gt;</span>`;
    }

    html += '</div>\n';
    return html;
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function escapeHTML(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function showToast(message) {
    // Simple console fallback
    console.warn('Toast:', message);
    alert(message);
  }

  // ── Keyboard shortcut hint ────────────────────────────────────────────
  xmlInput.setAttribute('title', 'Premi Ctrl+Invio per validare');

  // ── Initialize ────────────────────────────────────────────────────────
  updateCharCount();

  // Add spin keyframe if not already present
  if (!document.getElementById('xml-docile-spin-style')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'xml-docile-spin-style';
    styleEl.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
    document.head.appendChild(styleEl);
  }
})();
