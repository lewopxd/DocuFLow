// js/services.js
/**
 * Project: DocuFlow
 * File:  services.js
 * Created: 2025-10-29 (Refactored)
 * Author: @lewopxd 
 *
 * Description:
 * Main application service (Facade).
 * This file acts as a central hub (Strategy Pattern) to decouple the UI 
 * (app.js) from the data implementation (providers).
 *
 * It imports all available providers, selects the active one based on
 * the global configuration (from config.js), and exports a unified
 * API (AppService) for the rest of the application to consume.
 */

//-------------------------------------------------------------
//-------------[   IMPORTS & CONFIGURATION   ]-----------------
//-------------------------------------------------------------

// Import the environment configuration
import { ACTIVE_ENV, ENV_MODES } from './config.js';

// Import all available service providers (Strategies)
import * as DemoProvider from './providers/demo/provider.demo.js';
import * as PythonProvider from './providers/python/provider.python.js';

//--------------------------------------> END [ IMPORTS & CONFIGURATION ... ]

//-------------------------------------------------------------
//-------------[   STRATEGY SELECTION   ]----------------------
//-------------------------------------------------------------

/**
 * @type {object}
 * Holds the selected provider implementation (the active "Strategy").
 */
let activeProvider;

/**
 * Selects the active provider based on the ACTIVE_ENV configuration.
 * Falls back to DemoProvider if the configuration is invalid.
 */
switch (ACTIVE_ENV) {
    case ENV_MODES.PYTHON:
        activeProvider = PythonProvider;
        console.log('Service Layer: Python provider active.');
        break;

    case ENV_MODES.DEMO:
        activeProvider = DemoProvider;
        console.log('Service Layer: Demo provider active.');
        break;

    default:
        console.warn(`Service Layer: Unknown environment "${ACTIVE_ENV}". Falling back to DEMO mode.`);
        activeProvider = DemoProvider;
        break;
}

//--------------------------------------> END [ STRATEGY SELECTION ... ]

//-------------------------------------------------------------
//-------------[   PUBLIC API (FACADE)   ]---------------------
//-------------------------------------------------------------

/**
 * @public
 * @namespace AppService
 * The unified, environment-agnostic API facade for the UI.
 * The UI (app.js) should *only* import and call functions from this object.
 */
export const AppService = {

    /**
     * [Requests the host system to open a file dialog.]
     * [This is an environment-agnostic function.]
     * @param {object} [options={}] - Options for the file dialog.
     * @param {Array<string>} [options.fileTypes] - e.g., ['Documentos de Word (*.docx)', 'Todos (*.*)'].
     * @returns {Promise<object>} [A promise that resolves with { filePath: '...' } or { filePath: null } if canceled.]
     */
    requestFileDialog: (options = {}) => {
        // Delegate the call to the selected provider
        return activeProvider.requestFileDialog(options);
    },

    // --- NUEVA FUNCIÓN ---
    /**
     * [Requests the structure (sheets/tables/columns) of an Excel/CSV file.]
     * [This is an environment-agnostic function.]
     * @param {string} filePath - The full path of the file to inspect.
     * @returns {Promise<object|null>} [A promise that resolves with the structured data object or null if failed.]
     */
    getExcelFileStructure: (filePath) => {
        // Delegate the call to the selected provider
        return activeProvider.getExcelFileStructure(filePath);
    },
    // --- FIN NUEVA FUNCIÓN ---

    loadSettings: () => {
        // Delegate the call to the selected provider
        return activeProvider.loadSettings();
    },

    /**
     * [Saves a single key/value pair to the persistent UI settings.]
     * @param {string} key - The key of the setting to save (e.g., "last_opened_sheet").
     * @param {*} value - The value to save (e.g., ['path/to/file.xlsx']).
     * @returns {Promise<object>} [A promise that resolves with { success: true } or rejects.]
     */
    saveUiSetting: (key, value) => {
        // Delegate the call
        return activeProvider.saveUiSetting(key, value);
    },

    /**
     * [Fetches unified structure + data in a single call.]
     * @param {string} filePath - The full path of the Excel file.
     * @returns {Promise<object|null>}
     */
    getUnifiedExcelData: (filePath) => {
        return activeProvider.getUnifiedExcelData(filePath);
    },

    /**
     * [Split API - Step 1: Get structure only (fast, for Tree)]
     * @param {string} filePath - The full path of the Excel file.
     * @returns {Promise<object|null>}
     */
    getExcelStructure: (filePath) => {
        return activeProvider.getExcelStructure(filePath);
    },

    /**
     * [Split API - Step 2: Get full row data (for ExcelViewer)]
     * @param {string} filePath - The full path of the Excel file.
     * @returns {Promise<object|null>}
     */
    getExcelFullData: (filePath) => {
        return activeProvider.getExcelFullData(filePath);
    },

    /**
     * [Get template placeholders for mapping UI]
     * @param {string} filePath - The full path of the .docx template.
     * @returns {Promise<object|null>} Placeholder data with normalized names.
     */
    getTemplatePlaceholders: (filePath) => {
        return activeProvider.getTemplatePlaceholders(filePath);
    },

    /**
     * [Get docx file data as base64 for document viewer]
     * @param {string} filePath - The full path of the .docx file.
     * @returns {Promise<object|null>} Base64 encoded file data for viewing.
     */
    getDocxFileData: (filePath) => {
        return activeProvider.getDocxFileData(filePath);
    },

    // --- PROJECT MANAGEMENT ---

    /**
     * Gets project info for startup autoload.
     * @returns {Promise<object>} Project settings (autoLoad, path, exists, autoSave).
     */
    getProjectInfo: () => {
        return activeProvider.getProjectInfo();
    },

    /**
     * Loads a project from a .bkproj file.
     * @param {string} path - Full path to the project file.
     * @returns {Promise<object>} Project data with missingFiles array.
     */
    loadProject: (path) => {
        return activeProvider.loadProject(path);
    },

    /**
     * Saves the current project.
     * @param {string} path - Path to save the project.
     * @param {object} project - Project configuration object.
     * @returns {Promise<object>} Success status.
     */
    saveProject: (path, project) => {
        return activeProvider.saveProject(path, project);
    },

    /**
     * Creates a new project.
     * @param {string} path - Path for the new project file.
     * @param {string} name - Display name for the project.
     * @returns {Promise<object>} Created project data.
     */
    newProject: (path, name) => {
        return activeProvider.newProject(path, name);
    }
};

//--------------------------------------> END [ PUBLIC API (FACADE) ... ]