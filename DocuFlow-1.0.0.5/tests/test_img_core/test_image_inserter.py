#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_image_inserter.py (v2 - Diagnostic)
Created: 2025-11-06
Author: @lewopxd
Last Updated: 2025-11-06

Description:
DIAGNOSTIC Test script v2 for the v6 image insertion module.
Uses the v2 docx_analyzer to perform a deep-dive consistency
check on the output file.
"""

import sys
import pprint
from pathlib import Path

# --- [ INICIO: AJUSTE DE PYTHONPATH ] ---
try:
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent 
    src_path = project_root / 'src'

    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        
    print(f"Ruta 'src' añadida a sys.path: {src_path}")
        
except NameError:
    print("Advertencia: No se pudo ajustar el sys.path automáticamente.")
    pass
# --- [ FIN: AJUSTE DE PYTHONPATH ] ---

try:
    from core.ms_word.image_inserter import generate_document_with_images
    # --- [ INICIO: IMPORTAR ANALIZADOR v2 ] ---
    from core.utils.docx_analyzer import analyze_docx_structure
    # --- [ FIN: IMPORTAR ANALIZADOR v2 ] ---
except ImportError as e:
    print("❌ ERROR CRÍTICO: No se pudo importar 'generate_document_with_images' o 'analyze_docx_structure'.")
    print(f"   Asegúrese de que la ruta '{src_path}' es correcta y contiene 'core/ms_word' y 'core/utils'.")
    print(f"   Error de importación: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   TEST CONFIGURATION   ]----------------
# -------------------------------------------------------------

def get_test_config():
    """
    Construye el diccionario de configuración para la prueba.
    (Función sin cambios)
    """
    
    smart_policy = {
        "width": "auto",
        "height": "auto",
        "orientation_match_scale": 0.6,
        "allow_upscale": False,
        "alignment": "CENTER"
    }
    
    base_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST"
    source_doc = rf"{base_path}\ACTA 1 - APE - (ACTUALIZACION) - ANGIE LORENA RAMIREZ BARRETO.docx"
    output_dir = rf"{base_path}\OUTPUT"
    
    img_1_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - CERTIFICADO REGISTRO APE.jpg"
    img_2_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - ACTUALIZACION.png"

    test_config = {
        "source_path": source_doc,
        "target_directory": output_dir,
        "target_filename": "TEST_RESULT_ACTA.docx",
        "overwrite": True,
        "author": "Test Inserter v6",
        "debug": True,
        "image_map": [
            {
                "placeholder": "$IMG{{ADJUNTO CERTIFICACION APE}}",
                "image_path": img_1_path,
                "layout_policy": smart_policy
            },
            {
                "placeholder": "$IMG{{PANTALLAZO ACTUALIZACION}}",
                "image_path": img_2_path,
                "layout_policy": smart_policy
            }
        ]
    }
    
    return test_config

# -------------------------------------------------------------
# -------------------[   EXECUTION (DIAGNOSTIC v2) ]-----------
# -------------------------------------------------------------

def run_test():
    """
    Ejecuta la prueba de inserción de imagen CON ANÁLISIS PROFUNDO.
    """
    print("╔════════════════════════════════════════════╗")
    print("║   INICIANDO PRUEBA DE DIAGNÓSTICO (v7)     ║")
    print("╚════════════════════════════════════════════╝")
    
    config = get_test_config()
    source_file = config['source_path']
    target_file = str(Path(config['target_directory']) / config['target_filename'])
    
    # --- [ INICIO: ANÁLISIS ANTES ] ---
    print("\n" + "="*70)
    print(f"--- 1. ANALIZANDO ESTRUCTURA (ANTES): {source_file}")
    print("="*70)
    report_before = analyze_docx_structure(source_file)
    pprint.pprint(report_before)
    # --- [ FIN: ANÁLISIS ANTES ] ---

    print("\n" + "="*70)
    print(f"--- 2. EJECUTANDO INSERCIÓN (debug=True)")
    print("="*70)
    
    # Ejecutar la función principal (v9, con el bug)
    status_report = generate_document_with_images(config)
    
    print("\n" + "="*70)
    print(f"--- 3. REPORTE DE EJECUCIÓN")
    print("="*70)
    pprint.pprint(status_report)

    # --- [ INICIO: ANÁLISIS DESPUÉS ] ---
    if status_report["target_path"] and Path(status_report["target_path"]).exists():
        print("\n" + "="*70)
        print(f"--- 4. ANALIZANDO ESTRUCTURA (DESPUÉS): {target_file}")
        print("="*70)
        report_after = analyze_docx_structure(target_file)
        pprint.pprint(report_after)
        
        # Comparación simple
        print("\n" + "="*70)
        print("--- 5. COMPARACIÓN RÁPIDA ---")
        print(f"  Media files (ANTES): {len(report_before.get('media_files_found', []))}")
        print(f"  Media files (DESPUÉS): {len(report_after.get('media_files_found', []))}")
        print("\n  REPORTE DE CONSISTENCIA (DESPUÉS):")
        pprint.pprint(report_after.get("consistency_report", {}))
        print("="*70)
        
    # --- [ FIN: ANÁLISIS DESPUÉS ] ---

    if status_report["success"]:
        print("\n✅ EJECUCIÓN FINALIZADA (pero verifique el 'DESPUÉS' para corrupción).")
    else:
        print(f"\n❌ PRUEBA FALLIDA.")

if __name__ == "__main__":
    run_test()

# --------------------------------------> END [ EXECUTION ... ]