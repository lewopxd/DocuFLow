// js/config.js
/**
 * Project: DocuFlow
 * File:  config.js
 * Created: 2025-10-29
 * Author: @lewopxd 
 *
 * Description:
 * Global application configuration file.
 * Defines the operating mode (e.g., Python, Demo)
 * for the entire frontend application.
 */

//-------------------------------------------------------------
//-------------[   ENVIRONMENT MODES   ]-----------------------
//-------------------------------------------------------------

/**
 * @public
 * @enum {string}
 * @namespace ENV_MODES
 * Defines the available service provider environments.
 * Using an object as an Enum prevents magic strings and typos.
 */
export const ENV_MODES = {
    /** Connects to the live pywebview backend. */
    PYTHON: 'python',
    
    /** Runs in a sandboxed mode with mock data, no backend required. */
    DEMO: 'demo',

    /** Future placeholder for a cloud-based provider. */
    // CLOUD: 'cloud' 
};

//--------------------------------------> END [ ENVIRONMENT MODES ... ]

//-------------------------------------------------------------
//-------------[   ACTIVE ENVIRONMENT   ]----------------------
//-------------------------------------------------------------

/**
 * @public
 * @type {string}
 * The master switch that controls the application's data source.
 * Change this value to toggle between providers.
 *
 * @example
 * export const ACTIVE_ENV = ENV_MODES.PYTHON; // For production
 * export const ACTIVE_ENV = ENV_MODES.DEMO;   // For UI dev/testing
 */
export const ACTIVE_ENV = ENV_MODES.PYTHON;

//--------------------------------------> END [ ACTIVE ENVIRONMENT ... ]