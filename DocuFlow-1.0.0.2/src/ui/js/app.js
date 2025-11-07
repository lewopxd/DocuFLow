// js/app.js
/**
 * Project: DocuFlow
 * File:  app.js
 * Created: 2025-10-30 (Refactored)
 * Author: @lewopxd 
 *
 * Description:
 * [Main application entry point. Handles initial setup and event delegation.]
 * [The complex business logic is delegated to interactions.js.]
 */

// Import initialization and interaction logic
import { 
    handleLoadSheetWorkflow, 
    handleLoadTemplateWorkflow,
    loadAndRestoreSession
} from './interactions.js';

// Import UI helper functions
import { 
    initializeResizer, 
    setupTabClickHandling 
} from './uiHelpers.js';

// Import button icons for static injection
import { ICON_PLUS } from './icons.js';

//-------------------------------------------------------------
//-------------[   INITIALIZATION   ]--------------------------
//-------------------------------------------------------------

/**
 * [Injects dynamic SVG icons into their button containers.]
 * @private
 */
function injectIcons() {
    const loadSheetButton = document.getElementById('load-sheet-button');
    const loadTemplateButton = document.getElementById('load-template-button');
    
    if (loadSheetButton) {
        loadSheetButton.innerHTML = ICON_PLUS;
    }
    if (loadTemplateButton) {
        loadTemplateButton.innerHTML = ICON_PLUS;
    }
}

/**
 * [Initializes all components when the DOM is ready.]
 */
document.addEventListener('DOMContentLoaded', async () => {
 
    injectIcons();
 
    // Initialize standard UI components (Resizer, Tab Click Delegation)
    initializeResizer();
    setupTabClickHandling('left-panel');
    setupTabClickHandling('right-panel');
    
    // Connect button listeners: Calls the workflows from interactions.js
    const loadSheetButton = document.getElementById('load-sheet-button');
    if (loadSheetButton) {
        // Calls the complete workflow
        loadSheetButton.addEventListener('click', handleLoadSheetWorkflow);
    }
    
    const loadTemplateButton = document.getElementById('load-template-button');
    if (loadTemplateButton) {
        // Calls the complete workflow
        loadTemplateButton.addEventListener('click', handleLoadTemplateWorkflow);
    }
    
    // Load settings and restore previous session tabs
    await loadAndRestoreSession();
    
    console.log('DocuFlow Engine Initialized (Modularized)');
});
//--------------------------------------> END [ INITIALIZATION ... ]