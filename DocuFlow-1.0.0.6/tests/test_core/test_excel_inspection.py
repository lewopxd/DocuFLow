#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:    test_excel_inspection.py
Author:  @lewopxd

Description:
Script de diagnóstico para probar la función 'get_data_sheet_structure'
del data_sheet_parser.

Lee un archivo Excel y vuelca su estructura (hojas, tablas, columnas)
como un diccionario JSON.
"""

import sys
import json
from pathlib import Path

# --- [ INICIO: AJUSTE DE PYTHONPATH ] ---
# Idéntico al de tu script de 'run' para encontrar el módulo 'core'
try:
    # Asume que este script está en 'tests/test_core/'
    current_dir = Path(__file__).parent 
    # Sube dos niveles a 'tests/' y luego a la raíz del proyecto
    project_root = current_dir.parent.parent 
    src_path = project_root / 'src'

    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        
    print(f"Ruta 'src' añadida a sys.path: {src_path}\n")
        
except NameError:
    # Fallback por si se ejecuta en un entorno donde __file__ no está definido
    print("Advertencia: No se pudo ajustar el sys.path automáticamente.")
    # Intentar un ajuste relativo
    sys.path.insert(0, str(Path.cwd().parent / 'src'))
    pass
# --- [ FIN: AJUSTE DE PYTHONPATH ] ---

try:
    # Ahora el import debería funcionar
    from core.data_sheet.data_sheet_parser import get_data_sheet_structure
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'get_data_sheet_structure'.")
    print(f"   Asegúrate de que la carpeta 'src' está en el PYTHONPATH.")
    print(f"   Ruta del proyecto calculada: {project_root}")
    print(f"   Error: {e}")
    sys.exit(1)

# --- [ 1. Definir el archivo a probar ] ---
# Copiado de tu script 'run_acta_generation_ACTUALIZACION.py'
EXCEL_FILE_TO_TEST = r"C:\Users\Admin\Desktop\FASE3-APROBADOS\DB-JOVENES_F3.xlsx"

# --- [ 2. Ejecución de la prueba ] ---
if __name__ == "__main__":
    print(f"--- Iniciando prueba de 'get_data_sheet_structure' (Inspector Excel) ---")
    print(f"Archivo: {EXCEL_FILE_TO_TEST}")
    print(f"{'-'*70}")

    try:
        # Llamar a la función del core
        structure_dict = get_data_sheet_structure(EXCEL_FILE_TO_TEST)

        if structure_dict:
            print("✅ ¡Inspección de Excel completada! Estructura detectada:\n")
            
            # Imprimir el diccionario como JSON formateado
            # ensure_ascii=False para manejar tildes (ej. "GUIAS")
            print(json.dumps(
                structure_dict, 
                indent=4, 
                ensure_ascii=False
            ))
            
            print(f"\n{'-'*70}")
            print("✓ Éxito: El parser de Excel funcionó.")

        else:
            print(f"❌ FALLO: La función 'get_data_sheet_structure' devolvió None.")
            print("   Revisa la consola en busca de errores de 'openpyxl' o 'path_utils'.")

    except Exception as e:
        print(f"❌ ERROR CRÍTICO DURANTE LA PRUEBA:")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()

    print(f"--- Prueba finalizada ---")