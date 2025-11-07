#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  test_bulk_generation.py
Created: 2025-11-05
Author: @lewopxd

Description:
Test script for the main orchestrator function.
Tests reading from Excel and bulk-generating Word documents.
"""

import sys
import json
from pathlib import Path

# --- [ INICIO: AJUSTE DE PYTHONPATH (PARA SUB-CARPETA 'tests') ] ---
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
src_path = project_root / 'src'

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
# --- [ FIN: AJUSTE DE PYTHONPATH ] ---

try:
    from core.orchester.main_orchester import execute_bulk_document_job
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'execute_bulk_document_job'.")
    print(f"   Asegúrate de que la carpeta 'src' está en: {src_path}")
    print(f"   Error: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   CONFIGURACIÓN DE PRUEBA   ]-----------
# -------------------------------------------------------------

# Configuración del trabajo "Bulk" con la NUEVA estructura mejorada
BULK_JOB_CONFIG = {
    
    # --- SECCIÓN 1: EXTRACCIÓN DE DATOS ---
    "excel_config": {
        "filePath": r"C:\Users\Admin\Desktop\JOSE\CARPETAS JOVENES\DB-JOVENES_copia.xlsx",
        "sheetName": "GUIAS", 
        "tableName": "Table_3",
        "rangeConfig": {
            "type": "all", 
            "data": "none"  # rango 2-23
        },
        # Columnas necesarias para filtros, mapeos y patrones de nomenclatura
        "columns": ["PRONOMBRE", "NOMBRES", "APELLIDOS", "ESTADO INTERMEDIACION"] 
    },

    # --- SECCIÓN 2: PLANTILLA DE DOCUMENTO ---
    "template_config": {
        "source_path": r"C:\Users\Admin\Desktop\JOSE\CARPETAS JOVENES\CARPETAS JOVENES\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS\ACTA INCUMPLIMIENTO.docx",
        
        # Directorio base donde se creará la estructura de carpetas
        "target_directory": r"C:\Users\Admin\Desktop\test\GUIAS", 
        
        "clear_highlight": True,
        "author": "Jose Barreto",
        "last_modified_by": "Jose Barreto"
    },

    # --- SECCIÓN 3: CONFIGURACIÓN DEL TRABAJO ---
    "job_config": {
        
        # === FILTRO DE EVALUACIÓN ===
        # Solo procesa filas donde "ESTADO INTERMEDIACION" sea "INCUMPLIMIENTO"
        "filter_rules": {
            "column": "ESTADO INTERMEDIACION",
            "operator": "equal",
            "value": "INCUMPLIMIENTO"
        },
        
        # === MAPEO DIRECTO ===
        # Mapeo 1:1 de columnas Excel a placeholders Word (si aplica)
        "direct_mapping": {
            # "{{PLACEHOLDER_WORD}}": "COLUMNA_EXCEL"
        },
        
        # === MAPEO CALCULADO ===
        # Reglas de transformación para placeholders complejos
        "computed_mapping": [
            {
                "placeholder": "{{NOMBRE}}",
                "rule": {
                    "type": "concatenate",
                    "columns": ["NOMBRES", "APELLIDOS"],
                    "separator": " "
                }
            },
            {
                "placeholder": "{{EL_LA}}",
                "rule": {
                    "type": "conditional_map",
                    "on_column": "PRONOMBRE",
                    "map": {
                        "EL": "el",
                        "ELLA": "la",
                        "DEFAULT": "el/la"
                    }
                }
            },
            {
                "placeholder": "{{DEL_LA}}",
                "rule": {
                    "type": "conditional_map",
                    "on_column": "PRONOMBRE",
                    "map": {
                        "EL": "del",
                        "ELLA": "de la",
                        "DEFAULT": "del/de la"
                    }
                }
            }
        ],

        
       
        # === PATRÓN DE CARPETA (NUEVA ESTRUCTURA) ===
        # Define la estructura de subcarpetas usando variables {[COLUMNA]}
        "folder_pattern": {
            "template": r"{[NOMBRES]} {[APELLIDOS]}\\FASE 3 - INTERMEDIACION",
            "columns": [
                {
                    "name": "NOMBRES",
                    "format": "MAYUSCULAS"  # Opciones: MAYUSCULAS, MINUSCULAS, TIPO_FRASE
                },
                {
                    "name": "APELLIDOS",
                    "format": "MAYUSCULAS"
                }
            ]
        },
        
        # === PATRÓN DE NOMBRE DE ARCHIVO (NUEVA ESTRUCTURA) ===
        # Define el nombre del archivo final
        "filename_pattern": {
            "template": "Acta de incumplimiento - {[NOMBRES]} {[APELLIDOS]}.docx",
           "columns": [
                {
                    "name": "NOMBRES",
                    "format": "MAYUSCULAS"  # Opciones: MAYUSCULAS, MINUSCULAS, TIPO_FRASE
                },
                {
                    "name": "APELLIDOS",
                    "format": "MAYUSCULAS"
                }
            ]
        },
        
        # === OPCIONES ADICIONALES ===
        "overwrite_existing": True  # Sobrescribir archivos existentes
    }
}
 

# -------------------------------------------------------------
# -------------------[   EJECUCIÓN DE PRUEBA   ]---------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  PRUEBA DE ORQUESTADOR - GENERACIÓN BULK DE DOCUMENTOS      ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print()
    
    # Selecciona qué configuración usar
    ACTIVE_CONFIG = BULK_JOB_CONFIG  # Cambiar a BULK_JOB_CONFIG_ALTERNATIVO para probar la otra
    
    print(f"📊 Configuración del Trabajo:")
    print(f"   - Fuente Excel: {ACTIVE_CONFIG['excel_config']['filePath']}")
    print(f"   - Hoja: {ACTIVE_CONFIG['excel_config']['sheetName']}")
    print(f"   - Tabla: {ACTIVE_CONFIG['excel_config']['tableName']}")
    print(f"   - Plantilla Word: {ACTIVE_CONFIG['template_config']['source_path']}")
    print(f"   - Directorio Base: {ACTIVE_CONFIG['template_config']['target_directory']}")
    print()
    
    folder_template = ACTIVE_CONFIG['job_config']['folder_pattern']['template']
    file_template = ACTIVE_CONFIG['job_config']['filename_pattern']['template']
    print(f"📁 Patrón de Carpetas: {folder_template}")
    print(f"📄 Patrón de Archivo: {file_template}")
    print()
    print(f"{'─' * 70}")
    print()
    
    # Llamar a la función del Orquestador
    print("🚀 Iniciando ejecución del orquestador...")
    print()
    
    job_log = execute_bulk_document_job(ACTIVE_CONFIG)
    
    # Imprimir el resultado
    print()
    print(f"{'─' * 70}")
    print()
    print("✅ ¡Trabajo Bulk completado!")
    print()
    print("📋 LOG COMPLETO DEL TRABAJO:")
    print(json.dumps(job_log, indent=2, ensure_ascii=False))
    print()
    print(f"{'─' * 70}")
    print()
    
    # Resumen ejecutivo
    summary = job_log.get("job_summary", {})
    status = summary.get("status")
    
    print("📊 RESUMEN EJECUTIVO:")
    print(f"   Estado: {status}")
    
    if status == "total_failure":
        print(f"   ❌ Error Crítico: {summary.get('error')}")
    else:
        print(f"   ✓ Exitosos: {summary.get('success_count')}")
        print(f"   ✗ Fallidos: {summary.get('failure_count')}")
        print(f"   ⊝ Omitidos: {summary.get('total_skipped')}")
        print(f"   Total procesadas: {summary.get('total_rows_processed')}")
    
    print()
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║                   PRUEBA FINALIZADA                          ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")