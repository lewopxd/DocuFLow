#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_bulk_generation.py
Created: 2025-11-05
Author: @lewopxd

Description:
Test script for the main orchestrator function (v2 - Refactored).
Tests reading from Excel and bulk-generating Word documents using
the new "transforms" system, including "NA" cleanup with word boundaries.
"""

import sys
import json
from pathlib import Path

# --- [ INICIO: AJUSTE DE PYTHONPATH (PARA SUB-CARPETA 'tests') ] ---
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
    from core.orchester.main_orchester import execute_bulk_document_job
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'execute_bulk_document_job'.")
    print(f"   Asegúrate de que la carpeta 'src' está en el PYTHONPATH.")
    print(f"   Error: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   CONFIGURACIÓN DE PRUEBA   ]-----------
# -------------------------------------------------------------

BULK_JOB_CONFIG = {
    
    # --- SECCIÓN 1: EXTRACCIÓN DE DATOS ---
    "excel_config": {
        "filePath": r"C:\Users\Admin\Desktop\PLAYGROUND\DB-JOVENES_PLAYGROUND.xlsx",
        "sheetName": "PRESENCIAL", 
        "tableName": "Table_1",
        "rangeConfig": {
            "type": "all", 
            "data": None
        },
        "columns": ["PRONOMBRE", "NOMBRES", "APELLIDOS", "ESTADO INTERMEDIACION"] 
    },

    # --- SECCIÓN 2: PLANTILLA DE DOCUMENTO ---
    "template_config": {
        "source_path": r"C:\Users\Admin\Desktop\PLAYGROUND\PLANTILLAS ACTAS\ACTA INCUMPLIMIENTO.docx",
        "target_directory": r"C:\Users\Admin\Desktop\PLAYGROUND\OUTPUT", 
        "clear_highlight": True,
        "author": "DocuFlow Test Script",
        "last_modified_by": "DocuFlow Test Script"
    },

    # --- SECCIÓN 3: CONFIGURACIÓN DEL TRABAJO ---
    "job_config": {
        
        "filter_rules": {
            "column": "ESTADO INTERMEDIACION",
            "operator": "equal",
            "value": "INCUMPLIMIENTO"
        },
        
        "direct_mapping": {},
        
        "computed_mapping": [
            {
                "placeholder": "{{NOMBRE}}",
                "rule": {
                    "type": "concatenate",
                    "columns": ["NOMBRES", "APELLIDOS"],
                    "separator": " "
                },
                # Las transformaciones se aplican DESPUÉS de concatenar
                # Ej: "MARIA NA GOMEZ"
                "transforms": [
                    # "MARIA NA GOMEZ" -> "MARIA  GOMEZ" (Usa límite de palabra \b)
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    # "MARIA  GOMEZ" -> "MARIA GOMEZ" (limpia doble espacio)
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                    # " MARIA GOMEZ " -> "MARIA GOMEZ"
                    {"type": "trim"}
                ]
            },
            {
                "placeholder": "{{EL_LA}}",
                "rule": {
                    "type": "conditional_map",
                    "on_column": "PRONOMBRE",
                    "map": { "EL": "el", "ELLA": "la", "DEFAULT": "el/la" }
                },
                "transforms": []
            },
            {
                "placeholder": "{{DEL_LA}}",
                "rule": {
                    "type": "conditional_map",
                    "on_column": "PRONOMBRE",
                    "map": { "EL": "del", "ELLA": "de la", "DEFAULT": "del/de la" }
                },
                "transforms": []
            }
        ],

        
        # === PATRÓN DE CARPETA ===
        "folder_pattern": {
            "template": r"{[NOMBRES]} {[APELLIDOS]}",
            "columns": [
                {
                    "name": "NOMBRES",
                    # Las transformaciones se aplican ANTES de insertar
                    # Ej: "   MARIA NA  "
                    "transforms": [
                        # "   MARIA NA  " -> "   MARIA   " (Usa límite de palabra \b)
                        {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                        # "   MARIA   " -> "   MARIA   " (limpia doble espacio si existe)
                        {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                        # "   MARIA   " -> "MARIA"
                        {"type": "trim"},
                        # "MARIA" -> "MARIA"
                        {"type": "uppercase"}
                    ]
                },
                {
                    "name": "APELLIDOS",
                    "transforms": [
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                }
            ]
        },
        
        # === PATRÓN DE NOMBRE DE ARCHIVO ===
        "filename_pattern": {
            "template": "Acta de incumplimiento - {[NOMBRES]} {[APELLIDOS]}.docx",
           "columns": [
                {
                    "name": "NOMBRES",
                    # Mismo pipeline de limpieza que la carpeta
                    "transforms": [
                        {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                        {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                },
                {
                    "name": "APELLIDOS",
                    "transforms": [
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                }
            ]
        },
        
        # === OPCIONES ADICIONALES ===
        "overwrite_existing": True,
        "debug": True 
    }
}
 

# -------------------------------------------------------------
# -------------------[   EJECUCIÓN DE PRUEBA   ]---------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  PRUEBA DE ORQUESTADOR (v2) - GENERACIÓN BULK                ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print()
    
    ACTIVE_CONFIG = BULK_JOB_CONFIG
    
    print(f"📊 Configuración del Trabajo:")
    print(f" E- Fuente Excel: {ACTIVE_CONFIG['excel_config']['filePath']}")
    print(f"   - Hoja: {ACTIVE_CONFIG['excel_config']['sheetName']}")
    print(f"   - Tabla: {ACTIVE_CONFIG['excel_config']['tableName']}")
    print(f"   - Plantilla Word: {ACTIVE_CONFIG['template_config']['source_path']}")
    print(f"   - Directorio Base: {ACTIVE_CONFIG['template_config']['target_directory']}")
    print()
    
    folder_template = ACTIVE_CONFIG['job_config']['folder_pattern']['template']
    file_template = ACTIVE_CONFIG['job_config']['filename_pattern']['template']
    print(f"📁 Patrón de Carpetas: {folder_template}")
    print(f"📄 Patrón de Archivo: {file_template}")
    print(f"🐞 Modo Debug: {ACTIVE_CONFIG['job_config']['debug']}")
    print()
    print(f"{'─' * 70}")
    print()
    
    print("🚀 Iniciando ejecución del orquestador...")
    print()
    
    job_log = execute_bulk_document_job(ACTIVE_CONFIG)
    
    print()
    print(f"{'─' * 70}")
    print()
    print("✅ ¡Trabajo Bulk completado!")
    print()
    print("📋 LOG COMPLETO DEL TRABAJO (JSON):")
    
    print(json.dumps(job_log, indent=2, ensure_ascii=False))
    
    print()
    print(f"{'─' * 70}")
    print()
    
    summary = job_log.get("job_summary", {})
    status = summary.get("status")
    
    print("📊 RESUMEN EJECUTIVO:")
    print(f"   Estado: {status}")
    
    if status == "total_failure":
        print(f"   ❌ Error Crítico: {summary.get('error')}")
    else:
        print(f" --------------------------------------")
        print(f"   ✓ Exitosos: {summary.get('success_count')}")
        print(f"   ✗ Fallidos: {summary.get('failure_count')}")
        print(f"   ⊝ Omitidos (por filtro): {summary.get('total_skipped')}")
        print(f"   Total filas leídas: {summary.get('total_rows_processed')}")
        print(f" --------------------------------------")
    
    print()
    print(f"Destino de salida: {ACTIVE_CONFIG['template_config']['target_directory']}")
    print()
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║                   PRUEBA FINALIZADA                          ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")