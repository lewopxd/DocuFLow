// js/providers/python/provider.python.js
/**
 * Project: DocuFlow
 * File:  provider.python.js
 * Created: 2025-10-29 (Refactored)
 * Author: @lewopxd 
 *
 * Description:
 * Python-specific service provider.
 * This module implements the standard AppService interface by translating
 * generic function calls into specific window.bridgePy.send messages
 * for the pywebview backend.
 */

//-------------------------------------------------------------
//-------------[   PYTHON PROVIDER API   ]---------------------
//-------------------------------------------------------------

/**
 * [Requests the Python backend to open a file dialog.]
 * [This is the specific implementation for the 'PYTHON' environment.]
 *
 * @param {object} [options={}] - Options for the file dialog.
 * @param {Array<string>} [options.fileTypes] - e.g., ['Documentos de Word (*.docx)', 'Todos (*.*)'].
 * @returns {Promise<object>} [A promise that resolves with { filePath: '...' } or { filePath: null } if canceled.]
 */
export function requestFileDialog(options = {}) {

    // 1. Prepare the payload for the Python backend.
    // The Python handler _handle_open_file_dialog expects a dictionary
    // with the key 'file_types'.
    const content = {
        file_types: options.fileTypes || ['All files (*.*)', '*.*']
    };

    // 2. Call the bridge.
    // We assume window.bridgePy is globally available.
    // We send the specific message 'open_file_dialog' that the
    // Python BridgeAPI is registered to handle.
    return window.bridgePy.send('open_file_dialog', content);
}


/**
 * [Loads the persistent UI settings from the Python backend.]
 * [Calls the 'get_ui_settings' handler in main.py.]
 *
 * @returns {Promise<object>} [A promise that resolves with the UI settings object (e.g., { theme, last_opened_sheet: [] }).]
 */
export function loadSettings() {
    // Send the message 'get_ui_settings' defined in main.py.
    // No content is needed for this call.
    return window.bridgePy.send('get_ui_settings', {});
}


/**
 * [Saves a single key/value pair to the persistent UI settings via Python.]
 * [Calls the 'save_ui_setting' handler in main.py.]
 *
 * @param {string} key - The key of the setting to save (e.g., "last_opened_sheet").
 * @param {*} value - The value to save (e.g., ['path/to/file.xlsx']).
 * @returns {Promise<object>} [A promise that resolves with { success: true }.]
 */
export function saveUiSetting(key, value) {
    // Prepare the payload for the Python handler
    // _handle_save_ui_setting expects { key, value }.
    const content = {
        key: key,
        value: value
    };

    return window.bridgePy.send('save_ui_setting', content);
}

// --- [ NUEVA FUNCIÓN AÑADIDA ] ---
/**
 * [Requests the Python backend to read and parse an Excel file structure.]
 * [Calls the 'get_excel_structure' handler in main.py.]
 *
 * @param {string} filePath - The full path of the file to inspect.
 * @returns {Promise<object|null>} [A promise that resolves with the file structure object, or null if parsing failed.]
 */
export function getExcelFileStructure(filePath) {
    // Prepare the payload for the Python handler
    // _handle_get_excel_structure expects { filePath }.
    const content = {
        filePath: filePath
    };

    // Send the message 'get_excel_structure' defined in main.py.
    return window.bridgePy.send('get_excel_structure', content);
}
// --- [ FIN DE LA NUEVA FUNCIÓN ] ---

// --- [ NUEVA FUNCIÓN (DATA) ] ---
/**
 * [Requests the Python backend to read specific rows.]
 * @param {object} config - Configuration object.
 * @returns {Promise<Array<object>|null>}
 */
export function getExcelSheetData(config) {
    // Send the message 'get_excel_sheet_data' defined in main.py.
    return window.bridgePy.send('get_excel_sheet_data', config);
}

/**
 * [Requests the Python backend to read and unify data from an Excel file.]
 * @param {string} filePath - The full path of the Excel file.
 * @returns {Promise<object|null>} [A promise that resolves with the unified data object, or null if an error occurred.]
 */
export function getUnifiedExcelData(filePath) {
    return window.bridgePy.send('get_unified_excel_data', { filePath: filePath });
}
// --- [ FIN DE LA NUEVA FUNCIÓN (DATA) ] ---

/**
 * [Split API - Step 1: Get structure only (fast, for Tree)]
 * @param {string} filePath - The full path of the Excel file.
 * @returns {Promise<object|null>} Structure data for tree rendering.
 */
export function getExcelStructure(filePath) {
    return window.bridgePy.send('get_excel_structure', { filePath: filePath });
}

/**
 * [Split API - Step 2: Get full row data (for ExcelViewer)]
 * @param {string} filePath - The full path of the Excel file.
 * @returns {Promise<object|null>} Full serialized row data.
 */
export function getExcelFullData(filePath) {
    return window.bridgePy.send('get_excel_full_data', { filePath: filePath });
}

// --- [ TEMPLATE PLACEHOLDERS API ] ---

// Default placeholder definitions
const DEFAULT_PLACEHOLDER_DEFINITIONS = [
    { type: 'text', prefix: '{{', suffix: '}}' },
    { type: 'image', prefix: '$IMG{{', suffix: '}}' }
];

/**
 * [Requests the Python backend to parse a Word template and extract placeholders.]
 * @param {string} filePath - The full path of the .docx template file.
 * @param {Array} definitions - Optional custom definitions. Uses defaults if not provided.
 * @returns {Promise<object|null>} Placeholder data for mapping UI.
 */
export function getTemplatePlaceholders(filePath, definitions = null) {
    return window.bridgePy.send('get_template_placeholders', {
        source_path: filePath,
        definitions: definitions || DEFAULT_PLACEHOLDER_DEFINITIONS
    });
}
// --- [ END TEMPLATE PLACEHOLDERS API ] ---

// --- [ DOCUMENT VIEWER API ] ---

/**
 * [Requests the Python backend to send a docx file as base64 for viewing.]
 * @param {string} filePath - The full path of the .docx file.
 * @returns {Promise<object|null>} Base64 encoded file data for viewing.
 */
export function getDocxFileData(filePath) {
    return window.bridgePy.send('get_docx_file_data', {
        filePath: filePath
    });
}
// --- [ END DOCUMENT VIEWER API ] ---

// --- [ PROJECT MANAGEMENT API ] ---

/**
 * Gets project info for startup (autoLoad, lastPath, etc.)
 * @returns {Promise<object>} Project info with autoLoad, path, exists, autoSave settings.
 */
export function getProjectInfo() {
    return window.bridgePy.send('get_project_info', {});
}

/**
 * Loads a project from a .bkproj file.
 * @param {string} path - Full path to the .bkproj file.
 * @returns {Promise<object>} Project data with missingFiles array.
 */
export function loadProject(path) {
    return window.bridgePy.send('load_project', { path: path });
}

/**
 * Saves the current project state.
 * @param {string} path - Path to save the project.
 * @param {object} project - Project configuration object.
 * @returns {Promise<object>} Success status.
 */
export function saveProject(path, project) {
    return window.bridgePy.send('save_project', { path: path, project: project });
}

/**
 * Creates a new project file.
 * @param {string} path - Path for the new project.
 * @param {string} name - Display name for the project.
 * @returns {Promise<object>} Created project data.
 */
export function newProject(path, name) {
    return window.bridgePy.send('new_project', { path: path, name: name });
}

// --- [ END PROJECT MANAGEMENT API ] ---

//-------------------------------> END [ PYTHON PROVIDER API ... ]