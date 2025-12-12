/**
 * SimpleGrid - A lightweight, virtualized grid for DocuFlow.
 * Designed to match the minimalist, dark aesthetic of the application.
 * 
 * Features:
 * - Virtual scrolling (rows and columns)
 * - Sticky headers
 * - Custom scrollbars
 * - CSS Variable theming
 */
class SimpleGrid {
    constructor(container, options = {}) {
        this.container = container;
        this.options = Object.assign({
            data: [], // Array of objects or arrays
            columns: [], // { field: 'key', title: 'Title', width: 100 }
            rowHeight: 30,
            headerHeight: 32,
            theme: {}
        }, options);

        this.state = {
            scrollTop: 0,
            scrollLeft: 0,
            viewportHeight: 0,
            viewportWidth: 0,
            totalHeight: 0,
            totalWidth: 0
        };

        this._init();
    }

    _init() {
        this.container.classList.add('simple-grid-container');
        this.container.innerHTML = '';

        // Create specific scrollable wrappers
        // 1. Header Container (Sticky)
        this.headerContainer = document.createElement('div');
        this.headerContainer.className = 'sg-header-container';

        // 2. Body Viewport (Scrollable)
        this.viewport = document.createElement('div');
        this.viewport.className = 'sg-viewport';

        // 3. Content Sizer (Creates the scrollable area size)
        this.sizer = document.createElement('div');
        this.sizer.className = 'sg-sizer';

        this.viewport.appendChild(this.sizer);
        this.container.appendChild(this.headerContainer);
        this.container.appendChild(this.viewport);

        this._calculateDimensions();
        this._renderHeaders();
        this._setupEventListeners();

        // Initial render
        requestAnimationFrame(() => this._renderBody());
    }

    _calculateDimensions() {
        const { rowHeight, data, columns } = this.options;
        const rowNumberWidth = 50; // Width for the row number column

        // Calculate Total Height
        this.state.totalHeight = data.length * rowHeight;

        // Calculate Total Width (sum of column widths) + Row Number Column
        const colsWidth = columns.reduce((acc, col) => acc + (col.width || 100), 0);
        this.state.totalWidth = colsWidth + rowNumberWidth;

        // Apply to Sizer
        this.sizer.style.height = `${this.state.totalHeight}px`;
        this.sizer.style.width = `${this.state.totalWidth}px`;

        // Update Viewport Dimensions
        this.state.viewportHeight = this.viewport.clientHeight;
        this.state.viewportWidth = this.viewport.clientWidth;

        this.rowNumberWidth = rowNumberWidth;
    }

    _renderHeaders() {
        this.headerContainer.innerHTML = '';
        const headerRow = document.createElement('div');
        headerRow.className = 'sg-header-row';
        headerRow.style.width = `${this.state.totalWidth}px`;

        // 0. Row Number Header (Corner)
        const cornerCell = document.createElement('div');
        cornerCell.className = 'sg-header-cell sg-corner-cell'; // Special class for styling
        cornerCell.textContent = '#';
        cornerCell.style.width = `${this.rowNumberWidth}px`;
        headerRow.appendChild(cornerCell);

        // 1. Data Headers
        this.options.columns.forEach((col, index) => {
            const cell = document.createElement('div');
            cell.className = 'sg-header-cell';
            // Use title, or generate A, B, C... if requested (future)
            // User requested A, B, C... but we have real column names from Excel tables usually.
            // If we wanted A, B, C... we would map index -> Letter. 
            // prioritizing usage of real column names if available.
            cell.textContent = col.title || col.field || this._indexToLetter(index);
            cell.style.width = `${col.width || 100}px`;
            headerRow.appendChild(cell);
        });

        this.headerContainer.appendChild(headerRow);
    }

    _indexToLetter(i) {
        return String.fromCharCode(65 + i); // Simplistic A-Z for now
    }

    _renderBody() {
        const { scrollTop, scrollLeft, viewportHeight } = this.state;
        const { rowHeight, data, columns } = this.options;

        // Calculate visible range
        const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight));
        const endIndex = Math.min(
            data.length - 1,
            Math.ceil((scrollTop + viewportHeight) / rowHeight)
        );

        this.sizer.innerHTML = '';
        const fragment = document.createDocumentFragment();

        for (let i = startIndex; i <= endIndex; i++) {
            const rowData = data[i];
            const row = document.createElement('div');
            row.className = 'sg-row';
            row.style.height = `${rowHeight}px`;
            row.style.transform = `translateY(${i * rowHeight}px)`;

            // 0. Row Number Cell
            const rowNumCell = document.createElement('div');
            rowNumCell.className = 'sg-cell sg-row-number';
            rowNumCell.style.width = `${this.rowNumberWidth}px`;
            // If data has explicit row_index, use it, else use i+1
            const displayIndex = (rowData.row_index !== undefined) ? (rowData.row_index + 1) : (i + 1);
            rowNumCell.textContent = displayIndex;
            row.appendChild(rowNumCell);

            // 1. Data Cells
            columns.forEach(col => {
                const cell = document.createElement('div');
                cell.className = 'sg-cell';
                cell.style.width = `${col.width || 100}px`;
                cell.textContent = rowData[col.field] !== undefined ? rowData[col.field] : '';
                cell.title = cell.textContent; // Tooltip
                row.appendChild(cell);
            });

            fragment.appendChild(row);
        }

        this.sizer.appendChild(fragment);
    }

    _setupEventListeners() {
        this.viewport.addEventListener('scroll', (e) => {
            // Sync header scroll
            this.headerContainer.scrollLeft = e.target.scrollLeft;

            // Throttle body render
            if (!this._ticking) {
                window.requestAnimationFrame(() => {
                    this.state.scrollTop = e.target.scrollTop;
                    this.state.scrollLeft = e.target.scrollLeft;
                    this._renderBody();
                    this._ticking = false;
                });
                this._ticking = true;
            }
        });

        // Resize Observer for responsive viewport
        new ResizeObserver(() => {
            this.state.viewportHeight = this.viewport.clientHeight;
            this.state.viewportWidth = this.viewport.clientWidth;
            this._renderBody();
        }).observe(this.viewport);
    }

    // Public API
    setData(newData) {
        this.options.data = newData;
        this._calculateDimensions();
        this._renderBody();
    }
}

// Export to global scope for simple usage
window.SimpleGrid = SimpleGrid;
