// TalentFlow ATS - Modern Recruiter Workspace Core Engine

let state = {
  currentView: 'table', // 'table', 'kanban', 'analytics'
  jobs: [],
  selectedJobId: '',
  candidates: [],
  pagination: {
    page: 1,
    per_page: 25,
    total: 0,
    total_pages: 1
  },
  filters: {
    stage: 'all',
    min_score: '',
    min_exp: '',
    starred: false,
    search: '',
    sort_by: 'score_desc'
  },
  selectedCandidateIds: new Set(),
  activeCandidate: null,
  activeCandidateIndex: -1,
  activeDrawerTab: 'ai',
  currentRatingValue: 0
};

// ==================== INITIALIZATION & LIFECYCLE ====================

document.addEventListener('DOMContentLoaded', async () => {
  initKeyboardShortcuts();
  await loadJobs();
  await loadCandidates();
  if (state.currentView === 'analytics') {
    loadAnalytics();
  }
});

async function loadJobs() {
  try {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    state.jobs = jobs;

    const selector = document.getElementById('jobSelector');
    const modalJobSelect = document.getElementById('modalJobSelect');
    
    selector.innerHTML = '<option value="">All Requisitions (Overview)</option>';
    modalJobSelect.innerHTML = '';

    jobs.forEach(job => {
      const opt = document.createElement('option');
      opt.value = job.id;
      opt.textContent = `${job.title} (${job.total_candidates || 0} applicants)`;
      selector.appendChild(opt);

      const modalOpt = document.createElement('option');
      modalOpt.value = job.id;
      modalOpt.textContent = job.title;
      modalJobSelect.appendChild(modalOpt);
    });
  } catch (err) {
    showToast('Failed to load job requisitions', 'error');
  }
}

async function loadCandidates() {
  try {
    const params = new URLSearchParams();
    if (state.selectedJobId) params.append('job_id', state.selectedJobId);
    if (state.filters.stage && state.filters.stage !== 'all') params.append('stage', state.filters.stage);
    if (state.filters.min_score) params.append('min_score', state.filters.min_score);
    if (state.filters.min_exp) params.append('min_exp', state.filters.min_exp);
    if (state.filters.starred) params.append('starred', 'true');
    if (state.filters.search) params.append('search', state.filters.search);
    if (state.filters.sort_by) params.append('sort_by', state.filters.sort_by);
    params.append('page', state.pagination.page);
    params.append('per_page', state.pagination.per_page);

    const res = await fetch(`/api/candidates?${params.toString()}`);
    const data = await res.json();

    state.candidates = data.candidates || [];
    state.pagination = data.pagination || state.pagination;

    updateCountsSummary();
    renderTable();
    updatePaginationUI();

    if (state.currentView === 'kanban') {
      await renderKanbanBoard();
    }
  } catch (err) {
    showToast('Failed to load candidate applications', 'error');
  }
}

function updateCountsSummary() {
  const summaryEl = document.getElementById('candidateCountSummary');
  summaryEl.textContent = `${state.pagination.total} Applicants Screened`;
}

// ==================== VIEW SWITCHING ====================

function switchView(viewName) {
  state.currentView = viewName;
  
  // Update view button styling for sidebar navigation
  ['Table', 'Kanban', 'Analytics'].forEach(v => {
    const btn = document.getElementById(`viewTab${v}`);
    const isActive = v.toLowerCase() === viewName;
    if (isActive) {
      btn.className = 'w-full px-3.5 py-2.5 rounded-xl font-semibold text-white bg-slate-800/90 border border-slate-700/80 shadow-sm transition flex items-center gap-3';
      const svg = btn.querySelector('svg');
      if (svg) svg.className = 'w-4 h-4 text-brand-400 shrink-0';
    } else {
      btn.className = 'w-full px-3.5 py-2.5 rounded-xl font-medium text-slate-400 hover:text-white hover:bg-slate-900 transition flex items-center gap-3';
      const svg = btn.querySelector('svg');
      if (svg) svg.className = 'w-4 h-4 text-slate-400 shrink-0';
    }
  });

  // Toggle view containers
  document.getElementById('viewTable').classList.toggle('hidden', viewName !== 'table');
  document.getElementById('viewKanban').classList.toggle('hidden', viewName !== 'kanban');
  document.getElementById('viewAnalytics').classList.toggle('hidden', viewName !== 'analytics');

  if (viewName === 'kanban') {
    renderKanbanBoard();
  } else if (viewName === 'analytics') {
    loadAnalytics();
  }
}

// ==================== TRIAGE TABLE RENDERING (SPACIOUS & ELEGANT) ====================

function renderTable() {
  const tbody = document.getElementById('candidatesTableBody');
  tbody.innerHTML = '';

  if (state.candidates.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" class="py-16 text-center text-slate-500">
          <div class="max-w-sm mx-auto space-y-3">
            <div class="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center mx-auto text-slate-400">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            </div>
            <p class="font-bold text-sm text-slate-300">No applicants match your active criteria</p>
            <p class="text-xs text-slate-400 leading-relaxed">Try clearing search terms, adjusting score thresholds, or click "Reset Demo Data" in the top bar.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  state.candidates.forEach((c, index) => {
    const isSelected = state.selectedCandidateIds.has(c.id);
    const tr = document.createElement('tr');
    tr.className = `border-b border-slate-800/40 hover:bg-slate-800/50 transition cursor-pointer group ${isSelected ? 'bg-brand-950/25' : ''}`;
    
    // Row click opens drawer
    tr.addEventListener('click', (e) => {
      if (e.target.closest('input') || e.target.closest('button') || e.target.closest('select')) return;
      openCandidateDrawer(c.id, index);
    });

    const matchBadgeClass = c.match_score >= 85 ? 'badge-match-high' : (c.match_score >= 70 ? 'badge-match-med' : 'badge-match-low');
    const matchLabel = c.match_score >= 85 ? 'Top Fit' : (c.match_score >= 70 ? 'Strong' : 'Moderate');
    const stageClass = `stage-${c.stage}`;
    const formattedStage = c.stage.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

    const initials = c.name.split(' ').map(n=>n[0]).join('').slice(0, 2);

    tr.innerHTML = `
      <td class="py-4 px-4 text-center">
        <input type="checkbox" ${isSelected ? 'checked' : ''} onchange="toggleSelectCandidate(${c.id}, this.checked)" class="w-4 h-4 rounded bg-slate-800 border-slate-700 text-brand-600 focus:ring-0 cursor-pointer">
      </td>
      <td class="py-4 px-3 text-center">
        <button onclick="toggleStar(${c.id}, event)" class="${c.starred ? 'text-amber-400 scale-110' : 'text-slate-600 hover:text-amber-400'} transition text-base leading-none">
          ★
        </button>
      </td>
      <td class="py-4 px-5">
        <div class="flex items-center space-x-3.5">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-slate-800 to-indigo-950 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-200 uppercase tracking-wider shrink-0 shadow-sm">
            ${initials}
          </div>
          <div class="min-w-0">
            <span class="text-slate-100 font-bold text-xs tracking-tight group-hover:text-brand-300 transition block truncate">${c.name}</span>
            <div class="text-[11px] text-slate-400 flex items-center gap-1.5 mt-0.5 truncate">
              <span>${c.current_title || 'Software Engineer'}</span>
              ${c.current_company ? `<span class="text-slate-600">•</span><span class="text-slate-400 font-medium">${c.current_company}</span>` : ''}
            </div>
          </div>
        </div>
      </td>
      <td class="py-4 px-4">
        <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-mono text-[11px] font-bold ${matchBadgeClass}">
          <span>${c.match_score}%</span>
          <span class="text-[10px] uppercase font-sans font-semibold opacity-90">• ${matchLabel}</span>
        </div>
      </td>
      <td class="py-4 px-4 text-slate-300 max-w-[170px] truncate" title="${c.job_title}">
        <span class="text-xs font-medium text-slate-300">${c.job_title}</span>
      </td>
      <td class="py-4 px-4 font-mono text-xs text-slate-300 whitespace-nowrap">
        <span class="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60">${c.years_of_experience} yrs</span>
      </td>
      <td class="py-4 px-5 max-w-[220px]">
        <div class="flex flex-wrap gap-1.5 overflow-hidden h-6">
          ${(c.skills || []).slice(0, 3).map(s => `<span class="px-2 py-0.5 rounded-md bg-slate-800/90 text-slate-200 text-[11px] font-medium border border-slate-700/80 whitespace-nowrap">${s}</span>`).join('')}
          ${(c.skills || []).length > 3 ? `<span class="text-[10px] text-slate-400 font-mono self-center font-bold">+${(c.skills || []).length - 3}</span>` : ''}
        </div>
      </td>
      <td class="py-4 px-4 whitespace-nowrap">
        <span class="px-2.5 py-1 rounded-lg text-xs font-semibold ${stageClass}">
          ${formattedStage}
        </span>
      </td>
      <td class="py-4 px-4 text-slate-400 text-xs font-mono whitespace-nowrap">
        ${c.applied_at || ''}
      </td>
      <td class="py-4 px-5 text-right space-x-2 whitespace-nowrap">
        <button onclick="openCandidateDrawer(${c.id}, ${index})" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition border border-slate-700 shadow-sm">
          Review
        </button>
        <button onclick="quickAdvance(${c.id}, event)" title="Advance Candidate" class="px-3 py-1.5 rounded-lg bg-brand-600/90 hover:bg-brand-600 text-white transition text-xs font-semibold shadow-sm">
          Advance →
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ==================== KANBAN BOARD RENDERING (SPACIOUS COLUMNS) ====================

const KANBAN_STAGES = [
  { id: 'new', label: 'New / Applied', color: 'border-slate-700/80' },
  { id: 'screening', label: 'Screening', color: 'border-sky-500/40' },
  { id: 'phone_screen', label: 'Phone Screen', color: 'border-indigo-500/40' },
  { id: 'interview', label: 'Technical Interview', color: 'border-purple-500/40' },
  { id: 'offer', label: 'Offer Extended', color: 'border-emerald-500/40' },
  { id: 'rejected', label: 'Rejected', color: 'border-red-500/40' }
];

async function renderKanbanBoard() {
  const container = document.getElementById('kanbanBoardColumns');
  container.innerHTML = '';

  let kanbanCandidates = state.candidates;
  if (state.pagination.total > state.candidates.length) {
    try {
      const params = new URLSearchParams();
      if (state.selectedJobId) params.append('job_id', state.selectedJobId);
      params.append('per_page', '100');
      const res = await fetch(`/api/candidates?${params.toString()}`);
      const data = await res.json();
      kanbanCandidates = data.candidates || [];
    } catch(e) {}
  }

  KANBAN_STAGES.forEach(col => {
    const colCandidates = kanbanCandidates.filter(c => c.stage === col.id);
    const colDiv = document.createElement('div');
    colDiv.className = `w-80 bg-slate-950/80 border ${col.color} rounded-2xl flex flex-col h-full max-h-full overflow-hidden shadow-card`;

    colDiv.innerHTML = `
      <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
        <div class="flex items-center space-x-2.5">
          <span class="text-xs font-bold text-white tracking-wide uppercase font-mono">${col.label}</span>
          <span class="w-6 h-6 rounded-full bg-slate-800 text-slate-200 font-mono text-xs font-bold flex items-center justify-center">${colCandidates.length}</span>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto p-3.5 space-y-3.5" id="kanban-col-${col.id}"></div>
    `;

    const cardsContainer = colDiv.querySelector(`#kanban-col-${col.id}`);
    
    colCandidates.forEach(cand => {
      const card = document.createElement('div');
      card.className = 'bg-slate-900 border border-slate-800 hover:border-brand-500/70 rounded-xl p-4 space-y-2.5 cursor-pointer transition shadow-sm hover:shadow-card-hover';
      card.onclick = () => openCandidateDrawer(cand.id);

      const matchBadgeClass = cand.match_score >= 85 ? 'badge-match-high' : (cand.match_score >= 70 ? 'badge-match-med' : 'badge-match-low');

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-xs text-white hover:text-brand-300 transition">${cand.name}</span>
          <span class="px-2 py-0.5 rounded-full font-mono text-[10px] font-bold ${matchBadgeClass}">${cand.match_score}%</span>
        </div>
        <div class="text-[11px] text-slate-400 truncate">${cand.current_title || 'Engineer'} ${cand.current_company ? '@ ' + cand.current_company : ''}</div>
        <div class="flex flex-wrap gap-1.5">
          ${(cand.skills || []).slice(0, 3).map(s => `<span class="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-[10px] font-medium border border-slate-700/60">${s}</span>`).join('')}
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-slate-800 text-[10px] text-slate-400 font-mono">
          <span>${cand.years_of_experience} yrs exp</span>
          <span>${cand.applied_at}</span>
        </div>
      `;
      cardsContainer.appendChild(card);
    });

    container.appendChild(colDiv);
  });
}

// ==================== CANDIDATE PROFILE DRAWER (SPACIOUS & STRUCTURED) ====================

async function openCandidateDrawer(candidateId, index = -1) {
  try {
    const res = await fetch(`/api/candidates/${candidateId}`);
    const candidate = await res.json();
    state.activeCandidate = candidate;
    state.activeCandidateIndex = index !== -1 ? index : state.candidates.findIndex(c => c.id === candidateId);

    // Populate Header
    const initials = candidate.name.split(' ').map(n=>n[0]).join('').slice(0, 2);
    document.getElementById('drawerAvatarInitials').textContent = initials;
    document.getElementById('drawerCandidateName').textContent = candidate.name;
    document.getElementById('drawerCandidateSubtitle').textContent = `${candidate.current_title || 'Software Engineer'} ${candidate.current_company ? '@ ' + candidate.current_company : ''} • Target: ${candidate.job_title}`;
    
    // Star Status
    updateDrawerStarUI(candidate.starred);

    // Stage dropdown
    document.getElementById('drawerStageSelect').value = candidate.stage;

    // AI Tab
    document.getElementById('drawerMatchScoreVal').textContent = `${candidate.match_score}%`;
    const badgeEl = document.getElementById('drawerMatchBadge');
    badgeEl.className = `text-xs px-3 py-1 rounded-full font-bold ${candidate.match_score >= 85 ? 'badge-match-high' : (candidate.match_score >= 70 ? 'badge-match-med' : 'badge-match-low')}`;
    badgeEl.textContent = candidate.match_score >= 85 ? 'Top Tier Match' : (candidate.match_score >= 70 ? 'Strong Fit' : 'Moderate Match');
    document.getElementById('drawerAIHeadline').textContent = candidate.ai_headline || '';

    // Pros
    const prosList = document.getElementById('drawerProsList');
    prosList.innerHTML = (candidate.ai_pros || []).map(p => `
      <li class="flex items-start gap-2.5 p-2 rounded-xl bg-slate-950/40 border border-emerald-950/50">
        <span class="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">✓</span>
        <span>${p}</span>
      </li>
    `).join('');

    // Cons
    const consList = document.getElementById('drawerConsList');
    consList.innerHTML = (candidate.ai_cons || []).map(c => `
      <li class="flex items-start gap-2.5 p-2 rounded-xl bg-slate-950/40 border border-amber-950/50">
        <span class="w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">!</span>
        <span>${c}</span>
      </li>
    `).join('');

    // Questions
    const questionsList = document.getElementById('drawerQuestionsList');
    questionsList.innerHTML = (candidate.ai_questions || []).map((q, idx) => `
      <li class="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
        <span class="font-mono text-xs text-brand-400 font-bold block">Interview Question ${idx+1}</span>
        <p class="text-slate-200 text-xs leading-relaxed font-medium">${q}</p>
      </li>
    `).join('');

    // Quick Metadata
    document.getElementById('drawerEmailLink').textContent = candidate.email;
    document.getElementById('drawerEmailLink').href = `mailto:${candidate.email}`;
    document.getElementById('drawerPhone').textContent = candidate.phone || 'N/A';
    document.getElementById('drawerLocation').textContent = candidate.location || 'Remote';
    document.getElementById('drawerExp').textContent = `${candidate.years_of_experience} years professional experience`;
    document.getElementById('drawerEducation').textContent = candidate.education || 'N/A';

    // Resume Tab (Structured Formatted View)
    renderFormattedResume(candidate);

    // Notes Tab
    document.getElementById('drawerNotesCount').textContent = (candidate.notes || []).length;
    renderDrawerNotes(candidate.notes || []);

    // Activity Tab
    renderDrawerActivity(candidate.activity_logs || []);

    // Slide in
    const drawer = document.getElementById('candidateDrawer');
    drawer.classList.remove('hidden', 'translate-x-full');
    drawer.classList.add('translate-x-0');
  } catch (err) {
    showToast('Failed to open candidate profile', 'error');
  }
}

function renderFormattedResume(candidate) {
  const container = document.getElementById('drawerFormattedResume');
  const raw = candidate.raw_resume || '';

  container.innerHTML = `
    <!-- Executive Header Card -->
    <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-card space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-white">${candidate.name}</h3>
        <span class="px-2.5 py-1 rounded-lg bg-brand-500/20 text-brand-300 font-mono text-xs font-semibold">${candidate.years_of_experience} Years Exp</span>
      </div>
      <p class="text-xs text-slate-300 font-medium">${candidate.current_title} @ <strong class="text-white">${candidate.current_company}</strong></p>
      <div class="pt-2 border-t border-slate-800 flex flex-wrap gap-2">
        <span class="px-2 py-1 rounded bg-slate-950 text-slate-400 text-xs">📍 ${candidate.location}</span>
        <span class="px-2 py-1 rounded bg-slate-950 text-slate-400 text-xs">✉️ ${candidate.email}</span>
        <span class="px-2 py-1 rounded bg-slate-950 text-slate-400 text-xs">🎓 ${candidate.education}</span>
      </div>
    </div>

    <!-- Technical Stack Card -->
    <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-card space-y-3">
      <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">Verified Skills & Tools</h4>
      <div class="flex flex-wrap gap-2">
        ${(candidate.skills || []).map(s => `
          <span class="px-3 py-1 rounded-xl bg-slate-950 border border-slate-700 text-slate-200 text-xs font-medium">${s}</span>
        `).join('')}
      </div>
    </div>

    <!-- Career Experience Narrative Card -->
    <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-card space-y-4">
      <h4 class="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">Resume Document Overview</h4>
      <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
        ${raw}
      </div>
    </div>
  `;
}

function closeDrawer() {
  const drawer = document.getElementById('candidateDrawer');
  drawer.classList.remove('translate-x-0');
  drawer.classList.add('translate-x-full');
  setTimeout(() => {
    drawer.classList.add('hidden');
    state.activeCandidate = null;
  }, 200);
}

function navigateDrawer(direction) {
  if (state.candidates.length === 0) return;
  let newIndex = state.activeCandidateIndex + direction;
  if (newIndex < 0) newIndex = state.candidates.length - 1;
  if (newIndex >= state.candidates.length) newIndex = 0;

  const nextCand = state.candidates[newIndex];
  if (nextCand) {
    openCandidateDrawer(nextCand.id, newIndex);
  }
}

function switchDrawerTab(tabName) {
  state.activeDrawerTab = tabName;
  ['ai', 'resume', 'notes', 'activity'].forEach(t => {
    const btn = document.getElementById(`drawerTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const content = document.getElementById(`drawerContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (t === tabName) {
      btn.className = 'py-3 px-4 font-bold text-brand-400 border-b-2 border-brand-500 transition flex items-center gap-2';
      content.classList.remove('hidden');
    } else {
      btn.className = 'py-3 px-4 font-semibold text-slate-400 hover:text-white transition flex items-center gap-2';
      content.classList.add('hidden');
    }
  });
}

function updateDrawerStarUI(isStarred) {
  const icon = document.getElementById('drawerStarIcon');
  if (isStarred) {
    icon.classList.add('text-amber-400', 'fill-amber-400');
    icon.classList.remove('text-slate-500');
  } else {
    icon.classList.remove('text-amber-400', 'fill-amber-400');
    icon.classList.add('text-slate-500');
  }
}

async function toggleDrawerStar() {
  if (!state.activeCandidate) return;
  await toggleStar(state.activeCandidate.id);
  state.activeCandidate.starred = !state.activeCandidate.starred;
  updateDrawerStarUI(state.activeCandidate.starred);
}

async function onDrawerStageChange() {
  if (!state.activeCandidate) return;
  const newStage = document.getElementById('drawerStageSelect').value;
  await updateCandidateStage(state.activeCandidate.id, newStage);
}

async function drawerAdvanceStage() {
  if (!state.activeCandidate) return;
  const stageFlow = ['new', 'screening', 'phone_screen', 'interview', 'offer', 'hired'];
  const curIdx = stageFlow.indexOf(state.activeCandidate.stage);
  if (curIdx >= 0 && curIdx < stageFlow.length - 1) {
    const nextStage = stageFlow[curIdx + 1];
    document.getElementById('drawerStageSelect').value = nextStage;
    await updateCandidateStage(state.activeCandidate.id, nextStage);
    showToast(`Advanced to ${nextStage.replace('_', ' ')}`, 'success');
  } else {
    showToast('Candidate is already at latest stage', 'info');
  }
}

async function drawerRejectCandidate() {
  if (!state.activeCandidate) return;
  document.getElementById('drawerStageSelect').value = 'rejected';
  await updateCandidateStage(state.activeCandidate.id, 'rejected', 'Candidate rejected during review');
  showToast('Candidate marked as rejected', 'info');
}

async function rescoreCurrentCandidate() {
  if (!state.activeCandidate) return;
  try {
    const res = await fetch(`/api/candidates/${state.activeCandidate.id}/rescore`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Candidate rescored against requisition', 'success');
      await openCandidateDrawer(state.activeCandidate.id, state.activeCandidateIndex);
      loadCandidates();
    }
  } catch (err) {
    showToast('Failed to rescore candidate', 'error');
  }
}

// ==================== CANDIDATE ACTIONS ====================

async function updateCandidateStage(candidateId, newStage, note = '') {
  try {
    const res = await fetch(`/api/candidates/${candidateId}/stage`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage: newStage, note, actor: 'Recruiter' })
    });
    const data = await res.json();
    if (data.success) {
      await loadCandidates();
      if (state.activeCandidate && state.activeCandidate.id === candidateId) {
        state.activeCandidate.stage = newStage;
      }
    }
  } catch (err) {
    showToast('Failed to update stage', 'error');
  }
}

async function quickAdvance(candidateId, event) {
  event.stopPropagation();
  const cand = state.candidates.find(c => c.id === candidateId);
  if (!cand) return;
  const stageFlow = ['new', 'screening', 'phone_screen', 'interview', 'offer', 'hired'];
  const curIdx = stageFlow.indexOf(cand.stage);
  if (curIdx >= 0 && curIdx < stageFlow.length - 1) {
    await updateCandidateStage(candidateId, stageFlow[curIdx + 1]);
    showToast(`Moved ${cand.name} to ${stageFlow[curIdx + 1].replace('_', ' ')}`, 'success');
  }
}

async function quickReject(candidateId, event) {
  event.stopPropagation();
  const cand = state.candidates.find(c => c.id === candidateId);
  if (!cand) return;
  await updateCandidateStage(candidateId, 'rejected');
  showToast(`Moved ${cand.name} to Rejected`, 'info');
}

async function toggleStar(candidateId, event) {
  if (event) event.stopPropagation();
  try {
    const res = await fetch(`/api/candidates/${candidateId}/star`, { method: 'PATCH' });
    const data = await res.json();
    if (data.success) {
      const c = state.candidates.find(cand => cand.id === candidateId);
      if (c) c.starred = data.starred;
      renderTable();
    }
  } catch (err) {
    showToast('Failed to toggle star', 'error');
  }
}

// ==================== NOTES & RATINGS ====================

function setNoteRating(stars) {
  state.currentRatingValue = stars;
  const buttons = document.querySelectorAll('#starRatingSelect button');
  buttons.forEach((btn, idx) => {
    if (idx < stars) {
      btn.className = 'star-rating text-amber-400 text-lg transition';
    } else {
      btn.className = 'star-rating text-slate-600 hover:text-amber-400 text-lg transition';
    }
  });
}

async function submitCandidateNote() {
  if (!state.activeCandidate) return;
  const textInput = document.getElementById('noteTextInput');
  const text = textInput.value.trim();
  if (!text) {
    showToast('Please enter note text', 'error');
    return;
  }

  const category = document.getElementById('noteCategorySelect').value;
  try {
    const res = await fetch(`/api/candidates/${state.activeCandidate.id}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        category,
        rating: state.currentRatingValue || null,
        author: 'Sarah Jenkins (Recruiter)'
      })
    });
    const data = await res.json();
    if (data.success) {
      textInput.value = '';
      setNoteRating(0);
      showToast('Note added to candidate scorecard', 'success');
      await openCandidateDrawer(state.activeCandidate.id, state.activeCandidateIndex);
    }
  } catch (err) {
    showToast('Failed to save note', 'error');
  }
}

function renderDrawerNotes(notes) {
  const container = document.getElementById('drawerNotesList');
  if (notes.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 italic py-4 text-center">No review notes recorded yet for this applicant.</p>';
    return;
  }
  container.innerHTML = notes.map(n => `
    <div class="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2.5 text-xs shadow-card">
      <div class="flex items-center justify-between">
        <span class="font-bold text-slate-200 text-xs">${n.author}</span>
        <span class="text-[11px] text-slate-500 font-mono">${n.created_at}</span>
      </div>
      <div class="flex items-center gap-2.5">
        <span class="px-2 py-0.5 rounded-md bg-slate-950 text-brand-300 font-mono text-[10px] font-semibold border border-slate-800">${n.category}</span>
        ${n.rating ? `<span class="text-amber-400 font-bold">${'★'.repeat(n.rating)}</span>` : ''}
      </div>
      <p class="text-slate-300 leading-relaxed font-normal">${n.text}</p>
    </div>
  `).join('');
}

function renderDrawerActivity(activities) {
  const container = document.getElementById('drawerActivityTimeline');
  if (activities.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 italic py-4">No audit activity logged yet.</p>';
    return;
  }
  container.innerHTML = activities.map(a => `
    <div class="relative pb-5">
      <span class="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-brand-500 ring-4 ring-slate-950"></span>
      <div class="flex items-center justify-between">
        <span class="font-bold text-white text-xs">${a.action}</span>
        <span class="text-[11px] text-slate-500 font-mono">${a.timestamp}</span>
      </div>
      <p class="text-slate-400 text-xs mt-1">${a.details || ''} • <span class="text-slate-500 font-medium">${a.actor}</span></p>
    </div>
  `).join('');
}

// ==================== BULK OPERATIONS ====================

function toggleSelectCandidate(candidateId, isChecked) {
  if (isChecked) {
    state.selectedCandidateIds.add(candidateId);
  } else {
    state.selectedCandidateIds.delete(candidateId);
  }
  updateBulkToolbar();
}

function toggleSelectAllPage(isChecked) {
  state.candidates.forEach(c => {
    if (isChecked) {
      state.selectedCandidateIds.add(c.id);
    } else {
      state.selectedCandidateIds.delete(c.id);
    }
  });
  renderTable();
  updateBulkToolbar();
}

function selectAllAcrossPages() {
  state.candidates.forEach(c => state.selectedCandidateIds.add(c.id));
  renderTable();
  updateBulkToolbar();
  showToast(`Selected all ${state.selectedCandidateIds.size} visible candidates`, 'info');
}

function clearSelection() {
  state.selectedCandidateIds.clear();
  const selectAll = document.getElementById('selectAllCheckbox');
  if (selectAll) selectAll.checked = false;
  renderTable();
  updateBulkToolbar();
}

function updateBulkToolbar() {
  const bar = document.getElementById('bulkActionBar');
  const badge = document.getElementById('selectedCountBadge');
  const count = state.selectedCandidateIds.size;
  badge.textContent = count;
  if (count > 0) {
    bar.classList.remove('hidden');
  } else {
    bar.classList.add('hidden');
  }
}

async function executeBulkStageMove() {
  const ids = Array.from(state.selectedCandidateIds);
  if (ids.length === 0) return;
  const stage = document.getElementById('bulkStageSelect').value;

  try {
    const res = await fetch('/api/candidates/bulk-stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_ids: ids, stage })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Bulk updated ${data.updated_count} candidates to ${stage.replace('_', ' ')}`, 'success');
      clearSelection();
      await loadCandidates();
    }
  } catch (err) {
    showToast('Failed bulk stage transition', 'error');
  }
}

async function executeBulkReject() {
  const ids = Array.from(state.selectedCandidateIds);
  if (ids.length === 0) return;
  if (!confirm(`Are you sure you want to reject ${ids.length} selected candidates?`)) return;

  try {
    const res = await fetch('/api/candidates/bulk-reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_ids: ids, reason: 'High volume screening disposition' })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Bulk rejected ${data.rejected_count} candidates`, 'info');
      clearSelection();
      await loadCandidates();
    }
  } catch (err) {
    showToast('Failed bulk rejection', 'error');
  }
}

function openBulkEmailModal() {
  const count = state.selectedCandidateIds.size;
  if (count === 0) return;
  document.getElementById('bulkEmailCountBadge').textContent = `${count} recipients`;
  onEmailTemplateChange();
  document.getElementById('bulkEmailModal').classList.remove('hidden');
}

function closeBulkEmailModal() {
  document.getElementById('bulkEmailModal').classList.add('hidden');
}

function onEmailTemplateChange() {
  const tpl = document.getElementById('bulkEmailTemplateSelect').value;
  const subj = document.getElementById('bulkEmailSubject');
  const body = document.getElementById('bulkEmailBody');

  if (tpl === 'interview_invite') {
    subj.value = 'Invitation to Interview — TalentFlow Engineering Team';
    body.value = `Hi {{name}},\n\nThank you for applying to the {{job_title}} role at our company. Your profile stood out, and we would love to invite you to an introductory 25-minute conversation with our team.\n\nPlease reply with your availability over the next few days.\n\nBest regards,\nSarah Jenkins\nSenior Technical Recruiter`;
  } else if (tpl === 'technical_invite') {
    subj.value = 'Next Steps: Technical Deep-Dive Session';
    body.value = `Hi {{name}},\n\nFollowing up on our initial chat, we are thrilled to invite you to the technical architecture round for {{job_title}}.\n\nWe look forward to speaking soon!\n\nBest,\nRecruiting Team`;
  } else if (tpl === 'rejection') {
    subj.value = 'Update regarding your application for {{job_title}}';
    body.value = `Dear {{name}},\n\nThank you for your interest in {{job_title}}. While your background is impressive, we have decided to proceed with other candidates whose experience aligns more closely with our current requirements.\n\nWe wish you all the best in your search.\n\nWarm regards,\nTalent Acquisition`;
  }
}

async function executeBulkEmailSend() {
  const ids = Array.from(state.selectedCandidateIds);
  if (ids.length === 0) return;
  const template = document.getElementById('bulkEmailTemplateSelect').value;
  const subject = document.getElementById('bulkEmailSubject').value;
  const body = document.getElementById('bulkEmailBody').value;

  try {
    const res = await fetch('/api/candidates/bulk-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidate_ids: ids, template, subject, body })
    });
    const data = await res.json();
    if (data.success) {
      closeBulkEmailModal();
      clearSelection();
      showToast(`Dispatched ${data.sent_count} automated candidate notifications`, 'success');
      loadCandidates();
    }
  } catch (err) {
    showToast('Failed to dispatch bulk emails', 'error');
  }
}

// ==================== FILTERING & PAGINATION ====================

function onJobChange() {
  state.selectedJobId = document.getElementById('jobSelector').value;
  state.pagination.page = 1;
  loadCandidates();
  if (state.currentView === 'analytics') loadAnalytics();
}

let searchDebounceTimeout = null;
function handleSearchInput(e) {
  clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(() => {
    state.filters.search = e.target.value.trim();
    state.pagination.page = 1;
    loadCandidates();
  }, 250);
}

function onFilterChange() {
  state.filters.stage = document.getElementById('stageFilter').value;
  state.filters.min_score = document.getElementById('scoreFilter').value;
  state.filters.min_exp = document.getElementById('expFilter').value;
  state.filters.sort_by = document.getElementById('sortFilter').value;
  state.pagination.page = 1;
  loadCandidates();
}

function toggleStarredFilter() {
  state.filters.starred = !state.filters.starred;
  const btn = document.getElementById('starredToggleBtn');
  if (state.filters.starred) {
    btn.className = 'px-3.5 py-2.5 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 transition flex items-center gap-1.5 font-semibold';
  } else {
    btn.className = 'px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-amber-400 transition flex items-center gap-1.5 font-medium shadow-sm';
  }
  state.pagination.page = 1;
  loadCandidates();
}

function onPerPageChange() {
  state.pagination.per_page = parseInt(document.getElementById('perPageSelect').value, 10);
  state.pagination.page = 1;
  loadCandidates();
}

function changePage(delta) {
  const newPage = state.pagination.page + delta;
  if (newPage >= 1 && newPage <= state.pagination.total_pages) {
    state.pagination.page = newPage;
    loadCandidates();
  }
}

function updatePaginationUI() {
  const prevBtn = document.getElementById('prevPageBtn');
  const nextBtn = document.getElementById('nextPageBtn');
  const indicator = document.getElementById('currentPageIndicator');
  const rangeText = document.getElementById('paginationRangeText');

  const start = state.pagination.total === 0 ? 0 : (state.pagination.page - 1) * state.pagination.per_page + 1;
  const end = Math.min(state.pagination.total, state.pagination.page * state.pagination.per_page);

  indicator.textContent = `Page ${state.pagination.page} / ${state.pagination.total_pages}`;
  rangeText.textContent = `Showing ${start}-${end} of ${state.pagination.total}`;

  prevBtn.disabled = !state.pagination.has_prev;
  nextBtn.disabled = !state.pagination.has_next;
}

// ==================== ANALYTICS VIEW ====================

async function loadAnalytics() {
  try {
    const params = new URLSearchParams();
    if (state.selectedJobId) params.append('job_id', state.selectedJobId);
    const res = await fetch(`/api/analytics?${params.toString()}`);
    const data = await res.json();

    document.getElementById('statTotalApplicants').textContent = data.total_candidates;
    document.getElementById('statAvgMatchScore').textContent = `${data.avg_match_score}%`;
    document.getElementById('statHighMatchCount').textContent = data.score_distribution["90-100% (Top Match)"] || 0;
    
    const interviewCount = (data.stages_funnel.find(s=>s.stage==='interview')||{}).count || 0;
    const offerCount = (data.stages_funnel.find(s=>s.stage==='offer')||{}).count || 0;
    document.getElementById('statAdvancedCount').textContent = interviewCount + offerCount;

    // Funnel bars
    const funnelContainer = document.getElementById('pipelineFunnelBars');
    const maxFunnel = Math.max(...data.stages_funnel.map(s => s.count), 1);
    funnelContainer.innerHTML = data.stages_funnel.map(s => {
      const pct = Math.round((s.count / maxFunnel) * 100);
      return `
        <div class="space-y-1.5">
          <div class="flex justify-between text-xs">
            <span class="text-slate-200 font-semibold">${s.label}</span>
            <span class="font-mono text-slate-400 font-medium">${s.count} candidates</span>
          </div>
          <div class="w-full bg-slate-900 rounded-full h-3 overflow-hidden border border-slate-800">
            <div class="bg-gradient-to-r from-brand-600 to-indigo-500 h-3 rounded-full transition-all duration-700 shadow-sm" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    }).join('');

    // Score breakdown bars
    const scoreContainer = document.getElementById('scoreDistributionBars');
    const maxScoreBucket = Math.max(...Object.values(data.score_distribution), 1);
    scoreContainer.innerHTML = Object.entries(data.score_distribution).map(([bucket, count]) => {
      const pct = Math.round((count / maxScoreBucket) * 100);
      return `
        <div class="space-y-1.5">
          <div class="flex justify-between text-xs">
            <span class="text-slate-200 font-semibold">${bucket}</span>
            <span class="font-mono text-slate-400 font-medium">${count}</span>
          </div>
          <div class="w-full bg-slate-900 rounded-full h-3 overflow-hidden border border-slate-800">
            <div class="bg-gradient-to-r from-indigo-500 to-violet-500 h-3 rounded-full transition-all duration-700 shadow-sm" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    }).join('');

    // Top skills
    const skillsContainer = document.getElementById('topSkillsPills');
    skillsContainer.innerHTML = (data.top_skills || []).map(s => `
      <span class="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 font-mono flex items-center gap-2 shadow-sm">
        <span>${s.skill}</span>
        <span class="px-2 py-0.5 rounded-md bg-slate-800 text-brand-300 text-[10px] font-bold border border-slate-700">${s.count}</span>
      </span>
    `).join('');

  } catch (err) {
    showToast('Failed to load analytics', 'error');
  }
}

// ==================== CSV EXPORT & DEMO RESET ====================

function exportCurrentCSV() {
  const params = new URLSearchParams();
  if (state.selectedJobId) params.append('job_id', state.selectedJobId);
  if (state.filters.stage && state.filters.stage !== 'all') params.append('stage', state.filters.stage);
  window.location.href = `/api/export?${params.toString()}`;
  showToast('Generating CSV export...', 'info');
}

async function confirmResetDemo() {
  if (!confirm('Re-seed 120+ realistic applicants across all positions?')) return;
  try {
    const res = await fetch('/api/reset-demo', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      await loadJobs();
      await loadCandidates();
    }
  } catch (err) {
    showToast('Failed to reset demo data', 'error');
  }
}

// ==================== ADD CANDIDATE MODAL ====================

function openNewCandidateModal() {
  document.getElementById('newCandidateModal').classList.remove('hidden');
}

function closeNewCandidateModal() {
  document.getElementById('newCandidateModal').classList.add('hidden');
}

async function submitNewCandidate() {
  const jobId = document.getElementById('modalJobSelect').value;
  const name = document.getElementById('modalCandName').value.trim();
  const email = document.getElementById('modalCandEmail').value.trim();
  const title = document.getElementById('modalCandTitle').value.trim();
  const exp = document.getElementById('modalCandExp').value;
  const skills = document.getElementById('modalCandSkills').value.split(',').map(s=>s.trim()).filter(Boolean);
  const resume = document.getElementById('modalCandResume').value.trim();

  if (!jobId || !name || !email) {
    showToast('Job, name, and email are required', 'error');
    return;
  }

  try {
    const res = await fetch('/api/candidates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: parseInt(jobId, 10),
        name,
        email,
        current_title: title,
        years_of_experience: parseFloat(exp) || 2,
        skills,
        raw_resume: resume
      })
    });
    const candidate = await res.json();
    if (res.ok) {
      closeNewCandidateModal();
      showToast(`Applicant ${name} scored ${candidate.match_score}%!`, 'success');
      await loadCandidates();
      openCandidateDrawer(candidate.id);
    } else {
      showToast(candidate.error || 'Failed to add applicant', 'error');
    }
  } catch (err) {
    showToast('Failed to add candidate', 'error');
  }
}

// ==================== KEYBOARD SHORTCUTS ====================

function initKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea') {
      if (e.key === 'Escape') {
        document.activeElement.blur();
      }
      return;
    }

    if (e.key === '/') {
      e.preventDefault();
      const searchInput = document.getElementById('searchInput');
      searchInput.focus();
      searchInput.select();
    } else if (e.key === 'j' || e.key === 'J') {
      if (state.activeCandidate) {
        e.preventDefault();
        navigateDrawer(1);
      }
    } else if (e.key === 'k' || e.key === 'K') {
      if (state.activeCandidate) {
        e.preventDefault();
        navigateDrawer(-1);
      }
    } else if (e.key === 'a' || e.key === 'A') {
      if (state.activeCandidate) {
        e.preventDefault();
        drawerAdvanceStage();
      }
    } else if (e.key === 'r' || e.key === 'R') {
      if (state.activeCandidate) {
        e.preventDefault();
        drawerRejectCandidate();
      }
    } else if (e.key === 's' || e.key === 'S') {
      if (state.activeCandidate) {
        e.preventDefault();
        toggleDrawerStar();
      }
    } else if (e.key === 'Escape') {
      closeDrawer();
      closeNewCandidateModal();
      closeBulkEmailModal();
      toggleKeyboardModal(false);
    } else if (e.key === '?') {
      toggleKeyboardModal();
    }
  });
}

function toggleKeyboardModal(forceState) {
  const modal = document.getElementById('keyboardModal');
  if (typeof forceState === 'boolean') {
    modal.classList.toggle('hidden', !forceState);
  } else {
    modal.classList.toggle('hidden');
  }
}

// ==================== TOAST NOTIFICATIONS ====================

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-950/90 border-emerald-700/80 text-emerald-100 shadow-emerald-950/50' :
             type === 'error' ? 'bg-red-950/90 border-red-700/80 text-red-100 shadow-red-950/50' :
             'bg-slate-900/90 border-slate-700/80 text-slate-100 shadow-slate-950/50';

  toast.className = `${bg} border shadow-2xl rounded-2xl px-5 py-3 text-xs font-semibold flex items-center space-x-2.5 backdrop-blur-md animate-fade-in pointer-events-auto ring-1 ring-white/10`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}
