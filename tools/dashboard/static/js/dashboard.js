/**
 * Dashboard Controller para la Software Factory.
 * Maneja el ciclo de vida progresivo, wizard interactivo de Grill-Me por rondas,
 * generación y regeneración de artefactos y sugerencia del siguiente paso.
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
  artifactsStatus: {},
  activeProject: null,
  wizardStep: 1,
};

const ARTIFACT_NAMES = {
  discovery_notes: 'DISCOVERY_NOTES.md (Fase 0)',
  prd: 'PRD.md (Fase 1: PM)',
  system_design: 'SYSTEM_DESIGN.md (Fase 2: Arquitecto)',
  tasks: 'TASKS.md (Fase 2: Tareas)',
  change_plan: 'CHANGE_PLAN.md (Fase 3: Plan)',
  patch: 'model.patch (Fase 3: Código)',
  qa_report: 'QA_REPORT.md (Fase 4: QA)',
};

const STAGE_CONFIG = {
  discovery_notes: {
    tag: 'Fase 0: Requirements Discovery',
    desc: 'Protocolo de árbol de decisiones para desgranar y congelar requerimientos.',
    btnText: '✨ Re-ejecutar Elicitación Grill-Me',
    action: () => openGrillModal(),
  },
  prd: {
    tag: 'Fase 1: Product Manager',
    desc: 'Traduce las decisiones de Discovery en objetivos, historias Gherkin y pool priorizado.',
    btnText: '📝 Generar / Regenerar PRD',
    action: () => triggerStageGeneration('/api/actions/generate/prd', 'PRD.md generado con éxito por el Product Manager.'),
  },
  system_design: {
    tag: 'Fase 2: Arquitecto de Software',
    desc: 'Diseña la arquitectura técnica, diagramas de clases, secuencias y desglose de tareas.',
    btnText: '📐 Generar / Regenerar Arquitectura & Tareas',
    action: () => triggerStageGeneration('/api/actions/generate/system_design', 'Arquitectura y TASKS.md generados con éxito.'),
  },
  tasks: {
    tag: 'Fase 2: Tareas de Implementación',
    desc: 'Lista de módulos y unidades atómicas asignables al Programador.',
    btnText: '📐 Actualizar TASKS.md',
    action: () => triggerStageGeneration('/api/actions/generate/system_design', 'TASKS.md actualizado con éxito.'),
  },
  change_plan: {
    tag: 'Fase 3: Programador (Plan de Cambios)',
    desc: 'Congela la superficie autorizada de archivos antes de escribir código.',
    btnText: '📝 Ver Plan de Cambios',
    action: () => showToast('El plan de cambios se genera automáticamente al implementar el código.', 'info'),
  },
  patch: {
    tag: 'Fase 3: Programador (Código & Parche)',
    desc: 'Implementación completa del sistema en environment/workspace y generación de model.patch.',
    btnText: '💻 Validar Código en Workspace',
    action: () => showToast('Código inspeccionado. Procede con la auditoría de QA.', 'info'),
  },
  qa_report: {
    tag: 'Fase 4: QA & Hostile Auditor',
    desc: 'Ejecuta análisis de deriva (Drift Check), linter y la suite de pruebas dinámicas.',
    btnText: '🛡️ Ejecutar Auditoría Hostil y Tests',
    action: () => triggerStageGeneration('/api/actions/run_qa', 'Auditoría de QA y suite de pruebas ejecutadas.'),
  },
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
  // Barra de acción de etapa
  stageActionToolbar: document.getElementById('stage-action-toolbar'),
  stageActionTag: document.getElementById('stage-action-tag'),
  stageActionDesc: document.getElementById('stage-action-desc'),
  btnStageAction: document.getElementById('btn-stage-action'),
  // Banner de Siguiente Paso
  nextStepBanner: document.getElementById('next-step-banner'),
  nextStepTitle: document.getElementById('next-step-title'),
  nextStepDesc: document.getElementById('next-step-desc'),
  btnNextStep: document.getElementById('btn-next-step'),
  // Modales
  modalNewAppConfirm: document.getElementById('modal-new-app-confirm'),
  btnOpenNewApp: document.getElementById('btn-open-new-app'),
  btnCloseNewConfirm: document.getElementById('btn-close-new-confirm'),
  btnCancelNewConfirm: document.getElementById('btn-cancel-new-confirm'),
  btnAcceptNewConfirm: document.getElementById('btn-accept-new-confirm'),
  modalGrill: document.getElementById('modal-grill'),
  btnCloseGrill: document.getElementById('btn-close-grill'),
  btnWizardPrev: document.getElementById('btn-wizard-prev'),
  btnWizardNext: document.getElementById('btn-wizard-next'),
  btnWizardSubmit: document.getElementById('btn-wizard-submit'),
  grillSummaryContent: document.getElementById('grill-summary-content'),
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
  setTimeout(() => toast.remove(), 4500);
}

// --- Carga Inicial de Estado ---
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    state.activeProject = data.project_metadata;
    state.artifactsStatus = data.artifacts_status || {};

    dom.activeProjectName.textContent = data.project_metadata.project_name || 'Sin Proyecto';
    const status = data.project_metadata.status || 'INITIALIZED';
    dom.activeProjectStatus.textContent = status;
    dom.activeProjectStatus.className = `pill-status badge-${status.toLowerCase()}`;

    updateStepperBadges(state.artifactsStatus);
    renderWorkspaceFiles(data.workspace_files);
    updateNextStepSuggestion();
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

// --- Sugerencia del Siguiente Paso (Next Step Progression) ---
function updateNextStepSuggestion() {
  if (state.mode !== 'workspace') {
    dom.nextStepBanner.classList.add('hidden');
    return;
  }

  const s = state.artifactsStatus;

  if (!s.discovery_notes) {
    dom.nextStepTitle.textContent = 'Fase 0 Requerida: Discovery & Grilling';
    dom.nextStepDesc.textContent = 'Inicia el asistente para definir los requerimientos y congelar las decisiones iniciales.';
    dom.btnNextStep.textContent = '✨ Iniciar Grill-Me';
    dom.btnNextStep.onclick = () => openNewAppConfirmation();
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.prd) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Fase 1 (Product Manager)';
    dom.nextStepDesc.textContent = 'El Discovery está congelado. Genera el PRD.md con las historias de usuario y criterios Gherkin.';
    dom.btnNextStep.textContent = '➡️ Generar PRD (Product Manager)';
    dom.btnNextStep.onclick = () => {
      loadArtifactContent('prd');
      triggerStageGeneration('/api/actions/generate/prd', 'PRD.md generado con éxito.');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.system_design) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Fase 2 (Arquitecto de Software)';
    dom.nextStepDesc.textContent = 'El PRD está aprobado. Genera la especificación técnica (SYSTEM_DESIGN.md) y el desglose de tareas.';
    dom.btnNextStep.textContent = '➡️ Diseñar Arquitectura (Arquitecto)';
    dom.btnNextStep.onclick = () => {
      loadArtifactContent('system_design');
      triggerStageGeneration('/api/actions/generate/system_design', 'Arquitectura generada con éxito.');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.patch) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Fase 3 (Programador)';
    dom.nextStepDesc.textContent = 'Arquitectura congelada. El código se implementará dentro de environment/workspace/.';
    dom.btnNextStep.textContent = '➡️ Inspeccionar Workspace / Tareas';
    dom.btnNextStep.onclick = () => loadArtifactContent('tasks');
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.qa_report) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Fase 4 (QA & Hostile Auditor)';
    dom.nextStepDesc.textContent = 'Código implementado. Ejecuta la auditoría hostil y la suite de pruebas unitarias.';
    dom.btnNextStep.textContent = '🛡️ Ejecutar Auditoría de QA';
    dom.btnNextStep.onclick = () => {
      loadArtifactContent('qa_report');
      triggerStageGeneration('/api/actions/run_qa', 'Auditoría de QA ejecutada.');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else {
    dom.nextStepTitle.textContent = '🎉 ¡Ciclo de Software Factory Completado!';
    dom.nextStepDesc.textContent = 'Todas las etapas han sido aprobadas por QA. Puedes exportar la app o versionarla en Git.';
    dom.btnNextStep.textContent = '📦 Exportar Aplicación Standalone';
    dom.btnNextStep.onclick = () => dom.btnExportApp.click();
    dom.nextStepBanner.classList.remove('hidden');
  }
}

// --- Barra de Acción de la Etapa ---
function updateStageActionBar(artifactKey) {
  const cfg = STAGE_CONFIG[artifactKey] || {
    tag: 'Etapa del Sistema',
    desc: 'Información y especificaciones del artefacto.',
    btnText: 'Actualizar',
    action: () => {},
  };

  dom.stageActionTag.textContent = cfg.tag;
  dom.stageActionDesc.textContent = cfg.desc;

  if (state.mode === 'git') {
    dom.btnStageAction.textContent = '📥 Restaurar Esta Versión en Workspace';
    dom.btnStageAction.onclick = () => restoreCurrentBranch();
  } else {
    const exists = state.artifactsStatus[artifactKey];
    dom.btnStageAction.textContent = exists ? `🔄 Re-${cfg.btnText}` : `🚀 ${cfg.btnText}`;
    dom.btnStageAction.onclick = cfg.action;
  }
}

async function triggerStageGeneration(endpoint, successMsg) {
  dom.btnStageAction.disabled = true;
  dom.btnStageAction.textContent = 'Procesando Etapa...';

  try {
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Fallo al procesar etapa');

    showToast(successMsg, 'success');
    await loadStatus();
    loadArtifactContent(state.selectedArtifact);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    dom.btnStageAction.disabled = false;
  }
}

// --- Selección de Artefactos y Carga de Contenido ---
async function loadArtifactContent(artifactKey) {
  state.selectedArtifact = artifactKey;
  dom.bcFilename.textContent = ARTIFACT_NAMES[artifactKey] || artifactKey;

  // Actualizar clase activa en sidebar y stepper
  dom.artifactItems.forEach(el => el.classList.toggle('active', el.dataset.artifact === artifactKey));
  dom.stepCards.forEach(el => el.classList.toggle('active', el.dataset.stage === artifactKey));

  updateStageActionBar(artifactKey);

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
      dom.bcOrigin.textContent = `Git: ${state.selectedBranch}`;
      const res = await fetch(`/api/git/branch/${encodeURIComponent(state.selectedBranch)}/artifacts`);
      if (!res.ok) {
        throw new Error(`No se encontraron artefactos en la rama '${state.selectedBranch}'.`);
      }
      const data = await res.json();
      content = data.artifacts[artifactKey] || `El archivo ${artifactKey} no existe en esta rama histórica.`;
    }

    state.rawContent = content;
    renderContent(content);
  } catch (err) {
    renderEmptyState(err.message, artifactKey);
  }
}

function renderContent(markdownText) {
  dom.rawCode.textContent = markdownText;

  if (state.viewMode === 'rendered') {
    dom.rawView.classList.add('hidden');
    dom.markdownView.classList.remove('hidden');

    dom.markdownView.innerHTML = marked.parse(markdownText);

    const codeBlocks = dom.markdownView.querySelectorAll('code.language-mermaid');
    codeBlocks.forEach(codeEl => {
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

function renderEmptyState(msg, artifactKey) {
  state.rawContent = '';
  const cfg = STAGE_CONFIG[artifactKey] || { btnText: 'Generar' };
  dom.markdownView.innerHTML = `
    <div style="text-align: center; padding: 60px 20px; color: var(--text-dim);">
      <div style="font-size: 3.5rem; margin-bottom: 14px;">📭</div>
      <h3 style="color: #fff; font-size: 1.25rem;">Etapa Pendiente de Generación</h3>
      <p style="margin-top: 8px; color: #94a3b8; max-width: 500px; margin-left: auto; margin-right: auto;">
        ${msg}
      </p>
      ${state.mode === 'workspace' ? `
        <button class="btn btn-primary" style="margin-top: 20px;" onclick="dom.btnStageAction.click()">
          ${cfg.btnText}
        </button>
      ` : ''}
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
    if (!state.selectedBranch && state.branches.length > 0) {
      selectGitBranch(state.branches[0].name);
    } else if (state.selectedBranch) {
      selectGitBranch(state.selectedBranch);
    }
  }
  updateNextStepSuggestion();
}

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

function selectGitBranch(branchName) {
  state.selectedBranch = branchName;
  dom.bannerBranchName.textContent = branchName;
  dom.gitBranchBanner.classList.remove('hidden');

  document.querySelectorAll('.branch-card').forEach(card => {
    const isThis = card.querySelector('.branch-title')?.textContent === branchName;
    card.classList.toggle('active', isThis);
  });

  loadArtifactContent(state.selectedArtifact);
  updateNextStepSuggestion();
}

async function restoreCurrentBranch() {
  if (!state.selectedBranch) return;
  if (!confirm(`¿Deseas restaurar la aplicación de '${state.selectedBranch}' en el Workspace actual? Se creará una copia de seguridad automática previa.`)) return;

  try {
    const res = await fetch(`/api/git/branch/${encodeURIComponent(state.selectedBranch)}/restore`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Fallo al restaurar');
    showToast(data.message, 'success');
    setInspectionMode('workspace');
    await loadStatus();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- WIZARD POR RONDAS: "Nueva App (Grill-Me)" ---

function openNewAppConfirmation() {
  dom.modalNewAppConfirm.classList.remove('hidden');
}

dom.btnOpenNewApp.addEventListener('click', openNewAppConfirmation);
dom.btnCloseNewConfirm.addEventListener('click', () => dom.modalNewAppConfirm.classList.add('hidden'));
dom.btnCancelNewConfirm.addEventListener('click', () => dom.modalNewAppConfirm.classList.add('hidden'));

dom.btnAcceptNewConfirm.addEventListener('click', () => {
  dom.modalNewAppConfirm.classList.add('hidden');
  openGrillWizard();
});

function openGrillWizard() {
  state.wizardStep = 1;
  showWizardStep(1);
  dom.modalGrill.classList.remove('hidden');
}

dom.btnCloseGrill.addEventListener('click', () => dom.modalGrill.classList.add('hidden'));

function showWizardStep(step) {
  state.wizardStep = step;

  for (let i = 1; i <= 4; i++) {
    const pane = document.getElementById(`wpane-${i}`);
    const tab = document.getElementById(`wstep-${i}`);
    if (pane) pane.classList.toggle('hidden', i !== step);
    if (tab) {
      tab.classList.toggle('active', i === step);
      tab.classList.toggle('completed', i < step);
    }
  }

  dom.btnWizardPrev.disabled = (step === 1);

  if (step === 4) {
    dom.btnWizardNext.classList.add('hidden');
    dom.btnWizardSubmit.classList.remove('hidden');
    buildWizardSummary();
  } else {
    dom.btnWizardNext.classList.remove('hidden');
    dom.btnWizardSubmit.classList.add('hidden');
  }
}

dom.btnWizardPrev.addEventListener('click', () => {
  if (state.wizardStep > 1) showWizardStep(state.wizardStep - 1);
});

dom.btnWizardNext.addEventListener('click', () => {
  if (state.wizardStep === 1) {
    const prompt = document.getElementById('grill-prompt').value.trim();
    if (!prompt) {
      alert('Ingresa una frase inicial para el requerimiento.');
      return;
    }
  }
  if (state.wizardStep < 4) showWizardStep(state.wizardStep + 1);
});

function buildWizardSummary() {
  const platform = document.getElementById('grill-opt-platform').options[document.getElementById('grill-opt-platform').selectedIndex].text;
  const entities = document.getElementById('grill-opt-entities').value;
  const auth = document.getElementById('grill-opt-auth').value;
  const errors = document.getElementById('grill-opt-errors').value;
  const persistence = document.getElementById('grill-opt-persistence').value;
  const caching = document.getElementById('grill-opt-caching').value;
  const projName = document.getElementById('grill-proj-name').value.trim() || 'nueva_app';
  const prompt = document.getElementById('grill-prompt').value.trim();

  dom.grillSummaryContent.innerHTML = `
    <div><strong>Proyecto:</strong> <code>${projName}</code></div>
    <div><strong>Requerimiento:</strong> "${prompt}"</div>
    <div><strong>Plataforma / Interfaz:</strong> ${platform}</div>
    <div><strong>Entidades:</strong> ${entities}</div>
    <div><strong>Autenticación:</strong> ${auth}</div>
    <div><strong>Persistencia:</strong> ${persistence}</div>
    <div><strong>Caché:</strong> ${caching}</div>
    <div><strong>Manejo de Errores:</strong> ${errors}</div>
  `;
}

dom.btnWizardSubmit.addEventListener('click', async () => {
  const prompt = document.getElementById('grill-prompt').value.trim();
  const projName = document.getElementById('grill-proj-name').value.trim() || 'nueva_app';

  const answers = {
    api_style: document.getElementById('grill-opt-platform').options[document.getElementById('grill-opt-platform').selectedIndex].text,
    entities: document.getElementById('grill-opt-entities').value,
    consumers: "Clientes y usuarios de la plataforma seleccionada",
    auth_scheme: document.getElementById('grill-opt-auth').value,
    error_format: document.getElementById('grill-opt-errors').value,
    persistence: document.getElementById('grill-opt-persistence').value,
    caching: document.getElementById('grill-opt-caching').value,
    validation: "Esquemas estrictos tipados",
    deployment: "Contenedor Docker (python:3.11-slim) / Paquete",
  };

  dom.btnWizardSubmit.disabled = true;
  dom.btnWizardSubmit.textContent = 'Respaldando y Reiniciando...';

  try {
    const res = await fetch('/api/actions/interview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        answers,
        reset_first: true,
        project_name: projName,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error en Discovery');

    showToast('¡Fase 0 completada! Contrato congelado en DISCOVERY_NOTES.md.', 'success');
    dom.modalGrill.classList.add('hidden');
    setInspectionMode('workspace');
    await loadStatus();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    dom.btnWizardSubmit.disabled = false;
    dom.btnWizardSubmit.textContent = '🚀 Congelar Contrato y Generar Discovery';
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

// --- Event Listeners Globales ---
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
