// ═══════════════════════════════════════════════════════════════════════════
// DocuVerity — Dashboard Logic
// ═══════════════════════════════════════════════════════════════════════════

const API = '';  // same origin

// ── State ──
let currentFindings = [];
let uploadedFile = null;
let reportMarkdown = '';

const CATEGORIES = {
  typography: { label: 'Typography & printing', icon: '🔤' },
  signature: { label: 'Signatures & handwriting', icon: '✍️' },
  substrate: { label: 'Paper & security features', icon: '📜' },
  ink:       { label: 'Ink & writing instruments', icon: '🖋️' },
  digital:   { label: 'Digital file & metadata', icon: '💾' },
};

const INDICATOR_GENUINE_NOTES = {
  mod_date_after_issue: 'File was created on or before the stated issue date and not edited after.',
  producer_editing_tool: "Producer/creator is the issuer's own certificate system.",
  metadata_inconsistent: 'Info dictionary and XMP metadata agree on dates and producer.',
  incremental_updates: 'File contains a single revision — no re-saves.',
  mod_after_creation: 'Creation and modification dates are consistent.',
  tremor_hesitation: 'Signature is fluid and natural with no hesitation.',
  blunt_starts_ends: 'Strokes taper naturally at beginning and end.',
  unusual_pen_lifts: 'No unusual pen lifts found — consistent with exemplars.',
  proportion_slant_mismatch: 'Proportions and slant match the known exemplars.',
  tracing_guidelines: 'No indented guidelines or pencil traces detected.',
  signature_identical_overlay: 'Signature does not identically overlay any known signature.',
  font_family_mismatch: "Font matches the issuer's known template.",
  spacing_irregular: 'Character and word spacing is consistent.',
  baseline_misalignment: 'All text aligns properly with the baseline.',
  print_process_mismatch: 'Printing process is uniform throughout.',
  uv_fluorescence_differs: 'Paper fluorescence matches genuine stock.',
  watermark_absent: 'Watermark is present and correct.',
  security_feature_missing: 'All security features intact.',
  erasure_abrasion: 'No fibre disturbance detected.',
  ink_differentiation: 'Ink is consistent throughout the document.',
  ink_feathering: 'No abnormal ink feathering detected.',
  overwriting_retouching: 'No overwriting or retouching observed.',
  line_crossing_sequence: 'Line crossing sequence is consistent.',
  verification_failed: 'QR code / verification matches the issuer record.',
};

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  renderObsCategories();
  setupFileHandlers();
  generateCaseId();
});

function generateCaseId() {
  const id = 'UI-' + Math.random().toString(36).substring(2, 8).toUpperCase();
  document.getElementById('caseId').value = id;
}

// ── File Upload ──
function setupFileHandlers() {
  const zone = document.getElementById('dropZone');
  const input = document.getElementById('fileInput');

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => { if (input.files.length) handleFile(input.files[0]); });
  document.getElementById('removeFile').addEventListener('click', clearFile);
}

function handleFile(file) {
  uploadedFile = file;
  
  // Clear any previous findings from loaded samples when uploading a new file
  currentFindings = [];
  renderObsCategories();

  document.getElementById('dropZone').classList.add('hidden');
  const info = document.getElementById('fileInfo');
  info.classList.remove('hidden');
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileSize').textContent = formatBytes(file.size);
}

function clearFile() {
  uploadedFile = null;
  currentFindings = [];
  renderObsCategories();
  document.getElementById('fileInput').value = '';
  document.getElementById('dropZone').classList.remove('hidden');
  document.getElementById('fileInfo').classList.add('hidden');
}

function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
}

// ── Observation Categories ──
function renderObsCategories() {
  const el = document.getElementById('obsCategories');
  el.innerHTML = '';
  for (const [key, cat] of Object.entries(CATEGORIES)) {
    const count = currentFindings.filter(f => getCategoryForIndicator(f.indicator) === key).length;
    const div = document.createElement('div');
    div.className = 'obs-cat';
    div.innerHTML = `
      <span>${cat.icon} ${cat.label}</span>
      <span class="count ${count ? 'has-findings' : ''}">${count ? count + ' flagged' : 'Clear'}</span>
    `;
    el.appendChild(div);
  }
  document.getElementById('obsBadge').textContent = `${currentFindings.length} recorded`;
  renderFindingsList();
}

function getCategoryForIndicator(id) {
  const map = {
    font_family_mismatch: 'typography', spacing_irregular: 'typography',
    baseline_misalignment: 'typography', print_process_mismatch: 'typography',
    tremor_hesitation: 'signature', blunt_starts_ends: 'signature',
    unusual_pen_lifts: 'signature', proportion_slant_mismatch: 'signature',
    tracing_guidelines: 'signature', signature_identical_overlay: 'signature',
    uv_fluorescence_differs: 'substrate', watermark_absent: 'substrate',
    security_feature_missing: 'substrate', erasure_abrasion: 'substrate',
    ink_differentiation: 'ink', ink_feathering: 'ink',
    overwriting_retouching: 'ink', line_crossing_sequence: 'ink',
    mod_after_creation: 'digital', mod_date_after_issue: 'digital',
    producer_editing_tool: 'digital', incremental_updates: 'digital',
    metadata_inconsistent: 'digital', verification_failed: 'digital',
    ela_anomaly: 'digital', editing_software_in_exif: 'digital',
  };
  return map[id] || 'digital';
}

function renderFindingsList() {
  const el = document.getElementById('findingsList');
  el.innerHTML = '';
  currentFindings.forEach((f, i) => {
    const div = document.createElement('div');
    div.className = 'finding-chip';
    div.innerHTML = `
      <span class="dot ${f.status}"></span>
      <span class="lbl">${f.indicator.replace(/_/g, ' ')}</span>
      <span class="rm" onclick="removeFinding(${i})">✕</span>
    `;
    el.appendChild(div);
  });
}

function removeFinding(idx) {
  currentFindings.splice(idx, 1);
  renderObsCategories();
}

// ── Load Sample ──
async function loadSample(name) {
  try {
    const res = await fetch(`${API}/api/sample/${name}`);
    const data = await res.json();
    document.getElementById('docType').value = data.document_type || 'generic';
    document.getElementById('issueDate').value = data.stated_issue_date || '';
    document.getElementById('caseId').value = data.case_id || '';
    document.getElementById('examinerName').value = data.examiner_name || '';
    document.getElementById('docDesc').value = data.document_description || '';
    currentFindings = data.findings || [];
    clearFile();
    renderObsCategories();
  } catch (e) {
    console.error('Failed to load sample:', e);
  }
}

// ── Run Examination ──
async function runExamination() {
  const btn = document.getElementById('btnExamine');
  btn.disabled = true;

  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('results').classList.add('hidden');
  document.getElementById('loadingState').classList.remove('hidden');

  // If there's an uploaded file, analyze it first
  let fileFindings = [];
  if (uploadedFile) {
    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('stated_issue_date', document.getElementById('issueDate').value);
    try {
      const endpoint = uploadedFile.name.toLowerCase().endsWith('.pdf')
        ? '/api/analyze-pdf' : '/api/analyze-image';
      const res = await fetch(API + endpoint, { method: 'POST', body: formData });
      const analysis = await res.json();
      if (analysis.findings) fileFindings = analysis.findings;
    } catch (e) { console.error('File analysis error:', e); }
  }

  // Merge file findings with manual findings
  const allFindings = [...currentFindings];
  for (const ff of fileFindings) {
    if (!allFindings.find(f => f.indicator === ff.indicator)) {
      allFindings.push(ff);
    }
  }

  // Call the examine endpoint
  const payload = {
    case_id: document.getElementById('caseId').value,
    document_type: document.getElementById('docType').value,
    stated_issue_date: document.getElementById('issueDate').value,
    document_description: document.getElementById('docDesc').value,
    examiner_name: document.getElementById('examinerName').value,
    findings: allFindings,
  };

  try {
    const res = await fetch(API + '/api/examine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    displayResults(result, allFindings);
  } catch (e) {
    console.error('Examine error:', e);
    alert('Error running examination. Is the server running?');
  }

  document.getElementById('loadingState').classList.add('hidden');
  btn.disabled = false;
}

// ── Display Results ──
function displayResults(result, allFindings) {
  const ev = result.evaluation;
  const cls = result.classification;

  // Update findings list to include any file-derived findings
  currentFindings = allFindings;
  renderObsCategories();

  // Verdict class
  const card = document.getElementById('verdictCard');
  card.classList.remove('forged', 'genuine', 'neutral');
  const log10 = ev.combined_log10_lr;
  if (log10 > 0.5) card.classList.add('forged');
  else if (log10 < -0.5) card.classList.add('genuine');
  else card.classList.add('neutral');

  // Label
  document.getElementById('verdictLabel').textContent = `VERDICT · CASE ${document.getElementById('caseId').value}`;

  // Title
  const title = document.getElementById('verdictTitle');
  if (log10 > 2) title.textContent = 'LIKELY FORGED / ALTERED';
  else if (log10 > 0.5) title.textContent = 'POSSIBLY FORGED / ALTERED';
  else if (log10 < -0.5) title.textContent = 'LIKELY GENUINE';
  else title.textContent = 'INCONCLUSIVE';

  document.getElementById('verdictDesc').textContent = ev.verbal_conclusion;

  // Bar
  const pct = ev.triage_score;
  document.getElementById('barFill').style.width = pct + '%';
  document.getElementById('barDot').style.left = pct + '%';
  document.getElementById('barCaption').textContent =
    `Likelihood ratio ${ev.combined_lr.toLocaleString()} · Triage score ${pct}/100`;

  // Stats
  const anomalies = ev.contributions.filter(c => c.status === 'present').length;
  const genuine = ev.contributions.filter(c => c.status === 'absent').length;
  const missing = (result.recommended_examinations || []).length;

  document.getElementById('statAnomalies').querySelector('h2').textContent = anomalies;
  document.getElementById('statGenuine').querySelector('h2').textContent = genuine;
  document.getElementById('statMissing').querySelector('h2').textContent = missing;

  // Forgery type
  const ftEl = document.getElementById('forgeryType');
  ftEl.textContent = cls.anomaly_type;
  if (cls.anomaly_type.toLowerCase().includes('no anomaly')) {
    ftEl.style.background = 'var(--green-dim)';
    ftEl.style.color = '#6ee7b7';
    ftEl.style.borderColor = 'rgba(16,185,129,.2)';
  } else {
    ftEl.style.background = '';
    ftEl.style.color = '';
    ftEl.style.borderColor = '';
  }

  // Detailed findings
  const detailEl = document.getElementById('findingsDetail');
  detailEl.innerHTML = '';
  for (const c of ev.contributions) {
    const isAnomaly = c.status === 'present';
    const lrVal = c.lr;
    const div = document.createElement('div');
    div.className = 'detail-card animate-in';
    div.innerHTML = `
      <div class="detail-head">
        <h4>${c.label}</h4>
        <span class="lr-tag ${lrVal < 2 ? 'low' : ''}">${lrVal.toFixed(1)}× if forged</span>
      </div>
      <p class="detail-sub">${c.category} · ${c.indicator.replace(/_/g, ' ')}</p>
      <div class="compare-grid">
        <div class="compare-box ${isAnomaly ? 'found' : 'ok'}">
          <h5>${isAnomaly ? '❌ FOUND' : '✅ CLEAR'}</h5>
          <p>${c.note || (isAnomaly ? 'Anomaly detected' : 'No anomaly')}</p>
        </div>
        <div class="compare-box ok">
          <h5>✅ GENUINE SHOWS</h5>
          <p>${INDICATOR_GENUINE_NOTES[c.indicator] || 'Expected to be normal in a genuine document.'}</p>
        </div>
      </div>
    `;
    detailEl.appendChild(div);
  }

  // Standards
  const stdEl = document.getElementById('standardsList');
  stdEl.innerHTML = '';
  if (result.standards) {
    for (const s of (result.standards.examination_standards || [])) {
      stdEl.innerHTML += `<div class="std-item"><span class="std-dot"></span><span>${s}</span></div>`;
    }
    for (const s of (result.standards.legal_provisions_to_verify || [])) {
      stdEl.innerHTML += `<div class="std-item std-legal"><span class="std-dot"></span><span>${s}</span></div>`;
    }
  }

  // Report
  reportMarkdown = result.report_markdown || '';
  document.getElementById('reportPre').textContent = reportMarkdown;

  // Show results with animation
  const resultsEl = document.getElementById('results');
  resultsEl.classList.remove('hidden');
  resultsEl.querySelectorAll('.card').forEach((c, i) => {
    c.classList.add('animate-in');
    c.style.animationDelay = (i * 0.12) + 's';
  });
}

function copyReport() {
  navigator.clipboard.writeText(reportMarkdown).then(() => {
    const btn = event.target;
    btn.textContent = '✅ Copied!';
    setTimeout(() => { btn.textContent = '📋 Copy'; }, 1500);
  });
}
