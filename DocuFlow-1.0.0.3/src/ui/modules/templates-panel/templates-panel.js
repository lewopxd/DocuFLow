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
import { ICON_CLOSE, ICON_PLUS, ICON_FILE_TEMPLATE } from '../../js/icons.js';

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
    
    // 5. Load settings and restore previous session tabs
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

    // --- Build Internal Content (Simple Placeholder) ---
    // This module does not build a complex grid.
    const placeholderFrameTemplate = placeholder.querySelector('.placeholder-frame');
    if (placeholderFrameTemplate) {
        const newFrame = placeholderFrameTemplate.cloneNode(true);
        // Update placeholder text for the new tab
        newFrame.querySelector('h2').textContent = fileName;
        newFrame.querySelector('p').textContent = "Variable extraction logic will go here.";
        newContentPane.appendChild(newFrame);
    } else {
        newContentPane.innerHTML = '<p>Error: Content template not found.</p>';
    }
    
    return contentId;
}
//--------------------------------------> END [ DYNAMIC DOM BUILDERS ... ]