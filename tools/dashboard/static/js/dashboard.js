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
  humanApprovals: {},
  activeProject: null,
  wizardStep: 1,
};

const ARTIFACT_NAMES = {
  discovery_notes: 'DISCOVERY_NOTES.md (Etapa 1: Discovery)',
  delta_requirement: 'DELTA_REQUIREMENT.txt (Mantenimiento)',
  prd: 'PRD.md (Etapa 2: PM)',
  system_design: 'SYSTEM_DESIGN.md (Etapa 3: Arquitecto)',
  tasks: 'TASKS.md (Etapa 3: Tareas)',
  change_plan: 'CHANGE_PLAN.md (Etapa 4: Plan)',
  patch: 'model.patch (Etapa 4: Código)',
  qa_report: 'QA_REPORT.md (Etapa 5: QA)',
  local_runner: 'LOCAL_TESTING_SPEC.md (Etapa 6: Runner Local)',
  deploy: 'DEPLOY_SPEC.md (Etapa 7: Deploy & Cloud)',
};

const STAGE_CONFIG = {
  discovery_notes: {
    tag: 'Etapa 1: Requirements Discovery & Grilling',
    desc: 'Protocolo de árbol de decisiones para desgranar y congelar requerimientos.',
    skills: [
      { name: 'grill-me', version: '1.1.0', scope: 'global', role: 'Árbol de Preguntas y Smart Defaults' },
      { name: 'domain-modeling', version: '1.0.0', scope: 'global', role: 'Modelo de Recursos y Entidades' },
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Estándar de Endpoints y RFC 7807' },
    ],
    agent: 'Rita (Requirements Discovery)',
    btnText: '✨ Ejecutar Elicitación Grill-Me',
    action: () => openGrillWizard('active_project'),
  },
  delta_requirement: {
    tag: 'Lazo de Mantenimiento / Nueva Solicitud',
    desc: 'Semilla de modificación, issue o requerimiento evolutivo sobre el proyecto activo.',
    skills: [],
    btnText: '🛠️ Formular Modificación o Corrección',
    action: () => openMaintenanceModal(),
  },
  prd: {
    tag: 'Etapa 2: Product Manager',
    desc: 'Traduce las decisiones de Discovery en objetivos, historias Gherkin y pool priorizado.',
    skills: [
      { name: 'domain-modeling', version: '1.0.0', scope: 'global', role: 'Historias de Usuario y Criterios Gherkin' },
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Especificación de Contratos y Alcance' },
    ],
    agent: 'Alice (Product Manager)',
    btnText: '📝 Generar / Regenerar PRD',
    action: () => triggerStageGeneration('/api/actions/generate/prd', 'PRD.md generado con éxito por el Product Manager.'),
  },
  system_design: {
    tag: 'Etapa 3: Arquitecto de Software',
    desc: 'Diseña la arquitectura técnica, diagramas de clases, secuencias y desglose de tareas.',
    skills: [
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Firmas de Clases, Endpoints y DTOs' },
      { name: 'domain-modeling', version: '1.0.0', scope: 'global', role: 'Mapeo de Modelos de Datos' },
    ],
    agent: 'Bob (Architect)',
    btnText: '📐 Generar / Regenerar Arquitectura & Tareas',
    action: () => triggerStageGeneration('/api/actions/generate/system_design', 'Arquitectura y TASKS.md generados con éxito.'),
  },
  tasks: {
    tag: 'Etapa 3: Tareas de Implementación',
    desc: 'Lista de módulos y unidades atómicas asignables al Programador.',
    skills: [
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Desglose por archivo' },
    ],
    agent: 'Bob (Architect)',
    btnText: '📐 Actualizar TASKS.md',
    action: () => triggerStageGeneration('/api/actions/generate/system_design', 'TASKS.md actualizado con éxito.'),
  },
  change_plan: {
    tag: 'Etapa 4: Programador (Plan de Cambios)',
    desc: 'Congela la superficie autorizada de archivos antes de escribir código.',
    skills: [
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Límites de superficie y dependencias' },
    ],
    agent: 'Alex (Engineer)',
    btnText: 'Plan de Cambios & Código',
    action: async () => {
      if (!state.humanApprovals || !state.humanApprovals.code_modification) {
        openCodeApprovalModal();
        return;
      }
      await triggerStageGeneration('/api/actions/generate/code', 'Plan de cambios y código implementados con éxito.');
      loadArtifactContent('change_plan');
    },
  },
  patch: {
    tag: 'Etapa 4: Programador (Código & Parche)',
    desc: 'Implementación completa del sistema en workspace y emisión de model.patch.',
    skills: [
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Implementación según firmas' },
    ],
    agent: 'Alex (Engineer)',
    btnText: 'Implementar Código en Workspace',
    action: async () => {
      if (!state.humanApprovals || !state.humanApprovals.code_modification) {
        openCodeApprovalModal();
        return;
      }
      await triggerStageGeneration('/api/actions/generate/code', 'Código fuente implementado con éxito por el Programador.');
      loadArtifactContent('patch');
    },
  },
  qa_report: {
    tag: 'Etapa 5: QA & Hostile Auditor',
    desc: 'Ejecuta análisis de deriva (Drift Check), linter y la suite de pruebas dinámicas.',
    skills: [
      { name: 'api-design', version: '1.0.0', scope: 'global', role: 'Auditoría de conformidad de API' },
    ],
    agent: 'Dana (QA & Hostile Auditor)',
    btnText: '🛡️ Ejecutar Auditoría Hostil y Tests',
    action: () => triggerStageGeneration('/api/actions/run_qa', 'Auditoría de QA y suite de pruebas ejecutadas.'),
  },
  local_runner: {
    tag: 'Etapa 6: Entorno de Pruebas Local (PC de Desarrollo)',
    desc: 'Genera el lanzador local (local_runner.py), seeds y el Sandbox Web Testbench para el navegador.',
    skills: [],
    agent: 'Runtime Specialist',
    btnText: '⚡ Configurar / Generar Runner Local',
    action: () => triggerStageGeneration('/api/actions/generate/local_runner', 'Entorno de pruebas local y local_runner.py generados con éxito.'),
  },
  deploy: {
    tag: 'Etapa 7: Deploy & Cloud (DevOps)',
    desc: 'Generación de manifiestos, contenedores y configuración para despliegue en la nube o ambiente productivo.',
    skills: [],
    btnText: '🚀 Configurar Deploy en la Nube',
    action: () => showToast('La Etapa 7 de Deploy Cloud/DevOps estará disponible para la siguiente fase.', 'info'),
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
  stagesProgressText: document.getElementById('stages-progress-text'),
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
  // Barra de acción de etapa y compuerta de aprobación
  stageActionToolbar: document.getElementById('stage-action-toolbar'),
  stageActionTag: document.getElementById('stage-action-tag'),
  stageActionDesc: document.getElementById('stage-action-desc'),
  stageApprovalBadge: document.getElementById('stage-approval-badge'),
  btnApproveStage: document.getElementById('btn-approve-stage'),
  btnStageAction: document.getElementById('btn-stage-action'),
  // Banner de Siguiente Paso
  nextStepBanner: document.getElementById('next-step-banner'),
  nextStepTitle: document.getElementById('next-step-title'),
  nextStepDesc: document.getElementById('next-step-desc'),
  btnNextStep: document.getElementById('btn-next-step'),
  // Modales
  modalProjectLauncher: document.getElementById('modal-project-launcher'),
  btnOpenLauncher: document.getElementById('btn-open-launcher'),
  btnCloseLauncher: document.getElementById('btn-close-launcher'),
  launcherProjectsGrid: document.getElementById('launcher-projects-grid'),
  launcherGitCount: document.getElementById('launcher-git-count'),
  launcherGitList: document.getElementById('launcher-git-list'),
  btnLauncherNewApp: document.getElementById('btn-launcher-new-app'),
  launcherCurrentName: document.getElementById('launcher-current-name'),
  launcherCurrentStatus: document.getElementById('launcher-current-status'),
  btnLauncherContinue: document.getElementById('btn-launcher-continue'),
  // Modal Nueva App Confirmación
  modalNewAppConfirm: document.getElementById('modal-new-app-confirm'),
  btnOpenNewApp: document.getElementById('btn-open-new-app'),
  btnCloseNewConfirm: document.getElementById('btn-close-new-confirm'),
  btnCancelNewConfirm: document.getElementById('btn-cancel-new-confirm'),
  btnAcceptNewConfirm: document.getElementById('btn-accept-new-confirm'),
  // Modal Grill Wizard
  modalGrill: document.getElementById('modal-grill'),
  btnCloseGrill: document.getElementById('btn-close-grill'),
  btnWizardPrev: document.getElementById('btn-wizard-prev'),
  btnWizardNext: document.getElementById('btn-wizard-next'),
  btnWizardSubmit: document.getElementById('btn-wizard-submit'),
  grillSummaryContent: document.getElementById('grill-summary-content'),
  // Modal Mantenimiento / RFC
  modalMaintenance: document.getElementById('modal-maintenance'),
  btnOpenMaintenance: document.getElementById('btn-open-maintenance'),
  btnCloseMaintenance: document.getElementById('btn-close-maintenance'),
  btnCancelMaintenance: document.getElementById('btn-cancel-maintenance'),
  btnSubmitMaintenance: document.getElementById('btn-submit-maintenance'),
  // Modal Compuerta de Aprobación de Código
  modalCodeApproval: document.getElementById('modal-code-approval'),
  btnCloseCodeApproval: document.getElementById('btn-close-code-approval'),
  btnRejectCodeApproval: document.getElementById('btn-reject-code-approval'),
  btnConfirmCodeApproval: document.getElementById('btn-confirm-code-approval'),
  codeApprovalAllowedList: document.getElementById('code-approval-allowed-list'),
  codeApprovalForbiddenList: document.getElementById('code-approval-forbidden-list'),
  codeApprovalMaintContext: document.getElementById('code-approval-maint-context'),
  codeApprovalDeltaText: document.getElementById('code-approval-delta-text'),
  codeApprovalPlanText: document.getElementById('code-approval-plan-text'),
  // Modal Reset
  modalReset: document.getElementById('modal-reset'),
  resetModalPname: document.getElementById('reset-modal-pname'),
  btnOpenReset: document.getElementById('btn-open-reset'),
  btnCloseReset: document.getElementById('btn-close-reset'),
  btnCancelReset: document.getElementById('btn-cancel-reset'),
  btnConfirmReset: document.getElementById('btn-confirm-reset'),
  btnDeleteActiveProject: document.getElementById('btn-delete-active-project'),
  btnExportApp: document.getElementById('btn-export-app'),
  btnRunApp: document.getElementById('btn-run-app'),
  btnStopApp: document.getElementById('btn-stop-app'),
  // Modal Skills
  btnOpenSkills: document.getElementById('btn-open-skills'),
  modalSkills: document.getElementById('modal-skills'),
  btnCloseSkills: document.getElementById('btn-close-skills'),
  btnCloseSkillsFooter: document.getElementById('btn-close-skills-footer'),
  skillsModalPname: document.getElementById('skills-modal-pname'),
  btnToggleNewSkillForm: document.getElementById('btn-toggle-new-skill-form'),
  newSkillFormBox: document.getElementById('new-skill-form-box'),
  newSkillName: document.getElementById('new-skill-name'),
  newSkillDesc: document.getElementById('new-skill-desc'),
  newSkillBody: document.getElementById('new-skill-body'),
  btnCancelNewSkill: document.getElementById('btn-cancel-new-skill'),
  btnSubmitNewSkill: document.getElementById('btn-submit-new-skill'),
  projectSkillsCount: document.getElementById('project-skills-count'),
  projectSkillsList: document.getElementById('project-skills-list'),
  globalSkillsCount: document.getElementById('global-skills-count'),
  globalSkillsList: document.getElementById('global-skills-list'),
  // Modal Lecciones Aprendidas (Evolución Factory)
  btnOpenLesson: document.getElementById('btn-open-lesson'),
  modalLesson: document.getElementById('modal-lesson'),
  btnCloseLesson: document.getElementById('btn-close-lesson'),
  btnCancelLesson: document.getElementById('btn-cancel-lesson'),
  btnSubmitLesson: document.getElementById('btn-submit-lesson'),
  lessonStage: document.getElementById('lesson-stage'),
  lessonTarget: document.getElementById('lesson-target'),
  lessonSymptom: document.getElementById('lesson-symptom'),
  lessonCause: document.getElementById('lesson-cause'),
  lessonProposal: document.getElementById('lesson-proposal'),
  maintSkillRedirectBox: document.getElementById('maint-skill-redirect-box'),
  maintOpenSkillsLink: document.getElementById('maint-open-skills-link'),
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
    const projParam = state.activeProjectName ? `?project=${encodeURIComponent(state.activeProjectName)}` : '';
    const res = await fetch(`/api/status${projParam}`);
    const data = await res.json();
    state.activeProjectName = data.active_project;
    state.activeProject = {
      ...(data.project_metadata || {}),
      project_name: data.active_project,
    };
    state.artifactsStatus = data.artifacts_status || {};
    state.humanApprovals = data.human_approvals || {};

    const projName = data.active_project || data.project_metadata?.project_name || 'Sin Proyecto';
    const status = data.project_metadata?.status || 'INITIALIZED';

    dom.activeProjectName.textContent = projName;
    dom.activeProjectStatus.textContent = status;
    dom.activeProjectStatus.className = `pill-status badge-${status.toLowerCase()}`;
    document.title = `SoftFactory [${projName}] - Control Plane`;

    if (dom.launcherCurrentName) dom.launcherCurrentName.textContent = projName;
    if (dom.launcherCurrentStatus) {
      dom.launcherCurrentStatus.textContent = status;
      dom.launcherCurrentStatus.className = `badge-${status.toLowerCase()}`;
    }
    if (dom.resetModalPname) dom.resetModalPname.textContent = `${projName} (projects/${projName})`;

    if (data.projects) {
      renderProjectsGrid(data.projects, projName);
    }

    const deltaItem = document.getElementById('item-delta-req');
    if (deltaItem) {
      deltaItem.classList.toggle('hidden', !state.artifactsStatus.delta_requirement);
    }

    // Actualizar estado del botón Probar App: Requiere obligatoriamente que la Etapa 6 esté Aprobada
    if (dom.btnRunApp) {
      const runningApp = data.running_app;
      const isStage6Approved = Boolean(state.humanApprovals && state.humanApprovals.local_runner === true);

      if (!isStage6Approved) {
        dom.btnRunApp.textContent = '▶️ Probar App';
        dom.btnRunApp.classList.remove('app-running');
        dom.btnRunApp.title = 'Bloqueado: Requiere que la Etapa 6 (Entorno de Pruebas Local) esté formalmente Aprobada';
        dom.btnRunApp.disabled = true;
        if (dom.btnStopApp) dom.btnStopApp.classList.add('hidden');
      } else if (runningApp && runningApp.running) {
        dom.btnRunApp.textContent = `🟢 App Activa (:${runningApp.port})`;
        dom.btnRunApp.classList.add('app-running');
        dom.btnRunApp.title = `Abrir aplicación en ${runningApp.url} (clic para recargar en navegador)`;
        dom.btnRunApp.disabled = false;
        if (dom.btnStopApp) dom.btnStopApp.classList.remove('hidden');
      } else {
        dom.btnRunApp.textContent = '▶️ Probar App';
        dom.btnRunApp.classList.remove('app-running');
        dom.btnRunApp.title = 'Levantar servidor local de prueba y abrir en el navegador';
        dom.btnRunApp.disabled = false;
        if (dom.btnStopApp) dom.btnStopApp.classList.add('hidden');
      }
    }

    updateStepperBadges(state.artifactsStatus, state.humanApprovals);
    renderWorkspaceFiles(data.workspace_files);
    updateNextStepSuggestion();
    updateStageActionBar(state.selectedArtifact);
    await loadGitOverview();

    // Consultar modo del motor para visibilidad de registro de lecciones
    try {
      const fRes = await fetch('/api/factory/info');
      const fInfo = await fRes.json();
      if (dom.btnOpenLesson) {
        if (fInfo.mode === 'development') {
          dom.btnOpenLesson.classList.remove('hidden');
          dom.btnOpenLesson.title = `Registrar Lección Aprendida (Motor v${fInfo.engine_version} - Modo Desarrollo)`;
        } else {
          dom.btnOpenLesson.classList.add('hidden');
        }
      }
    } catch (_) {}
  } catch (err) {
    console.error('Error cargando estado:', err);
  }
}

const STAGE_DEPENDENCIES = {
  discovery_notes: {
    approvalKey: 'discovery_notes',
    prevApprovalKey: null,
    prevArtifactKey: null,
    prevName: null,
  },
  delta_requirement: {
    approvalKey: null,
    prevApprovalKey: null,
    prevArtifactKey: null,
    prevName: null,
  },
  prd: {
    approvalKey: 'prd',
    prevApprovalKey: 'discovery_notes',
    prevArtifactKey: 'discovery_notes',
    prevName: 'Etapa 1 (Discovery)',
  },
  system_design: {
    approvalKey: 'system_design',
    prevApprovalKey: 'prd',
    prevArtifactKey: 'prd',
    prevName: 'Etapa 2 (PRD)',
  },
  tasks: {
    approvalKey: 'system_design',
    prevApprovalKey: 'prd',
    prevArtifactKey: 'prd',
    prevName: 'Etapa 2 (PRD)',
  },
  change_plan: {
    approvalKey: 'code_modification',
    prevApprovalKey: 'system_design',
    prevArtifactKey: 'system_design',
    prevName: 'Etapa 3 (Arquitectura)',
  },
  patch: {
    approvalKey: 'code_modification',
    prevApprovalKey: 'system_design',
    prevArtifactKey: 'system_design',
    prevName: 'Etapa 3 (Arquitectura)',
  },
  qa_report: {
    approvalKey: 'qa_report',
    prevApprovalKey: 'code_modification',
    prevArtifactKey: 'patch',
    prevName: 'Etapa 4 (Código)',
  },
  local_runner: {
    approvalKey: 'local_runner',
    prevApprovalKey: 'qa_report',
    prevArtifactKey: 'qa_report',
    prevName: 'Etapa 5 (QA)',
  },
  deploy: {
    approvalKey: 'deploy',
    prevApprovalKey: 'local_runner',
    prevArtifactKey: 'local_runner',
    prevName: 'Etapa 6 (Test Local)',
  },
};

function updateStepperBadges(artifacts, approvals = state.humanApprovals) {
  const steps = [
    { cardId: 'step-discovery', iconId: 'status-icon-discovery', exists: artifacts.discovery_notes, approvalKey: 'discovery_notes', prevKey: null },
    { cardId: 'step-prd', iconId: 'status-icon-prd', exists: artifacts.prd, approvalKey: 'prd', prevKey: 'discovery_notes' },
    { cardId: 'step-system_design', iconId: 'status-icon-system_design', exists: artifacts.system_design, approvalKey: 'system_design', prevKey: 'prd' },
    { cardId: 'step-patch', iconId: 'status-icon-patch', exists: artifacts.patch, approvalKey: 'code_modification', prevKey: 'system_design' },
    { cardId: 'step-qa_report', iconId: 'status-icon-qa_report', exists: artifacts.qa_report, approvalKey: 'qa_report', prevKey: 'code_modification' },
    { cardId: 'step-local_runner', iconId: 'status-icon-local_runner', exists: artifacts.local_runner, approvalKey: 'local_runner', prevKey: 'qa_report' },
    { cardId: 'step-deploy', iconId: 'status-icon-deploy', exists: Boolean(artifacts.deploy), approvalKey: 'deploy', prevKey: 'local_runner' },
  ];

  let approvedCount = 0;

  steps.forEach(s => {
    const iconEl = document.getElementById(s.iconId);
    const card = document.getElementById(s.cardId);
    const isApproved = Boolean(approvals && approvals[s.approvalKey]);
    const isPrevApproved = !s.prevKey || Boolean(approvals && approvals[s.prevKey]);
    const isLocked = !isPrevApproved && !s.exists;

    if (isApproved) {
      approvedCount++;
    }

    if (card) {
      card.classList.toggle('locked', isLocked);
      card.classList.toggle('step-approved', isApproved);
    }

    if (iconEl) {
      if (isLocked) {
        iconEl.textContent = '🔒';
        iconEl.title = 'Bloqueado: Requiere aprobar la etapa previa';
        iconEl.className = 'stage-status-icon icon-locked';
      } else if (!s.exists) {
        iconEl.textContent = '⚪';
        iconEl.title = 'Pendiente: Aún no generado';
        iconEl.className = 'stage-status-icon icon-pending';
      } else if (isApproved) {
        iconEl.textContent = '✅';
        iconEl.title = 'Aprobado formalmente por el usuario';
        iconEl.className = 'stage-status-icon icon-approved';
      } else {
        iconEl.textContent = '⏳';
        iconEl.title = 'Por Aprobar: Requiere revisión y aprobación';
        iconEl.className = 'stage-status-icon icon-review';
      }
    }
  });

  if (dom.stagesProgressText) {
    dom.stagesProgressText.textContent = `${approvedCount} / 7`;
  }

  updateArtifactTreeBadges();
}

function updateArtifactTreeBadges() {
  const treeItems = document.querySelectorAll('#artifact-tree .artifact-item');
  treeItems.forEach(item => {
    const key = item.dataset.artifact;
    const dep = STAGE_DEPENDENCIES[key];
    if (!dep || !dep.approvalKey) return;

    const exists = Boolean(state.artifactsStatus[key]);
    const isApproved = Boolean(state.humanApprovals[dep.approvalKey]);
    let badgeSpan = item.querySelector('.artifact-tree-badge');
    if (!badgeSpan) {
      badgeSpan = document.createElement('span');
      badgeSpan.className = 'artifact-tree-badge';
      item.appendChild(badgeSpan);
    }

    if (!exists) {
      badgeSpan.textContent = 'Pendiente';
      badgeSpan.className = 'artifact-tree-badge badge-pending-mini';
    } else if (isApproved) {
      badgeSpan.textContent = 'Aprobado';
      badgeSpan.className = 'artifact-tree-badge badge-approved-mini';
    } else {
      badgeSpan.textContent = 'Por Aprobar';
      badgeSpan.className = 'artifact-tree-badge badge-review-mini';
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

// --- Compuerta de Aprobación Humana (Helpers) ---
function getStageApprovalKey(artifactKey) {
  if (artifactKey === 'discovery_notes') return 'discovery_notes';
  if (artifactKey === 'prd') return 'prd';
  if (artifactKey === 'system_design' || artifactKey === 'tasks') return 'system_design';
  if (artifactKey === 'patch' || artifactKey === 'change_plan') return 'code_modification';
  if (artifactKey === 'qa_report') return 'qa_report';
  if (artifactKey === 'local_runner') return 'local_runner';
  if (artifactKey === 'deploy') return 'deploy';
  return null;
}

async function toggleStageApproval(stageKey, approve) {
  if (!approve) {
    const label = STAGE_CONFIG[stageKey]?.tag || stageKey;
    const confirmed = confirm(
      `¿Revocar la aprobación de '${label}'?\n\n` +
      `ATENCIÓN: Por gobernanza de la Software Factory (AGENTS.md), todas las etapas posteriores deberán ser regeneradas y pasarán automáticamente al estado 'Pendiente'.`
    );
    if (!confirmed) return;
  }
  try {
    const projParam = state.activeProjectName ? `?project=${encodeURIComponent(state.activeProjectName)}` : '';
    const endpoint = approve ? `/api/actions/approve/${stageKey}${projParam}` : `/api/actions/revoke/${stageKey}${projParam}`;
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al cambiar aprobación');
    showToast(data.message, approve ? 'success' : 'info');
    await loadStatus();
    loadArtifactContent(state.selectedArtifact);
    updateStageActionBar(state.selectedArtifact);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openCodeApprovalModal() {
  if (!dom.modalCodeApproval) return;
  try {
    const res = await fetch('/api/actions/preflight_code_check');
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error obteniendo chequeo de código');

    if (dom.codeApprovalAllowedList) {
      dom.codeApprovalAllowedList.innerHTML = '';
      if (data.allowed_to_touch && data.allowed_to_touch.length > 0) {
        data.allowed_to_touch.forEach(file => {
          const li = document.createElement('li');
          li.textContent = `📄 ${file}`;
          dom.codeApprovalAllowedList.appendChild(li);
        });
      } else {
        dom.codeApprovalAllowedList.innerHTML = '<li class="empty-state-small">Sin restricciones específicas declaradas (aplica workspace completo).</li>';
      }
    }

    if (dom.codeApprovalForbiddenList) {
      dom.codeApprovalForbiddenList.innerHTML = '';
      (data.forbidden_directories || []).forEach(dir => {
        const li = document.createElement('li');
        li.textContent = `🔒 ${dir}`;
        dom.codeApprovalForbiddenList.appendChild(li);
      });
    }

    if (dom.codeApprovalMaintContext) {
      dom.codeApprovalMaintContext.classList.toggle('hidden', !data.delta_requirement);
    }

    if (dom.codeApprovalDeltaText) {
      dom.codeApprovalDeltaText.textContent = data.delta_requirement || 'No hay delta de mantenimiento activo. Generación inicial del proyecto.';
    }

    if (dom.codeApprovalPlanText) {
      dom.codeApprovalPlanText.textContent = data.change_plan || 'El plan de cambios se basará en las tareas asignadas en TASKS.md.';
    }

    dom.modalCodeApproval.classList.remove('hidden');
  } catch (err) {
    showToast('Error cargando preflight de código: ' + err.message, 'error');
  }
}

function closeCodeApprovalModal() {
  if (dom.modalCodeApproval) {
    dom.modalCodeApproval.classList.add('hidden');
  }
}

// --- Sugerencia del Siguiente Paso (Next Step Progression 1 a 5 con Compuertas Humanas) ---
function updateNextStepSuggestion() {
  if (state.mode !== 'workspace') {
    dom.nextStepBanner.classList.add('hidden');
    return;
  }

  const s = state.artifactsStatus;
  const approvals = state.humanApprovals || {};

  // Caso A: Lazo de mantenimiento o corrección activo y modificación de fuentes NO aprobada aún
  if (s.delta_requirement && !approvals.code_modification) {
    dom.nextStepTitle.textContent = '🛡️ Compuerta Crítica: Aprobación de Modificación de Fuentes';
    dom.nextStepDesc.textContent = 'Se solicitó una corrección o nuevo requerimiento (DELTA). Antes de que el Programador modifique o agregue archivos en environment/workspace/, debes revisar el impacto y autorizarlo.';
    dom.btnNextStep.textContent = '🛡️ Revisar Impacto y Aprobar Modificación de Fuentes';
    dom.btnNextStep.onclick = () => openCodeApprovalModal();
    dom.nextStepBanner.classList.remove('hidden');
    return;
  }

  // Caso B: Flujo secuencial 1 a 5 con compuertas de aprobación
  if (!s.discovery_notes) {
    dom.nextStepTitle.textContent = 'Etapa 1 Requerida: Discovery & Grilling';
    dom.nextStepDesc.textContent = 'Inicia el asistente para definir los requerimientos, la plataforma y congelar las decisiones iniciales.';
    dom.btnNextStep.textContent = '✨ Iniciar Grill-Me (Etapa 1)';
    dom.btnNextStep.onclick = () => openGrillWizard('active_project');
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!approvals.discovery_notes) {
    dom.nextStepTitle.textContent = 'Compuerta Etapa 1: Aprobación de DISCOVERY_NOTES.md';
    dom.nextStepDesc.textContent = 'El Discovery está generado. Revisa las notas y autoriza el avance hacia el Product Manager.';
    dom.btnNextStep.textContent = '✅ Aprobar Discovery (Etapa 1)';
    dom.btnNextStep.onclick = () => toggleStageApproval('discovery_notes', true);
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.prd) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Etapa 2 (Product Manager)';
    dom.nextStepDesc.textContent = 'El Discovery está aprobado. Genera el PRD.md con las historias de usuario y criterios Gherkin.';
    dom.btnNextStep.textContent = '➡️ Generar PRD (Product Manager)';
    dom.btnNextStep.onclick = async () => {
      await triggerStageGeneration('/api/actions/generate/prd', 'PRD.md generado con éxito por el Product Manager.');
      loadArtifactContent('prd');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!approvals.prd) {
    dom.nextStepTitle.textContent = 'Compuerta Etapa 2: Aprobación de PRD.md';
    dom.nextStepDesc.textContent = 'El PRD ha sido redactado. Revisa los objetivos y criterios Gherkin antes de diseñar la arquitectura.';
    dom.btnNextStep.textContent = '✅ Aprobar PRD (Etapa 2)';
    dom.btnNextStep.onclick = () => toggleStageApproval('prd', true);
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.system_design) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Etapa 3 (Arquitecto de Software)';
    dom.nextStepDesc.textContent = 'El PRD está aprobado. Genera la especificación técnica (SYSTEM_DESIGN.md) y el desglose de tareas.';
    dom.btnNextStep.textContent = '➡️ Diseñar Arquitectura (Arquitecto)';
    dom.btnNextStep.onclick = async () => {
      await triggerStageGeneration('/api/actions/generate/system_design', 'Arquitectura generada con éxito por el Arquitecto.');
      loadArtifactContent('system_design');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!approvals.system_design) {
    dom.nextStepTitle.textContent = 'Compuerta Etapa 3: Aprobación de Arquitectura';
    dom.nextStepDesc.textContent = 'La arquitectura técnica está lista. Revisa el diseño y las tareas antes de autorizar código.';
    dom.btnNextStep.textContent = '✅ Aprobar Arquitectura (Etapa 3)';
    dom.btnNextStep.onclick = () => toggleStageApproval('system_design', true);
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!approvals.code_modification) {
    dom.nextStepTitle.textContent = '🛡️ Compuerta Crítica: Aprobación de Modificación de Fuentes (Etapa 4)';
    dom.nextStepDesc.textContent = 'La arquitectura está aprobada. Antes de que el Programador modifique o escriba código en environment/workspace/, debes revisar la superficie permitida y dar tu aprobación explícita.';
    dom.btnNextStep.textContent = '🛡️ Revisar Impacto y Aprobar Código';
    dom.btnNextStep.onclick = () => openCodeApprovalModal();
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.patch) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Etapa 4 (Programador)';
    dom.nextStepDesc.textContent = 'Modificación de fuentes autorizada. Implementa los modelos, persistencia, servicios y tests en el workspace.';
    dom.btnNextStep.textContent = '💻 Implementar Código en Workspace (Etapa 4)';
    dom.btnNextStep.onclick = async () => {
      await triggerStageGeneration('/api/actions/generate/code', 'Código fuente implementado con éxito por el Programador.');
      loadArtifactContent('patch');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.qa_report) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Etapa 5 (QA & Hostile Auditor)';
    dom.nextStepDesc.textContent = 'Código modificado bajo aprobación humana. Ejecuta la auditoría hostil y la suite de pruebas unitarias.';
    dom.btnNextStep.textContent = '🛡️ Ejecutar Auditoría de QA (Etapa 5)';
    dom.btnNextStep.onclick = async () => {
      await triggerStageGeneration('/api/actions/run_qa', 'Auditoría de QA y suite de pruebas ejecutadas.');
      loadArtifactContent('qa_report');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!approvals.qa_report) {
    dom.nextStepTitle.textContent = 'Compuerta Etapa 5: Aprobación de QA_REPORT.md';
    dom.nextStepDesc.textContent = 'La suite de pruebas y auditoría de drift finalizaron. Revisa los resultados y aprueba la entrega formal.';
    dom.btnNextStep.textContent = '✅ Aprobar Entrega de QA (Etapa 5)';
    dom.btnNextStep.onclick = () => toggleStageApproval('qa_report', true);
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!s.local_runner) {
    dom.nextStepTitle.textContent = 'Siguiente Paso: Etapa 6 (Runner Local - Testing PC)';
    dom.nextStepDesc.textContent = 'Código y pruebas de QA aprobados. Genera el lanzador local (local_runner.py) y el Sandbox Testbench para probar la aplicación en tu PC.';
    dom.btnNextStep.textContent = '⚡ Generar Runner Local de Pruebas (Etapa 6)';
    dom.btnNextStep.onclick = async () => {
      await triggerStageGeneration('/api/actions/generate/local_runner', 'Entorno de pruebas local generado con éxito.');
      loadArtifactContent('local_runner');
    };
    dom.nextStepBanner.classList.remove('hidden');
  } else if (!approvals.local_runner) {
    dom.nextStepTitle.textContent = 'Compuerta Etapa 6: Aprobación del Entorno de Pruebas Local';
    dom.nextStepDesc.textContent = 'El runner local y el testbench han sido generados. Revisa la especificación y aprueba formalmente el entorno local para habilitar la prueba en el navegador.';
    dom.btnNextStep.textContent = '✅ Aprobar Entorno de Pruebas Local (Etapa 6)';
    dom.btnNextStep.onclick = () => toggleStageApproval('local_runner', true);
    dom.nextStepBanner.classList.remove('hidden');
  } else {
    dom.nextStepTitle.textContent = '🎉 ¡Entorno Local Aprobado y Listo para Probar!';
    dom.nextStepDesc.textContent = 'Todas las etapas (1 a 6) han sido validadas por el usuario humano. Puedes probar la aplicación en tu navegador en cualquier momento, solicitar mantenimiento o exportarla.';
    dom.btnNextStep.textContent = '▶️ Probar Aplicación en el Navegador';
    dom.btnNextStep.onclick = () => startAppTestServer();
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

  const skillsContainer = document.getElementById('stage-skills-badges');
  if (skillsContainer) {
    if (cfg.skills && cfg.skills.length > 0) {
      const badgesHtml = cfg.skills.map(s => 
        `<span style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35); color: #c7d2fe; font-size: 0.72rem; padding: 2px 7px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px;" title="${escapeHtml(s.role || '')}">
          <span style="color: #818cf8;">⚡</span> <strong>${escapeHtml(s.name)}</strong> <span style="opacity: 0.7;">v${escapeHtml(s.version)}</span>
        </span>`
      ).join('');
      const agentHtml = cfg.agent ? `<span style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); color: #a7f3d0; font-size: 0.72rem; padding: 2px 7px; border-radius: 4px;">👤 ${escapeHtml(cfg.agent)}</span>` : '';
      skillsContainer.innerHTML = `<span style="font-size: 0.72rem; color: #94a3b8; align-self: center;">Skills Activos:</span> ${badgesHtml} ${agentHtml}`;
      skillsContainer.classList.remove('hidden');
    } else {
      skillsContainer.innerHTML = '';
      skillsContainer.classList.add('hidden');
    }
  }

  if (state.mode === 'git') {
    dom.btnStageAction.textContent = '📥 Restaurar Esta Versión en Workspace';
    dom.btnStageAction.disabled = false;
    dom.btnStageAction.title = 'Restaura los archivos de esta versión en el workspace del proyecto.';
    dom.btnStageAction.onclick = () => restoreCurrentBranch();
    if (dom.stageApprovalBadge) dom.stageApprovalBadge.classList.add('hidden');
    if (dom.btnApproveStage) dom.btnApproveStage.classList.add('hidden');
    return;
  }

  const dep = STAGE_DEPENDENCIES[artifactKey] || { approvalKey: null, prevApprovalKey: null, prevArtifactKey: null, prevName: null };
  const exists = Boolean(state.artifactsStatus[artifactKey]);
  const isApproved = Boolean(dep.approvalKey && state.humanApprovals[dep.approvalKey]);
  const prevApproved = !dep.prevApprovalKey || Boolean(state.humanApprovals[dep.prevApprovalKey]);
  const prevArtifactExists = !dep.prevArtifactKey || Boolean(state.artifactsStatus[dep.prevArtifactKey]);

  // Tres estados posibles de la etapa:
  // 1. Pendiente - No existe
  // 2. Por Aprobar - Existe pero no aprobado por el humano
  // 3. Aprobado - Existe y aprobado por el humano
  let stageState = 1;
  if (exists && isApproved) {
    stageState = 3;
  } else if (exists && !isApproved) {
    stageState = 2;
  } else {
    stageState = 1;
  }

  // 1. Badge de Estado de la Etapa
  if (dom.stageApprovalBadge) {
    dom.stageApprovalBadge.classList.remove('hidden');
    if (stageState === 1) {
      dom.stageApprovalBadge.textContent = '⚪ Estado 1: Pendiente (No existe)';
      dom.stageApprovalBadge.className = 'approval-badge badge-pending';
    } else if (stageState === 2) {
      dom.stageApprovalBadge.textContent = '⏳ Estado 2: Por Aprobar (Requiere Aprobación Humana)';
      dom.stageApprovalBadge.className = 'approval-badge badge-pending-approval';
    } else {
      dom.stageApprovalBadge.textContent = '✅ Estado 3: Aprobado por Humano';
      dom.stageApprovalBadge.className = 'approval-badge badge-approved-human';
    }
  }

  // 2. Botón de Aprobación / Revocación
  if (dom.btnApproveStage && dep.approvalKey) {
    if (stageState === 1) {
      // Estado 1: No existe aún el documento, no hay nada que aprobar
      dom.btnApproveStage.classList.add('hidden');
    } else if (stageState === 2) {
      // Estado 2: Existe pero no aprobado -> Botón para Aprobar
      dom.btnApproveStage.classList.remove('hidden');
      if (dep.approvalKey === 'code_modification') {
        dom.btnApproveStage.textContent = '🛡️ Revisar Impacto y Aprobar Código';
        dom.btnApproveStage.className = 'btn btn-success-action';
        dom.btnApproveStage.onclick = () => openCodeApprovalModal();
      } else {
        dom.btnApproveStage.textContent = '✅ Aprobar Esta Etapa';
        dom.btnApproveStage.className = 'btn btn-success-action';
        dom.btnApproveStage.onclick = () => toggleStageApproval(dep.approvalKey, true);
      }

      // No se puede aprobar si el paso anterior no está en estado 3 (Aprobado)
      if (!prevApproved) {
        dom.btnApproveStage.disabled = true;
        dom.btnApproveStage.title = `Bloqueado: Requiere que la ${dep.prevName} esté Aprobada primero.`;
      } else {
        dom.btnApproveStage.disabled = false;
        dom.btnApproveStage.title = 'Aprobar formalmente esta etapa y habilitar la fase siguiente.';
      }
    } else {
      // Estado 3: Aprobado -> Botón para Revocar Aprobación
      dom.btnApproveStage.classList.remove('hidden');
      dom.btnApproveStage.textContent = '❌ Revocar Aprobación';
      dom.btnApproveStage.className = 'btn btn-secondary';
      dom.btnApproveStage.disabled = false;
      dom.btnApproveStage.title = 'Revoca la aprobación para habilitar la re-ejecución de esta etapa.';
      dom.btnApproveStage.onclick = () => toggleStageApproval(dep.approvalKey, false);
    }
  } else if (dom.btnApproveStage) {
    dom.btnApproveStage.classList.add('hidden');
  }

  // 3. Botón de Generación / Regeneración de la Etapa
  // Regla A: NO puedo generar el documento si está APROBADO (Estado 3). Debe revocarse primero.
  // Regla B: NO puedo generar el documento si NO existe el documento anterior o no está Aprobado.
  if (stageState === 3) {
    // Regla A: Ya está APROBADO
    dom.btnStageAction.disabled = true;
    dom.btnStageAction.textContent = '🔒 Bloqueado: Etapa Aprobada (Revoca para regenerar)';
    dom.btnStageAction.title = 'Esta etapa ya está APROBADA. Para regenerarla, haz clic primero en "Revocar Aprobación".';
    dom.btnStageAction.onclick = null;
  } else if (!prevArtifactExists || !prevApproved) {
    // Regla B: Predecesor no existe o no está en Estado 3 (Aprobado)
    dom.btnStageAction.disabled = true;
    const reason = !prevArtifactExists 
      ? `Falta documento de ${dep.prevName}` 
      : `${dep.prevName} no está Aprobada`;
    dom.btnStageAction.textContent = `🚫 Bloqueado (${reason})`;
    dom.btnStageAction.title = `Hasta que la ${dep.prevName} no esté en estado 3 (Aprobado), no se puede hacer nada con las etapas posteriores.`;
    dom.btnStageAction.onclick = null;
  } else {
    // Permitido generar o re-generar (Estado 1 o Estado 2 con predecesor aprobado)
    dom.btnStageAction.disabled = false;
    dom.btnStageAction.textContent = (stageState === 2) ? `🔄 Re-${cfg.btnText}` : `🚀 ${cfg.btnText}`;
    dom.btnStageAction.title = (stageState === 2)
      ? 'Re-ejecutar la generación de esta etapa.'
      : 'Generar el documento inicial de esta etapa.';
    dom.btnStageAction.onclick = cfg.action;
  }
}

async function triggerStageGeneration(endpoint, successMsg) {
  dom.btnStageAction.disabled = true;
  dom.btnStageAction.textContent = 'Procesando Etapa...';
  if (dom.btnNextStep) {
    dom.btnNextStep.disabled = true;
    dom.btnNextStep.textContent = 'Procesando...';
  }

  try {
    const url = new URL(endpoint, window.location.origin);
    if (state.activeProjectName && !url.searchParams.has('project')) {
      url.searchParams.set('project', state.activeProjectName);
    }
    const res = await fetch(url.toString(), { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Fallo al procesar etapa');

    showToast(successMsg, 'success');
    await loadStatus();
    loadArtifactContent(state.selectedArtifact);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    dom.btnStageAction.disabled = false;
    if (dom.btnNextStep) dom.btnNextStep.disabled = false;
    updateStageActionBar(state.selectedArtifact);
    updateNextStepSuggestion();
  }
}

// --- Selección de Artefactos y Carga de Contenido ---
async function loadArtifactContent(artifactKey) {
  state.selectedArtifact = artifactKey;
  dom.bcFilename.textContent = ARTIFACT_NAMES[artifactKey] || artifactKey;

  // Actualizar clase activa en árbol de archivos y menú lateral de etapas
  const parentStageKey = (artifactKey === 'tasks') ? 'system_design' : (artifactKey === 'change_plan') ? 'patch' : artifactKey;
  dom.artifactItems.forEach(el => el.classList.toggle('active', el.dataset.artifact === artifactKey));
  dom.stepCards.forEach(el => el.classList.toggle('active', el.dataset.stage === parentStageKey));

  updateStageActionBar(artifactKey);

  try {
    let content = '';
    if (state.mode === 'workspace') {
      const pName = state.activeProjectName || state.activeProject?.project_name || 'app';
      dom.bcOrigin.textContent = `projects/${pName}`;
      const projParam = state.activeProjectName ? `?project=${encodeURIComponent(state.activeProjectName)}` : '';
      const res = await fetch(`/api/artifacts/${artifactKey}${projParam}`);
      if (!res.ok) {
        throw new Error(`Artefacto '${artifactKey}' aún no ha sido generado en esta etapa.`);
      }
      const data = await res.json();
      if (data.exists === false) {
        throw new Error(data.message || `Artefacto '${artifactKey}' aún no ha sido generado para el proyecto '${pName}'.`);
      }
      content = data.content;
    } else {
      dom.bcOrigin.textContent = `Git: ${state.selectedBranch}`;
      const res = await fetch(`/api/git/branch/${encodeURIComponent(state.selectedBranch)}/artifacts`);
      if (!res.ok) {
        throw new Error(`No se encontraron artefactos en la rama '${state.selectedBranch}'.`);
      }
      const data = await res.json();
      content = data.artifacts[artifactKey];
      if (!content && artifactKey === 'patch') {
        try {
          const diffRes = await fetch(`/api/git/branch/${encodeURIComponent(state.selectedBranch)}/diff`);
          if (diffRes.ok) {
            const diffData = await diffRes.json();
            if (diffData.diff) {
              content = "```diff\n" + diffData.diff + "\n```";
            }
          }
        } catch (_) {}
      }
      if (!content) {
        content = `El archivo ${artifactKey} no existe en este commit histórico.`;
      }
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
      selectGitBranch(state.branches[0].commit);
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
    state.branches = data.branches || [];
    if (dom.branchCount) dom.branchCount.textContent = state.branches.length;
    if (dom.launcherGitCount) dom.launcherGitCount.textContent = state.branches.length;

    dom.branchList.innerHTML = '';
    if (state.branches.length === 0) {
      dom.branchList.innerHTML = '<div class="empty-state-small">Sin commits aún en este proyecto.</div>';
    } else {
      state.branches.forEach(b => {
        const card = document.createElement('div');
        card.className = `branch-card ${b.commit === state.selectedBranch ? 'active' : ''}`;
        card.dataset.commit = b.commit;
        card.innerHTML = `
          <div class="branch-header">
            <span class="branch-title">${escapeHtml(b.subject)}</span>
            <span class="branch-date">${escapeHtml(b.date)}</span>
          </div>
          <div class="branch-commit"><code>#${escapeHtml(b.commit)}</code> ${escapeHtml(b.ref_info ? `· ${b.ref_info}` : '')}</div>
        `;
        card.addEventListener('click', () => selectGitBranch(b.commit, b.subject));
        dom.branchList.appendChild(card);
      });
    }

    renderLauncherGitList(state.branches);
  } catch (err) {
    console.error('Error cargando git overview:', err);
  }
}

function renderLauncherGitList(branches) {
  if (!dom.launcherGitList) return;
  dom.launcherGitList.innerHTML = '';

  if (!branches || branches.length === 0) {
    dom.launcherGitList.innerHTML = '<div class="empty-state-small">No hay commits registrados en este proyecto aún.</div>';
    return;
  }

  branches.forEach(b => {
    const item = document.createElement('div');
    item.className = 'launcher-git-item';
    item.innerHTML = `
      <div class="launcher-git-meta">
        <span class="launcher-git-name">${escapeHtml(b.subject)}</span>
        <span class="launcher-git-desc">Commit <code>#${escapeHtml(b.commit)}</code> (${escapeHtml(b.date)})</span>
      </div>
      <div style="display: flex; gap: 6px; align-items: center;">
        <button class="btn btn-secondary-sm btn-inspect-launcher" data-branch="${escapeHtml(b.commit)}">
          🔍 Ver en Git
        </button>
        <button class="btn btn-warning-sm btn-restore-launcher" data-branch="${escapeHtml(b.commit)}" title="Restaurar este commit en el workspace del proyecto">
          ⏪ Restaurar
        </button>
      </div>
    `;
    item.querySelector('.btn-inspect-launcher').addEventListener('click', (e) => {
      e.stopPropagation();
      closeProjectLauncher();
      setInspectionMode('git');
      selectGitBranch(b.commit, b.subject);
    });
    item.querySelector('.btn-restore-launcher').addEventListener('click', async (e) => {
      e.stopPropagation();
      await restoreSpecificBranch(b.commit);
      closeProjectLauncher();
    });
    dom.launcherGitList.appendChild(item);
  });
}

function selectGitBranch(commitHash, title) {
  state.selectedBranch = commitHash;
  const commitObj = state.branches.find(b => b.commit === commitHash);
  const displayTitle = title || (commitObj ? commitObj.subject : commitHash);
  dom.bannerBranchName.textContent = `${displayTitle} (#${commitHash})`;
  dom.gitBranchBanner.classList.remove('hidden');

  document.querySelectorAll('.branch-card').forEach(card => {
    card.classList.toggle('active', card.dataset.commit === commitHash);
  });

  loadArtifactContent(state.selectedArtifact);
  updateNextStepSuggestion();
}

async function restoreSpecificBranch(branchName) {
  const pName = state.activeProject?.project_name || 'proyecto actual';
  if (!confirm(`¿Deseas restaurar los archivos del proyecto '${pName}' al commit '${branchName}'?\n\nSoftFactory permanecerá 100% intacta.`)) return;

  try {
    const res = await fetch(`/api/git/branch/${encodeURIComponent(branchName)}/restore`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Fallo al restaurar');
    showToast(data.message, 'success');
    setInspectionMode('workspace');
    await loadStatus();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function restoreCurrentBranch() {
  if (!state.selectedBranch) return;
  await restoreSpecificBranch(state.selectedBranch);
}

// --- GESTIÓN DE PROYECTOS AISLADOS (MULTI-PROJECT HUB) ---
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderProjectsGrid(projects, activeName) {
  if (!dom.launcherProjectsGrid) return;
  if (!projects || projects.length === 0) {
    dom.launcherProjectsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 24px; color: var(--text-dim);">
        No hay proyectos en <code>projects/</code>. Haz clic en <strong>Nuevo Proyecto</strong> para comenzar.
      </div>`;
    return;
  }

  dom.launcherProjectsGrid.innerHTML = projects.map(p => {
    const isActive = (p.name === activeName);
    return `
      <div class="project-card ${isActive ? 'active-project' : ''}">
        <div class="project-card-header">
          <div class="project-card-title">
            <span>📁</span> <strong>${escapeHtml(p.name)}</strong>
          </div>
          ${isActive ? '<span class="badge-active-tag">Activo</span>' : ''}
        </div>
        <div class="project-card-path">projects/${escapeHtml(p.name)}</div>
        <div class="project-card-stats">
          <span>⚡ <strong style="color: #a5b4fc;">${escapeHtml(p.status)}</strong></span>
          <span>📄 ${p.workspace_files_count} archivos</span>
        </div>
        <div style="font-size: 0.72rem; color: var(--text-dim);">
          Etapas: ${p.completed_stages}/5 completadas · Modif: ${p.modified_at}
        </div>
        <div class="project-card-actions">
          <button class="btn-open-proj" onclick="selectProject('${escapeHtml(p.name)}')">
            ${isActive ? '✓ Proyecto Activo' : '📂 Abrir Proyecto'}
          </button>
          <button class="btn-delete-proj" title="Eliminar carpeta del proyecto del disco" onclick="deleteProject('${escapeHtml(p.name)}')">
            🗑️
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function loadProjects() {
  try {
    const res = await fetch('/api/projects');
    const data = await res.json();
    state.projects = data.projects || [];
    renderProjectsGrid(state.projects, data.active_project);
  } catch (err) {
    console.error('Error al cargar lista de proyectos:', err);
  }
}

async function selectProject(projectName) {
  try {
    const res = await fetch('/api/projects/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_name: projectName }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al seleccionar proyecto');
    state.activeProjectName = data.active_project || projectName;
    showToast(data.message, 'success');
    closeProjectLauncher();
    await loadStatus();
    await loadGitOverview();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteProject(projectName) {
  if (!confirm(`¿Estás seguro de que deseas eliminar permanentemente la carpeta projects/${projectName}/ y todo su contenido?\n\nLa Software Factory y los demás proyectos permanecerán intactos.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/projects/${encodeURIComponent(projectName)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al eliminar proyecto');
    showToast(data.message, 'success');
    await loadStatus();
    await loadProjects();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

window.selectProject = selectProject;
window.deleteProject = deleteProject;

// --- CONTROLES DEL LANZADOR DE SESIÓN (PROYECTOS) ---
function openProjectLauncher() {
  if (dom.modalProjectLauncher) {
    dom.modalProjectLauncher.classList.remove('hidden');
    loadProjects();
  }
}

function closeProjectLauncher() {
  if (dom.modalProjectLauncher) {
    dom.modalProjectLauncher.classList.add('hidden');
    sessionStorage.setItem('launcher_dismissed', 'true');
  }
}

if (dom.btnOpenLauncher) dom.btnOpenLauncher.addEventListener('click', openProjectLauncher);
if (dom.btnCloseLauncher) dom.btnCloseLauncher.addEventListener('click', closeProjectLauncher);
if (dom.btnLauncherContinue) dom.btnLauncherContinue.addEventListener('click', closeProjectLauncher);
if (dom.btnLauncherNewApp) {
  dom.btnLauncherNewApp.addEventListener('click', () => {
    closeProjectLauncher();
    openNewAppConfirmation();
  });
}

// --- CONTROLES DEL LAZO DE MANTENIMIENTO ---
function openMaintenanceModal() {
  if (dom.modalMaintenance) {
    dom.modalMaintenance.classList.remove('hidden');
  }
}

function closeMaintenanceModal() {
  if (dom.modalMaintenance) {
    dom.modalMaintenance.classList.add('hidden');
  }
}

if (dom.btnOpenMaintenance) dom.btnOpenMaintenance.addEventListener('click', openMaintenanceModal);
if (dom.btnCloseMaintenance) dom.btnCloseMaintenance.addEventListener('click', closeMaintenanceModal);
if (dom.btnCancelMaintenance) dom.btnCancelMaintenance.addEventListener('click', closeMaintenanceModal);

const maintTypeSelect = document.getElementById('maint-type');
if (maintTypeSelect) {
  maintTypeSelect.addEventListener('change', () => {
    if (maintTypeSelect.value === 'skill') {
      if (dom.maintSkillRedirectBox) dom.maintSkillRedirectBox.classList.remove('hidden');
    } else {
      if (dom.maintSkillRedirectBox) dom.maintSkillRedirectBox.classList.add('hidden');
    }
  });
}
if (dom.maintOpenSkillsLink) {
  dom.maintOpenSkillsLink.addEventListener('click', (e) => {
    e.preventDefault();
    closeMaintenanceModal();
    openSkillsModal();
  });
}

if (dom.btnSubmitMaintenance) {
  dom.btnSubmitMaintenance.addEventListener('click', async () => {
    const request_type = document.getElementById('maint-type').value;
    const title = document.getElementById('maint-title').value.trim();
    const description = document.getElementById('maint-desc').value.trim();

    if (!title || !description) {
      alert('Por favor ingresa un título y una descripción detallada.');
      return;
    }

    dom.btnSubmitMaintenance.disabled = true;
    dom.btnSubmitMaintenance.textContent = 'Procesando...';

    try {
      if (request_type === 'skill') {
        // Guardar como propuesta de skill de proyecto
        const skillName = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'custom-rule';
        const res = await fetch('/api/skills/project/propose', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: skillName,
            description: title,
            applies_to_stages: ['prd', 'system_design', 'code_modification', 'qa_report'],
            instructions_md: `## Regla del Proyecto: ${title}\n\n${description}\n`,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al proponer skill');
        showToast(data.message, 'success');
        closeMaintenanceModal();
        document.getElementById('maint-title').value = '';
        document.getElementById('maint-desc').value = '';
        openSkillsModal();
      } else {
        const res = await fetch('/api/actions/maintenance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ request_type, title, description }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error al registrar mantenimiento');

        showToast(data.message, 'success');
        closeMaintenanceModal();
        document.getElementById('maint-title').value = '';
        document.getElementById('maint-desc').value = '';
        await loadStatus();
        loadArtifactContent('delta_requirement');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      dom.btnSubmitMaintenance.disabled = false;
      dom.btnSubmitMaintenance.textContent = '🚀 Activar Lazo de Mantenimiento';
    }
  });
}

// --- GESTIÓN DE SKILLS Y REGLAS DE DISEÑO ---
function openSkillsModal() {
  if (dom.modalSkills) {
    dom.modalSkills.classList.remove('hidden');
    const pname = state.activeProject?.project_name || 'Sin Proyecto';
    if (dom.skillsModalPname) dom.skillsModalPname.textContent = pname;
    loadSkills();
  }
}

function closeSkillsModal() {
  if (dom.modalSkills) {
    dom.modalSkills.classList.add('hidden');
    if (dom.newSkillFormBox) dom.newSkillFormBox.classList.add('hidden');
  }
}

async function loadSkills() {
  try {
    const res = await fetch('/api/skills');
    const data = await res.json();
    renderSkills(data.global_skills || [], data.project_skills || []);
  } catch (err) {
    showToast('Error al cargar skills: ' + err.message, 'error');
  }
}

function renderSkills(globals, projects) {
  if (dom.globalSkillsCount) dom.globalSkillsCount.textContent = globals.length;
  if (dom.projectSkillsCount) dom.projectSkillsCount.textContent = projects.length;

  // Renderizar Globales
  if (dom.globalSkillsList) {
    if (!globals.length) {
      dom.globalSkillsList.innerHTML = '<div style="font-size: 0.8rem; color: #64748b; font-style: italic;">No hay skills globales cargados.</div>';
    } else {
      dom.globalSkillsList.innerHTML = globals.map(s => `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
            <div style="font-weight: 600; color: #34d399; font-size: 0.88rem;">🌐 ${escapeHtml(s.name)} <span style="font-size: 0.72rem; color: #94a3b8; font-weight: normal;">v${escapeHtml(s.version || '1.0.0')}</span></div>
            <span class="badge-stage" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 0.68rem; padding: 2px 8px;">GLOBAL</span>
          </div>
          <p style="font-size: 0.78rem; color: #cbd5e1; margin-bottom: 6px;">${escapeHtml(s.description)}</p>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            ${(s.applies_to_stages || []).map(st => `<span style="font-size: 0.68rem; background: rgba(51, 65, 85, 0.6); color: #94a3b8; padding: 1px 6px; border-radius: 4px;">${escapeHtml(st)}</span>`).join('')}
          </div>
        </div>
      `).join('');
    }
  }

  // Renderizar Proyecto
  if (dom.projectSkillsList) {
    if (!projects.length) {
      dom.projectSkillsList.innerHTML = '<div style="font-size: 0.8rem; color: #64748b; font-style: italic;">No hay skills exclusivos configurados en este proyecto. Puedes proponer uno con el botón de arriba.</div>';
    } else {
      dom.projectSkillsList.innerHTML = projects.map(s => {
        const isApproved = s.status === 'approved';
        const isRevoked = s.status === 'revoked';
        const statusBadge = isApproved
          ? '<span class="badge-stage" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 0.7rem;">✅ Aprobado (Activo)</span>'
          : (isRevoked
            ? '<span class="badge-stage" style="background: rgba(239, 68, 68, 0.2); color: #f87171; font-size: 0.7rem;">⏸️ Revocado</span>'
            : '<span class="badge-stage" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; font-size: 0.7rem;">⏳ Propuesto (Inactivo)</span>');

        let actionButtons = '';
        if (isApproved) {
          actionButtons = `
            <button class="btn btn-secondary btn-sm" onclick="handleRevokeSkill('${escapeHtml(s.name)}')" title="Revoca la restricción e invalida etapas afectadas">⏸️ Revocar</button>
            <button class="btn btn-secondary btn-sm" onclick="handlePromoteSkill('${escapeHtml(s.name)}')" title="Proponer para que forme parte del motor global de la Software Factory">⬆️ Proponer a Global</button>
          `;
        } else if (isRevoked) {
          actionButtons = `
            <button class="btn btn-primary btn-sm" onclick="handleApproveSkill('${escapeHtml(s.name)}')" title="Re-activa el skill e invalida etapas posteriores">🔄 Re-aprobar</button>
            <button class="btn btn-danger-ghost btn-sm" onclick="handleDeleteSkill('${escapeHtml(s.name)}')">🗑️</button>
          `;
        } else {
          actionButtons = `
            <button class="btn btn-primary btn-sm" onclick="handleApproveSkill('${escapeHtml(s.name)}')" title="Aprueba el skill e invalida en cascada las etapas afectadas para regenerarlas">✅ Aprobar (Invalida Etapas)</button>
            <button class="btn btn-danger-ghost btn-sm" onclick="handleDeleteSkill('${escapeHtml(s.name)}')">🗑️</button>
          `;
        }

        return `
          <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid ${isApproved ? '#38bdf8' : 'var(--border-subtle)'}; border-radius: 8px; padding: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
              <div>
                <strong style="color: #67e8f9; font-size: 0.88rem;">📁 ${escapeHtml(s.name)}</strong>
                <span style="font-size: 0.72rem; color: #94a3b8; margin-left: 6px;">v${escapeHtml(s.version || '0.1.0')}</span>
              </div>
              <div>${statusBadge}</div>
            </div>
            <p style="font-size: 0.78rem; color: #cbd5e1; margin-bottom: 8px;">${escapeHtml(s.description)}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
              <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                ${(s.applies_to_stages || []).map(st => `<span style="font-size: 0.68rem; background: rgba(56, 189, 248, 0.15); color: #7dd3fc; padding: 1px 6px; border-radius: 4px;">${escapeHtml(st)}</span>`).join('')}
              </div>
              <div style="display: flex; gap: 6px;">
                ${actionButtons}
              </div>
            </div>
          </div>
        `;
      }).join('');
    }
  }
}

// Handlers globales para skills
window.handleApproveSkill = async function(name) {
  if (!confirm(`¿Aprobar el skill '${name}'?\n\nATENCIÓN: Por gobernanza de la Software Factory, todas las etapas afectadas y sus posteriores pasarán a estado 'Pendiente' (sus artefactos se archivarán) para ser regeneradas aplicando estas nuevas restricciones.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/skills/project/${encodeURIComponent(name)}/approve`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al aprobar skill');
    showToast(`Skill '${name}' aprobado. Etapas a regenerar: ${data.invalidated_stages.join(', ')}`, 'success');
    await loadStatus();
    await loadSkills();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.handleRevokeSkill = async function(name) {
  if (!confirm(`¿Revocar el skill '${name}'?\n\nLas etapas afectadas pasarán a estado 'Pendiente' para regenerarse sin este skill.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/skills/project/${encodeURIComponent(name)}/revoke`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al revocar skill');
    showToast(`Skill '${name}' revocado. Etapas a regenerar: ${data.invalidated_stages.join(', ')}`, 'info');
    await loadStatus();
    await loadSkills();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.handleDeleteSkill = async function(name) {
  if (!confirm(`¿Eliminar definitivamente el skill de proyecto '${name}'?`)) {
    return;
  }
  try {
    const res = await fetch(`/api/skills/project/${encodeURIComponent(name)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al eliminar skill');
    showToast(data.message, 'success');
    await loadSkills();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

window.handlePromoteSkill = async function(name) {
  if (!confirm(`¿Proponer la promoción del skill '${name}' a la Software Factory global?\n\nQuedará registrada una propuesta en factory/skill_proposals/ para evaluación del usuario/administrador.`)) {
    return;
  }
  try {
    const res = await fetch(`/api/skills/project/${encodeURIComponent(name)}/promote`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al proponer promoción');
    showToast(`Propuesta de promoción registrada en ${data.file}`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
};

if (dom.btnOpenSkills) dom.btnOpenSkills.addEventListener('click', openSkillsModal);
if (dom.btnCloseSkills) dom.btnCloseSkills.addEventListener('click', closeSkillsModal);
if (dom.btnCloseSkillsFooter) dom.btnCloseSkillsFooter.addEventListener('click', closeSkillsModal);

if (dom.btnToggleNewSkillForm) {
  dom.btnToggleNewSkillForm.addEventListener('click', () => {
    if (dom.newSkillFormBox) dom.newSkillFormBox.classList.toggle('hidden');
  });
}
if (dom.btnCancelNewSkill) {
  dom.btnCancelNewSkill.addEventListener('click', () => {
    if (dom.newSkillFormBox) dom.newSkillFormBox.classList.add('hidden');
  });
}
if (dom.btnSubmitNewSkill) {
  dom.btnSubmitNewSkill.addEventListener('click', async () => {
    const name = dom.newSkillName.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const description = dom.newSkillDesc.value.trim();
    const instructions_md = dom.newSkillBody.value.trim();
    const checkedStages = Array.from(document.querySelectorAll('input[name="skill-stage"]:checked')).map(cb => cb.value);

    if (!name || !description || !instructions_md) {
      alert('Por favor completa el nombre, descripción e instrucciones del skill.');
      return;
    }
    if (!checkedStages.length) {
      alert('Selecciona al menos una etapa a la que aplicará el skill.');
      return;
    }

    dom.btnSubmitNewSkill.disabled = true;
    try {
      const res = await fetch('/api/skills/project/propose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description,
          applies_to_stages: checkedStages,
          instructions_md,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al proponer skill');
      showToast(data.message, 'success');
      dom.newSkillName.value = '';
      dom.newSkillDesc.value = '';
      dom.newSkillBody.value = '';
      if (dom.newSkillFormBox) dom.newSkillFormBox.classList.add('hidden');
      await loadSkills();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      dom.btnSubmitNewSkill.disabled = false;
    }
  });
}

// --- MODAL DE LECCIONES DEL MOTOR (EVOLUCIÓN FACTORY) ---
function openLessonModal() {
  if (dom.modalLesson) dom.modalLesson.classList.remove('hidden');
}
function closeLessonModal() {
  if (dom.modalLesson) dom.modalLesson.classList.add('hidden');
}

if (dom.btnOpenLesson) dom.btnOpenLesson.addEventListener('click', openLessonModal);
if (dom.btnCloseLesson) dom.btnCloseLesson.addEventListener('click', closeLessonModal);
if (dom.btnCancelLesson) dom.btnCancelLesson.addEventListener('click', closeLessonModal);

if (dom.btnSubmitLesson) {
  dom.btnSubmitLesson.addEventListener('click', async () => {
    const stage = dom.lessonStage.value;
    const target = dom.lessonTarget.value;
    const symptom = dom.lessonSymptom.value.trim();
    const root_cause = dom.lessonCause.value.trim();
    const proposal = dom.lessonProposal.value.trim();

    if (!symptom) {
      alert('Por favor describe el síntoma o fallo observado.');
      return;
    }

    dom.btnSubmitLesson.disabled = true;
    try {
      const res = await fetch('/api/factory/lessons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage, target, symptom, root_cause, proposal }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al registrar lección');
      showToast('Lección registrada exitosamente en FACTORY_LESSONS.md', 'success');
      dom.lessonSymptom.value = '';
      dom.lessonCause.value = '';
      dom.lessonProposal.value = '';
      closeLessonModal();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      dom.btnSubmitLesson.disabled = false;
    }
  });
}


// --- CONTROLES DE LA COMPUERTA DE APROBACIÓN DE CÓDIGO ---
if (dom.btnCloseCodeApproval) dom.btnCloseCodeApproval.addEventListener('click', closeCodeApprovalModal);
if (dom.btnRejectCodeApproval) {
  dom.btnRejectCodeApproval.addEventListener('click', async () => {
    await toggleStageApproval('code_modification', false);
    closeCodeApprovalModal();
  });
}
if (dom.btnConfirmCodeApproval) {
  dom.btnConfirmCodeApproval.addEventListener('click', async () => {
    dom.btnConfirmCodeApproval.disabled = true;
    dom.btnConfirmCodeApproval.textContent = 'Implementando Código...';
    try {
      await toggleStageApproval('code_modification', true);
      await triggerStageGeneration('/api/actions/generate/code', 'Código fuente implementado con éxito en el workspace.');
      closeCodeApprovalModal();
      loadArtifactContent('patch');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      dom.btnConfirmCodeApproval.disabled = false;
      dom.btnConfirmCodeApproval.textContent = '✅ Aprobar y Autorizar Modificación de Fuentes';
    }
  });
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
  openGrillWizard('new_app');
});

function selectMatchingOption(selectElem, targetValue) {
  if (!selectElem || !targetValue) return false;
  const target = String(targetValue).trim().toLowerCase();
  if (!target) return false;

  // 1. Coincidencia exacta con valor o texto
  for (let i = 0; i < selectElem.options.length; i++) {
    const opt = selectElem.options[i];
    const val = (opt.value || '').trim().toLowerCase();
    const txt = (opt.text || '').trim().toLowerCase();
    if (val === target || txt === target) {
      selectElem.selectedIndex = i;
      return true;
    }
  }

  // 2. Coincidencia por contención parcial
  for (let i = 0; i < selectElem.options.length; i++) {
    const opt = selectElem.options[i];
    const val = (opt.value || '').trim().toLowerCase();
    const txt = (opt.text || '').trim().toLowerCase();
    if (val && (val.includes(target) || target.includes(val))) {
      selectElem.selectedIndex = i;
      return true;
    }
    if (txt && (txt.includes(target) || target.includes(txt))) {
      selectElem.selectedIndex = i;
      return true;
    }
  }

  // 3. Coincidencia semántica / tokens de palabras clave
  const targetTokens = target.replace(/[^a-z0-9áéíóúñ]/gi, ' ').split(/\s+/).filter(w => w.length >= 3);
  let bestIndex = -1;
  let maxScore = 0;

  for (let i = 0; i < selectElem.options.length; i++) {
    const opt = selectElem.options[i];
    const combined = `${opt.value} ${opt.text}`.toLowerCase();
    let score = 0;
    for (const t of targetTokens) {
      if (combined.includes(t)) score++;
    }
    if (score > maxScore) {
      maxScore = score;
      bestIndex = i;
    }
  }

  if (bestIndex !== -1 && maxScore > 0) {
    selectElem.selectedIndex = bestIndex;
    return true;
  }
  return false;
}

function adaptWizardSmartDefaults(text) {
  const low = (text || '').toLowerCase();
  const platformSelect = document.getElementById('grill-opt-platform');
  const uiLayoutSelect = document.getElementById('grill-opt-ui-layout');
  const entitiesInput = document.getElementById('grill-opt-entities');

  const isWeather = low.includes('clima') || low.includes('tiempo') || low.includes('meteorol') || low.includes('weather') || low.includes('pronostico') || low.includes('pronóstico');
  const wantsScreen = low.includes('pantalla') || low.includes('interfaz') || low.includes('frontend') || low.includes('ui') || low.includes('vista') || low.includes('dashboard') || low.includes('web');

  if (isWeather) {
    if (platformSelect) selectMatchingOption(platformSelect, 'web_spa');
    if (uiLayoutSelect) selectMatchingOption(uiLayoutSelect, 'weather_dashboard');
    if (entitiesInput && (entitiesInput.value === 'Productos, Clientes, Facturas' || entitiesInput.dataset.autoFilled === 'true' || !entitiesInput.value.trim())) {
      entitiesInput.value = 'Ciudades, Pronósticos, ClimaActual';
      entitiesInput.dataset.autoFilled = 'true';
    }
  } else if (wantsScreen) {
    if (platformSelect && platformSelect.value === 'web_rest') selectMatchingOption(platformSelect, 'web_spa');
    if (uiLayoutSelect && uiLayoutSelect.value === 'none_headless') {
      selectMatchingOption(uiLayoutSelect, 'interactive_dashboard');
    }
    if (entitiesInput && (entitiesInput.value === 'Productos, Clientes, Facturas' || entitiesInput.dataset.autoFilled === 'true')) {
      entitiesInput.value = 'Vistas, Componentes, Métricas';
      entitiesInput.dataset.autoFilled = 'true';
    }
  }
}

async function openGrillWizard(mode = 'active_project') {
  state.grillMode = mode;
  state.wizardStep = 1;

  const projInput = document.getElementById('grill-proj-name');
  const projHint = document.getElementById('grill-proj-hint');
  const projLabel = document.getElementById('lbl-grill-proj-name');
  const modalTitle = document.querySelector('#modal-grill .modal-title-group h3');
  const modalSub = document.querySelector('#modal-grill .modal-title-group p');
  const promptInput = document.getElementById('grill-prompt');
  const platformSelect = document.getElementById('grill-opt-platform');
  const uiLayoutSelect = document.getElementById('grill-opt-ui-layout');
  const entitiesInput = document.getElementById('grill-opt-entities');
  const authSelect = document.getElementById('grill-opt-auth');
  const errorsSelect = document.getElementById('grill-opt-errors');
  const persistenceSelect = document.getElementById('grill-opt-persistence');
  const cachingSelect = document.getElementById('grill-opt-caching');

  // Reactividad en vivo al escribir en el prompt inicial
  if (promptInput) {
    promptInput.oninput = () => adaptWizardSmartDefaults(promptInput.value);
  }
  if (entitiesInput) {
    entitiesInput.oninput = () => { entitiesInput.dataset.autoFilled = 'false'; };
  }

  const activeName = state.activeProjectName || state.activeProject?.project_name || 'app';

  if (mode === 'active_project') {
    if (modalTitle) modalTitle.textContent = `✨ Elicitación Grill-Me (Etapa 1): ${activeName}`;
    if (modalSub) modalSub.textContent = `Revisando o re-ejecutando decisiones para '${activeName}'.`;
    if (projLabel) projLabel.innerHTML = `<strong>Proyecto Seleccionado:</strong>`;
    if (projInput) {
      projInput.value = activeName;
      projInput.disabled = true;
    }
    if (projHint) projHint.innerHTML = `🔒 Se ejecutará sobre el proyecto activo <code>projects/${escapeHtml(activeName)}/</code> sin crear nuevos proyectos ni reiniciar nada.`;
    
    // Si el proyecto tiene requerimiento inicial guardado, pre-cargar si el campo está vacío
    if (!promptInput.value.trim() && state.activeProject?.context?.project_metadata?.seed_requirement) {
      promptInput.value = state.activeProject.context.project_metadata.seed_requirement;
    }

    // Pre-cargar valores existentes desde DISCOVERY_NOTES.md si ya existe en el proyecto activo
    try {
      const res = await fetch(`/api/artifacts/discovery_notes?project=${encodeURIComponent(activeName)}`);
      const data = await res.json();
      if (data && data.exists && data.parsed_answers) {
        const a = data.parsed_answers;
        if (a.prompt && promptInput) promptInput.value = a.prompt;
        if (a.api_style && platformSelect) selectMatchingOption(platformSelect, a.api_style);
        if (a.ui_layout && uiLayoutSelect) selectMatchingOption(uiLayoutSelect, a.ui_layout);
        if (a.entities && entitiesInput) entitiesInput.value = a.entities;
        if (a.auth_scheme && authSelect) selectMatchingOption(authSelect, a.auth_scheme);
        if (a.error_format && errorsSelect) selectMatchingOption(errorsSelect, a.error_format);
        if (a.persistence && persistenceSelect) selectMatchingOption(persistenceSelect, a.persistence);
        if (a.caching && cachingSelect) selectMatchingOption(cachingSelect, a.caching);

        if (projHint) {
          projHint.innerHTML = `🔒 Proyecto activo <code>projects/${escapeHtml(activeName)}/</code>. Decisiones pre-cargadas desde <code>DISCOVERY_NOTES.md</code>.`;
        }
      }
    } catch (err) {
      console.warn("No se pudieron pre-cargar respuestas previas de DISCOVERY_NOTES.md:", err);
    }
  } else {
    // Modo: 'new_app' (disparado exclusivamente desde "Nueva App")
    if (modalTitle) modalTitle.textContent = '✨ Nuevo Proyecto Aislado (Grill-Me)';
    if (modalSub) modalSub.textContent = 'Aislamiento total en carpeta dedicada dentro de projects/. SoftFactory no se modifica.';
    if (projLabel) projLabel.innerHTML = `<strong>Nombre del Nuevo Proyecto:</strong>`;
    if (projInput) {
      projInput.value = '';
      projInput.disabled = false;
      projInput.placeholder = 'Ej: Inventario Taller';
    }
    if (projHint) projHint.innerHTML = `📁 Se creará la carpeta aislada <code>projects/&lt;nombre&gt;/</code> sin alterar archivos de SoftFactory.`;
    if (promptInput) promptInput.value = '';
    if (platformSelect) platformSelect.selectedIndex = 0;
    if (uiLayoutSelect) uiLayoutSelect.selectedIndex = 1;
    if (entitiesInput) {
      entitiesInput.value = 'Productos, Clientes, Facturas';
      entitiesInput.dataset.autoFilled = 'true';
    }
    if (authSelect) authSelect.selectedIndex = 0;
    if (errorsSelect) errorsSelect.selectedIndex = 0;
    if (persistenceSelect) persistenceSelect.selectedIndex = 0;
    if (cachingSelect) cachingSelect.selectedIndex = 0;
  }

  // Ejecutar adaptación reactiva inicial por si ya había texto
  if (promptInput && promptInput.value.trim()) {
    adaptWizardSmartDefaults(promptInput.value);
  }

  // Cargar skills activos y verificar árbol de preguntas
  try {
    const qRes = await fetch(`/api/grill/questions?project=${encodeURIComponent(activeName)}`);
    const qData = await qRes.json();
    if (qData && qData.skills) {
      const banner = document.getElementById('grill-skills-banner');
      if (banner) {
        const skillsTags = qData.skills.map(s => `<code style="background: rgba(0,0,0,0.35); padding: 2px 7px; border-radius: 4px; color: #c7d2fe;">${escapeHtml(s.name)} v${escapeHtml(s.version)} (${escapeHtml(s.scope)})</code>`).join(' ');
        banner.innerHTML = `
          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="font-size: 1.15rem;">⚡</span>
            <span><strong>Skills Activos:</strong> ${skillsTags}</span>
          </div>
          <span style="color: #cbd5e1; font-size: 0.78rem; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); padding: 2px 8px; border-radius: 4px;">👤 Agente: <strong>Rita (Discovery)</strong></span>
        `;
      }
    }
  } catch (e) {
    console.warn("No se pudieron cargar skills de grill:", e);
  }

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
    // Asegurar que las recomendaciones inteligentes se sincronicen antes de pasar al paso 2
    adaptWizardSmartDefaults(prompt);
  }
  if (state.wizardStep < 4) showWizardStep(state.wizardStep + 1);
});

function buildWizardSummary() {
  const platform = document.getElementById('grill-opt-platform').options[document.getElementById('grill-opt-platform').selectedIndex].text;
  const uiLayoutEl = document.getElementById('grill-opt-ui-layout');
  const uiLayout = uiLayoutEl ? uiLayoutEl.options[uiLayoutEl.selectedIndex].text : 'Dashboard Web Interactivo';
  const entities = document.getElementById('grill-opt-entities').value;
  const auth = document.getElementById('grill-opt-auth').value;
  const errors = document.getElementById('grill-opt-errors').value;
  const persistence = document.getElementById('grill-opt-persistence').value;
  const caching = document.getElementById('grill-opt-caching').value;
  const isNew = (state.grillMode === 'new_app');
  const projName = isNew 
    ? (document.getElementById('grill-proj-name').value.trim() || 'nueva_app')
    : (state.activeProjectName || state.activeProject?.project_name || 'app');
  const prompt = document.getElementById('grill-prompt').value.trim();

  dom.grillSummaryContent.innerHTML = `
    <div><strong>Modo:</strong> <span class="badge-${isNew ? 'initialized' : 'active-tag'}">${isNew ? 'Nuevo Proyecto' : 'Proyecto Activo'}</span></div>
    <div><strong>Proyecto:</strong> <code>projects/${escapeHtml(projName)}/</code></div>
    <div><strong>Requerimiento:</strong> "${escapeHtml(prompt)}"</div>
    <div style="margin-top: 8px; margin-bottom: 8px; padding: 8px 12px; background: rgba(99, 102, 241, 0.12); border-left: 3px solid #6366f1; border-radius: 4px;">
      <strong style="color: #a5b4fc; font-size: 0.82rem;">⚡ Skills y Gobernanza Aplicada (AGENTS.md §5):</strong>
      <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 4px; line-height: 1.5;">
        • <strong style="color: #c7d2fe;">grill-me v1.1.0</strong>: Árbol de decisiones y recomendaciones inteligentes (Smart Defaults)<br>
        • <strong style="color: #c7d2fe;">domain-modeling v1.0.0</strong>: Modelo de dominio y entidades clave<br>
        • <strong style="color: #c7d2fe;">api-design v1.0.0</strong>: Borrador OpenAPI y estándar RFC 7807 Problem Details
      </div>
    </div>
    <div><strong>Plataforma / Interfaz:</strong> ${escapeHtml(platform)}</div>
    <div><strong>Pantalla Inicial & UI:</strong> ${escapeHtml(uiLayout)}</div>
    <div><strong>Entidades:</strong> ${escapeHtml(entities)}</div>
    <div><strong>Autenticación:</strong> ${escapeHtml(auth)}</div>
    <div><strong>Persistencia:</strong> ${escapeHtml(persistence)}</div>
    <div><strong>Caché:</strong> ${escapeHtml(caching)}</div>
    <div><strong>Manejo de Errores:</strong> ${escapeHtml(errors)}</div>
  `;
}

dom.btnWizardSubmit.addEventListener('click', async () => {
  const prompt = document.getElementById('grill-prompt').value.trim();
  const isNew = (state.grillMode === 'new_app');
  let projName = '';

  if (isNew) {
    projName = document.getElementById('grill-proj-name').value.trim();
    if (!projName) {
      alert('Ingresa un nombre para el nuevo proyecto.');
      return;
    }
  } else {
    projName = state.activeProjectName || state.activeProject?.project_name;
    if (!projName) {
      alert('No hay un proyecto activo seleccionado.');
      return;
    }
  }

  const uiLayoutEl = document.getElementById('grill-opt-ui-layout');
  const uiLayoutVal = uiLayoutEl ? uiLayoutEl.options[uiLayoutEl.selectedIndex].text : "Dashboard Web Interactivo";
  const isWeatherPrompt = (prompt.toLowerCase().includes('clima') || prompt.toLowerCase().includes('tiempo') || prompt.toLowerCase().includes('weather'));

  const answers = {
    api_style: document.getElementById('grill-opt-platform').options[document.getElementById('grill-opt-platform').selectedIndex].text,
    ui_layout: uiLayoutVal,
    ui_theme: isWeatherPrompt ? "Dark Mode Meteorológico Moderno con gradientes" : "Modern Dark Mode",
    entities: document.getElementById('grill-opt-entities').value,
    consumers: "Usuarios en navegador web (Pantalla Inicial SPA) y clientes móviles",
    auth_scheme: document.getElementById('grill-opt-auth').value,
    error_format: document.getElementById('grill-opt-errors').value,
    persistence: document.getElementById('grill-opt-persistence').value,
    caching: document.getElementById('grill-opt-caching').value,
    validation: "Esquemas estrictos tipados",
    deployment: "Contenedor Docker (python:3.11-slim) / Paquete",
  };

  dom.btnWizardSubmit.disabled = true;
  dom.btnWizardSubmit.textContent = isNew ? 'Creando Nuevo Proyecto...' : 'Generando Discovery...';

  try {
    const res = await fetch('/api/actions/interview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        answers,
        reset_first: isNew,
        project_name: projName,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error en Discovery');

    showToast(isNew 
      ? `¡Proyecto '${projName}' creado y contrato congelado en DISCOVERY_NOTES.md!` 
      : `¡Discovery completado para '${projName}' y contrato congelado en DISCOVERY_NOTES.md!`, 
      'success'
    );
    dom.modalGrill.classList.add('hidden');
    setInspectionMode('workspace');
    await loadStatus();
    await loadGitOverview();
    loadArtifactContent('discovery_notes');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    dom.btnWizardSubmit.disabled = false;
    dom.btnWizardSubmit.textContent = '🚀 Congelar Contrato y Generar Discovery';
  }
});

// --- Ejecución y Prueba en Vivo de la Aplicación en Navegador ---
async function startAppTestServer() {
  if (!dom.btnRunApp) return;
  const isStage6Approved = Boolean(state.humanApprovals && state.humanApprovals.local_runner === true);
  if (!isStage6Approved) {
    showToast('Bloqueado: La Etapa 6 (Entorno de Pruebas Local) debe estar formalmente Aprobada antes de probar la aplicación.', 'error');
    dom.btnRunApp.disabled = true;
    return;
  }

  dom.btnRunApp.disabled = true;
  const prevText = dom.btnRunApp.textContent;
  dom.btnRunApp.textContent = '⏳ Iniciando...';

  try {
    const projParam = state.activeProjectName ? `?project=${encodeURIComponent(state.activeProjectName)}` : '';
    const res = await fetch(`/api/actions/app/start${projParam}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al iniciar la aplicación');

    showToast(data.message, 'success');
    if (data.url) {
      window.open(data.url, '_blank');
    }
    await loadStatus();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (dom.btnRunApp) {
      const stillApproved = Boolean(state.humanApprovals && state.humanApprovals.local_runner === true);
      dom.btnRunApp.disabled = !stillApproved;
      if (!stillApproved) dom.btnRunApp.textContent = prevText;
    }
  }
}

async function stopAppTestServer() {
  if (!dom.btnStopApp) return;
  try {
    const projParam = state.activeProjectName ? `?project=${encodeURIComponent(state.activeProjectName)}` : '';
    const res = await fetch(`/api/actions/app/stop${projParam}`, { method: 'POST' });
    const data = await res.json();
    showToast(data.message, 'info');
    await loadStatus();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

if (dom.btnRunApp) {
  dom.btnRunApp.addEventListener('click', startAppTestServer);
}
if (dom.btnStopApp) {
  dom.btnStopApp.addEventListener('click', stopAppTestServer);
}

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

if (dom.btnDeleteActiveProject) {
  dom.btnDeleteActiveProject.addEventListener('click', async () => {
    const currName = state.activeProject?.project_name;
    if (!currName) return;
    dom.modalReset.classList.add('hidden');
    await deleteProject(currName);
  });
}

// --- Event Listeners Globales ---
dom.toggleWorkspace.addEventListener('click', () => setInspectionMode('workspace'));
dom.toggleGit.addEventListener('click', () => setInspectionMode('git'));
dom.btnRestoreBranch.addEventListener('click', restoreCurrentBranch);

dom.artifactItems.forEach(item => {
  item.addEventListener('click', () => loadArtifactContent(item.dataset.artifact));
});

dom.stepCards.forEach(card => {
  card.addEventListener('click', () => {
    if (card.classList.contains('locked')) {
      showToast('🔒 Esta etapa está bloqueada hasta que apruebes formalmente la etapa previa.', 'warning');
      return;
    }
    const stageKey = card.dataset.stage;
    if (stageKey === 'deploy') {
      showToast('🚀 La Etapa 7 (Deploy Cloud/DevOps) se encuentra en preparación para la siguiente fase.', 'info');
      return;
    }
    loadArtifactContent(stageKey);
  });
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

  // Si no se ha descartado el lanzador en esta sesión, abrir el diálogo de selección inicial
  if (!sessionStorage.getItem('launcher_dismissed')) {
    openProjectLauncher();
  }
});
