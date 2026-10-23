/**
 * Dashboard Controller para la Software Factory.
 * Maneja el estado en vivo, la navegación de artefactos, el renderizado de Markdown/Mermaid
 * y la inspección profunda de ramas Git.
 */

// Inicializar Mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    darkMode: true,
    background: '#060911',
    primaryColor: '#6366f1',
    primaryTextColor: '#fff',
    primaryBorderColor: '#818cf8',
    lineColor: '#94a3b8',
    secondaryColor: '#0f172a',
    tertiaryColor: '#1e293b'
  }
});

const state = {
  mode: 'workspace', // 'workspace' o 'git'
  selectedBranch: null,
  selectedArtifact: 'discovery_notes',
  viewMode: 'rendered', // 'rendered' o 'raw'
  rawContent: '',
  branches: [],
  activeProject: null,
};

// --- Mapeo de Nombres de Artefactos ---
const ARTIFACT_NAMES = {
  discovery_notes: 'DISCOVERY_NOTES.md (Fase 0)',
  prd: 'PRD.md (Fase 1: PM)',
  system_design: 'SYSTEM_DESIGN.md (Fase 2: Arquitecto)',
  tasks: 'TASKS.md (Fase 2: Tareas)',
  change_plan: 'CHANGE_PLAN.md (Fase 3: Plan)',
  patch: 'model.patch (Fase 3: Código)',
  qa_report: 'QA_REPORT.md (Fase 4: QA)',
};

// --- Elementos DOM ---
const dom = {
  activeProjectName: document.getElementById('active-project-name'),
  activeProjectStatus: document.getElementById('active-project-status'),
  branchCount: document.getElementById('branch-count'),
  branchList: document.getElementById('branch-list'),
  gitBranchesSection: document.getElementById('git-branches-section'),
  workspaceFilesList: document.getElementById('workspace-files-list'),
  toggleWorkspace: document.getElementById('toggle-workspace'),
  toggleGit: document.getElementById('toggle-git'),
  artifactItems: document.querySelectorAll('.artifact-item'),
  stepCards: document.querySelectorAll('.step-card'),
  bcFilename: document.getElementById('bc-filename'),
  bcOrigin: document.querySelector('.bc-origin'),
  markdownView: document.getElementById('markdown-view'),
  rawView: document.getElementById('raw-view'),
  rawCode: document.getElementById('raw-code'),
  btnViewRendered: document.getElementById('btn-view-rendered'),
  btnViewRaw: document.getElementById('btn-view-raw'),
  btnCopy: document.getElementById('btn-copy-content'),
  gitBranchBanner: document.getElementById('git-branch-banner'),
  bannerBranchName: document.getElementById('banner-branch-name'),
  btnRestoreBranch: document.getElementById('btn-restore-branch'),
  // Modales
  modalGrill: document.getElementById('modal-grill'),
  btnOpenGrill: document.getElementById('btn-open-grill'),
  btnCloseGrill: document.getElementById('btn-close-grill'),
  btnCancelGrill: document.getElementById('btn-cancel-grill'),
  btnSubmitGrill: document.getElementById('btn-submit-grill'),
  modalReset: document.getElementById('modal-reset'),
  btnOpenReset: document.getElementById('btn-open-reset'),
  btnCloseReset: document.getElementById('btn-close-reset'),
  btnCancelReset: document.getElementById('btn-cancel-reset'),
  btnConfirmReset: document.getElementById('btn-confirm-reset'),
  btnExportApp: document.getElementById('btn-export-app'),
  toastContainer: document.getElementById('toast-container'),
};

// --- Notificaciones Toast ---
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  dom.toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// --- Carga Inicial de Estado ---
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    state.activeProject = data.project_metadata;

    dom.activeProjectName.textContent = data.project_metadata.project_name || 'Sin Proyecto';
    const status = data.project_metadata.status || 'INITIALIZED';
    dom.activeProjectStatus.textContent = status;
    dom.activeProjectStatus.className = `pill-status badge-${status.toLowerCase()}`;

    // Actualizar Badges de las 5 Etapas en el Stepper
    updateStepperBadges(data.artifacts_status);

    // Actualizar lista de archivos en Workspace
    renderWorkspaceFiles(data.workspace_files);
  } catch (err) {
    console.error('Error cargando estado:', err);
  }
}

function updateStepperBadges(artifacts) {
  const steps = [
    { id: 'badge-discovery', exists: artifacts.discovery_notes },
    { id: 'badge-prd', exists: artifacts.prd },
    { id: 'badge-system_design', exists: artifacts.system_design },
    { id: 'badge-patch', exists: artifacts.patch },
    { id: 'badge-qa_report', exists: artifacts.qa_report },
  ];

  steps.forEach(s => {
    const el = document.getElementById(s.id);
    if (el) {
      el.textContent = s.exists ? 'Completado' : 'Pendiente';
      el.className = `step-status-badge ${s.exists ? 'badge-approved' : 'badge-pending'}`;
    }
  });
}

function renderWorkspaceFiles(files) {
  dom.workspaceFilesList.innerHTML = '';
  if (!files || files.length === 0) {
    dom.workspaceFilesList.innerHTML = '<li class="empty-state-small">Workspace limpio (0 archivos)</li>';
    return;
  }
  files.forEach(f => {
    const li = document.createElement('li');
    li.textContent = `📄 ${f}`;
    dom.workspaceFilesList.appendChild(li);
  });
}

// --- Carga de Ramas Git ---
async function loadGitOverview() {
  try {
    const res = await fetch('/api/git/overview');
    const data = await res.json();
    state.branches = data.branches;
    dom.branchCount.textContent = data.branches.length;

    dom.branchList.innerHTML = '';
    data.branches.forEach(b => {
      const card = document.createElement('div');
      card.className = `branch-card ${b.name === state.selectedBranch ? 'active' : ''}`;
      card.innerHTML = `
        <div class="branch-header">
          <span class="branch-title">${b.name}</span>
          <span class="branch-date">${b.date}</span>
        </div>
        <div class="branch-commit">#${b.commit}: ${b.subject}</div>
      `;
      card.addEventListener('click', () => selectGitBranch(b.name));
      dom.branchList.appendChild(card);
    });
  } catch (err) {
    console.error('Error cargando ramas:', err);
  }
}

// --- Selección de Artefacto y Carga de Contenido ---
async function loadArtifactContent(artifactKey) {
  state.selectedArtifact = artifactKey;
  dom.bcFilename.textContent = ARTIFACT_NAMES[artifactKey] || artifactKey;

  // Actualizar clase activa en sidebar
  dom.artifactItems.forEach(el => {
    el.classList.toggle('active', el.dataset.artifact === artifactKey);
  });

  try {
    let content = '';
    if (state.mode === 'workspace') {
      dom.bcOrigin.textContent = 'Workspace Activo';
      const res = await fetch(`/api/artifacts/${artifactKey}`);
      if (!res.ok) {
        throw new Error(`Artefacto '${artifactKey}' aún no ha sido generado en esta etapa.`);
      }
      const data = await res.json();
      content = data.content;
    } else {
      // Modo Git Branch
      dom.bcOrigin.textContent = `Git: ${state.selectedBranch}`;
      const res = await fetch(`/api/git/branch/${encodeURIComponent(state.selectedBranch)}/artifacts`);
      if (!res.ok) {
        throw new Error(`No se encontraron artefactos en la rama '${state.selectedBranch}'.`);
      }
      const data = await res.json();
      content = data.artifacts[artifactKey] || `El archivo ${artifactKey} no existe en esta rama.`;
    }

    state.rawContent = content;
    renderContent(content);
  } catch (err) {
    renderEmptyState(err.message);
  }
}

function renderContent(markdownText) {
  dom.rawCode.textContent = markdownText;

  if (state.viewMode === 'rendered') {
    dom.rawView.classList.add('hidden');
    dom.markdownView.classList.remove('hidden');

    // Parsear Markdown
    dom.markdownView.innerHTML = marked.parse(markdownText);

    // Buscar y renderizar bloques Mermaid
    const codeBlocks = dom.markdownView.querySelectorAll('code.language-mermaid');
    codeBlocks.forEach((codeEl, idx) => {
      const preEl = codeEl.parentElement;
      const mermaidDiv = document.createElement('div');
      mermaidDiv.className = 'mermaid';
      mermaidDiv.textContent = codeEl.textContent;
      preEl.parentNode.replaceChild(mermaidDiv, preEl);
    });

    try {
      mermaid.run({ querySelector: '.mermaid' });
    } catch (e) {
      console.warn('Error renderizando Mermaid:', e);
    }
  } else {
    dom.markdownView.classList.add('hidden');
    dom.rawView.classList.remove('hidden');
  }
}

function renderEmptyState(msg) {
  state.rawContent = '';
  dom.markdownView.innerHTML = `
    <div style="text-align: center; padding: 60px 20px; color: var(--text-dim);">
      <div style="font-size: 3rem; margin-bottom: 12px;">📭</div>
      <h3>Artefacto no generado todavía</h3>
      <p style="margin-top: 6px;">${msg}</p>
    </div>
  `;
  dom.rawCode.textContent = msg;
}

// --- Alternar Entre Workspace y Ramas Git ---
function setInspectionMode(mode) {
  state.mode = mode;
  dom.toggleWorkspace.classList.toggle('active', mode === 'workspace');
  dom.toggleGit.classList.toggle('active', mode === 'git');
  dom.gitBranchesSection.classList.toggle('hidden', mode !== 'git');

  if (mode === 'workspace') {
    dom.gitBranchBanner.classList.add('hidden');
    loadArtifactContent(state.selectedArtifact);
  } else {
    // Si no hay rama seleccionada, elegir la primera de la lista
    if (!state.selectedBranch && state.branches.length > 0) {
      selectGitBranch(state.branches[0].name);
    } else if (state.selectedBranch) {
      selectGitBranch(state.selectedBranch);
    }
  }
}

function selectGitBranch(branchName) {
  state.selectedBranch = branchName;
  dom.bannerBranchName.textContent = branchName;
  dom.gitBranchBanner.classList.remove('hidden');

  // Actualizar tarjetas de ramas
  document.querySelectorAll('.branch-card').forEach(card => {
    const isThis = card.querySelector('.branch-title')?.textContent === branchName;
    card.classList.toggle('active', isThis);
  });

  loadArtifactContent(state.selectedArtifact);
}

// --- Restaurar Rama a Workspace ---
async function restoreCurrentBranch() {
  if (!state.selectedBranch) return;
  if (!confirm(`¿Deseas restaurar la aplicación de '${state.selectedBranch}' en el Workspace actual? Se creará una copia de seguridad automática previa.`)) return;

  try {
    const res = await fetch(`/api/git/branch/${encodeURIComponent(state.selectedBranch)}/restore`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Fallo al restaurar');
    showToast(data.message, 'success');
    setInspectionMode('workspace');
    loadStatus();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- Acciones de Grill-Me y Modales ---
dom.btnOpenGrill.addEventListener('click', () => dom.modalGrill.classList.remove('hidden'));
dom.btnCloseGrill.addEventListener('click', () => dom.modalGrill.classList.add('hidden'));
dom.btnCancelGrill.addEventListener('click', () => dom.modalGrill.classList.add('hidden'));

dom.btnSubmitGrill.addEventListener('click', async () => {
  const prompt = document.getElementById('grill-prompt').value.trim();
  if (!prompt) {
    alert('Ingresa una frase inicial para el requerimiento.');
    return;
  }

  const answers = {
    api_style: document.getElementById('grill-opt-style').value,
    entities: document.getElementById('grill-opt-entities').value,
    consumers: "Aplicaciones frontend (SPA Web) y clientes móviles",
    auth_scheme: document.getElementById('grill-opt-auth').value,
    error_format: document.getElementById('grill-opt-errors').value,
    persistence: document.getElementById('grill-opt-persistence').value,
    caching: document.getElementById('grill-opt-caching').value,
    validation: "Esquemas estrictos tipados (Pydantic / dataclasses)",
    deployment: "Contenedor Docker (python:3.11-slim)",
  };

  dom.btnSubmitGrill.disabled = true;
  dom.btnSubmitGrill.textContent = 'Procesando Rondas...';

  try {
    const res = await fetch('/api/actions/interview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, answers }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error en Discovery');

    showToast('Discovery completado y congelado en DISCOVERY_NOTES.md', 'success');
    dom.modalGrill.classList.add('hidden');
    setInspectionMode('workspace');
    await loadStatus();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    dom.btnSubmitGrill.disabled = false;
    dom.btnSubmitGrill.textContent = '🚀 Generar Discovery y Congelar Contrato';
  }
});

// --- Exportar y Resetear Fábrica ---
dom.btnExportApp.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/actions/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al exportar');
    showToast(`Aplicación exportada con éxito en ${data.target_dir}`, 'success');
    loadStatus();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

dom.btnOpenReset.addEventListener('click', () => dom.modalReset.classList.remove('hidden'));
dom.btnCloseReset.addEventListener('click', () => dom.modalReset.classList.add('hidden'));
dom.btnCancelReset.addEventListener('click', () => dom.modalReset.classList.add('hidden'));

dom.btnConfirmReset.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/actions/reset', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al reiniciar');
    showToast('Ambiente respaldado y reiniciado a estado base.', 'success');
    dom.modalReset.classList.add('hidden');
    await loadStatus();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// --- Event Listeners de UI ---
dom.toggleWorkspace.addEventListener('click', () => setInspectionMode('workspace'));
dom.toggleGit.addEventListener('click', () => setInspectionMode('git'));
dom.btnRestoreBranch.addEventListener('click', restoreCurrentBranch);

dom.artifactItems.forEach(item => {
  item.addEventListener('click', () => loadArtifactContent(item.dataset.artifact));
});

dom.stepCards.forEach(card => {
  card.addEventListener('click', () => loadArtifactContent(card.dataset.stage));
});

dom.btnViewRendered.addEventListener('click', () => {
  state.viewMode = 'rendered';
  dom.btnViewRendered.classList.add('active');
  dom.btnViewRaw.classList.remove('active');
  renderContent(state.rawContent);
});

dom.btnViewRaw.addEventListener('click', () => {
  state.viewMode = 'raw';
  dom.btnViewRaw.classList.add('active');
  dom.btnViewRendered.classList.remove('active');
  renderContent(state.rawContent);
});

dom.btnCopy.addEventListener('click', () => {
  navigator.clipboard.writeText(state.rawContent).then(() => {
    showToast('Contenido copiado al portapapeles', 'success');
  });
});

// --- Inicialización al Cargar la Página ---
document.addEventListener('DOMContentLoaded', async () => {
  await loadStatus();
  await loadGitOverview();
  loadArtifactContent('discovery_notes');
});
