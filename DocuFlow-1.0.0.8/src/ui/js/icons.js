// js/icons.js
/**
 * Project: DocuFlow
 * File:  icons.js
 * Created: 2025-10-29
 * Author: @lewopxd
 *
 * Description:
 * Centralized module for storing all application SVG icons
 * as string constants for dynamic injection.
 */

//-------------------------------------------------------------
//-------------[   TOOLBAR ICONS   ]---------------------------
//-------------------------------------------------------------

/**
 * @const {string}
 * Icon for loading data sheets (Excel, CSV).
 * Used in: #load-sheet-button
 */
export const ICON_SHEET = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
    <polyline points="10 9 9 9 8 9"></polyline>
</svg>`;

/**
 * @const {string}
 * Icon for loading templates (Word).
 * Used in: #load-template-button
 */
export const ICON_TEMPLATE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="12" y1="18" x2="12" y2="12"></line>
    <line x1="9" y1="15" x2="15" y2="15"></line>
</svg>`;

/**
 * @const {string}
 * Icon for adding a new file (replaces sheet/template icons).
 * Used in: #load-sheet-button, #load-template-button
 */
export const ICON_PLUS = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
</svg>`;

/**
 * @const {string}
 * Icon for closing tabs.
 * Used in: .tab-close
 */
export const ICON_CLOSE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
</svg>`;

/**
 * @const {string}
 * Icon for reloading data.
 * Used in: .icon-button (Reload)
 */
export const ICON_RELOAD = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M23 4v6h-6"></path>
    <path d="M1 20v-6h6"></path>
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
</svg>`;

/**
 * @const {string}
 * Icon for Grid Layout view.
 * Used in: .icon-button (Toggle View)
 */
export const ICON_LAYOUT_GRID = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="3" width="7" height="7"></rect>
    <rect x="14" y="3" width="7" height="7"></rect>
    <rect x="14" y="14" width="7" height="7"></rect>
    <rect x="3" y="14" width="7" height="7"></rect>
</svg>`;

/**
 * @const {string}
 * Icon for Tree Layout view.
 * Used in: .icon-button (Toggle View State)
 */
export const ICON_LAYOUT_TREE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="21" y1="10" x2="3" y2="10"></line>
    <line x1="21" y1="6" x2="3" y2="6"></line>
    <line x1="21" y1="14" x2="3" y2="14"></line>
    <line x1="21" y1="18" x2="3" y2="18"></line>
</svg>`;


//---------------------------------------> END [ TOOLBAR ICONS ... ]

//-------------------------------------------------------------
//-------------[   FILE TYPE ICONS   ]-------------------------
//-------------------------------------------------------------

/**
 * @const {string}
 * Icon for Spreadsheet tabs (Excel, CSV).
 * Used in: .tab-icon (Data Panel)
 */
export const ICON_FILE_SHEET = `<svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="100" height="100" viewBox="0 0 30 30">
<path d="M 15 3 A 2 2 0 0 0 14.599609 3.0429688 L 14.597656 3.0410156 L 4.6289062 5.0351562 L 4.6269531 5.0371094 A 2 2 0 0 0 3 7 L 3 23 A 2 2 0 0 0 4.6289062 24.964844 L 14.597656 26.958984 A 2 2 0 0 0 15 27 A 2 2 0 0 0 17 25 L 17 5 A 2 2 0 0 0 15 3 z M 19 5 L 19 8 L 21 8 L 21 10 L 19 10 L 19 12 L 21 12 L 21 14 L 19 14 L 19 16 L 21 16 L 21 18 L 19 18 L 19 20 L 21 20 L 21 22 L 19 22 L 19 25 L 25 25 C 26.105 25 27 24.105 27 23 L 27 7 C 27 5.895 26.105 5 25 5 L 19 5 z M 23 8 L 24 8 C 24.552 8 25 8.448 25 9 C 25 9.552 24.552 10 24 10 L 23 10 L 23 8 z M 6.1855469 10 L 8.5878906 10 L 9.8320312 12.990234 C 9.9330313 13.234234 10.013797 13.516891 10.091797 13.837891 L 10.125 13.837891 C 10.17 13.644891 10.258531 13.351797 10.394531 12.966797 L 11.785156 10 L 13.972656 10 L 11.359375 14.955078 L 14.050781 19.998047 L 11.716797 19.998047 L 10.212891 16.740234 C 10.155891 16.625234 10.089203 16.393266 10.033203 16.072266 L 10.011719 16.072266 C 9.9777187 16.226266 9.9105937 16.458578 9.8085938 16.767578 L 8.2949219 20 L 5.9492188 20 L 8.7324219 14.994141 L 6.1855469 10 z M 23 12 L 24 12 C 24.552 12 25 12.448 25 13 C 25 13.552 24.552 14 24 14 L 23 14 L 23 12 z M 23 16 L 24 16 C 24.552 16 25 16.448 25 17 C 25 17.552 24.552 18 24 18 L 23 18 L 23 16 z M 23 20 L 24 20 C 24.552 20 25 20.448 25 21 C 25 21.552 24.552 22 24 22 L 23 22 L 23 20 z"></path>
</svg>`;

/**
 * @const {string}
 * Icon for Document tabs (Word).
 * Used in: .tab-icon (Templates Panel)
 */
export const ICON_FILE_TEMPLATE = `<svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" width="100" height="100" viewBox="0 0 30 30">
    <path d="M 15 3 A 2 2 0 0 0 14.599609 3.0429688 L 14.597656 3.0410156 L 4.6601562 5.0292969 L 4.6289062 5.0351562 L 4.6269531 5.0371094 A 2 2 0 0 0 3 7 L 3 23 A 2 2 0 0 0 4.6289062 24.964844 L 14.589844 26.957031 L 14.597656 26.958984 A 2 2 0 0 0 15 27 A 2 2 0 0 0 17 25 L 17 5 A 2 2 0 0 0 15 3 z M 19 5 L 19 8 L 23 8 C 23.552 8 24 8.448 24 9 C 24 9.552 23.552 10 23 10 L 19 10 L 19 12 L 23 12 C 23.552 12 24 12.448 24 13 C 24 13.552 23.552 14 23 14 L 19 14 L 19 16 L 23 16 C 23.552 16 24 16.448 24 17 C 24 17.552 23.552 18 23 18 L 19 18 L 19 20 L 23 20 C 23.552 20 24 20.448 24 21 C 24 21.552 23.552 22 23 22 L 19 22 L 19 25 L 25 25 C 26.105 25 27 24.105 27 23 L 27 7 C 27 5.895 26.105 5 25 5 L 19 5 z M 5.2636719 10 L 7.1230469 10 L 8.0625 16.632812 L 8.1503906 16.632812 L 9.2773438 10 L 10.712891 10 L 11.880859 16.632812 L 11.96875 16.632812 L 12.890625 10 L 14.736328 10 L 12.896484 20 L 11.216797 20 L 10.039062 13.873047 L 9.9511719 13.873047 L 8.7949219 20 L 7.1035156 20 L 5.2636719 10 z"></path>
</svg>`;

//---------------------------------------> END [ FILE TYPE ICONS ... ]

//-------------------------------------------------------------
//-------------[   MODULE/WINDOW ICONS   ]---------------------
//-------------------------------------------------------------

/**
 * @const {string}
 * Icon for the Data Panel's title bar.
 * (Represents a table/grid)
 */
export const ICON_WINDOW_DATA = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
    <line x1="3" y1="9" x2="21" y2="9"></line>
    <line x1="9" y1="3" x2="9" y2="21"></line>
</svg>`;

/**
 * @const {string}
 * Icon for the Templates Panel's title bar.
 * (Represents a document with template/variable braces)
 */
export const ICON_WINDOW_TEMPLATES = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <polyline points="9 13 10 14 9 15"></polyline>
    <polyline points="15 13 14 14 15 15"></polyline>
</svg>`;

/**
 * @const {string}
 * Icon for collapsing a module window (Arrow Up).
 */
export const ICON_CHEVRON_UP = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="18 15 12 9 6 15"></polyline>
</svg>`;

/**
 * @const {string}
 * Icon for expanding a module window (Arrow Down).
 */
export const ICON_CHEVRON_DOWN = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="6 9 12 15 18 9"></polyline>
</svg>`;

/**
 * @const {string}
 * Icon for List Layout view.
 * Used in: .icon-button (Toggle View in Templates Panel)
 */
export const ICON_LAYOUT_LIST = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="8" y1="6" x2="21" y2="6"></line>
    <line x1="8" y1="12" x2="21" y2="12"></line>
    <line x1="8" y1="18" x2="21" y2="18"></line>
    <line x1="3" y1="6" x2="3.01" y2="6"></line>
    <line x1="3" y1="12" x2="3.01" y2="12"></line>
    <line x1="3" y1="18" x2="3.01" y2="18"></line>
</svg>`;

/**
 * @const {string}
 * Icon for Document Layout view.
 * Used in: .icon-button (Toggle View in Templates Panel)
 */
export const ICON_LAYOUT_DOC = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
</svg>`;

//---------------------------------------> END [ MODULE/WINDOW ICONS ... ]