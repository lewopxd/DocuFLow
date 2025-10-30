// js/recursiveDomBuilder.js
/**
 * Project: DocuFlow
 * File:  recursiveDomBuilder.js
 * Created: 2025-10-30
 * Author: @lewopxd 
 *
 * Description:
 * Módulo de utilidades para construir y manipular la estructura DOM de la UI.
 * Contiene funciones para crear elementos dinámicos (pestañas, nodos de árbol, etc.).
 */

// Importa los iconos SVG
import { ICON_CLOSE } from './icons.js';

// --- Global: Paneton.Tree se carga desde index.html via script tag ---
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
    
    // 1. Crear el nodo Raíz (Archivo)
    const fileNode = {
        name: metadata.fileName,
        path: metadata.fileName,
        type: 'file', // Metadato para control de iconos
        expanded: true, // Expandir por defecto
        children: []
    };

    // 2. Iterar sobre las Hojas
    // Usamos map para asegurar que las hojas mantengan el orden del JSON (del Excel)
    sheets.map(sheet => {
        const sheetNode = {
            name: sheet.sheetName,
            path: `${metadata.fileName}/${sheet.sheetName}`,
            type: 'sheet', // Metadato para control de iconos
            expanded: true,
            children: []
        };

        // 3. Iterar sobre las Tablas dentro de la Hoja
        // Usamos map para asegurar que las tablas mantengan el orden del JSON (del Excel)
        sheet.tables.map(table => {
            
            // Asignar un nombre legible a la tabla
            const displayTableName = table.isNamedTable 
                ? table.tableName 
                : `UNAMED_TABLE (Hoja Completa)`;

            const tableNode = {
                name: displayTableName,
                path: `${metadata.fileName}/${sheet.sheetName}/${table.tableName}`,
                type: 'table', // Metadato para control de iconos
                expanded: false, // Las tablas se colapsan por defecto
                buttons: [ 
                    // Simulamos un botón que muestra metadatos
                    { tooltip: `Rows: ${table.rowCount}` }
                ],
                children: []
            };

            // 4. Iterar sobre las Columnas (los nodos más bajos)
            // Usamos map para asegurar que las columnas mantengan el orden del Excel
            table.columns.map(columnName => {
                const columnNode = {
                    name: columnName,
                    path: `${tableNode.path}/${columnName}`,
                    type: 'column', // Metadato para control de iconos
                    isLeaf: true,
                    // No children, es el nodo final
                };
                tableNode.children.push(columnNode);
            });

            sheetNode.children.push(tableNode);
        });

        // Solo agregar la hoja si tiene tablas (evitar hojas vacías en el árbol)
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
    // Apunta directamente al contenedor del árbol (el wrapper de la Fila 2)
    const treeContainer = document.getElementById(containerId);

    if (!treeContainer) {
        console.error(`Paneton Tree: Target container #${containerId} not found.`);
        return;
    }

    // 1. Añadimos la clase de estilo
    treeContainer.classList.add('paneton-tree-container');
    
    // 2. Inicializar Paneton.Tree
    if (PanetonTree) { 
        const treeInstance = new PanetonTree(treeContainer, {
            data: treeData,
            // Opciones de configuración del árbol Paneton:
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
 * @param {object|null} fileStructure - [NUEVO] El objeto de estructura del archivo para poblar metadatos.
 * @returns {string} The ID of the new content pane (o el tree-wrapper si es panel izq).
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
    newContentPane.className = 'tab-content active'; // <-- Este tiene el margin: 20px
    const contentId = `${panelId}-content-${Date.now()}`;
    newContentPane.id = contentId;
    
    // Link tab and content
    newTab.dataset.tabTarget = `#${contentId}`;

    if (data.filePath) {
        newTab.dataset.filePath = data.filePath;
        newTab.title = data.filePath;
    }
    
    tabsContainer.appendChild(newTab);
    contentContainer.appendChild(newContentPane);

    // --- LÓGICA CONDICIONAL DE LAYOUT ---
    
    // Si es el panel izquierdo y tenemos datos, construimos el grid.
    if (panelId === 'left-panel' && fileStructure) {
        
        // [NUEVO] Crear el wrapper del grid que irá DENTRO del .tab-content
        const gridWrapper = document.createElement('div');
        gridWrapper.className = 'tab-content-grid'; // Nueva clase para el grid
        newContentPane.appendChild(gridWrapper); // Añadirlo al .tab-content

        // 1. Calcular metadatos
        const stats = _calculateFileStats(fileStructure);
        
        const fullPath = fileStructure.metadata.fullPath || data.filePath || '';
        const fileName = fileStructure.metadata.fileName || tabName;
        const directoryPath = fullPath.replace(fileName, '');

        // 2. Construir el DOM del Grid
        
        // Fila 1: Path Bar
        const pathBar = document.createElement('div');
        pathBar.className = 'status-bar__path'; 
        pathBar.innerHTML = `<span>${directoryPath}</span>`;
        
        // Fila 2: Tree Wrapper
        const treeWrapper = document.createElement('div');
        treeWrapper.className = 'tree-wrapper';
        const treeWrapperId = `tree-wrapper-${Date.now()}`;
        treeWrapper.id = treeWrapperId;
        
        // Fila 3: Meta Bar con 2 filas
        const metaBar = document.createElement('div');
        metaBar.className = 'meta-bar'; 

        // Crear Fila Superior (Format + Size)
        const metaBarRowTop = document.createElement('div');
        metaBarRowTop.className = 'meta-bar-row-top';
        metaBarRowTop.appendChild(_createMetaBox('Format', stats.format, 'top'));
        metaBarRowTop.appendChild(_createMetaBox('Size', stats.size, 'top'));

        // Crear Fila Inferior (Resto de metadatos)
        const metaBarRowBottom = document.createElement('div');
        metaBarRowBottom.className = 'meta-bar-row-bottom';
        metaBarRowBottom.appendChild(_createMetaBox('Sheets', stats.sheetCount, 'bottom'));
        metaBarRowBottom.appendChild(_createMetaBox('Tables', stats.tableCount, 'bottom'));
        metaBarRowBottom.appendChild(_createMetaBox('Columns', stats.columnCount, 'bottom'));
        metaBarRowBottom.appendChild(_createMetaBox('Total Rows', stats.totalRows, 'bottom'));

        // Añadir ambas filas al metaBar
        metaBar.appendChild(metaBarRowTop);
        metaBar.appendChild(metaBarRowBottom);
        
        // [MODIFICADO] Añadir filas al gridWrapper, NO al newContentPane
        gridWrapper.appendChild(pathBar);
        gridWrapper.appendChild(treeWrapper);
        gridWrapper.appendChild(metaBar);
        
        // Devolvemos el ID del wrapper para que Paneton se inyecte allí
        return treeWrapperId;

    } else {
        // Fallback para panel derecho o si no hay datos
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
 * [Calcula estadísticas agregadas desde el objeto fileStructure.]
 * @param {object} fileStructure - El objeto de estructura del archivo.
 * @returns {object} - Un objeto con las estadísticas calculadas.
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

    // Extraer extensión para formato
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
 * [Crea un contenedor de metadato individual.]
 * @param {string} label - El texto de la etiqueta (ej. "Size").
 * @param {string|number} value - El valor del metadato (ej. "215 KB").
 * @param {string} position - 'top' o 'bottom' para aplicar la clase correcta.
 * @returns {HTMLElement} - El elemento DOM .meta-stat-box.
 * @private
 */
function _createMetaBox(label, value, position = 'top') {
    const box = document.createElement('div');
    // Clase base + clase específica de posición
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