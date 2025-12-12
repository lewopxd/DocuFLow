// js/project-manager.js
/**
 * Project: DocuFlow
 * File:  project-manager.js
 * Created: 2025-12-11
 * Author: @lewopxd
 *
 * Description:
 * Frontend project state management.
 * Handles auto-save, state collection, and state restoration.
 */

import { AppService } from './services.js';

//-------------------------------------------------------------
//-------------[   AUTO-SAVE CLASS   ]-------------------------
//-------------------------------------------------------------

/**
 * Manages automatic project saving with debounce.
 */
class ProjectAutoSave {
    constructor(intervalMs = 10000) {  // 10 seconds for testing (change to 60000 for production)
        this.intervalMs = intervalMs;
        this.isDirty = false;
        this.timer = null;
        this.currentPath = null;
        this.enabled = true;
    }

    /**
     * Marks the project as dirty (needs saving).
     */
    markDirty() {
        if (!this.enabled) return;
        this.isDirty = true;
        console.log('[AutoSave] Project marked dirty');
    }

    /**
     * Sets the current project path.
     * @param {string} path 
     */
    setPath(path) {
        this.currentPath = path;
    }

    /**
     * Starts the auto-save timer.
     */
    start() {
        if (this.timer) {
            clearInterval(this.timer);
        }

        this.timer = setInterval(() => {
            if (this.isDirty && this.currentPath) {
                this._save();
            }
        }, this.intervalMs);

        console.log(`[AutoSave] Started with ${this.intervalMs}ms interval`);
    }

    /**
     * Stops the auto-save timer.
     */
    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
        console.log('[AutoSave] Stopped');
    }

    /**
     * Performs the save operation.
     */
    async _save() {
        if (!this.currentPath) {
            console.warn('[AutoSave] No project path set');
            return;
        }

        console.log('[AutoSave] Saving project...');

        try {
            const projectState = collectProjectState();
            const result = await AppService.saveProject(this.currentPath, projectState);

            if (result.success) {
                this.isDirty = false;
                console.log('[AutoSave] ✅ Project saved');
            } else {
                console.error('[AutoSave] ❌ Failed:', result.error);
            }
        } catch (error) {
            console.error('[AutoSave] ❌ Error:', error);
        }
    }

    /**
     * Triggers an immediate save (e.g., on file load/close).
     */
    async triggerImmediateSave() {
        this.markDirty();
        await this._save();
    }
}

//--------------------------------------> END [ AUTO-SAVE CLASS ... ]

//-------------------------------------------------------------
//-------------[   STATE COLLECTION   ]------------------------
//-------------------------------------------------------------

/**
 * Collects the current project state from all panels.
 * @returns {object} Project state object.
 */
function collectProjectState() {
    const layoutState = getLayoutState();
    console.log('[ProjectManager] Collected layout:', layoutState);

    const state = {
        meta: {
            version: "1.0.0",
            appVersion: "1.0.0.8",
            lastModifiedAt: new Date().toISOString()
        },
        layout: layoutState,
        panels: {
            dataPanel: getDataPanelState(),
            templatesPanel: getTemplatesPanelState()
        },
        automation: {
            outputFolder: null,
            namingPattern: "output_{{ROW}}",
            format: "pdf"
        }
    };

    return state;
}

/**
 * Gets the current layout state (panel sizes as percentages).
 * @returns {object} Layout state.
 */
function getLayoutState() {
    const layout = {
        columns: {
            leftColumnPercent: 50,
            rightColumnPercent: 50
        },
        leftColumn: {
            topPanelPercent: 60,
            bottomPanelPercent: 40,
            topCollapsed: false,
            bottomCollapsed: false
        },
        rightColumn: {
            topPanelPercent: 70,
            bottomPanelPercent: 30,
            topCollapsed: false,
            bottomCollapsed: false
        }
    };

    // Calculate actual percentages from DOM
    try {
        const mainContainer = document.getElementById('main-container');
        const leftColumn = document.getElementById('left-column');
        const rightColumn = document.getElementById('right-column');

        if (mainContainer && leftColumn && rightColumn) {
            const totalWidth = mainContainer.clientWidth;
            const leftWidth = leftColumn.clientWidth;

            if (totalWidth > 0) {
                layout.columns.leftColumnPercent = Math.round((leftWidth / totalWidth) * 100);
                layout.columns.rightColumnPercent = 100 - layout.columns.leftColumnPercent;
            }
        }

        // Left column panels
        const leftTop = document.getElementById('left-top-panel');
        const leftBottom = document.getElementById('left-bottom-panel');

        if (leftTop && leftBottom && leftColumn) {
            const colHeight = leftColumn.clientHeight;
            const topHeight = leftTop.clientHeight;

            if (colHeight > 0) {
                layout.leftColumn.topPanelPercent = Math.round((topHeight / colHeight) * 100);
                layout.leftColumn.bottomPanelPercent = 100 - layout.leftColumn.topPanelPercent;
            }
            layout.leftColumn.topCollapsed = leftTop.classList.contains('collapsed');
            layout.leftColumn.bottomCollapsed = leftBottom.classList.contains('collapsed');
        }

        // Right column panels
        const rightTop = document.getElementById('right-top-panel');
        const rightBottom = document.getElementById('right-bottom-panel');

        if (rightTop && rightBottom && rightColumn) {
            const colHeight = rightColumn.clientHeight;
            const topHeight = rightTop.clientHeight;

            if (colHeight > 0) {
                layout.rightColumn.topPanelPercent = Math.round((topHeight / colHeight) * 100);
                layout.rightColumn.bottomPanelPercent = 100 - layout.rightColumn.topPanelPercent;
            }
            layout.rightColumn.topCollapsed = rightTop.classList.contains('collapsed');
            layout.rightColumn.bottomCollapsed = rightBottom.classList.contains('collapsed');
        }

    } catch (e) {
        console.error('[ProjectManager] Error calculating layout:', e);
    }

    return layout;
}

/**
 * Gets the data panel state.
 * Calls the module's exportPanelState if available.
 * @returns {object}
 */
function getDataPanelState() {
    if (window.DataPanel && typeof window.DataPanel.exportPanelState === 'function') {
        return window.DataPanel.exportPanelState();
    }

    // Fallback: basic state from DOM
    return {
        activeTabIndex: 0,
        tabs: []
    };
}

/**
 * Gets the templates panel state.
 * Calls the module's exportPanelState if available.
 * @returns {object}
 */
function getTemplatesPanelState() {
    if (window.TemplatesPanel && typeof window.TemplatesPanel.exportPanelState === 'function') {
        return window.TemplatesPanel.exportPanelState();
    }

    // Fallback: basic state from DOM
    return {
        activeTabIndex: 0,
        tabs: []
    };
}

//--------------------------------------> END [ STATE COLLECTION ... ]

//-------------------------------------------------------------
//-------------[   STATE APPLICATION   ]-----------------------
//-------------------------------------------------------------

/**
 * Applies a project state to the UI.
 * @param {object} project - The project data to apply.
 */
async function applyProjectState(project) {
    console.log('[ProjectManager] Applying project state...', project);

    // 1. Apply layout first (before panels populate)
    if (project.layout) {
        console.log('[ProjectManager] Layout to apply:', project.layout);
        // Delay more to ensure DOM and container sizes are ready
        setTimeout(() => {
            applyLayoutState(project.layout);
        }, 300);
    } else {
        console.log('[ProjectManager] No layout in project');
    }

    // 2. Apply panel states
    if (project.panels) {
        if (project.panels.dataPanel && window.DataPanel &&
            typeof window.DataPanel.importPanelState === 'function') {
            await window.DataPanel.importPanelState(project.panels.dataPanel);
        }

        if (project.panels.templatesPanel && window.TemplatesPanel &&
            typeof window.TemplatesPanel.importPanelState === 'function') {
            await window.TemplatesPanel.importPanelState(project.panels.templatesPanel);
        }
    }

    console.log('[ProjectManager] Project state applied');
}

/**
 * Applies layout state (panel sizes) to the DOM.
 * @param {object} layout - Layout configuration.
 */
function applyLayoutState(layout) {
    try {
        const mainContainer = document.getElementById('main-container');
        const leftColumn = document.getElementById('left-column');
        const rightColumn = document.getElementById('right-column');

        // Apply column widths
        if (layout.columns && leftColumn && rightColumn && mainContainer) {
            const totalWidth = mainContainer.clientWidth;
            const leftPercent = layout.columns.leftColumnPercent || 50;

            leftColumn.style.flexGrow = '0';
            leftColumn.style.flexBasis = `${(totalWidth * leftPercent) / 100}px`;

            rightColumn.style.flexGrow = '0';
            rightColumn.style.flexBasis = `${(totalWidth * (100 - leftPercent)) / 100}px`;
        }

        // Apply left column panel heights
        if (layout.leftColumn) {
            const leftTop = document.getElementById('left-top-panel');
            const leftBottom = document.getElementById('left-bottom-panel');
            const leftCol = document.getElementById('left-column');

            if (leftTop && leftBottom && leftCol) {
                const colHeight = leftCol.clientHeight;
                const topPercent = layout.leftColumn.topPanelPercent || 60;

                leftTop.style.flexGrow = '0';
                leftTop.style.flexBasis = `${(colHeight * topPercent) / 100}px`;

                leftBottom.style.flexGrow = '0';
                leftBottom.style.flexBasis = `${(colHeight * (100 - topPercent)) / 100}px`;
            }
        }

        // Apply right column panel heights  
        if (layout.rightColumn) {
            const rightTop = document.getElementById('right-top-panel');
            const rightBottom = document.getElementById('right-bottom-panel');
            const rightCol = document.getElementById('right-column');

            if (rightTop && rightBottom && rightCol) {
                const colHeight = rightCol.clientHeight;
                const topPercent = layout.rightColumn.topPanelPercent || 70;

                rightTop.style.flexGrow = '0';
                rightTop.style.flexBasis = `${(colHeight * topPercent) / 100}px`;

                rightBottom.style.flexGrow = '0';
                rightBottom.style.flexBasis = `${(colHeight * (100 - topPercent)) / 100}px`;
            }
        }

        console.log('[ProjectManager] Layout state applied');

    } catch (e) {
        console.error('[ProjectManager] Error applying layout:', e);
    }
}

//--------------------------------------> END [ STATE APPLICATION ... ]

//-------------------------------------------------------------
//-------------[   STARTUP FLOW   ]----------------------------
//-------------------------------------------------------------

/**
 * Checks for and loads the last project on startup.
 * If no project exists, creates a default one.
 * @returns {Promise<boolean>} True if a project was loaded or created.
 */
async function checkAndLoadProject() {
    console.log('[ProjectManager] Checking for last project...');

    try {
        const info = await AppService.getProjectInfo();

        console.log('[ProjectManager] Project info:', info);

        if (info.autoLoad && info.exists && info.path) {
            // Load existing project
            console.log(`[ProjectManager] Auto-loading project: ${info.path}`);

            const result = await AppService.loadProject(info.path);

            if (result.success) {
                await applyProjectState(result.project);

                // Show notification for missing files
                if (result.missingFiles && result.missingFiles.length > 0) {
                    console.warn('[ProjectManager] Missing files:', result.missingFiles);
                }

                // Start auto-save
                if (info.autoSaveEnabled) {
                    autoSave.setPath(info.path);
                    autoSave.intervalMs = (info.autoSaveIntervalSeconds || 60) * 1000;
                    autoSave.start();
                }

                console.log('[ProjectManager] ✅ Project loaded successfully');
                return true;
            } else {
                console.error('[ProjectManager] Failed to load project:', result.error);
            }
        } else {
            // No existing project - create a default one
            console.log('[ProjectManager] No project found, creating default...');

            // Default path: same folder as app config (AppData/DocuFlow/default.bkproj)
            // We'll ask the backend to create it in the AppData folder
            const defaultPath = await createDefaultProject();

            if (defaultPath) {
                autoSave.setPath(defaultPath);
                autoSave.intervalMs = (info.autoSaveIntervalSeconds || 60) * 1000;
                autoSave.start();
                console.log('[ProjectManager] ✅ Default project created and auto-save started');
                return true;
            }
        }

    } catch (e) {
        console.error('[ProjectManager] Error in startup flow:', e);
    }

    return false;
}

/**
 * Creates a default project in the AppData folder.
 * @returns {Promise<string|null>} The path of the created project, or null on failure.
 */
async function createDefaultProject() {
    try {
        // Request backend to create default project
        // The backend will use the AppData folder path
        const result = await AppService.newProject('__DEFAULT__', 'DocuFlow Project');

        if (result.success && result.path) {
            console.log('[ProjectManager] Default project created at:', result.path);
            return result.path;
        } else {
            console.error('[ProjectManager] Failed to create default project:', result.error);
            return null;
        }
    } catch (e) {
        console.error('[ProjectManager] Error creating default project:', e);
        return null;
    }
}

//--------------------------------------> END [ STARTUP FLOW ... ]

// --- SINGLETON & EXPORTS ---

// Singleton auto-save instance
const autoSave = new ProjectAutoSave();

// Expose globally for modules to access
window.ProjectManager = {
    autoSave,
    collectProjectState,
    applyProjectState,
    getLayoutState,
    applyLayoutState,
    checkAndLoadProject,
    markDirty: () => autoSave.markDirty()
};

export {
    ProjectAutoSave,
    autoSave,
    collectProjectState,
    applyProjectState,
    getLayoutState,
    applyLayoutState,
    checkAndLoadProject
};
