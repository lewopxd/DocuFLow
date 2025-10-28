/**
 * ============================================
 * DocuFlow Engine - Lógica Principal
 * ============================================
 */

// --- Lógica para la Barra de Arrastre Funcional ---
function initializeResizer() {
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
 * Initializes a tab system for a given panel.
 * It dynamically creates content panes for each tab and handles the switching logic.
 * @param {string} panelId - The ID of the panel element (e.g., 'left-panel').
 */
function setupTabSystem(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const tabsContainer = panel.querySelector('.toolbar-tabs');
    const contentContainer = panel.querySelector('.panel-content');
    const placeholderTemplate = panel.querySelector('.placeholder');
    const tabs = tabsContainer.querySelectorAll('.tab');

    if (!placeholderTemplate || tabs.length === 0) return;

    const placeholderHtml = placeholderTemplate.innerHTML;

    tabs.forEach((tab, index) => {
        // Create the content div for this tab
        const contentPane = document.createElement('div');
        contentPane.className = 'tab-content';
        const panelName = panelId.replace('-panel', '');
        contentPane.id = `${panelName}-tab-content-${index}`;
        contentPane.innerHTML = placeholderHtml;
        contentContainer.appendChild(contentPane);

        // Assign a data attribute to the tab to link it to its content pane
        tab.dataset.tabTarget = `#${contentPane.id}`;

        // Add click listener
        tab.addEventListener('click', () => {
            // Deactivate all tabs and content panes within this panel
            tabs.forEach(t => t.classList.remove('active'));
            contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Activate the clicked tab and its corresponding content
            tab.classList.add('active');
            const targetPane = document.querySelector(tab.dataset.tabTarget);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });

    // Activate the first tab and its content by default
    if (tabs.length > 0) {
        tabs[0].classList.add('active');
        const firstContentPane = document.querySelector(tabs[0].dataset.tabTarget);
        if (firstContentPane) {
            firstContentPane.classList.add('active');
        }
    }
}

/**
 * Initialize all components when the document is ready
 */
document.addEventListener('DOMContentLoaded', () => {
 
    
    // Initialize resizer functionality
    initializeResizer();
    
    // Initialize both tab systems
    setupTabSystem('left-panel');
    setupTabSystem('right-panel');
    
    console.log('DocuFlow Engine initialized successfully');
});