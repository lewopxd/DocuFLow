/**
 * ExcelViewer - Professional Excel-like grid viewer for DocuFlow
 * 
 * Features:
 * - Unified table structure (no alignment issues)
 * - Excel-style column letters (A, B, C... AA, AB...)
 * - Real column names as second header row
 * - Sticky row numbers and column headers
 * - Dynamic column widths based on content
 * - Sheet tabs for switching between sheets
 * - Cell selection with formula bar
 */
class ExcelViewer {
    constructor(container, options = {}) {
        this.container = container;
        this.options = Object.assign({
            sheets: {},           // { sheetName: { tableName: [rows...], ... }, ... }
            structure: null,      // The simple_data structure
            activeSheet: null,    // Currently active sheet name
            activeTable: null,    // Currently active table name
            maxColumnWidth: 300,
            minColumnWidth: 60,
            defaultColumnWidth: 100,
            rowHeight: 26,
            headerHeight: 28
        }, options);

        this.state = {
            columnWidths: [],
            columns: [],
            rows: [],
            selectedCell: null,   // { row, col }
            selectedRow: null
        };

        this._init();
    }

    // ==================== INITIALIZATION ====================

    _init() {
        this.container.innerHTML = '';
        this.container.classList.add('excel-viewer');

        // Main structure
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'ev-wrapper';

        // 1. Formula Bar (cell reference + content)
        this.formulaBar = document.createElement('div');
        this.formulaBar.className = 'ev-formula-bar';
        this.formulaBar.innerHTML = `
            <div class="ev-cell-ref">A1</div>
            <div class="ev-cell-content"></div>
        `;
        this.cellRefEl = this.formulaBar.querySelector('.ev-cell-ref');
        this.cellContentEl = this.formulaBar.querySelector('.ev-cell-content');

        // 2. Grid container (scrollable)
        this.gridContainer = document.createElement('div');
        this.gridContainer.className = 'ev-grid-container';

        // 3. The actual table
        this.table = document.createElement('table');
        this.table.className = 'ev-table';

        this.thead = document.createElement('thead');
        this.tbody = document.createElement('tbody');
        this.table.appendChild(this.thead);
        this.table.appendChild(this.tbody);

        this.gridContainer.appendChild(this.table);

        // 4. Sheet tabs bar
        this.tabsBar = document.createElement('div');
        this.tabsBar.className = 'ev-tabs-bar';

        this.wrapper.appendChild(this.formulaBar);
        this.wrapper.appendChild(this.gridContainer);
        this.wrapper.appendChild(this.tabsBar);
        this.container.appendChild(this.wrapper);

        // Determine initial sheet/table
        this._determineActiveSheetAndTable();
        this._renderTabs();
        this._prepareData();
        this._render();
        this._setupEventListeners();
    }

    // ==================== DATA PREPARATION ====================

    _determineActiveSheetAndTable() {
        const structure = this.options.structure;
        if (!structure || !structure.sheets) return;

        // Find first sheet with tables
        for (const sheet of structure.sheets) {
            if (sheet.tables && sheet.tables.length > 0) {
                this.options.activeSheet = sheet.sheetName;
                this.options.activeTable = sheet.tables[0].tableName;
                break;
            }
        }
    }

    _prepareData() {
        const { activeSheet, activeTable, structure, sheets } = this.options;
        if (!activeSheet || !activeTable || !structure) {
            this.state.columns = [];
            this.state.rows = [];
            return;
        }

        // Get columns from structure
        const sheetInfo = structure.sheets.find(s => s.sheetName === activeSheet);
        if (!sheetInfo) return;

        const tableInfo = sheetInfo.tables.find(t => t.tableName === activeTable);
        if (!tableInfo) return;

        this.state.columns = tableInfo.columns;

        // Get rows from sheets data
        if (sheets[activeSheet] && sheets[activeSheet][activeTable]) {
            this.state.rows = sheets[activeSheet][activeTable];
        } else {
            this.state.rows = [];
        }

        // Calculate column widths using canvas measuring
        this._calculateColumnWidths();

        // Calculate row number column width based on max row number
        this._calculateRowNumWidth();
    }

    _calculateRowNumWidth() {
        const { rows } = this.state;
        // Total rows = header (1) + data rows
        const maxRowNum = rows.length + 1;
        const numDigits = String(maxRowNum).length;

        // Use canvas to measure width
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.font = '11px "Segoe UI", system-ui, sans-serif';

        const textWidth = ctx.measureText(String(maxRowNum)).width;
        // Add minimal padding (4px each side)
        this.state.rowNumWidth = Math.max(20, Math.round(textWidth + 8));
    }

    _calculateColumnWidths() {
        // Let CSS handle column widths automatically with max-content
        // No JavaScript calculation needed - CSS will size columns perfectly
        this.state.columnWidths = null; // Not used anymore
    }

    // ==================== RENDERING ====================

    _render() {
        this._renderHeader();
        this._renderBody();
    }

    _renderHeader() {
        this.thead.innerHTML = '';
        const { columns, columnWidths } = this.state;

        // ROW 1: Letter row (A, B, C...) in thead
        const letterRow = document.createElement('tr');
        letterRow.className = 'ev-letter-row';

        // Corner cell (width calculated dynamically)
        const cornerTh = document.createElement('th');
        cornerTh.className = 'ev-corner';
        cornerTh.style.width = `${this.state.rowNumWidth}px`;
        cornerTh.style.minWidth = `${this.state.rowNumWidth}px`;
        cornerTh.textContent = '';
        letterRow.appendChild(cornerTh);

        // Letter headers - no fixed width, CSS handles it
        columns.forEach((colName, i) => {
            const th = document.createElement('th');
            th.className = 'ev-letter-cell';
            th.textContent = this._indexToLetter(i);
            letterRow.appendChild(th);
        });

        this.thead.appendChild(letterRow);

        // ROW 2: Column Names row - NOW IN THEAD for proper sticky behavior
        const namesRow = document.createElement('tr');
        namesRow.className = 'ev-names-row';
        namesRow.dataset.rowIndex = '-1'; // Use -1 for header row (will display as row 1)

        const namesRowNum = document.createElement('th');
        namesRowNum.className = 'ev-corner ev-row-num-header';
        namesRowNum.style.width = `${this.state.rowNumWidth}px`;
        namesRowNum.style.minWidth = `${this.state.rowNumWidth}px`;
        namesRowNum.textContent = '1';
        namesRow.appendChild(namesRowNum);

        columns.forEach((colName, colIndex) => {
            const th = document.createElement('th');
            th.className = 'ev-cell ev-name-cell';
            th.dataset.rowIndex = '-1';
            th.dataset.colIndex = colIndex;
            th.textContent = colName;
            th.title = colName;
            namesRow.appendChild(th);
        });

        this.thead.appendChild(namesRow);
    }

    _renderBody() {
        this.tbody.innerHTML = '';
        const { columns, rows, columnWidths } = this.state;

        // Empty state check
        if (rows.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = columns.length + 1;
            td.className = 'ev-empty';
            td.textContent = 'No data available';
            tr.appendChild(td);
            this.tbody.appendChild(tr);
            return;
        }

        // DATA ROWS: Start from Row 2 (display rowIndex + 2 because row 1 is headers in thead)
        rows.forEach((rowData, rowIndex) => {
            const tr = document.createElement('tr');
            tr.dataset.rowIndex = rowIndex;

            // Row number cell (rowIndex + 2 because row 1 is headers)
            const rowNumTd = document.createElement('td');
            rowNumTd.className = 'ev-row-num';
            rowNumTd.style.width = `${this.state.rowNumWidth}px`;
            rowNumTd.style.minWidth = `${this.state.rowNumWidth}px`;
            rowNumTd.textContent = rowIndex + 2;
            rowNumTd.dataset.rowIndex = rowIndex;
            tr.appendChild(rowNumTd);

            // Data cells - no fixed width, CSS handles it
            columns.forEach((colName, colIndex) => {
                const td = document.createElement('td');
                td.className = 'ev-cell';
                td.dataset.rowIndex = rowIndex;
                td.dataset.colIndex = colIndex;

                const value = rowData[colName];
                td.textContent = value !== undefined && value !== null ? value : '';
                td.title = td.textContent;

                tr.appendChild(td);
            });

            this.tbody.appendChild(tr);
        });
    }

    _renderTabs() {
        this.tabsBar.innerHTML = '';
        const structure = this.options.structure;
        if (!structure || !structure.sheets) return;

        structure.sheets.forEach(sheet => {
            // Only show sheets that have tables
            if (!sheet.tables || sheet.tables.length === 0) return;

            const tab = document.createElement('button');
            tab.className = 'ev-tab';
            tab.textContent = sheet.sheetName;

            if (sheet.sheetName === this.options.activeSheet) {
                tab.classList.add('ev-tab-active');
            }

            tab.addEventListener('click', () => {
                this.setActiveSheet(sheet.sheetName, sheet.tables[0].tableName);
            });

            this.tabsBar.appendChild(tab);
        });
    }

    // ==================== EVENT HANDLING ====================

    _setupEventListeners() {
        // Cell click for selection in tbody
        this.tbody.addEventListener('click', (e) => {
            const cell = e.target.closest('.ev-cell');
            if (cell) {
                const rowIndex = parseInt(cell.dataset.rowIndex, 10);
                const colIndex = parseInt(cell.dataset.colIndex, 10);
                this._selectCell(rowIndex, colIndex);
            }
        });

        // Row number click for row selection
        this.tbody.addEventListener('click', (e) => {
            const rowNum = e.target.closest('.ev-row-num');
            if (rowNum) {
                const rowIndex = parseInt(rowNum.dataset.rowIndex, 10);
                this._selectRow(rowIndex);
            }
        });

        // Header cell click for selection (row 1 = column names)
        this.thead.addEventListener('click', (e) => {
            const cell = e.target.closest('.ev-cell');
            if (cell) {
                const rowIndex = parseInt(cell.dataset.rowIndex, 10);
                const colIndex = parseInt(cell.dataset.colIndex, 10);
                this._selectCell(rowIndex, colIndex);
            }
        });
    }

    _selectCell(rowIndex, colIndex) {
        // Remove previous selection
        this._clearSelection();

        // Set new selection
        this.state.selectedCell = { row: rowIndex, col: colIndex };
        this.state.selectedRow = null;

        // Find and mark the cell (could be in tbody or thead)
        let cell = this.tbody.querySelector(
            `td.ev-cell[data-row-index="${rowIndex}"][data-col-index="${colIndex}"]`
        );
        // If not found in tbody, check thead (for header row)
        if (!cell) {
            cell = this.thead.querySelector(
                `th.ev-cell[data-row-index="${rowIndex}"][data-col-index="${colIndex}"]`
            );
        }
        if (cell) {
            cell.classList.add('ev-selected');
        }

        // Highlight the row (could be in tbody or thead)
        let row = this.tbody.querySelector(`tr[data-row-index="${rowIndex}"]`);
        if (!row) {
            row = this.thead.querySelector(`tr[data-row-index="${rowIndex}"]`);
        }
        if (row) {
            row.classList.add('ev-row-active');
            const rowNum = row.querySelector('.ev-row-num, .ev-row-num-header');
            if (rowNum) rowNum.classList.add('ev-row-num-active');
        }

        // Update formula bar
        const colLetter = this._indexToLetter(colIndex);
        const colName = this.state.columns[colIndex];
        let displayRow, cellValue;

        if (rowIndex === -1) {
            // Row 1 (headers)
            displayRow = 1;
            cellValue = colName;
        } else {
            // Data rows (rowIndex + 2 because row 1 is headers)
            displayRow = rowIndex + 2;
            cellValue = this.state.rows[rowIndex]?.[colName] ?? '';
        }

        const cellRef = `${colLetter}${displayRow}`;
        this.cellRefEl.textContent = cellRef;
        this.cellContentEl.textContent = cellValue;
    }

    _selectRow(rowIndex) {
        // Remove previous selection
        this._clearSelection();

        // Set new selection
        this.state.selectedRow = rowIndex;
        this.state.selectedCell = null;

        // Highlight entire row
        const row = this.tbody.querySelector(`tr[data-row-index="${rowIndex}"]`);
        if (row) {
            row.classList.add('ev-row-selected');
            const rowNum = row.querySelector('.ev-row-num');
            if (rowNum) rowNum.classList.add('ev-row-num-active');
        }

        // Update formula bar
        const displayRow = rowIndex === -1 ? 1 : rowIndex + 2;
        this.cellRefEl.textContent = `Row ${displayRow}`;
        this.cellContentEl.textContent = '';
    }

    _clearSelection() {
        // Remove cell selection (from both tbody and thead)
        this.table.querySelectorAll('.ev-selected').forEach(el => el.classList.remove('ev-selected'));

        // Remove row highlight (from both tbody and thead)
        this.table.querySelectorAll('.ev-row-active').forEach(el => el.classList.remove('ev-row-active'));

        // Remove row selection
        this.table.querySelectorAll('.ev-row-selected').forEach(el => el.classList.remove('ev-row-selected'));

        // Remove row num highlight (from both tbody and thead)
        this.table.querySelectorAll('.ev-row-num-active').forEach(el => el.classList.remove('ev-row-num-active'));
    }

    // ==================== UTILITIES ====================

    _indexToLetter(index) {
        let letter = '';
        let i = index;
        while (i >= 0) {
            letter = String.fromCharCode(65 + (i % 26)) + letter;
            i = Math.floor(i / 26) - 1;
        }
        return letter;
    }

    // ==================== PUBLIC API ====================

    setActiveSheet(sheetName, tableName) {
        this.options.activeSheet = sheetName;
        this.options.activeTable = tableName;
        this._prepareData();
        this._renderTabs();
        this._render();
        this._clearSelection();
        this.cellRefEl.textContent = 'A1';
        this.cellContentEl.textContent = '';
    }

    setData(sheets, structure) {
        this.options.sheets = sheets;
        this.options.structure = structure;
        this._determineActiveSheetAndTable();
        this._prepareData();
        this._renderTabs();
        this._render();
    }

    destroy() {
        this.container.innerHTML = '';
        this.container.classList.remove('excel-viewer');
    }
}

// Export to global scope
window.ExcelViewer = ExcelViewer;
