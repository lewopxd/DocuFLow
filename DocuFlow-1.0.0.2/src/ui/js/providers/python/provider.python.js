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

// --- NEW ---
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

// --- NEW ---
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

//--------------------------------------> END [ PYTHON PROVIDER API ... ]