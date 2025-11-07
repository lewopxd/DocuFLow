#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_word_generation.py
Created: 2025-11-05
Author: @lewopxd

Description:
Test script for isolated Core functions.
This script tests the 'generate_document_from_template' function
from the ms_word package without launching the full UI.
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
    from core.ms_word.replace_holders_text import generate_document_from_template
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'generate_document_from_template'.")
    print("Asegúrate de que 'src/' existe, tu venv está activado y 'python-docx' está instalado.")
    print(f"Error: {e}")
    sys.exit(1)


# -------------------------------------------------------------
# -------------------[   CONFIGURACIÓN DE PRUEBA   ]-----------
# -------------------------------------------------------------

# ===================================================================
# ==                                                               ==
# ==   IMPORTANTE: Modifica este diccionario con tus datos reales.  ==
# ==                                                               ==
# ===================================================================
TEST_CONFIG_WORD = {
    # --- Rutas ---
    
    "source_path": r"C:\Users\Admin\Desktop\JOSE\CARPETAS JOVENES\CARPETAS JOVENES\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS\ACTA INCUMPLIMIENTO.docx",
    "target_directory": r"C:\Users\Admin\Desktop\JOSE\CARPETAS JOVENES\CARPETAS JOVENES\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS\test",
    "target_filename": "documento_generado_01.docx",

    # --- Opciones de Guardado ---
    "overwrite": True,

    # --- Datos de Reemplazo ---
    "replacements": {
        "{{NOMBRE}}": "Carlos Sanchez",
        "{{DEL_LA}}": "del",
        "{{EL_LA}}": "el",
        "{{TAG_INEXISTENTE}}": "Este tag no se encontrará"
    },
    
    # --- Opciones de Formato ---
    "clear_highlight": True,
    
    # --- [ NUEVOS CAMPOS DE METADATOS ] ---
    "author": "DocuFlow Bot",
    "last_modified_by": "Sistema de Automatización"
    # --- [ FIN DE NUEVOS CAMPOS ] ---
}


# -------------------------------------------------------------
# -------------------[   EJECUCIÓN DE PRUEBA   ]---------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print(f"--- Iniciando prueba de 'generate_document_from_template' ---")
    print(f"Plantilla: {TEST_CONFIG_WORD.get('source_path')}")
    print(f"Destino:   {TEST_CONFIG_WORD.get('target_directory')}\{TEST_CONFIG_WORD.get('target_filename')}")
    print("---------------------------------------------------------------")
    
    # Llamar a la función del Core
    result_log = generate_document_from_template(TEST_CONFIG_WORD)
    
    # Imprimir el resultado
    print("✅ ¡Proceso completado! Resumen del log:")
    print(json.dumps(result_log, indent=2, ensure_ascii=False))
        
    print("---------------------------------------------------------------")
    
    if result_log.get("success"):
        print(f"✓ Archivo guardado en: {result_log.get('target_path')}")
        if result_log.get("details", {}).get("metadata_updated"):
            print("✓ Los metadatos (Autor/Modificado por) fueron actualizados.")
    else:
        print(f"❌ Falla: {result_log.get('error')}")

    print("--- Prueba finalizada ---")