/**
 * AttentionX AI — Frontend Application
 * Handles all UI interactions, API calls, animations, and demo mode.
 */

/* ══════════════════════════════════════════════════════════════
   CONFIG
══════════════════════════════════════════════════════════════ */
const API_BASE = 'http://localhost:8000/api/v1';
let currentVideoId = null;
let currentHighlights = [];
let selectedClips = new Set();
let selectedFormat = 'reels';
let selectedTheme = 'netflix';
let allClips = [];

/* ══════════════════════════════════════════════════════════════
   NAV SCROLL EFFECT
══════════════════════════════════════════════════════════════ */
window.addEventListener('scroll', () => {
  const nav = document.getElementById('main-nav');
  if (nav) nav.classList.toggle('scrolled', window.scrollY > 40);
});

/* ══════════════════════════════════════════════════════════════
   SECTION SWITCHING
══════════════════════════════════════════════════════════════ */
function showSection(section) {
  const landing = document.getElementById('landing-page');
  const app = document.getElementById('app-section');
  if (section === 'app') {
    landing.style.display = 'none';
    app.style.display = 'block';
    checkApiStatus();
    loadDashboard();
    updateExportPanel();
    document.title = 'AttentionX AI — Dashboard';
    window.scrollTo(0, 0);
  } else {
    landing.style.display = 'block';
    app.style.display = 'none';
    document.title = 'AttentionX AI — Turn Long Videos Into Viral Clips';
  }
}

/* ══════════════════════════════════════════════════════════════
   LOGIN LOGIC
══════════════════════════════════════════════════════════════ */
function openLoginModal() {
  document.getElementById('login-overlay').classList.add('open');
}

function closeLoginModal() {
  document.getElementById('login-overlay').classList.remove('open');
}

function processLogin() {
  const email = document.getElementById('login-email').value;
  const pass = document.getElementById('login-pass').value;
  if (!email || !pass) {
    showToast('⚠️ Please enter both email and password.', true);
    return;
  }
  
  // Create mock user session
  localStorage.setItem('ax_user', email.split('@')[0]);
  closeLoginModal();
  showSection('app');
  showToast('✅ Logged in successfully!');
  
  // Update header to reflect user
  updateUserUI();
}

function updateUserUI() {
  const user = localStorage.getItem('ax_user');
  if (user) {
    const navActions = document.querySelector('.nav-actions');
    if (navActions) {
      navActions.innerHTML = `<span style="color:var(--text-secondary); margin-right: 15px;">Hey, ${user}</span><button class="btn btn-outline" onclick="showSection('app')">Dashboard →</button>`;
    }
  }
}

// Check if already logged in on load
window.addEventListener('DOMContentLoaded', () => {
    updateUserUI();
});

/* ══════════════════════════════════════════════════════════════
   MOBILE MENU
══════════════════════════════════════════════════════════════ */
function toggleMobile() {
  document.getElementById('mobile-menu').classList.toggle('open');
}

/* ══════════════════════════════════════════════════════════════
   APP VIEW SWITCHING
══════════════════════════════════════════════════════════════ */
function switchView(viewName, btnEl) {
  // Update nav buttons
  document.querySelectorAll('.app-nav-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  else {
    const btn = document.querySelector(`[data-view="${viewName}"]`);
    if (btn) btn.classList.add('active');
  }

  // Update views
  document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
  const view = document.getElementById(`view-${viewName}`);
  if (view) view.classList.add('active');

  // Update step indicator
  const steps = ['upload','analyze','clips','export-step'];
  const stepMap = { upload: 0, analyze: 1, clips: 2, export: 3, dashboard: -1 };
  const stepIdx = stepMap[viewName] ?? -1;
  steps.forEach((s, i) => {
    const el = document.getElementById(`si-${s}`);
    if (!el) return;
    el.classList.remove('active', 'done');
    if (i < stepIdx) el.classList.add('done');
    else if (i === stepIdx) el.classList.add('active');
  });

  // View-specific initializations
  if (viewName === 'clips') renderClipsGrid();
  if (viewName === 'export') updateExportPanel();
  if (viewName === 'dashboard') loadDashboard();
  if (viewName === 'analyze') {
    if (!currentVideoId) {
      document.getElementById('analyze-config').style.display = 'none';
      document.getElementById('no-video-msg').style.display = 'block';
    } else {
      document.getElementById('analyze-config').style.display = 'block';
      document.getElementById('no-video-msg').style.display = 'none';
    }
  }
}

/* ══════════════════════════════════════════════════════════════
   API STATUS CHECK
══════════════════════════════════════════════════════════════ */
async function checkApiStatus() {
  const indicator = document.getElementById('api-indicator');
  try {
    const r = await fetch(`${API_BASE.replace('/api/v1','/health')}`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      indicator.textContent = '● API Connected';
      indicator.style.color = 'var(--brand-green)';
    }
  } catch {
    indicator.textContent = '● Demo Mode';
    indicator.style.color = 'var(--brand-accent)';
  }
}

/* ══════════════════════════════════════════════════════════════
   UPLOAD HANDLERS
══════════════════════════════════════════════════════════════ */
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('upload-area').classList.add('dragover');
}

function handleDragLeave(e) {
  e.preventDefault();
  document.getElementById('upload-area').classList.remove('dragover');
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-area').classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) processUpload(file);
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) processUpload(file);
}

async function processUpload(file) {
  const allowedExts = ['mp4','mov','avi','mkv','webm'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowedExts.includes(ext)) {
    showToast('❌ Unsupported file type. Use MP4, MOV, or AVI.', true);
    return;
  }

  // Switch to progress view
  document.getElementById('upload-idle').style.display = 'none';
  document.getElementById('upload-progress-view').style.display = 'block';
  document.getElementById('upv-filename').textContent = file.name;
  document.getElementById('upv-size').textContent = formatBytes(file.size);

  try {
    // Try real API first
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    let videoData = null;

    // Simulate progress even while uploading
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        updateUploadProgress(pct, 'Uploading…');
      }
    };

    const uploadPromise = new Promise((resolve, reject) => {
      xhr.onload = () => {
        if (xhr.status === 200) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new Error(`HTTP ${xhr.status}`));
        }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.timeout = 300000;
      xhr.ontimeout = () => reject(new Error('Timeout'));
      xhr.open('POST', `${API_BASE}/upload`);
      xhr.send(formData);
    });

    videoData = await uploadPromise;

    updateUploadProgress(100, 'Processing metadata…');
    setTimeout(() => finishUpload(videoData), 600);

  } catch (err) {
    console.error('API upload failed:', err);
    showToast('❌ Upload failed: ' + err.message, true);
    
    // Switch back to idle view on fail
    document.getElementById('upload-idle').style.display = 'flex';
    document.getElementById('upload-progress-view').style.display = 'none';
  }
}

function updateUploadProgress(pct, status) {
  document.getElementById('upload-prog-bar').style.width = pct + '%';
  document.getElementById('upv-pct').textContent = pct + '%';
  document.getElementById('upv-status').textContent = status;
}

function simulateUploadProgress() {
  return new Promise(resolve => {
    let pct = 0;
    const iv = setInterval(() => {
      pct += Math.random() * 12 + 4;
      if (pct >= 100) { pct = 100; clearInterval(iv); resolve(); }
      updateUploadProgress(Math.min(100, Math.round(pct)), 'Uploading…');
    }, 150);
  });
}

function finishUpload(data) {
  currentVideoId = data.video_id;

  document.getElementById('upload-progress-view').style.display = 'none';
  document.getElementById('upload-success-view').style.display = 'block';

  // Build metadata grid
  const grid = document.getElementById('video-meta-grid');
  const duration = formatDuration(data.duration || 0);
  grid.innerHTML = `
    <div class="vmg-item"><span>Duration</span><strong>${duration}</strong></div>
    <div class="vmg-item"><span>Resolution</span><strong>${data.width}×${data.height}</strong></div>
    <div class="vmg-item"><span>File Size</span><strong>${formatBytes(data.file_size_mb * 1024 * 1024)}</strong></div>
    <div class="vmg-item"><span>FPS</span><strong>${(data.fps || 30).toFixed(2)}</strong></div>
  `;

  // Show recent uploads
  addToRecentUploads(data);

  showToast('✅ Video uploaded successfully!');
}

function addToRecentUploads(data) {
  const recentSection = document.getElementById('recent-uploads');
  const recentList = document.getElementById('recent-list');
  recentSection.style.display = 'block';

  const item = document.createElement('div');
  item.className = 'recent-item';
  item.innerHTML = `
    <span class="ri-icon">🎥</span>
    <div class="ri-info">
      <div class="ri-name">${data.filename}</div>
      <div class="ri-meta">${formatDuration(data.duration || 0)} · ${formatBytes((data.file_size_mb || 0) * 1024 * 1024)}</div>
    </div>
    <span class="ri-status uploaded">Uploaded</span>
  `;
  item.addEventListener('click', () => {
    currentVideoId = data.video_id;
    switchView('analyze', document.querySelector('[data-view=analyze]'));
    showToast('📹 Video selected: ' + data.filename);
  });
  recentList.prepend(item);
}

/* ══════════════════════════════════════════════════════════════
   ANALYSIS
══════════════════════════════════════════════════════════════ */
function updateDurLabel(el, targetId) {
  document.getElementById(targetId).textContent =
    targetId.includes('clips') ? el.value : el.value + 's';
}

async function startAnalysis() {
  if (!currentVideoId) {
    showToast('⚠️ Please upload a video first.', true);
    return;
  }

  // Show analyzer UI
  document.getElementById('analyze-config').style.display = 'none';
  document.getElementById('analyze-running').style.display = 'block';
  document.getElementById('analyze-results').style.display = 'none';

  const steps = [
    'Extracting audio signal…',
    'Computing energy peaks (Librosa)…',
    'Analysing sentiment (Gemini 1.5 Flash)…',
    'Running face detection (MediaPipe)…',
    'Generating hook titles…',
    'Computing virality scores…',
    'Ranking clips by impact…',
  ];
  buildWaveform('ar-wave-bars', 50);
  await runAnalysisSteps(steps);

  const minDur = parseFloat(document.getElementById('min-dur').value);
  const maxDur = parseFloat(document.getElementById('max-dur').value);
  const maxClips = parseInt(document.getElementById('max-clips').value);
  const language = document.getElementById('lang-sel').value;

  try {
    const resp = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: currentVideoId,
        min_clip_duration: minDur,
        max_clip_duration: maxDur,
        max_clips: maxClips,
        language,
      }),
    });
    if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || 'API analysis error');
    }
    const data = await resp.json();
    currentHighlights = data.highlights;
    allClips = [...currentHighlights];
    showAnalysisResults(data);
  } catch (err) {
    console.error('AI Analysis failed:', err);
    showToast('❌ AI Analysis failed: ' + err.message, true);
    
    // Switch back to config
    document.getElementById('analyze-config').style.display = 'block';
    document.getElementById('analyze-running').style.display = 'none';
    document.getElementById('analyze-results').style.display = 'none';
  }
}

async function runAnalysisSteps(steps) {
  const container = document.getElementById('ar-steps');
  container.innerHTML = '';
  const stepEls = steps.map((text, i) => {
    const el = document.createElement('div');
    el.className = 'ar-step';
    el.innerHTML = `<div class="ar-step-dot"></div><span>${text}</span>`;
    container.appendChild(el);
    return el;
  });

  for (let i = 0; i < stepEls.length; i++) {
    stepEls[i].classList.add('active');
    await delay(600 + Math.random() * 400);
    stepEls[i].classList.remove('active');
    stepEls[i].classList.add('done');
    stepEls[i].querySelector('span').textContent = '✅ ' + steps[i].replace('…','');
  }
}

function showAnalysisResults(data) {
  document.getElementById('analyze-running').style.display = 'none';
  document.getElementById('analyze-results').style.display = 'block';

  // Summary
  const summary = document.getElementById('ar-summary');
  const topScore = data.highlights[0]?.virality_score ?? 0;
  summary.innerHTML = `
    <h3>🎯 Analysis Complete — ${data.total_clips} Golden Moments Found</h3>
    <p>${data.summary || `Processed in ${data.processing_time_sec?.toFixed(2) ?? '~3.2'}s · Top virality score: ${topScore}%`}</p>
  `;

  // Highlights list
  const list = document.getElementById('highlights-list');
  list.innerHTML = '';
  data.highlights.forEach((h, i) => {
    const el = document.createElement('div');
    el.className = 'highlight-item';
    el.setAttribute('data-highlight-id', h.id);
    const viralityColor = h.virality_score >= 80 ? 'var(--brand-hot)' : h.virality_score >= 60 ? 'var(--brand-accent)' : 'var(--brand-secondary)';
    el.innerHTML = `
      <div class="hi-rank">#${i+1}</div>
      <div class="hi-info">
        <div class="hi-hook">${h.hook_title || 'AI-Generated Hook'}</div>
        <span class="hi-topic">${h.topic}</span>
        <div class="hi-meta">⏱ ${formatDuration(h.start_time)} – ${formatDuration(h.end_time)} · ${h.duration}s</div>
      </div>
      <div class="hi-scores">
        <div class="score-badge virality">🔥 ${h.virality_score}% Viral</div>
        <div class="score-badge energy">⚡ ${h.energy_score}% Energy</div>
      </div>
    `;
    el.addEventListener('click', () => openHighlightModal(h));
    list.appendChild(el);
  });

  showToast(`✅ Found ${data.total_clips} viral clips!`);
}

/* ══════════════════════════════════════════════════════════════
   DEMO HIGHLIGHT GENERATION
══════════════════════════════════════════════════════════════ */
const TOPICS = [
  'Mindset & Growth','Success Habits','Entrepreneurship','Leadership',
  'Mental Health','Productivity','Finance','Relationships','Motivation',
  'Personal Branding','Marketing Strategy','AI & Technology',
];

const HOOKS = [
  'This will completely change how you think 🔥',
  'Nobody talks about this success secret 👀',
  'The truth no one tells you about growth 💡',
  'Stop making this productivity mistake ⚠️',
  'This hack changed everything for me 🤯',
  'I tried this for 30 days — here\'s what happened',
  'The #1 lesson that changed my life 💡',
  'Why most people fail (and how to fix it)',
  'This strategy made me 10x more effective ⚡',
  'The uncomfortable truth about success 🎯',
];

function generateDemoHighlights(count, minDur, maxDur) {
  const highlights = [];
  let t = 30;
  for (let i = 0; i < count; i++) {
    const dur = minDur + Math.random() * (maxDur - minDur);
    const virality = Math.round(97 - i * 6 + Math.random() * 8);
    const energy = Math.round(70 + Math.random() * 28);
    const sentiment = Math.round(65 + Math.random() * 30);
    const topic = TOPICS[i % TOPICS.length];
    highlights.push({
      id: 'h' + Math.random().toString(36).slice(2,7),
      video_id: currentVideoId,
      start_time: Math.round(t),
      end_time: Math.round(t + dur),
      duration: Math.round(dur),
      virality_score: Math.min(99, Math.max(30, virality)),
      energy_score: energy,
      sentiment_score: sentiment,
      topic,
      hook_title: HOOKS[i % HOOKS.length],
      description: `High-energy segment about ${topic.toLowerCase()} with strong emotional resonance.`,
      key_insight: 'Your most powerful asset is consistency — show up every single day.',
      thumbnail_url: null,
      clip_url: null,
    });
    t += dur + 60 + Math.random() * 120;
  }
  highlights.sort((a, b) => b.virality_score - a.virality_score);
  return {
    video_id: currentVideoId,
    highlights,
    total_clips: count,
    processing_time_sec: 2.8 + Math.random() * 1.5,
    summary: `Found ${count} high-impact moments. Top clip virality: ${highlights[0]?.virality_score}%.`,
  };
}

/* ══════════════════════════════════════════════════════════════
   CLIPS VIEW
══════════════════════════════════════════════════════════════ */
function renderClipsGrid(clips = null) {
  const grid = document.getElementById('clips-grid');
  const toRender = clips ?? allClips;

  if (!toRender.length) {
    grid.innerHTML = `
      <div class="empty-clips" id="empty-clips">
        <div class="ec-icon">🧠</div>
        <h3>No clips yet</h3>
        <p>Run AI Analysis to find your best moments.</p>
        <button class="btn btn-primary" onclick="switchView('analyze', document.querySelector('[data-view=analyze]'))">Start Analysis</button>
      </div>`;
    return;
  }

  grid.innerHTML = '';
  toRender.forEach((h, i) => {
    const card = document.createElement('div');
    card.className = 'clip-card';
    card.setAttribute('data-id', h.id);
    const viralGrad = h.virality_score >= 80
      ? 'linear-gradient(90deg, #ef4444, #f59e0b)'
      : 'linear-gradient(90deg, #7c3aed, #a855f7)';
    const scoreClass = h.virality_score >= 70 ? 'hot' : 'normal';

    card.innerHTML = `
      <div class="clip-thumb" onclick="openHighlightModal(allClips.find(c => c.id === '${h.id}'))">
        <span>🎬</span>
        <div class="clip-play-btn">▶</div>
        <div class="clip-virality-bar" style="background:${viralGrad}"></div>
      </div>
      <div class="clip-body">
        <h3>${h.hook_title || 'Viral Clip'}</h3>
        <span class="clip-topic">${h.topic}</span>
        <div class="clip-scores">
          <span class="clip-score ${scoreClass}">🔥 ${h.virality_score}%</span>
          <span class="clip-score normal">⚡ ${h.energy_score}%</span>
          <span class="clip-score normal">⏱ ${h.duration}s</span>
        </div>
        <div class="clip-actions">
          <button class="btn btn-primary btn-sm" onclick="extractClip('${h.id}', event)">✂️ Extract</button>
          <button class="btn btn-outline btn-sm" onclick="generateCaptions('${h.id}', event)">📝 Captions</button>
          <button class="btn btn-ghost btn-sm" onclick="addToExport('${h.id}', event)">🚀 Export</button>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function sortClips(by) {
  const sorted = [...allClips].sort((a, b) => {
    if (by === 'virality') return b.virality_score - a.virality_score;
    if (by === 'energy') return b.energy_score - a.energy_score;
    if (by === 'duration') return b.duration - a.duration;
    return 0;
  });
  renderClipsGrid(sorted);
}

function filterClips(filter, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  let filtered = allClips;
  if (filter === 'hot') filtered = allClips.filter(c => c.virality_score >= 80);
  if (filter === 'medium') filtered = allClips.filter(c => c.virality_score >= 50 && c.virality_score < 80);
  renderClipsGrid(filtered);
}

async function extractClip(highlightId, evt) {
  if (evt) evt.stopPropagation();
  showToast('✂️ Extracting clip (demo mode)…');
  const h = allClips.find(c => c.id === highlightId);
  if (!h) return;

  try {
    const resp = await fetch(`${API_BASE}/clips/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ highlight_id: highlightId, vertical: true }),
    });
    if (resp.ok) {
      const data = await resp.json();
      h.clip_url = data.clip_url;
    }
  } catch {
    h.clip_url = '#demo-clip';
  }

  await delay(1200);
  showToast('✅ Clip extracted in 9:16 format!');
}

async function generateCaptions(highlightId, evt) {
  if (evt) evt.stopPropagation();
  const h = allClips.find(c => c.id === highlightId);
  if (!h) return;

  if (h.captions && h.captions.length > 0) {
      showToast('✅ Captions already generated for this clip!');
      return;
  }
  
  showToast('❌ Captions failed to generate from the AI Analysis step.', true);
}

function addToExport(highlightId, evt) {
  if (evt) evt.stopPropagation();
  selectedClips.add(highlightId);
  showToast('🚀 Added to export queue!');
  updateExportPanel();
}

/* ══════════════════════════════════════════════════════════════
   HIGHLIGHT MODAL
══════════════════════════════════════════════════════════════ */
function openHighlightModal(h) {
  if (!h) return;
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');

  const captions = h.captions ? h.captions.slice(0, 4).map(c => `<div class="hook-ex">"${c.text}"</div>`).join('') : '<p class="ec-empty">No captions yet. Click Captions in clip editor.</p>';

  content.innerHTML = `
    <div style="display:flex; gap:20px; align-items:flex-start; flex-wrap:wrap">
      <div style="flex:1; min-width:200px">
        <div style="background:linear-gradient(135deg,#1a0033,#000c1f); border-radius:12px; height:200px; display:flex; align-items:center; justify-content:center; font-size:56px; margin-bottom:16px;">🎬</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px">
          <span class="clip-score hot">🔥 ${h.virality_score}% Viral</span>
          <span class="clip-score normal">⚡ ${h.energy_score}% Energy</span>
          <span class="clip-score normal">😊 ${h.sentiment_score}% Sentiment</span>
        </div>
        <div style="font-size:12px; color:var(--text-muted)">
          ⏱ ${formatDuration(h.start_time)} – ${formatDuration(h.end_time)} · ${h.duration}s
        </div>
      </div>
      <div style="flex:2; min-width:260px">
        <span class="hi-topic">${h.topic}</span>
        <h2 style="font-size:20px; font-weight:800; margin:10px 0 12px; line-height:1.3">${h.hook_title}</h2>
        <p style="font-size:14px; color:var(--text-secondary); margin-bottom:16px">${h.description}</p>
        ${h.key_insight ? `<div style="padding:12px; background:rgba(124,58,237,0.08); border-left:3px solid var(--brand-primary); border-radius:0 8px 8px 0; font-size:13px; color:var(--text-secondary); margin-bottom:16px">"${h.key_insight}"</div>` : ''}
        <h4 style="font-size:14px; font-weight:700; margin-bottom:10px">📝 Captions Preview</h4>
        ${captions}
        <div style="display:flex; gap:10px; margin-top:20px; flex-wrap:wrap">
          <button class="btn btn-primary btn-sm" onclick="extractClip('${h.id}');closeModal()">✂️ Extract Clip</button>
          <button class="btn btn-outline btn-sm" onclick="generateCaptions('${h.id}');closeModal()">📝 Generate Captions</button>
          <button class="btn btn-outline btn-sm" onclick="addToExport('${h.id}');closeModal()">🚀 Add to Export</button>
        </div>
      </div>
    </div>
  `;
  overlay.classList.add('open');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

/* ══════════════════════════════════════════════════════════════
   EXPORT VIEW
══════════════════════════════════════════════════════════════ */
function pickFormat(el) {
  document.querySelectorAll('.fp-item').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  selectedFormat = el.dataset.format;
}

function pickTheme(el) {
  document.querySelectorAll('.tp-item').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  selectedTheme = el.dataset.theme;
}

function updateExportPanel() {
  const list = document.getElementById('export-clips-list');
  if (!allClips.length) {
    list.innerHTML = '<p class="ec-empty">Analyze a video first to see clips here.</p>';
    return;
  }

  list.innerHTML = '';
  allClips.forEach(h => {
    const item = document.createElement('div');
    const isSelected = selectedClips.has(h.id);
    item.className = `export-clip-item ${isSelected ? 'selected' : ''}`;
    item.setAttribute('data-id', h.id);
    item.innerHTML = `
      <div class="eci-check">${isSelected ? '✓' : ''}</div>
      <div class="eci-info">
        <div class="eci-hook">${h.hook_title || 'Clip'}</div>
        <div class="eci-meta">${h.topic} · ${h.duration}s · ⏱ ${formatDuration(h.start_time)}</div>
      </div>
      <div class="eci-score">🔥 ${h.virality_score}%</div>
    `;
    item.addEventListener('click', () => toggleExportClip(h.id, item));
    list.appendChild(item);
  });
}

function toggleExportClip(id, el) {
  if (selectedClips.has(id)) {
    selectedClips.delete(id);
    el.classList.remove('selected');
    el.querySelector('.eci-check').textContent = '';
  } else {
    selectedClips.add(id);
    el.classList.add('selected');
    el.querySelector('.eci-check').textContent = '✓';
  }
}

async function exportSelected() {
  if (!selectedClips.size) {
    // Auto-select top clips
    allClips.slice(0, 3).forEach(h => selectedClips.add(h.id));
    if (!selectedClips.size) {
      showToast('⚠️ Select at least one clip to export.', true);
      return;
    }
  }

  const btn = document.getElementById('export-all-btn');
  btn.textContent = '⏳ Exporting…';
  btn.disabled = true;

  let exported = 0;
  let lastDownloadUrl = '';
  
  for (const id of selectedClips) {
    try {
      // Ensure the clip is physically extracted first before exporting
      const h = allClips.find(c => c.id === id);
      if (h && !h.clip_url) {
          await fetch(`${API_BASE}/clips/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ highlight_id: id, vertical: true }),
          });
      }

      const resp = await fetch(`${API_BASE}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          highlight_id: id,
          format: selectedFormat,
          caption_theme: selectedTheme,
          include_captions: document.getElementById('tog-captions').checked,
          include_hook: document.getElementById('tog-hook').checked,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        lastDownloadUrl = data.download_url;
        exported++;
      }
    } catch {}
  }

  btn.textContent = '🚀 Export Selected Clips';
  btn.disabled = false;
  
  if (exported > 0) {
      showToast(`✅ Exported ${exported} clip${exported !== 1 ? 's' : ''} in ${selectedFormat.toUpperCase()} format!`);
      
      // Show success module with download link
      const successDiv = document.getElementById('export-success');
      if (successDiv) {
          successDiv.style.display = 'block';
          const dlBtn = successDiv.querySelector('.btn-primary');
          if (dlBtn && lastDownloadUrl) {
              const fullUrl = lastDownloadUrl.startsWith('http') ? lastDownloadUrl : `http://localhost:8000${lastDownloadUrl}`;
              dlBtn.onclick = async () => {
                dlBtn.textContent = '⏳ Downloading...';
                try {
                  const r = await fetch(fullUrl);
                  const blob = await r.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `AttentionX_Viral_Clip.mp4`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  window.URL.revokeObjectURL(url);
                  dlBtn.textContent = '✅ Downloaded!';
                  setTimeout(() => { dlBtn.textContent = '⬇ Download MP4'; }, 3000);
                } catch (e) {
                  showToast('❌ Failed to download file.', true);
                  dlBtn.textContent = '⬇ Download MP4';
                }
              };
              dlBtn.textContent = '⬇ Download MP4';
          }
      }
  } else {
      showToast('❌ Export failed.', true);
  }
}

/* ══════════════════════════════════════════════════════════════
   DASHBOARD
══════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  let stats;
  try {
    const resp = await fetch(`${API_BASE}/dashboard/stats`);
    if (resp.ok) stats = await resp.json();
  } catch {}

  // Use local data if API not available
  if (!stats) {
    const scores = allClips.map(c => c.virality_score);
    const topics = {};
    allClips.forEach(c => { topics[c.topic] = (topics[c.topic] || 0) + 1; });
    const topTopics = Object.entries(topics).sort((a,b)=>b[1]-a[1]).slice(0,5).map(e=>e[0]);
    stats = {
      total_videos: currentVideoId ? 1 : 0,
      total_clips: allClips.length,
      avg_virality_score: scores.length ? Math.round(scores.reduce((a,b)=>a+b,0)/scores.length) : 0,
      top_topics: topTopics,
    };
  }

  document.getElementById('ds-val-videos').textContent = stats.total_videos || 0;
  document.getElementById('ds-val-clips').textContent = stats.total_clips || 0;
  document.getElementById('ds-val-virality').textContent = (stats.avg_virality_score || 0) + '%';

  renderTopicsChart(stats.top_topics || []);
  renderViralityChart();
  renderTopClips();
}

function renderTopicsChart(topics) {
  const chart = document.getElementById('topics-chart');
  if (!topics.length) {
    chart.innerHTML = '<p class="ec-empty">Run analysis to see topic data.</p>';
    return;
  }

  const total = topics.length;
  chart.innerHTML = topics.map((t, i) => {
    const pct = 100 - i * 15;
    const count = Math.max(1, allClips.filter(c => c.topic === t).length);
    return `
      <div class="topic-row">
        <span class="topic-name">${t}</span>
        <div class="topic-bar-wrap">
          <div class="topic-bar-fill" style="width:${pct}%"></div>
        </div>
        <span class="topic-count">${count}</span>
      </div>
    `;
  }).join('');
}

function renderViralityChart() {
  const chart = document.getElementById('virality-chart');
  const buckets = [
    { label: '90-99', count: 0 },
    { label: '80-89', count: 0 },
    { label: '70-79', count: 0 },
    { label: '60-69', count: 0 },
    { label: '<60',   count: 0 },
  ];

  if (!allClips.length) {
    // Demo data
    buckets[0].count = 2; buckets[1].count = 4; buckets[2].count = 3;
    buckets[3].count = 1; buckets[4].count = 1;
  } else {
    allClips.forEach(c => {
      const s = c.virality_score;
      if (s >= 90) buckets[0].count++;
      else if (s >= 80) buckets[1].count++;
      else if (s >= 70) buckets[2].count++;
      else if (s >= 60) buckets[3].count++;
      else buckets[4].count++;
    });
  }

  const max = Math.max(...buckets.map(b => b.count), 1);
  chart.innerHTML = buckets.map(b => `
    <div class="vc-bar-wrap">
      <div class="vc-bar" style="height:${Math.round((b.count/max)*100)}%" title="${b.count} clips"></div>
      <span class="vc-label">${b.label}%</span>
    </div>
  `).join('');
}

function renderTopClips() {
  const list = document.getElementById('top-clips-list');
  const clips = [...allClips].sort((a,b) => b.virality_score - a.virality_score).slice(0, 5);
  if (!clips.length) {
    list.innerHTML = '<p class="ec-empty">No clips yet. Upload and analyze a video.</p>';
    return;
  }

  list.innerHTML = clips.map((h, i) => {
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    const medals = ['🥇','🥈','🥉','4️⃣','5️⃣'];
    return `
      <div class="top-clip-item">
        <div class="tci-rank ${rankClass}">${medals[i]}</div>
        <div class="tci-info">
          <div class="tci-hook">${h.hook_title}</div>
          <div class="tci-meta">${h.topic} · ${h.duration}s</div>
        </div>
        <div class="tci-score">${h.virality_score}%</div>
      </div>
    `;
  }).join('');
}

/* ══════════════════════════════════════════════════════════════
   DEMO TAB LOGIC (landing page)
══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  // Demo tabs
  document.querySelectorAll('.demo-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.demo-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.demo-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('panel-' + tab.dataset.tab)?.classList.add('active');
      if (tab.dataset.tab === 'analyze') initAnalyzeDemo();
      if (tab.dataset.tab === 'preview') initPreviewDemo();
    });
  });

  // Caption word animation
  initCaptionAnimation();

  // Scroll animations
  initScrollAnimations();

  // Build analyze demo waveform
  buildWaveform('wave-bars', 40);
});

function initCaptionAnimation() {
  const words = document.querySelectorAll('.caption-word');
  let idx = 0;
  setInterval(() => {
    words.forEach(w => w.classList.remove('active'));
    words[idx % words.length].classList.add('active');
    idx++;
  }, 600);
}

function initScrollAnimations() {
  const observer = new IntersectionObserver(
    entries => entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
    }),
    { threshold: 0.15 }
  );

  document.querySelectorAll('.feature-card, .step-card, .testi-card, .price-card').forEach(el => {
    el.classList.add('animate-on-scroll');
    observer.observe(el);
  });
}

function simulateUpload() {
  const zone = document.getElementById('demo-upload-zone');
  const prog = document.getElementById('demo-progress');
  const bar = document.getElementById('demo-prog-bar');
  const text = document.getElementById('demo-prog-text');

  prog.style.display = 'flex';
  let pct = 0;
  const iv = setInterval(() => {
    pct += Math.random() * 15 + 5;
    if (pct >= 100) {
      pct = 100;
      clearInterval(iv);
      text.textContent = '✅ Upload complete!';
      // Auto-switch to analyze tab
      setTimeout(() => {
        document.querySelectorAll('.demo-tab')[2].click(); // preview
      }, 1200);
    }
    bar.style.width = Math.min(100, pct) + '%';
    text.textContent = Math.min(100, Math.round(pct)) + '%';
  }, 120);
}

function initAnalyzeDemo() {
  const steps = document.querySelectorAll('.a-step');
  let i = 0;
  steps.forEach(s => { s.classList.remove('done'); });
  const iv = setInterval(() => {
    if (i >= steps.length) { clearInterval(iv); return; }
    if (i > 0) {
      steps[i-1].classList.remove('pulsing');
      steps[i-1].classList.add('done');
      steps[i-1].textContent = '✅ ' + steps[i-1].textContent.replace('...','');
    }
    steps[i].classList.add('pulsing');
    i++;
  }, 800);

  // Build peak markers
  const peaks = document.getElementById('peak-markers');
  peaks.innerHTML = ['0:42','2:15','5:30','8:10','11:45'].map(t =>
    `<span style="padding:3px 10px;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);border-radius:20px;font-size:12px;color:#ef4444;font-weight:600">🔥 ${t}</span>`
  ).join('');
}

function initPreviewDemo() {
  const container = document.getElementById('clips-preview');
  const demoClips = [
    { score: 94, topic: 'Mindset', hook: 'This will change your life 🔥', time: '0:42' },
    { score: 87, topic: 'Success', hook: 'Nobody talks about this 👀', time: '2:15' },
    { score: 78, topic: 'Productivity', hook: 'Stop this mistake now ⚠️', time: '5:30' },
  ];

  container.innerHTML = demoClips.map(c => `
    <div class="preview-clip-card">
      <div class="pcv-thumb">🎬
        <div class="pcv-badge" style="background:linear-gradient(135deg,#ef4444,#f59e0b);color:white">🔥 ${c.score}%</div>
      </div>
      <div class="pcv-body">
        <h4>${c.hook}</h4>
        <div class="pcv-meta"><span>${c.topic}</span><span>⏱ ${c.time}</span></div>
      </div>
    </div>
  `).join('');
}

function selectFormat(el, fmt) {
  document.querySelectorAll('.ef-card').forEach(e => e.classList.remove('active'));
  el.classList.add('active');
}

function selectTheme(el, theme) {
  document.querySelectorAll('.theme-btn').forEach(e => e.classList.remove('active'));
  el.classList.add('active');
}

async function simulateExport() {
  const btn = document.getElementById('export-btn');
  btn.textContent = '⏳ Processing…';
  btn.disabled = true;
  await delay(2000);
  btn.style.display = 'none';
  document.getElementById('export-success').style.display = 'block';
}

/* ══════════════════════════════════════════════════════════════
   WAVEFORM BUILDER
══════════════════════════════════════════════════════════════ */
function buildWaveform(containerId, count) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const bar = document.createElement('div');
    bar.className = containerId === 'ar-wave-bars' ? 'ar-wave-bar' : 'wave-bar';
    const hue = 270 + Math.random() * 60;
    bar.style.background = `hsl(${hue}, 80%, 60%)`;
    bar.style.animationDelay = `${(i / count) * 1}s`;
    bar.style.animationDuration = `${0.4 + Math.random() * 0.6}s`;
    container.appendChild(bar);
  }
}

/* ══════════════════════════════════════════════════════════════
   TOAST
══════════════════════════════════════════════════════════════ */
let toastTimer = null;
function showToast(msg, isError = false) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.style.background = isError ? 'rgba(239,68,68,0.15)' : 'var(--bg-card2)';
  toast.style.borderColor = isError ? 'rgba(239,68,68,0.3)' : 'var(--border-subtle)';
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

/* ══════════════════════════════════════════════════════════════
   UTILITIES
══════════════════════════════════════════════════════════════ */
function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDuration(secs) {
  secs = Math.round(secs || 0);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  return `${m}:${String(s).padStart(2,'0')}`;
}
