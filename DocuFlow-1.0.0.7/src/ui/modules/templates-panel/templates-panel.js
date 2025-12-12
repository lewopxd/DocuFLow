// modules/output-panel/output-panel.js
/**
 * Project: DocuFlow
 * File:  modules/output-panel/output-panel.js
 * Created: 2025-11-04
 * Author: @lewopxd
 *
 * Description:
 * The main controller and logic for the Output Panel Module.
 * This module is responsible for:
 * - Loading Word (.docx) templates.
 * - Displaying variables (Future).
 * - Managing its own tabs and state.
 */

//-------------------------------------------------------------
//-------------[   MODULE IMPORTS   ]--------------------------
//-------------------------------------------------------------

// Import global services and icons
import { AppService } from '../../js/services.js';
import { ICON_CLOSE, ICON_PLUS, ICON_FILE_TEMPLATE, ICON_RELOAD } from '../../js/icons.js';

//-------------------------------------------------------------
//-------------[   MODULE STATE   ]----------------------------
//-------------------------------------------------------------

/**
 * @type {Array<string>}
 * In-memory list of file paths for this panel.
 * (Logic moved from interactions.js)
 */
let currentTemplatePaths = [];

// DOM element references, set by initialize()
let panelId = 'output-panel'; // ID for this module's logic
let tabsContainer = null;
let contentContainer = null;
let placeholder = null;

//-------------------------------------------------------------
//-------------[   GLOBAL STATE: Locked Mappings   ]-----------
//-------------------------------------------------------------

/**
 * Global state for locked column mappings.
 * Structure: { "template_path": { "placeholder_raw": "column_value" } }
 * Locked mappings are preserved during document reload.
 */
window.DocuFlowLockedMappings = window.DocuFlowLockedMappings || {};

// Lock icon SVG
const ICON_LOCK = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>`;
const ICON_UNLOCK = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>`;

//-------------------------------------------------------------
//-------------[   MODULE INITIALIZATION   ]-------------------
//-------------------------------------------------------------

/**
 * [Initializes the Output Panel module.]
 * This function is called by main.js after the module's HTML is loaded.
 * @param {HTMLElement} panelElement - The container element (e.g., #right-top-panel).
 * @exports
 */
export async function initialize(panelElement) {
    if (!panelElement) return;

    // 1. Set module-level DOM references
    tabsContainer = panelElement.querySelector('.toolbar-tabs');
    contentContainer = panelElement.querySelector('.panel-content');
    placeholder = panelElement.querySelector('.placeholder');

    if (!tabsContainer || !contentContainer || !placeholder) {
        console.error('[OutputPanel] Module HTML structure is missing required elements.');
        return;
    }

    // 2. Inject static icons
    const loadTemplateButton = panelElement.querySelector('#load-template-button');
    if (loadTemplateButton) {
        loadTemplateButton.innerHTML = ICON_PLUS;
        // 3. Attach workflow listeners
        loadTemplateButton.addEventListener('click', handleLoadTemplateWorkflow);
    }

    // 4. Initialize tab click handling
    setupTabClickHandling();

    // 5. Listen for Excel columns loaded (for auto-match when Excel loads after template)
    window.addEventListener('docuflow:columns-loaded', handleColumnsLoaded);

    // 6. Load settings and restore previous session tabs
    await loadAndRestoreSession_Output();

    console.log('[OutputPanel] Module initialized.');
}

//--------------------------------------> END [ MODULE INITIALIZATION ... ]

//-------------------------------------------------------------
//-------------[   MODULE WORKFLOWS (Private)   ]--------------
//-------------------------------------------------------------

/**
 * [Full workflow for loading a Document Template.]
 * (Logic moved from interactions.js)
 * @returns {Promise<void>}
 */
async function handleLoadTemplateWorkflow() {
    try {
        const fileTypes = [
            'Word Documents (*.docx;*.doc)',
            'All Files (*.*)'
        ];

        // 1. Get file path
        const response = await AppService.requestFileDialog({
            fileTypes: fileTypes
        });

        if (!response || !response.filePath) {
            console.log('[OutputPanel] User cancelled selection.');
            return;
        }

        const filePath = response.filePath;
        const fileName = filePath.split(/[\\/]/).pop();

        // 2. Add the tab (no complex structure needed)
        // null is passed for fileStructure
        addTab(fileName, { filePath: filePath }, ICON_FILE_TEMPLATE, null);

        // 3. Persist state
        await updateTemplatePathsAndSave(filePath);

    } catch (error) {
        console.error('[OutputPanel] Error during Load Template Workflow:', error);
    }
}


/**
 * [Loads persistent settings and restores session for this module.]
 * (Logic moved from interactions.js)
 * @returns {Promise<void>}
 */
async function loadAndRestoreSession_Output() {
    try {
        const settings = await AppService.loadSettings();

        if (settings.last_opened_template && Array.isArray(settings.last_opened_template)) {
            currentTemplatePaths = settings.last_opened_template;
            for (const path of currentTemplatePaths) {
                const fileName = path.split(/[\\/]/).pop();
                // Just add the tab, no structure to parse
                addTab(fileName, { filePath: path }, ICON_FILE_TEMPLATE, null);
            }
        }
    } catch (error) {
        console.error('[OutputPanel] Could not load persistent settings:', error);
    }
}
//--------------------------------------> END [ MODULE WORKFLOWS ... ]

//-------------------------------------------------------------
//-------------[   MODULE STATE & MUTATORS (Private)   ]-------
//-------------------------------------------------------------

/**
 * [Updates the in-memory template path list and persists it.]
 * (Logic moved from interactions.js)
 * @param {string} filePath - The path to add.
 * @returns {Promise<void>}
 */
async function updateTemplatePathsAndSave(filePath) {
    if (!currentTemplatePaths.includes(filePath)) {
        currentTemplatePaths.push(filePath);
        await AppService.saveUiSetting('last_opened_template', currentTemplatePaths)
            .catch(err => console.error('[OutputPanel] Failed to save template list:', err));
    }
}

/**
 * [Business logic for closing a tab.]
 * (Logic moved from interactions.js)
 * @param {HTMLElement} tabElement - The tab element (.tab) to be closed.
 * @returns {object} status - Data needed by the UI helper to remove the tab.
 */
function handleCloseTabWorkflow(tabElement) {
    const filePath = tabElement.dataset.filePath;
    const settingKey = 'last_opened_template';

    // 1. Remove from in-memory state
    currentTemplatePaths = currentTemplatePaths.filter(p => p !== filePath);

    // 2. Save the updated state (asynchronously)
    AppService.saveUiSetting(settingKey, currentTemplatePaths)
        .catch(err => console.error(`[OutputPanel] Failed to save state after closing tab: ${err}`));

    // 3. Return data needed for DOM manipulation
    return {
        success: true,
        tabElement: tabElement,
        remainingTabsCount: tabsContainer.querySelectorAll('.tab:not(#load-template-button)').length - 1,
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
 * (Logic moved from uiHelpers.js)
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
        const remainingTabs = tabsContainer.querySelectorAll('.tab:not(#load-template-button)');
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
 * (Logic moved from uiHelpers.js)
 */
function setupTabClickHandling() {
    tabsContainer.addEventListener('click', (e) => {
        const clickedTab = e.target.closest('.tab');

        // Click was outside a tab, or on the "add" button
        if (!clickedTab || clickedTab.id === 'load-template-button') {
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
 * [Dynamically creates and adds a new tab and its content pane.]
 * (Logic moved from recursiveDomBuilder.js)
 * @param {string} tabName - The text for the tab label.
 * @param {object} data - Optional data to store in the tab (e.g., { filePath: '...' }).
 * @param {string} fileIconSvg - The SVG string for the file type icon.
 * @param {object|null} fileStructure - (Ignored in this module, but part of the signature).
 * @returns {string} The ID of the new content pane.
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

    newTab.innerHTML = `
        <div class="tab-icon">${fileIconSvg}</div>
        <div class="tab-name-wrapper">
            <span class="tab-label">${name}</span>
            <span class="tab-ext">${parts[2] || ''}</span>
        </div>
        <div class="tab-close">${ICON_CLOSE}</div>
    `;

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
    const actionButton = tabsContainer.querySelector('#load-template-button');
    tabsContainer.insertBefore(newTab, actionButton);
    contentContainer.appendChild(newContentPane);

    // --- Build Internal Content with Path Bar ---
    const gridWrapper = document.createElement('div');
    gridWrapper.className = 'tab-content-grid';
    newContentPane.appendChild(gridWrapper);

    // 1. Path Bar (same as data-panel)
    const pathBar = document.createElement('div');
    pathBar.className = 'status-bar__path';

    const pathInput = document.createElement('input');
    pathInput.type = 'text';
    pathInput.className = 'status-bar__path-input';
    pathInput.value = data.filePath || '';
    pathInput.readOnly = true;
    pathBar.appendChild(pathInput);

    // 1.5 Controls (Reload button)
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'status-bar__controls';

    const reloadBtn = document.createElement('button');
    reloadBtn.className = 'icon-button';
    reloadBtn.title = 'Reload Template';
    reloadBtn.innerHTML = ICON_RELOAD;
    reloadBtn.dataset.action = 'reload';
    reloadBtn.addEventListener('click', () => loadTemplatePlaceholders(data.filePath, mappingGrid, metaBar));

    controlsDiv.appendChild(reloadBtn);
    pathBar.appendChild(controlsDiv);

    gridWrapper.appendChild(pathBar);

    // 2. Mapping Grid Container
    const mappingGrid = document.createElement('div');
    mappingGrid.className = 'mapping-grid';
    mappingGrid.dataset.filePath = data.filePath; // Store for refresh lookup
    mappingGrid.innerHTML = '<div class="loading-spinner-container"><div class="loading-spinner"></div></div>';
    gridWrapper.appendChild(mappingGrid);

    // 3. Meta Footer Bar (similar to data-panel)
    const metaBar = document.createElement('div');
    metaBar.className = 'template-meta-bar';
    metaBar.innerHTML = '<span class="meta-item">Cargando información...</span>';
    gridWrapper.appendChild(metaBar);

    // 4. Load placeholders from backend
    loadTemplatePlaceholders(data.filePath, mappingGrid, metaBar);

    return contentId;
}

//--------------------------------------> END [ DYNAMIC DOM BUILDERS ... ]


//-------------------------------------------------------------
//-------------[   MAPPING SYSTEM   ]--------------------------
//-------------------------------------------------------------

/**
 * Handles the event when Excel columns are loaded.
 * Re-runs auto-match on all open template tabs.
 */
function handleColumnsLoaded(event) {
    console.log('[OutputPanel] Excel columns loaded, refreshing auto-match...');
    refreshAllMappingCards();
}

/**
 * Refreshes mapping cards for all open template tabs.
 * Called when Excel data loads to update auto-match.
 */
function refreshAllMappingCards() {
    // Get all mapping grids (each has data-file-path)
    const mappingGrids = contentContainer.querySelectorAll('.mapping-grid[data-file-path]');

    console.log(`[OutputPanel] Found ${mappingGrids.length} template tabs to refresh`);

    for (const grid of mappingGrids) {
        const filePath = grid.dataset.filePath;
        if (!filePath) continue;

        // Find the meta bar (sibling element)
        const metaBar = grid.parentElement?.querySelector('.template-meta-bar');

        // Reload placeholders (which will re-run auto-match)
        console.log(`[OutputPanel] Refreshing match for: ${filePath}`);
        loadTemplatePlaceholders(filePath, grid, metaBar);
    }
}

// Arrow SVG for mapping visualization
const ICON_ARROW_RIGHT = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>`;

/**
 * Normalizes text for fuzzy matching (same as backend)
 */
function normalizeForMatching(text) {
    return text
        .toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // Remove accents
        .replace(/[\s_-]+/g, '') // Remove spaces, underscores, hyphens
        .trim();
}

/**
 * Gets available columns from the data panel (if loaded)
 */
function getAvailableColumns() {
    const columns = [];

    // Try to get columns from cached Excel data (via global or event)
    if (window.DocuFlowState && window.DocuFlowState.availableColumns) {
        return window.DocuFlowState.availableColumns;
    }

    // Fallback: try to extract from Tree nodes
    const treeLabels = document.querySelectorAll('#left-column .paneton-tree-label[data-level="2"]');
    treeLabels.forEach(label => {
        const colName = label.textContent.trim();
        if (colName) columns.push(colName);
    });

    return columns;
}

/**
 * Auto-matches placeholders to available columns
 * Respects locked mappings - won't override them
 */
function autoMatchColumns(placeholders, templatePath) {
    const matches = {};
    const availableColumns = getAvailableColumns();
    const lockedMappings = window.DocuFlowLockedMappings[templatePath] || {};

    for (const placeholder of placeholders) {
        // Check if this placeholder is locked
        if (lockedMappings[placeholder.raw] !== undefined) {
            matches[placeholder.raw] = lockedMappings[placeholder.raw];
            continue;
        }

        let match = null;

        // 1. Exact match on normalized name
        match = availableColumns.find(col =>
            normalizeForMatching(col) === placeholder.normalized
        );

        if (!match) {
            // 2. Try with placeholder name (without prefix/suffix)
            match = availableColumns.find(col =>
                normalizeForMatching(col) === normalizeForMatching(placeholder.name)
            );
        }

        matches[placeholder.raw] = match || null;
    }

    return matches;
}

/**
 * Loads placeholders from backend and builds mapping UI
 */
async function loadTemplatePlaceholders(filePath, containerElement, metaBar = null) {
    try {
        containerElement.innerHTML = '<div class="loading-spinner-container"><div class="loading-spinner"></div></div>';
        if (metaBar) metaBar.innerHTML = '<span class="meta-item">Cargando información...</span>';

        const result = await AppService.getTemplatePlaceholders(filePath);

        if (!result || !result.success) {
            containerElement.innerHTML = `<div class="mapping-error"><p>Error: ${result?.error || 'No se pudo cargar la plantilla'}</p></div>`;
            if (metaBar) metaBar.innerHTML = '<span class="meta-item meta-error">Error al cargar</span>';
            return;
        }

        if (result.placeholders.length === 0) {
            containerElement.innerHTML = '<div class="mapping-empty"><p>No se encontraron placeholders en la plantilla</p></div>';
        } else {
            // Auto-match columns (respects locked mappings)
            const matches = autoMatchColumns(result.placeholders, filePath);
            // Build mapping cards
            buildMappingCards(containerElement, result.placeholders, matches, filePath);
        }

        // Update meta bar with file metadata
        if (metaBar && result.metadata) {
            buildMetaBar(metaBar, result.metadata, result.total_count, result.placeholders);
        }

    } catch (error) {
        console.error('[OutputPanel] Error loading placeholders:', error);
        containerElement.innerHTML = `<div class="mapping-error"><p>Error: ${error.message}</p></div>`;
        if (metaBar) metaBar.innerHTML = '<span class="meta-item meta-error">Error al cargar</span>';
    }
}

/**
 * Builds the metadata footer bar with file info
 */
function buildMetaBar(metaBar, metadata, totalCount, placeholders) {
    const items = [];

    // Count placeholders by type
    const textCount = placeholders.filter(p => p.type === 'text').length;
    const imageCount = placeholders.filter(p => p.type === 'image').length;

    // Placeholder counts
    if (totalCount > 0) {
        let countText = `${totalCount} placeholder${totalCount !== 1 ? 's' : ''}`;
        if (textCount > 0 && imageCount > 0) {
            countText = `${textCount} text, ${imageCount} image`;
        } else if (imageCount > 0) {
            countText = `${imageCount} image${imageCount !== 1 ? 's' : ''}`;
        }
        items.push(`<span class="meta-item meta-highlight">${countText}</span>`);
    } else {
        items.push('<span class="meta-item">No placeholders</span>');
    }

    // File size
    if (metadata.file_size_kb) {
        items.push(`<span class="meta-item">Size: ${metadata.file_size_kb} KB</span>`);
    }

    // Paragraphs and tables
    if (metadata.paragraphs !== undefined) {
        items.push(`<span class="meta-item">Paragraphs: ${metadata.paragraphs}</span>`);
    }
    if (metadata.tables !== undefined && metadata.tables > 0) {
        items.push(`<span class="meta-item">Tables: ${metadata.tables}</span>`);
    }

    // Author (if available)
    if (metadata.author) {
        items.push(`<span class="meta-item">Author: ${metadata.author}</span>`);
    }

    metaBar.innerHTML = items.join('');
}

/**
 * Builds the mapping cards UI with split layout
 */
function buildMappingCards(container, placeholders, matches, templatePath) {
    container.innerHTML = '';

    // Get locked mappings for this template
    const lockedMappings = window.DocuFlowLockedMappings[templatePath] || {};

    // Create split layout
    const leftPanel = document.createElement('div');
    leftPanel.className = 'mapping-left-panel';

    const rightPanel = document.createElement('div');
    rightPanel.className = 'mapping-right-panel';

    // Group placeholders by type for both panels
    const groupedPlaceholders = {
        text: placeholders.filter(p => p.type === 'text'),
        image: placeholders.filter(p => p.type === 'image'),
        other: placeholders.filter(p => p.type !== 'text' && p.type !== 'image')
    };

    // === LEFT PANEL: Mapping pairs (ordered by type) ===
    const typeOrder = ['text', 'image', 'other'];
    let isFirstGroup = true;

    for (const typeName of typeOrder) {
        const typeGroup = groupedPlaceholders[typeName];
        if (typeGroup.length === 0) continue;

        // Add separator between groups (not before first group)
        if (!isFirstGroup) {
            const separator = document.createElement('div');
            separator.className = 'mapping-type-separator';
            leftPanel.appendChild(separator);
        }
        isFirstGroup = false;

        for (const placeholder of typeGroup) {
            // Column Card (left - editable) - GREEN theme
            const columnCard = document.createElement('div');
            columnCard.className = 'mapping-card mapping-card-column';
            columnCard.dataset.placeholderRaw = placeholder.raw;
            columnCard.dataset.templatePath = templatePath;

            const matchedColumn = matches[placeholder.raw];
            const isLocked = lockedMappings[placeholder.raw] !== undefined;

            if (matchedColumn) {
                columnCard.classList.add('matched');
                if (isLocked) {
                    columnCard.classList.add('locked');
                }
                columnCard.dataset.columnValue = matchedColumn;
            } else {
                columnCard.classList.add('unmatched');
                columnCard.dataset.columnValue = '';
            }

            // Build card content with lock icon
            buildColumnCardContent(columnCard, matchedColumn, isLocked);

            // Double-click to edit (only if not locked)
            columnCard.addEventListener('dblclick', handleColumnCardDoubleClick);

            // Drag & Drop handlers
            columnCard.addEventListener('dragover', (e) => {
                if (!columnCard.classList.contains('locked')) {
                    e.preventDefault();
                    columnCard.classList.add('drag-over');
                }
            });
            columnCard.addEventListener('dragleave', () => {
                columnCard.classList.remove('drag-over');
            });
            columnCard.addEventListener('drop', handleColumnDrop);

            // Arrow (middle column in grid)
            const arrow = document.createElement('div');
            arrow.className = 'mapping-arrow';
            arrow.innerHTML = ICON_ARROW_RIGHT;

            // Placeholder Card (right column) - Type-based colors
            const placeholderCard = document.createElement('div');
            placeholderCard.className = `mapping-card mapping-card-placeholder type-${placeholder.type || 'other'}`;
            placeholderCard.innerHTML = `<input type="text" class="mapping-card-input-readonly" value="${placeholder.raw}" readonly>`;
            placeholderCard.title = placeholder.raw;

            // Append directly to grid (no pair wrapper)
            leftPanel.appendChild(columnCard);
            leftPanel.appendChild(arrow);
            leftPanel.appendChild(placeholderCard);
        }
    } // End of typeOrder loop

    // === RIGHT PANEL: Tag type summary with counts ===
    // Get unique tag patterns (prefix + suffix) with counts
    const tagSummary = {};
    for (const p of placeholders) {
        const prefix = p.prefix || '{{';
        const suffix = p.suffix || '}}';
        const tagPattern = `${prefix}...${suffix}`;
        const typeClass = p.type || 'other';

        if (!tagSummary[tagPattern]) {
            tagSummary[tagPattern] = { count: 0, type: typeClass, prefix, suffix };
        }
        tagSummary[tagPattern].count++;
    }

    // Display tag summaries
    const tagEntries = Object.entries(tagSummary);

    // Sort: text first, then image, then others
    tagEntries.sort((a, b) => {
        const typeOrder = { text: 0, image: 1, other: 2 };
        const orderA = typeOrder[a[1].type] ?? 2;
        const orderB = typeOrder[b[1].type] ?? 2;
        return orderA - orderB;
    });

    let lastType = null;
    for (const [pattern, data] of tagEntries) {
        // Add separator between different types
        if (lastType !== null && lastType !== data.type) {
            const sep = document.createElement('div');
            sep.className = 'placeholder-type-separator';
            rightPanel.appendChild(sep);
        }
        lastType = data.type;

        const item = document.createElement('div');
        item.className = `placeholder-summary-item type-${data.type}`;
        item.innerHTML = `<span class="tag-pattern">${data.prefix}${data.suffix}</span> <span class="tag-count">: ${data.count}</span>`;
        item.title = `${data.count} placeholder${data.count !== 1 ? 's' : ''} of type ${data.type}`;
        rightPanel.appendChild(item);
    }

    container.appendChild(leftPanel);
    container.appendChild(rightPanel);
}

/**
 * Builds the inner content of a column card (value + lock icon)
 */
function buildColumnCardContent(card, value, isLocked) {
    card.innerHTML = '';

    if (value) {
        // Value display (scrollable input for long values)
        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.className = 'mapping-card-input-readonly';
        valueInput.value = value;
        valueInput.readOnly = true;
        card.appendChild(valueInput);
    } else {
        // Placeholder text
        const placeholder = document.createElement('span');
        placeholder.className = 'card-placeholder-text';
        placeholder.textContent = 'Drop column';
        card.appendChild(placeholder);
    }

    // Lock icon (always present for matched cards)
    if (value) {
        const lockBtn = document.createElement('div');
        lockBtn.className = 'mapping-card-lock';
        lockBtn.innerHTML = isLocked ? ICON_LOCK : ICON_UNLOCK;
        lockBtn.title = isLocked
            ? 'Bloqueado - Al recargar se conservará este valor (clic para desbloquear)'
            : 'Desbloqueado - Al recargar se hará auto-match (clic para bloquear)';
        lockBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleLockToggle(card);
        });
        card.appendChild(lockBtn);
    }
}

/**
 * Toggles lock state for a column card
 */
function handleLockToggle(card) {
    const templatePath = card.dataset.templatePath;
    const placeholderRaw = card.dataset.placeholderRaw;
    const columnValue = card.dataset.columnValue;

    if (!templatePath || !placeholderRaw) return;

    // Initialize template entry if needed
    if (!window.DocuFlowLockedMappings[templatePath]) {
        window.DocuFlowLockedMappings[templatePath] = {};
    }

    const isCurrentlyLocked = card.classList.contains('locked');

    if (isCurrentlyLocked) {
        // Unlock
        delete window.DocuFlowLockedMappings[templatePath][placeholderRaw];
        card.classList.remove('locked');
    } else {
        // Lock with current value
        window.DocuFlowLockedMappings[templatePath][placeholderRaw] = columnValue;
        card.classList.add('locked');
    }

    // Rebuild content with new lock state
    buildColumnCardContent(card, columnValue, !isCurrentlyLocked);
}

/**
 * Handles double-click on column card to enable editing
 */
function handleColumnCardDoubleClick(event) {
    const card = event.currentTarget;
    // Check if click was on lock button
    if (event.target.closest('.mapping-card-lock')) return;
    // Don't allow editing if locked
    if (card.classList.contains('locked')) return;
    // Already has editable input (not readonly)
    if (card.querySelector('.mapping-card-input')) return;

    const currentValue = card.dataset.columnValue || '';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'mapping-card-input';
    input.value = currentValue;
    input.placeholder = 'Nombre de columna';

    input.addEventListener('blur', () => finishEditing(card, input));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            finishEditing(card, input);
        } else if (e.key === 'Escape') {
            cancelEditing(card, currentValue);
        }
    });

    card.innerHTML = '';
    card.appendChild(input);
    input.focus();
    input.select();
}

function finishEditing(card, input) {
    const newValue = input.value.trim();
    card.dataset.columnValue = newValue;
    const isLocked = card.classList.contains('locked');

    if (newValue) {
        card.classList.remove('unmatched');
        card.classList.add('matched');

        // Update locked mapping if locked
        if (isLocked) {
            const templatePath = card.dataset.templatePath;
            const placeholderRaw = card.dataset.placeholderRaw;
            if (templatePath && placeholderRaw) {
                window.DocuFlowLockedMappings[templatePath][placeholderRaw] = newValue;
            }
        }
    } else {
        card.classList.remove('matched', 'locked');
        card.classList.add('unmatched');

        // Remove from locked mappings
        const templatePath = card.dataset.templatePath;
        const placeholderRaw = card.dataset.placeholderRaw;
        if (templatePath && placeholderRaw && window.DocuFlowLockedMappings[templatePath]) {
            delete window.DocuFlowLockedMappings[templatePath][placeholderRaw];
        }
    }

    buildColumnCardContent(card, newValue, isLocked && newValue);
}

function cancelEditing(card, originalValue) {
    const isLocked = card.classList.contains('locked');
    buildColumnCardContent(card, originalValue, isLocked);
}

/**
 * Handles drop of a column onto a mapping card
 */
function handleColumnDrop(event) {
    event.preventDefault();
    const card = event.currentTarget;
    card.classList.remove('drag-over');

    // Don't allow drop on locked cards
    if (card.classList.contains('locked')) return;

    const columnName = event.dataTransfer.getData('text/plain');
    if (columnName) {
        card.dataset.columnValue = columnName;
        card.classList.remove('unmatched');
        card.classList.add('matched');

        const isLocked = card.classList.contains('locked');
        buildColumnCardContent(card, columnName, isLocked);
    }
}

//--------------------------------------> END [ MAPPING SYSTEM ... ]