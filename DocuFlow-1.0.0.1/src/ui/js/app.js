// js/app.js
/**
 * Project: DocuFlow
 * File:  app.js
 * Created: [YYYY-MM-DD]
 * Author: @lewopxd 
 *
 * Description:
 * [Lógica principal del frontend, manejo de UI, pestañas y resizer.]
 */

//-------------------------------------------------------------
//-------------[   RESIZER LOGIC   ]---------------------------
//-------------------------------------------------------------

/**
 * [Inicializa la barra de arrastre (resizer) entre paneles.]
 */
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
//--------------------------------------> END [ RESIZER LOGIC ... ]

//-------------------------------------------------------------
//-------------[   TAB SYSTEM   ]------------------------------
//-------------------------------------------------------------

/**
 * [Añade un manejador de clics delegado a un contenedor de pestañas.]
 * [Esto maneja el cambio de pestañas de forma eficiente.]
 * @param {string} panelId - El ID del panel (e.g., 'left-panel').
 */
function setupTabClickHandling(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const tabsContainer = panel.querySelector('.toolbar-tabs');
    const contentContainer = panel.querySelector('.panel-content');

    tabsContainer.addEventListener('click', (e) => {
        // Asegurarse de que se hizo clic en una pestaña y no en el espacio entre ellas
        const clickedTab = e.target.closest('.tab');
        if (clickedTab) {
            
            // Ocultar placeholder si está visible
            const placeholder = panel.querySelector('.placeholder');
            if (placeholder && placeholder.style.display !== 'none') {
                placeholder.style.display = 'none';
            }
            
            // Desactivar todas las pestañas y contenidos de ESTE panel
            tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Activar la pestaña clicada y su contenido
            clickedTab.classList.add('active');
            const targetPane = document.querySelector(clickedTab.dataset.tabTarget);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        }
    });
}

/**
 * [Crea y añade dinámicamente una nueva pestaña y su panel de contenido.]
 * [También oculta el placeholder por defecto si está visible.]
 * @param {string} panelId - El ID del panel donde añadir la pestaña (e.g., 'left-panel').
 * @param {string} tabName - El texto que mostrará la pestaña (e.g., el nombre del archivo).
 * @param {object} data - Datos opcionales para almacenar en la pestaña (e.g., { filePath: '...' }).
 */
function addTab(panelId, tabName, data = {}) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    const tabsContainer = panel.querySelector('.toolbar-tabs');
    const contentContainer = panel.querySelector('.panel-content');
    
    // --- LÓGICA DEL PLACEHOLDER ---
    const placeholder = panel.querySelector('.placeholder');
    // Encontrar el NODO de la tarjeta de línea punteada
    const placeholderFrameTemplate = panel.querySelector('.placeholder-frame');
    
    if (placeholder && placeholder.style.display !== 'none') {
        // Ocultar el contenedor del placeholder original
        placeholder.style.display = 'none';
    }

    // 3. Desactivar todas las pestañas y contenidos existentes
    tabsContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    contentContainer.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // 4. Crear la nueva pestaña (Contenedor Flex)
    const newTab = document.createElement('div');
    newTab.className = 'tab active';
    
    // --- MODIFICACIÓN ---
    // 5. Crear la etiqueta de texto (Hijo)
    const newLabel = document.createElement('span');
    newLabel.className = 'tab-label';
    newLabel.textContent = tabName;
    newTab.appendChild(newLabel); // Añadir el span dentro del div.tab
    // --- FIN DE MODIFICACIÓN ---
    
    // 6. Crear el nuevo panel de contenido
    const newContentPane = document.createElement('div');
    newContentPane.className = 'tab-content active';
    const contentId = `${panelId}-content-${Date.now()}`; // ID único
    newContentPane.id = contentId;
    
    // 7. Clonar el NODO del placeholder-frame y añadirlo
    if (placeholderFrameTemplate) {
        const newFrame = placeholderFrameTemplate.cloneNode(true); // true = clonación profunda
        newContentPane.appendChild(newFrame);
    } else {
        newContentPane.innerHTML = '<p>Error: Plantilla de contenido no encontrada.</p>';
    }

    // 8. Vincularlos
    newTab.dataset.tabTarget = `#${contentId}`;

    // Almacenar datos (como la ruta del archivo) en el elemento de la pestaña
    if (data.filePath) {
        newTab.dataset.filePath = data.filePath;
        newTab.title = data.filePath; // Tooltip con la ruta completa
    }
    
    // 9. Añadirlos al DOM
    tabsContainer.appendChild(newTab);
    contentContainer.appendChild(newContentPane);
}

//--------------------------------------> END [ TAB SYSTEM ... ]

//-------------------------------------------------------------
//-------------[   EVENT LISTENERS   ]-------------------------
//-------------------------------------------------------------

/**
 * [Maneja el clic en el botón 'Cargar hoja de datos' (Panel Izquierdo).]
 * [Llama a Python para abrir un diálogo de archivo y añade una pestaña.]
 */
async function handleLoadSheetClick() {
    try {
        const fileTypes = [
            'Hojas de cálculo (*.xlsx;*.xls;*.csv)',
            'Todos los archivos (*.*)'
        ];
        
        const response = await window.bridgePy.send('open_file_dialog', {
            file_types: fileTypes
        });
        
        if (response && response.filePath) {
            const filePath = response.filePath;
            const fileName = filePath.split(/[\\/]/).pop();
            addTab('left-panel', fileName, { filePath: filePath });
            console.log('Archivo de datos seleccionado:', filePath);
        } else {
            console.log('El usuario canceló la selección.');
        }
    } catch (error) {
        console.error('Error al abrir el diálogo de archivo de datos:', error);
    }
}

/**
 * [Maneja el clic en el botón 'Cargar template' (Panel Derecho).]
 * [Llama a Python para abrir un diálogo de archivo y añade una pestaña.]
 */
async function handleLoadTemplateClick() {
    try {
        // Filtro específico para documentos de Word
        const fileTypes = [
            'Documentos de Word (*.docx;*.doc)',
            'Todos los archivos (*.*)'
        ];
        
        const response = await window.bridgePy.send('open_file_dialog', {
            file_types: fileTypes
        });
        
        if (response && response.filePath) {
            const filePath = response.filePath;
            const fileName = filePath.split(/[\\/]/).pop();
            // Añade la pestaña al 'right-panel'
            addTab('right-panel', fileName, { filePath: filePath });
            console.log('Archivo de plantilla seleccionado:', filePath);
        } else {
            console.log('El usuario canceló la selección.');
        }
    } catch (error)
    {
        console.error('Error al abrir el diálogo de archivo de plantilla:', error);
    }
}

//--------------------------------------> END [ EVENT LISTENERS ... ]

//-------------------------------------------------------------
//-------------[   INITIALIZATION   ]--------------------------
//-------------------------------------------------------------

/**
 * [Inicializa todos los componentes cuando el DOM está listo.]
 */
document.addEventListener('DOMContentLoaded', () => {
 
    // Inicializar resizer
    initializeResizer();
    
    // Inicializar manejadores de clics para pestañas
    setupTabClickHandling('left-panel');
    setupTabClickHandling('right-panel');
    
    // Conectar botón del panel izquierdo
    const loadSheetButton = document.getElementById('load-sheet-button');
    if (loadSheetButton) {
        loadSheetButton.addEventListener('click', handleLoadSheetClick);
    }
    
    // Conectar botón del panel derecho
    const loadTemplateButton = document.getElementById('load-template-button');
    if (loadTemplateButton) {
        loadTemplateButton.addEventListener('click', handleLoadTemplateClick);
    }
    
    console.log('DocuFlow Engine initialized successfully');
});
//--------------------------------------> END [ INITIALIZATION ... ]