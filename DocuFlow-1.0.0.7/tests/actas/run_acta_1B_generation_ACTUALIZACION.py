#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  run_acta_generation_ACTUALIZACION.py
Created: 2025-11-05
Author: @lewopxd

Description:
Script de "producción" para generar el lote de documentos 
"ACTA 1 - REGISTRO APE (ACTUALIZACIÓN)".

Itera sobre múltiples hojas (PRESENCIAL, VIRTUAL, GUIAS) y ejecuta
un trabajo de orquestación aislado para cada una.
"""

import sys
import json
import copy
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
    from core.orchester.main_orchester import execute_bulk_document_job
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar 'execute_bulk_document_job'.")
    print(f"   Asegúrate de que la carpeta 'src' está en el PYTHONPATH.")
    print(f"   Error: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   DEFINICIÓN DE TRABAJOS   ]------------
# -------------------------------------------------------------

# --- 1. Definir las rutas base ---
EXCEL_FILE_PATH = r"C:\Users\Admin\Desktop\FASE3-APROBADOS\DB-JOVENES_F3.xlsx"
TEMPLATE_FILE_PATH = r"C:\Users\Admin\Desktop\FASE3-APROBADOS\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS\ACTA 1 - REGISTRO APE\01b - Intermediación laboral – Registro APE (ACTUALIZACIÓN).docx"
BASE_OUTPUT_PATH = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\OUTPUT")

# --- 2. Definir los trabajos a ejecutar ---
JOBS_TO_RUN = [
    {
        "name": "PRESENCIAL",
        "sheet": "PRESENCIAL",
        "table": "Table_1"
    },
    {
        "name": "VIRTUAL",
        "sheet": "VIRTUAL",
        "table": "Table_2"
    },
    {
        "name": "GUIAS",
        "sheet": "GUIAS",
        "table": "Table_3"
    }
]

# --- 3. Definir la Configuración Base ---
BASE_CONFIG = {
    
    "excel_config": {
        "filePath": EXCEL_FILE_PATH,
        "sheetName": None, # Se rellenará en el bucle
        "tableName": None, # Se rellenará en el bucle
        "rangeConfig": {
            "type": "all", 
            "data": None
        },
        # Lista completa de columnas inferidas para filtros y mapeos
        "columns": [
            "ACTUALIZACION",
            "ESTADO INTERMEDIACION",
            "FECHA HV",
            "E1 FECHA REGISTRO APE",
            "NOMBRES",
            "APELLIDOS",
            "PRONOMBRE",
            "NUM_DOCUMENTO",
            "TIPO DE DOCUMENTO" 
        ]
    },

    "template_config": {
        "source_path": TEMPLATE_FILE_PATH,
        "target_directory": None, # Se rellenará en el bucle
        "clear_highlight": True,
        "author": "Jose Barreto",
        "last_modified_by": "Jose Barreto"
    },

    "job_config": {
        
        # Política GLOBAL para manejar datos faltantes de Excel.
        # "KEEP_PLACEHOLDER": Deja el {{tag}} en el documento. (Recomendado)
        # "REPLACE_EMPTY": Reemplaza con "".
        # "FAIL": Detiene la fila y la reporta como fallo.
        # Esto se puede anular por cada placeholder individualmente.
        "on_missing_data": "KEEP_PLACEHOLDER",

        # === FILTRO: (ACTUALIZACION == SI) Y (ESTADO INTERMEDIACION == OK) ===
        "filter_rules": {
            "AND": [
                {"column": "ACTUALIZACION", "operator": "equal", "value": "SI"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        
        # === MAPEO DIRECTO (1:1) ===
        #
        # EJEMPLO DE ANULACIÓN (OVERRIDE):
        # Para anular la política global, puedes añadir "on_missing" a un tag:
        #
        # "{{OTRO_DATO_OPCIONAL}}": {
        #     "source_column": "COL_OPCIONAL",
        #     "on_missing": "REPLACE_EMPTY" # Anula el global "KEEP_PLACEHOLDER"
        # },
        #
        "direct_mapping": {
            "{{N_DOCUMENTO}}": {
                "source_column": "NUM_DOCUMENTO",
                "transforms": [
                    {"type": "round", "decimals": 0}, 
                    {"type": "trim"}
                ]
            },
            
            "{{TIPO_DOCUMENTO}}": {
                "source_column": "TIPO DE DOCUMENTO",
                "transforms": [
                    {"type": "trim"},
                    {"type": "title_case"}, # "Cédula De Ciudadanía"
                    {"type": "replace", "from": "Cédula", "to": "Cedula"},
                    {"type": "replace", "from": "Ciudadanía", "to": "Ciudadania"},
                    {"type": "replace", "from": "Cedula De Ciudadania", "to": "C.C."}
                ]
            },
            
            # Mapeos para [FECHA HV]
            "{{DIA_HV}}": {
                "source_column": "FECHA HV",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%d"}]
            },
            "{{MES_HV}}": {
                "source_column": "FECHA HV",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%mes_es"}]
            },
            "{{AÑO_HV}}": {
                "source_column": "FECHA HV",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%Y"}]
            },
            
            # Mapeos para [E1 FECHA REGISTRO APE]
            "{{DIA_REGISTRO_APE}}": {
                "source_column": "E1 FECHA REGISTRO APE",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%d"}]
            },
            "{{MES_REGISTRO_APE}}": {
                "source_column": "E1 FECHA REGISTRO APE",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%mes_es"}]
            },
            "{{AÑO_REGISTRO_APE}}": {
                "source_column": "E1 FECHA REGISTRO APE",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%Y"}]
            }
        },
        
        # === MAPEO CALCULADO (Lógica) ===
        "computed_mapping": [
            {
                "placeholder": "{{NOMBRE_JOVEN}}", 
                "rule": {
                    "type": "concatenate",
                    "columns": ["NOMBRES", "APELLIDOS"],
                    "separator": " "
                },
                "transforms": [
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
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
                "placeholder": "{{REGISTRADO_A}}",
                "rule": {
                    "type": "conditional_map",
                    "on_column": "PRONOMBRE",
                    "map": { "EL": "registrado", "ELLA": "registrada", "DEFAULT": "registrado/a" }
                },
                "transforms": []
            },
            {
                "placeholder": "{{IDENTIFICADO_A}}",
                "rule": {
                    "type": "conditional_map",
                    "on_column": "PRONOMBRE",
                    "map": { "EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a" }
                },
                "transforms": []
            }
        ],

        # === PATRÓN DE CARPETA (relativo a target_directory) ===
        "folder_pattern": {
            "template": r"{[NOMBRES]} {[APELLIDOS]}",
            "columns": [
                {"name": "NOMBRES", "transforms": [
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                    {"type": "trim"},
                    {"type": "uppercase"}
                ]},
                {"name": "APELLIDOS", "transforms": [
                    {"type": "trim"},
                    {"type": "uppercase"}
                ]}
            ]
        },
        
        # === PATRÓN DE NOMBRE DE ARCHIVO ===
        "filename_pattern": {
            "template": "ACTA 1 - APE - (ACTUALIZACION) - {[NOMBRES]} {[APELLIDOS]}.docx",
           "columns": [
                {"name": "NOMBRES", "transforms": [
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                    {"type": "trim"},
                    {"type": "uppercase"}
                ]},
                {"name": "APELLIDOS", "transforms": [
                    {"type": "trim"},
                    {"type": "uppercase"}
                ]}
            ]
        },
        
        # === OPCIONES ADICIONALES ===
        "overwrite_existing": True,
        "debug": True # Poner en True si algo falla
    }
}
 

# -------------------------------------------------------------
# -------------------[   EJECUCIÓN MAESTRA   ]-----------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║   SCRIPT DE GENERACIÓN - ACTA 1 (ACTUALIZACIÓN)     _         ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print(f"\nSe ejecutarán {len(JOBS_TO_RUN)} trabajos en secuencia...")
    print(f"Fuente Excel: {EXCEL_FILE_PATH}")
    print(f"Plantilla: {TEMPLATE_FILE_PATH}")
    print(f"Directorio Raíz: {BASE_OUTPUT_PATH}")
    
    grand_total_success = 0
    grand_total_failed = 0
    grand_total_skipped = 0

    for i, job in enumerate(JOBS_TO_RUN, 1):
        job_name = job["name"]
        print(f"\n{'-'*70}")
        print(f"INICIANDO TRABAJO {i}/{len(JOBS_TO_RUN)}: \"{job_name}\"")
        # --- [ LÍNEA CORREGIDA ] ---
        print(f"{'-'*70}")

        current_config = copy.deepcopy(BASE_CONFIG)
        current_config["excel_config"]["sheetName"] = job["sheet"]
        current_config["excel_config"]["tableName"] = job["table"]
        
        target_dir_for_job = str(BASE_OUTPUT_PATH / job_name)
        current_config["template_config"]["target_directory"] = target_dir_for_job
        
        print(f"   Hoja: {job['sheet']} (Tabla: {job['table']})")
        print(f"   Destino: {target_dir_for_job}")
        print("   Aplicando filtros:")
        print("     - 'ACTUALIZACION' == 'SI'")
        print("     - 'ESTADO INTERMEDIACION' == 'OK'")
        print("\n   🚀 Ejecutando orquestador...")

        job_log = execute_bulk_document_job(current_config)
        summary = job_log.get("job_summary", {})
        status = summary.get("status", "unknown")

        if status.startswith("complete") or status.startswith("partial"):
            print("   ... Trabajo completado.")
            print(f"   RESUMEN DEL TRABAJO ({job_name}):")
            print(f"     ✓ Exitosos: {summary.get('success_count', 0)}")
            print(f" S ✗ Fallidos: {summary.get('failure_count', 0)}")
            print(f"     ⊝ Omitidos: {summary.get('total_skipped', 0)}")
            
            grand_total_success += summary.get('success_count', 0)
            grand_total_failed += summary.get('failure_count', 0)
            grand_total_skipped += summary.get('total_skipped', 0)

        else: 
            print(f"   ❌ ERROR CRÍTICO EN EL TRABAJO ({job_name}).")
            print(f"     Error: {summary.get('error', 'Error desconocido.')}")
            grand_total_failed += summary.get('total_rows_processed', 0)

    print(f"\n{'-'*70}")
    print("TODOS LOS TRABAJOS HAN FINALIZADO.")
    print(f"📊 RESUMEN TOTAL:")
    print(f" B ✓ Total Archivos Creados: {grand_total_success}")
    print(f"   ✗ Total Fallos: {grand_total_failed}")
    print(f"   ⊝ Total Omitidos (por filtro): {grand_total_skipped}")
    print(f"\nDestino final: {BASE_OUTPUT_PATH}")
    print(f"\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║                     PROCESO FINALIZADO                       ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")