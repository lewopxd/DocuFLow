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
 * - Displaying the data structure in a tree.
 * - Managing its own tabs and state.
 * * NOTE: This module's logic runs *inside* the .module-content container
 * * created by main.js.
 */

//-------------------------------------------------------------
//-------------[   MODULE IMPORTS   ]--------------------------
//-------------------------------------------------------------

// Import global services and icons
import { AppService } from '../../js/services.js';
import { 
    ICON_CLOSE, 
    ICON_PLUS, 
    ICON_FILE_SHEET, 
    ICON_WINDOW_DATA,
    ICON_CHEVRON_UP,
    ICON_CHEVRON_DOWN 
} from '../../js/icons.js';

//-------------------------------------------------------------
//-------------[   MODULE STATE   ]----------------------------
//-------------------------------------------------------------

/**
 * @type {Array<string>}
 * In-memory list of file paths for this panel.
 */
let currentSheetPaths = [];

/**
 * @type {object | null}
 * A reference to the Paneton.Tree library from the global scope.
 */
const PanetonTree = window.Paneton ? window.Paneton.Tree : null;

// DOM element references, set by initialize()
let panelId = 'data-panel'; // ID for this module's logic
let tabsContainer = null;
let contentContainer = null;
let placeholder = null;

//-------------------------------------------------------------
//-------------[   MODULE INITIALIZATION   ]-------------------
//-------------------------------------------------------------

/**
 * [Initializes the Data Panel module.]
 * This function is called by main.js after the module's HTML is loaded.
 * @param {HTMLElement} panelElement - The container element (this is .module-content).
 * @exports
 */
export async function initialize(panelElement) {
    if (!panelElement) return;

    // 1. Set module-level DOM references
    // Find elements *within* the passed .module-content
    tabsContainer = panelElement.querySelector('.toolbar-tabs');
    contentContainer = panelElement.querySelector('.panel-content');
    placeholder = panelElement.querySelector('.placeholder');

    if (!tabsContainer || !contentContainer || !placeholder) {
        console.error('[DataPanel] Module HTML structure is missing required elements.');
        return;
    }

    // 2. Inject static icons
    
    // Inject Tab "Add" Icon
    const loadSheetButton = panelElement.querySelector('#load-sheet-button');
    if (loadSheetButton) {
        loadSheetButton.innerHTML = ICON_PLUS;
        // 3. Attach workflow listeners
        loadSheetButton.addEventListener('click', handleLoadSheetWorkflow);
    }
    
    // 4. Initialize tab click handling
    setupTabClickHandling();
    
    // 5. Load settings and restore previous session tabs
    await loadAndRestoreSession_Data();
    
    console.log('[DataPanel] Module initialized.');
}

//--------------------------------------> END [ MODULE INITIALIZATION ... ]

//-------------------------------------------------------------
//-------------[   MODULE WORKFLOWS (Private)   ]--------------
//-------------------------------------------------------------

/**
 * [Full workflow for loading a Data Sheet.]
 * @returns {Promise<void>}
 */
async function handleLoadSheetWorkflow() {
    try {
        const fileTypes = [
            'Spreadsheets (*.xlsx;*.xls;*.csv)',
            'All Files (*.*)'
        ];
        
        // 1. Get file path (using global AppService)
        const response = await AppService.requestFileDialog({
            fileTypes: fileTypes
        });
        
        if (!response || !response.filePath) {
            console.log('[DataPanel] User cancelled selection.');
            return;
        }

        const filePath = response.filePath;
        const fileName = filePath.split(/[\\/]/).pop();
        
        // 2. Get file structure (using global AppService)
        const fileStructure = await AppService.getExcelFileStructure(filePath);

        if (fileStructure) {
            console.log(`[DataPanel] Structure loaded for: ${fileName}`);
            console.log(JSON.stringify(fileStructure, null, 2));
            
            // 3. Transform structure to Paneton format
            const panetonData = excelStructureToPanetonData(fileStructure);

            // 4. Create the tab and get the tree wrapper ID
            const treeWrapperId = addTab(
                fileName, 
                { filePath: filePath }, 
                ICON_FILE_SHEET,
                fileStructure
            );
            
            // 5. Inject Paneton Tree into the new wrapper
            if (treeWrapperId) {
                initializePanetonTree(treeWrapperId, panetonData);
            }

            // 6. Persist state
            await updateSheetPathsAndSave(filePath);

        } else {
             console.error(`[DataPanel] Could not retrieve structure for ${fileName}.`);
        }
        
    } catch (error) {
        console.error('[DataPanel] Error during Load Sheet Workflow:', error);
    }
}

/**
 * [Loads persistent settings and restores session for this module.]
 * @returns {Promise<void>}
 */
async function loadAndRestoreSession_Data() {
    try {
        const settings = await AppService.loadSettings();

        if (settings.last_opened_sheet && Array.isArray(settings.last_opened_sheet)) {
            currentSheetPaths = settings.last_opened_sheet;
            for (const path of currentSheetPaths) {
                const fileName = path.split(/[\\/]/).pop();
                
                // Get structure to restore the tree
                const fileStructure = await AppService.getExcelFileStructure(path);
                
                if (fileStructure) {
                    const panetonData = excelStructureToPanetonData(fileStructure);
                    
                    const treeWrapperId = addTab(
                        fileName, 
                        { filePath: path }, 
                        ICON_FILE_SHEET,
                        fileStructure
                    );
                    
                    if (treeWrapperId) {
                        initializePanetonTree(treeWrapperId, panetonData);
                    }
                } else {
                     console.warn(`[DataPanel] Skipping restoration of ${fileName}: Structure not found.`);
                }
            }
        }
    } catch (error) {
        console.error('[DataPanel] Could not load persistent settings:', error);
    }
}

//--------------------------------------> END [ MODULE WORKFLOWS ... ]

//-------------------------------------------------------------
//-------------[   MODULE STATE & MUTATORS (Private)   ]-------
//-------------------------------------------------------------

/**
 * [Updates the in-memory sheet path list and persists it.]
 * @param {string} filePath - The path to add.
 * @returns {Promise<void>}
 */
async function updateSheetPathsAndSave(filePath) {
    if (!currentSheetPaths.includes(filePath)) {
        currentSheetPaths.push(filePath);
        await AppService.saveUiSetting('last_opened_sheet', currentSheetPaths)
            .catch(err => console.error('[DataPanel] Failed to save sheet list:', err));
    }
}

/**
 * [Business logic for closing a tab.]
 * @param {HTMLElement} tabElement - The tab element (.tab) to be closed.
 * @returns {object} status - Data needed by the UI helper to remove the tab.
 */
function handleCloseTabWorkflow(tabElement) {
    const filePath = tabElement.dataset.filePath;
    const settingKey = 'last_opened_sheet';

    // 1. Remove from in-memory state
    currentSheetPaths = currentSheetPaths.filter(p => p !== filePath);
    
    // 2. Save the updated state (asynchronously)
    AppService.saveUiSetting(settingKey, currentSheetPaths)
        .catch(err => console.error(`[DataPanel] Failed to save state after closing tab: ${err}`));

    // 3. Return data needed for DOM manipulation
    return { 
        success: true, 
        tabElement: tabElement,
        remainingTabsCount: tabsContainer.querySelectorAll('.tab:not(#load-sheet-button)').length - 1,
        wasActive: tabElement.classList.contains('active'),
        targetPaneSelector: tabElement.dataset.tabTarget
    };
}
//--------------------------------------> END [ MODULE STATE & MUTATORS ... ]

//-------------------------------------------------------------
//-------------[   UI DOM HELPERS (Private)   ]----------------
//-------------------------------------------------------------

/**
 * [Removes the tab and content pane from the DOM.]
 * @param {HTMLElement} tabElement - The tab element to be removed.
 * @param {string} targetPaneSelector - The selector of the content pane to be removed.
 * @param {number} remainingTabsCount - Tabs remaining *after* this one is removed.
 * @param {boolean} wasActive - True if the tab being removed was the active one.
 */
function removeTabAndRestoreState(tabElement, targetPaneSelector, remainingTabsCount, wasActive) {
    
    // 1. Remove content and tab
    const contentPane = contentContainer.querySelector(targetPaneSelector);
    if (contentPane) contentPane.remove();
    tabElement.remove();

    if (remainingTabsCount === 0) {
        // Show placeholder if no tabs left
        if (placeholder) {
            placeholder.style.display = 'block';
        }
    } else if (wasActive) {
        // Activate the last tab if the active one was closed
        const remainingTabs = tabsContainer.querySelectorAll('.tab:not(#load-sheet-button)');
        const lastTab = remainingTabs[remainingTabs.length - 1];
        lastTab.classList.add('active');
        
        const targetPane = contentContainer.querySelector(lastTab.dataset.tabTarget);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    }
}

/**
 * [Sets up delegated click handling for tab activation and closing.]
 */
function setupTabClickHandling() {
    tabsContainer.addEventListener('click', (e) => {
        const clickedTab = e.target.closest('.tab');
        
        // Click was outside a tab, or on the "add" button
        if (!clickedTab || clickedTab.id === 'load-sheet-button') {
            return;
        }

        const clickedClose = e.target.closest('.tab-close');

        // 1. Handle Tab Close
        if (clickedClose) {
             const result = handleCloseTabWorkflow(clickedTab);
             if (result.success) {
                // Manipulate the DOM
                removeTabAndRestoreState(
                    result.tabElement,
                    result.targetPaneSelector,
                    result.remainingTabsCount,
                    result.wasActive
                );
             }
             return;
        }
        
        // 2. Handle Tab Activation
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        clickedTab.classList.add('active');
        const targetPane = contentContainer.querySelector(clickedTab.dataset.tabTarget);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    });
}

//--------------------------------------> END [ UI DOM HELPERS ... ]


//-------------------------------------------------------------
//-------------[   DYNAMIC DOM BUILDERS (Private)   ]----------
//-------------------------------------------------------------

/**
 * [Calculates aggregate statistics from the fileStructure object.]
 * @param {object} fileStructure - The file structure object.
 * @returns {object} - An object with the calculated statistics.
 * @private
 */
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
        tableCount: tableCount,
        columnCount: columnCount,
        totalRows: totalRows
    };
}

/**
 * [Creates an individual metadata container.]
 * @param {string} label - The label text (e.g., "Size").
 * @param {string|number} value - The metadata value (e.g., "215 KB").
 * @param {string} position - 'top' or 'bottom' to apply the correct class.
 * @returns {HTMLElement} - The .meta-stat-box DOM element.
 * @private
 */
function _createMetaBox(label, value, position = 'top') {
    const box = document.createElement('div');
    box.className = `meta-stat-box meta-stat-box--${position}`;
    
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

/**
 * [Converts Excel structure object into the Paneton.Tree data format.]
 * @param {object} excelStructure - The data object from AppService.
 * @returns {Array<object>} - An array containing the root node for Paneton.Tree.
 */
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

    sheets.map(sheet => {
        const sheetNode = {
            name: sheet.sheetName,
            path: `${metadata.fileName}/${sheet.sheetName}`,
            type: 'sheet',
            expanded: true,
            children: []
        };

        sheet.tables.map(table => {
            const displayTableName = table.isNamedTable ? table.tableName : `UNAMED_TABLE (Full Sheet)`;
            const tableNode = {
                name: displayTableName,
                path: `${metadata.fileName}/${sheet.sheetName}/${table.tableName}`,
                type: 'table',
                expanded: false,
                children: []
            };

            table.columns.map(columnName => {
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
                                : Paneton.Tree.DEFAULT_BUTTON_ICON, // Fallback
                            
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

/**
 * [Initializes the Paneton.Tree component inside the given container.]
 * @param {string} containerId - The ID of the div where the tree should be placed.
 * @param {Array<object>} treeData - The data structure in Paneton format.
 */
function initializePanetonTree(containerId, treeData) {
    const treeContainer = document.getElementById(containerId);
    if (!treeContainer) {
        console.error(`[DataPanel] Paneton Tree: Target container #${containerId} not found.`);
        return;
    }
    treeContainer.classList.add('paneton-tree-container');
    
    if (PanetonTree) { 
        new PanetonTree(treeContainer, {
            data: treeData,
            sortNodes: false,
            compactFolders: false,
            autoHideButtons: 'activeNode'
        });
    } else {
        console.error("[DataPanel] Paneton.Tree library not found in global scope.");
    }
}


/**
 * [Dynamically creates and adds a new tab and its content pane.]
 * @param {string} tabName - The text for the tab label.
 * @param {object} data - Optional data to store in the tab (e.g., { filePath: '...' }).
 * @param {string} fileIconSvg - The SVG string for the file type icon.
 * @param {object|null} fileStructure - The file structure object to populate metadata.
 * @returns {string} The ID of the new content pane (or the tree-wrapper).
 */
function addTab(tabName, data = {}, fileIconSvg = '', fileStructure = null) {
    
    if (placeholder && placeholder.style.display !== 'none') {
        placeholder.style.display = 'none';
    }

    // Deactivate existing tabs
    tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // --- Create New Tab ---
    const newTab = document.createElement('div');
    newTab.className = 'tab active';

    const parts = tabName.match(/^(.*?)(\.[^.]*)?$/) || [null, tabName, ''];
    const name = parts[1];

    // --- MODIFIED: Corrected the typo (class" -> class=") ---
    newTab.innerHTML = `
        <div class="tab-icon">${fileIconSvg}</div>
        <div class="tab-name-wrapper">
            <span class="tab-label">${name}</span>
            <span class="tab-ext">${parts[2] || ''}</span>
        </div>
        <div class="tab-close">${ICON_CLOSE}</div>
    `;
    // --- END MODIFICATION ---
    
    // --- Create New Content Pane ---
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
    
    // Insert tab before the action button
    const actionButton = tabsContainer.querySelector('#load-sheet-button');
    tabsContainer.insertBefore(newTab, actionButton);
    contentContainer.appendChild(newContentPane);

    // --- Build Internal Grid (if fileStructure is provided) ---
    if (fileStructure) {
        const gridWrapper = document.createElement('div');
        gridWrapper.className = 'tab-content-grid';
        newContentPane.appendChild(gridWrapper);

        const stats = _calculateFileStats(fileStructure);
        const fullPath = fileStructure.metadata.fullPath || data.filePath || '';
        const fileName = fileStructure.metadata.fileName || tabName;
        const directoryPath = fullPath.replace(fileName, '');

        // 1. Path Bar
        const pathBar = document.createElement('div');
        pathBar.className = 'status-bar__path'; 
        
        const pathInput = document.createElement('input');
        pathInput.type = 'text';
        pathInput.className = 'status-bar__path-input';
        pathInput.value = `${directoryPath}${fileName}`;
        pathInput.readOnly = true; 
        pathBar.appendChild(pathInput);

        // 2. Tree Wrapper
        const treeWrapper = document.createElement('div');
        treeWrapper.className = 'tree-wrapper';
        const treeWrapperId = `tree-wrapper-${Date.now()}`;
        treeWrapper.id = treeWrapperId;
        
        // 3. Meta Bar
        const metaBar = document.createElement('div');
        metaBar.className = 'meta-bar'; 
        const metaBarRow = document.createElement('div');
        metaBarRow.className = 'meta-bar-row';
        
        metaBarRow.appendChild(_createMetaBox('Size', stats.size, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Sheets', stats.sheetCount, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Tables', stats.tableCount, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Columns', stats.columnCount, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Total Rows', stats.totalRows, 'bottom'));

        metaBar.appendChild(metaBarRow);
        
        gridWrapper.appendChild(pathBar);
        gridWrapper.appendChild(treeWrapper);
        gridWrapper.appendChild(metaBar);
        
        return treeWrapperId; // Return ID for Paneton to target

    } else {
        // Fallback for content (should not happen in this module)
        newContentPane.innerHTML = '<p>Error: Content template not found.</p>';
        return contentId;
    }
}
//--------------------------------------> END [ DYNAMIC DOM BUILDERS ... ]