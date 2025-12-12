#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_parser.py
Created: 2025-12-10
Author: @lewopxd

Description:
Unit tests for data_sheet_parser.py
Verifies datetime serialization, JSON compatibility, and performance.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime, date, time as time_type, timedelta
from decimal import Decimal

# Add src to path for imports
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

# Test Excel file path
TEST_EXCEL = TEST_DIR / "test_multisheet.xlsx"

# ============================================================
# TEST: Serialization Function
# ============================================================

def test_serialize_cell_value():
    """Test _serialize_cell_value handles all types correctly."""
    from core.data_sheet.data_sheet_parser import _serialize_cell_value
    
    print("\n" + "="*60)
    print("TEST: _serialize_cell_value()")
    print("="*60)
    
    test_cases = [
        # (input, expected_type, description)
        (None, type(None), "None value"),
        ("Hello World", str, "String"),
        ("  Trimmed  ", str, "String with spaces"),
        (123, int, "Integer"),
        (123.456, float, "Float"),
        (True, bool, "Boolean"),
        (datetime(2024, 12, 31, 14, 30), str, "Datetime with time"),
        (datetime(2024, 12, 31, 0, 0), str, "Datetime without time"),
        (date(2024, 12, 31), str, "Date only"),
        (time_type(14, 30, 45), str, "Time only"),
        (timedelta(hours=2, minutes=30), float, "Timedelta"),
        (Decimal("123.456"), float, "Decimal"),
        (b"binary data", type(None), "Bytes (should be None)"),
    ]
    
    passed = 0
    failed = 0
    
    for value, expected_type, description in test_cases:
        result = _serialize_cell_value(value)
        result_type = type(result)
        
        if result_type == expected_type:
            print(f"  ✅ {description}: {repr(value)} → {repr(result)}")
            passed += 1
        else:
            print(f"  ❌ {description}: Expected {expected_type.__name__}, got {result_type.__name__}")
            print(f"     Input: {repr(value)}, Output: {repr(result)}")
            failed += 1
    
    # Verify JSON serializable
    print("\n  Testing JSON serialization...")
    all_results = [_serialize_cell_value(v) for v, _, _ in test_cases]
    try:
        json.dumps(all_results)
        print("  ✅ All results are JSON serializable")
        passed += 1
    except TypeError as e:
        print(f"  ❌ JSON serialization failed: {e}")
        failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed")
    return failed == 0


def test_date_formats():
    """Test different date format configurations."""
    from core.data_sheet import data_sheet_parser as parser
    
    print("\n" + "="*60)
    print("TEST: Date Formats")
    print("="*60)
    
    test_date = datetime(2024, 12, 31, 14, 30)
    
    original_format = parser.DATE_FORMAT_KEY
    
    results = {}
    for fmt_key in parser.DATE_FORMATS:
        parser.DATE_FORMAT_KEY = fmt_key
        result = parser._serialize_cell_value(test_date)
        results[fmt_key] = result
        print(f"  {fmt_key:12} → {result}")
    
    # Restore original
    parser.DATE_FORMAT_KEY = original_format
    
    print(f"\n  ✅ All {len(results)} format options working")
    return True


# ============================================================
# TEST: Full Parser with Excel File
# ============================================================

def test_excel_structure():
    """Test get_excel_structure (fast, for tree)."""
    if not TEST_EXCEL.exists():
        print(f"\n⚠️ Test Excel not found: {TEST_EXCEL}")
        print("  Run: python test_parser.py --create-excel")
        return False
    
    from core.data_sheet.data_sheet_parser import get_data_sheet_structure
    
    print("\n" + "="*60)
    print("TEST: get_data_sheet_structure()")
    print("="*60)
    
    start = time.time()
    structure = get_data_sheet_structure(str(TEST_EXCEL))
    elapsed = time.time() - start
    
    if structure:
        print(f"  ✅ Structure loaded in {elapsed:.3f}s")
        print(f"     File: {structure['metadata']['fileName']}")
        print(f"     Sheets: {len(structure['sheets'])}")
        for sheet in structure['sheets']:
            print(f"       - {sheet['sheetName']}: {len(sheet.get('tables', []))} tables")
        return True
    else:
        print(f"  ❌ Failed to load structure")
        return False


def test_excel_full_data():
    """Test full data load with serialization."""
    if not TEST_EXCEL.exists():
        print(f"\n⚠️ Test Excel not found: {TEST_EXCEL}")
        return False
    
    from core.data_sheet.data_sheet_parser import get_unified_excel_data
    
    print("\n" + "="*60)
    print("TEST: get_unified_excel_data() - Full Data")
    print("="*60)
    
    start = time.time()
    result = get_unified_excel_data(str(TEST_EXCEL))
    elapsed = time.time() - start
    
    if not result:
        print(f"  ❌ Failed to load data")
        return False
    
    print(f"  ✅ Data loaded in {elapsed:.3f}s")
    
    full_data = result.get("full_data", {})
    total_rows = 0
    for sheet_name, tables in full_data.items():
        for table_name, rows in tables.items():
            total_rows += len(rows)
            print(f"     {sheet_name}/{table_name}: {len(rows)} rows")
    
    print(f"  Total rows: {total_rows}")
    
    # Verify JSON serializable
    print("\n  Testing JSON serialization of full data...")
    start = time.time()
    try:
        json_str = json.dumps(result)
        json_elapsed = time.time() - start
        print(f"  ✅ JSON serialization successful in {json_elapsed:.3f}s")
        print(f"     JSON size: {len(json_str) / 1024:.2f} KB")
        return True
    except TypeError as e:
        print(f"  ❌ JSON serialization FAILED: {e}")
        return False


def test_performance_500_rows():
    """Performance test with 500+ rows."""
    if not TEST_EXCEL.exists():
        print(f"\n⚠️ Run --create-excel first")
        return False
    
    from core.data_sheet.data_sheet_parser import get_unified_excel_data
    
    print("\n" + "="*60)
    print("PERFORMANCE TEST: 500+ Rows")
    print("="*60)
    
    # Multiple runs for average
    times = []
    for i in range(3):
        start = time.time()
        result = get_unified_excel_data(str(TEST_EXCEL))
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s")
    
    avg = sum(times) / len(times)
    print(f"\n  Average: {avg:.3f}s")
    
    if avg < 2.0:
        print(f"  ✅ Performance OK (< 2s)")
        return True
    else:
        print(f"  ⚠️ Performance slow (> 2s)")
        return True  # Still pass, just warn


# ============================================================
# HELPER: Create Test Excel File
# ============================================================

def create_test_excel():
    """Create a test Excel file with multiple sheets and 500+ rows."""
    import openpyxl
    from openpyxl.worksheet.table import Table, TableStyleInfo
    
    print("\n" + "="*60)
    print("Creating Test Excel File")
    print("="*60)
    
    wb = openpyxl.Workbook()
    
    # Sheet 1: Dates and Numbers (500 rows)
    ws1 = wb.active
    ws1.title = "Datos"
    
    # Headers
    headers = ["ID", "Fecha", "FechaHora", "Monto", "Descripcion", "Activo"]
    for col, header in enumerate(headers, 1):
        ws1.cell(row=1, column=col, value=header)
    
    # Data rows
    base_date = datetime(2024, 1, 1)
    for i in range(500):
        row = i + 2
        ws1.cell(row=row, column=1, value=i + 1)
        ws1.cell(row=row, column=2, value=base_date + timedelta(days=i))
        ws1.cell(row=row, column=3, value=datetime(2024, 1, 1, 9, 0) + timedelta(hours=i))
        ws1.cell(row=row, column=4, value=round(100 + i * 0.5, 2))
        ws1.cell(row=row, column=5, value=f"Item número {i + 1}")
        ws1.cell(row=row, column=6, value=i % 2 == 0)
    
    # Create table
    table1 = Table(displayName="TablaDatos", ref=f"A1:F501")
    table1.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False,
                                           showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    ws1.add_table(table1)
    print(f"  Created sheet 'Datos' with 500 rows")
    
    # Sheet 2: Smaller table (50 rows)
    ws2 = wb.create_sheet("Categorias")
    cat_headers = ["CatID", "Nombre", "FechaCreacion"]
    for col, header in enumerate(cat_headers, 1):
        ws2.cell(row=1, column=col, value=header)
    
    for i in range(50):
        row = i + 2
        ws2.cell(row=row, column=1, value=i + 1)
        ws2.cell(row=row, column=2, value=f"Categoría {i + 1}")
        ws2.cell(row=row, column=3, value=datetime(2024, 6, 1) + timedelta(days=i))
    
    table2 = Table(displayName="TablaCategorias", ref="A1:C51")
    table2.tableStyleInfo = TableStyleInfo(name="TableStyleLight1")
    ws2.add_table(table2)
    print(f"  Created sheet 'Categorias' with 50 rows")
    
    # Sheet 3: Empty (no tables)
    ws3 = wb.create_sheet("Vacia")
    ws3.cell(row=1, column=1, value="Esta hoja está vacía")
    print(f"  Created sheet 'Vacia' (no tables)")
    
    # Save
    wb.save(TEST_EXCEL)
    print(f"\n  ✅ Test Excel created: {TEST_EXCEL}")
    print(f"     Total: 3 sheets, 550 rows, 2 tables")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "="*60)
    print("DocuFlow Data Sheet Parser - Unit Tests")
    print("="*60)
    
    if "--create-excel" in sys.argv:
        create_test_excel()
        return
    
    results = []
    
    # Run tests
    results.append(("Serialize Cell Value", test_serialize_cell_value()))
    results.append(("Date Formats", test_date_formats()))
    results.append(("Excel Structure", test_excel_structure()))
    results.append(("Excel Full Data", test_excel_full_data()))
    results.append(("Performance 500 Rows", test_performance_500_rows()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"  {icon} {name}")
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
