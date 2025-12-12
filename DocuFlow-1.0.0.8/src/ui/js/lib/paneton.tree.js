/**
 * Paneton Tree v1.0.0
 * A modern, powerful hierarchical tree component with virtual rendering
 * 
 * @author @lewopxd
 * @license MIT
 * @repository https://github.com/0zdev/paneton
 */
(function (factory) {
    typeof define === 'function' && define.amd ? define(factory) :
    factory();
  })((function () { 'use strict';
  
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
     */
  
    window.Paneton = window.Paneton || {};
  
    Paneton.Tree = class {
  
        //-------------------------------------------------------------
        //-------------[   CLASS STRUCTURE   ]-------------------------
        //-------------------------------------------------------------
  
        /**
         * Default SVG icon used for buttons when one is not provided.
         * @type {string}
         * @static
         */
        static DEFAULT_CUBE_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>`;
  
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
  
            this.options = {
                data: [],
                theme: {},
                compactFolders: false,
                sortNodes: true,
                autoHideButtons: false,
                expandOnClick: false,
                showSegments: true,            
                ...options
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
            };
  
            this._isDirty = false;
            this._renderScheduled = false;
            this._scrollThrottled = false;
  
            this.id = `pntn-tree-${Date.now()}${Math.random().toString(36).substring(2, 9)}`;
            this._boundHandleClick = this._handleContainerClick.bind(this);
            this._boundHandleScroll = this._handleScroll.bind(this);
  
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
            if (this.styleElement) this.styleElement.remove();
            if (this.container) {
                this.container.removeEventListener('click', this._boundHandleClick);
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
  
            if (this.options.compactFolders) {
                processedData = this._compactData(processedData);
            }
  
            if (this.options.sortNodes) {
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
              --pntn-tree-size-node-vertical-padding: 4px;
  
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
              --pntn-tree-spacing-button-gap: 4px;
  
              /* --- Leaf Spacer Width Control --- */
              --_pntn-tree-spacer-width-auto: max(var(--pntn-tree-base-indent-width), var(--pntn-tree-toggler-icon-size));
              --_pntn-tree-spacer-width-compact: calc(var(--pntn-tree-base-indent-width) / 2);
              --pntn-tree-leaf-spacer-width: var(--_pntn-tree-spacer-width-auto);
  
              /* --- Indent Width Control --- */
              --_pntn-tree-indent-width-auto: max(var(--pntn-tree-base-indent-width), var(--pntn-tree-toggler-icon-size));
              --_pntn-tree-indent-width-compact: calc(var(--pntn-tree-base-indent-width) / 2);
              --pntn-tree-indent-width: var(--_pntn-tree-indent-width-auto);
  
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
              gap: 2px; 
              cursor: pointer; 
              transition: background-color 0.15s ease-in-out;
              background-color: var(--pntn-tree-color-node-background); 
              color: var(--pntn-tree-color-node-text);  
              -webkit-user-select: none;  
              -ms-user-select: none;  
              user-select: none;
              pointer-events: auto;
          }
          [data-paneton-tree-id="${this.id}"] .pntn-tree-node:hover { 
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
      transition: opacity 0.3s ease-in-out;
      
      
  }
  
  /* 3. HOVER - Aparece línea gris */
  [data-paneton-tree][data-paneton-tree-id="${this.id}"]:hover .pntn-tree-node__line-segment::before {
      opacity: 1;
  }
  
  /* 4. ACTIVO - Línea más visible */
  [data-paneton-tree-id="${this.id}"] .pntn-tree-node__line-segment.line-active::before {
      border-left-color: var(--pntn-tree-color-segment-active);
      border-left-width: 3px;  
      transform: scaleX(0.4);
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
          [data-paneton-tree][data-paneton-tree-id="${this.id}"]:hover .pntn-tree-node__toggler-icon { 
              color: var(--pntn-tree-color-icon-focus); 
          }
          [data-paneton-tree-id="${this.id}"] .pntn-tree-node__content { 
              min-width: 0; 
              display: flex; 
              align-items: center; 
              gap: 4px; 
              padding: var(--pntn-tree-size-node-vertical-padding) 0;
          }
          [data-paneton-tree-id="${this.id}"] .pntn-tree-node__label { 
              white-space: nowrap; 
              overflow: hidden; 
              text-overflow: ellipsis; 
          }
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
              text-align: center; 
          }
          [data-paneton-tree-id="${this.id}"] .pntn-tree-node__button > svg { 
              width: 14px; 
              height: 14px; 
          }
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-active .pntn-tree-node__button { 
              opacity: 0; 
          }
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-active .pntn-tree-node:hover .pntn-tree-node__button,
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-active .pntn-tree-node.is-selected .pntn-tree-node__button { 
              opacity: 1; 
          }
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-all .pntn-tree-node__button { 
              opacity: 0; 
          }
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-all:hover .pntn-tree-node__button { 
              opacity: 0.7; 
          }
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-all .pntn-tree-node:hover .pntn-tree-node__button,
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-all .pntn-tree-node__button:hover,
          [data-paneton-tree-id="${this.id}"].pntn-tree--autohide-all .pntn-tree-node.is-selected .pntn-tree-node__button { 
              opacity: 1; 
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
  
            if (this.options.autoHideButtons === 'all') {
                this.container.classList.add('pntn-tree--autohide-all');
            } else if (this.options.autoHideButtons === 'activeNode') {
                this.container.classList.add('pntn-tree--autohide-active');
            }
  
            if (!this.options.showSegments) {
                this.container.classList.add('pntn-tree--hide-segments');
            }
  
            // Apply theme
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
                console.log(`Paneton.Tree: Measured row height: ${this.state.rowHeight}px, Pool size: ${this.state.totalPoolSize}`);
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
                buttonEl.innerHTML = Paneton.Tree.DEFAULT_CUBE_ICON;
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
    _updateRow(element, nodeInfo, index, options = {}) {
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
        element.classList.toggle('is-expanded', hasChildren && nodeData.expanded !== false);
  
         const label = element.querySelector('.pntn-tree-node__label');
        label.textContent = nodeData.name;
        const icon = element.querySelector('.pntn-tree-node__icon');
        if (nodeData.icon) {
            icon.textContent = nodeData.icon;
            icon.style.display = '';
        } else {
            icon.style.display = 'none';
        }
  
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
         * Updates the buttons for a row element.
         * @param {HTMLElement} element - The row element.
         * @param {object} nodeData - The node data.
         * @param {string} path - The node path.
         * @private
         */
        _updateRowButtons(element, nodeData, path) {
            const actionsContainer = element.querySelector('.pntn-tree-node__actions');
            actionsContainer.innerHTML = '';
  
            if (nodeData.buttons && nodeData.buttons.length > 0) {
                nodeData.buttons.forEach((buttonData, buttonIndex) => {
                    const buttonEl = document.createElement('div');
                    buttonEl.className = 'pntn-tree-node__button';
                    buttonEl.innerHTML = buttonData.icon || Paneton.Tree.DEFAULT_CUBE_ICON;
                    if (buttonData.tooltip) buttonEl.title = buttonData.tooltip;
                    buttonEl.dataset.buttonIndex = buttonIndex;
                    buttonEl.dataset.nodePath = path;
                    actionsContainer.appendChild(buttonEl);
                });
            }
        }
  
        /**
         * The main virtual rendering loop (performance-critical function).
         * @private
         */
        _virtualRender(options = {})  {
            if (!this.viewport || !this.sizer) return;
  
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
        }
  
        /**
         * Handles scroll events with throttling for performance.
         * @private
         */
        _handleScroll() {
            if (!this._scrollThrottled) {
                this._scrollThrottled = true;
                requestAnimationFrame(() => {
                    this._virtualRender();
                    this._scrollThrottled = false;
                });
            }
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
            if (isFolder && (clickedToggler || this.options.expandOnClick)) {
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
  
        //--------------------------------------> END [ PRIVATE UTILITIES ... ]
  
    };
  
  }));
  //# sourceMappingURL=paneton.tree.js.map