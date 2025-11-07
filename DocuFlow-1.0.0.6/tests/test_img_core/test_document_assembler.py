#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_document_assembler.py
Created: 2025-11-06
Author: @lewopxd

Description:
Test script for the main "Document Assembler" orchestrator.
(v7: Habilitada la neutralización de página en blanco)
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
    from core.ms_word.document_assembler import assemble_document_with_media
except ImportError as e:
    print("❌ ERROR CRÍTICO: No se pudo importar 'assemble_document_with_media'.")
    print(f"   Asegúrese de que la ruta '{src_path}' es correcta y contiene 'core/ms_word/document_assembler.py'.")
    print(f"   Error de importación: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   TEST CONFIGURATION   ]----------------
# -------------------------------------------------------------

def get_test_config():
    """
    Construye el diccionario de configuración para la prueba
    del Ensamblador (Imágenes + PDFs).
    """
    
    # --- [ POLÍTICA PARA IMÁGENES ESTÁNDAR ] ---
    smart_policy_auto = {
        "width": "auto",
        "height": "auto",
        "orientation_match_scale": 1.0, 
        "allow_upscale": False,
        "alignment": "CENTER",
        "compression": {
            "max_width_px": 3000,
            "max_height_px": 3000,
            "quality": 90
        },
        "output_format": "PNG"
    }

    # --- [ POLÍTICA PARA PDFs ] ---
    pdf_policy = smart_policy_auto.copy()
    pdf_policy["orientation_match_scale"] = 0.85
    pdf_policy["pdf_options"] = {
        "dpi": 150,
        "page_ranges": None # Todas las páginas
    }
    
    
    base_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST"
    
    source_doc = rf"{base_path}\ACTA 1 - APE - (ACTUALIZACION) - ANGIE LORENA RAMIREZ BARRETO.docx"
    output_dir = rf"{base_path}\OUTPUT"
    
    # --- Rutas de Imágenes ---
    img_1_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - CERTIFICADO REGISTRO APE.jpg"
    img_2_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - ACTUALIZACION.png"

    # --- Ruta de PDF ---
    pdf_1_path = r"C:\Users\Admin\Desktop\PLAYGROUND\IMG_TEST\ANGIE LORENA RAMIREZ BARRETO\FASE 3 - INTERMEDIACION\SOPORTES\01 - HV.pdf"


    test_config = {
        "source_path": source_doc,
        "target_path": str(Path(output_dir) / "TEST_ASSEMBLER_RESULT_FINAL.docx"), 
        
        "overwrite": True,
        "author": "Test Assembler v7 (No Blank Page)",
        "debug": True,
        
        # --- [ NUEVA CONFIGURACIÓN ] ---
        "remove_trailing_blank_page": True,
        
        # --- MAPA DE IMÁGENES ESTÁNDAR ---
        "image_map": [
            {
                "placeholder": "$IMG{{ADJUNTO CERTIFICACION APE}}",
                "image_path": img_1_path,
                "layout_policy": smart_policy_auto
            },
            {
                "placeholder": "$IMG{{PANTALLAZO ACTUALIZACION}}",
                "image_path": img_2_path,
                "layout_policy": smart_policy_auto
            }
        ],
        
        # --- MAPA DE PDFs ---
        "pdf_map": [
            {
                "placeholder": "$PDF{{PDF HV}}",
                "pdf_path": pdf_1_path,
                "layout_policy": pdf_policy
            }
        ]
    }
    
    return test_config

# -------------------------------------------------------------
# -------------------[   EXECUTION   ]-------------------------
# -------------------------------------------------------------

def run_test():
    """
    Ejecuta la prueba del ENSAMBLADOR DE DOCUMENTOS.
    """
    print("╔════════════════════════════════════════════╗")
    print("║  INICIANDO PRUEBA DEL ENSAMBLADOR (v7)     ║")
    print("╚════════════════════════════════════════════╝")
    
    config = get_test_config()
    
    print("\n[CONFIGURACIÓN DE PRUEBA CARGADA]:")
    print(f"  Fuente: {config['source_path']}")
    print(f"  Salida: {config['target_path']}")
    print(f"  Jobs IMG: {len(config['image_map'])} imágenes")
    print(f"  Jobs PDF: {len(config['pdf_map'])} PDFs")
    print("-------------------------------------------------")
    
    status_report = assemble_document_with_media(config)
    
    print("-------------------------------------------------")
    print("\n[REPORTE FINAL DE LA EJECUCIÓN]:")
    
    pprint.pprint(status_report)
    
    if status_report.get("error"):
        if status_report.get("success"):
             print("\n⚠️ PRUEBA FALLIDA (ÉXITO PARCIAL).")
             print(f"   El archivo fue generado, pero ocurrieron errores.")
             print(f"   Error: {status_report['error']}")
        else:
            print(f"\n❌ PRUEBA FALLIDA.")
            print(f"   Error: {status_report['error']}")

    elif status_report.get("success"):
        print("\n✅ PRUEBA FINALIZADA CON ÉXITO.")
        print(f"  Verifique el archivo: {status_report['target_path']}")
        
    else:
         print(f"\n❌ PRUEBA FALLIDA (Estado desconocido).")


if __name__ == "__main__":
    run_test()