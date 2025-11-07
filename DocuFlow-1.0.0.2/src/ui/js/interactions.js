// js/interactions.js
/**
 * Project: DocuFlow
 * File:  interactions.js
 * Created: 2025-10-30
 * Author: @lewopxd 
 *
 * Description:
 * Módulo que contiene toda la lógica de negocio y los flujos de trabajo (workflows)
 * activados por las interacciones del usuario.
 */

import { AppService } from './services.js';
import { 
    addTab, 
    excelStructureToPanetonData,
    initializePanetonTree
} from './recursiveDomBuilder.js';

import { ICON_FILE_SHEET, ICON_FILE_TEMPLATE } from './icons.js'; 

//-------------------------------------------------------------
//-------------[   STATE & MUTATORS   ]------------------------
//-------------------------------------------------------------

/**
 * @type {Array<string>}
 * In-memory list of file paths for the left panel (data sheets).
 */
let currentSheetPaths = [];

/**
 * @type {Array<string>}
 * In-memory list of file paths for the right panel (templates).
 */
let currentTemplatePaths = [];


/**
 * [Updates the in-memory sheet path list and persists it.]
 * @param {string} filePath - The path to add.
 * @returns {Promise<void>}
 */
async function updateSheetPathsAndSave(filePath) {
    if (!currentSheetPaths.includes(filePath)) {
        currentSheetPaths.push(filePath);
        await AppService.saveUiSetting('last_opened_sheet', currentSheetPaths)
            .then(() => console.log('Saved updated sheet list.'))
            .catch(err => console.error('Failed to save sheet list:', err));
    }
}

/**
 * [Updates the in-memory template path list and persists it.]
 * @param {string} filePath - The path to add.
 * @returns {Promise<void>}
 */
async function updateTemplatePathsAndSave(filePath) {
    if (!currentTemplatePaths.includes(filePath)) {
        currentTemplatePaths.push(filePath);
        await AppService.saveUiSetting('last_opened_template', currentTemplatePaths)
            .then(() => console.log('Saved updated template list.'))
            .catch(err => console.error('Failed to save template list:', err));
    }
}

/**
 * [Handles closing a tab, updating state, and saving.]
 * (Lógica de negocio recuperada de app.js original)
 * @param {HTMLElement} tabElement - The tab element (.tab) to be closed.
 * @returns {object} status - Devuelve el panel y el tab a cerrar.
 * @exports
 */
export function handleCloseTabWorkflow(tabElement) {
    const panel = tabElement.closest('.panel');
    if (!panel) return { success: false, panelId: null };

    const panelId = panel.id;
    const filePath = tabElement.dataset.filePath;

    let pathArray, settingKey;

    // Determine which state array and storage key to update
    if (panelId === 'left-panel') {
        pathArray = currentSheetPaths;
        settingKey = 'last_opened_sheet';
    } else if (panelId === 'right-panel') {
        pathArray = currentTemplatePaths;
        settingKey = 'last_opened_template';
    } else {
        return { success: false, panelId: null }; // Unknown panel
    }

    // 1. Remove from in-memory state
    const newPathArray = pathArray.filter(p => p !== filePath);
    if (panelId === 'left-panel') {
        currentSheetPaths = newPathArray;
    } else {
        currentTemplatePaths = newPathArray;
    }
    
    // 2. Save the updated state (asynchronously)
    AppService.saveUiSetting(settingKey, newPathArray)
        .then(() => console.log(`[STATE] Removed ${filePath} and saved state.`))
        .catch(err => console.error(`[STATE] Failed to save state after closing tab: ${err}`));

    // 3. Devolver los datos necesarios para que UIHelpers maneje la remoción del DOM
    return { 
        success: true, 
        panelId: panelId,
        tabElement: tabElement,
        remainingTabsCount: panel.querySelector('.toolbar-tabs').querySelectorAll('.tab').length - 1,
        wasActive: tabElement.classList.contains('active'),
        targetPaneSelector: tabElement.dataset.tabTarget
    };
}
//--------------------------------------> END [ STATE & MUTATORS ... ]

//-------------------------------------------------------------
//-------------[   PUBLIC WORKFLOWS   ]------------------------
//-------------------------------------------------------------

/**
 * [Workflow completo para cargar una Hoja de Datos.]
 * 1. Pide la ruta al SO.
 * 2. Obtiene y transforma la estructura de columnas del archivo.
 * 3. Actualiza la UI con el árbol de Paneton.
 * 4. Guarda el estado.
 * @returns {Promise<void>}
 */
export async function handleLoadSheetWorkflow() {
    try {
        const fileTypes = [
            'Spreadsheets (*.xlsx;*.xls;*.csv)',
            'All Files (*.*)'
        ];
        
        // 1. Obtener el path del archivo
        const response = await AppService.requestFileDialog({
            fileTypes: fileTypes
        });
        
        if (!response || !response.filePath) {
            console.log('User cancelled selection.');
            return;
        }

        const filePath = response.filePath;
        const fileName = filePath.split(/[\\/]/).pop();
        
        // 2. Obtener la estructura del archivo (Mock/Python)
        const fileStructure = await AppService.getExcelFileStructure(filePath);

        if (fileStructure) {
            
            // Imprimir el JSON completo a la consola (Requerimiento)
            console.log(`[EXCEL STRUCTURE] Data loaded for: ${fileName}`);
            console.log(JSON.stringify(fileStructure, null, 2));
            
            // 3. Transformar la estructura a formato Paneton
            const panetonData = excelStructureToPanetonData(fileStructure);

            // 4. Crear la pestaña y obtener el ID del contenedor del ÁRBOL
            // [MODIFICADO] Pasamos el fileStructure para construir el status bar
            const treeWrapperId = addTab(
                'left-panel', 
                fileName, 
                { filePath: filePath }, 
                ICON_FILE_SHEET,
                fileStructure // <-- NUEVO
            );
            
            // 5. Inyectar el árbol de Paneton en el wrapper recién creado
            if (treeWrapperId) {
                // [MODIFICADO] Usamos el ID del wrapper
                initializePanetonTree(treeWrapperId, panetonData);
            }

            // 6. Persistir el estado
            await updateSheetPathsAndSave(filePath);

        } else {
             console.error(`[EXCEL STRUCTURE] Could not retrieve structure for ${fileName}.`);
        }
        
    } catch (error) {
        console.error('Error during Load Sheet Workflow:', error);
    }
}

/**
 * [Workflow completo para cargar una Plantilla de Documentos.]
 * 1. Pide la ruta al SO.
 * 2. Actualiza la UI y guarda el estado.
 * @returns {Promise<void>}
 */
export async function handleLoadTemplateWorkflow() {
    try {
        const fileTypes = [
            'Word Documents (*.docx;*.doc)',
            'All Files (*.*)'
        ];
        
        const response = await AppService.requestFileDialog({
            fileTypes: fileTypes
        });
        
        if (!response || !response.filePath) {
            console.log('User cancelled selection.');
            return;
        }
        
        const filePath = response.filePath;
        const fileName = filePath.split(/[\\/]/).pop();
        
        // [SIN CAMBIOS] El panel derecho sigue usando la lógica antigua
        const contentId = addTab('right-panel', fileName, { filePath: filePath }, ICON_FILE_TEMPLATE, null); 
        
        await updateTemplatePathsAndSave(filePath);

    } catch (error) {
        console.error('Error during Load Template Workflow:', error);
    }
}


/**
 * [Loads the persistent UI settings and restores the session.]
 * @returns {Promise<void>}
 */
export async function loadAndRestoreSession() {
    try {
        console.log('Loading persistent settings...');
        const settings = await AppService.loadSettings();
        console.log('Settings loaded:', settings);

        // 1. Restore Sheet tabs (Left Panel)
        if (settings.last_opened_sheet && Array.isArray(settings.last_opened_sheet)) {
            currentSheetPaths = settings.last_opened_sheet;
            for (const path of currentSheetPaths) {
                const fileName = path.split(/[\\/]/).pop();
                
                // RESTAURACIÓN CLAVE: NECESITAMOS LA ESTRUCTURA PARA RESTAURAR EL ÁRBOL
                const fileStructure = await AppService.getExcelFileStructure(path);
                
                // Se asume que solo restauramos la pestaña si podemos restaurar el árbol.
                if (fileStructure) {
                    const panetonData = excelStructureToPanetonData(fileStructure);
                    
                    // [MODIFICADO] Pasamos el fileStructure
                    const treeWrapperId = addTab(
                        'left-panel', 
                        fileName, 
                        { filePath: path }, 
                        ICON_FILE_SHEET,
                        fileStructure // <-- NUEVO
                    );
                    
                    if (treeWrapperId) {
                         // [MODIFICADO] Usamos el ID del wrapper
                        initializePanetonTree(treeWrapperId, panetonData);
                    }
                } else {
                     console.warn(`Skipping restoration of ${fileName}: Structure not found in DEMO data.`);
                }
            }
        }

        // 2. Restore Template tabs (Right Panel)
        if (settings.last_opened_template && Array.isArray(settings.last_opened_template)) {
            currentTemplatePaths = settings.last_opened_template;
            for (const path of currentTemplatePaths) {
                const fileName = path.split(/[\\/]/).pop();
                // [SIN CAMBIOS] El panel derecho sigue usando la lógica antigua
                addTab('right-panel', fileName, { filePath: path }, ICON_FILE_TEMPLATE, null);
            }
        }
        
        console.log('Session restored.');

    } catch (error) {
        console.error('Could not load persistent settings:', error);
        // App will continue to run with a blank state.
    }
}
//--------------------------------------> END [ PUBLIC WORKFLOWS ... ]