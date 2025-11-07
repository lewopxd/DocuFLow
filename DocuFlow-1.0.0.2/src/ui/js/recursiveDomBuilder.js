// js/recursiveDomBuilder.js
/**
 * Project: DocuFlow
 * File:  recursiveDomBuilder.js
 * Created: 2025-10-30
 * Author: @lewopxd 
 *
 * Description:
 * Utility module for building and manipulating the UI's DOM structure.
 * Contains functions for creating dynamic elements (tabs, tree nodes, etc.).
 */

// Import SVG icons
import { ICON_CLOSE } from './icons.js';

// --- Global: Paneton.Tree is loaded from index.html via script tag ---
const PanetonTree = window.Paneton ? window.Paneton.Tree : null;

//-------------------------------------------------------------
//-------------[   DATA ADAPTERS   ]---------------------------
//-------------------------------------------------------------

/**
 * [Converts the Excel/Pandas structure object into the Paneton.Tree data format.]
 *
 * @param {object} excelStructure - The data object from the AppService.getExcelFileStructure.
 * @returns {Array<object>} - An array containing the root node for Paneton.Tree.
 * @exports
 */
export function excelStructureToPanetonData(excelStructure) {
    if (!excelStructure || !excelStructure.sheets) {
        return [];
    }

    const { metadata, sheets } = excelStructure;
    
    // 1. Create the Root (File) node
    const fileNode = {
        name: metadata.fileName,
        path: metadata.fileName,
        type: 'file', // Metadata for icon control
        expanded: true, // Expand by default
        children: []
    };

    // 2. Iterate over the Sheets
    // We use map to ensure sheets maintain the JSON order (from Excel)
    sheets.map(sheet => {
        const sheetNode = {
            name: sheet.sheetName,
            path: `${metadata.fileName}/${sheet.sheetName}`,
            type: 'sheet', // Metadata for icon control
            expanded: true,
            children: []
        };

        // 3. Iterate over the Tables within the Sheet
        // We use map to ensure tables maintain the JSON order (from Excel)
        sheet.tables.map(table => {
            
            // Assign a readable name to the table
            const displayTableName = table.isNamedTable 
                ? table.tableName 
                : `UNAMED_TABLE (Full Sheet)`;

            const tableNode = {
                name: displayTableName,
                path: `${metadata.fileName}/${sheet.sheetName}/${table.tableName}`,
                type: 'table', // Metadata for icon control
                expanded: false, // Tables are collapsed by default
                buttons: [ 
                    // Simulate a button that shows metadata
                    { tooltip: `Rows: ${table.rowCount}` }
                ],
                children: []
            };

            // 4. Iterate over the Columns (the lowest nodes)
            // We use map to ensure columns maintain the Excel order
            table.columns.map(columnName => {
                const columnNode = {
                    name: columnName,
                    path: `${tableNode.path}/${columnName}`,
                    type: 'column', // Metadata for icon control
                    isLeaf: true,
                    // No children, it's the final node
                };
                tableNode.children.push(columnNode);
            });

            sheetNode.children.push(tableNode);
        });

        // Only add the sheet if it has tables (avoid empty sheets in the tree)
        if (sheetNode.children.length > 0) {
            fileNode.children.push(sheetNode);
        }
    });

    return [fileNode];
}

//--------------------------------------> END [ DATA ADAPTERS ... ]

//-------------------------------------------------------------
//-------------[   DYNAMIC DOM INJECTION   ]-------------------
//-------------------------------------------------------------

/**
 * [Initializes the Paneton.Tree component inside the given container.]
 * @param {string} containerId - The ID of the div where the tree should be placed.
 * @param {Array<object>} treeData - The data structure in Paneton format.
 * @exports
 */
export function initializePanetonTree(containerId, treeData) {
    // Point directly to the tree container (the Row 2 wrapper)
    const treeContainer = document.getElementById(containerId);

    if (!treeContainer) {
        console.error(`Paneton Tree: Target container #${containerId} not found.`);
        return;
    }

    // 1. Add the style class
    treeContainer.classList.add('paneton-tree-container');
    
    // 2. Initialize Paneton.Tree
    if (PanetonTree) { 
        const treeInstance = new PanetonTree(treeContainer, {
            data: treeData,
            // Paneton.Tree configuration options:
            sortNodes: false,
            compactFolders: false,
            autoHideButtons: 'activeNode'
        });
        
        console.log(`Paneton Tree initialized in #${containerId}`);
        return treeInstance;
    } else {
        console.error("Paneton.Tree library not found in global scope.");
    }
}


/**
 * [Dynamically creates and adds a new tab and its content pane.]
 * @param {string} panelId - The ID of the panel (e.g., 'left-panel').
 * @param {string} tabName - The text for the tab label (full filename).
 * @param {object} data - Optional data to store in the tab (e.g., { filePath: '...' }).
 * @param {string} fileIconSvg - The SVG string for the file type icon.
 * @param {object|null} fileStructure - [NEW] The file structure object to populate metadata.
 * @returns {string} The ID of the new content pane (or the tree-wrapper if it's the left panel).
 * @exports
 */
export function addTab(panelId, tabName, data = {}, fileIconSvg = '', fileStructure = null) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const tabsContainer = panel.querySelector('.toolbar-tabs');
    const contentContainer = panel.querySelector('.panel-content');
    
    const placeholder = panel.querySelector('.placeholder');
    
    if (placeholder && placeholder.style.display !== 'none') {
        placeholder.style.display = 'none';
    }

    // Deactivate existing tabs
    tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // --- NEW TAB STRUCTURE ---
    const newTab = document.createElement('div');
    newTab.className = 'tab active';

    const parts = tabName.match(/^(.*?)(\.[^.]*)?$/) || [null, tabName, ''];
    const name = parts[1];

    const tabIcon = document.createElement('div');
    tabIcon.className = 'tab-icon';
    tabIcon.innerHTML = fileIconSvg;
    
    const tabNameWrapper = document.createElement('div');
    tabNameWrapper.className = 'tab-name-wrapper';
    
    const tabLabel = document.createElement('span');
    tabLabel.className = 'tab-label';
    tabLabel.textContent = name;
    
    const tabExt = document.createElement('span');
    tabExt.className = 'tab-ext';
    tabExt.textContent = parts[2] || '';

    tabNameWrapper.appendChild(tabLabel);
    tabNameWrapper.appendChild(tabExt);
    
    const tabClose = document.createElement('div');
    tabClose.className = 'tab-close';
    tabClose.innerHTML = ICON_CLOSE;
    
    newTab.appendChild(tabIcon);
    newTab.appendChild(tabNameWrapper);
    newTab.appendChild(tabClose);
    // --- END NEW TAB STRUCTURE ---

    // --- NEW CONTENT PANE STRUCTURE ---
    const newContentPane = document.createElement('div');
    newContentPane.className = 'tab-content active'; // <-- This one has margin: 20px
    const contentId = `${panelId}-content-${Date.now()}`;
    newContentPane.id = contentId;
    
    // Link tab and content
    newTab.dataset.tabTarget = `#${contentId}`;

    if (data.filePath) {
        newTab.dataset.filePath = data.filePath;
        newTab.title = data.filePath;
    }
    
    // [MODIFIED] Insert tab before the action button
    const actionButtonId = (panelId === 'left-panel') 
        ? 'load-sheet-button' 
        : 'load-template-button';
    const actionButton = document.getElementById(actionButtonId);
    
    // insertBefore handles actionButton being null gracefully (acts as appendChild)
    tabsContainer.insertBefore(newTab, actionButton);
    contentContainer.appendChild(newContentPane);

    // --- CONDITIONAL LAYOUT LOGIC ---
    
    // If it's the left panel and we have data, build the grid.
    if (panelId === 'left-panel' && fileStructure) {
        
        // [NEW] Create the grid wrapper that goes INSIDE .tab-content
        const gridWrapper = document.createElement('div');
        gridWrapper.className = 'tab-content-grid'; // New class for the grid
        newContentPane.appendChild(gridWrapper); // Add it to .tab-content

        // 1. Calculate metadata
        const stats = _calculateFileStats(fileStructure);
        
        const fullPath = fileStructure.metadata.fullPath || data.filePath || '';
        const fileName = fileStructure.metadata.fileName || tabName;
        const directoryPath = fullPath.replace(fileName, '');

        // 2. Build the Grid DOM
        
        // Row 1: Path Bar
        const pathBar = document.createElement('div');
        pathBar.className = 'status-bar__path'; 
        // [MODIFIED] Added fileName to the span
        pathBar.innerHTML = `<span>${directoryPath}${fileName}</span>`;
        
        // Row 2: Tree Wrapper
        const treeWrapper = document.createElement('div');
        treeWrapper.className = 'tree-wrapper';
        const treeWrapperId = `tree-wrapper-${Date.now()}`;
        treeWrapper.id = treeWrapperId;
        
        // Row 3: Meta Bar with 1 row
        const metaBar = document.createElement('div');
        metaBar.className = 'meta-bar'; 

        // [MODIFIED] Create Single Row (removed metaBarRowTop)
        const metaBarRow = document.createElement('div');
        metaBarRow.className = 'meta-bar-row'; // New class for the single row

        // [MODIFIED] Add 'Size' and remove 'Format'. Use 'bottom' for box style.
        metaBarRow.appendChild(_createMetaBox('Size', stats.size, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Sheets', stats.sheetCount, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Tables', stats.tableCount, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Columns', stats.columnCount, 'bottom'));
        metaBarRow.appendChild(_createMetaBox('Total Rows', stats.totalRows, 'bottom'));

        // Add the single row to the metaBar
        metaBar.appendChild(metaBarRow);
        
        // [MODIFIED] Add rows to gridWrapper, NOT to newContentPane
        gridWrapper.appendChild(pathBar);
        gridWrapper.appendChild(treeWrapper);
        gridWrapper.appendChild(metaBar);
        
        // Return the wrapper ID so Paneton can inject there
        return treeWrapperId;

    } else {
        // Fallback for right panel or if no data
        const placeholderFrameTemplate = panel.querySelector('.placeholder-frame');
        if (placeholderFrameTemplate) {
            const newFrame = placeholderFrameTemplate.cloneNode(true);
            newContentPane.appendChild(newFrame);
        } else {
            newContentPane.innerHTML = '<p>Error: Content template not found.</p>';
        }
        return contentId;
    }
}

//--------------------------------------> END [ DYNAMIC DOM INJECTION ... ]

//-------------------------------------------------------------
//-------------[   PRIVATE HELPERS   ]-------------------------
//-------------------------------------------------------------

/**
 * [Calculates aggregate statistics from the fileStructure object.]
 * @param {object} fileStructure - The file structure object.
 * @returns {object} - An object with the calculated statistics.
 * @private
 */
function _calculateFileStats(fileStructure) {
    const { metadata, sheets } = fileStructure;
    
    let tableCount = 0;
    let columnCount = 0;
    let totalRows = 0;
    
    sheets.forEach(sheet => {
        tableCount += sheet.tables.length;
        sheet.tables.forEach(table => {
            columnCount += table.columns.length;
            totalRows += table.rowCount;
        });
    });

    // Extract extension for format
    const format = metadata.fileName.split('.').pop().toUpperCase();
    
    return {
        format: format,
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
    // Base class + position-specific class
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

//--------------------------------------> END [ PRIVATE HELPERS ... ]