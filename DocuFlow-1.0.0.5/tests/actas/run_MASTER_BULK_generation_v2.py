#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: run_MASTER_BULK_generation_v2.py
Created: 2025-11-06
Author: @lewopxd

Description:
Script "Maestro" v2 de producción para generar TODAS las actas (6 tipos)
para todas las hojas (3) en un solo proceso.

Mejoras respecto a v1:
- Ejecución secuencial acta por acta para mejor control
- Manejo robusto de errores
- Validación de rutas antes de ejecutar
- Salida consolidada en 'OUTPUT_ALL_BULK_2'
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
# -------------------[  CONFIGURACIÓN GLOBAL  ]----------------
# -------------------------------------------------------------

EXCEL_FILE_PATH = r"C:\Users\Admin\Desktop\FASE3-APROBADOS\DB-JOVENES_F3.xlsx"
BASE_TEMPLATE_PATH = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS")
BASE_OUTPUT_PATH = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\OUTPUT_ALL_BULK_2")

# Hojas a procesar
SHEETS_TO_RUN = [
    {"name": "PRESENCIAL", "sheet": "PRESENCIAL", "table": "Table_1"},
    {"name": "VIRTUAL", "sheet": "VIRTUAL", "table": "Table_2"},
    {"name": "GUIAS", "sheet": "GUIAS", "table": "Table_3"}
]

# Configuración común para carpetas y nombres de archivo
COMMON_FOLDER_PATTERN = {
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
}

# -------------------------------------------------------------
# -------------------[  FUNCIONES AUXILIARES  ]----------------
# -------------------------------------------------------------

def validate_template_path(template_path):
    """Valida que la ruta de la plantilla exista."""
    path = Path(template_path)
    if not path.exists():
        print(f"  ⚠️ ADVERTENCIA: Plantilla no encontrada: {template_path}")
        return False
    return True

def create_base_config(sheet_job, target_dir):
    """Crea la configuración base común para todos los trabajos."""
    return {
        "excel_config": {
            "filePath": EXCEL_FILE_PATH,
            "sheetName": sheet_job["sheet"],
            "tableName": sheet_job["table"],
            "rangeConfig": {"type": "all", "data": None}
        },
        "template_config": {
            "target_directory": str(target_dir),
            "clear_highlight": True,
            "author": "Jose Barreto",
            "last_modified_by": "Jose Barreto"
        },
        "job_config": {
            "folder_pattern": COMMON_FOLDER_PATTERN,
            "overwrite_existing": True,
            "debug": False
        }
    }

def execute_acta_job(job_name, config, sheet_name):
    """Ejecuta un trabajo individual y retorna el resumen."""
    print(f"\n{'-'*70}")
    print(f"EJECUTANDO: {job_name} @ {sheet_name}")
    print(f"{'-'*70}")
    print(f"  Plantilla: {config['template_config']['source_path']}")
    print(f"  Destino: {config['template_config']['target_directory']}")
    print(f"  🚀 Ejecutando orquestador...")
    
    try:
        job_log = execute_bulk_document_job(config)
        summary = job_log.get("job_summary", {})
        status = summary.get("status", "unknown")
        
        if status.startswith("complete") or status.startswith("partial"):
            print(f"  ✅ Lote completado.")
            print(f"    ✓ Exitosos: {summary.get('success_count', 0)}")
            print(f"    ✗ Fallidos: {summary.get('failure_count', 0)}")
            print(f"    ⊘ Omitidos: {summary.get('total_skipped', 0)}")
        else:
            print(f"  ❌ ERROR CRÍTICO EN EL LOTE.")
            print(f"    Error: {summary.get('error', 'Error desconocido.')}")
        
        return summary
        
    except Exception as e:
        print(f"  ❌ EXCEPCIÓN DURANTE LA EJECUCIÓN: {e}")
        return {
            "status": "error",
            "success_count": 0,
            "failure_count": 0,
            "total_skipped": 0,
            "error": str(e)
        }

# -------------------------------------------------------------
# -------------------[  ACTA 1 - NUEVO  ]----------------------
# -------------------------------------------------------------

def generate_acta_1_nuevo(sheet_job, target_dir):
    """Genera ACTA 1 - REGISTRO APE (USUARIOS NUEVOS)"""
    template_path = BASE_TEMPLATE_PATH / "ACTA 1 - REGISTRO APE" / "01a - Intermediación laboral – Registro APE (USUARIOS NUEVOS).docx"
    
    if not validate_template_path(template_path):
        return {"success_count": 0, "failure_count": 0, "total_skipped": 0}
    
    config = create_base_config(sheet_job, target_dir)
    config["template_config"]["source_path"] = str(template_path)
    
    config["excel_config"]["columns"] = [
        "ACTUALIZACION", "ESTADO INTERMEDIACION", "E1 FECHA REGISTRO APE",
        "NOMBRES", "APELLIDOS", "PRONOMBRE", "TIPO DE DOCUMENTO", "NUM_DOCUMENTO"
    ]
    
    config["job_config"].update({
        "on_missing_data": "KEEP_PLACEHOLDER",
        "filter_rules": {
            "AND": [
                {"column": "ACTUALIZACION", "operator": "equal", "value": "NO"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        "direct_mapping": {
            "{{TIPO_DOCUMENTO}}": {
                "source_column": "TIPO DE DOCUMENTO",
                "transforms": [
                    {"type": "trim"},
                    {"type": "title_case"},
                    {"type": "replace", "from": "Cédula", "to": "Cedula"},
                    {"type": "replace", "from": "Ciudadanía", "to": "Ciudadania"},
                    {"type": "replace", "from": "Cedula De Ciudadania", "to": "C.C."}
                ]
            },
            "{{N_DOCUMENTO}}": {
                "source_column": "NUM_DOCUMENTO",
                "transforms": [{"type": "round", "decimals": 0}, {"type": "trim"}]
            },
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
        "computed_mapping": [
            {
                "placeholder": "{{NOMBRE_JOVEN}}", 
                "rule": {"type": "concatenate", "columns": ["NOMBRES", "APELLIDOS"], "separator": " "},
                "transforms": [
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                    {"type": "trim"}
                ]
            },
            {
                "placeholder": "{{EL_LA}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "el", "ELLA": "la", "DEFAULT": "el/la"}},
                "transforms": [{"type": "sentence_case"}]
            },
            {
                "placeholder": "{{IDENTIFICADO_A}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a"}},
                "transforms": []
            }
        ],
        "filename_pattern": {
            "template": "ACTA 1 - APE - (USUARIO NUEVO) - {[NOMBRES]} {[APELLIDOS]}.docx",
            "columns": COMMON_FOLDER_PATTERN["columns"]
        }
    })
    
    return execute_acta_job("Acta 1 - Nuevo (APE)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[  ACTA 1 - ACTUALIZACIÓN  ]--------------
# -------------------------------------------------------------

def generate_acta_1_actualizacion(sheet_job, target_dir):
    """Genera ACTA 1 - REGISTRO APE (ACTUALIZACIÓN)"""
    template_path = BASE_TEMPLATE_PATH / "ACTA 1 - REGISTRO APE" / "01b - Intermediación laboral – Registro APE (ACTUALIZACIÓN).docx"
    
    if not validate_template_path(template_path):
        return {"success_count": 0, "failure_count": 0, "total_skipped": 0}
    
    config = create_base_config(sheet_job, target_dir)
    config["template_config"]["source_path"] = str(template_path)
    
    config["excel_config"]["columns"] = [
        "ACTUALIZACION", "ESTADO INTERMEDIACION", "FECHA HV", "E1 FECHA REGISTRO APE",
        "NOMBRES", "APELLIDOS", "PRONOMBRE", "NUM_DOCUMENTO", "TIPO DE DOCUMENTO"
    ]
    
    config["job_config"].update({
        "on_missing_data": "KEEP_PLACEHOLDER",
        "filter_rules": {
            "AND": [
                {"column": "ACTUALIZACION", "operator": "equal", "value": "SI"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        "direct_mapping": {
            "{{N_DOCUMENTO}}": {
                "source_column": "NUM_DOCUMENTO",
                "transforms": [{"type": "round", "decimals": 0}, {"type": "trim"}]
            },
            "{{TIPO_DOCUMENTO}}": {
                "source_column": "TIPO DE DOCUMENTO",
                "transforms": [
                    {"type": "trim"}, {"type": "title_case"},
                    {"type": "replace", "from": "Cédula", "to": "Cedula"},
                    {"type": "replace", "from": "Ciudadanía", "to": "Ciudadania"},
                    {"type": "replace", "from": "Cedula De Ciudadania", "to": "C.C."}
                ]
            },
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
        "computed_mapping": [
            {
                "placeholder": "{{NOMBRE_JOVEN}}", 
                "rule": {"type": "concatenate", "columns": ["NOMBRES", "APELLIDOS"], "separator": " "},
                "transforms": [
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                    {"type": "trim"}
                ]
            },
            {
                "placeholder": "{{EL_LA}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "el", "ELLA": "la", "DEFAULT": "el/la"}},
                "transforms": [{"type": "sentence_case"}]
            },
            {
                "placeholder": "{{REGISTRADO_A}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "registrado", "ELLA": "registrada", "DEFAULT": "registrado/a"}},
                "transforms": []
            },
            {
                "placeholder": "{{IDENTIFICADO_A}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a"}},
                "transforms": []
            }
        ],
        "filename_pattern": {
            "template": "ACTA 1 - APE - (ACTUALIZACION) - {[NOMBRES]} {[APELLIDOS]}.docx",
            "columns": COMMON_FOLDER_PATTERN["columns"]
        }
    })
    
    return execute_acta_job("Acta 1 - Actualización (APE)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[  ACTA 2 - PRESENCIAL  ]-----------------
# -------------------------------------------------------------

def generate_acta_2_presencial(sheet_job, target_dir):
    """Genera ACTA 2 - HABILIDADES BLANDAS (PRESENCIAL)"""
    template_path = BASE_TEMPLATE_PATH / "ACTA 2 - HABILIDADES BLANDAS" / "02_PRESENCIAL.pdf"
    
    if not validate_template_path(template_path):
        return {"success_count": 0, "failure_count": 0, "total_skipped": 0}
    
    config = create_base_config(sheet_job, target_dir)
    config["template_config"]["source_path"] = str(template_path)
    config["template_config"]["clear_highlight"] = False  # No aplica para PDF
    
    config["excel_config"]["columns"] = [
        "E2. HABILIDADES BLANDAS", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS"
    ]
    
    config["job_config"].update({
        "on_missing_data": "KEEP_PLACEHOLDER",
        "filter_rules": {
            "AND": [
                {"column": "E2. HABILIDADES BLANDAS", "operator": "equal", "value": "Presencial"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        "direct_mapping": {},
        "computed_mapping": [],
        "filename_pattern": {
            "template": "ACTA 2 - PRESENCIAL - {[NOMBRES]} {[APELLIDOS]}.pdf",
            "columns": COMMON_FOLDER_PATTERN["columns"]
        }
    })
    
    return execute_acta_job("Acta 2 - Hab. Presencial (PDF)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[  ACTA 2 - VIRTUAL  ]--------------------
# -------------------------------------------------------------

def generate_acta_2_virtual(sheet_job, target_dir):
    """Genera ACTA 2 - HABILIDADES BLANDAS (VIRTUAL)"""
    template_path = BASE_TEMPLATE_PATH / "ACTA 2 - HABILIDADES BLANDAS" / "02_VIRTUAL.pdf"
    
    if not validate_template_path(template_path):
        return {"success_count": 0, "failure_count": 0, "total_skipped": 0}
    
    config = create_base_config(sheet_job, target_dir)
    config["template_config"]["source_path"] = str(template_path)
    config["template_config"]["clear_highlight"] = False  # No aplica para PDF
    
    config["excel_config"]["columns"] = [
        "E2. HABILIDADES BLANDAS", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS"
    ]
    
    config["job_config"].update({
        "on_missing_data": "KEEP_PLACEHOLDER",
        "filter_rules": {
            "AND": [
                {"column": "E2. HABILIDADES BLANDAS", "operator": "equal", "value": "Virtual"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        "direct_mapping": {},
        "computed_mapping": [],
        "filename_pattern": {
            "template": "ACTA 2 - VIRTUAL - {[NOMBRES]} {[APELLIDOS]}.pdf",
            "columns": COMMON_FOLDER_PATTERN["columns"]
        }
    })
    
    return execute_acta_job("Acta 2 - Hab. Virtual (PDF)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[  ACTA 3 - AUTOPOSTULACIÓN  ]------------
# -------------------------------------------------------------

def generate_acta_3_autopostulacion(sheet_job, target_dir):
    """Genera ACTA 3 - AUTOPOSTULACIÓN A VACANTE"""
    template_path = BASE_TEMPLATE_PATH / "ACTA 3 - POSTULACION VACANTE" / "03 -Intermediación laboral - auto postulación a vacante laboral.docx"
    
    if not validate_template_path(template_path):
        return {"success_count": 0, "failure_count": 0, "total_skipped": 0}
    
    config = create_base_config(sheet_job, target_dir)
    config["template_config"]["source_path"] = str(template_path)
    
    config["excel_config"]["columns"] = [
        "E3. FERIA O AUTOPOSTULACION", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS",
        "PRONOMBRE", "NUM_DOCUMENTO", "TIPO DE DOCUMENTO", "E3.FECHA AUTOPOSTULACION"
    ]
    
    config["job_config"].update({
        "on_missing_data": "KEEP_PLACEHOLDER",
        "filter_rules": {
            "AND": [
                {"column": "E3. FERIA O AUTOPOSTULACION", "operator": "equal", "value": "Autopostulación"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        "direct_mapping": {
            "{{NUMERO_DOCUMENTO}}": {
                "source_column": "NUM_DOCUMENTO",
                "transforms": [{"type": "round", "decimals": 0}, {"type": "trim"}]
            },
            "{{TIPO_DOCUMENTO}}": {
                "source_column": "TIPO DE DOCUMENTO",
                "transforms": [
                    {"type": "trim"}, {"type": "title_case"},
                    {"type": "replace", "from": "Cédula", "to": "Cedula"},
                    {"type": "replace", "from": "Ciudadanía", "to": "Ciudadania"},
                    {"type": "replace", "from": "Cedula De Ciudadania", "to": "C.C."}
                ]
            },
            "{{DIA_POSTULACION}}": {
                "source_column": "E3.FECHA AUTOPOSTULACION",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%d"}]
            },
            "{{MES_POSTULACION}}": {
                "source_column": "E3.FECHA AUTOPOSTULACION",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%mes_es"}]
            },
            "{{AÑO_POSTULACION}}": {
                "source_column": "E3.FECHA AUTOPOSTULACION",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%Y"}]
            }
        },
        "computed_mapping": [
            {
                "placeholder": "{{NOMBRE_JOVEN}}", 
                "rule": {"type": "concatenate", "columns": ["NOMBRES", "APELLIDOS"], "separator": " "},
                "transforms": [
                    {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                    {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                    {"type": "trim"}
                ]
            },
            {
                "placeholder": "{{EL_LA}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "el", "ELLA": "la", "DEFAULT": "el/la"}},
                "transforms": [{"type": "sentence_case"}]
            },
            {
                "placeholder": "{{IDENTIFICADO_A}}",
                "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": {"EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a"}},
                "transforms": []
            }
        ],
        "filename_pattern": {
            "template": "ACTA 3 - AUTOPOSTULACION - {[NOMBRES]} {[APELLIDOS]}.docx",
            "columns": COMMON_FOLDER_PATTERN["columns"]
        }
    })
    
    return execute_acta_job("Acta 3 - Autopostulación", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[  ACTA 3 - FERIA  ]----------------------
# -------------------------------------------------------------

def generate_acta_3_feria(sheet_job, target_dir):
    """Genera ACTA 3 - FERIA EXPOEMPLEO"""
    template_path = BASE_TEMPLATE_PATH / "ACTA 3 - POSTULACION VACANTE" / "03 - Intermediacion laboral - Feria ExpoEmpleo (TODOS).docx"
    
    if not validate_template_path(template_path):
        return {"success_count": 0, "failure_count": 0, "total_skipped": 0}
    
    config = create_base_config(sheet_job, target_dir)
    config["template_config"]["source_path"] = str(template_path)
    
    config["excel_config"]["columns"] = [
        "E3. FERIA O AUTOPOSTULACION", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS"
    ]
    
    config["job_config"].update({
        "on_missing_data": "KEEP_PLACEHOLDER",
        "filter_rules": {
            "AND": [
                {"column": "E3. FERIA O AUTOPOSTULACION", "operator": "equal", "value": "Feria"},
                {"column": "ESTADO INTERMEDIACION", "operator": "equal", "value": "OK"}
            ]
        },
        "direct_mapping": {},
        "computed_mapping": [],
        "filename_pattern": {
            "template": "ACTA 3 - FERIA EXPOEMPLEO OCT23 - {[NOMBRES]} {[APELLIDOS]}.docx",
            "columns": COMMON_FOLDER_PATTERN["columns"]
        }
    })
    
    return execute_acta_job("Acta 3 - Feria ExpoEmpleo", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[  EJECUCIÓN PRINCIPAL  ]-----------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║       SCRIPT DE GENERACIÓN MAESTRA v2 (BULK)                 ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print(f"\nGenerando 6 tipos de actas para {len(SHEETS_TO_RUN)} hojas.")
    print(f"Fuente Excel: {EXCEL_FILE_PATH}")
    print(f"Directorio Raíz de Salida: {BASE_OUTPUT_PATH}")
    
    # Crear directorio de salida si no existe
    BASE_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    # Contadores globales
    grand_total_success = 0
    grand_total_failed = 0
    grand_total_skipped = 0
    
    # Lista de funciones generadoras
    acta_generators = [
        ("ACTA 1 - NUEVO", generate_acta_1_nuevo),
        ("ACTA 1 - ACTUALIZACIÓN", generate_acta_1_actualizacion),
        ("ACTA 2 - PRESENCIAL", generate_acta_2_presencial),
        ("ACTA 2 - VIRTUAL", generate_acta_2_virtual),
        ("ACTA 3 - AUTOPOSTULACIÓN", generate_acta_3_autopostulacion),
        ("ACTA 3 - FERIA", generate_acta_3_feria)
    ]
    
    # Iterar por cada HOJA
    for sheet_job in SHEETS_TO_RUN:
        sheet_name = sheet_job["name"]
        print(f"\n{'='*70}")
        print(f"PROCESANDO HOJA: \"{sheet_name}\"")
        print(f"{'='*70}")
        
        target_dir = BASE_OUTPUT_PATH / sheet_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Ejecutar cada tipo de acta para esta hoja
        for acta_name, generator_func in acta_generators:
            print(f"\n--- {acta_name} ---")
            try:
                summary = generator_func(sheet_job, target_dir)
                grand_total_success += summary.get('success_count', 0)
                grand_total_failed += summary.get('failure_count', 0)
                grand_total_skipped += summary.get('total_skipped', 0)
            except Exception as e:
                print(f"  ❌ EXCEPCIÓN NO CONTROLADA: {e}")
                grand_total_failed += 1
    
    # Reporte Final
    print(f"\n{'='*70}")
    print("TODOS LOS TRABAJOS HAN FINALIZADO.")
    print(f"📊 RESUMEN TOTAL (TODAS LAS ACTAS, TODAS LAS HOJAS):")
    print(f"  ✓ Total Archivos Creados: {grand_total_success}")
    print(f"  ✗ Total Fallos: {grand_total_failed}")
    print(f"  ⊘ Total Omitidos (por filtro): {grand_total_skipped}")
    print(f"\nDestino final: {BASE_OUTPUT_PATH}")
    print(f"\n╔═══════════════════════════════════════════════════════════════╗")
    print(f"║              PROCESO FINALIZADO EXITOSAMENTE                  ║")
    print(f"╚═══════════════════════════════════════════════════════════════╝")