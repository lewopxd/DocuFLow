#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_template_inspection.py
Created: 2025-11-05
Author: @lewopxd

Description:
Test script for isolated Core functions.
This script tests the 'get_template_info' parser from
the ms_word package to find all placeholders.
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
    from core.ms_word.template_parser import get_template_info
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'get_template_info'.")
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
TEST_CONFIG_SCAN = {
    # 1. Reemplaza con la ruta completa a tu PLANTILLA .docx
    
    "source_path": r"C:\Users\Admin\Desktop\FASE3-APROBADOS\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS\ACTA 3 - POSTULACION VACANTE\03 -Intermediación laboral - auto postulación a vacante laboral.docx",
    # 2. Define los tipos de placeholders que quieres buscar
    "definitions": [
        {
            "type": "text", 
            "prefix": "${{", 
            "suffix": "}}"
        },
        {
            "type": "image", 
            "prefix": "$im{{", 
            "suffix": "}}"
        },
        {
            "type": "legacy",
            "prefix": "{{", 
            "suffix": "}}"
        }
    ]
}


# -------------------------------------------------------------
# -------------------[   EJECUCIÓN DE PRUEBA   ]---------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print(f"--- Iniciando prueba de 'get_template_info' (Inspector) ---")
    print(f"Plantilla: {TEST_CONFIG_SCAN.get('source_path')}")
    print("---------------------------------------------------------------")
    
    # Llamar a la función del Core
    result_log = get_template_info(TEST_CONFIG_SCAN)
    
    # Imprimir el resultado
    print("✅ ¡Inspección completada! Resumen del log:")
    print(json.dumps(result_log, indent=2, ensure_ascii=False))
        
    print("---------------------------------------------------------------")
    
    if result_log.get("success"):
        stats = result_log.get("stats", {})
        print(f"✓ Éxito: Se encontraron {stats.get('total_unique_tags')} placeholders únicos.")
    else:
        print(f"❌ Falla: {result_log.get('error')}")

    print("--- Prueba finalizada ---")