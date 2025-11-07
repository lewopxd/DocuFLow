// js/uiHelpers.js
/**
 * Project: DocuFlow
 * File:  uiHelpers.js
 * Created: 2025-10-30
 * Author: @lewopxd
 *
 * Description:
 * Módulo para funciones auxiliares de la Interfaz de Usuario (UI)
 * que manejan el DOM directamente pero no contienen lógica de negocio.
 */

// Importa la lógica de negocio para cerrar pestañas
import { handleCloseTabWorkflow } from './interactions.js';

//-------------------------------------------------------------
//-------------[   UI HELPERS   ]------------------------------
//-------------------------------------------------------------

/**
 * [Initializes the resizer bar between panels.]
 * @exports
 */
export function initializeResizer() {
    const resizer = document.getElementById('resizer');
    const leftPanel = document.getElementById('left-panel');
    const mainContainer = document.querySelector('.main-container');
    let isResizing = false;

    resizer.addEventListener('mousedown', function(e) {
        e.preventDefault();
        isResizing = true;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    });

    function handleMouseMove(e) {
        if (!isResizing) return;
        
        const containerRect = mainContainer.getBoundingClientRect();
        const minWidthPx = 200;
        let leftWidth = e.clientX - containerRect.left;
        
        if (leftWidth < minWidthPx) {
            leftWidth = minWidthPx;
        }
        
        if (leftWidth > containerRect.width - minWidthPx - resizer.offsetWidth) {
            leftWidth = containerRect.width - minWidthPx - resizer.offsetWidth;
        }
        
        leftPanel.style.flexBasis = leftWidth + 'px';
    }

    function handleMouseUp() {
        isResizing = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
    }
}

/**
 * [Removes the tab and content pane from the DOM, and manages placeholder/active state.]
 * @param {HTMLElement} tabElement - The tab element to be removed.
 * @param {string} targetPaneSelector - The selector of the content pane to be removed.
 * @param {string} panelId - The ID of the parent panel.
 * @param {number} remainingTabsCount - Tabs remaining *after* this one is removed.
 * @param {boolean} wasActive - True if the tab being removed was the active one.
 * @private
 */
function removeTabAndRestoreState(tabElement, targetPaneSelector, panelId, remainingTabsCount, wasActive) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    
    // 1. Remover el contenido y la pestaña
    const contentPane = document.querySelector(targetPaneSelector);
    if (contentPane) contentPane.remove();
    tabElement.remove();

    if (remainingTabsCount === 0) {
        // Mostrar placeholder si no quedan pestañas
        const placeholder = panel.querySelector('.placeholder');
        if (placeholder) {
            placeholder.style.display = 'block';
        }
    } else if (wasActive) {
        // Activar la última pestaña si la activa fue cerrada
        const tabsContainer = panel.querySelector('.toolbar-tabs');
        const remainingTabs = tabsContainer.querySelectorAll('.tab');
        
        const lastTab = remainingTabs[remainingTabs.length - 1];
        lastTab.classList.add('active');
        
        const targetPane = document.querySelector(lastTab.dataset.tabTarget);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    }
}

/**
 * [Sets up delegated click handling for tab activation and potential closing.]
 * @param {string} panelId - The ID of the panel (e.g., 'left-panel').
 * @exports
 */
export function setupTabClickHandling(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const tabsContainer = panel.querySelector('.toolbar-tabs');
    const contentContainer = panel.querySelector('.panel-content');

    tabsContainer.addEventListener('click', (e) => {
        const clickedTab = e.target.closest('.tab');
        if (!clickedTab) return; // Click was not inside any tab

        const clickedClose = e.target.closest('.tab-close');

        // 1. Manejo del Cierre de Pestaña (Lógica de Negocio)
        if (clickedClose) {
             const result = handleCloseTabWorkflow(clickedTab);
             if (result.success) {
                // Manipulación del DOM (Lógica de UI)
                removeTabAndRestoreState(
                    result.tabElement,
                    result.targetPaneSelector,
                    result.panelId,
                    result.remainingTabsCount,
                    result.wasActive
                );
             }
             return;
        }
        
        // 2. Manejo de Activación de Pestaña
        const placeholder = panel.querySelector('.placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        clickedTab.classList.add('active');
        const targetPane = document.querySelector(clickedTab.dataset.tabTarget);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    });
}
//--------------------------------------> END [ UI HELPERS ... ]