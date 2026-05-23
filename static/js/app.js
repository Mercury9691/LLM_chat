// App state
let currentProject = 'default';
let currentView = 'chat';
let currentCrudType = ''; // character, template, segment
let editingItemName = null;
let chatHistory = [];
let pendingMediaItems = [];
let currentImages = []; // Array of {url, path} for the CRUD editor
let currentDialogId = generateId();
let allDialogs = [];
let scenarioState = {
    currentGameId: null,
    games: [],
    state: null,
    storyView: 'main_story',
    consoleView: 'actions',
    roleOrder: [],
    enableThinking: false
};
let scenarioImportState = {
    characters: [],
    selected: new Set()
};
let mediaGalleryState = {
    activeTab: 'chat',
    chat: [],
    character: [],
    generated: []
};

const IMAGE_PARAM_PRESETS = {
    'Z-Image 6000': {
        service_type: 'zimage',
        default_params: {
            negative_prompt: '',
            width: 1024,
            height: 1024,
            num_inference_steps: 8,
            guidance_scale: 0.0,
            cfg_normalization: false,
            seed: 42,
            output_dir: 'outputs',
            output_name: ''
        },
        enabled_params: ['width', 'height', 'num_inference_steps', 'guidance_scale', 'seed', 'output_dir', 'output_name'],
        param_types: {
            negative_prompt: 'text',
            width: 'int',
            height: 'int',
            num_inference_steps: 'int',
            guidance_scale: 'float',
            cfg_normalization: 'boolean',
            seed: 'int',
            output_dir: 'text',
            output_name: 'text'
        }
    },
    'Z-Image 6001': {
        service_type: 'zimage',
        default_params: {
            negative_prompt: '',
            width: 720,
            height: 1280,
            num_inference_steps: 50,
            guidance_scale: 4.0,
            cfg_normalization: false,
            seed: 42,
            output_dir: 'outputs',
            output_name: ''
        },
        enabled_params: ['negative_prompt', 'width', 'height', 'num_inference_steps', 'guidance_scale', 'cfg_normalization', 'seed', 'output_dir', 'output_name'],
        param_types: {
            negative_prompt: 'text',
            width: 'int',
            height: 'int',
            num_inference_steps: 'int',
            guidance_scale: 'float',
            cfg_normalization: 'boolean',
            seed: 'int',
            output_dir: 'text',
            output_name: 'text'
        }
    }
};

const IMAGE_SERVICE_TYPE_PRESETS = {
    zimage: {
        default_params: {
            negative_prompt: '',
            width: 1024,
            height: 1024,
            num_inference_steps: 8,
            guidance_scale: 0.0,
            cfg_normalization: false,
            seed: 42,
            output_dir: 'outputs',
            output_name: ''
        },
        enabled_params: ['negative_prompt', 'width', 'height', 'num_inference_steps', 'guidance_scale', 'cfg_normalization', 'seed', 'output_dir', 'output_name'],
        param_types: {
            negative_prompt: 'text',
            width: 'int',
            height: 'int',
            num_inference_steps: 'int',
            guidance_scale: 'float',
            cfg_normalization: 'boolean',
            seed: 'int',
            output_dir: 'text',
            output_name: 'text'
        }
    },
    hidream_o1: {
        default_params: {
            mode: 't2i',
            width: 2048,
            height: 2048,
            seed: 32,
            num_inference_steps: 50,
            guidance_scale: 5.0,
            shift: 3.0,
            scheduler_name: 'default',
            editing_scheduler: 'flow_match',
            keep_original_aspect: true,
            preview_steps: '7,14,21'
        },
        enabled_params: ['mode', 'width', 'height', 'seed', 'num_inference_steps', 'guidance_scale', 'shift', 'scheduler_name', 'editing_scheduler', 'keep_original_aspect', 'preview_steps'],
        param_types: {
            mode: 'text',
            width: 'int',
            height: 'int',
            seed: 'int',
            num_inference_steps: 'int',
            guidance_scale: 'float',
            shift: 'float',
            scheduler_name: 'text',
            editing_scheduler: 'text',
            keep_original_aspect: 'boolean',
            preview_steps: 'text'
        }
    }
};

const IMAGE_PARAM_FIELDS = [
    { key: 'negative_prompt', label: 'Negative Prompt', type: 'text' },
    { key: 'width', label: 'Width', type: 'int' },
    { key: 'height', label: 'Height', type: 'int' },
    { key: 'num_inference_steps', label: 'Steps', type: 'int' },
    { key: 'guidance_scale', label: 'Guidance', type: 'float' },
    { key: 'cfg_normalization', label: 'CFG Normalization', type: 'boolean' },
    { key: 'seed', label: 'Seed', type: 'int' },
    { key: 'mode', label: 'Mode', type: 'text' },
    { key: 'shift', label: 'Shift', type: 'float' },
    { key: 'scheduler_name', label: 'Scheduler', type: 'text' },
    { key: 'editing_scheduler', label: 'Editing Scheduler', type: 'text' },
    { key: 'keep_original_aspect', label: 'Keep Original Aspect', type: 'boolean' },
    { key: 'preview_steps', label: 'Preview Steps', type: 'text' },
    { key: 'output_dir', label: 'Output Dir', type: 'text' },
    { key: 'output_name', label: 'Output Name', type: 'text' }
];

const IMAGE_PARAM_META = IMAGE_PARAM_FIELDS.reduce((acc, item) => {
    acc[item.key] = item;
    return acc;
}, {});

const IMAGE_PARAM_TOOLTIPS = {
    negative_prompt: '不希望画面出现的内容。留空则不额外限制。',
    width: '生成图片的宽度。越大越清晰，但通常也越慢。',
    height: '生成图片的高度。越大越清晰，但通常也越慢。',
    num_inference_steps: '生成步数。步数越高通常细节越多，但生成时间也越长。',
    guidance_scale: '提示词约束强度。越高越贴近提示词，但过高可能让画面变僵。',
    cfg_normalization: '对提示词强度做额外稳定处理。通常在画面不稳时再开启。',
    seed: '随机种子。相同参数和种子更容易复现相似结果。',
    mode: '生成模式。文生图不需要参考图，编辑模式需要 1 张图，多参考主体需要 2 张及以上。',
    shift: 'HiDream 的细节控制参数。一般保持默认即可，需要微调风格时再改。',
    scheduler_name: '主采样调度器。不同选项会影响生成节奏和画面风格。',
    editing_scheduler: '编辑模式专用调度器，只在编辑模式下生效。',
    keep_original_aspect: '编辑模式下尽量保持原图宽高比例，避免构图被拉伸。',
    preview_steps: '在哪些步数返回中途预览图，例如 7,14,21。',
    output_dir: '服务端保存结果时使用的输出目录。',
    output_name: '输出文件名。留空时由系统自动生成。'
};

function generateId() {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

function applyImageParamTooltips() {
    document.querySelectorAll('[data-image-param]').forEach(node => {
        const key = node.getAttribute('data-image-param');
        const text = IMAGE_PARAM_TOOLTIPS[key];
        if (!text) return;
        node.title = text;
        node.setAttribute('aria-label', text);
        const label = node.querySelector('label');
        if (label) {
            label.title = text;
            label.classList.add('help-cursor');
        }
        node.querySelectorAll('input, select, textarea').forEach(control => {
            control.title = text;
            control.setAttribute('aria-label', text);
        });
    });
    if (els.hidreamModeBar) {
        const text = IMAGE_PARAM_TOOLTIPS.mode;
        els.hidreamModeBar.title = text;
        const label = els.hidreamModeBar.querySelector('label');
        if (label) {
            label.title = text;
            label.classList.add('help-cursor');
        }
        els.hidreamModeBar.querySelectorAll('select').forEach(control => {
            control.title = text;
            control.setAttribute('aria-label', text);
        });
    }
}

// DOM Elements
const els = {
    sidebar: document.getElementById('sidebar'),
    toggleSidebar: document.getElementById('toggle-sidebar'),
    navItems: document.querySelectorAll('.nav-item'),
    viewSections: document.querySelectorAll('.view-section'),
    projectSelect: document.getElementById('project-select'),
    newProjectBtn: document.getElementById('new-project-btn'),
    modelSelect: document.getElementById('model-select'),
    samplingTemperature: document.getElementById('sampling-temperature'),
    samplingTopP: document.getElementById('sampling-top-p'),
    samplingTopK: document.getElementById('sampling-top-k'),
    samplingTemperatureSlider: document.getElementById('sampling-temperature-slider'),
    samplingTopPSlider: document.getElementById('sampling-top-p-slider'),
    samplingTopKSlider: document.getElementById('sampling-top-k-slider'),
    samplingSaveBtn: document.getElementById('sampling-save-btn'),
    samplingRecommendBtn: document.getElementById('sampling-recommend-btn'),
    
    // Chat
    chatMessages: document.getElementById('chat-messages'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    uploadBtn: document.getElementById('upload-btn'),
    fileInput: document.getElementById('file-input'),
    mediaPreviewContainer: document.getElementById('media-preview-container'),
    
    // Controls
    thinkingToggle: document.getElementById('thinking-toggle'),
    preloadToggle: document.getElementById('preload-toggle'),
    promptAgentToggle: document.getElementById('prompt-agent-toggle'),
    imageGenToggle: document.getElementById('image-gen-toggle'),
    imageGenPanel: document.getElementById('image-gen-panel'),
    imageGenExpandBtn: document.getElementById('image-gen-expand-btn'),
    imageServiceStatusDot: document.getElementById('image-service-status-dot'),
    imageGenNegativePrompt: document.getElementById('image-gen-negative-prompt'),
    imageGenWidth: document.getElementById('image-gen-width'),
    imageGenHeight: document.getElementById('image-gen-height'),
    imageGenSteps: document.getElementById('image-gen-steps'),
    imageGenGuidance: document.getElementById('image-gen-guidance'),
    imageGenCfgNormalization: document.getElementById('image-gen-cfg-normalization'),
    imageGenSeed: document.getElementById('image-gen-seed'),
    imageGenOutputDir: document.getElementById('image-gen-output-dir'),
    imageGenOutputName: document.getElementById('image-gen-output-name'),
    imageGenFieldNodes: document.querySelectorAll('[data-image-param]'),
    hidreamModeBar: document.getElementById('hidream-mode-bar'),
    hidreamMode: document.getElementById('hidream-mode'),
    hidreamModeInline: document.getElementById('hidream-mode-inline'),
    hidreamShift: document.getElementById('hidream-shift'),
    hidreamSchedulerName: document.getElementById('hidream-scheduler-name'),
    hidreamEditingScheduler: document.getElementById('hidream-editing-scheduler'),
    hidreamKeepOriginalAspect: document.getElementById('hidream-keep-original-aspect'),
    hidreamPreviewSteps: document.getElementById('hidream-preview-steps'),
    clearChatBtn: document.getElementById('clear-chat-btn'),
    
    // Right Sidebar (Dialogs)
    rightSidebar: document.getElementById('right-sidebar'),
    toggleRightSidebar: document.getElementById('toggle-right-sidebar'),
    toggleRightSidebarFloating: document.getElementById('right-sidebar-toggle-floating'),
    newChatBtn: document.getElementById('new-chat-btn'),
    dialogList: document.getElementById('dialog-list'),
    
    // Preload
    preloadCharacter: document.getElementById('preload-character'),
    preloadTemplate: document.getElementById('preload-template'),
    savePreloadBtn: document.getElementById('save-preload-btn'),
    clearPreloadBtn: document.getElementById('clear-preload-btn'),
    
    // CRUD
    crudTitle: document.getElementById('crud-title'),
    crudAddBtn: document.getElementById('crud-add-btn'),
    crudList: document.getElementById('crud-list'),
    crudEditor: document.getElementById('crud-editor'),
    crudEditorTitle: document.getElementById('crud-editor-title'),
    crudName: document.getElementById('crud-name'),
    crudInfo: document.getElementById('crud-info'),
    crudImgGroup: document.getElementById('crud-img-group'),
    crudImgUpload: document.getElementById('crud-img-upload'),
    crudImgGallery: document.getElementById('crud-img-gallery'),
    crudImgAddBtn: document.getElementById('gallery-add-btn'),
    crudSaveBtn: document.getElementById('crud-save-btn'),
    crudDeleteBtn: document.getElementById('crud-delete-btn'),
    crudGalleryBtn: document.getElementById('crud-gallery-btn'),
    crudSendPreloadBtn: document.getElementById('crud-send-preload-btn'),
    crudCancelBtn: document.getElementById('crud-cancel-btn'),

    // Gallery
    galleryRefreshBtn: document.getElementById('gallery-refresh-btn'),
    galleryTabs: document.querySelectorAll('[data-gallery-tab]'),
    galleryHint: document.getElementById('gallery-hint'),
    galleryGrid: document.getElementById('gallery-grid'),

    // AI Scenario
    scenarioHome: document.getElementById('scenario-home'),
    scenarioSetup: document.getElementById('scenario-setup'),
    scenarioGame: document.getElementById('scenario-game'),
    scenarioNewBtn: document.getElementById('scenario-new-btn'),
    scenarioBackBtn: document.getElementById('scenario-back-btn'),
    scenarioGameList: document.getElementById('scenario-game-list'),
    scenarioSetupTitle: document.getElementById('scenario-setup-title'),
    scenarioTitle: document.getElementById('scenario-title'),
    scenarioBackground: document.getElementById('scenario-background'),
    scenarioScene: document.getElementById('scenario-scene'),
    scenarioInitialState: document.getElementById('scenario-initial-state'),
    scenarioMainStoryInput: document.getElementById('scenario-main-story-input'),
    scenarioAddRoleBtn: document.getElementById('scenario-add-role-btn'),
    scenarioImportCharactersBtn: document.getElementById('scenario-import-characters-btn'),
    scenarioRolesEditor: document.getElementById('scenario-roles-editor'),
    scenarioSaveSetupBtn: document.getElementById('scenario-save-setup-btn'),
    scenarioStartBtn: document.getElementById('scenario-start-btn'),
    scenarioGameTitle: document.getElementById('scenario-game-title'),
    scenarioViewMainBtn: document.getElementById('scenario-view-main-btn'),
    scenarioViewModelBtn: document.getElementById('scenario-view-model-btn'),
    scenarioStoryTokens: document.getElementById('scenario-story-tokens'),
    scenarioStoryMeta: document.getElementById('scenario-story-meta'),
    scenarioMainStory: document.getElementById('scenario-main-story'),
    scenarioEditBtn: document.getElementById('scenario-edit-btn'),
    scenarioRefreshBtn: document.getElementById('scenario-refresh-btn'),
    scenarioStatus: document.getElementById('scenario-status'),
    scenarioStreamLog: document.getElementById('scenario-stream-log'),
    scenarioGenerateActionsBtn: document.getElementById('scenario-generate-actions-btn'),
    scenarioResolveBtn: document.getElementById('scenario-resolve-btn'),
    scenarioSummarizeBtn: document.getElementById('scenario-summarize-btn'),
    scenarioClearSummaryBtn: document.getElementById('scenario-clear-summary-btn'),
    scenarioClearBoardBtn: document.getElementById('scenario-clear-board-btn'),
    scenarioResetProgressBtn: document.getElementById('scenario-reset-progress-btn'),
    scenarioOrderToggleBtn: document.getElementById('scenario-order-toggle-btn'),
    scenarioThinkingToggle: document.getElementById('scenario-thinking-toggle-control'),
    scenarioHumanActions: document.getElementById('scenario-human-actions'),
    scenarioActions: document.getElementById('scenario-actions'),
    scenarioPendingResolution: document.getElementById('scenario-pending-resolution'),
    scenarioFinalResolution: document.getElementById('scenario-final-resolution'),
    scenarioGenerateNarrativeBtn: document.getElementById('scenario-generate-narrative-btn'),
    scenarioCommitBtn: document.getElementById('scenario-commit-btn'),
    scenarioRoleOrderList: document.getElementById('scenario-role-order-list'),
    scenarioImportModal: document.getElementById('scenario-import-modal'),
    scenarioImportModalBackdrop: document.getElementById('scenario-import-modal-backdrop'),
    scenarioImportModalClose: document.getElementById('scenario-import-modal-close'),
    scenarioImportModalCancel: document.getElementById('scenario-import-modal-cancel'),
    scenarioImportModalSave: document.getElementById('scenario-import-modal-save'),
    scenarioImportSelectAllBtn: document.getElementById('scenario-import-select-all-btn'),
    scenarioImportClearBtn: document.getElementById('scenario-import-clear-btn'),
    scenarioImportList: document.getElementById('scenario-import-list'),
    scenarioImportCount: document.getElementById('scenario-import-count'),
    
    // System
    sysBackupBtn: document.getElementById('sys-backup-btn'),
    sysExportBtn: document.getElementById('sys-export-btn'),
    sysModelList: document.getElementById('sys-model-list'),
    sysAddModelBtn: document.getElementById('sys-add-model-btn'),
    newModelDisplayName: document.getElementById('new-model-display-name'),
    newModelUrl: document.getElementById('new-model-url'),
    newModelName: document.getElementById('new-model-name'),
    imageServiceSelect: document.getElementById('image-service-select'),
    imageServiceTestSelectedBtn: document.getElementById('image-service-test-selected-btn'),
    imageServiceList: document.getElementById('image-service-list'),
    imageServiceAddBtn: document.getElementById('image-service-add-btn'),
    newImageServiceName: document.getElementById('new-image-service-name'),
    newImageServiceType: document.getElementById('new-image-service-type'),
    newImageServiceUrl: document.getElementById('new-image-service-url'),
    imageParamModal: document.getElementById('image-param-modal'),
    imageParamModalBackdrop: document.getElementById('image-param-modal-backdrop'),
    imageParamModalTitle: document.getElementById('image-param-modal-title'),
    imageParamModalClose: document.getElementById('image-param-modal-close'),
    imageParamModalCancel: document.getElementById('image-param-modal-cancel'),
    imageParamModalSave: document.getElementById('image-param-modal-save'),
    paramTemplateList: document.getElementById('param-template-list'),
    paramTemplateAddBtn: document.getElementById('param-template-add-btn'),
    tokenCountDisplay: document.getElementById('token-count-display'),
};

// Initialize
async function init() {
    setupEventListeners();
    applyImageParamTooltips();
    const legacyScenarioThinkingToggle = document.getElementById('scenario-thinking-toggle');
    if (legacyScenarioThinkingToggle) {
        legacyScenarioThinkingToggle.closest('label')?.remove();
    }
    await loadProjects();
    await loadModels();
    await loadDialogs();
    await loadOpenAIModels(); // Add this line
    await loadImageServices();
    initSamplingControls();
    await loadSamplingParams();
    await checkImageServiceHealth();
    await updateTokenCount();
    
    
    // Auto-resize chat input
    els.chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        updateTokenCount();
    });
}

function setupEventListeners() {
    // Mobile detection helper
    const isMobile = () => window.innerWidth <= 768;
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');

    function openMobileSidebar() {
        els.sidebar.classList.add('mobile-open');
        sidebarBackdrop.classList.add('visible');
    }
    function closeMobileSidebar() {
        els.sidebar.classList.remove('mobile-open');
        sidebarBackdrop.classList.remove('visible');
    }

    // Event Listeners
    els.toggleSidebar.addEventListener('click', () => {
        if (isMobile()) {
            closeMobileSidebar();
        } else {
            els.sidebar.classList.toggle('collapsed');
        }
    });

    mobileMenuBtn.addEventListener('click', openMobileSidebar);
    sidebarBackdrop.addEventListener('click', closeMobileSidebar);
    
    els.toggleRightSidebar.addEventListener('click', () => {
        els.rightSidebar.classList.add('collapsed');
        els.toggleRightSidebarFloating.classList.remove('hidden');
    });
    
    els.toggleRightSidebarFloating.addEventListener('click', () => {
        els.rightSidebar.classList.remove('collapsed');
        els.toggleRightSidebarFloating.classList.add('hidden');
    });
    
    els.navItems.forEach(item => {
        item.addEventListener('click', () => {
            const view = item.getAttribute('data-view');
            switchView(view);
            els.navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            // Close sidebar on mobile after navigation
            if (isMobile()) closeMobileSidebar();
        });
    });

    els.projectSelect.addEventListener('change', (e) => {
        currentProject = e.target.value;
        if (['character', 'template', 'segment'].includes(currentView)) {
            loadCrudData(currentView);
        }
        if (currentView === 'gallery') {
            loadMediaGallery();
        }
        if (currentView === 'scenario') {
            showScenarioHome();
        }
        loadDialogs();
    });

    els.newProjectBtn.addEventListener('click', async () => {
        const name = prompt('请输入新项目名称？');
        if (name) {
            await API.post('/api/project', { name });
            await loadProjects();
            els.projectSelect.value = name;
            currentProject = name;
        }
    });

    // Chat
    els.sendBtn.addEventListener('click', sendChatMessage);
    els.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    els.uploadBtn.addEventListener('click', () => els.fileInput.click());
    els.fileInput.addEventListener('change', handleFileUpload);
    
    // Controls
    els.clearChatBtn.addEventListener('click', clearChat);
    if (els.imageGenExpandBtn && els.imageGenPanel) {
        els.imageGenExpandBtn.addEventListener('click', () => {
            els.imageGenPanel.classList.toggle('hidden');
            els.imageGenExpandBtn.classList.toggle('expanded', !els.imageGenPanel.classList.contains('hidden'));
            updateImageUploadCapabilities();
        });
    }
    if (els.imageGenToggle) {
        els.imageGenToggle.addEventListener('change', () => {
            updateImageUploadCapabilities();
            checkImageServiceHealth();
        });
    }
    if (els.hidreamMode) {
        els.hidreamMode.addEventListener('change', () => {
            syncHiDreamModeControls();
            updateHiDreamModeFields();
            updateImageUploadCapabilities();
        });
    }
    if (els.hidreamModeInline) {
        els.hidreamModeInline.addEventListener('change', () => {
            syncHiDreamModeControls();
            updateHiDreamModeFields();
            updateImageUploadCapabilities();
        });
    }
    
    // Preload
    els.savePreloadBtn.addEventListener('click', () => {
        alert('预设已保存！');
    });
    els.clearPreloadBtn.addEventListener('click', () => {
        els.preloadCharacter.value = '';
        els.preloadTemplate.value = '';
    });
    
    // CRUD
    els.crudAddBtn.addEventListener('click', showCrudEditor);
    els.crudCancelBtn.addEventListener('click', () => els.crudEditor.classList.add('hidden'));
    els.crudSaveBtn.addEventListener('click', saveCrudItem);
    els.crudDeleteBtn.addEventListener('click', deleteCrudItem);
    els.crudSendPreloadBtn.addEventListener('click', sendToPreload);
    els.crudImgAddBtn.addEventListener('click', () => els.crudImgUpload.click());
    els.crudImgUpload.addEventListener('change', handleCrudImgUpload);
    els.crudGalleryBtn.addEventListener('click', () => {
        if (editingItemName && currentCrudType === 'character') {
            window.open(`/gallery/${currentProject}/${encodeURIComponent(editingItemName)}`, '_blank');
        }
    });

    if (els.galleryRefreshBtn) {
        els.galleryRefreshBtn.addEventListener('click', loadMediaGallery);
    }
    els.galleryTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            setGalleryTab(tab.getAttribute('data-gallery-tab'));
        });
    });

    if (els.scenarioNewBtn) els.scenarioNewBtn.addEventListener('click', createScenarioGame);
    if (els.scenarioBackBtn) els.scenarioBackBtn.addEventListener('click', showScenarioHome);
    if (els.scenarioAddRoleBtn) els.scenarioAddRoleBtn.addEventListener('click', () => addScenarioRole());
    if (els.scenarioImportCharactersBtn) els.scenarioImportCharactersBtn.addEventListener('click', importScenarioRolesFromCharacters);
    if (els.scenarioSaveSetupBtn) els.scenarioSaveSetupBtn.addEventListener('click', saveScenarioSetup);
    if (els.scenarioStartBtn) els.scenarioStartBtn.addEventListener('click', startScenarioGame);
    if (els.scenarioEditBtn) els.scenarioEditBtn.addEventListener('click', () => openScenarioSetup(scenarioState.currentGameId));
    if (els.scenarioRefreshBtn) els.scenarioRefreshBtn.addEventListener('click', () => openScenarioGame(scenarioState.currentGameId));
    if (els.scenarioViewMainBtn) els.scenarioViewMainBtn.addEventListener('click', () => setScenarioStoryView('main_story'));
    if (els.scenarioViewModelBtn) els.scenarioViewModelBtn.addEventListener('click', () => setScenarioStoryView('model_context'));
    if (els.scenarioThinkingToggle) {
        els.scenarioThinkingToggle.addEventListener('change', () => {
            scenarioState.enableThinking = !!els.scenarioThinkingToggle.checked;
        });
    }
    if (els.scenarioOrderToggleBtn) els.scenarioOrderToggleBtn.addEventListener('click', toggleScenarioOrderView);
    if (els.scenarioGenerateActionsBtn) els.scenarioGenerateActionsBtn.addEventListener('click', () => runScenarioStep('generate_ai_actions'));
    if (els.scenarioResolveBtn) els.scenarioResolveBtn.addEventListener('click', () => runScenarioStep('resolve_turn'));
    if (els.scenarioSummarizeBtn) els.scenarioSummarizeBtn.addEventListener('click', () => runScenarioStep('summarize'));
    if (els.scenarioClearSummaryBtn) els.scenarioClearSummaryBtn.addEventListener('click', clearScenarioSummary);
    if (els.scenarioClearBoardBtn) els.scenarioClearBoardBtn.addEventListener('click', clearScenarioBoard);
    if (els.scenarioResetProgressBtn) els.scenarioResetProgressBtn.addEventListener('click', resetScenarioProgress);
    if (els.scenarioGenerateNarrativeBtn) els.scenarioGenerateNarrativeBtn.addEventListener('click', () => runScenarioStep('narrate_turn'));
    if (els.scenarioCommitBtn) els.scenarioCommitBtn.addEventListener('click', commitScenarioTurn);
    if (els.scenarioImportModalClose) els.scenarioImportModalClose.addEventListener('click', closeScenarioImportModal);
    if (els.scenarioImportModalCancel) els.scenarioImportModalCancel.addEventListener('click', closeScenarioImportModal);
    if (els.scenarioImportModalBackdrop) els.scenarioImportModalBackdrop.addEventListener('click', closeScenarioImportModal);
    if (els.scenarioImportModalSave) els.scenarioImportModalSave.addEventListener('click', commitScenarioImportSelection);
    if (els.scenarioImportSelectAllBtn) els.scenarioImportSelectAllBtn.addEventListener('click', () => scenarioSetImportSelection(true));
    if (els.scenarioImportClearBtn) els.scenarioImportClearBtn.addEventListener('click', () => scenarioSetImportSelection(false));
    if (els.scenarioImportList) {
        els.scenarioImportList.addEventListener('change', handleScenarioImportListChange);
    }
    
    els.newChatBtn.addEventListener('click', startNewChat);
    
    // System
    els.sysBackupBtn.addEventListener('click', async () => {
        try {
            const res = await API.post('/api/system/backup', {}, currentProject);
            alert('备份成功：' + res.path);
        } catch (e) { alert('备份失败。'); }
    });
    els.sysExportBtn.addEventListener('click', () => {
        window.location.href = `/api/system/export?project=${currentProject}`;
    });

    els.sysAddModelBtn.addEventListener('click', addOpenAIModel);
    if (els.imageServiceAddBtn) {
        els.imageServiceAddBtn.addEventListener('click', addImageService);
    }
    if (els.imageServiceSelect) {
        els.imageServiceSelect.addEventListener('change', async () => {
            selectedImageService = els.imageServiceSelect.value;
            applySelectedImageServiceToPanel();
            await saveImageServices();
            checkImageServiceHealth();
        });
    }
    if (els.imageServiceTestSelectedBtn) {
        els.imageServiceTestSelectedBtn.addEventListener('click', testSelectedImageService);
    }
    if (els.imageParamModalClose) {
        els.imageParamModalClose.addEventListener('click', closeImageParamModal);
    }
    if (els.imageParamModalCancel) {
        els.imageParamModalCancel.addEventListener('click', closeImageParamModal);
    }
    if (els.imageParamModalBackdrop) {
        els.imageParamModalBackdrop.addEventListener('click', closeImageParamModal);
    }
    if (els.imageParamModalSave) {
        els.imageParamModalSave.addEventListener('click', saveImageParamTemplate);
    }
    if (els.paramTemplateAddBtn) {
        els.paramTemplateAddBtn.addEventListener('click', () => {
            paramTemplateDraft.push({ key: '', type: 'text', value: '', enabled: true });
            renderParamTemplateRows();
        });
    }
    if (els.paramTemplateList) {
        els.paramTemplateList.addEventListener('input', handleParamTemplateListInput);
        els.paramTemplateList.addEventListener('change', handleParamTemplateListInput);
        els.paramTemplateList.addEventListener('click', handleParamTemplateListClick);
    }

    if (els.samplingSaveBtn) {
        els.samplingSaveBtn.addEventListener('click', saveSamplingParams);
    }
    if (els.samplingRecommendBtn) {
        els.samplingRecommendBtn.addEventListener('click', () => {
            setSamplingInputs({ temperature: 0.7, top_p: 0.9, top_k: 40 });
        });
    }
}

function inferImageParamType(value) {
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'float';
    return 'text';
}

function getImageServiceType(service = {}) {
    return String(service?.service_type || 'zimage').trim() || 'zimage';
}

function isHiDreamImageService(service = null) {
    return getImageServiceType(service || getSelectedImageServiceConfig()) === 'hidream_o1';
}

function cloneImageParamPreset(name, url = '', serviceType = 'zimage') {
    const typePreset = IMAGE_SERVICE_TYPE_PRESETS[serviceType] || IMAGE_SERVICE_TYPE_PRESETS.zimage;
    const preset = IMAGE_PARAM_PRESETS[name] || (serviceType === 'zimage'
        ? (String(url).includes(':6001') ? IMAGE_PARAM_PRESETS['Z-Image 6001'] : IMAGE_PARAM_PRESETS['Z-Image 6000'])
        : typePreset);
    return {
        service_type: serviceType,
        default_params: { ...(preset?.default_params || {}) },
        enabled_params: [...(preset?.enabled_params || [])],
        param_types: { ...(preset?.param_types || {}) }
    };
}

function normalizeImageServiceConfig(service = {}) {
    const serviceType = getImageServiceType(service);
    const base = cloneImageParamPreset(service.name, service.url, serviceType);
    const defaultParams = { ...base.default_params, ...(service.default_params || {}) };
    const enabledParams = Array.isArray(service.enabled_params) && service.enabled_params.length
        ? [...new Set(service.enabled_params.map(item => String(item).trim()).filter(Boolean))]
        : [...Object.keys(defaultParams)];
    const paramTypes = { ...base.param_types };
    Object.entries(defaultParams).forEach(([key, value]) => {
        paramTypes[key] = paramTypes[key] || inferImageParamType(value);
    });
    Object.entries(service.param_types || {}).forEach(([key, value]) => {
        paramTypes[key] = value || paramTypes[key] || 'text';
    });
    return {
        name: service.name || '',
        url: service.url || '',
        service_type: serviceType,
        default_params: defaultParams,
        enabled_params: enabledParams,
        param_types: paramTypes
    };
}

function normalizeImageServiceList(services = []) {
    const seen = new Set();
    const list = [];
    services.forEach(service => {
        const normalized = normalizeImageServiceConfig(service);
        if (!normalized.name || seen.has(normalized.name)) return;
        seen.add(normalized.name);
        list.push(normalized);
    });
    return list;
}

function getSelectedImageServiceConfig() {
    return imageServices.find(service => service.name === selectedImageService) || imageServices[0] || null;
}

function setImageFieldValue(key, value) {
    if (key === 'negative_prompt' && els.imageGenNegativePrompt) {
        els.imageGenNegativePrompt.value = value ?? '';
    } else if (key === 'width' && els.imageGenWidth) {
        els.imageGenWidth.value = value ?? 1024;
    } else if (key === 'height' && els.imageGenHeight) {
        els.imageGenHeight.value = value ?? 1024;
    } else if (key === 'num_inference_steps' && els.imageGenSteps) {
        els.imageGenSteps.value = value ?? 8;
    } else if (key === 'guidance_scale' && els.imageGenGuidance) {
        els.imageGenGuidance.value = value ?? 0;
    } else if (key === 'cfg_normalization' && els.imageGenCfgNormalization) {
        els.imageGenCfgNormalization.checked = !!value;
    } else if (key === 'seed' && els.imageGenSeed) {
        els.imageGenSeed.value = value ?? 42;
    } else if (key === 'mode' && els.hidreamMode && els.hidreamModeInline) {
        els.hidreamMode.value = value ?? 't2i';
        els.hidreamModeInline.value = value ?? 't2i';
    } else if (key === 'shift' && els.hidreamShift) {
        els.hidreamShift.value = value ?? 3.0;
    } else if (key === 'scheduler_name' && els.hidreamSchedulerName) {
        els.hidreamSchedulerName.value = value ?? 'default';
    } else if (key === 'editing_scheduler' && els.hidreamEditingScheduler) {
        els.hidreamEditingScheduler.value = value ?? 'flow_match';
    } else if (key === 'keep_original_aspect' && els.hidreamKeepOriginalAspect) {
        els.hidreamKeepOriginalAspect.checked = !!value;
    } else if (key === 'preview_steps' && els.hidreamPreviewSteps) {
        els.hidreamPreviewSteps.value = value ?? '7,14,21';
    } else if (key === 'output_dir' && els.imageGenOutputDir) {
        els.imageGenOutputDir.value = value ?? 'outputs';
    } else if (key === 'output_name' && els.imageGenOutputName) {
        els.imageGenOutputName.value = value ?? '';
    }
}

function getImageFieldValue(key) {
    if (key === 'negative_prompt') return els.imageGenNegativePrompt?.value ?? '';
    if (key === 'width') return parseInt(els.imageGenWidth?.value, 10) || 1024;
    if (key === 'height') return parseInt(els.imageGenHeight?.value, 10) || 1024;
    if (key === 'num_inference_steps') return parseInt(els.imageGenSteps?.value, 10) || 8;
    if (key === 'guidance_scale') return parseFloat(els.imageGenGuidance?.value) || 0;
    if (key === 'cfg_normalization') return !!els.imageGenCfgNormalization?.checked;
    if (key === 'seed') return parseInt(els.imageGenSeed?.value, 10) || 42;
    if (key === 'mode') return els.hidreamMode?.value || els.hidreamModeInline?.value || 't2i';
    if (key === 'shift') return parseFloat(els.hidreamShift?.value) || 3.0;
    if (key === 'scheduler_name') return els.hidreamSchedulerName?.value || 'default';
    if (key === 'editing_scheduler') return els.hidreamEditingScheduler?.value || 'flow_match';
    if (key === 'keep_original_aspect') return !!els.hidreamKeepOriginalAspect?.checked;
    if (key === 'preview_steps') return els.hidreamPreviewSteps?.value?.trim() || '';
    if (key === 'output_dir') return els.imageGenOutputDir?.value?.trim() || 'outputs';
    if (key === 'output_name') return els.imageGenOutputName?.value?.trim() || '';
    return '';
}

function syncHiDreamModeControls() {
    if (!els.hidreamMode || !els.hidreamModeInline) return;
    const mode = els.hidreamMode.value || els.hidreamModeInline.value || 't2i';
    els.hidreamMode.value = mode;
    els.hidreamModeInline.value = mode;
}

function updateHiDreamModeFields() {
    const isHiDream = isHiDreamImageService();
    const modeField = document.querySelector('[data-image-param="mode"]');
    if (modeField) {
        modeField.classList.toggle('hidden', isHiDream);
    }
    if (!isHiDream) return;
    const mode = getImageFieldValue('mode');
    document.querySelectorAll('[data-image-param="editing_scheduler"], [data-image-param="keep_original_aspect"]').forEach(node => {
        node.classList.toggle('hidden', mode !== 'edit');
    });
    if (mode !== 'subject' && pendingMediaItems.length > 1) {
        pendingMediaItems = pendingMediaItems.slice(0, 1);
        renderPendingMediaPreview();
    }
}

function updateImageUploadCapabilities() {
    if (!els.fileInput) return;
    const isHiDream = !!els.imageGenToggle?.checked && isHiDreamImageService();
    const mode = isHiDream ? getImageFieldValue('mode') : '';
    const allowMultiple = isHiDream && mode === 'subject';
    els.fileInput.multiple = allowMultiple;
    els.fileInput.accept = isHiDream ? 'image/*,image/heic,image/heif' : 'image/*,image/heic,image/heif,video/mp4';
}

function renderPendingMediaPreview() {
    if (!els.mediaPreviewContainer) return;
    if (!pendingMediaItems.length) {
        els.mediaPreviewContainer.classList.add('hidden');
        els.mediaPreviewContainer.innerHTML = '';
        return;
    }
    els.mediaPreviewContainer.classList.remove('hidden');
    els.mediaPreviewContainer.innerHTML = pendingMediaItems.map((item, idx) => {
        const media = item.type === 'video'
            ? `<video src="${item.url}" controls></video>`
            : `<img src="${item.url}" alt="preview ${idx + 1}">`;
        return `
            <div class="media-preview-item">
                ${media}
                <button class="media-preview-remove" type="button" onclick="removePendingMedia(${idx})">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;
    }).join('');
}

function applySelectedImageServiceToPanel() {
    const service = getSelectedImageServiceConfig();
    const serviceType = getImageServiceType(service);
    const enabled = new Set(service?.enabled_params || []);
    const defaults = service?.default_params || {};
    els.imageGenFieldNodes.forEach(node => {
        const key = node.getAttribute('data-image-param');
        const shouldShow = enabled.has(key);
        node.classList.toggle('hidden', !shouldShow);
        if (Object.prototype.hasOwnProperty.call(defaults, key)) {
            setImageFieldValue(key, defaults[key]);
        } else if (!shouldShow) {
            setImageFieldValue(key, IMAGE_PARAM_META[key]?.type === 'boolean' ? false : '');
        }
    });
    if (els.hidreamModeBar) {
        els.hidreamModeBar.classList.toggle('hidden', serviceType !== 'hidream_o1');
    }
    syncHiDreamModeControls();
    updateHiDreamModeFields();
    updateImageUploadCapabilities();
}

const samplingConfig = {
    temperature: {
        input: () => els.samplingTemperature,
        slider: () => els.samplingTemperatureSlider,
        min: 0,
        max: 2,
        decimals: 2,
        segments: [
            { p0: 0, p1: 65, v0: 0.0, v1: 1.0 },
            { p0: 65, p1: 85, v0: 1.0, v1: 1.4 },
            { p0: 85, p1: 100, v0: 1.4, v1: 2.0 }
        ]
    },
    top_p: {
        input: () => els.samplingTopP,
        slider: () => els.samplingTopPSlider,
        min: 0,
        max: 1,
        decimals: 2,
        segments: [
            { p0: 0, p1: 40, v0: 0.0, v1: 0.8 },
            { p0: 40, p1: 80, v0: 0.8, v1: 0.97 },
            { p0: 80, p1: 100, v0: 0.97, v1: 1.0 }
        ]
    },
    top_k: {
        input: () => els.samplingTopK,
        slider: () => els.samplingTopKSlider,
        min: 1,
        max: 200,
        decimals: 0,
        segments: [
            { p0: 0, p1: 60, v0: 1, v1: 80 },
            { p0: 60, p1: 85, v0: 80, v1: 140 },
            { p0: 85, p1: 100, v0: 140, v1: 200 }
        ]
    }
};

function clampValue(value, min, max) {
    if (Number.isNaN(value)) return min;
    return Math.min(Math.max(value, min), max);
}

function mapPosToValue(pos, segments) {
    const clamped = clampValue(pos, segments[0].p0, segments[segments.length - 1].p1);
    const seg = segments.find(s => clamped <= s.p1) || segments[segments.length - 1];
    const t = (clamped - seg.p0) / (seg.p1 - seg.p0 || 1);
    return seg.v0 + t * (seg.v1 - seg.v0);
}

function mapValueToPos(value, segments) {
    const clamped = clampValue(value, segments[0].v0, segments[segments.length - 1].v1);
    const seg = segments.find(s => clamped <= s.v1) || segments[segments.length - 1];
    const t = (clamped - seg.v0) / (seg.v1 - seg.v0 || 1);
    return seg.p0 + t * (seg.p1 - seg.p0);
}

function formatSamplingValue(value, decimals) {
    if (decimals === 0) return String(Math.round(value));
    return value.toFixed(decimals);
}

function setSamplingValue(key, value) {
    const cfg = samplingConfig[key];
    if (!cfg) return;
    const input = cfg.input();
    const slider = cfg.slider();
    const clamped = clampValue(value, cfg.min, cfg.max);
    if (input) input.value = formatSamplingValue(clamped, cfg.decimals);
    if (slider) slider.value = mapValueToPos(clamped, cfg.segments);
}

function syncInputFromSlider(key) {
    const cfg = samplingConfig[key];
    if (!cfg) return;
    const input = cfg.input();
    const slider = cfg.slider();
    if (!input || !slider) return;
    const value = mapPosToValue(parseFloat(slider.value), cfg.segments);
    input.value = formatSamplingValue(value, cfg.decimals);
}

function syncSliderFromInput(key) {
    const cfg = samplingConfig[key];
    if (!cfg) return;
    const input = cfg.input();
    const slider = cfg.slider();
    if (!input || !slider) return;
    const value = parseFloat(input.value);
    if (Number.isNaN(value)) return;
    const clamped = clampValue(value, cfg.min, cfg.max);
    slider.value = mapValueToPos(clamped, cfg.segments);
}

function normalizeSamplingInput(key) {
    const cfg = samplingConfig[key];
    if (!cfg) return;
    const input = cfg.input();
    if (!input) return;
    const value = parseFloat(input.value);
    const clamped = clampValue(value, cfg.min, cfg.max);
    setSamplingValue(key, clamped);
}

function initSamplingControls() {
    Object.keys(samplingConfig).forEach(key => {
        const cfg = samplingConfig[key];
        const input = cfg.input();
        const slider = cfg.slider();
        if (slider) {
            slider.addEventListener('input', () => syncInputFromSlider(key));
        }
        if (input) {
            input.addEventListener('input', () => syncSliderFromInput(key));
            input.addEventListener('blur', () => normalizeSamplingInput(key));
        }
    });
}

function setSamplingInputs(params) {
    if (!params) return;
    if (params.temperature !== undefined) setSamplingValue('temperature', params.temperature);
    if (params.top_p !== undefined) setSamplingValue('top_p', params.top_p);
    if (params.top_k !== undefined) setSamplingValue('top_k', params.top_k);
}

function getSamplingParamsFromUI() {
    const temperatureRaw = parseFloat(els.samplingTemperature?.value);
    const topPRaw = parseFloat(els.samplingTopP?.value);
    const topKRaw = parseInt(els.samplingTopK?.value, 10);
    const temperature = Number.isFinite(temperatureRaw) ? temperatureRaw : 0.7;
    const topP = Number.isFinite(topPRaw) ? topPRaw : 0.9;
    const topK = Number.isFinite(topKRaw) ? topKRaw : 40;
    return { temperature, top_p: topP, top_k: topK };
}

async function loadSamplingParams() {
    try {
        const params = await API.get('/api/config/sampling');
        setSamplingInputs(params);
    } catch (e) { console.error('Failed to load sampling params', e); }
}

async function saveSamplingParams() {
    try {
        const params = getSamplingParamsFromUI();
        await API.post('/api/config/sampling', params);
        alert('采样参数已保存');
    } catch (e) {
        alert('保存采样参数失败');
    }
}

async function loadProjects() {
    try {
        const data = await API.get('/api/projects');
        els.projectSelect.innerHTML = data.projects.map(p => `<option value="${p}">${p}</option>`).join('');
        if (data.projects.length > 0) {
            if (!data.projects.includes(currentProject)) currentProject = data.projects[0];
            els.projectSelect.value = currentProject;
        }
    } catch (e) { console.error('Failed to load projects', e); }
}

async function loadModels() {
    try {
        const models = await API.get('/models');
        els.modelSelect.innerHTML = models.map(m => `<option value="${m.name}" data-source="${m.source}">${m.name} (${m.source})</option>`).join('');
    } catch (e) { console.error('Failed to load models', e); }
}

function switchView(view) {
    currentView = view;
    els.viewSections.forEach(s => s.classList.remove('active'));
    
    if (['character', 'template', 'segment'].includes(view)) {
        els.crudEditor.classList.add('hidden');
        document.getElementById('view-crud').classList.add('active');
        currentCrudType = view;
        const titles = { character: '角色管理', template: '模板管理', segment: '片段管理' };
        els.crudTitle.innerText = titles[view];
        els.crudImgGroup.style.display = view === 'character' ? 'block' : 'none';
        loadCrudData(view);
    } else if (view === 'gallery') {
        const section = document.getElementById('view-gallery');
        if (section) section.classList.add('active');
        loadMediaGallery();
    } else if (view === 'scenario') {
        const section = document.getElementById('view-scenario');
        if (section) section.classList.add('active');
        showScenarioHome();
    } else {
        const section = document.getElementById(`view-${view}`);
        if (section) section.classList.add('active');
    }
}

// --- Chat Logic ---

async function handleFileUpload(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    try {
        const isHiDream = !!els.imageGenToggle?.checked && isHiDreamImageService();
        const allowMultiple = isHiDream && getImageFieldValue('mode') === 'subject';
        const uploadFiles = allowMultiple ? files : [files[0]];
        if (!allowMultiple) {
            pendingMediaItems = [];
        }
        for (const file of uploadFiles) {
            const res = await API.upload(file, currentProject, 'chat');
            pendingMediaItems.push({
                url: res.url,
                path: res.path,
                type: file.type.startsWith('video') ? 'video' : 'image'
            });
        }
        renderPendingMediaPreview();
        updateImageUploadCapabilities();
    } catch (err) {
        alert('上传失败');
    } finally {
        e.target.value = '';
    }
}

window.removePendingMedia = function(idx) {
    pendingMediaItems.splice(idx, 1);
    renderPendingMediaPreview();
};

function appendMessage(role, text, mediaUrl = null, mediaType = null, mediaItems = null, meta = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    let contentHtml = '';
    const items = Array.isArray(mediaItems) && mediaItems.length
        ? mediaItems
        : (mediaUrl ? [{ url: mediaUrl, type: mediaType }] : []);
    if (items.length) {
        contentHtml += `<div class="message-media-strip">`;
        items.forEach(item => {
            if (item.type === 'video') contentHtml += `<video src="${item.url}" controls></video>`;
            else contentHtml += `<img src="${item.url}" alt="media">`;
        });
        contentHtml += `</div>`;
    }
    
    let textHtml = '';
    if (role === 'assistant' && meta?.message_kind === 'prompt_agent_result' && meta?.prompt_agent_result) {
        const result = meta.prompt_agent_result;
        const status = meta.prompt_agent_status || 'pending';
        const actionHtml = status === 'pending'
            ? `
                <div class="prompt-agent-actions">
                    <button class="btn btn-primary btn-sm" type="button" onclick="acceptPromptAgentResult('${meta.id}')">接受</button>
                    <button class="btn btn-secondary btn-sm" type="button" onclick="rejectPromptAgentResult('${meta.id}')">放弃</button>
                </div>
            `
            : `<div class="prompt-agent-status ${status}">${status === 'accepted' ? '已接受到预载模板' : '已放弃本次优化结果'}</div>`;
        textHtml = `
            <div class="prompt-agent-card">
                <div class="prompt-agent-title">提示词优化结果</div>
                <div class="prompt-agent-prompt">${escapeHtml(result.prompt || '')}</div>
                <div class="prompt-agent-meta"><strong>说明：</strong>${escapeHtml(result.reasoning || '')}</div>
                <div class="prompt-agent-meta"><strong>补全信息：</strong>${escapeHtml(result.resolved_knowledge || '无')}</div>
                ${actionHtml}
            </div>
        `;
    } else if (role === 'assistant') {
        textHtml = formatTextWithThink(text || '');
    } else {
        textHtml = marked.parse(text || '');
    }
    contentHtml += `<div class="text-content">${textHtml}</div>`;
    
    msgDiv.innerHTML = `<div class="message-content">${contentHtml}</div>`;
    els.chatMessages.appendChild(msgDiv);
    
    // Scroll to bottom
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return msgDiv;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function renderImageGenerationProgress(messageEl, state = {}) {
    const percent = Math.max(0, Math.min(100, Number(state.percent ?? 0)));
    const title = state.title || '正在生成图片';
    const detail = state.detail || '服务正在处理中';
    const previewUrl = state.previewUrl || messageEl.dataset.previewUrl || '';
    const textContent = messageEl.querySelector('.text-content');
    if (!textContent) return;
    if (previewUrl) {
        messageEl.dataset.previewUrl = previewUrl;
    }

    textContent.innerHTML = `
        <div class="image-progress-card">
            <div class="image-progress-header">
                <span class="image-progress-title">${escapeHtml(title)}</span>
                <span class="image-progress-percent">${percent.toFixed(percent % 1 ? 1 : 0)}%</span>
            </div>
            <div class="image-progress-bar" role="progressbar" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100">
                <div class="image-progress-bar-fill" style="width: ${percent}%"></div>
            </div>
            <div class="image-progress-detail">${escapeHtml(detail)}</div>
            ${previewUrl ? `<div class="image-progress-preview"><img src="${previewUrl}" alt="preview"></div>` : ''}
        </div>
    `;
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
}

function setAssistantMessageContent(messageEl, text, mediaUrl = null, mediaType = null) {
    const messageContent = messageEl.querySelector('.message-content');
    if (!messageContent) return;
    delete messageEl.dataset.previewUrl;

    let contentHtml = '';
    if (mediaUrl) {
        if (mediaType === 'image') {
            contentHtml += `<img src="${mediaUrl}" alt="generated image">`;
        } else if (mediaType === 'video') {
            contentHtml += `<video src="${mediaUrl}" controls></video>`;
        }
    }
    contentHtml += `<div class="text-content">${formatTextWithThink(text || '')}</div>`;
    messageContent.innerHTML = contentHtml;
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
}

function renderMessages() {
    els.chatMessages.innerHTML = '';
    if (chatHistory.length === 0) {
        els.chatMessages.innerHTML = `
            <div class="message system-greeting">
                <h2>你好，今天有什么可以帮你的吗？</h2>
            </div>
        `;
        return;
    }
    chatHistory.forEach(msg => {
        appendMessage(msg.role, msg.text, msg.media_url, msg.media_type, msg.media_items, msg);
    });
}

function setImageServiceStatus(online, detail = '') {
    if (!els.imageServiceStatusDot) return;
    els.imageServiceStatusDot.classList.toggle('online', !!online);
    els.imageServiceStatusDot.classList.toggle('offline', !online);
    els.imageServiceStatusDot.title = online ? '图片服务在线' : (detail || '图片服务离线');
}

async function checkImageServiceHealth() {
    try {
        const data = await API.get('/api/image-service/health', currentProject);
        setImageServiceStatus(data.online, data.error);
        return !!data.online;
    } catch (e) {
        setImageServiceStatus(false, '图片服务离线');
        return false;
    }
}

function getImageGenerationParams(prompt) {
    const service = getSelectedImageServiceConfig();
    const enabled = new Set(service?.enabled_params || []);
    const params = { prompt };
    if (isHiDreamImageService(service)) {
        IMAGE_PARAM_FIELDS.forEach(field => {
            if (!enabled.has(field.key)) return;
            const value = getImageFieldValue(field.key);
            if (field.key === 'preview_steps' && !value) return;
            params[field.key] = value;
        });
        if (pendingMediaItems.length) {
            params.refs_paths = pendingMediaItems.map(item => item.path).filter(Boolean);
        }
        return params;
    }
    IMAGE_PARAM_FIELDS.forEach(field => {
        if (!enabled.has(field.key)) return;
        const value = getImageFieldValue(field.key);
        if (field.key === 'output_name' && !value) return;
        params[field.key] = value;
    });
    Object.entries(service?.default_params || {}).forEach(([key, value]) => {
        if (!enabled.has(key) || Object.prototype.hasOwnProperty.call(params, key) || IMAGE_PARAM_META[key]) return;
        params[key] = value;
    });
    return params;
}

function buildPreloadText() {
    if (!els.preloadToggle?.checked) return '';
    const sections = [];
    const character = els.preloadCharacter?.value?.trim();
    const template = els.preloadTemplate?.value?.trim();
    if (character) sections.push(`角色设定：\n${character}`);
    if (template) sections.push(`模板要求：\n${template}`);
    return sections.length ? `\n\n${sections.join('\n\n')}` : '';
}

function buildImagePreloadText() {
    if (!els.preloadToggle?.checked) return '';
    const sections = [];
    const character = els.preloadCharacter?.value?.trim();
    const template = els.preloadTemplate?.value?.trim();
    if (character) sections.push(character);
    if (template) sections.push(template);
    return sections.length ? `\n\n${sections.join('\n\n')}` : '';
}

function buildImageGenerationPrompt(prompt) {
    return `${prompt}${buildImagePreloadText()}`;
}

function formatImageGenerationText(result) {
    return formatImageGenerationTextV2(result);
}

function formatImageGenerationTextV2(result) {
    const params = result.params || {};
    const service = result.service_response || {};
    const rows = [
        '图片生成完成。',
        '',
        '| 参数 | 值 |',
        '| --- | --- |'
    ];
    Object.entries(params).forEach(([key, value]) => {
        if (key === 'prompt') return;
        rows.push(`| ${key} | ${String(value ?? '')} |`);
    });
    rows.push(`| service_output_path | ${service.output_path || ''} |`);
    rows.push(`| time_sec | ${service.time_sec ?? ''} |`);
    rows.push(`| saved_path | ${result.path || ''} |`);
    return rows.join('\n');
}

function buildImageResultQuery(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            query.set(key, String(value));
        }
    });
    return query.toString();
}

async function generateImageMessage(prompt, refItems = []) {
    const botMsgDiv = appendMessage('assistant', '正在生成图片...');
    renderImageGenerationProgress(botMsgDiv, { percent: 0, title: '正在提交任务', detail: '准备发送到图片服务' });
    try {
        const service = getSelectedImageServiceConfig();
        if (isHiDreamImageService(service)) {
            const mode = getImageFieldValue('mode');
            const refCount = refItems.length;
            if (mode === 'edit' && refCount < 1) {
                throw new Error('编辑模式至少需要上传 1 张参考图');
            }
            if (mode === 'subject' && refCount < 2) {
                throw new Error('多参考主体模式至少需要上传 2 张参考图');
            }
            if (mode === 't2i' && refCount > 0) {
                throw new Error('文生图模式不需要上传参考图，请切换到编辑或多参考主体模式');
            }
        }
        const previousMediaItems = pendingMediaItems;
        pendingMediaItems = refItems;
        const params = getImageGenerationParams(buildImageGenerationPrompt(prompt));
        pendingMediaItems = previousMediaItems;
        const submitRes = await API.post('/api/image-service/generate_async', params, currentProject);
        if (!submitRes.success || !submitRes.job_id) {
            throw new Error(submitRes.error || '图片任务提交失败');
        }

        const result = await new Promise((resolve, reject) => {
            const query = buildImageResultQuery(params);
            const serviceQuery = submitRes.service?.name ? `service=${encodeURIComponent(submitRes.service.name)}` : '';
            const progressUrl = `/api/image-service/progress/${encodeURIComponent(submitRes.job_id)}${serviceQuery ? `?${serviceQuery}` : ''}`;
            const es = new EventSource(progressUrl);
            let settled = false;

            const cleanup = () => {
                if (!settled) settled = true;
                es.close();
            };

            es.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'progress') {
                        const previewUrl = data.preview ? `data:image/jpeg;base64,${data.preview}` : '';
                        renderImageGenerationProgress(botMsgDiv, {
                            percent: data.percent ?? 0,
                            step: data.step ?? 0,
                            total: data.total ?? 0,
                            title: '正在生成图片',
                            detail: data.total ? `第 ${data.step ?? 0} / ${data.total} 步` : '服务正在处理中',
                            previewUrl
                        });
                    } else if (data.type === 'complete' || data.type === 'done') {
                        renderImageGenerationProgress(botMsgDiv, {
                            percent: 100,
                            step: data.step ?? params.num_inference_steps,
                            total: data.total ?? params.num_inference_steps,
                            title: '正在保存结果',
                            detail: '生成完成，正在写入项目图库'
                        });
                        cleanup();
                        const finalQuery = [query, serviceQuery].filter(Boolean).join('&');
                        const finalRes = await API.get(`/api/image-service/result/${encodeURIComponent(submitRes.job_id)}?${finalQuery}`, currentProject);
                        resolve(finalRes);
                    } else if (data.type === 'error') {
                        cleanup();
                        reject(new Error(data.message || '图片生成失败'));
                    }
                } catch (err) {
                    cleanup();
                    reject(err);
                }
            };

            es.onerror = () => {
                cleanup();
                reject(new Error('进度连接中断'));
            };
        });

        const infoText = formatImageGenerationTextV2(result);
        setAssistantMessageContent(botMsgDiv, infoText, result.url, 'image');
        chatHistory.push({
            role: 'assistant',
            text: infoText,
            media_url: result.url,
            media_path: result.path,
            media_type: 'image',
            generation_params: result.params,
            generation_response: result.service_response,
            image_service_type: service?.service_type || 'zimage'
        });
        await saveCurrentDialog();
        await updateTokenCount();
        if (currentView === 'gallery') await loadMediaGallery();
    } catch (e) {
        setAssistantMessageContent(botMsgDiv, `图片生成失败，请确认服务已启动并稍后重试。\n\n${e.message || ''}`);
    } finally {
        checkImageServiceHealth();
    }
}

function getCurrentModelPayload() {
    const selectedOpt = els.modelSelect.options[els.modelSelect.selectedIndex];
    return {
        name: selectedOpt?.value || '',
        source: selectedOpt?.getAttribute('data-source') || 'OpenAI'
    };
}

function getCurrentPreloadPayload() {
    return {
        character: els.preloadCharacter?.value || '',
        template: els.preloadTemplate?.value || ''
    };
}

async function runPromptAgentFlow(text) {
    const botMsgDiv = appendMessage('assistant', '正在优化提示词...');
    const textContentDiv = botMsgDiv.querySelector('.text-content');
    try {
        const res = await API.post('/api/prompt-agent/rewrite', {
            prompt: text,
            model_info: getCurrentModelPayload(),
            sampling_params: getSamplingParamsFromUI(),
            enable_thinking: els.thinkingToggle?.checked ?? false,
            enable_preload: els.preloadToggle?.checked ?? false,
            preload: getCurrentPreloadPayload()
        }, currentProject);
        if (!res.success || !res.prompt) {
            throw new Error(res.error || '提示词优化失败');
        }
        const messageId = generateId();
        const assistantMsg = {
            id: messageId,
            role: 'assistant',
            text: res.prompt,
            message_kind: 'prompt_agent_result',
            prompt_agent_status: 'pending',
            prompt_agent_result: {
                prompt: res.prompt,
                reasoning: res.reasoning || '',
                resolved_knowledge: res.resolved_knowledge || '无'
            }
        };
        chatHistory.push(assistantMsg);
        saveCurrentDialog();
        appendMessage(
            assistantMsg.role,
            assistantMsg.text,
            null,
            null,
            null,
            assistantMsg
        );
        botMsgDiv.remove();
    } catch (e) {
        textContentDiv.innerHTML = `<span style="color:var(--danger-color)">提示词优化失败：${escapeHtml(e.message || '')}</span>`;
    }
}

window.acceptPromptAgentResult = async function(messageId) {
    const target = chatHistory.find(msg => msg.id === messageId && msg.message_kind === 'prompt_agent_result');
    if (!target || !target.prompt_agent_result?.prompt) return;
    els.preloadCharacter.value = '';
    els.preloadTemplate.value = target.prompt_agent_result.prompt;
    target.prompt_agent_status = 'accepted';
    renderMessages();
    await saveCurrentDialog();
    alert('已接受优化后的提示词，并写入预载模板。');
};

window.rejectPromptAgentResult = async function(messageId) {
    const target = chatHistory.find(msg => msg.id === messageId && msg.message_kind === 'prompt_agent_result');
    if (!target) return;
    target.prompt_agent_status = 'rejected';
    renderMessages();
    await saveCurrentDialog();
};

async function sendChatMessage() {
    const text = els.chatInput.value.trim();
    if (!text && pendingMediaItems.length === 0) return;
    if (els.imageGenToggle?.checked && !text) {
        alert('图片生成需要输入提示词。');
        return;
    }
    
    // Hide system greeting
    const greeting = document.querySelector('.system-greeting');
    if (greeting) greeting.style.display = 'none';
    
    // Add User message
    const sentMediaItems = pendingMediaItems.map(item => ({ ...item }));
    const msgObj = { role: 'user', text: text };
    if (sentMediaItems.length === 1) {
        msgObj.media_url = sentMediaItems[0].url;
        msgObj.media_path = sentMediaItems[0].path;
        msgObj.media_type = sentMediaItems[0].type;
    } else if (sentMediaItems.length > 1) {
        msgObj.media_items = sentMediaItems.map(item => ({ url: item.url, type: item.type, path: item.path }));
    }
    
    appendMessage(
        'user',
        text,
        sentMediaItems[0]?.url || null,
        sentMediaItems[0]?.type || null,
        sentMediaItems.length > 1 ? sentMediaItems : null
    );
    chatHistory.push(msgObj);
    saveCurrentDialog();
    updateTokenCount();
    
    els.chatInput.value = '';
    els.chatInput.style.height = 'auto';
    pendingMediaItems = [];
    renderPendingMediaPreview();

    if (els.promptAgentToggle?.checked) {
        if (sentMediaItems.length) {
            alert('提示词优化流程暂不支持上传图片，请先移除附件。');
            return;
        }
        await runPromptAgentFlow(text);
        return;
    }

    if (els.imageGenToggle?.checked) {
        generateImageMessage(text, sentMediaItems);
        return;
    }
    
    const modelInfo = getCurrentModelPayload();
    const preload = getCurrentPreloadPayload();
    
    const payload = {
        messages: chatHistory,
        model_info: modelInfo,
        sampling_params: getSamplingParamsFromUI(),
        enable_thinking: els.thinkingToggle.checked,
        include_thinking: document.getElementById('include-thinking-toggle')?.checked ?? false,
        enable_preload: els.preloadToggle.checked,
        preload: preload
    };
    
    // Add Assistant placeholder
    const botMsgDiv = appendMessage('assistant', '...');
    const textContentDiv = botMsgDiv.querySelector('.text-content');
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullText = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;
            textContentDiv.innerHTML = formatTextWithThink(fullText);
            els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
        }
        
        chatHistory.push({ role: 'assistant', text: fullText });
        saveCurrentDialog();
        updateTokenCount();
        
    } catch (e) {
        textContentDiv.innerHTML = `<span style="color:var(--danger-color)">与模型通信出错。</span>`;
    }
}

function clearChat() {
    if (!confirm('确定要清空所有聊天记录吗？')) return;
    chatHistory = [];
    els.chatMessages.innerHTML = `
        <div class="message system-greeting">
            <h2>你好，今天有什么可以帮你的吗？</h2>
        </div>
    `;
    saveCurrentDialog();
    updateTokenCount();
}

// --- Dialogs Logic ---

async function loadDialogs() {
    try {
        allDialogs = await API.get('/api/dialogs', currentProject);
        renderDialogList();
    } catch (e) {
        console.error('加载对话失败');
    }
}

function renderDialogList() {
    els.dialogList.innerHTML = '';
    allDialogs.forEach(dialog => {
        const div = document.createElement('div');
        div.className = `dialog-item ${dialog.id === currentDialogId ? 'active' : ''}`;
        
        const titleSpan = document.createElement('span');
        titleSpan.className = 'title';
        titleSpan.innerText = dialog.title || '新对话';
        
        const delBtn = document.createElement('button');
        delBtn.className = 'delete-btn';
        delBtn.innerHTML = '<i class="bi bi-trash"></i>';
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteDialog(dialog.id);
        };
        
        div.onclick = () => switchDialog(dialog.id);
        
        div.appendChild(titleSpan);
        div.appendChild(delBtn);
        els.dialogList.appendChild(div);
    });
}

function switchDialog(id) {
    const dialog = allDialogs.find(d => d.id === id);
    if (!dialog) return;
    currentDialogId = dialog.id;
    chatHistory = dialog.messages || [];
    renderMessages();
    renderDialogList();
    updateTokenCount();
}

function startNewChat() {
    currentDialogId = generateId();
    chatHistory = [];
    els.chatMessages.innerHTML = `
        <div class="message system-greeting">
            <h2>你好，今天有什么可以帮你的吗？</h2>
        </div>
    `;
    renderDialogList();
    updateTokenCount();
}

async function saveCurrentDialog() {
    let title = '新对话';
    if (chatHistory.length > 0) {
        // Try to find the first user message for the title
        const firstUserMsg = chatHistory.find(m => m.role === 'user');
        if (firstUserMsg && firstUserMsg.text) {
            title = firstUserMsg.text.substring(0, 20);
        }
    }
    try {
        await API.post(`/api/dialogs/${currentDialogId}`, { title, messages: chatHistory }, currentProject);
        // Update local list
        let d = allDialogs.find(d => d.id === currentDialogId);
        if (d) {
            d.title = title;
            d.messages = chatHistory;
        } else {
            allDialogs.unshift({ id: currentDialogId, title, messages: chatHistory });
        }
        renderDialogList();
    } catch(e) {
        console.error('保存对话失败', e);
    }
}

async function deleteDialog(id) {
    if (!confirm('确定要删除此对话吗？')) return;
    try {
        await API.del(`/api/dialogs/${id}`, currentProject);
        allDialogs = allDialogs.filter(d => d.id !== id);
        if (currentDialogId === id) {
            startNewChat();
        } else {
            renderDialogList();
        }
    } catch(e) {
        alert('删除对话失败');
    }
}

// --- CRUD Logic ---

async function loadCrudData(type) {
    try {
        const data = await API.get(`/api/data/${type}`, currentProject);
        renderCrudList(data);
    } catch (e) { console.error('加载 CRUD 数据失败'); }
}

function renderCrudList(data) {
    els.crudList.innerHTML = '';
    data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'list-item';
        
        let thumb = '';
        if (item.img_paths) {
            try {
                let imgs = [];
                if (item.img_paths.startsWith('[') || item.img_paths.startsWith('{')) {
                    imgs = JSON.parse(item.img_paths);
                } else if (item.img_paths.trim()) {
                    imgs = [{ url: `/static/projects/${currentProject}/${item.img_paths}` }];
                }
                if (imgs.length > 0) {
                    thumb = `<img src="${imgs[0].url}" class="list-thumb">`;
                }
            } catch(e) {}
        }
        
        div.innerHTML = `${thumb}<span>${item.name}</span>`;
        div.onclick = () => {
            document.querySelectorAll('.list-item').forEach(el => el.classList.remove('active'));
            div.classList.add('active');
            editCrudItem(item);
        };
        els.crudList.appendChild(div);
    });
}

function editCrudItem(item) {
    showCrudEditor(false, item);
}

function showCrudEditor(isNew = true, item = {}) {
    editingItemName = isNew ? null : item.name;
    els.crudEditorTitle.innerText = isNew ? '新增项目' : '编辑项目';
    els.crudName.value = item.name || '';
    els.crudInfo.value = item.base_info || '';
    
    // Parse images
    currentImages = [];
    if (item.img_paths) {
        try {
            // Handle if it's already JSON or just a string from migration
            if (item.img_paths.startsWith('[') || item.img_paths.startsWith('{')) {
                currentImages = JSON.parse(item.img_paths);
            } else if (item.img_paths.trim()) {
                // If it's a single path string (legacy)
                currentImages = [{ url: `/static/projects/${currentProject}/${item.img_paths}`, path: item.img_paths }];
            }
        } catch (e) {
            console.error('Failed to parse img_paths', e);
        }
    }
    renderGallery();
    
    if (isNew) {
        els.crudDeleteBtn.style.display = 'none';
        els.crudSendPreloadBtn.style.display = 'none';
        els.crudGalleryBtn.style.display = 'none';
    } else {
        els.crudDeleteBtn.style.display = 'inline-block';
        els.crudSendPreloadBtn.style.display = ['character', 'template'].includes(currentCrudType) ? 'inline-block' : 'none';
        els.crudGalleryBtn.style.display = currentCrudType === 'character' ? 'inline-flex' : 'none';
    }
    els.crudEditor.classList.remove('hidden');
}

// --- Model Management ---
let openAIModels = [];
let editingModelIndex = -1;
let imageServices = [];
let selectedImageService = '';
let editingImageServiceIndex = -1;
let editingImageParamServiceIndex = -1;
let paramTemplateDraft = [];
const serviceTestStatuses = { openai: {}, image: {} };

async function loadOpenAIModels() {
    try {
        openAIModels = await API.get('/api/config/models');
        renderOpenAIModelList();
    } catch (e) { console.error('Failed to load models', e); }
}

function renderOpenAIModelList() {
    els.sysModelList.innerHTML = openAIModels.map((m, idx) => {
        const status = serviceTestStatuses.openai[idx];
        const statusText = status ? (status.online ? '在线' : '离线') : '未测试';
        return `
        <tr>
            <td>${m.name}</td>
            <td>${m.url}</td>
            <td>${m.model_name}</td>
            <td>
                <span class="connection-status ${status?.online ? 'online' : (status ? 'offline' : '')}">
                    ${statusText}
                </span>
            </td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="editOpenAIModel(${idx})">编辑</button>
                <button class="btn btn-outline btn-sm" onclick="testOpenAIModel(${idx})">测试</button>
                <button class="btn btn-danger btn-sm" onclick="deleteOpenAIModel(${idx})">删除</button>
            </td>
        </tr>
    `;}).join('');
}

window.editOpenAIModel = function(idx) {
    editingModelIndex = idx;
    const m = openAIModels[idx];
    els.newModelDisplayName.value = m.name;
    els.newModelUrl.value = m.url;
    els.newModelName.value = m.model_name;
    els.sysAddModelBtn.innerText = '保存修改';
};

async function addOpenAIModel() {
    const name = els.newModelDisplayName.value.trim();
    const url = els.newModelUrl.value.trim();
    const modelName = els.newModelName.value.trim();
    
    if (!name || !url || !modelName) return alert('请填写完整信息');
    
    // Check uniqueness if new or name changed
    if (editingModelIndex === -1 || openAIModels[editingModelIndex].name !== name) {
        if (openAIModels.some(m => m.name === name)) return alert('显示名称已存在');
    }
    
    if (editingModelIndex === -1) {
        openAIModels.push({ name, url, model_name: modelName });
    } else {
        openAIModels[editingModelIndex] = { name, url, model_name: modelName };
        editingModelIndex = -1;
        els.sysAddModelBtn.innerText = '添加模型';
    }
    
    await saveOpenAIModels();
    
    els.newModelDisplayName.value = '';
    els.newModelUrl.value = '';
    els.newModelName.value = '';
    
    loadModels(); // Refresh the chat model selector too
}

window.deleteOpenAIModel = async function(idx) {
    if (!confirm('确定删除该模型吗？')) return;
    openAIModels.splice(idx, 1);
    await saveOpenAIModels();
    loadModels();
};

window.testOpenAIModel = async function(idx) {
    const model = openAIModels[idx];
    if (!model) return;
    serviceTestStatuses.openai[idx] = { online: false, testing: true };
    renderOpenAIModelList();
    try {
        const res = await API.post('/api/test/openai-model', model);
        serviceTestStatuses.openai[idx] = res;
    } catch (e) {
        serviceTestStatuses.openai[idx] = { online: false, error: e.message };
    }
    renderOpenAIModelList();
};

async function saveOpenAIModels() {
    try {
        await API.post('/api/config/models', openAIModels);
        renderOpenAIModelList();
    } catch (e) { alert('保存失败'); }
}

async function loadImageServices() {
    try {
        const data = await API.get('/api/config/image-services');
        imageServices = normalizeImageServiceList(data.services || []);
        selectedImageService = data.selected || imageServices[0]?.name || '';
        renderImageServiceListV3();
        applySelectedImageServiceToPanel();
    } catch (e) {
        console.error('Failed to load image services', e);
    }
}

function renderImageServiceListV3() {
    if (!els.imageServiceList || !els.imageServiceSelect) return;
    els.imageServiceSelect.innerHTML = imageServices.map(service => (
        `<option value="${service.name}" ${service.name === selectedImageService ? 'selected' : ''}>${service.name}</option>`
    )).join('');

    els.imageServiceList.innerHTML = imageServices.map((service, idx) => {
        const status = serviceTestStatuses.image[idx];
        const isSelected = service.name === selectedImageService;
        const statusText = status ? (status.online ? '在线' : '离线') : '未测试';
        const typeLabel = service.service_type === 'hidream_o1' ? 'HiDream-O1' : 'Z-Image';
        return `
            <tr>
                <td>${service.name}${isSelected ? ' <span class="connection-status online">当前</span>' : ''}</td>
                <td>${typeLabel}</td>
                <td>${service.url}</td>
                <td>
                    <span class="connection-status ${status?.online ? 'online' : (status ? 'offline' : '')}">
                        ${statusText}
                    </span>
                </td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="editImageService(${idx})">编辑</button>
                    <button class="btn btn-outline btn-sm" onclick="editImageParamTemplate(${idx})">默认参数</button>
                    <button class="btn btn-outline btn-sm" onclick="testImageService(${idx})">测试</button>
                    <button class="btn btn-secondary btn-sm" onclick="selectImageService(${idx})">选择</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteImageService(${idx})">删除</button>
                </td>
            </tr>
        `;
    }).join('');
}

function buildParamTemplateDraft(service) {
    const enabled = new Set(service?.enabled_params || []);
    const allKeys = new Set([
        ...Object.keys(service?.default_params || {}),
        ...(service?.enabled_params || [])
    ]);
    return Array.from(allKeys).map(key => ({
        key,
        type: service?.param_types?.[key] || inferImageParamType(service?.default_params?.[key]),
        value: service?.default_params?.[key],
        enabled: enabled.has(key)
    }));
}

function renderParamTemplateRows() {
    if (!els.paramTemplateList) return;
    if (!paramTemplateDraft.length) {
        els.paramTemplateList.innerHTML = '<div class="param-template-empty">还没有参数模板，点击下方按钮新增。</div>';
        return;
    }
    els.paramTemplateList.innerHTML = paramTemplateDraft.map((row, idx) => {
        const valueControl = row.type === 'boolean'
            ? `<label class="param-template-bool"><input type="checkbox" data-field="value" data-index="${idx}" ${row.value ? 'checked' : ''}><span>${row.value ? 'true' : 'false'}</span></label>`
            : `<input type="${row.type === 'text' ? 'text' : 'number'}" class="input-element" data-field="value" data-index="${idx}" value="${row.value ?? ''}" ${row.type === 'float' ? 'step="0.1"' : ''}>`;
        return `
            <div class="param-template-row">
                <label class="param-template-enable">
                    <input type="checkbox" data-field="enabled" data-index="${idx}" ${row.enabled ? 'checked' : ''}>
                    <span>启用</span>
                </label>
                <input type="text" class="input-element" data-field="key" data-index="${idx}" value="${row.key || ''}" placeholder="参数名">
                <select class="input-element" data-field="type" data-index="${idx}">
                    <option value="text" ${row.type === 'text' ? 'selected' : ''}>text</option>
                    <option value="int" ${row.type === 'int' ? 'selected' : ''}>int</option>
                    <option value="float" ${row.type === 'float' ? 'selected' : ''}>float</option>
                    <option value="boolean" ${row.type === 'boolean' ? 'selected' : ''}>boolean</option>
                </select>
                <div class="param-template-value">${valueControl}</div>
                <button class="btn btn-text btn-sm" data-action="delete-row" data-index="${idx}">删除</button>
            </div>
        `;
    }).join('');
}

function openImageParamModal(idx) {
    const service = imageServices[idx];
    if (!service || !els.imageParamModal) return;
    editingImageParamServiceIndex = idx;
    paramTemplateDraft = buildParamTemplateDraft(service);
    els.imageParamModalTitle.textContent = `${service.name} 默认参数模板`;
    renderParamTemplateRows();
    els.imageParamModal.classList.remove('hidden');
}

function closeImageParamModal() {
    editingImageParamServiceIndex = -1;
    paramTemplateDraft = [];
    els.imageParamModal?.classList.add('hidden');
}

function coerceParamTemplateValue(type, value) {
    if (type === 'boolean') return !!value;
    if (type === 'int') {
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : 0;
    }
    if (type === 'float') {
        const parsed = parseFloat(value);
        return Number.isFinite(parsed) ? parsed : 0;
    }
    return value == null ? '' : String(value);
}

function handleParamTemplateListInput(event) {
    const target = event.target;
    const idx = Number(target.dataset.index);
    const field = target.dataset.field;
    if (!Number.isInteger(idx) || !field || !paramTemplateDraft[idx]) return;
    if (field === 'enabled') {
        paramTemplateDraft[idx].enabled = !!target.checked;
    } else if (field === 'key') {
        paramTemplateDraft[idx].key = target.value;
    } else if (field === 'type') {
        paramTemplateDraft[idx].type = target.value;
        paramTemplateDraft[idx].value = target.value === 'boolean' ? false : '';
        renderParamTemplateRows();
        return;
    } else if (field === 'value') {
        paramTemplateDraft[idx].value = target.type === 'checkbox' ? target.checked : target.value;
        if (target.type === 'checkbox') {
            const label = target.parentElement?.querySelector('span');
            if (label) label.textContent = target.checked ? 'true' : 'false';
        }
    }
}

function handleParamTemplateListClick(event) {
    const action = event.target.dataset.action || event.target.closest('[data-action]')?.dataset.action;
    const idx = Number(event.target.dataset.index || event.target.closest('[data-index]')?.dataset.index);
    if (action === 'delete-row' && Number.isInteger(idx)) {
        paramTemplateDraft.splice(idx, 1);
        renderParamTemplateRows();
    }
}

async function saveImageParamTemplate() {
    if (editingImageParamServiceIndex < 0) return;
    const defaults = {};
    const enabled = [];
    const paramTypes = {};
    const seen = new Set();

    for (const row of paramTemplateDraft) {
        const key = String(row.key || '').trim();
        if (!key) continue;
        if (seen.has(key)) {
            alert(`参数名重复：${key}`);
            return;
        }
        seen.add(key);
        const type = row.type || 'text';
        defaults[key] = coerceParamTemplateValue(type, row.value);
        paramTypes[key] = type;
        if (row.enabled) enabled.push(key);
    }

    imageServices[editingImageParamServiceIndex] = normalizeImageServiceConfig({
        ...imageServices[editingImageParamServiceIndex],
        default_params: defaults,
        enabled_params: enabled,
        param_types: paramTypes
    });
    await saveImageServices();
    closeImageParamModal();
}

window.editImageParamTemplate = function(idx) {
    openImageParamModal(idx);
};

window.editImageService = function(idx) {
    editingImageServiceIndex = idx;
    const service = imageServices[idx];
    els.newImageServiceName.value = service.name;
    if (els.newImageServiceType) {
        els.newImageServiceType.value = service.service_type || 'zimage';
    }
    els.newImageServiceUrl.value = service.url;
    els.imageServiceAddBtn.innerText = '保存修改';
};

async function addImageService() {
    const name = els.newImageServiceName.value.trim();
    const serviceType = els.newImageServiceType?.value || 'zimage';
    const url = els.newImageServiceUrl.value.trim();
    if (!name || !url) return alert('请填写完整服务信息');

    if (editingImageServiceIndex === -1 || imageServices[editingImageServiceIndex].name !== name) {
        if (imageServices.some(s => s.name === name)) return alert('显示名称已存在');
    }

    if (editingImageServiceIndex === -1) {
        imageServices.push(normalizeImageServiceConfig({ name, url, service_type: serviceType }));
        if (!selectedImageService) selectedImageService = name;
    } else {
        const oldName = imageServices[editingImageServiceIndex].name;
        const previous = imageServices[editingImageServiceIndex];
        const baseConfig = previous.service_type === serviceType ? previous : {};
        imageServices[editingImageServiceIndex] = normalizeImageServiceConfig({
            ...baseConfig,
            name,
            url,
            service_type: serviceType
        });
        if (selectedImageService === oldName) selectedImageService = name;
        editingImageServiceIndex = -1;
        els.imageServiceAddBtn.innerText = '添加服务';
    }

    els.newImageServiceName.value = '';
    if (els.newImageServiceType) {
        els.newImageServiceType.value = 'zimage';
    }
    els.newImageServiceUrl.value = '';
    await saveImageServices();
}

window.deleteImageService = async function(idx) {
    if (!confirm('确定删除该图片生成服务吗？')) return;
    const removed = imageServices.splice(idx, 1)[0];
    if (removed?.name === selectedImageService) {
        selectedImageService = imageServices[0]?.name || '';
    }
    await saveImageServices();
};

window.selectImageService = async function(idx) {
    const service = imageServices[idx];
    if (!service) return;
    selectedImageService = service.name;
    applySelectedImageServiceToPanel();
    await saveImageServices();
    checkImageServiceHealth();
};

window.testImageService = async function(idx) {
    const service = imageServices[idx];
    if (!service) return;
    serviceTestStatuses.image[idx] = { online: false, testing: true };
    renderImageServiceListV3();
    try {
        const res = await API.post('/api/test/image-service', { url: service.url, service_type: service.service_type || 'zimage' });
        serviceTestStatuses.image[idx] = res;
    } catch (e) {
        serviceTestStatuses.image[idx] = { online: false, error: e.message };
    }
    renderImageServiceListV3();
};

async function testSelectedImageService() {
    const idx = imageServices.findIndex(s => s.name === selectedImageService);
    if (idx >= 0) await window.testImageService(idx);
    checkImageServiceHealth();
}

async function saveImageServices() {
    try {
        const res = await API.post('/api/config/image-services', { services: imageServices, selected: selectedImageService });
        imageServices = normalizeImageServiceList(res.services || imageServices);
        selectedImageService = res.selected || selectedImageService || imageServices[0]?.name || '';
        renderImageServiceListV3();
        applySelectedImageServiceToPanel();
    } catch (e) {
        alert('保存图片生成服务失败');
    }
}

async function updateTokenCount() {
    if (!els.tokenCountDisplay) return;
    
    let msgsToCount = [...chatHistory];
    const currentInput = els.chatInput.value.trim();
    if (currentInput) {
        msgsToCount.push({ role: 'user', text: currentInput });
    }
    
    if (msgsToCount.length === 0) {
        els.tokenCountDisplay.innerText = '上下文 Token: 0 (不含思考: 0)';
        return;
    }
    try {
        const res = await API.post('/api/utils/count_tokens', { messages: msgsToCount });
        const countAll = res.count || 0;
        const countNoThink = res.count_no_think || 0;
        els.tokenCountDisplay.innerText = `上下文 Token: ${countAll} (不含思考: ${countNoThink})`;
    } catch (e) {
        console.error('Failed to update token count', e);
    }
}

function renderGallery() {
    els.crudImgGallery.innerHTML = '';
    currentImages.forEach((img, index) => {
        const item = document.createElement('div');
        item.className = 'gallery-item';
        item.innerHTML = `
            <img src="${img.url}" alt="image">
            <button class="delete-btn" onclick="removeGalleryImage(${index})"><i class="bi bi-x-lg"></i></button>
        `;
        els.crudImgGallery.appendChild(item);
    });
}

function removeGalleryImage(index) {
    currentImages.splice(index, 1);
    renderGallery();
}

window.removeGalleryImage = removeGalleryImage; // Make it global for onclick

async function handleCrudImgUpload(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    for (const file of files) {
        try {
            const res = await API.upload(file, currentProject, 'crud');
            currentImages.push({ url: res.url, path: res.path });
        } catch (e) { alert('上传失败'); }
    }
    renderGallery();
    els.crudImgUpload.value = ''; // Reset input
}

async function saveCrudItem() {
    const name = els.crudName.value.trim();
    const info = els.crudInfo.value;
    const img_paths_str = JSON.stringify(currentImages);
    
    if (!name) return alert('名称为必填项');
    
    try {
        if (editingItemName) {
            await API.put(`/api/data/${currentCrudType}/${editingItemName}`, { new_name: name, base_info: info, img_paths: img_paths_str }, currentProject);
        } else {
            await API.post(`/api/data/${currentCrudType}`, { name, base_info: info, img_paths: img_paths_str }, currentProject);
        }
        await loadCrudData(currentCrudType);
        els.crudEditor.classList.add('hidden');
    } catch (e) { alert('保存失败'); }
}

async function deleteCrudItem() {
    if (!editingItemName || !confirm('确定要删除吗？')) return;
    try {
        await API.del(`/api/data/${currentCrudType}/${editingItemName}`, currentProject);
        await loadCrudData(currentCrudType);
        els.crudEditor.classList.add('hidden');
    } catch (e) { alert('删除失败'); }
}

function setGalleryTab(tab) {
    mediaGalleryState.activeTab = tab;
    els.galleryTabs.forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-gallery-tab') === tab);
    });
    renderMediaGallery();
}

function formatGalleryDate(value) {
    if (!value) return '未知时间';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('zh-CN', { hour12: false });
}

function formatGallerySize(size) {
    if (!size || size <= 0) return '';
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function getGalleryTabHint() {
    if (mediaGalleryState.activeTab === 'chat') {
        return '聊天图片来自当前项目的对话缓存目录，删除后会同步清理消息里的引用。';
    }
    if (mediaGalleryState.activeTab === 'generated') {
        return '创建的图片保存在当前项目的 gen_pic 目录，可在这里查看和删除。';
    }
    return '角色图片来自角色管理目录。仍被角色引用的图片不可删除，未归属任何角色的图片可直接清理。';
}

function renderMediaGallery() {
    if (!els.galleryGrid || !els.galleryHint) return;
    const items = mediaGalleryState[mediaGalleryState.activeTab] || [];
    els.galleryHint.textContent = getGalleryTabHint();

    if (items.length === 0) {
        els.galleryGrid.innerHTML = `
            <div class="gallery-empty-state">
                <i class="bi bi-image"></i>
                <p>当前分组还没有可管理的图片</p>
            </div>
        `;
        return;
    }

    els.galleryGrid.innerHTML = items.map(item => {
        const canDelete = mediaGalleryState.activeTab === 'chat' || mediaGalleryState.activeTab === 'generated' || !item.in_use;
        let statusText = '创建的图片，可删除';
        let metaText = '生成图片';
        if (mediaGalleryState.activeTab === 'chat') {
            statusText = `出现于 ${item.dialog_count || 0} 个对话`;
            metaText = `${item.message_count || 0} 条消息`;
        } else if (mediaGalleryState.activeTab === 'character') {
            statusText = item.in_use ? `绑定角色：${(item.character_names || []).join('、')}` : '未绑定角色，可删除';
            metaText = `${(item.character_names || []).length} 个角色`;
        }
        const encodedPath = encodeURIComponent(item.path || '');

        return `
            <article class="media-card">
                <button class="media-card-preview" onclick="window.open('${item.url}', '_blank')">
                    <img src="${item.url}" alt="${item.filename}">
                </button>
                <div class="media-card-body">
                    <div class="media-card-header">
                        <h3 title="${item.filename}">${item.filename}</h3>
                        <span class="media-badge ${canDelete ? 'is-free' : 'is-locked'}">${canDelete ? '可清理' : '使用中'}</span>
                    </div>
                    <p class="media-card-status" title="${statusText}">${statusText}</p>
                    <div class="media-card-meta">
                        <span>${metaText}</span>
                        <span>${formatGallerySize(item.size)}</span>
                        <span>${formatGalleryDate(item.updated_at)}</span>
                    </div>
                    <div class="media-card-actions">
                        <button class="btn btn-outline btn-sm" onclick="window.open('${item.url}', '_blank')">查看原图</button>
                        <button class="btn btn-secondary btn-sm" ${canDelete ? '' : 'disabled'} onclick="deleteGalleryImage('${mediaGalleryState.activeTab}', '${encodedPath}')">删除</button>
                    </div>
                </div>
            </article>
        `;
    }).join('');
}

async function loadMediaGallery() {
    try {
        const data = await API.get('/api/gallery', currentProject);
        mediaGalleryState.chat = data.chat || [];
        mediaGalleryState.character = data.character || [];
        mediaGalleryState.generated = data.generated || [];
        renderMediaGallery();
    } catch (e) {
        console.error('Failed to load gallery', e);
        if (els.galleryGrid) {
            els.galleryGrid.innerHTML = `
                <div class="gallery-empty-state">
                    <i class="bi bi-exclamation-circle"></i>
                    <p>图库加载失败，请稍后重试</p>
                </div>
            `;
        }
    }
}

async function deleteGalleryImage(scope, encodedPath) {
    const imagePath = decodeURIComponent(encodedPath || '');
    if (!imagePath) return;

    const confirmText = scope === 'chat'
        ? '确定删除这张聊天图片吗？对应聊天记录中的图片引用也会一并清理。'
        : (scope === 'generated' ? '确定删除这张创建的图片吗？' : '确定删除这张未绑定角色的图片吗？');
    if (!confirm(confirmText)) return;

    try {
        const res = await API.del(`/api/gallery/${scope}`, currentProject, { path: imagePath });
        if (!res.success && res.reason === 'in_use') {
            alert('这张角色图片仍属于某个角色，暂时不能删除。');
            return;
        }
        await loadMediaGallery();
        if (scope === 'chat' || scope === 'generated') {
            await loadDialogs();
            const activeDialog = allDialogs.find(d => d.id === currentDialogId);
            if (activeDialog) {
                chatHistory = activeDialog.messages || [];
                renderMessages();
            }
        }
    } catch (e) {
        alert(scope === 'character' ? '删除角色图片失败' : '删除聊天图片失败');
    }
}

window.deleteGalleryImage = deleteGalleryImage;

function sendToPreload() {
    const info = els.crudInfo.value;
    if (currentCrudType === 'character') {
        els.preloadCharacter.value += (els.preloadCharacter.value ? '\n\n' : '') + info;
    } else if (currentCrudType === 'template') {
        els.preloadTemplate.value += (els.preloadTemplate.value ? '\n\n' : '') + info;
    }
    alert('已发送到预载配置。');
}

function formatTextWithThink(text) {
    if (!text) return '';
    
    let processedText = text;
    
    // Normalize missing <think> tags for models like Qwen3.5 that output "Thinking Process:" or omit <think>
    if (/^(Thinking Process|Thinking process|思考过程[:：]?\s*)/i.test(processedText)) {
        processedText = processedText.replace(/^(Thinking Process|Thinking process|思考过程[:：]?\s*)/i, '<think>\n');
    } else if (processedText.includes('</think>') && !processedText.includes('<think>')) {
        processedText = '<think>\n' + processedText;
    }
    // If it's still streaming and we don't have <think> but we strongly suspect it's reasoning (e.g. starts with step 1 or is Qwen)
    // Actually, if it's supposed to have thinking but misses the tag, we can check if there's no <think> and no </think>
    // but the user enabled thinking. It's safer to just rely on the 'Thinking Process:' prefix or wait for </think>.

    const parts = processedText.split('<think>');
    if (parts.length === 1) {
        return marked.parse(processedText);
    }
    
    let result = marked.parse(parts[0]);
    for (let i = 1; i < parts.length; i++) {
        const subParts = parts[i].split('</think>');
        const thinkContent = subParts[0];
        const isStreaming = subParts.length === 1;
        
        let thinkHtml = `<details class="think-block" ${isStreaming ? 'open' : ''}>
            <summary>思考过程</summary>
            <div class="think-content">
                ${marked.parse(thinkContent)}
            </div>
        </details>`;
        
        result += thinkHtml;
        if (!isStreaming) {
            result += marked.parse(subParts.slice(1).join('</think>'));
        }
    }
    return result;
}

// --- AI Scenario Logic ---

function getSelectedModelInfo() {
    const option = els.modelSelect?.selectedOptions?.[0];
    return {
        name: els.modelSelect?.value || '',
        source: option?.dataset?.source || 'OpenAI'
    };
}

function showScenarioPanel(panel) {
    [els.scenarioHome, els.scenarioSetup, els.scenarioGame].forEach(el => {
        if (el) el.classList.add('hidden');
    });
    if (panel) panel.classList.remove('hidden');
}

async function showScenarioHome() {
    showScenarioPanel(els.scenarioHome);
    await loadScenarioGames();
}

async function loadScenarioGames() {
    if (!els.scenarioGameList) return;
    try {
        const data = await API.get('/api/scenario/games', currentProject);
        scenarioState.games = data.games || [];
        if (scenarioState.games.length === 0) {
            els.scenarioGameList.innerHTML = `
                <div class="scenario-empty">
                    <i class="bi bi-diagram-3"></i>
                    <h3>暂无推演</h3>
                    <p>新建一个场景，设定背景、角色和初始状态后即可开始。</p>
                </div>
            `;
            return;
        }
        els.scenarioGameList.innerHTML = scenarioState.games.map(game => `
            <div class="scenario-list-item">
                <div>
                    <h3>${escapeHtml(fixMojibake(game.title))}</h3>
                    <p>状态：${escapeHtml(game.status)} · 第 ${game.current_turn} 回合 · 更新：${escapeHtml(game.updated_at)}</p>
                </div>
                <div class="scenario-list-actions">
                    <button class="btn btn-secondary" data-scenario-edit="${game.id}">编辑设定</button>
                    <button class="btn btn-primary" data-scenario-open="${game.id}">继续游戏</button>
                    <button class="btn btn-text" data-scenario-delete="${game.id}">删除</button>
                </div>
            </div>
        `).join('');
        els.scenarioGameList.querySelectorAll('[data-scenario-open]').forEach(btn => {
            btn.addEventListener('click', () => openScenarioGame(btn.dataset.scenarioOpen));
        });
        els.scenarioGameList.querySelectorAll('[data-scenario-edit]').forEach(btn => {
            btn.addEventListener('click', () => openScenarioSetup(btn.dataset.scenarioEdit));
        });
        els.scenarioGameList.querySelectorAll('[data-scenario-delete]').forEach(btn => {
            btn.addEventListener('click', () => deleteScenarioGame(btn.dataset.scenarioDelete));
        });
    } catch (e) {
        els.scenarioGameList.innerHTML = `<div class="scenario-empty error">${escapeHtml(e.message)}</div>`;
    }
}

async function createScenarioGame() {
    try {
        const data = await API.post('/api/scenario/games', { title: '未命名剧本' }, currentProject);
        await openScenarioSetup(data.game_id, true);
    } catch (e) {
        alert(e.message);
    }
}

function scenarioDefaultRoles() {
    return [
        {
            name: '顾明',
            public_info: '年轻的律师，表面冷静，习惯观察每个人的细节。',
            goal_prompt: '你要尽量找出真相，同时隐藏自己曾经见过死者的事实。',
            is_human: false
        },
        {
            name: '沈玥',
            public_info: '庄园主人的侄女，举止优雅，但情绪紧绷。',
            goal_prompt: '你要保护家族名誉，避免旧账被公开。',
            is_human: false
        },
        {
            name: '玩家',
            public_info: '受邀来到庄园的调查者。',
            goal_prompt: '你要推进调查，识破其他人的谎言。',
            is_human: true
        }
    ];
}

async function openScenarioSetup(gameId, useDefaults = false) {
    try {
        const data = await API.get(`/api/scenario/games/${gameId}`, currentProject);
        scenarioState.currentGameId = Number(gameId);
        scenarioState.state = data;
        const game = data.game;
        els.scenarioSetupTitle.textContent = game.status === 'draft' ? '初始条件设定' : '编辑推演设定';
        els.scenarioTitle.value = fixMojibake(game.title || '');
        els.scenarioBackground.value = fixMojibake(game.background || '');
        els.scenarioScene.value = fixMojibake(game.scene || '');
        els.scenarioInitialState.value = fixMojibake(game.initial_state || '');
        els.scenarioMainStoryInput.value = fixMojibake(game.main_story || '');
        els.scenarioRolesEditor.innerHTML = '';
        const roles = data.roles.length ? data.roles : (useDefaults ? scenarioDefaultRoles() : []);
        roles.forEach(addScenarioRole);
        if (roles.length === 0) scenarioDefaultRoles().forEach(addScenarioRole);
        showScenarioPanel(els.scenarioSetup);
    } catch (e) {
        alert(e.message);
    }
}

function addScenarioRole(role = {}) {
    const id = `scenario-role-${generateId()}`;
    const div = document.createElement('div');
    div.className = 'scenario-role-card';
    div.id = id;
    div.innerHTML = `
        <div class="scenario-role-card-header">
            <input class="scenario-role-name" value="${escapeHtml(role.name || '')}" placeholder="角色名">
            <label class="toggle-control">
                <div class="toggle-switch">
                    <input type="checkbox" class="scenario-role-human" ${role.is_human ? 'checked' : ''}>
                    <span class="slider"></span>
                </div>
                <span>真人控制</span>
            </label>
            <button class="icon-btn" title="删除角色"><i class="bi bi-trash"></i></button>
        </div>
        <textarea class="scenario-role-info" rows="3" placeholder="角色公开信息">${escapeHtml(role.public_info || '')}</textarea>
        <textarea class="scenario-role-goal" rows="3" placeholder="角色目标 / 隐藏提示词">${escapeHtml(role.goal_prompt || '')}</textarea>
    `;
    div.querySelector('.icon-btn').addEventListener('click', () => div.remove());
    els.scenarioRolesEditor.appendChild(div);
}

function collectScenarioRoles() {
    return Array.from(els.scenarioRolesEditor.querySelectorAll('.scenario-role-card')).map(card => ({
        name: card.querySelector('.scenario-role-name').value.trim(),
        public_info: card.querySelector('.scenario-role-info').value,
        goal_prompt: card.querySelector('.scenario-role-goal').value,
        is_human: card.querySelector('.scenario-role-human').checked
    })).filter(role => role.name);
}

function parseCharacterExtraTexts(value) {
    if (!value) return [];
    if (Array.isArray(value)) return value.map(item => String(item || '').trim()).filter(Boolean);
    if (typeof value === 'string') {
        const text = value.trim();
        if (!text) return [];
        if (text.startsWith('[')) {
            try {
                const parsed = JSON.parse(text);
                if (Array.isArray(parsed)) return parsed.map(item => String(item || '').trim()).filter(Boolean);
            } catch (e) {}
        }
        return [text];
    }
    return [];
}

async function importScenarioRolesFromCharacters() {
    try {
        const characters = await API.get('/api/data/character', currentProject);
        openScenarioImportModal(Array.isArray(characters) ? characters : []);
    } catch (e) {
        alert(`导入失败：${e.message}`);
    }
}

function getScenarioExistingRoleNames() {
    return new Set(
        Array.from(els.scenarioRolesEditor.querySelectorAll('.scenario-role-name'))
            .map(input => (input.value || '').trim())
            .filter(Boolean)
    );
}

function openScenarioImportModal(characters) {
    scenarioImportState.characters = (characters || []).map((ch, idx) => ({
        ...ch,
        __idx: idx
    }));
    scenarioImportState.selected = new Set();
    if (!scenarioImportState.characters.length) {
        alert('当前项目没有可导入的角色。');
        return;
    }
    renderScenarioImportModal();
    els.scenarioImportModal?.classList.remove('hidden');
}

function closeScenarioImportModal() {
    els.scenarioImportModal?.classList.add('hidden');
}

function renderScenarioImportModal() {
    if (!els.scenarioImportList) return;
    const existingNames = getScenarioExistingRoleNames();
    const selectable = scenarioImportState.characters.filter(ch => {
        const name = (ch.name || '').trim();
        return name && !existingNames.has(name);
    });
    if (els.scenarioImportCount) {
        els.scenarioImportCount.textContent = `已选 ${scenarioImportState.selected.size} 项`;
    }
    if (selectable.length === 0) {
        els.scenarioImportList.innerHTML = '<div class="scenario-import-empty">没有可导入的角色：要么当前项目没有角色，要么都已经在场景里了。</div>';
        return;
    }
    els.scenarioImportList.innerHTML = scenarioImportState.characters.map((ch, idx) => {
        const name = (ch.name || '').trim();
        const isDuplicate = !name || existingNames.has(name);
        const checked = scenarioImportState.selected.has(name);
        const preview = fixMojibake((ch.base_info || '').trim()).slice(0, 180);
        const extraPreview = parseCharacterExtraTexts(ch.extra_texts)
            .map(item => fixMojibake(item))
            .join(' / ')
            .slice(0, 120);
        return `
            <label class="scenario-import-row ${isDuplicate ? 'is-disabled' : ''}">
                <input
                    type="checkbox"
                    data-scenario-import-name="${escapeHtml(name)}"
                    ${checked ? 'checked' : ''}
                    ${isDuplicate ? 'disabled' : ''}
                >
                <div class="scenario-import-row-main">
                    <div class="scenario-import-row-title">
                        <span class="scenario-import-row-name">${escapeHtml(name || '未命名角色')}</span>
                        ${isDuplicate ? '<span class="scenario-import-row-badge is-exist">已在场景中</span>' : ''}
                    </div>
                    <div class="scenario-import-row-meta">
                        <span class="scenario-import-row-preview">${escapeHtml(preview || '无公开信息')}</span>
                        <span class="scenario-import-row-preview">${escapeHtml(extraPreview || '无目标提示词')}</span>
                    </div>
                </div>
                <div class="scenario-import-row-badge">${idx + 1}</div>
            </label>
        `;
    }).join('');
    updateScenarioImportCount();
}

function updateScenarioImportCount() {
    if (els.scenarioImportCount) {
        els.scenarioImportCount.textContent = `已选 ${scenarioImportState.selected.size} 项`;
    }
}

function scenarioSetImportSelection(checked) {
    const existingNames = getScenarioExistingRoleNames();
    scenarioImportState.selected = new Set(
        scenarioImportState.characters
            .map(ch => (ch.name || '').trim())
            .filter(name => name && !existingNames.has(name) && checked)
    );
    if (!checked) {
        scenarioImportState.selected.clear();
    }
    renderScenarioImportModal();
}

function handleScenarioImportListChange(event) {
    const target = event.target;
    if (!target || !target.matches('[data-scenario-import-name]')) return;
    const name = (target.dataset.scenarioImportName || '').trim();
    if (!name) return;
    if (target.checked) {
        scenarioImportState.selected.add(name);
    } else {
        scenarioImportState.selected.delete(name);
    }
    updateScenarioImportCount();
}

function commitScenarioImportSelection() {
    const existingNames = getScenarioExistingRoleNames();
    const selectedNames = scenarioImportState.characters
        .map(ch => (ch.name || '').trim())
        .filter(name => name && scenarioImportState.selected.has(name) && !existingNames.has(name));
    if (selectedNames.length === 0) {
        alert('请先勾选至少一个可导入角色。');
        return;
    }
    let imported = 0;
    selectedNames.forEach(name => {
        const ch = scenarioImportState.characters.find(item => (item.name || '').trim() === name);
        if (!ch) return;
        const extras = parseCharacterExtraTexts(ch.extra_texts);
        addScenarioRole({
            name,
            public_info: ch.base_info || '',
            goal_prompt: extras.join('\n'),
            is_human: false
        });
        imported += 1;
    });
    closeScenarioImportModal();
    alert(`已导入 ${imported} 个角色。`);
}

async function saveScenarioSetup() {
    const gameId = scenarioState.currentGameId;
    if (!gameId) return;
    await API.put(`/api/scenario/games/${gameId}`, {
        title: els.scenarioTitle.value,
        background: els.scenarioBackground.value,
        scene: els.scenarioScene.value,
        initial_state: els.scenarioInitialState.value,
        main_story: els.scenarioMainStoryInput.value
    }, currentProject);
    await API.post(`/api/scenario/games/${gameId}/roles`, { roles: collectScenarioRoles() }, currentProject);
}

async function startScenarioGame() {
    try {
        await saveScenarioSetup();
        await API.post(`/api/scenario/games/${scenarioState.currentGameId}/start`, {}, currentProject);
        await openScenarioGame(scenarioState.currentGameId);
    } catch (e) {
        alert(e.message);
    }
}

async function openScenarioGame(gameId) {
    try {
        const data = await API.get(`/api/scenario/games/${gameId}`, currentProject);
        scenarioState.currentGameId = Number(gameId);
        scenarioState.state = data;
        scenarioState.roleOrder = (data.roles || []).map(role => ({ ...role }));
        renderScenarioGame(data);
        showScenarioPanel(els.scenarioGame);
    } catch (e) {
        alert(e.message);
    }
}

function renderScenarioGame(data) {
    const { game, roles, turn, actions } = data;
    const gameTitle = fixMojibake(game.title || 'AI场景推演');
    const gameStatus = fixMojibake(game.status || '进行中');
    const sceneText = fixMojibake(game.scene || '未填写');

    els.scenarioGameTitle.textContent = gameTitle;
    els.scenarioStoryMeta.textContent = `状态：${gameStatus} · 第 ${game.current_turn} 回合 · 当前场景：${sceneText}`;

    renderScenarioStoryPane(data);

    // Store hidden data
    if (els.scenarioPendingResolution) {
        els.scenarioPendingResolution.value = sanitizeScenarioText(turn.pending_resolution || '');
    }
    if (els.scenarioFinalResolution) {
        els.scenarioFinalResolution.value = sanitizeScenarioText(turn.final_resolution || '');
    }
    if (els.scenarioThinkingToggle) {
        els.scenarioThinkingToggle.checked = !!scenarioState.enableThinking;
    }

    // Update toolbar buttons visibility
    const hasResolution = !!(turn.pending_resolution || '').trim();
    const hasNarrative = !!(turn.final_resolution || '').trim();
    if (els.scenarioGenerateNarrativeBtn) {
        els.scenarioGenerateNarrativeBtn.style.display = hasResolution ? '' : 'none';
    }
    if (els.scenarioCommitBtn) {
        els.scenarioCommitBtn.style.display = hasNarrative ? '' : 'none';
    }

    // Build stream messages
    renderScenarioStream(data);
    setScenarioStatus('待机');
}

// ---- Stream rendering ----

function scrollStreamToBottom() {
    const log = els.scenarioStreamLog;
    if (!log) return;
    log.scrollTop = log.scrollHeight;
    requestAnimationFrame(() => { if (log) log.scrollTop = log.scrollHeight; });
}

function addStreamMsg(html, cls = '') {
    const log = els.scenarioStreamLog;
    if (!log) return null;
    const div = document.createElement('div');
    div.className = `sc-msg ${cls}`;
    div.innerHTML = html;
    log.appendChild(div);
    scrollStreamToBottom();
    return div;
}

function addStreamSystemMsg(text, icon = 'bi-info-circle') {
    return addStreamMsg(`<i class="bi ${icon}"></i><span>${escapeHtml(text)}</span>`, 'sc-msg-system');
}

function addStreamAssistantMsg(label, initialHtml = '') {
    const div = addStreamMsg(`
        <div class="sc-msg-label"><i class="bi bi-robot"></i>${escapeHtml(label)}</div>
        <div class="sc-msg-body">${initialHtml}</div>
    `, 'sc-msg-assistant');
    return div ? div.querySelector('.sc-msg-body') : null;
}

function renderScenarioStream(data) {
    const log = els.scenarioStreamLog;
    if (!log) return;
    log.innerHTML = '';

    const { game, roles, turn, actions } = data;

    // 1. Status header
    addStreamSystemMsg(
        `第 ${game.current_turn} 回合 · ${fixMojibake(game.scene || '未设定场景')}`,
        'bi-compass'
    );

    // 2. Human action inputs
    const humans = (roles || []).filter(r => r.is_human);
    if (humans.length > 0) {
        humans.forEach(role => {
            const div = addStreamMsg(`
                <h4><i class="bi bi-person-fill"></i> ${escapeHtml(role.name)} · 真人行动</h4>
                <textarea rows="2" id="sc-speech-${role.id}" placeholder="本回合发言"></textarea>
                <textarea rows="2" id="sc-action-${role.id}" placeholder="本回合行动"></textarea>
                <button class="sc-submit-btn" data-sc-human="${role.id}">提交行动</button>
            `, 'sc-msg-human-input');
            if (div) {
                div.querySelector(`[data-sc-human="${role.id}"]`).addEventListener('click', () => {
                    submitScenarioHumanAction(role.id);
                });
            }
        });
    }

    // 3. Current actions (on-hold pool)
    if (actions && actions.length > 0) {
        addStreamSystemMsg(`当前回合已有 ${actions.length} 个行动`, 'bi-collection');
        actions.forEach(action => {
            const normalized = normalizeScenarioAction(action);
            addStreamMsg(`
                <div class="sc-action-header">
                    <span class="sc-action-name">${escapeHtml(fixMojibake(action.role_name))}</span>
                    <span class="sc-action-source">${escapeHtml(action.source)}</span>
                </div>
                <div class="sc-action-detail"><strong>发言：</strong>${escapeHtml(normalized.speech || '无')}</div>
                <div class="sc-action-detail"><strong>行动：</strong>${escapeHtml(normalized.action || '无')}</div>
            `, 'sc-msg-action');
        });
    }

    // 4. Resolution content (if exists)
    const resolution = sanitizeScenarioText(turn.pending_resolution || '');
    if (resolution) {
        addStreamSystemMsg('管理员裁定已生成，可编辑后继续', 'bi-clipboard-check');
        const resDiv = addStreamMsg(`
            <div class="sc-msg-label"><i class="bi bi-clipboard-data"></i>管理员裁定</div>
            <textarea class="sc-editable-area" id="sc-resolution-edit" rows="6">${escapeHtml(resolution)}</textarea>
        `, 'sc-msg-assistant');
        if (resDiv) {
            const ta = resDiv.querySelector('#sc-resolution-edit');
            if (ta) {
                ta.addEventListener('input', () => {
                    if (els.scenarioPendingResolution) els.scenarioPendingResolution.value = ta.value;
                });
            }
        }
        // Show decision to generate narrative
        addStreamMsg(`
            <div class="sc-decision-text"><i class="bi bi-question-circle"></i> 裁定内容就绪，是否生成主故事线正文？</div>
            <div class="sc-decision-actions">
                <button class="sc-decision-btn sc-btn-confirm" id="sc-btn-gen-narrative"><i class="bi bi-pencil-square"></i> 生成正文</button>
                <button class="sc-decision-btn sc-btn-regen" id="sc-btn-regen-resolve"><i class="bi bi-arrow-clockwise"></i> 重新结算</button>
            </div>
        `, 'sc-msg-decision');
        document.getElementById('sc-btn-gen-narrative')?.addEventListener('click', () => runScenarioStep('narrate_turn'));
        document.getElementById('sc-btn-regen-resolve')?.addEventListener('click', () => runScenarioStep('resolve_turn'));
    }

    // 5. Final narrative (if exists)
    const narrative = sanitizeScenarioText(turn.final_resolution || '');
    if (narrative) {
        addStreamSystemMsg('主故事线正文草稿已生成', 'bi-pencil-square');
        const narDiv = addStreamMsg(`
            <div class="sc-msg-label"><i class="bi bi-book"></i>主故事线正文草稿</div>
            <textarea class="sc-editable-area" id="sc-narrative-edit" rows="6">${escapeHtml(narrative)}</textarea>
        `, 'sc-msg-assistant');
        if (narDiv) {
            const ta = narDiv.querySelector('#sc-narrative-edit');
            if (ta) {
                ta.addEventListener('input', () => {
                    if (els.scenarioFinalResolution) els.scenarioFinalResolution.value = ta.value;
                });
            }
        }
        // Commit decision
        addStreamMsg(`
            <div class="sc-decision-text"><i class="bi bi-check-circle"></i> 正文就绪，是否写入主故事线？</div>
            <div class="sc-decision-actions">
                <button class="sc-decision-btn sc-btn-confirm" id="sc-btn-commit"><i class="bi bi-check-lg"></i> 确认写入</button>
                <button class="sc-decision-btn sc-btn-regen" id="sc-btn-regen-narrative"><i class="bi bi-arrow-clockwise"></i> 重新生成</button>
            </div>
        `, 'sc-msg-decision');
        document.getElementById('sc-btn-commit')?.addEventListener('click', commitScenarioTurn);
        document.getElementById('sc-btn-regen-narrative')?.addEventListener('click', () => runScenarioStep('narrate_turn'));
    }

    scrollStreamToBottom();
}

// ---- Role order view (toggled as stream overlay) ----

function toggleScenarioOrderView() {
    const log = els.scenarioStreamLog;
    if (!log) return;
    // Check if order view already exists
    const existing = log.querySelector('.sc-msg-order');
    if (existing) {
        existing.remove();
        return;
    }
    renderScenarioRoleOrderInStream();
}

function renderScenarioRoleOrderInStream() {
    const roles = scenarioState.roleOrder;
    if (!roles || !roles.length) {
        addStreamSystemMsg('当前没有可调整顺序的角色', 'bi-arrow-down-up');
        return;
    }
    const itemsHtml = roles.map((role, idx) => `
        <div class="sc-order-item">
            <div class="sc-order-item-left">
                <span class="sc-order-num">${idx + 1}</span>
                <span class="sc-order-name">${escapeHtml(fixMojibake(role.name || '未命名'))}</span>
                <span class="sc-order-badge ${role.is_human ? 'is-human' : ''}">${role.is_human ? '真人' : 'AI'}</span>
            </div>
            <div class="sc-order-btns">
                <button class="sc-order-btn" data-sc-order-up="${idx}" ${idx === 0 ? 'disabled' : ''} title="上移"><i class="bi bi-arrow-up"></i></button>
                <button class="sc-order-btn" data-sc-order-down="${idx}" ${idx === roles.length - 1 ? 'disabled' : ''} title="下移"><i class="bi bi-arrow-down"></i></button>
            </div>
        </div>
    `).join('');

    const div = addStreamMsg(`
        <h4><i class="bi bi-arrow-down-up"></i> 行动顺序调整</h4>
        <p style="color:#94a3b8;font-size:0.82rem;margin-bottom:10px;">后行动角色会读取前面角色本回合已发生的发言和行动。</p>
        <div class="sc-order-list">${itemsHtml}</div>
        <button class="sc-order-save-btn" id="sc-save-order">保存顺序</button>
    `, 'sc-msg-order');

    if (div) {
        div.querySelectorAll('[data-sc-order-up]').forEach(btn => {
            btn.addEventListener('click', () => {
                moveScenarioRoleOrder(Number(btn.dataset.scOrderUp), -1);
                div.remove();
                renderScenarioRoleOrderInStream();
            });
        });
        div.querySelectorAll('[data-sc-order-down]').forEach(btn => {
            btn.addEventListener('click', () => {
                moveScenarioRoleOrder(Number(btn.dataset.scOrderDown), 1);
                div.remove();
                renderScenarioRoleOrderInStream();
            });
        });
        div.querySelector('#sc-save-order')?.addEventListener('click', saveScenarioRoleOrder);
    }
    scrollStreamToBottom();
}

function renderScenarioRoleOrder(roles) {
    scenarioState.roleOrder = (roles || []).map(role => ({ ...role }));
}

function moveScenarioRoleOrder(index, delta) {
    const targetIndex = index + delta;
    if (index < 0 || targetIndex < 0 || targetIndex >= scenarioState.roleOrder.length) return;
    const nextOrder = [...scenarioState.roleOrder];
    [nextOrder[index], nextOrder[targetIndex]] = [nextOrder[targetIndex], nextOrder[index]];
    scenarioState.roleOrder = nextOrder;
}

async function saveScenarioRoleOrder() {
    if (!scenarioState.currentGameId || !scenarioState.roleOrder.length) return;
    await API.post(`/api/scenario/games/${scenarioState.currentGameId}/role-order`, {
        role_ids: scenarioState.roleOrder.map(role => role.id)
    }, currentProject);
    await openScenarioGame(scenarioState.currentGameId);
    addStreamSystemMsg('行动顺序已更新', 'bi-check-circle');
}

function renderScenarioHumanActions(roles) {
    // No-op: handled in renderScenarioStream
}

function renderScenarioActions(actions) {
    // No-op: handled in renderScenarioStream
}

async function submitScenarioHumanAction(roleId) {
    const speech = document.getElementById(`sc-speech-${roleId}`)?.value || '';
    const action = document.getElementById(`sc-action-${roleId}`)?.value || '';
    await API.post(`/api/scenario/games/${scenarioState.currentGameId}/human_action`, {
        role_id: roleId,
        speech: speech,
        action: action
    }, currentProject);
    await openScenarioGame(scenarioState.currentGameId);
}

function setScenarioStatus(text, isError = false) {
    if (!els.scenarioStatus) return;
    els.scenarioStatus.textContent = text;
    els.scenarioStatus.classList.toggle('error', isError);
}

function setScenarioConsoleView() {
    // No-op: old function, kept for compatibility
}

function renderScenarioConsoleView() {
    // No-op: old function, kept for compatibility
}

// ---- Streaming step execution ----

async function runScenarioStep(step) {
    if (!scenarioState.currentGameId) return;
    setScenarioStatus('运行中...');
    const allBtns = [els.scenarioGenerateActionsBtn, els.scenarioResolveBtn, els.scenarioGenerateNarrativeBtn, els.scenarioSummarizeBtn, els.scenarioCommitBtn];
    allBtns.forEach(btn => { if (btn) btn.disabled = true; });

    // Add status message to stream
    const stepLabels = {
        'generate_ai_actions': '生成 AI 行动',
        'resolve_turn': '管理员结算',
        'narrate_turn': '生成主故事线正文',
        'summarize': '压缩上下文'
    };
    addStreamSystemMsg(`正在执行：${stepLabels[step] || step}...`, 'bi-hourglass-split');

    let currentBody = addStreamAssistantMsg(stepLabels[step] || step);
    let buffered = '';

    try {
        const payload = { step, model_info: getSelectedModelInfo(), enable_thinking: !!scenarioState.enableThinking };
        if (step === 'narrate_turn') {
            // Sync from inline editor if present
            const inlineEdit = document.getElementById('sc-resolution-edit');
            if (inlineEdit) {
                els.scenarioPendingResolution.value = inlineEdit.value;
            }
            payload.adjudication = sanitizeScenarioText(els.scenarioPendingResolution?.value || '');
        }
        const response = await fetch(`/api/scenario/games/${scenarioState.currentGameId}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Project': currentProject
            },
            body: JSON.stringify(payload)
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let pending = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            pending += decoder.decode(value, { stream: true });
            const events = pending.split('\n\n');
            pending = events.pop();
            for (const rawEvent of events) {
                const line = rawEvent.split('\n').find(item => item.startsWith('data:'));
                if (!line) continue;
                const event = JSON.parse(line.slice(5));
                if (event.type === 'section') {
                    buffered = '';
                    currentBody = addStreamAssistantMsg(sanitizeScenarioText(event.title));
                } else if (event.type === 'delta') {
                    buffered += sanitizeScenarioOutputText(event.text || '');
                    if (currentBody) currentBody.innerHTML = formatTextWithThink(buffered);
                    scrollStreamToBottom();
                } else if (event.type === 'status') {
                    setScenarioStatus(sanitizeScenarioText(event.message || '运行中...'));
                } else if (event.type === 'error') {
                    setScenarioStatus(sanitizeScenarioText(event.message || '执行失败'), true);
                    addStreamSystemMsg(`错误：${sanitizeScenarioText(event.message || '执行失败')}`, 'bi-exclamation-triangle');
                } else if (event.type === 'done') {
                    if (event.resolution) els.scenarioPendingResolution.value = sanitizeScenarioText(event.resolution);
                    if (event.narrative && els.scenarioFinalResolution) els.scenarioFinalResolution.value = sanitizeScenarioText(event.narrative);
                    setScenarioStatus('完成');
                } else if (event.type === 'result') {
                    setScenarioStatus(sanitizeScenarioText(event.message || '已保存'));
                }
            }
        }
        // Refresh game state to rebuild stream with updated data
        await openScenarioGame(scenarioState.currentGameId);
        showScenarioPanel(els.scenarioGame);
    } catch (e) {
        setScenarioStatus(e.message, true);
        addStreamSystemMsg(`执行出错：${e.message}`, 'bi-exclamation-triangle');
    } finally {
        allBtns.forEach(btn => { if (btn) btn.disabled = false; });
    }
}

async function commitScenarioTurn() {
    // Sync from inline editor if present
    const inlineEdit = document.getElementById('sc-narrative-edit');
    if (inlineEdit) {
        els.scenarioFinalResolution.value = inlineEdit.value;
    }
    const finalResolution = sanitizeScenarioText(els.scenarioFinalResolution?.value || '').trim();
    if (els.scenarioFinalResolution) els.scenarioFinalResolution.value = finalResolution;
    if (!finalResolution) {
        setScenarioStatus('主故事线正文草稿为空，不能写入。', true);
        addStreamSystemMsg('写入失败：正文草稿为空', 'bi-exclamation-triangle');
        return;
    }
    addStreamSystemMsg('正在写入主故事线...', 'bi-hourglass-split');
    await API.post(`/api/scenario/games/${scenarioState.currentGameId}/commit_turn`, {
        final_resolution: finalResolution
    }, currentProject);
    addStreamSystemMsg('已成功写入主故事线，进入下一回合', 'bi-check-circle');
    await openScenarioGame(scenarioState.currentGameId);
}

async function clearScenarioSummary() {
    await API.post(`/api/scenario/games/${scenarioState.currentGameId}/clear_summary`, {}, currentProject);
    addStreamSystemMsg('已取消压缩', 'bi-arrows-expand');
    await openScenarioGame(scenarioState.currentGameId);
}

async function clearScenarioBoard() {
    if (!scenarioState.currentGameId) return;
    const ok = confirm('确认清空当前回合的所有行动和结算内容吗？');
    if (!ok) return;
    await API.post(`/api/scenario/games/${scenarioState.currentGameId}/clear_board`, {}, currentProject);
    addStreamSystemMsg('当前回合已清空', 'bi-eraser');
    await openScenarioGame(scenarioState.currentGameId);
}

async function resetScenarioProgress() {
    if (!scenarioState.currentGameId) return;
    const ok = confirm('确认清空所有推进内容吗？会保留设定和角色，只重置故事推进、回合和看板内容。');
    if (!ok) return;
    await API.post(`/api/scenario/games/${scenarioState.currentGameId}/reset_progress`, {}, currentProject);
    await openScenarioGame(scenarioState.currentGameId);
}

async function deleteScenarioGame(gameId) {
    if (!confirm('确定删除这个推演吗？')) return;
    await API.del(`/api/scenario/games/${gameId}`, currentProject);
    await showScenarioHome();
}

function renderScenarioStoryPane(data) {
    const isModelView = scenarioState.storyView === 'model_context';
    const content = isModelView
        ? sanitizeScenarioText(data.model_context_preview || '暂无模型上下文。')
        : sanitizeScenarioText(data.main_story_preview || data.game?.main_story || '暂无主故事线。');
    const tokens = isModelView
        ? data.token_counts?.model_context ?? 0
        : data.token_counts?.main_story ?? 0;
    els.scenarioMainStory.innerHTML = marked.parse(content);
    if (els.scenarioStoryTokens) {
        els.scenarioStoryTokens.textContent = `Token: ${tokens}`;
    }
    els.scenarioViewMainBtn?.classList.toggle('active', !isModelView);
    els.scenarioViewModelBtn?.classList.toggle('active', isModelView);
}

function setScenarioStoryView(view) {
    scenarioState.storyView = view;
    if (scenarioState.state) {
        renderScenarioStoryPane(scenarioState.state);
    }
}

function fixMojibake(value) {
    const text = String(value ?? '');
    if (!/[ÃÂåæèéäöüð\u0080-\u009f]/.test(text)) return text;
    try {
        const bytes = Uint8Array.from(Array.from(text), ch => ch.charCodeAt(0) & 0xff);
        const decoded = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
        const badScore = (text.match(/[ÃÂåæèéäöüð\u0080-\u009f]/g) || []).length;
        const decodedBadScore = (decoded.match(/[ÃÂåæèéäöüð\u0080-\u009f]/g) || []).length;
        return decodedBadScore < badScore ? decoded : text;
    } catch (e) {
        return text;
    }
}

function normalizeScenarioAction(action) {
    let speech = sanitizeScenarioText(action.speech || '').trim();
    let act = sanitizeScenarioText(action.action || '').trim();
    if (!speech && act) {
        const match = act.match(/(?:^|\n)\s*(?:发言|speech|说的话)\s*[:：]\s*([\s\S]*?)(?:\n\s*(?:行动|action)\s*[:：]\s*([\s\S]*))?$/i);
        if (match) {
            speech = (match[1] || '').trim();
            act = (match[2] || '').trim();
        }
    }
    return { speech, action: act };
}

function sanitizeScenarioText(value) {
    let text = fixMojibake(value);
    text = text.replace(/<think>\s*<\/think>/gi, '');
    text = text.replace(/<\/?think>/gi, '');
    return text.trim();
}

function sanitizeScenarioOutputText(value) {
    let text = fixMojibake(value);
    text = text.replace(/<think>\s*<\/think>/gi, '');
    return text;
}

// Run
document.addEventListener('DOMContentLoaded', init);
