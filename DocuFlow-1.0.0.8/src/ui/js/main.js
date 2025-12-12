// js/main.js
/**
 * Project: DocuFlow
 * File:  main.js
 * Created: 2025-11-04 (Refactored)
 * Author: @lewopxd
 *
 * Description:
 * Main application entry point (App Shell Orchestrator).
 *
 * Responsibilities:
 * 1. Finds the static shell containers (panel slots) defined in main.html.
 * 2. Builds the "Window Frame" (title bar, collapse button) inside *every* slot.
 * 3. Applies the initial layout configuration (showing/hiding panels).
 * 4. Initializes global components (resizers) and logic (panel collapse).
 * 5. Loads the independent modules into their respective "Window Frame" content areas.
 */

// Import global-only UI helpers
import { initializeResizer } from './uiHelpers.js';

// Import project manager for startup flow
import { checkAndLoadProject } from './project-manager.js';

// Import global icons needed by the shell
import {
    ICON_WINDOW_DATA,
    ICON_WINDOW_TEMPLATES,
    ICON_CHEVRON_UP,
    ICON_CHEVRON_DOWN
} from './icons.js';

//-------------------------------------------------------------
//-------------[   INITIAL LAYOUT CONFIGURATION   ]------------
//-------------------------------------------------------------

/**
 * @const {object}
 * Defines the initial visible state of the IDE panels.
 */
const layoutConfig = {
    // Column Visibility
    showLeftColumn: true,
    showRightColumn: true,

    // Left Column Slots
    showLeftTop: true,
    showLeftBottom: true, // MODIFIED: Set to true per user request

    // Right Column Slots
    showRightTop: true,
    showRightBottom: true,
};

//-------------------------------------------------------------
//-------------[   DYNAMIC MODULE LOADER   ]-------------------
//-------------------------------------------------------------

/**
 * [Creates the standard "window frame" DOM inside a panel slot.]
 * @param {HTMLElement} container - The panel slot (e.g., #left-top-panel).
 * @param {string} title - The title for the window.
 * @param {string} iconSvg - The SVG string for the title bar icon.
 * @returns {HTMLElement} The `.module-content` element, for the loader to inject content into.
 */
function buildWindowFrame(container, title, iconSvg) {
    // 1. Create Frame
    const frame = document.createElement('div');
    frame.className = 'module-window-frame';

    // 2. Create Title Bar
    const titleBar = document.createElement('div');
    titleBar.className = 'module-title-bar';
    titleBar.innerHTML = `
        <div class="module-icon-container">${iconSvg}</div>
        <span class="module-title">${title}</span>
        <div class="module-collapse-button" title="Collapse Panel">
            ${ICON_CHEVRON_UP}
        </div>
    `;

    // 3. Create Content Area
    const content = document.createElement('div');
    content.className = 'module-content';

    // 4. Assemble
    frame.appendChild(titleBar);
    frame.appendChild(content);
    container.appendChild(frame);

    // 5. Wire up collapse button
    const collapseButton = titleBar.querySelector('.module-collapse-button');
    collapseButton.addEventListener('click', () => handleCollapseToggle(container.id));

    return content; // Return the content area for the module to be loaded into
}

/**
 * [Handles the logic for collapsing/expanding a panel slot.]
 * This is global logic, as it must affect sibling panels and resizers.
 * @param {string} slotId - The ID of the panel slot to toggle (e.g., 'left-top-panel').
 */
function handleCollapseToggle(slotId) {
    const slot = document.getElementById(slotId);
    if (!slot) return;

    // MODIFIED: Find the button *within* the slot
    const button = slot.querySelector('.module-collapse-button');
    let resizer, siblingSlot;

    // Determine the resizer and sibling for layout changes
    if (slotId === 'left-top-panel') {
        resizer = document.getElementById('resizer-h-left');
        siblingSlot = document.getElementById('left-bottom-panel');
    } else if (slotId === 'left-bottom-panel') {
        resizer = document.getElementById('resizer-h-left');
        siblingSlot = document.getElementById('left-top-panel');
    } else if (slotId === 'right-top-panel') {
        resizer = document.getElementById('resizer-h-right');
        siblingSlot = document.getElementById('right-bottom-panel');
    } else if (slotId === 'right-bottom-panel') {
        resizer = document.getElementById('resizer-h-right');
        siblingSlot = document.getElementById('right-top-panel');
    }

    // MODIFIED: Toggle the class on the *slot*, not the frame
    const isNowCollapsed = slot.classList.toggle('is-panel-collapsed');

    // Update icon and title
    if (button) {
        // The CSS will handle the rotation
        button.title = isNowCollapsed ? "Expand Panel" : "Collapse Panel";
    }

    // Toggle the resizer and the sibling's fill state
    if (resizer) {
        resizer.classList.toggle('is-hidden', isNowCollapsed);
    }
    if (siblingSlot) {
        // .is-expanded-fill is a class in main.css
        siblingSlot.classList.toggle('is-expanded-fill', isNowCollapsed);
    }
}


/**
 * [Loads a module's content (HTML, CSS, JS) into a pre-built content container.]
 * @param {string} moduleName - The name of the module folder (e.g., 'data-panel').
 * @param {HTMLElement} contentContainer - The `.module-content` element to inject into.
 * @returns {Promise<void>}
 */
async function loadModule(moduleName, contentContainer) {
    console.log(`[Main] Loading module content: ${moduleName}...`);

    try {
        // 1. Load CSS
        const cssLink = document.createElement('link');
        cssLink.rel = 'stylesheet';
        cssLink.href = `modules/${moduleName}/${moduleName}.css`;
        document.head.appendChild(cssLink);

        // 2. Load HTML
        // Fetch the module's HTML and inject it *inside* the .module-content
        const htmlResponse = await fetch(`modules/${moduleName}/${moduleName}.html`);
        if (!htmlResponse.ok) {
            throw new Error(`Failed to fetch HTML for ${moduleName}: ${htmlResponse.statusText}`);
        }
        contentContainer.innerHTML = await htmlResponse.text();

        // 3. Load JS
        const jsModule = await import(`../modules/${moduleName}/${moduleName}.js`);

        // 4. Initialize Module
        // Pass the .module-content container to the module's JS
        if (jsModule && typeof jsModule.initialize === 'function') {
            jsModule.initialize(contentContainer); // Pass the inner content element
            console.log(`[Main] Module ${moduleName} initialized successfully.`);
        } else {
            throw new Error(`Module ${moduleName} does not have an 'initialize' function.`);
        }

    } catch (error) {
        console.error(`[Main] Failed to load module ${moduleName}:`, error);
        contentContainer.innerHTML = `<div class="placeholder"><div class="placeholder-frame"><h2>Error</h2><p>Could not load module: ${moduleName}</p></div></div>`;
    }
}

//--------------------------------------> END [ DYNAMIC MODULE LOADER ... ]

//-------------------------------------------------------------
//-------------[   LAYOUT APPLY & BOOTSTRAP   ]----------------
//-------------------------------------------------------------

/**
 * [Finds a DOM element and toggles its visibility based on a boolean.]
 * @param {string} id - The ID of the element to find.
 * @param {boolean} show - If true, remove .is-hidden; if false, add .is-hidden.
 */
function toggleElement(id, show) {
    const el = document.getElementById(id);
    if (el) {
        if (show) {
            el.classList.remove('is-hidden');
        } else {
            el.classList.add('is-hidden');
        }
    }
}

/**
 * [Applies the layoutConfig to the DOM, showing/hiding panels and resizers.]
 */
function applyLayoutConfiguration() {
    // Apply full column visibility
    toggleElement('left-column', layoutConfig.showLeftColumn);
    toggleElement('right-column', layoutConfig.showRightColumn);
    toggleElement('resizer-v-main', layoutConfig.showLeftColumn && layoutConfig.showRightColumn);

    // Apply left column slot visibility
    toggleElement('left-top-panel', layoutConfig.showLeftTop);
    toggleElement('left-bottom-panel', layoutConfig.showLeftBottom);
    toggleElement('resizer-h-left', layoutConfig.showLeftTop && layoutConfig.showLeftBottom);

    // Apply right column slot visibility
    toggleElement('right-top-panel', layoutConfig.showRightTop);
    toggleElement('right-bottom-panel', layoutConfig.showRightBottom);
    toggleElement('resizer-h-right', layoutConfig.showRightTop && layoutConfig.showRightBottom);
}

/**
 * [Initializes the App Shell when the DOM is ready.]
 */
document.addEventListener('DOMContentLoaded', async () => {

    // 1. Find all static slots
    const leftTopSlot = document.getElementById('left-top-panel');
    const leftBottomSlot = document.getElementById('left-bottom-panel');
    const rightTopSlot = document.getElementById('right-top-panel');
    const rightBottomSlot = document.getElementById('right-bottom-panel');

    // 2. Build the Window Frame for ALL slots
    const ltContent = buildWindowFrame(leftTopSlot, 'Data Panel', ICON_WINDOW_DATA);
    const lbContent = buildWindowFrame(leftBottomSlot, 'Attachments', ICON_WINDOW_DATA); // Using placeholder icon
    const rtContent = buildWindowFrame(rightTopSlot, 'Templates Panel', ICON_WINDOW_TEMPLATES);
    const rbContent = buildWindowFrame(rightBottomSlot, 'Build & Save', ICON_WINDOW_TEMPLATES); // Using placeholder icon

    // 3. Apply the layout configuration (show/hide slots)
    applyLayoutConfiguration();

    // 4. Initialize Global Components (Resizers)
    initializeResizer('resizer-v-main', 'left-column', 'vertical');
    initializeResizer('resizer-h-left', 'left-top-panel', 'horizontal');
    initializeResizer('resizer-h-right', 'right-top-panel', 'horizontal');

    // 5. Load Modules *only* into visible slots
    // (loadModule is smart enough to skip if the slot was hidden, but this is cleaner)

    if (layoutConfig.showLeftTop) {
        await loadModule('data-panel', ltContent);
    }

    // (We don't have an 'attachments-panel' module yet, so we don't load it)
    if (layoutConfig.showLeftBottom) {
        // await loadModule('attachments-panel', lbContent);
    }

    if (layoutConfig.showRightTop) {
        await loadModule('templates-panel', rtContent);
    }

    // (We don't have a 'build-panel' module yet, so we don't load it)
    if (layoutConfig.showRightBottom) {
        // await loadModule('build-panel', rbContent);
    }

    console.log('DocuFlow Engine Initialized (Modular Shell)');

    // 6. Check for and load last project (after modules are ready)
    setTimeout(async () => {
        try {
            const projectLoaded = await checkAndLoadProject();
            if (projectLoaded) {
                console.log('[Main] Last project restored successfully');
            }
        } catch (e) {
            console.error('[Main] Error loading project:', e);
        }
    }, 200);
});
//--------------------------------------> END [ LAYOUT APPLY & BOOTSTRAP ... ]