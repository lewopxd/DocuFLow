// js/pntn.tree.js
/**
 * Project: Paneton Framework
 * File: pntn.tree.js
 * Created: 2025-09-17
 * Author: @lewopxd
 *
 * Description:
 * A modern, powerful, and efficient hierarchical tree component with high-performance
 * virtual rendering engine for massive datasets. It is self-contained, themable, and
 * provides a rich API for programmatic control while maintaining 1:1 visual parity.
 * 
 * Features intelligent icon engine with multi-layer caching, support for multiple
 * content sources (SVG, URLs, emojis, presets), smart resource management, and
 * accessibility compliance.
 */

window.Paneton = window.Paneton || {};

Paneton.Tree = class {

    //-------------------------------------------------------------
    //-------------[   CLASS STRUCTURE   ]-------------------------
    //-------------------------------------------------------------

    /**
     * Default button icon (replaces the cube icon).
     * @type {string}
     * @static
     */
    static DEFAULT_BUTTON_ICON = `<svg  xmlns="http://www.w3.org/2000/svg"  width="24"  height="24"  viewBox="0 0 24 24"  fill="none"  stroke="currentColor"  stroke-width="1"  stroke-linecap="round"  stroke-linejoin="round"  class="icon icon-tabler icons-tabler-outline icon-tabler-square"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M3 3m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z" /></svg>`;

    /**
     * Icon shown when a button icon is not found.
     * @type {string}
     * @static
     */
    static MISSING_BUTTON_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg>`;

    /**
     * Button icon collection for common UI actions with state variations.
     * @type {object}
     * @static
     */
    static BUTTON_ICONS = {
        // Dual state icons
        visibility: {
            on: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
            off: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>'
        },


    };

    /**
     * Static getter for plug-and-play button icon access.
     * Usage: tree.icon.checkBox.on, tree.icon.play.off, tree.icon.close
     * @type {object}
     * @static
     */
    static get icon() {
        // Create a proxy to handle dynamic access
        return new Proxy(this.BUTTON_ICONS, {
            get(target, prop) {
                if (target.hasOwnProperty(prop)) {
                    const iconData = target[prop];
                    // If it's a dual-state icon (has on/off), return the object
                    if (typeof iconData === 'object' && iconData.on && iconData.off) {
                        return iconData;
                    }
                    // If it's a single icon string, return it directly
                    return iconData;
                }
                console.warn(`Button icon "${prop}" not found in Paneton.Tree.icon`);
                return Paneton.Tree.MISSING_BUTTON_ICON;
            }
        });
    }

    /**
     * Built-in icon sets for various use cases.
     * @type {object}
     * @static
     */
    static ICON_SETS = {
        files: {
            // Base icons (keys with _)
            _folder: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M5 4h4l3 3h7a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2" /></svg>',

            _folderOpen: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M5 19l2.757 -7.351a1 1 0 0 1 .936 -.649h12.307a1 1 0 0 1 .986 1.164l-.996 5.211a2 2 0 0 1 -1.964 1.625h-14.026a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2h4l3 3h7a2 2 0 0 1 2 2v2" /></svg>',

            _file: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M14 3v4a1 1 0 0 0 1 1h4" /><path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z" /></svg>',

            // File type specific icons
        }
    };

    /**
     * Creates an instance of the Tree component.
     * @param {string|HTMLElement} target - A CSS selector or DOM element where the tree will be rendered.
     * @param {object} [options={}] - Configuration options for the tree.
     */
    constructor(target, options = {}) {
        this.container = typeof target === 'string' ? document.querySelector(target) : target;
        if (!this.container) {
            throw new Error(`Paneton.Tree: The container "${target}" was not found.`);
        }

        const userOptions = options || {};
        this.options = {
            data: userOptions.data || [],
            theme: userOptions.theme || {},
            tree: {
                sortNodes: true,
                compactFolders: false,
                showSegments: true,
                compactDensity: false,
                toggleOnRowClick: false,
                ...(userOptions.tree || {})
            },
            node: {
                content: {
                    showIconForBranches: true,
                    showIconForLeaves: true,
                    iconSet: 'files',
                    sourcePolicy: 'customAndPreset',
                    dynamicFolderIcons: true,
                    ...(userOptions.node?.content || {})
                },
                actions: {
                    visibility: 'always', // 'always' | 'onFocusNode' | 'onFocusTree'
                    ...(userOptions.node?.actions || {})
                },
                // toggler: { ... } // Futuro
            },
            iconEngine: {
                sanitize: true,
                cacheTimeout: 300000,
                maxCacheSize: 1000,
                fallbackIcon: null,
                loadingIcon: '⏳',
                ...(userOptions.iconEngine || {})
            }
        };

        this.state = {
            maxButtons: 0,
            nodesByPath: new Map(),
            renderableTree: [],
            flatVisibleList: [],
            domPool: [],
            rowHeight: 0, // Will be measured
            totalPoolSize: 0,
            scrollTop: 0,
            viewportHeight: 0,
            maxIndentDepth: 0,
            activeNode: { path: null, depth: -1 },
            mousePosition: { x: -1, y: -1 },
        };

        // Icon engine state
        this._iconCache = new Map();
        this._resourceCache = new Map();
        this._nodeIconCache = new WeakMap();
        this._pendingRequests = new Map();

        this._isDirty = false;
        this._renderScheduled = false;
        this._scrollThrottled = false;
        this._scrollEndTimer = null;

        this.id = `pntn-tree-${Date.now()}${Math.random().toString(36).substring(2, 9)}`;
        this._boundHandleClick = this._handleContainerClick.bind(this);
        this._boundHandleScroll = this._handleScroll.bind(this);
        this._boundHandleMouseMove = this._handleMouseMove.bind(this);
        this._boundHandleMouseLeave = this._handleMouseLeave.bind(this);

        this.init();
    }

    //--------------------------------------> END [ CLASS STRUCTURE ... ]


    //-------------------------------------------------------------
    //-------------[   PUBLIC API   ]------------------------------
    //-------------------------------------------------------------

    /**
     * Initializes the tree component: computes state, injects styles,
     * builds the virtual DOM structure and pool, and sets up event listeners.
     */
    init() {
        this._computeRenderState();
        this.state.maxButtons = this._findMaxButtons(this.state.renderableTree);
        this.state.maxIndentDepth = this._findMaxDepth(this.state.renderableTree);

        this._injectStyles();
        this._renderInitialView();
        this._createAndMeasurePool();
        this._setupEventListeners();
        this._setupCustomScrollbar();

        // Start cache cleanup timer
        this._startCacheCleanupTimer();

        // Initial render
        this._virtualRender();
    }

    /**
     * Finds a node by its full path and returns an API object to manipulate it.
     * @param {string} path - The complete path of the node (e.g., 'Scene/Robot/Head').
     * @returns {object|null} An API object for the node or null if not found.
     */
    findNode(path) {
        const nodeProxy = this.state.nodesByPath.get(path);
        if (!nodeProxy) {
            console.warn(`Paneton.Tree: Node with path not found: ${path}`);
            return null;
        }

        // Find the element in the current DOM pool if rendered
        const renderedElement = this.state.domPool.find(el =>
            el.style.display !== 'none' && el.dataset.path === path
        ) || null;

        return {
            get data() { return nodeProxy.data; },
            get element() { return renderedElement; },
            get path() { return path; },
            select: () => this._selectNode(path),
            expand: () => { if (nodeProxy.data.children) this._toggleNode(nodeProxy, true); },
            collapse: () => { if (nodeProxy.data.children) this._toggleNode(nodeProxy, false); },
            reveal: () => this.revealNode(path)
        };
    }

    /**
     * Programmatically scrolls the tree to make a node visible and selects it.
     * @param {string} path - The complete path of the node to reveal.
     * @returns {Promise<HTMLElement|null>} A promise that resolves with the node's element.
     */
    revealNode(path) {
        return new Promise(resolve => {
            // Find node in flat list
            const nodeIndex = this.state.flatVisibleList.findIndex(item => item.path === path);

            if (nodeIndex === -1) {
                console.warn(`Paneton.Tree: Cannot reveal node. Path not found or node is not visible: ${path}`);
                resolve(null);
                return;
            }

            // Scroll to make node visible
            const targetScrollTop = nodeIndex * this.state.rowHeight;
            this.viewport.scrollTop = targetScrollTop;

            // Wait for next frame to ensure rendering
            requestAnimationFrame(() => {
                const api = this.findNode(path);
                if (api && api.element) {
                    this._selectNode(path);
                }
                resolve(api ? api.element : null);
            });
        });
    }

    /**
     * Adds one or more nodes to the tree at a specified parent path.
     * @param {object|Array<object>} nodeOrNodes - A single node object or an array of nodes to add.
     * @param {object} [options={}] - Options for the add operation.
     * @param {string|null} [options.parentPath=null] - The path of the parent to add nodes to.
     */
    add(nodeOrNodes, options = {}) {
        const { parentPath = null } = options;
        const nodesToAdd = Array.isArray(nodeOrNodes) ? nodeOrNodes : [nodeOrNodes];
        if (nodesToAdd.length === 0) return;

        let parentNodeList;

        if (parentPath) {
            const parent = this._findNodeInDataByPath(parentPath);
            if (!parent) {
                console.warn(`Paneton.Tree: Parent node with path "${parentPath}" not found.`);
                return;
            }
            parent.children = parent.children || [];
            parentNodeList = parent.children;
        } else {
            parentNodeList = this.options.data;
        }

        parentNodeList.push(...nodesToAdd);
        this._isDirty = true;
        this._scheduleRender();
    }

    /**
     * Completely removes the tree instance, its styles, and all event listeners from the DOM.
     */
    destroy() {
        // Stop cache cleanup timer
        this._stopCacheCleanupTimer();

        // Clear caches
        this._iconCache.clear();
        this._resourceCache.clear();
        this._nodeIconCache = new WeakMap();
        this._pendingRequests.clear();

        if (this.styleElement) this.styleElement.remove();
        if (this.container) {
            this.container.removeEventListener('click', this._boundHandleClick);
            this.container.removeEventListener('mousemove', this._boundHandleMouseMove);
            this.container.removeEventListener('mouseleave', this._boundHandleMouseLeave);
            if (this.viewport) {
                this.viewport.removeEventListener('scroll', this._boundHandleScroll);
            }
            this.container.innerHTML = '';
            this.container.removeAttribute('data-paneton-tree');
            this.container.removeAttribute('data-paneton-tree-id');
            this.container.removeAttribute('style');
        }
        this.state.nodesByPath.clear();
        this.state.domPool = [];
    }

    //--------------------------------------> END [ PUBLIC API ... ]


    //-------------------------------------------------------------
    //-------------[   ICON ENGINE CORE   ]-----------------------
    //-------------------------------------------------------------

    /**
    * Universal icon processor - takes any icon source string, processes it, and returns HTML.
    * @param {string} iconSource - The icon source (SVG, URL, Emoji, or Preset key).
    * @param {object} [context={}] - Optional context for preset icons.
    * @param {boolean} [context.hasChildren] - Node type context.
    * @param {boolean} [context.isExpanded] - Node state context.
    * @returns {Promise<string|null>} The processed icon HTML.
    * @private
    */
    async _processIconSource(iconSource, context = {}) {

        
        if (!iconSource) return null;

        const { hasChildren = false, isExpanded = false } = context;

        // 1. Generate cache key
        const cacheKey = this._generateCacheKey(
            iconSource,
            hasChildren ? 'branch' : 'leaf',
            isExpanded
        );

        // 2. Check primary cache
        const cached = this._iconCache.get(cacheKey);
        if (cached && !this._isCacheExpired(cached)) {
            return cached.html;
        }

        // 3. Process based on resource type
        let processedHtml;
        try {
            if (this._isUrl(iconSource)) {
                processedHtml = await this._processRemoteIcon(iconSource, cacheKey);
            } else if (this._isSvg(iconSource)) {
                processedHtml = this._processSvgIcon(iconSource);
            } else if (this._isEmoji(iconSource)) {
                processedHtml = this._processEmojiIcon(iconSource);
            } else {
                // Assume it's a preset key if no other type matches
                processedHtml = this._processPresetIcon(iconSource, hasChildren, isExpanded);
            }
        } catch (error) {
            console.warn('Icon processing failed:', error);
            processedHtml = this._getFallbackIcon();
        }

        // 4. Store in cache
        if (processedHtml) {
            this._iconCache.set(cacheKey, {
                html: processedHtml,
                type: this._detectIconType(iconSource),
                timestamp: Date.now()
            });
        }

        return processedHtml;
    }


    async _getIconMarkup(nodeData, hasChildren, isExpanded = false) {
        // 1. Check if icon should be shown
        if (!this._shouldShowIcon(hasChildren)) return null;

        // 2. Determine icon source using node-specific logic
        const iconSource = this._resolveIconSource(nodeData, hasChildren, isExpanded);

        // 3. Process the resolved source using the universal processor
        return this._processIconSource(iconSource, { hasChildren, isExpanded });
    }

    /**
     * Determines if an icon should be shown based on configuration and node type.
     * @param {boolean} hasChildren - Whether the node has children.
     * @returns {boolean} True if icon should be shown.
     * @private
     */
    _shouldShowIcon(hasChildren) {
        const { showIconForBranches, showIconForLeaves } = this.options.node.content;
        return hasChildren ? showIconForBranches : showIconForLeaves;
    }

    /**
     * Checks if a cache entry has expired based on the timeout setting.
     * @param {object} cacheEntry - The cache entry object.
     * @returns {boolean} True if cache entry is expired.
     * @private
     */
    _isCacheExpired(cacheEntry) {
        const now = Date.now();
        const timeout = this.options.iconEngine.cacheTimeout;
        return (now - cacheEntry.timestamp) > timeout;
    }

    /**
     * Generates a unique cache key for an icon based on its source and context.
     * @param {string} iconSource - The icon source string.
     * @param {string} nodeType - Either 'branch' or 'leaf'.
     * @param {boolean} isExpanded - Whether the node is expanded.
     * @returns {string} The generated cache key.
     * @private
     */
    _generateCacheKey(iconSource, nodeType, isExpanded = false) {
        if (iconSource.startsWith('http://') || iconSource.startsWith('https://')) {
            return `url:${iconSource}`;
        }
        if (iconSource.startsWith('<svg')) {
            return `svg:${this._hashString(iconSource)}`;
        }
        if (iconSource.length <= 4 && /[\u{1F000}-\u{1F6FF}]/u.test(iconSource)) {
            return `emoji:${iconSource}`;
        }
        return `preset:${iconSource}:${nodeType}:${isExpanded}`;
    }

    /**
     * Generates a hash string from input text for cache key generation.
     * @param {string} str - The string to hash.
     * @returns {string} The hash string.
     * @private
     */
    _hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return hash.toString(36);
    }

    //--------------------------------------> END [ ICON ENGINE CORE ... ]


    //-------------------------------------------------------------
    //-------------[   ICON RESOLUTION   ]------------------------
    //-------------------------------------------------------------

    /**
     * Resolves the appropriate icon source for a node based on configuration and precedence.
     * @param {object} nodeData - The node data object.
     * @param {boolean} hasChildren - Whether this node has children.
     * @param {boolean} isExpanded - Whether this node is expanded.
     * @returns {string|null} The resolved icon source or null.
     * @private
     */
    _resolveIconSource(nodeData, hasChildren, isExpanded) {
        const { sourcePolicy } = this.options.node.content;

        // 1. Custom node icons (highest priority)
        if (sourcePolicy !== 'presetOnly') {
            // State-specific icons
            if (nodeData.iconOverride) {
                const stateIcon = isExpanded ?
                    nodeData.iconOverride.expanded :
                    nodeData.iconOverride.collapsed;
                if (stateIcon) return stateIcon;
            }

            // General node icon - CRITICAL: Check if it's a non-preset type first
            if (nodeData.icon) {
                // If it's URL, SVG, or emoji, return it directly without preset processing
                if (this._isUrl(nodeData.icon) || this._isSvg(nodeData.icon) || this._isEmoji(nodeData.icon)) {
                    return nodeData.icon;
                }
                // Only if it's not a recognized type, treat as potential preset key
                return nodeData.icon;
            }
        }

        // 2. Preset icons (lower priority) - only when no custom icon or when custom is preset key
        if (sourcePolicy !== 'customOnly') {
            return this._getPresetIcon(nodeData, hasChildren, isExpanded);
        }

        return null;
    }

    /**
     * Gets the appropriate preset icon for a node.
     * @param {object} nodeData - The node data object.
     * @param {boolean} hasChildren - Whether this node has children.
     * @param {boolean} isExpanded - Whether this node is expanded.
     * @returns {string|null} The preset icon SVG string or null.
     * @private
     */
    _getPresetIcon(nodeData, hasChildren, isExpanded) {
        const { iconSet, dynamicFolderIcons } = this.options.node.content;
        const iconSetData = Paneton.Tree.ICON_SETS[iconSet];

        if (!iconSetData) {
            console.warn(`Icon set "${iconSet}" not found`);
            return null;
        }

        if (hasChildren) {
            // Folders: use dynamic icons if enabled
            if (dynamicFolderIcons) {
                return isExpanded ? iconSetData._folderOpen : iconSetData._folder;
            }
            return iconSetData._folder;
        } else {
            // Files: detect by extension
            const extension = this._extractFileExtension(nodeData.name);
            return iconSetData[extension] || iconSetData._file;
        }
    }

    /**
     * Extracts file extension from a filename.
     * @param {string} filename - The filename to extract extension from.
     * @returns {string|null} The file extension or null.
     * @private
     */
    _extractFileExtension(filename) {
        if (!filename || typeof filename !== 'string') return null;

        const match = filename.match(/\.([a-zA-Z0-9]+)$/);
        return match ? match[1].toLowerCase() : null;
    }

    //--------------------------------------> END [ ICON RESOLUTION ... ]


    //-------------------------------------------------------------
    //-------------[   ICON TYPE DETECTION   ]--------------------
    //-------------------------------------------------------------

    /**
     * Detects if a string is a URL.
     * @param {string} str - The string to check.
     * @returns {boolean} True if string is a URL.
     * @private
     */
    _isUrl(str) {
        return typeof str === 'string' &&
            (str.startsWith('http://') || str.startsWith('https://'));
    }

    /**
     * Detects if a string is SVG markup.
     * @param {string} str - The string to check.
     * @returns {boolean} True if string is SVG markup.
     * @private
     */
    _isSvg(str) {
        return typeof str === 'string' &&
            str.trim().startsWith('<svg') &&
            str.includes('</svg>');
    }

    /**
     * Detects if a string is an emoji using comprehensive Unicode detection.
     * @param {string} str - The string to check.
     * @returns {boolean} True if string is an emoji.
     * @private
     */
    _isEmoji(str) {
        if (typeof str !== 'string' || str.length === 0 || str.length > 50) return false;

        // Use a more robust approach: test if the string contains emoji characters
        // This regex covers all major emoji blocks and modifiers
        const emojiPattern = /[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|[\u{1F900}-\u{1F9FF}]|[\u{1F018}-\u{1F270}]|[\u{238C}-\u{2454}]|[\u{20D0}-\u{20FF}]|[\u{FE00}-\u{FE0F}]|[\u{1F000}-\u{1F02F}]|[\u{1F0A0}-\u{1F0FF}]|[\u{1F100}-\u{1F64F}]|[\u{1F700}-\u{1F77F}]|[\u{1F780}-\u{1F7FF}]|[\u{1F800}-\u{1F8FF}]|[\u{1FA00}-\u{1FA6F}]|[\u{1FA70}-\u{1FAFF}]|[\u{2194}-\u{2199}]|[\u{21A9}-\u{21AA}]|[\u{231A}-\u{231B}]|[\u{2328}]|[\u{23CF}]|[\u{23E9}-\u{23F3}]|[\u{23F8}-\u{23FA}]|[\u{24C2}]|[\u{25AA}-\u{25AB}]|[\u{25B6}]|[\u{25C0}]|[\u{25FB}-\u{25FE}]|[\u{2600}-\u{2604}]|[\u{260E}]|[\u{2611}]|[\u{2614}-\u{2615}]|[\u{2618}]|[\u{261D}]|[\u{2620}]|[\u{2622}-\u{2623}]|[\u{2626}]|[\u{262A}]|[\u{262E}-\u{262F}]|[\u{2638}-\u{263A}]|[\u{2640}]|[\u{2642}]|[\u{2648}-\u{2653}]|[\u{2660}]|[\u{2663}]|[\u{2665}-\u{2666}]|[\u{2668}]|[\u{267B}]|[\u{267F}]|[\u{2692}-\u{2697}]|[\u{2699}]|[\u{269B}-\u{269C}]|[\u{26A0}-\u{26A1}]|[\u{26AA}-\u{26AB}]|[\u{26B0}-\u{26B1}]|[\u{26BD}-\u{26BE}]|[\u{26C4}-\u{26C5}]|[\u{26C8}]|[\u{26CE}-\u{26CF}]|[\u{26D1}]|[\u{26D3}-\u{26D4}]|[\u{26E9}-\u{26EA}]|[\u{26F0}-\u{26F5}]|[\u{26F7}-\u{26FA}]|[\u{26FD}]|[\u{2702}]|[\u{2705}]|[\u{2708}-\u{270D}]|[\u{270F}]|[\u{2712}]|[\u{2714}]|[\u{2716}]|[\u{271D}]|[\u{2721}]|[\u{2728}]|[\u{2733}-\u{2734}]|[\u{2744}]|[\u{2747}]|[\u{274C}]|[\u{274E}]|[\u{2753}-\u{2755}]|[\u{2757}]|[\u{2763}-\u{2764}]|[\u{2795}-\u{2797}]|[\u{27A1}]|[\u{27B0}]|[\u{27BF}]|[\u{2934}-\u{2935}]|[\u{2B05}-\u{2B07}]|[\u{2B1B}-\u{2B1C}]|[\u{2B50}]|[\u{2B55}]|[\u{3030}]|[\u{303D}]|[\u{3297}]|[\u{3299}]|[\u{1F004}]|[\u{1F0CF}]|[\u{1F170}-\u{1F171}]|[\u{1F17E}-\u{1F17F}]|[\u{1F18E}]|[\u{1F191}-\u{1F251}]|[\u{00A9}]|[\u{00AE}]|[\u{203C}]|[\u{2049}]|[\u{2122}]|[\u{2139}]|[\u{200D}]|[\u{20E3}]/u;

        return emojiPattern.test(str);
    }

    /**
     * Detects the icon type based on its source.
     * @param {string} iconSource - The icon source string.
     * @returns {string} The detected icon type.
     * @private
     */
    _detectIconType(iconSource) {
        if (this._isUrl(iconSource)) return 'image';
        if (this._isSvg(iconSource)) return 'svg';
        if (this._isEmoji(iconSource)) return 'emoji';
        return 'preset';
    }

    //--------------------------------------> END [ ICON TYPE DETECTION ... ]


    //-------------------------------------------------------------
    //-------------[   ICON PROCESSORS   ]------------------------
    //-------------------------------------------------------------

/**
     * Processes SVG icons with theming and sanitization.
     * @param {string} svgString - The SVG string to process.
     * @returns {string} The processed SVG HTML.
     * @private
     */
    _processSvgIcon(svgString) {
        let processed = svgString;

        // 1. Remove hardcoded size attributes to allow CSS control.
        // This regex is robust and handles attributes with or without leading spaces.
        processed = processed.replace(/\s*(width|height)="[^"]*"/g, '');

        // 2. Inject the base icon class intelligently.
        if (processed.includes('class="')) {
            // If class attribute exists, prepend 'pntn-icon ' to it.
            processed = processed.replace(/class="([^"]*)"/, 'class="pntn-icon $1"');
        } else {
            // Otherwise, add the class attribute to the svg tag.
            processed = processed.replace(/<svg/, '<svg class="pntn-icon"');
        }

        // Apply theming
        processed = this._applyIconTheming(processed);

        // Sanitize if enabled
        if (this.options.iconEngine.sanitize) {
            processed = this._sanitizeSvg(processed);
        }

        // Apply accessibility
        processed = this._applyAccessibility(processed, 'decorative');

        return processed;
    }

/**
     * Processes preset icons by looking them up and processing as SVG.
     * @param {string} presetKey - The preset key to look up.
     * @param {boolean} hasChildren - Whether this is for a folder.
     * @param {boolean} isExpanded - Whether the folder is expanded.
     * @returns {string} The processed preset icon HTML.
     * @private
     */
    _processPresetIcon(presetKey, hasChildren, isExpanded) {
        const iconSet = this.options.node.content.iconSet;
        const iconSetData = Paneton.Tree.ICON_SETS[iconSet];
        let svgString = iconSetData[presetKey];

        if (!svgString) {
            console.warn(`Preset icon "${presetKey}" not found in set "${iconSet}"`);
            return this._getFallbackIcon();
        }

        return this._processSvgIcon(svgString);
    }

  /**
     * Processes emoji icons by wrapping them in appropriate markup.
     * @param {string} emoji - The emoji string.
     * @returns {string} The processed emoji HTML.
     * @private
     */
    _processEmojiIcon(emoji) {
        return `<span class="pntn-icon pntn-icon--emoji" aria-hidden="true">${emoji}</span>`;
    }

 /**
     * Applies theme-consistent styling to SVG icons.
     * @param {string} svgString - The SVG string to theme.
     * @returns {string} The themed SVG string.
     * @private
     */
    _applyIconTheming(svgString) {
        return svgString
            .replace(/stroke="(?!none|currentColor)[^"]*"/g, 'stroke="currentColor"')
            .replace(/fill="(?!none|currentColor)[^"]*"/g, 'fill="currentColor"')
            .replace(/#[0-9a-fA-F]{3,8}/g, 'currentColor'); // Replace hex colors
    }

    /**
     * Applies accessibility attributes to icon markup.
     * @param {string} iconHtml - The icon HTML to enhance.
     * @param {string} role - The accessibility role ('decorative' or 'semantic').
     * @returns {string} The enhanced HTML with accessibility attributes.
     * @private
     */
    _applyAccessibility(iconHtml, role = 'decorative') {
        if (role === 'decorative') {
            return iconHtml.replace(/<svg([^>]*)>/, '<svg$1 aria-hidden="true">');
        }
        return iconHtml;
    }

    /**
     * Processes remote icon resources with caching and error handling.
     * @param {string} url - The URL of the remote icon.
     * @param {string} cacheKey - The cache key for this icon.
     * @returns {Promise<string>} The processed icon HTML.
     * @private
     */
    async _processRemoteIcon(url, cacheKey) {
        // Check if already loading
        if (this._pendingRequests.has(url)) {
            return await this._pendingRequests.get(url);
        }

        // Check resource cache
        const cached = this._resourceCache.get(url);
        if (cached) {
            switch (cached.status) {
                case 'loaded':
                    return this._wrapImageIcon(cached.dataUrl);
                case 'loading':
                    return this._wrapLoadingIcon();
                case 'error':
                    return this._wrapFallbackIcon();
            }
        }

        // Mark as loading
        this._resourceCache.set(url, { status: 'loading', timestamp: Date.now() });

        // Start loading
        const loadPromise = this._loadRemoteResource(url);
        this._pendingRequests.set(url, loadPromise);

        try {
            const dataUrl = await loadPromise;
            this._resourceCache.set(url, {
                dataUrl: dataUrl,
                status: 'loaded',
                timestamp: Date.now()
            });
            return this._wrapImageIcon(dataUrl);

        } catch (error) {
            this._resourceCache.set(url, {
                status: 'error',
                timestamp: Date.now()
            });
            return this._wrapFallbackIcon();

        } finally {
            this._pendingRequests.delete(url);
        }
    }

    /**
     * Loads a remote resource and converts it to data URL.
     * @param {string} url - The URL to load.
     * @returns {Promise<string>} The data URL of the loaded resource.
     * @private
     */
    async _loadRemoteResource(url) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        try {
            const response = await fetch(url, {
                signal: controller.signal,
                mode: 'cors'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const blob = await response.blob();

            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(new Error('Failed to read blob'));
                reader.readAsDataURL(blob);
            });

        } finally {
            clearTimeout(timeoutId);
        }
    }

    //--------------------------------------> END [ ICON PROCESSORS ... ]


    //-------------------------------------------------------------
    //-------------[   ICON WRAPPERS   ]---------------------------
    //-------------------------------------------------------------

  /**
     * Wraps image data URL in appropriate HTML markup.
     * @param {string} dataUrl - The image data URL.
     * @returns {string} The wrapped image HTML.
     * @private
     */
    _wrapImageIcon(dataUrl) {
        return `<img src="${dataUrl}" class="pntn-icon" aria-hidden="true" />`;
    }

   /**
     * Wraps loading icon in appropriate markup.
     * @returns {string} The loading icon HTML.
     * @private
     */
    _wrapLoadingIcon() {
        const loadingIcon = this.options.iconEngine.loadingIcon || '⏳';
        return `<span class="pntn-icon pntn-icon--loading" aria-hidden="true">${loadingIcon}</span>`;
    }

    /**
     * Wraps fallback icon in appropriate markup.
     * @returns {string|null} The fallback icon HTML or null.
     * @private
     */
    _wrapFallbackIcon() {
        const fallback = this.options.iconEngine.fallbackIcon;
        if (!fallback) return null;

        if (this._isSvg(fallback)) {
            return this._processSvgIcon(fallback);
        }
        return `<span class="pntn-tree-fallback-icon" aria-hidden="true">${fallback}</span>`;
    }

    /**
     * Gets the fallback icon HTML.
     * @returns {string|null} The fallback icon HTML or null.
     * @private
     */
    _getFallbackIcon() {
        return this._wrapFallbackIcon();
    }

    //--------------------------------------> END [ ICON WRAPPERS ... ]


    //-------------------------------------------------------------
    //-------------[   ICON SANITIZATION   ]----------------------
    //-------------------------------------------------------------

    /**
     * Sanitizes SVG content for security (basic implementation).
     * @param {string} svgString - The SVG string to sanitize.
     * @returns {string} The sanitized SVG string.
     * @private
     */
    _sanitizeSvg(svgString) {
        // Basic sanitization - remove potentially dangerous elements and attributes
        return svgString
            .replace(/<script[\s\S]*?<\/script>/gi, '')
            .replace(/<style[\s\S]*?<\/style>/gi, '')
            .replace(/on\w+="[^"]*"/gi, '')
            .replace(/javascript:/gi, '')
            .replace(/<foreignObject[\s\S]*?<\/foreignObject>/gi, '')
            .replace(/<use[^>]*href\s*=\s*["'][^"']*javascript[^"']*["'][^>]*>/gi, '')
            .replace(/<image[^>]*href\s*=\s*["'][^"']*javascript[^"']*["'][^>]*>/gi, '');
    }

    //--------------------------------------> END [ ICON SANITIZATION ... ]


    //-------------------------------------------------------------
    //-------------[   CACHE MANAGEMENT   ]-----------------------
    //-------------------------------------------------------------

    /**
     * Cleans up expired cache entries and enforces size limits.
     * @private
     */
    _cleanupCache() {
        const now = Date.now();
        const timeout = this.options.iconEngine.cacheTimeout;

        // Clean main cache
        for (const [key, entry] of this._iconCache) {
            if (now - entry.timestamp > timeout) {
                this._iconCache.delete(key);
            }
        }

        // Clean resource cache
        for (const [url, resource] of this._resourceCache) {
            if (now - resource.timestamp > timeout) {
                this._resourceCache.delete(url);
            }
        }

        // Enforce size limits
        this._enforceCacheSizeLimit();
    }

    /**
     * Enforces cache size limits using LRU eviction.
     * @private
     */
    _enforceCacheSizeLimit() {
        const maxSize = this.options.iconEngine.maxCacheSize;
        if (this._iconCache.size <= maxSize) return;

        // Remove oldest entries using LRU
        const entries = Array.from(this._iconCache.entries())
            .sort((a, b) => a[1].timestamp - b[1].timestamp);

        const toDelete = entries.slice(0, entries.length - maxSize);
        toDelete.forEach(([key]) => this._iconCache.delete(key));
    }

    /**
     * Starts the cache cleanup timer.
     * @private
     */
    _startCacheCleanupTimer() {
        // Run cleanup every 2 minutes
        this._cleanupInterval = setInterval(() => {
            this._cleanupCache();
        }, 120000);
    }

    /**
     * Stops the cache cleanup timer.
     * @private
     */
    _stopCacheCleanupTimer() {
        if (this._cleanupInterval) {
            clearInterval(this._cleanupInterval);
            this._cleanupInterval = null;
        }
    }

    //--------------------------------------> END [ CACHE MANAGEMENT ... ]


    //-------------------------------------------------------------
    //-------------[   PRIVATE DATA LOGIC   ]----------------------
    //-------------------------------------------------------------

    /**
     * Recursively finds a node in the original `options.data` structure by its full path.
     * @param {string} path - The complete path of the node.
     * @returns {object|null} The found node object or null.
     * @private
     */
    _findNodeInDataByPath(path) {
        const parts = path.split('/');
        let currentNodes = this.options.data;
        let foundNode = null;

        for (const part of parts) {
            foundNode = currentNodes.find(n => n.name === part);
            if (foundNode) {
                currentNodes = foundNode.children || [];
            } else {
                return null;
            }
        }
        return foundNode;
    }

    /**
     * Helper function to determine if a node should be compacted.
     * @param {object} node - The node to check.
     * @returns {boolean} True if the node has exactly one child that is also a folder.
     * @private
     */
    _shouldCompact(node) {
        return node?.children?.length === 1 &&
            node.children[0]?.children &&
            Array.isArray(node.children[0].children);
    }

    /**
     * Recursively compacts nodes where a folder has only one child that is also a folder.
     * @param {Array<object>} nodes - The array of node objects to process.
     * @returns {Array<object>} The mutated array with compacted nodes.
     * @private
     */
    _compactData(nodes) {
        if (!nodes || !Array.isArray(nodes)) return [];

        nodes.forEach(node => {
            if (!node || typeof node !== 'object') return;

            if (!node._originalPath) {
                node._originalPath = node.name || '';
            }

            let currentNode = node;
            const pathSegments = [];

            while (this._shouldCompact(currentNode)) {
                const singleChild = currentNode.children[0];
                pathSegments.push(singleChild.name);
                currentNode = singleChild;
            }

            if (pathSegments.length > 0) {
                const originalName = node.name || '';
                node.name = originalName + '/' + pathSegments.join('/');
            }

            node.children = currentNode.children;

            if (node.children && Array.isArray(node.children)) {
                this._compactData(node.children);
            }
        });

        return nodes;
    }

    /**
     * Traverses the data to find the maximum number of buttons on any single node.
     * @param {Array<object>} nodes - The array of node objects to search through.
     * @returns {number} The maximum number of buttons found.
     * @private
     */
    _findMaxButtons(nodes) {
        let max = 0;
        if (!nodes) return 0;
        for (const node of nodes) {
            max = Math.max(max, node.buttons?.length || 0);
            if (node.children) {
                max = Math.max(max, this._findMaxButtons(node.children));
            }
        }
        return max;
    }

    /**
     * Finds the maximum depth in the tree structure.
     * @param {Array<object>} nodes - The array of node objects.
     * @param {number} depth - Current depth.
     * @returns {number} The maximum depth found.
     * @private
     */
    _findMaxDepth(nodes, depth = 0) {
        let maxDepth = depth;
        if (!nodes) return maxDepth;

        for (const node of nodes) {
            if (node.children && node.children.length > 0) {
                maxDepth = Math.max(maxDepth, this._findMaxDepth(node.children, depth + 1));
            }
        }
        return maxDepth;
    }

    /**
     * Processes the raw user data through compaction and sorting to generate the final renderable tree state.
     * @private
     */
    _computeRenderState() {
        let processedData = JSON.parse(JSON.stringify(this.options.data));

        if (this.options.tree.compactFolders) {
            processedData = this._compactData(processedData);
        }

        if (this.options.tree.sortNodes) {
            const sortNodesRecursive = (nodes) => {
                if (!nodes) return [];

                nodes.sort((a, b) => {
                    const aIsFolder = !!(a.children && a.children.length > 0);
                    const bIsFolder = !!(b.children && b.children.length > 0);
                    if (aIsFolder && !bIsFolder) return -1;
                    if (!aIsFolder && bIsFolder) return 1;
                    return a.name.localeCompare(b.name);
                });

                nodes.forEach(node => {
                    if (node.children) {
                        sortNodesRecursive(node.children);
                    }
                });
                return nodes;
            };
            processedData = sortNodesRecursive(processedData);
        }

        this.state.renderableTree = processedData;
        this._flattenVisibleTree();
    }

    /**
     * Traverses the hierarchical renderableTree and creates a flat array of visible nodes.
     * @private
     */
    _flattenVisibleTree() {
        this.state.flatVisibleList = [];
        this.state.nodesByPath.clear();

        const flatten = (nodes, depth, parentPath) => {
            if (!nodes) return;

            const hasFolderSibling = nodes.some(node => node.children && node.children.length > 0);

            nodes.forEach(node => {
                const nodeNameForPath = node._originalPath || node.name;
                const currentPath = parentPath ? `${parentPath}/${nodeNameForPath}` : nodeNameForPath;

                this.state.flatVisibleList.push({
                    data: node,
                    depth: depth,
                    path: currentPath,
                    hasFolderSibling: hasFolderSibling
                });

                this.state.nodesByPath.set(currentPath, {
                    data: node,
                    depth: depth,
                    path: currentPath
                });

                // Only add children if node is expanded
                if ((node.expanded !== false) && node.children && node.children.length > 0) {
                    flatten(node.children, depth + 1, currentPath);
                }
            });
        };

        flatten(this.state.renderableTree, 0, '');
    }

    //--------------------------------------> END [ PRIVATE DATA LOGIC ... ]


    //-------------------------------------------------------------
    //-------------[   PRIVATE RENDERING & STYLES   ]--------------
    //-------------------------------------------------------------

 /**
     * Generates and injects the component's scoped CSS into the document's <head>.
      * @private
     */
    _injectStyles() {
            const css = `
            [data-paneton-tree-id="${this.id}"] {
                /*=============================================
                =            PRIMARY VARIABLES (THEMING)      =
                =============================================*/
            --pntn-tree-color-background: #1d1d1d;
            --pntn-tree-color-node-background: transparent;
            --pntn-tree-color-node-background-hover: #37373792;
            --pntn-tree-color-node-background-active: #4c4c4c37;
            --pntn-tree-color-node-background-selected: #97979757;
            --pntn-tree-color-node-text: #c6c5c5f0;
            --pntn-tree-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --pntn-tree-font-size: 13px;
            --pntn-tree-font-weight: 380;
            --pntn-tree-size-node-vertical-padding: 2px;

             --pntn-tree-content-icon-size: 16px;
             --pntn-tree-action-icon-size: 12px;

            /*=====  End of PRIMARY VARIABLES (THEMING)  ======*/

            /*=============================================
            =         ADVANCED VARIABLES (FINE TUNING)    =
            =============================================*/
            --pntn-tree-color-icon: #a0a0a0;
            --pntn-tree-color-icon-focus: #ffffff;
            --pntn-tree-color-segment:rgba(79, 78, 78, 0.91);
            --pntn-tree-color-segment-active: #afafaf94;
            --pntn-tree-color-scrollbar-thumb: rgba(152, 152, 152, 0.4);
            --pntn-tree-color-scrollbar-thumb-hover: rgba(152, 152, 152, 0.7);
            --pntn-tree-base-indent-width: 14px;
            --pntn-tree-toggler-icon-size: 14px;
            --pntn-tree-spacing-button-gap: 2px;
            
            /*-- Content Icon Variables --*/
           
            --pntn-tree-content-icon-color: var(--pntn-tree-color-icon);
            --pntn-tree-content-icon-opacity: 1;
            --pntn-tree-content-icon-loading-opacity: 0.5;

            /*-- Action Icon Variables --*/
           
            --pntn-tree-action-icon-color: var(--pntn-tree-color-icon);
            --pntn-tree-action-icon-color-hover: var(--pntn-tree-color-icon-focus);
            --pntn-tree-action-icon-opacity: 0.8;
            --pntn-tree-action-icon-opacity-hover: 1;

           /* --- Leaf Spacer Width Control --- */
            --_pntn-tree-spacer-width-default: max(var(--pntn-tree-base-indent-width), var(--pntn-tree-toggler-icon-size));
            --_pntn-tree-spacer-width-compact: calc(var(--pntn-tree-base-indent-width) / 2);
            --pntn-tree-leaf-spacer-width: var(--_pntn-tree-spacer-width-default);


           /* --- Indent Width Control --- */
            --_pntn-tree-indent-width-default: max(var(--pntn-tree-base-indent-width), var(--pntn-tree-toggler-icon-size));
            --_pntn-tree-indent-width-compact: calc(var(--pntn-tree-base-indent-width) / 2);
            --pntn-tree-indent-width: var(--_pntn-tree-indent-width-default);


             /* --- Content Gap Control --- */
            --_pntn-tree-content-gap-default: 4px;
            --_pntn-tree-content-gap-compact: 2px;
            --pntn-tree-content-gap: var(--_pntn-tree-content-gap-default);


            /*=====  End of ADVANCED VARIABLES (FINE TUNING)  ======*/

            font-family: var(--pntn-tree-font-family);
            font-weight: var(--pntn-tree-font-weight);
            font-size: var(--pntn-tree-font-size);
            background-color: var(--pntn-tree-color-background);
            height: 100%;
            width: 100%;
            overflow: hidden;
            display: flex;
        }
        [data-paneton-tree-id="${this.id}"] * { box-sizing: border-box; }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-viewport {
            flex: 1;
            overflow-y: auto;
            position: relative;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-viewport::-webkit-scrollbar { display: none; }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-sizer {
            position: relative;
            width: 100%;
            pointer-events: none;
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node {
            position: absolute;
            width: 100%;
            display: grid;
            grid-template-columns: max-content 1fr max-content;
            align-items: center;
            gap: 3px;
            cursor: pointer;
            transition: background-color 0s ease-in-out;
            background-color: var(--pntn-tree-color-node-background);
            color: var(--pntn-tree-color-node-text);
            -webkit-user-select: none;
            -ms-user-select: none;
            user-select: none;
            pointer-events: auto;
        }
      


          [data-paneton-tree-id="${this.id}"].pntn-tree--is-scrolling .pntn-tree-node {
            transition: none !important;
        }

        [data-paneton-tree-id="${this.id}"] .pntn-tree-node.is-hovered {
            background-color: var(--pntn-tree-color-node-background-hover);
        }   
        

        [data-paneton-tree-id="${this.id}"] .pntn-tree-node.is-selected {
            background-color: var(--pntn-tree-color-node-background-active);
        }
        [data-paneton-tree][data-paneton-tree-id="${this.id}"]:hover .pntn-tree-node.is-selected {
            background-color: var(--pntn-tree-color-node-background-selected);
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__indent {
            display: flex;
            height: 100%;
            align-items: center;
        }



        /* 1. CONTENEDOR - Solo define espacio, SIN transform */
[data-paneton-tree-id="${this.id}"] .pntn-tree-node__line-segment {
    width: var(--pntn-tree-indent-width);
    height: 100%;
    position: relative;
    display: flex;
    justify-content: center; /* Centra el contenido */
    align-items: stretch; /* Estira verticalmente */

}

/* 2. LÍNEA BASE - Invisible por defecto */
[data-paneton-tree-id="${this.id}"] .pntn-tree-node__line-segment::before {
    content: '';
    width: 0;
    height: 100%;
    border-left: 1px solid var(--pntn-tree-color-segment);
    opacity: 0; /* Invisible por defecto */
    transition: all 0.3s ease-in-out;
      transform: scaleX(0.5);

}

/* 3. HOVER - Aparece línea gris */
[data-paneton-tree][data-paneton-tree-id="${this.id}"]:hover .pntn-tree-node__line-segment::before {
    opacity: 1;
}

/* 4. ACTIVO - Línea más visible */
[data-paneton-tree-id="${this.id}"] .pntn-tree-node__line-segment.line-active::before {
    border-left-color: var(--pntn-tree-color-segment-active);
    border-left-width: 1px;
    transform: scaleX(0.6);
    opacity: 1;

}




        [data-paneton-tree-id="${this.id}"] .pntn-tree-node.pntn-no-transition .pntn-tree-node__toggler-icon,
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node.pntn-no-transition .pntn-tree-node__line-segment::before {
            transition: none !important;
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__toggler {
            width: var(--pntn-tree-indent-width);
            display: flex;
            justify-content: center;
            align-items: center;
            user-select: none;
            z-index: 1;
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__leaf-spacer {
            width: var(--pntn-tree-leaf-spacer-width);
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__toggler-icon {
            width: var(--pntn-tree-toggler-icon-size);
            height: var(--pntn-tree-toggler-icon-size);
            flex-shrink: 0;
            display: block;
            transform-origin: center;
            transition: transform 0.2s ease-in-out, color 0.2s ease-in-out;
            color: var(--pntn-tree-color-icon);
        }
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node.is-expanded .pntn-tree-node__toggler-icon {
            transform: rotate(90deg);
        }

        [data-paneton-tree-id="${this.id}"] .pntn-tree-node:hover .pntn-tree-node__toggler-icon {
              color: var(--pntn-tree-color-icon-focus);
        }

        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__content {
            min-width: 0;
            display: flex;
            align-items: center;
            gap: var(--pntn-tree-content-gap);
            padding: var(--pntn-tree-size-node-vertical-padding) 0;
        }

        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__label {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /*=============================================
        =            ICON SYSTEM                      =
        =============================================*/
        /*-- 1. Base Class: Applied to all icons --*/
        [data-paneton-tree-id="${this.id}"] .pntn-icon {
            display: block;
            flex-shrink: 0;
            vertical-align: baseline;
            width: var(--_icon-size, 16px);
            height: var(--_icon-size, 16px);
            color: var(--_icon-color, currentColor);
            opacity: var(--_icon-opacity, 1);
            transition: color 0.2s ease, opacity 0.2s ease;
        }

        /*-- 2. Type Modifiers --*/
        [data-paneton-tree-id="${this.id}"] img.pntn-icon {
            object-fit: contain;
        }
        
        [data-paneton-tree-id="${this.id}"] .pntn-icon--emoji,
        [data-paneton-tree-id="${this.id}"] .pntn-icon--loading {
            font-size: calc(var(--_icon-size, 16px) * 0.8);
            line-height: 1.1;
            text-align: center;
        }
        
        [data-paneton-tree-id="${this.id}"] .pntn-icon--loading {
            opacity: var(--pntn-tree-content-icon-loading-opacity, 0.5);
            animation: pntn-tree-loading-pulse 1.5s ease-in-out infinite;
        }

        @keyframes pntn-tree-loading-pulse {
            0%, 100% { opacity: var(--pntn-tree-content-icon-loading-opacity, 0.5); }
            50% { opacity: calc(var(--pntn-tree-content-icon-loading-opacity, 0.5) * 0.3); }
        }

        /*-- 3. Contextual Application --*/
        /*-- Component: Content Icon --*/
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__icon .pntn-icon {
            --_icon-size: var(--pntn-tree-content-icon-size);
            --_icon-color: var(--pntn-tree-content-icon-color);
            --_icon-opacity: var(--pntn-tree-content-icon-opacity);
        }
        
        /*-- Component: Action Icon (Button) --*/
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__button .pntn-icon {
            --_icon-size: var(--pntn-tree-action-icon-size);
            --_icon-color: var(--pntn-tree-action-icon-color);
            --_icon-opacity: var(--pntn-tree-action-icon-opacity);
        }
        
        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__button:hover .pntn-icon {
            --_icon-color: var(--pntn-tree-action-icon-color-hover);
            --_icon-opacity: var(--pntn-tree-action-icon-opacity-hover);
        }
        /*=====  End of ICON SYSTEM  ======*/


        [data-paneton-tree-id="${this.id}"] .pntn-tree-node__actions {
            display: grid;
            grid-template-columns: repeat(${this.state.maxButtons}, max-content);
            justify-content: end;
            gap: var(--pntn-tree-spacing-button-gap);
            padding-right: 4px;
            align-items: center;
        }
       [data-paneton-tree-id="${this.id}"] .pntn-tree-node__button {
            transition: opacity 0.15s ease;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-node .pntn-tree-node__button {
            opacity: 0;
        }
        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-node .pntn-tree-node:hover .pntn-tree-node__button,
        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-node .pntn-tree-node.is-selected .pntn-tree-node__button {
            opacity: 1;
        }

        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-tree .pntn-tree-node__button {
            opacity: 0;
        }
        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-tree:hover .pntn-tree-node__button {
            opacity: 0.7;
        }
        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-tree .pntn-tree-node:hover .pntn-tree-node__button,
        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-tree .pntn-tree-node__button:hover,
        [data-paneton-tree-id="${this.id}"].pntn-tree--buttons-on-focus-tree .pntn-tree-node.is-selected .pntn-tree-node__button {
            opacity: 1;
        }

        [data-paneton-tree-id="${this.id}"].pntn-tree--hide-segments .pntn-tree-node__line-segment {
            visibility: hidden;
        }

        [data-paneton-tree-id="${this.id}"] .pntn-scrollbar-track {
            width: 4px;
            position: relative;
            background: transparent;
        }
        [data-paneton-tree-id="${this.id}"] .pntn-scrollbar-thumb {
            width: 4px;
            background-color: var(--pntn-tree-color-scrollbar-thumb);
            position: absolute;
            right: 0px;
            cursor: pointer;
            border-radius: 0px;
            opacity: 0;
            transition: opacity .2s ease-in-out, background-color .2s ease;
        }
        [data-paneton-tree][data-paneton-tree-id="${this.id}"]:hover .pntn-scrollbar-thumb {
            opacity: 1;
        }
        [data-paneton-tree-id="${this.id}"] .pntn-scrollbar-thumb:hover {
            background-color: var(--pntn-tree-color-scrollbar-thumb-hover);
        }
    `;

        this.styleElement = document.createElement('style');
        this.styleElement.id = `style-${this.id}`;
        this.styleElement.textContent = css;
        document.head.appendChild(this.styleElement);
    }






    /**
     * Renders the initial HTML structure for virtualization.
     * @private
     */
    _renderInitialView() {
        this.container.innerHTML = '';

        const viewport = document.createElement('div');
        viewport.className = 'pntn-tree-viewport';

        const sizer = document.createElement('div');
        sizer.className = 'pntn-tree-sizer';

        const scrollbarTrack = document.createElement('div');
        scrollbarTrack.className = 'pntn-scrollbar-track';
        scrollbarTrack.innerHTML = `<div class="pntn-scrollbar-thumb"></div>`;

        viewport.appendChild(sizer);
        this.container.appendChild(viewport);
        this.container.appendChild(scrollbarTrack);

        this.viewport = viewport;
        this.sizer = sizer;

        this.container.setAttribute('data-paneton-tree', '');
        this.container.setAttribute('data-paneton-tree-id', this.id);



        if (this.options.node.actions.visibility === 'onFocusTree') {
            this.container.classList.add('pntn-tree--buttons-on-focus-tree');
        } else if (this.options.node.actions.visibility === 'onFocusNode') {
            this.container.classList.add('pntn-tree--buttons-on-focus-node');
        }



      if (!this.options.tree.showSegments) {
            this.container.classList.add('pntn-tree--hide-segments');
        }

        this._applyDensity();

        this._applyTheme();
    }

    /**
     * Applies theme overrides to the container.
     * @private
     */
    _applyTheme() {
        const theme = this.options.theme;
        const themeMap = {
            backgroundColor: '--pntn-tree-color-background',
            nodeBackgroundColor: '--pntn-tree-color-node-background',
            nodeBackgroundHover: '--pntn-tree-color-node-background-hover',
            nodeBackgroundActive: '--pntn-tree-color-node-background-active',
            nodeBackgroundSelected: '--pntn-tree-color-node-background-selected',
            nodeTextColor: '--pntn-tree-color-node-text',
            fontFamily: '--pntn-tree-font-family',
            fontSize: '--pntn-tree-font-size',
            fontWeight: '--pntn-tree-font-weight',
        };

        for (const key in theme) {
            if (themeMap[key]) {
                const cssVar = themeMap[key];
                this.container.style.setProperty(cssVar, theme[key]);
            }
        }
    }

    /**
 * Creates the DOM element pool and measures row height using robust off-screen staging.
 * This method ensures accurate measurement by applying complete CSS styles in an off-screen
 * staging area before measuring, guaranteeing design-first compliance with any theme.
 * @private
 */
    _createAndMeasurePool() {
        // Create off-screen staging container with complete style context
        const stagingContainer = document.createElement('div');
        stagingContainer.style.position = 'absolute';
        stagingContainer.style.top = '-9999px';
        stagingContainer.style.left = '-9999px';
        stagingContainer.style.width = this.viewport.clientWidth + 'px';
        stagingContainer.style.visibility = 'hidden'; // Prevent flash but allow layout
        stagingContainer.style.pointerEvents = 'none';

        // Apply complete style context to staging container
        stagingContainer.className = this.container.className;
        stagingContainer.setAttribute('data-paneton-tree-id', this.id);
        stagingContainer.setAttribute('data-paneton-tree', '');

        // Create staging viewport structure to match real structure
        const stagingViewport = document.createElement('div');
        stagingViewport.className = 'pntn-tree-viewport';
        stagingViewport.style.height = 'auto';

        const stagingSizer = document.createElement('div');
        stagingSizer.className = 'pntn-tree-sizer';

        stagingViewport.appendChild(stagingSizer);
        stagingContainer.appendChild(stagingViewport);

        // Insert staging container into DOM for accurate CSS computation
        document.body.appendChild(stagingContainer);

        // Create sample node with complete structure
        const sampleNode = this._createRowTemplate();

        // Populate with realistic content for accurate measurement
        const longestLabel = this._findLongestLabel();
        const labelElement = sampleNode.querySelector('.pntn-tree-node__label');
        labelElement.textContent = longestLabel;

        // Populate with maximum buttons for complete measurement
        this._populateMaxButtons(sampleNode);

        // Set up realistic indentation (use maximum expected depth)
        const indentContainer = sampleNode.querySelector('.pntn-tree-node__indent');
        const segments = indentContainer.querySelectorAll('.pntn-tree-node__line-segment');
        for (let i = 0; i < Math.min(this.state.maxIndentDepth, segments.length); i++) {
            segments[i].style.display = '';
        }

        // Add to staging sizer
        stagingSizer.appendChild(sampleNode);

        // Critical: Force complete layout calculation
        sampleNode.offsetHeight; // Trigger reflow
        stagingContainer.offsetHeight; // Ensure container layout

        // Measure actual rendered height
        const measuredHeight = sampleNode.offsetHeight;
        const computedStyle = window.getComputedStyle(sampleNode);
        const computedHeight = parseFloat(computedStyle.height);

        // Validation: Ensure measurement is reasonable
        if (measuredHeight < 10 || measuredHeight > 100) {
            console.warn(`Paneton.Tree: Suspicious height measurement (${measuredHeight}px). Using fallback.`);
            this.state.rowHeight = 20; // Reasonable fallback
        } else {
            this.state.rowHeight = Math.max(measuredHeight, computedHeight);
        }

        // Cleanup staging area
        document.body.removeChild(stagingContainer);

        // Calculate pool size based on accurate measurement
        this.state.viewportHeight = this.viewport.clientHeight;
        this.state.totalPoolSize = Math.ceil(this.state.viewportHeight / this.state.rowHeight) + 5;

        // Create actual pool elements
        for (let i = 0; i < this.state.totalPoolSize; i++) {
            const nodeElement = this._createRowTemplate();
            nodeElement.style.display = 'none';
            this.state.domPool.push(nodeElement);
            this.sizer.appendChild(nodeElement);
        }

        // Debug logging for verification
        if (window.console && window.console.log) {
          //  console.log(`Paneton.Tree: Measured row height: ${this.state.rowHeight}px, Pool size: ${this.state.totalPoolSize}`);
        }
    }

    /**
     * Finds the longest label text from all nodes in the dataset to ensure
     * accurate width-based height measurement during staging.
     * @returns {string} The longest label text found, or a reasonable default.
     * @private
     */
    _findLongestLabel() {
        let longestLabel = 'Sample Node Label';
        let maxLength = longestLabel.length;

        /**
         * Recursively traverse nodes to find longest label.
         * @param {Array<object>} nodes - Array of node objects to search.
         */
        const traverseNodes = (nodes) => {
            if (!nodes || !Array.isArray(nodes)) return;

            nodes.forEach(node => {
                if (node && typeof node === 'object') {
                    const nodeLabel = node.name || '';
                    if (nodeLabel.length > maxLength) {
                        maxLength = nodeLabel.length;
                        longestLabel = nodeLabel;
                    }

                    // Recursively check children
                    if (node.children && Array.isArray(node.children)) {
                        traverseNodes(node.children);
                    }
                }
            });
        };

        // Start traversal from the root data
        traverseNodes(this.options.data);

        // Ensure we have a reasonable minimum length for measurement
        if (longestLabel.length < 20) {
            longestLabel = 'Sample Node With Long Label Name';
        }

        return longestLabel;
    }

    /**
     * Populates a sample node with the maximum number of buttons to ensure
     * accurate measurement of row height when buttons are present.
     * @param {HTMLElement} sampleNode - The DOM element to populate with buttons.
     * @private
     */
    _populateMaxButtons(sampleNode) {
        if (this.state.maxButtons === 0) return;

        const actionsContainer = sampleNode.querySelector('.pntn-tree-node__actions');
        if (!actionsContainer) return;

        // Clear any existing buttons
        actionsContainer.innerHTML = '';

        // Create maximum number of sample buttons
        for (let i = 0; i < this.state.maxButtons; i++) {
            const buttonEl = document.createElement('div');
            buttonEl.className = 'pntn-tree-node__button';
            buttonEl.innerHTML = Paneton.Tree.DEFAULT_BUTTON_ICON;
            buttonEl.title = `Sample Button ${i + 1}`;

            // Ensure button is visible for measurement
            buttonEl.style.opacity = '1';

            actionsContainer.appendChild(buttonEl);
        }

        // Apply grid template to match actual render behavior
        if (this.state.maxButtons > 0) {
            actionsContainer.style.gridTemplateColumns = `repeat(${this.state.maxButtons}, max-content)`;
        }
    }

    /**
     * Creates a single row element template with all necessary structure.
     * @returns {HTMLElement} The created DOM element template.
     * @private
     */
    _createRowTemplate() {
        const nodeEl = document.createElement('div');
        nodeEl.className = 'pntn-tree-node';

        const indentContainer = document.createElement('div');
        indentContainer.className = 'pntn-tree-node__indent';

        // Pre-allocate indent segments for maximum depth
        for (let i = 0; i < this.state.maxIndentDepth + 2; i++) {
            const lineSegment = document.createElement('div');
            lineSegment.className = 'pntn-tree-node__line-segment';
            lineSegment.style.display = 'none'; // Initially hidden
            indentContainer.appendChild(lineSegment);
        }

        const toggler = document.createElement('div');
        toggler.className = 'pntn-tree-node__toggler';
        toggler.innerHTML = `<svg class="pntn-tree-node__toggler-icon" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6l-6 6"></path></svg>`;

        const leafSpacer = document.createElement('div');
        leafSpacer.className = 'pntn-tree-node__leaf-spacer';

        indentContainer.appendChild(toggler);
        indentContainer.appendChild(leafSpacer);

        const mainContentContainer = document.createElement('div');
        mainContentContainer.className = 'pntn-tree-node__content';

        const iconEl = document.createElement('span');
        iconEl.className = 'pntn-tree-node__icon';
        iconEl.style.display = 'none'; // Initially hidden
        mainContentContainer.appendChild(iconEl);

        const labelEl = document.createElement('span');
        labelEl.className = 'pntn-tree-node__label';
        mainContentContainer.appendChild(labelEl);

        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'pntn-tree-node__actions';

        nodeEl.appendChild(indentContainer);
        nodeEl.appendChild(mainContentContainer);
        nodeEl.appendChild(buttonContainer);

        return nodeEl;
    }


    /**
    * Updates a row element with data from a specific node (performance-critical function).
    * This is the final, corrected version that handles selection, indentation, and conditional animations.
    * @param {HTMLElement} element - The row element from the DOM pool.
    * @param {object} nodeInfo - The node object from the flat list.
    * @param {number} index - The index of the node in the flat visible list.
    * @param {object} [options={}] - Render options, e.g., { isToggle: boolean, toggledPath: string }.
    * @private
    */
    async _updateRow(element, nodeInfo, index, options = {}) {
        const { data: nodeData, depth, path, hasFolderSibling } = nodeInfo;

        const { isToggle = false, toggledPath = null } = options;
        const isTheNodeThatWasToggled = (path === toggledPath);

        if (isToggle && !isTheNodeThatWasToggled) {
            element.classList.add('pntn-no-transition');
        }

        const hasChildren = nodeData.children && nodeData.children.length > 0;

        element.style.transform = `translateY(${index * this.state.rowHeight}px)`;
        element.style.height = `${this.state.rowHeight}px`;
        element.dataset.path = path;


        element.classList.toggle('is-selected', this.state.activeNode.path === path);
        element.classList.toggle('is-hovered', this.state.hoveredNodePath === path);  
        element.classList.toggle('is-expanded', hasChildren && nodeData.expanded !== false);

        const label = element.querySelector('.pntn-tree-node__label');
        label.textContent = nodeData.name;

        // Update icon with new icon engine
        await this._updateRowIcon(element, nodeInfo, index, options);

        const indentContainer = element.querySelector('.pntn-tree-node__indent');
        if (depth === 0 && !hasChildren) {
            indentContainer.style.width = '0px';
            indentContainer.style.minWidth = '0px';
        } else {
            indentContainer.style.width = '';
            indentContainer.style.minWidth = '';
        }
        const segments = indentContainer.querySelectorAll('.pntn-tree-node__line-segment');
        for (let i = 0; i < segments.length; i++) {
            segments[i].style.display = i < depth ? '' : 'none';
        }
        const toggler = element.querySelector('.pntn-tree-node__toggler');
        const leafSpacer = element.querySelector('.pntn-tree-node__leaf-spacer');
        if (hasChildren) {
            toggler.style.display = '';
            leafSpacer.style.display = 'none';
        } else {
            toggler.style.display = 'none';
            if (!hasFolderSibling) {
                leafSpacer.style.display = '';
            } else {
                leafSpacer.style.display = 'none';
            }
        }

        const { path: activePath, depth: activeDepth } = this.state.activeNode;
        if (activePath) {
            const activeNodeProxy = this.state.nodesByPath.get(activePath);
            if (activeNodeProxy) {
                const isActiveNodeFolder = !!(activeNodeProxy.data.children && activeNodeProxy.data.children.length > 0);
                const activeSegmentIndex = isActiveNodeFolder ? activeDepth : activeDepth - 1;
                let familyAncestorPath = activePath;
                if (!isActiveNodeFolder && activePath.includes('/')) {
                    familyAncestorPath = activePath.substring(0, activePath.lastIndexOf('/'));
                }
                const isFamilyMember = path === familyAncestorPath || path.startsWith(familyAncestorPath + '/');
                segments.forEach((segment, index) => {
                    const shouldBeActive = isFamilyMember && index === activeSegmentIndex;
                    segment.classList.toggle('line-active', shouldBeActive);
                });
            }
        } else {
            segments.forEach(segment => segment.classList.remove('line-active'));
        }

        this._updateRowButtons(element, nodeData, path);

        if (isToggle && !isTheNodeThatWasToggled) {
            void element.offsetHeight;
            element.classList.remove('pntn-no-transition');
        }
    }

    /**
     * Updates the icon for a row element using the icon engine.
     * @param {HTMLElement} element - The row element from the DOM pool.
     * @param {object} nodeInfo - The node object from the flat list.
     * @param {number} index - The index of the node in the flat visible list.
     * @param {object} [options={}] - Render options.
     * @private
     */
    async _updateRowIcon(element, nodeInfo, index, options = {}) {
        const { data: nodeData, depth, path } = nodeInfo;
        const iconEl = element.querySelector('.pntn-tree-node__icon');
        const hasChildren = nodeData.children && nodeData.children.length > 0;
        const isExpanded = hasChildren && nodeData.expanded !== false;

        try {
            const iconHtml = await this._getIconMarkup(nodeData, hasChildren, isExpanded);

            if (iconHtml) {
                iconEl.innerHTML = iconHtml;
                iconEl.style.display = '';
            } else {
                iconEl.style.display = 'none';
            }

        } catch (error) {
            console.warn('Icon processing failed for node:', path, error);
            const fallback = this._getFallbackIcon();
            if (fallback) {
                iconEl.innerHTML = fallback;
                iconEl.style.display = '';
            } else {
                iconEl.style.display = 'none';
            }
        }
    }

    async _updateRowButtons(element, nodeData, path) {
        const actionsContainer = element.querySelector('.pntn-tree-node__actions');
        actionsContainer.innerHTML = '';

        if (nodeData.buttons && nodeData.buttons.length > 0) {
            for (const [buttonIndex, buttonData] of nodeData.buttons.entries()) {
                const buttonEl = document.createElement('div');
                buttonEl.className = 'pntn-tree-node__button';

                let iconToUse = buttonData?.icon || Paneton.Tree.DEFAULT_BUTTON_ICON;

                // process icon through icon engine
                buttonEl.innerHTML = await this._processIconSource(iconToUse) || '';

                const tooltip = buttonData?.tooltip || `Action ${buttonIndex + 1}`;
                buttonEl.setAttribute('aria-label', `${tooltip} on ${nodeData.name}`);
                buttonEl.setAttribute('role', 'button');
                buttonEl.setAttribute('tabindex', '0');

                if (buttonData?.tooltip) {
                    buttonEl.title = buttonData.tooltip;
                }

                buttonEl.dataset.buttonIndex = buttonIndex;
                buttonEl.dataset.nodePath = path;
                actionsContainer.appendChild(buttonEl);
            }
        }
    }

  /**
     * The main virtual rendering loop (performance-critical function).
     * It now also calculates the programmatic hover state on each frame.
     * @private
     */
    _virtualRender(options = {}) {
        if (!this.viewport || !this.sizer) return;

         const { x, y } = this.state.mousePosition;
        let currentHoveredPath = null;
        const viewportRect = this.viewport.getBoundingClientRect();

        // Check if the mouse is within the viewport bounds
        if (x >= viewportRect.left && x <= viewportRect.right &&
            y >= viewportRect.top && y <= viewportRect.bottom) {

            // Use the browser's fast API to find what's under the cursor
            const elementUnderMouse = document.elementFromPoint(x, y);
            if (elementUnderMouse) {
                const targetNode = elementUnderMouse.closest('.pntn-tree-node');
                // Ensure the found node is a direct child of our sizer
                if (targetNode && targetNode.parentElement === this.sizer) {
                    currentHoveredPath = targetNode.dataset.path;
                }
            }
        }
        this.state.hoveredNodePath = currentHoveredPath;
 

        const scrollTop = this.viewport.scrollTop;
        const viewportHeight = this.viewport.clientHeight;
        const totalHeight = this.state.flatVisibleList.length * this.state.rowHeight;

        // Update sizer height
        this.sizer.style.height = `${totalHeight}px`;

        // Calculate visible range with buffer
        const startIndex = Math.max(0, Math.floor(scrollTop / this.state.rowHeight) - 2);
        const endIndex = Math.min(
            this.state.flatVisibleList.length - 1,
            startIndex + Math.ceil(viewportHeight / this.state.rowHeight) + 4
        );

        // Update pool elements
        for (let i = 0; i < this.state.totalPoolSize; i++) {
            const nodeIndex = startIndex + i;
            const element = this.state.domPool[i];

            if (nodeIndex >= 0 && nodeIndex <= endIndex && nodeIndex < this.state.flatVisibleList.length) {
                const nodeInfo = this.state.flatVisibleList[nodeIndex];
                element.style.display = '';
                this._updateRow(element, nodeInfo, nodeIndex, options);
            } else {
                element.style.display = 'none';
                element.dataset.path = '';
            }
        }

        // Update scrollbar
        if (this.updateScrollbar) {
            this.updateScrollbar();
        }
    }

    //--------------------------------------> END [ PRIVATE RENDERING & STYLES ... ]


    //-------------------------------------------------------------
    //-------------[   PRIVATE EVENT HANDLING   ]------------------
    //-------------------------------------------------------------

    /**
     * Sets up the main event listeners for the component.
     * @private
     */
    _setupEventListeners() {
        this.container.addEventListener('click', this._boundHandleClick);
        this.viewport.addEventListener('scroll', this._boundHandleScroll);
        this.container.addEventListener('mousemove', this._boundHandleMouseMove);
        this.container.addEventListener('mouseleave', this._boundHandleMouseLeave);
    }

   /**
 * Handles scroll events with throttling and adds a class to the container
 * during scroll to prevent animation artifacts on recycled nodes.
 * @private
 */
_handleScroll() {
    // Add scrolling class to the main container
    this.container.classList.add('pntn-tree--is-scrolling');

    // Throttle virtual render
    if (!this._scrollThrottled) {
        this._scrollThrottled = true;
        requestAnimationFrame(() => {
            this._virtualRender();
            this._scrollThrottled = false;
        });
    }

    // Debounce the removal of the scrolling class
    clearTimeout(this._scrollEndTimer);
    this._scrollEndTimer = setTimeout(() => {
        this.container.classList.remove('pntn-tree--is-scrolling');
    }, 150); // A delay of 150ms after the last scroll event
}


    /**
     * Handles click events on the container using event delegation.
     * @param {MouseEvent} event - The click event object.
     * @private
     */
    _handleContainerClick(event) {
        const rowElement = event.target.closest('.pntn-tree-node');
        if (!rowElement) return;

        const path = rowElement.dataset.path;
        if (!path) return;

        const nodeProxy = this.state.nodesByPath.get(path);
        if (!nodeProxy) return;

        // Handle action button clicks first and exit
        const button = event.target.closest('.pntn-tree-node__button');
        if (button) {
            event.stopPropagation();
            this._selectNode(path, nodeProxy.depth);
            this._virtualRender(); // Re-render to show selection on button click
            const buttonIndex = parseInt(button.dataset.buttonIndex);
            const buttonData = nodeProxy.data.buttons?.[buttonIndex];
            if (buttonData && typeof buttonData.onClick === 'function') {
                buttonData.onClick(this.findNode(path));
            }
            return;
        }

        // Update state for the new selection
        this._selectNode(path, nodeProxy.depth);

        const isFolder = nodeProxy.data.children && nodeProxy.data.children.length > 0;
        const clickedToggler = !!event.target.closest('.pntn-tree-node__toggler');

        // Decide if we should toggle based on config and what was clicked
        if (isFolder && (clickedToggler || this.options.tree.toggleOnRowClick)) {
            // Toggle action will trigger its own re-render, which will apply selection visuals
            this._toggleNode(nodeProxy);
        } else {
            // If it's not a toggle action, we must manually re-render to apply the selection visuals
            this._virtualRender({ isToggle: false });

            // Call the custom node onClick if it exists
            if (typeof nodeProxy.data.onClick === 'function') {
                nodeProxy.data.onClick(this.findNode(path));
            }
        }
    }



    /**
  * Updates the state to reflect the currently selected node.
  * @param {string} path - The path of the node to select.
  * @param {number} depth - The depth of the node to select.
  * @private
  */
    _selectNode(path, depth) {
        this.state.activeNode.path = path;
        this.state.activeNode.depth = depth;
    }



    /**
     * Toggles the expanded/collapsed state of a folder node.
     * @param {object} nodeProxy - The internal proxy object for the node.
     * @param {boolean} [forceState] - If provided, forces the expand/collapse state.
     * @private
     */
    _toggleNode(nodeProxy, forceState) {
        if (!nodeProxy?.data?.children) return;

        const isExpanded = nodeProxy.data.expanded !== false;
        const shouldBeExpanded = forceState !== undefined ? forceState : !isExpanded;

        if (isExpanded === shouldBeExpanded) return;

        nodeProxy.data.expanded = shouldBeExpanded;

        // Re-flatten the tree to update visible list
        this._flattenVisibleTree();

        // Re-render
        this._virtualRender({ isToggle: true, toggledPath: nodeProxy.path });

        // Call onExpand callback if defined
        if (typeof nodeProxy.data.onExpand === 'function') {
            nodeProxy.data.onExpand(shouldBeExpanded, this.findNode(nodeProxy.path));
        }
    }

/**
     * Handles mouse movement over the container. It passively tracks the mouse
     * position and efficiently triggers a single re-render per animation frame
     * to update the programmatic hover state.
     * @param {MouseEvent} event - The mousemove event object.
     * @private
     */
    _handleMouseMove(event) {
        // 1. Passively update the coordinates for the render loop to use.
        this.state.mousePosition.x = event.clientX;
        this.state.mousePosition.y = event.clientY;

        // 2. Trigger a render, but throttled to once per frame.
        // This is the key part that was missing.
        if (!this._renderScheduled) {
            this._renderScheduled = true;
            requestAnimationFrame(() => {
                this._virtualRender();
                this._renderScheduled = false; // Allow the next frame's event to schedule a render
            });
        }
    }

    /**
     * Handles the mouse leaving the container to clear the programmatic hover state.
     * @param {MouseEvent} event - The mouseleave event object.
     * @private
     */
    _handleMouseLeave(event) {
        // Reset position to avoid re-hovering the last element on mouse re-entry
        this.state.mousePosition.x = -1;
        this.state.mousePosition.y = -1;

        if (this.state.hoveredNodePath !== null) {
            this.state.hoveredNodePath = null;
            this._virtualRender();
        }
    }
  
    //--------------------------------------> END [ PRIVATE EVENT HANDLING ... ]


    //-------------------------------------------------------------
    //-------------[   PRIVATE RENDER LOOP   ]---------------------
    //-------------------------------------------------------------

    /**
     * Schedules a render task for the next animation frame if one isn't already scheduled.
     * @private
     */
    _scheduleRender() {
        if (this._renderScheduled) return;

        this._renderScheduled = true;
        requestAnimationFrame(() => this._performRender());
    }

    /**
     * Executes the DOM update by recalculating state and re-rendering.
     * @private
     */
    _performRender() {
        try {
            if (!this._isDirty) return;

            this._computeRenderState();
            this.state.maxButtons = this._findMaxButtons(this.state.renderableTree);
            const newMaxDepth = this._findMaxDepth(this.state.renderableTree);

            if (newMaxDepth > this.state.maxIndentDepth) {
                this.state.maxIndentDepth = newMaxDepth;
                this._expandIndentPool(newMaxDepth);
            }

            this._virtualRender();

        } finally {
            this._isDirty = false;
            this._renderScheduled = false;
        }
    }

    /**
     * Expands the indent pool for all elements to accommodate deeper nesting.
     * @param {number} newCapacity - The new maximum depth required.
     * @private
     */
    _expandIndentPool(newCapacity) {
        this.state.domPool.forEach(element => {
            const indentContainer = element.querySelector('.pntn-tree-node__indent');
            const currentSegments = indentContainer.querySelectorAll('.pntn-tree-node__line-segment');

            while (currentSegments.length < newCapacity + 2) {
                const lineSegment = document.createElement('div');
                lineSegment.className = 'pntn-tree-node__line-segment';
                lineSegment.style.display = 'none';

                // Insert before toggler and spacer
                const toggler = indentContainer.querySelector('.pntn-tree-node__toggler');
                indentContainer.insertBefore(lineSegment, toggler);
            }
        });
    }

    //--------------------------------------> END [ PRIVATE RENDER LOOP ... ]


    //-------------------------------------------------------------
    //-------------[   PRIVATE UTILITIES   ]-----------------------
    //-------------------------------------------------------------

    /**
     * Sets up the logic and event listeners for the custom scrollbar.
     * @private
     */
    _setupCustomScrollbar() {
        const scrollWrapper = this.viewport;
        const track = this.container.querySelector('.pntn-scrollbar-track');
        const thumb = this.container.querySelector('.pntn-scrollbar-thumb');

        if (!scrollWrapper || !track || !thumb) return;

        this.updateScrollbar = () => {
            const contentHeight = scrollWrapper.scrollHeight;
            const visibleHeight = scrollWrapper.clientHeight;

            if (contentHeight <= visibleHeight) {
                track.style.display = 'none';
                return;
            }

            track.style.display = 'block';

            const thumbHeight = Math.max(20, (visibleHeight / contentHeight) * visibleHeight);
            thumb.style.height = `${thumbHeight}px`;

            const scrollTop = scrollWrapper.scrollTop;
            const maxScrollTop = contentHeight - visibleHeight;

            if (maxScrollTop === 0) return;

            const thumbMaxY = track.clientHeight - thumbHeight;
            const thumbY = (scrollTop / maxScrollTop) * thumbMaxY;
            thumb.style.top = `${thumbY}px`;
        };

        // Scrollbar drag handling
        thumb.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const startY = e.clientY;
            const startScrollTop = scrollWrapper.scrollTop;
            document.body.style.userSelect = 'none';

            const onMouseMove = (moveEvent) => {
                const deltaY = moveEvent.clientY - startY;
                const scrollableHeight = track.clientHeight - thumb.offsetHeight;

                if (scrollableHeight === 0) return;

                const contentScrollableHeight = scrollWrapper.scrollHeight - scrollWrapper.clientHeight;
                const scrollRatio = contentScrollableHeight / scrollableHeight;
                scrollWrapper.scrollTop = startScrollTop + deltaY * scrollRatio;
            };

            const onMouseUp = () => {
                document.body.style.userSelect = '';
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        // Initial scrollbar setup
        setTimeout(() => this.updateScrollbar(), 0);

        // Observe viewport size changes
        new ResizeObserver(() => {
            this.state.viewportHeight = this.viewport.clientHeight;
            this.updateScrollbar();
        }).observe(scrollWrapper);
    }


    /**
     * Applies layout density styles based on the 'compactDensity' option.
     * @private
     */
    _applyDensity() {
        if (this.options.tree.compactDensity) {
            this.container.style.setProperty('--pntn-tree-leaf-spacer-width', 'var(--_pntn-tree-spacer-width-compact)');
            this.container.style.setProperty('--pntn-tree-indent-width', 'var(--_pntn-tree-indent-width-compact)');
            this.container.style.setProperty('--pntn-tree-content-gap', 'var(--_pntn-tree-content-gap-compact)');


        } else { // Default
            this.container.style.setProperty('--pntn-tree-leaf-spacer-width', 'var(--_pntn-tree-spacer-width-default)');
            this.container.style.setProperty('--pntn-tree-indent-width', 'var(--_pntn-tree-indent-width-default)');
            this.container.style.setProperty('--pntn-tree-content-gap', 'var(--_pntn-tree-content-gap-default)');
        }
    }


    //--------------------------------------> END [ PRIVATE UTILITIES ... ]

};