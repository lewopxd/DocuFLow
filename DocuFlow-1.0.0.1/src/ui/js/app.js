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

// Importa funciones de inicialización y lógica de interacción
import { 
    handleLoadSheetWorkflow, 
    handleLoadTemplateWorkflow,
    loadAndRestoreSession
} from './interactions.js';

// Importa funciones auxiliares de UI
import { 
    initializeResizer, 
    setupTabClickHandling 
} from './uiHelpers.js';

// Importa iconos de botón para inyección estática
import { ICON_SHEET, ICON_TEMPLATE } from './icons.js';

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
        loadSheetButton.innerHTML = ICON_SHEET;
    }
    if (loadTemplateButton) {
        loadTemplateButton.innerHTML = ICON_TEMPLATE;
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
    
    // Connect button listeners: Llama a los Workflows de interactions.js
    const loadSheetButton = document.getElementById('load-sheet-button');
    if (loadSheetButton) {
        // Llama al workflow completo
        loadSheetButton.addEventListener('click', handleLoadSheetWorkflow);
    }
    
    const loadTemplateButton = document.getElementById('load-template-button');
    if (loadTemplateButton) {
        // Llama al workflow completo
        loadTemplateButton.addEventListener('click', handleLoadTemplateWorkflow);
    }
    
    // Load settings and restore previous session tabs
    await loadAndRestoreSession();
    
    console.log('DocuFlow Engine Initialized (Modularized)');
});
//--------------------------------------> END [ INITIALIZATION ... ]