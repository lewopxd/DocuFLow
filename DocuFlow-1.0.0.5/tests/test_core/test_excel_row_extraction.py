#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_excel_row_extraction.py
Created: 2025-11-05
Author: @lewopxd

Description:
Test script for isolated Core functions.
This script tests the 'get_row_data_sheet' parser without
launching the full UI application.
"""

import sys
import json
from pathlib import Path

# --- [ INICIO: AJUSTE DE PYTHONPATH (PARA SUB-CARPETA 'tests') ] ---
# Obtenemos la ruta de este archivo (.../tests/test_core)
current_dir = Path(__file__).parent
# Navegamos 2 niveles arriba para llegar a la raíz del proyecto
project_root = current_dir.parent.parent
# Apuntamos a la carpeta 'src'
src_path = project_root / 'src'

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
# --- [ FIN: AJUSTE DE PYTHONPATH ] ---

try:
    from core.data_sheet.data_sheet_parser import get_row_data_sheet
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'get_row_data_sheet'.")
    print(f"   Asegúrate de que la carpeta 'src' está en: {src_path}")
    print(f"   Error: {e}")
    sys.exit(1)


# -------------------------------------------------------------
# -------------------[   CONFIGURACIÓN DE PRUEBA   ]-----------
# -------------------------------------------------------------

# ===================================================================
# ==                                                               ==
# ==   IMPORTANTE: Modifica este diccionario con tus datos reales.  ==
# ==                                                               ==
# ===================================================================
TEST_CONFIG = {
    # Reemplaza con la ruta completa a tu archivo de prueba
    "filePath": r"C:\Users\Admin\Desktop\FASE3-APROBADOS\DB-JOVENES_F3.xlsx",
    
    # Reemplaza con el nombre exacto de la hoja
    "sheetName": "PRESENCIAL", 
    
    # Reemplaza con el nombre exacto de la Tabla con Nombre
    "tableName": "Table_1",
    
    # Define el rango de filas (1-based, fila 1 es el encabezado)
    "rangeConfig": {
        "type": "multiple_row", 
        "data": "2-5"  # <-- Solicita las filas 2, 3, 4 y 5 de la tabla
    },
    
    # Reemplaza con los nombres de columna exactos que quieres extraer
    "columns": ["NOMBRES", "APELLIDOS", "ESTADO INTERMEDIACION"]
}


# -------------------------------------------------------------
# -------------------[   EJECUCIÓN DE PRUEBA   ]---------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print(f"--- Iniciando prueba de 'get_row_data_sheet' ---")
    print(f"Archivo: {TEST_CONFIG.get('filePath')}")
    print(f"Hoja:    {TEST_CONFIG.get('sheetName')}")
    print(f"Tabla:   {TEST_CONFIG.get('tableName')}")
    print("-----------------------------------------------------")
    
    # Llamar a la función del Core
    row_data = get_row_data_sheet(TEST_CONFIG)
    
    # Imprimir el resultado
    if row_data is not None:
        print("✅ ¡Éxito! Datos extraídos:")
        # Usamos json.dumps para una impresión bonita (pretty-print)
        print(json.dumps(row_data, indent=2, ensure_ascii=False))
    else:
        print("❌ Falla: La función devolvió None.")
        
    print("-----------------------------------------------------")
    print("--- Prueba finalizada ---")