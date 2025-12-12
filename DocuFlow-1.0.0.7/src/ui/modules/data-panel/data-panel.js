// modules/data-panel/data-panel.js
/**
 * Project: DocuFlow
 * File:  modules/data-panel/data-panel.js
 * Created: 2025-11-04
 * Author: @lewopxd
 *
 * Description:
 * The main controller and logic for the Data Panel Module.
 * This module is responsible for:
 * - Loading and parsing Excel/Sheet data.
 * - Displaying the data structure in a tree OR as an ExcelViewer grid.
 * - Managing its own tabs and state.
 * * NOTE: This module's logic runs *inside* the .module-content container
 * * created by main.js.
 */

//-------------------------------------------------------------
//-------------[   MODULE IMPORTS   ]--------------------------
//-------------------------------------------------------------

import { AppService } from '../../js/services.js';
import {
    ICON_CLOSE,
    ICON_PLUS,
    ICON_FILE_SHEET,
    ICON_RELOAD,
    ICON_LAYOUT_GRID,
    ICON_LAYOUT_TREE
} from '../../js/icons.js';

//-------------------------------------------------------------
//-------------[   MODULE STATE   ]----------------------------
//-------------------------------------------------------------

/** @type {Array<string>} In-memory list of file paths for this panel. */
let currentSheetPaths = [];

/** @type {object} Map of containerId -> PanetonTree instance. */
let treeInstances = {};

/** @type {object} Map of containerId -> ExcelViewer instance. */
let excelViewerInstances = {};

/** @type {object | null} Reference to the Paneton.Tree library. */
const PanetonTree = window.Paneton ? window.Paneton.Tree : null;

// DOM element references, set by initialize()
let panelId = 'data-panel';
let tabsContainer = null;
let contentContainer = null;
let placeholder = null;
let loadSheetButton = null;

//-------------------------------------------------------------
//-------------[   MODULE CONFIGURATION   ]--------------------
//-------------------------------------------------------------

/**
 * @type {boolean}
 * Set to false to allow only one tab at a time.
 * When false, the add button is hidden after loading a file.
 */
const ALLOW_MULTIPLE_TABS = false;

//-------------------------------------------------------------
//-------------[   MODULE INITIALIZATION   ]-------------------
//-------------------------------------------------------------

/**
 * [Initializes the Data Panel module.]
 * @param {HTMLElement} panelElement - The container element (.module-content).
 * @exports
 */
export async function initialize(panelElement) {
    if (!panelElement) return;

    // 1. Set module-level DOM references
    tabsContainer = panelElement.querySelector('.toolbar-tabs');
    contentContainer = panelElement.querySelector('.panel-content');
    placeholder = panelElement.querySelector('.placeholder');

    if (!tabsContainer || !contentContainer || !placeholder) {
        console.error('[DataPanel] Module HTML structure is missing required elements.');
        return;
    }

    // 2. Setup load button
    loadSheetButton = panelElement.querySelector('#load-sheet-button');
    if (loadSheetButton) {
        loadSheetButton.innerHTML = ICON_PLUS;
        loadSheetButton.addEventListener('click', handleLoadSheetWorkflow);
    }

    // 3. Initialize tab click handling
    setupTabClickHandling();

    // 4. Load settings and restore previous session tabs
    await loadAndRestoreSession_Data();

    console.log('[DataPanel] Module initialized.');
}

//-------------------------------------------------------------
//-------------[   MODULE WORKFLOWS (Private)   ]--------------
//-------------------------------------------------------------

/**
 * [Full workflow for loading a Data Sheet using Split API.]
 */
async function handleLoadSheetWorkflow() {
    try {
        const fileTypes = [
            'Spreadsheets (*.xlsx;*.xls;*.csv)',
            'All Files (*.*)'
        ];

        // 1. Get file path
        const response = await AppService.requestFileDialog({ fileTypes });

        if (!response || !response.filePath) {
            console.log('[DataPanel] User cancelled selection.');
            return;
        }

        const filePath = response.filePath;
        const fileName = filePath.split(/[\\/]/).pop();

        // ========== SPLIT API: Step 1 - Load Structure (Fast) ==========
        console.log(`[DataPanel] Loading structure for: ${fileName}`);
        const fileStructure = await AppService.getExcelStructure(filePath);

        if (!fileStructure) {
            console.error(`[DataPanel] Could not retrieve structure for ${fileName}.`);
            return;
        }

        console.log(`[DataPanel] ✅ Structure loaded for: ${fileName}`);

        // 2. Transform structure to Paneton format
        const panetonData = excelStructureToPanetonData(fileStructure);

        // 3. Create the tab and get the tree container ID
        const treeContainerId = addTab(fileName, { filePath }, ICON_FILE_SHEET, fileStructure);

        // 4. Inject Paneton Tree immediately (fast UX)
        if (treeContainerId) {
            initializePanetonTree(treeContainerId, panetonData);
            setupPanelControls(treeContainerId, filePath);
        }

        // 5. Extract and expose columns for cross-module access (auto-match)
        const allColumns = extractColumnsFromStructure(fileStructure);
        exposeAvailableColumns(allColumns);

        // 6. Persist state
        await updateSheetPathsAndSave(filePath);

        // 7. Hide add button if multiple tabs not allowed
        if (!ALLOW_MULTIPLE_TABS && loadSheetButton) {
            loadSheetButton.style.display = 'none';
        }

        // ========== SPLIT API: Step 2 - Load Full Data (Background) ==========
        console.log(`[DataPanel] Loading full data for: ${fileName}`);
        const fullData = await AppService.getExcelFullData(filePath);

        if (fullData) {
            console.log(`[DataPanel] ✅ Full data loaded for: ${fileName}`);
            // Cache full data in the content pane
            const tab = document.querySelector(`[data-file-path="${CSS.escape(filePath)}"]`);
            if (tab) {
                const contentPaneSelector = tab.dataset.tabTarget;
                const contentPane = contentPaneSelector ? contentContainer.querySelector(contentPaneSelector) : null;
                if (contentPane) {
                    contentPane.fullDataCache = fullData;
                }
            }
        } else {
            console.warn(`[DataPanel] Could not load full data for ${fileName}.`);
        }

    } catch (error) {
        console.error('[DataPanel] Error during Load Sheet Workflow:', error);
    }
}

/**
 * [Loads persistent settings and restores session for this module.]
 */
async function loadAndRestoreSession_Data() {
    try {
        const settings = await AppService.loadSettings();

        if (settings.last_opened_sheet && Array.isArray(settings.last_opened_sheet)) {
            currentSheetPaths = settings.last_opened_sheet;
            for (const path of currentSheetPaths) {
                const fileName = path.split(/[\\/]/).pop();

                // Step 1: Load structure (fast)
                const fileStructure = await AppService.getExcelStructure(path);

                if (fileStructure) {
                    const panetonData = excelStructureToPanetonData(fileStructure);

                    const treeContainerId = addTab(fileName, { filePath: path }, ICON_FILE_SHEET, fileStructure);

                    if (treeContainerId) {
                        initializePanetonTree(treeContainerId, panetonData);
                        setupPanelControls(treeContainerId, path);
                    }

                    // Step 2: Load full data in background
                    AppService.getExcelFullData(path).then(fullData => {
                        if (fullData) {
                            const tab = document.querySelector(`[data-file-path="${CSS.escape(path)}"]`);
                            if (tab) {
                                const contentPaneSelector = tab.dataset.tabTarget;
                                const contentPane = contentPaneSelector ? contentContainer.querySelector(contentPaneSelector) : null;
                                if (contentPane) {
                                    contentPane.fullDataCache = fullData;
                                }
                            }
                        }
                    });

                } else {
                    console.warn(`[DataPanel] Skipping restoration of ${fileName}: Structure not found.`);
                }
            }

            // Hide add button if we restored tabs
            if (!ALLOW_MULTIPLE_TABS && currentSheetPaths.length > 0 && loadSheetButton) {
                loadSheetButton.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('[DataPanel] Could not load persistent settings:', error);
    }
}

/**
 * [Sets up listeners for the path bar controls (Reload, Toggle).]
 */
function setupPanelControls(treeContainerId, filePath) {
    const treeContainer = document.getElementById(treeContainerId);
    if (!treeContainer) return;

    // Navigate up: treeContainer -> tree-static-container -> tree-wrapper -> tab-content-grid
    const treeWrapper = treeContainer.closest('.tree-wrapper');
    const gridWrapper = treeWrapper ? treeWrapper.closest('.tab-content-grid') : null;
    if (!gridWrapper) return;

    const controlsContainer = gridWrapper.querySelector('.status-bar__controls');
    if (!controlsContainer) return;

    controlsContainer.addEventListener('click', (e) => {
        const btn = e.target.closest('.icon-button');
        if (!btn) return;

        const action = btn.dataset.action;
        const contentPane = gridWrapper.closest('.tab-content');

        if (action === 'reload') {
            reloadSheetData(filePath, treeContainerId, contentPane, btn);
        } else if (action === 'toggle-view') {
            const spreadsheetId = contentPane?.dataset.spreadsheetId;
            toggleView(treeContainerId, spreadsheetId, filePath, contentPane, btn);
        }
    });
}

/**
 * [Reloads the data for a specific sheet.]
 */
async function reloadSheetData(filePath, treeContainerId, contentPane, btnElement) {
    console.log(`[DataPanel] Reloading data for: ${filePath}`);

    const originalHtml = btnElement.innerHTML;
    btnElement.innerHTML = '...';
    btnElement.disabled = true;

    const treeContainer = document.getElementById(treeContainerId);
    const spreadsheetId = contentPane?.dataset.spreadsheetId;
    const spreadsheetWrapper = spreadsheetId ? document.getElementById(spreadsheetId) : null;
    const treeWrapper = treeContainer?.closest('.tree-wrapper');

    const spinnerHtml = '<div class="loading-spinner-container"><div class="loading-spinner"></div></div>';

    // Show spinner in visible container
    if (treeWrapper && treeWrapper.style.display !== 'none' && treeContainer) {
        treeContainer.innerHTML = spinnerHtml;
    }
    if (spreadsheetWrapper && spreadsheetWrapper.style.display !== 'none') {
        spreadsheetWrapper.innerHTML = spinnerHtml;
        if (excelViewerInstances[spreadsheetId]) {
            delete excelViewerInstances[spreadsheetId];
        }
    }

    try {
        const fileStructure = await AppService.getExcelStructure(filePath);

        if (fileStructure) {
            // Update caches
            if (contentPane) {
                contentPane.structureCache = fileStructure;
            }

            // Re-init tree
            const panetonData = excelStructureToPanetonData(fileStructure);
            initializePanetonTree(treeContainerId, panetonData);

            // Reload full data
            const fullData = await AppService.getExcelFullData(filePath);
            if (fullData && contentPane) {
                contentPane.fullDataCache = fullData;

                // Re-init ExcelViewer if visible
                if (spreadsheetWrapper && spreadsheetWrapper.style.display !== 'none') {
                    spreadsheetWrapper.innerHTML = '';
                    initializeExcelViewer(spreadsheetId, fileStructure, fullData);
                }
            }

            console.log('[DataPanel] ✅ Reload complete.');
        } else {
            console.error('[DataPanel] Failed to reload structure.');
        }
    } catch (err) {
        console.error('[DataPanel] Error reloading data:', err);
    } finally {
        btnElement.innerHTML = originalHtml;
        btnElement.disabled = false;
    }
}

/**
 * [Toggles between Tree view and ExcelViewer.]
 */
function toggleView(treeContainerId, spreadsheetId, filePath, contentPane, btn) {
    const treeContainer = document.getElementById(treeContainerId);
    const treeWrapper = treeContainer?.closest('.tree-wrapper');
    const spreadsheetWrapper = spreadsheetId ? document.getElementById(spreadsheetId) : null;

    if (!treeWrapper || !spreadsheetWrapper) {
        console.warn('[DataPanel] Toggle view: Missing elements');
        return;
    }

    const isTreeVisible = treeWrapper.style.display !== 'none';

    if (isTreeVisible) {
        // Switch to ExcelViewer
        treeWrapper.style.display = 'none';
        spreadsheetWrapper.style.display = 'flex';
        btn.innerHTML = ICON_LAYOUT_TREE;
        btn.title = 'Switch to Tree View';

        // Lazy-init ExcelViewer if not exists
        if (!excelViewerInstances[spreadsheetId]) {
            const cachedStructure = contentPane?.structureCache;
            const cachedData = contentPane?.fullDataCache;

            if (cachedStructure && cachedData) {
                initializeExcelViewer(spreadsheetId, cachedStructure, cachedData);
            } else if (cachedStructure && !cachedData) {
                // Data still loading - show spinner and wait
                spreadsheetWrapper.innerHTML = '<div class="loading-spinner-container"><div class="loading-spinner"></div></div>';
                AppService.getExcelFullData(filePath).then(fullData => {
                    if (fullData && contentPane) {
                        contentPane.fullDataCache = fullData;
                        spreadsheetWrapper.innerHTML = '';
                        initializeExcelViewer(spreadsheetId, cachedStructure, fullData);
                    }
                });
            }
        }
    } else {
        // Switch to Tree
        treeWrapper.style.display = 'block';
        spreadsheetWrapper.style.display = 'none';
        btn.innerHTML = ICON_LAYOUT_GRID;
        btn.title = 'Switch to Spreadsheet View';
    }
}

/**
 * [Initializes an ExcelViewer in the given container.]
 */
function initializeExcelViewer(containerId, structure, fullData) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (window.ExcelViewer) {
        const viewer = new window.ExcelViewer(container, {
            structure: structure,
            sheets: fullData || {}
        });
        excelViewerInstances[containerId] = viewer;
        console.log('[DataPanel] ✅ ExcelViewer initialized.');
    } else {
        console.warn('[DataPanel] ExcelViewer library not found.');
        container.innerHTML = '<div style="padding:20px;text-align:center;opacity:0.6;">ExcelViewer not available</div>';
    }
}

//-------------------------------------------------------------
//-------------[   MODULE STATE & MUTATORS (Private)   ]-------
//-------------------------------------------------------------

async function updateSheetPathsAndSave(filePath) {
    if (!currentSheetPaths.includes(filePath)) {
        currentSheetPaths.push(filePath);
        await AppService.saveUiSetting('last_opened_sheet', currentSheetPaths)
            .catch(err => console.error('[DataPanel] Failed to save sheet list:', err));
    }
}

function handleCloseTabWorkflow(tabElement) {
    const filePath = tabElement.dataset.filePath;

    // Remove from in-memory state
    currentSheetPaths = currentSheetPaths.filter(p => p !== filePath);

    // Save updated state
    AppService.saveUiSetting('last_opened_sheet', currentSheetPaths)
        .catch(err => console.error(`[DataPanel] Failed to save state after closing tab: ${err}`));

    return {
        success: true,
        tabElement: tabElement,
        remainingTabsCount: tabsContainer.querySelectorAll('.tab:not(#load-sheet-button)').length - 1,
        wasActive: tabElement.classList.contains('active'),
        targetPaneSelector: tabElement.dataset.tabTarget
    };
}

//-------------------------------------------------------------
//-------------[   UI DOM HELPERS (Private)   ]----------------
//-------------------------------------------------------------

function removeTabAndRestoreState(tabElement, targetPaneSelector, remainingTabsCount, wasActive) {
    const contentPane = contentContainer.querySelector(targetPaneSelector);
    if (contentPane) {
        // Cleanup instances
        const treeId = contentPane.dataset.treeContainerId;
        const spreadsheetId = contentPane.dataset.spreadsheetId;
        if (treeId && treeInstances[treeId]) delete treeInstances[treeId];
        if (spreadsheetId && excelViewerInstances[spreadsheetId]) delete excelViewerInstances[spreadsheetId];
        contentPane.remove();
    }
    tabElement.remove();

    if (remainingTabsCount === 0) {
        if (placeholder) placeholder.style.display = 'block';
        // Show add button again
        if (!ALLOW_MULTIPLE_TABS && loadSheetButton) {
            loadSheetButton.style.display = '';
        }
    } else if (wasActive) {
        const remainingTabs = tabsContainer.querySelectorAll('.tab:not(#load-sheet-button)');
        const lastTab = remainingTabs[remainingTabs.length - 1];
        if (lastTab) {
            lastTab.classList.add('active');
            const targetPane = contentContainer.querySelector(lastTab.dataset.tabTarget);
            if (targetPane) targetPane.classList.add('active');
        }
    }
}

function setupTabClickHandling() {
    tabsContainer.addEventListener('click', (e) => {
        const clickedTab = e.target.closest('.tab');

        if (!clickedTab || clickedTab.id === 'load-sheet-button') return;

        const clickedClose = e.target.closest('.tab-close');

        // Handle Tab Close
        if (clickedClose) {
            const result = handleCloseTabWorkflow(clickedTab);
            if (result.success) {
                removeTabAndRestoreState(
                    result.tabElement,
                    result.targetPaneSelector,
                    result.remainingTabsCount,
                    result.wasActive
                );
            }
            return;
        }

        // Handle Tab Activation
        if (placeholder) placeholder.style.display = 'none';

        tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        clickedTab.classList.add('active');
        const targetPane = contentContainer.querySelector(clickedTab.dataset.tabTarget);
        if (targetPane) targetPane.classList.add('active');
    });
}

//-------------------------------------------------------------
//-------------[   DYNAMIC DOM BUILDERS (Private)   ]----------
//-------------------------------------------------------------

function _calculateFileStats(fileStructure) {
    const { metadata, sheets } = fileStructure;
    let tableCount = 0, columnCount = 0, totalRows = 0;

    sheets.forEach(sheet => {
        tableCount += sheet.tables.length;
        sheet.tables.forEach(table => {
            columnCount += table.columns.length;
            totalRows += table.rowCount;
        });
    });

    return {
        size: `${metadata.fileSizeKB || 0} KB`,
        sheetCount: metadata.sheetCount || sheets.length,
        tableCount,
        columnCount,
        totalRows
    };
}

function _createMetaBox(label, value) {
    const box = document.createElement('div');
    box.className = 'meta-stat-box meta-stat-box--bottom';

    const labelSpan = document.createElement('span');
    labelSpan.className = 'meta-stat-label';
    labelSpan.textContent = `${label}:`;

    const valueSpan = document.createElement('span');
    valueSpan.className = 'meta-stat-value';
    valueSpan.textContent = value;

    box.appendChild(labelSpan);
    box.appendChild(valueSpan);

    return box;
}

function excelStructureToPanetonData(excelStructure) {
    if (!excelStructure || !excelStructure.sheets) return [];
    const { metadata, sheets } = excelStructure;

    const fileNode = {
        name: metadata.fileName,
        path: metadata.fileName,
        type: 'file',
        expanded: true,
        children: []
    };

    sheets.forEach(sheet => {
        const sheetNode = {
            name: sheet.sheetName,
            path: `${metadata.fileName}/${sheet.sheetName}`,
            type: 'sheet',
            expanded: true,
            children: []
        };

        sheet.tables.forEach(table => {
            const displayTableName = table.isNamedTable ? table.tableName : `UNNAMED_TABLE (Full Sheet)`;
            const tableNode = {
                name: displayTableName,
                path: `${metadata.fileName}/${sheet.sheetName}/${table.tableName}`,
                type: 'table',
                expanded: false,
                children: []
            };

            table.columns.forEach(columnName => {
                const columnNode = {
                    name: columnName,
                    path: `${tableNode.path}/${columnName}`,
                    type: 'column',
                    isLeaf: true,
                    buttons: [
                        {
                            tooltip: 'Toggle Selection State',
                            icon: (PanetonTree && PanetonTree.icon)
                                ? PanetonTree.icon.visibility.off
                                : (window.Paneton?.Tree?.DEFAULT_BUTTON_ICON || '👁'),
                            onClick: (nodeApi) => {
                                console.log(`[DataPanel] Toggled column: ${nodeApi.path}`);
                            }
                        }
                    ]
                };
                tableNode.children.push(columnNode);
            });
            sheetNode.children.push(tableNode);
        });

        if (sheetNode.children.length > 0) {
            fileNode.children.push(sheetNode);
        }
    });
    return [fileNode];
}

function initializePanetonTree(containerId, treeData) {
    const treeContainer = document.getElementById(containerId);
    if (!treeContainer) {
        console.error(`[DataPanel] Paneton Tree: Container #${containerId} not found.`);
        return;
    }

    treeContainer.innerHTML = '';
    treeContainer.classList.add('paneton-tree-container');

    if (PanetonTree) {
        const tree = new PanetonTree(treeContainer, {
            data: treeData,
            sortNodes: false,
            compactFolders: false,
            autoHideButtons: 'activeNode'
        });
        treeInstances[containerId] = tree;
    } else {
        console.error('[DataPanel] Paneton.Tree library not found.');
    }
}

function addTab(tabName, data = {}, fileIconSvg = '', fileStructure = null) {
    if (placeholder && placeholder.style.display !== 'none') {
        placeholder.style.display = 'none';
    }

    // Deactivate existing tabs
    tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // Create Tab
    const newTab = document.createElement('div');
    newTab.className = 'tab active';

    const parts = tabName.match(/^(.*?)(\.[^.]*)?$/) || [null, tabName, ''];
    const name = parts[1];

    newTab.innerHTML = `
        <div class="tab-icon">${fileIconSvg}</div>
        <div class="tab-name-wrapper">
            <span class="tab-label">${name}</span>
            <span class="tab-ext">${parts[2] || ''}</span>
        </div>
        <div class="tab-close">${ICON_CLOSE}</div>
    `;

    // Create Content Pane
    const newContentPane = document.createElement('div');
    newContentPane.className = 'tab-content active';
    const contentId = `${panelId}-content-${Date.now()}`;
    newContentPane.id = contentId;

    // Link tab and content
    newTab.dataset.tabTarget = `#${contentId}`;
    if (data.filePath) {
        newTab.dataset.filePath = data.filePath;
        newTab.title = data.filePath;
    }

    // Insert tab before action button
    const actionButton = tabsContainer.querySelector('#load-sheet-button');
    tabsContainer.insertBefore(newTab, actionButton);
    contentContainer.appendChild(newContentPane);

    // Build content grid if fileStructure is provided
    if (fileStructure) {
        const gridWrapper = document.createElement('div');
        gridWrapper.className = 'tab-content-grid';
        newContentPane.appendChild(gridWrapper);

        const stats = _calculateFileStats(fileStructure);
        const fullPath = fileStructure.metadata.fullPath || data.filePath || '';
        const fileName = fileStructure.metadata.fileName || tabName;
        const directoryPath = fullPath.replace(fileName, '');

        // 1. Path Bar with Controls
        const pathBar = document.createElement('div');
        pathBar.className = 'status-bar__path';

        const pathInput = document.createElement('input');
        pathInput.type = 'text';
        pathInput.className = 'status-bar__path-input';
        pathInput.value = `${directoryPath}${fileName}`;
        pathInput.readOnly = true;
        pathBar.appendChild(pathInput);

        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'status-bar__controls';

        // Reload Button
        const reloadBtn = document.createElement('button');
        reloadBtn.className = 'icon-button';
        reloadBtn.title = 'Reload Data';
        reloadBtn.innerHTML = ICON_RELOAD;
        reloadBtn.dataset.action = 'reload';
        controlsDiv.appendChild(reloadBtn);

        // Toggle View Button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'icon-button';
        toggleBtn.title = 'Switch to Spreadsheet View';
        toggleBtn.innerHTML = ICON_LAYOUT_GRID;
        toggleBtn.dataset.action = 'toggle-view';
        controlsDiv.appendChild(toggleBtn);

        pathBar.appendChild(controlsDiv);

        // 2. Tree Wrapper with Static Container
        const treeWrapper = document.createElement('div');
        treeWrapper.className = 'tree-wrapper';

        const staticContainer = document.createElement('div');
        staticContainer.className = 'tree-static-container';
        const treeContainerId = `tree-container-${Date.now()}`;
        staticContainer.id = treeContainerId;
        staticContainer.innerHTML = '<div class="loading-spinner-container"><div class="loading-spinner"></div></div>';
        treeWrapper.appendChild(staticContainer);

        // 3. Spreadsheet Wrapper (hidden)
        const spreadsheetWrapper = document.createElement('div');
        spreadsheetWrapper.className = 'spreadsheet-wrapper';
        spreadsheetWrapper.style.display = 'none';
        const spreadsheetId = `spreadsheet-container-${Date.now()}`;
        spreadsheetWrapper.id = spreadsheetId;

        // Store IDs and caches on content pane
        newContentPane.dataset.treeContainerId = treeContainerId;
        newContentPane.dataset.spreadsheetId = spreadsheetId;
        newContentPane.structureCache = fileStructure;

        // 4. Meta Bar
        const metaBar = document.createElement('div');
        metaBar.className = 'meta-bar';

        const metaBarRow = document.createElement('div');
        metaBarRow.className = 'meta-bar-row';
        metaBarRow.appendChild(_createMetaBox('Size', stats.size));
        metaBarRow.appendChild(_createMetaBox('Sheets', stats.sheetCount));
        metaBarRow.appendChild(_createMetaBox('Tables', stats.tableCount));
        metaBarRow.appendChild(_createMetaBox('Columns', stats.columnCount));
        metaBarRow.appendChild(_createMetaBox('Total Rows', stats.totalRows));
        metaBar.appendChild(metaBarRow);

        gridWrapper.appendChild(pathBar);
        gridWrapper.appendChild(treeWrapper);
        gridWrapper.appendChild(spreadsheetWrapper);
        gridWrapper.appendChild(metaBar);

        return treeContainerId;

    } else {
        newContentPane.innerHTML = '<p>Error: Content template not found.</p>';
        return contentId;
    }
}

//-------------------------------------------------------------
//-------------[   CROSS-MODULE HELPERS (Private)   ]----------
//-------------------------------------------------------------

function extractColumnsFromStructure(fileStructure) {
    const columns = [];
    if (!fileStructure || !fileStructure.sheets) return columns;

    for (const sheet of fileStructure.sheets) {
        for (const table of sheet.tables) {
            for (const col of table.columns) {
                if (!columns.includes(col)) {
                    columns.push(col);
                }
            }
        }
    }
    return columns;
}

function exposeAvailableColumns(columns) {
    if (!window.DocuFlowState) {
        window.DocuFlowState = {};
    }
    window.DocuFlowState.availableColumns = columns;
    console.log(`[DataPanel] Exposed ${columns.length} columns for auto-match.`);
}