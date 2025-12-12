#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_image_inserter_manual.py
Created: 2025-11-06
Author: @lewopxd

Description:
Test script for the "Nuclear Option" (manual) image insertion module.
This script calls 'generate_document_with_images_manual' to validate
the full ZIP-to-ZIP transformation pipeline.
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
    from core.ms_word.image_inserter_manual import generate_document_with_images_manual
except ImportError as e:
    print("❌ ERROR CRÍTICO: No se pudo importar 'generate_document_with_images_manual'.")
    print(f"   Asegúrese de que la ruta '{src_path}' es correcta y contiene 'core/ms_word/image_inserter_manual.py'.")
    print(f"   Error de importación: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   TEST CONFIGURATION   ]----------------
# -------------------------------------------------------------

def get_test_config():
    """
    Construye el diccionario de configuración para la prueba.
    ACTUALIZADO para trabajar con la v2 del inserter.
    """
    
    # Política inteligente con nuevas características v2
    smart_policy = {
        "width": "auto",
        "height": "auto",
        "orientation_match_scale": 1,
        "allow_upscale": True,
        "alignment": "CENTER",
        
        # --- NUEVAS OPCIONES v2 ---
        "turn_to_fit": False,        # Auto-rotación si mejora el fit
        "rotate": 0,                 # Rotación manual (0, 90, -90, 180)
        "flip_horizontal": False,    # Espejo horizontal
        "flip_vertical": False,      # Espejo vertical
        
        # Compresión opcional
        "compression": {
            "max_width_px": 3000,
            "max_height_px": 3000,
            "max_file_size_kb": 800,
            "quality": 90
        },
        "output_format": "PNG"       # "PNG", "JPEG", o "AUTO"
    }

    
    base_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST"
    
    source_doc = rf"{base_path}\ACTA 1 - APE - (ACTUALIZACION) - ANGIE LORENA RAMIREZ BARRETO.docx"
    output_dir = rf"{base_path}\OUTPUT"
    
    img_1_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - CERTIFICADO REGISTRO APE.jpg"
    img_2_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - ACTUALIZACION.png"

    test_config = {
        "source_path": source_doc,
        "target_directory": output_dir,
        "target_filename": "TEST_MANUAL_RESULT_ACTA.docx",
        
        "overwrite": True,
        "author": "Test Inserter v10 (Manual)",
        "debug": True,  # <-- ACTIVADO
        
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
# -------------------[   EXECUTION   ]-------------------------
# -------------------------------------------------------------

def run_test():
    """
    Ejecuta la prueba de inserción de imagen MANUAL.
    """
    print("╔════════════════════════════════════════════╗")
    print("║   INICIANDO PRUEBA DEL MOTOR MANUAL (v10)  ║")
    print("╚════════════════════════════════════════════╝")
    
    config = get_test_config()
    
    print("\n[CONFIGURACIÓN DE PRUEBA CARGADA]:")
    print(f"  Fuente: {config['source_path']}")
    print(f"  Salida: {Path(config['target_directory']) / config['target_filename']}")
    print(f"  Jobs: {len(config['image_map'])} imágenes a insertar")
    print("-------------------------------------------------")
    
    status_report = generate_document_with_images_manual(config)
    
    print("-------------------------------------------------")
    print("\n[REPORTE FINAL DE LA EJECUCIÓN]:")
    
    pprint.pprint(status_report)
    
    if status_report["success"]:
        print("\n✅ PRUEBA FINALIZADA CON ÉXITO (o parcialmente).")
        print(f"  Verifique el archivo: {status_report['target_path']}")
    else:
        print(f"\n❌ PRUEBA FALLIDA.")
        print(f"   Error: {status_report['error']}")

if __name__ == "__main__":
    run_test()

# --------------------------------------> END [ EXECUTION ... ]