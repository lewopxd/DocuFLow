// js/lib/docx-viewer.js
/**
 * Project: DocuFlow
 * File:  lib/docx-viewer.js
 * Created: 2025-12-12
 * Author: @lewopxd
 *
 * Description:
 * Dedicated module for Word document viewing using docx-preview library.
 * Handles rendering, CSS isolation, and theme management.
 * This module is completely isolated from the main application logic.
 */

//-------------------------------------------------------------
//-------------[   MODULE STATE   ]----------------------------
//-------------------------------------------------------------

/** @type {WeakMap<HTMLElement, DocxViewerInstance>} */
const viewerInstances = new WeakMap();

/** @type {boolean} Library load status */
let libraryLoaded = false;

/** @type {Promise|null} Library loading promise */
let loadingPromise = null;

//---------------------------------------> END [ MODULE STATE ... ]


//-------------------------------------------------------------
//-------------[   LIBRARY LOADER   ]--------------------------
//-------------------------------------------------------------

/**
 * Dynamically loads the docx-preview library if not already loaded.
 * @returns {Promise<void>}
 */
async function ensureLibraryLoaded() {
    if (libraryLoaded) return;
    if (loadingPromise) return loadingPromise;

    loadingPromise = new Promise((resolve, reject) => {
        // Check if docx object already exists (library already loaded)
        if (window.docx && typeof window.docx.renderAsync === 'function') {
            libraryLoaded = true;
            resolve();
            return;
        }

        // Load JSZip first (required dependency)
        const jszipScript = document.createElement('script');
        jszipScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
        jszipScript.onload = () => {
            // Then load docx-preview
            const docxScript = document.createElement('script');
            docxScript.src = 'https://cdn.jsdelivr.net/npm/docx-preview@0.3.1/dist/docx-preview.min.js';
            docxScript.onload = () => {
                if (window.docx && typeof window.docx.renderAsync === 'function') {
                    libraryLoaded = true;
                    console.log('[DocxViewer] Library loaded successfully');
                    resolve();
                } else {
                    reject(new Error('docx-preview loaded but window.docx not available'));
                }
            };
            docxScript.onerror = () => reject(new Error('Failed to load docx-preview library'));
            document.head.appendChild(docxScript);
        };
        jszipScript.onerror = () => reject(new Error('Failed to load JSZip library'));
        document.head.appendChild(jszipScript);
    });

    return loadingPromise;
}

//---------------------------------------> END [ LIBRARY LOADER ... ]


//-------------------------------------------------------------
//-------------[   DOCX VIEWER CLASS   ]-----------------------
//-------------------------------------------------------------

/**
 * Individual viewer instance for a single document.
 */
class DocxViewerInstance {
    /**
     * @param {HTMLElement} container - The container element to render into.
     * @param {object} options - Configuration options.
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            className: 'dv',         // CSS class prefix for isolation
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            ignoreFonts: false,
            breakPages: true,
            useBase64URL: true,
            renderHeaders: true,
            renderFooters: true,
            renderFootnotes: true,
            ...options
        };
        this.isRendered = false;
        this.currentFilePath = null;
    }

    /**
     * Renders a docx file from base64 data.
     * @param {string} base64Data - Base64 encoded docx file content.
     * @param {string} filePath - Original file path (for reference).
     * @returns {Promise<void>}
     */
    async render(base64Data, filePath) {
        await ensureLibraryLoaded();

        // Clear container
        this.container.innerHTML = '';

        // Convert base64 to ArrayBuffer
        const binaryString = atob(base64Data);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        // Create wrapper for styling
        const wrapper = document.createElement('div');
        wrapper.className = 'docx-viewer-wrapper';
        this.container.appendChild(wrapper);

        try {
            await window.docx.renderAsync(bytes.buffer, wrapper, null, this.options);
            this.isRendered = true;
            this.currentFilePath = filePath;
            console.log(`[DocxViewer] Rendered: ${filePath}`);
        } catch (error) {
            console.error('[DocxViewer] Render error:', error);
            wrapper.innerHTML = `<div class="docx-viewer-error"><p>Error loading document: ${error.message}</p></div>`;
            throw error;
        }
    }

    /**
     * Shows a loading state in the container.
     */
    showLoading() {
        this.container.innerHTML = `
            <div class="docx-viewer-loading">
                <div class="loading-spinner"></div>
                <p>Loading document...</p>
            </div>
        `;
    }

    /**
     * Shows an error state in the container.
     * @param {string} message - Error message to display.
     */
    showError(message) {
        this.container.innerHTML = `
            <div class="docx-viewer-error">
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * Clears the viewer.
     */
    clear() {
        this.container.innerHTML = '';
        this.isRendered = false;
        this.currentFilePath = null;
    }
}

//---------------------------------------> END [ DOCX VIEWER CLASS ... ]


//-------------------------------------------------------------
//-------------[   PUBLIC API   ]------------------------------
//-------------------------------------------------------------

/**
 * Creates or retrieves a DocxViewer instance for a container.
 * @param {HTMLElement} container - The container element.
 * @param {object} options - Configuration options.
 * @returns {DocxViewerInstance}
 */
export function createViewer(container, options = {}) {
    let instance = viewerInstances.get(container);
    if (!instance) {
        instance = new DocxViewerInstance(container, options);
        viewerInstances.set(container, instance);
    }
    return instance;
}

/**
 * Gets an existing viewer instance.
 * @param {HTMLElement} container - The container element.
 * @returns {DocxViewerInstance|null}
 */
export function getViewer(container) {
    return viewerInstances.get(container) || null;
}

/**
 * Destroys a viewer instance.
 * @param {HTMLElement} container - The container element.
 */
export function destroyViewer(container) {
    const instance = viewerInstances.get(container);
    if (instance) {
        instance.clear();
        viewerInstances.delete(container);
    }
}

/**
 * Preloads the docx-preview library.
 * Call this early to avoid delay when first document is opened.
 * @returns {Promise<void>}
 */
export async function preloadLibrary() {
    return ensureLibraryLoaded();
}

//---------------------------------------> END [ PUBLIC API ... ]
