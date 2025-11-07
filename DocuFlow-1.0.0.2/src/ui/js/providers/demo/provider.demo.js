// js/providers/demo/provider.demo.js
/**
 * Project: DocuFlow
 * File:  provider.demo.js
 * Created: 2025-10-29 (Refactored)
 * Author: @lewopxd 
 *
 * Description:
 * Intelligent Demo (mock) service provider.
 * This module implements the AppService interface by fetching and
 * returning sequential, cyclical mock data from demo-data.json.
 */

//-------------------------------------------------------------
//-------------[   DATA LOADING (SINGLETON)   ]----------------
//-------------------------------------------------------------

/**
 * @private
 * A promise that resolves with the content of demo-data.json.
 * This "singleton" pattern ensures we only fetch the file once.
 */
let demoDataPromise = null;

/**
 * @private
 * [Fetches and returns the mock data store, caching the promise.]
 * @returns {Promise<object>} [A promise that resolves to the parsed demo-data.json object]
 */
function getDemoData() {
    if (demoDataPromise) {
        return demoDataPromise;
    }

    console.log('DEMO PROVIDER: Fetching demo-data.json for the first time...');
    
    // Path is relative to the index.html file that loads the script
    demoDataPromise = fetch('./js/providers/demo/demo-data.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(err => {
            console.error("CRITICAL DEMO ERROR: Could not load demo-data.json.", err);
            // Fallback
            return {
                providerData: { paths: [], sheets: [], docs: [], fileStructures: {} },
                uiData: { theme: "dark", language: "es", last_opened_sheet: [], last_opened_template: [] }
            };
        });
    
    return demoDataPromise;
}

//--------------------------------------> END [ DATA LOADING (SINGLETON) ... ]

//-------------------------------------------------------------
//-------------[   SEQUENTIAL STATE   ]------------------------
//-------------------------------------------------------------

/**
 * @private
 * Module-level counters for cyclical, predictable demo data.
 */
let currentPathIndex = 0;
let currentSheetIndex = 0;
let currentDocIndex = 0;

//--------------------------------------> END [ SEQUENTIAL STATE ... ]


//-------------------------------------------------------------
//-------------[   PRIVATE UTILITIES   ]-----------------------
//-------------------------------------------------------------

// --- (No private utilities in this simplified file) ---

//--------------------------------------> END [ PRIVATE UTILITIES ... ]

//-------------------------------------------------------------
//-------------[   DEMO PROVIDER API   ]-----------------------
//-------------------------------------------------------------

/**
 * [Simulates opening a file dialog sequentially.]
 * [This implementation inspects options.fileTypes to return the
 * *next* relevant mock file type from the list.]
 *
 * @param {object} [options={}] - Options passed from the UI (e.g., fileTypes).
 * @param {Array<string>} [options.fileTypes] - e.g., ['Spreadsheets (*.xlsx...)']
 * @returns {Promise<object>} [A promise that resolves with a sequential mock file path.]
 */
export async function requestFileDialog(options = {}) {
    
    console.log('DEMO PROVIDER: Received sequential request with options:', options);

    const demoDataStore = await getDemoData();
    const { paths, sheets, docs } = demoDataStore.providerData;

    // Simulate a network/user delay
    const delay = 200; // Shorter delay now
    
    return new Promise((resolve) => {
        setTimeout(() => {
            
            // 1. Get the next path sequentially
            // Aseguramos que solo usamos el primer path que es el único definido ahora.
            const sequentialPath = paths[0]; 
            currentPathIndex = 0; // Se mantiene fijo si solo hay uno
            
            let sequentialFile;
            const optionsString = JSON.stringify(options.fileTypes);

            // 2. Get the next file based on type
            if (optionsString && optionsString.includes('Spreadsheets')) {
                console.log(`DEMO PROVIDER: Serving sheet index ${currentSheetIndex}`);
                sequentialFile = sheets[currentSheetIndex];
                currentSheetIndex = (currentSheetIndex + 1) % sheets.length; // Loop back
            
            } else if (optionsString && optionsString.includes('Word Documents')) {
                console.log(`DEMO PROVIDER: Serving doc index ${currentDocIndex}`);
                sequentialFile = docs[currentDocIndex];
                currentDocIndex = (currentDocIndex + 1) % docs.length; // Loop back
            
            } else {
                // Fallback (should not happen with current UI)
                console.warn('DEMO PROVIDER: Unknown file type requested, serving sheet.');
                sequentialFile = sheets[currentSheetIndex];
                currentSheetIndex = (currentSheetIndex + 1) % sheets.length;
            }

            const fullMockPath = sequentialPath + sequentialFile;
            
            const mockResponse = {
                filePath: fullMockPath
            };
            
            console.log('DEMO PROVIDER: Resolved with sequential mock path.', mockResponse);
            resolve(mockResponse);

        }, delay);
    });
}

/**
 * [Simulates loading the persistent UI settings from demo-data.json.]
 * [Returns a mock UI object matching the structure in storage.py.]
 *
 * @returns {Promise<object>} [A promise that resolves with the mock UI settings object.]
 */
export async function loadSettings() {
    console.log('DEMO PROVIDER: Simulating settings load from demo-data.json...');
    
    const demoDataStore = await getDemoData();

    const delay = 100; 

    return new Promise((resolve) => {
        setTimeout(() => {
            const mockSettings = JSON.parse(JSON.stringify(demoDataStore.uiData));
            console.log('DEMO PROVIDER: Resolved with mock settings.', mockSettings);
            resolve(mockSettings);
        }, delay);
    });
}

/**
 * [Simulates saving a single key/value pair.]
 * [Logs the action to the console and resolves. Does NOT persist data.]
 *
 * @param {string} key - The key of the setting to save (e.g., "last_opened_sheet").
 * @param {*} value - The value to save (e.g., ['path/to/file.xlsx']).
 * @returns {Promise<object>} [A promise that resolves with { success: true }.]
 */
export function saveUiSetting(key, value) {
    
    console.warn(`DEMO PROVIDER: saveUiSetting call received (Persistence is skipped in DEMO mode).`);
    console.log(`  > Key to save:   ${key}`);
    console.log(`  > Value to save:`, value);
    
    return Promise.resolve({ success: true });
}

/**
 * [Simulates reading the complex structure (sheets, tables, columns) of an Excel file.]
 * [This is a mock implementation that fetches the structure from fileStructures in demo-data.json.]
 * * @param {string} filePath - The full path of the file to inspect.
 * @returns {Promise<object|null>} [A promise that resolves with the structured data object or null if not found.]
 */
export async function getExcelFileStructure(filePath) {
    
    console.log(`DEMO PROVIDER: Simulating reading structure for: ${filePath}`);

    const demoDataStore = await getDemoData();
    // Extraer el nombre del archivo de la ruta completa (ej. 'Sales_Report_Q3_2025.xlsx')
    const fileName = filePath.split(/[\\/]/).pop();
    
    // Acceder a la estructura dentro de providerData.fileStructures
    const structuredData = demoDataStore.providerData.fileStructures[fileName];

    const delay = 300; // Simular un retardo típico de lectura de archivo/red
    
    return new Promise((resolve) => {
        setTimeout(() => {
            if (structuredData) {
                console.log(`DEMO PROVIDER: Found structure for ${fileName}.`);
                resolve(structuredData);
            } else {
                console.warn(`DEMO PROVIDER: Structure not found for ${fileName}.`);
                // Devolver una estructura vacía si no se encuentra (para evitar fallos en el frontend)
                resolve(null);
            }
        }, delay);
    });
}

//--------------------------------------> END [ DEMO PROVIDER API ... ]