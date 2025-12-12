// js/uiHelpers.js
/**
 * Project: DocuFlow
 * File:  uiHelpers.js
 * Created: 2025-10-30 (Refactored 2025-11-04)
 * Author: @lewopxd
 *
 * Description:
 * Module for GLOBAL UI helper functions.
 * (Note: Tab logic like setupTabClickHandling was moved to the modules.)
 */

//-------------------------------------------------------------
//-------------[   GLOBAL UI HELPERS   ]-----------------------
//-------------------------------------------------------------

/**
 * [Initializes a resizer bar (vertical or horizontal).]
 * @param {string} resizerId - The ID of the resizer element.
 * @param {string} elementToResizeId - The ID of the element whose flex-basis will change.
 * @param {'vertical' | 'horizontal'} direction - The direction of resizing.
 * @exports
 */
export function initializeResizer(resizerId, elementToResizeId, direction) {

    const resizer = document.getElementById(resizerId);
    const elementToResize = document.getElementById(elementToResizeId);

    // Get the parent container (column or main-container)
    const mainContainer = resizer.parentElement;

    if (!resizer || !elementToResize || !mainContainer) {
        console.warn(`[uiHelpers] Resizer components not found for ${resizerId}. Skipping init.`);
        return;
    }

    // Check if the resizer is hidden by the layout
    if (resizer.classList.contains('is-hidden')) {
        return; // Do not attach listener if resizer is not visible
    }

    let isResizing = false;

    // Variables to store initial state on mousedown
    let initialMouseX = 0;
    let initialMouseY = 0;

    // * MODIFIED: We now need to track the basis for BOTH panels
    let initialTopOrLeftBasis = 0;
    let initialBottomOrRightBasis = 0;
    let siblingElement = null; // Store the sibling

    resizer.addEventListener('mousedown', function (e) {
        e.preventDefault();
        isResizing = true;

        // Store initial mouse position
        initialMouseX = e.clientX;
        initialMouseY = e.clientY;

        // * MODIFIED: Get initial sizes for BOTH panels and lock them
        const rect = elementToResize.getBoundingClientRect();

        if (direction === 'vertical') {
            siblingElement = resizer.nextElementSibling;
            initialTopOrLeftBasis = rect.width;
            if (siblingElement) {
                initialBottomOrRightBasis = siblingElement.getBoundingClientRect().width;
                siblingElement.style.flexGrow = '0';
            }
        } else { // horizontal
            siblingElement = resizer.nextElementSibling;
            initialTopOrLeftBasis = rect.height;
            if (siblingElement) {
                initialBottomOrRightBasis = siblingElement.getBoundingClientRect().height;
                // Lock both panels to pixel-based height and flex-grow: 0
                elementToResize.style.flexBasis = initialTopOrLeftBasis + 'px';
                siblingElement.style.flexBasis = initialBottomOrRightBasis + 'px';
                siblingElement.style.flexGrow = '0';
            }
        }

        // Lock the primary panel
        elementToResize.style.flexGrow = '0';

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    });

    function handleMouseMove(e) {
        if (!isResizing) return;

        let newTopOrLeftBasis = 0;
        let newBottomOrRightBasis = 0;

        if (direction === 'vertical') {
            const deltaX = e.clientX - initialMouseX;
            newTopOrLeftBasis = initialTopOrLeftBasis + deltaX;
            newBottomOrRightBasis = initialBottomOrRightBasis - deltaX;

            // Constrain
            const minWidthPx = 150;
            if (newTopOrLeftBasis < minWidthPx) {
                newTopOrLeftBasis = minWidthPx;
                newBottomOrRightBasis = (initialTopOrLeftBasis + initialBottomOrRightBasis) - minWidthPx;
            } else if (newBottomOrRightBasis < minWidthPx) {
                newBottomOrRightBasis = minWidthPx;
                newTopOrLeftBasis = (initialTopOrLeftBasis + initialBottomOrRightBasis) - minWidthPx;
            }

            // Apply the new basis to BOTH panels
            elementToResize.style.flexBasis = newTopOrLeftBasis + 'px';
            if (siblingElement) {
                siblingElement.style.flexBasis = newBottomOrRightBasis + 'px';
            }

        } else if (direction === 'horizontal') {
            const deltaY = e.clientY - initialMouseY;
            newTopOrLeftBasis = initialTopOrLeftBasis + deltaY;
            newBottomOrRightBasis = initialBottomOrRightBasis - deltaY;

            // Constrain
            const minHeightPx = 50;
            if (newTopOrLeftBasis < minHeightPx) {
                newTopOrLeftBasis = minHeightPx;
                newBottomOrRightBasis = (initialTopOrLeftBasis + initialBottomOrRightBasis) - minHeightPx;
            } else if (newBottomOrRightBasis < minHeightPx) {
                newBottomOrRightBasis = minHeightPx;
                newTopOrLeftBasis = (initialTopOrLeftBasis + initialBottomOrRightBasis) - minHeightPx;
            }

            // Apply the new basis to BOTH panels
            elementToResize.style.flexBasis = newTopOrLeftBasis + 'px';
            if (siblingElement) {
                siblingElement.style.flexBasis = newBottomOrRightBasis + 'px';
            }
        }
    }

    function handleMouseUp() {
        isResizing = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);

        // Mark project dirty after layout change
        if (window.ProjectManager && window.ProjectManager.markDirty) {
            window.ProjectManager.markDirty();
        }
    }
}
//--------------------------------------> END [ GLOBAL UI HELPERS ... ]