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
- Salida consolidada en 'OUTPUT_ALL_BULK_2'

MODIFICADO (v6 - Cronológico CORRECTO):
- Añadido prefijo de fecha YYYYMMDD_ al nombre de todos los archivos.
- Corregida la lógica de 'filename_pattern' para usar los NOMBRES
  DE COLUMNA REALES de Excel en el template (ej. {[E1 FECHA REGISTRO APE]})
  y definir sus transformaciones en la lista 'columns'.

MODIFICADO (v7-v9 - Log de Errores):
- Añadida la captura precisa de errores por joven/acta.
- Se genera un archivo "generation_error_report.json" en el
  directorio de salida con el detalle de todos los fallos.
- Corregida la discrepancia donde 'failure_count' > 0 pero
  'failure_details' estaba vacío.
- Corregido error de case-sensitivity en las claves de 'GLOBAL_ERROR_LOG'.

MODIFICADO (v10 - BUGFIX de Configuración):
- Eliminados los placeholders '{{MES_REGISTRO_APE}}' y
  '{{AÑO_REGISTRO_APE}}' del 'direct_mapping' de 'generate_acta_1_nuevo'
  porque ya no existen en la plantilla de Word.
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
# -------------------[   CONFIGURACIÓN GLOBAL   ]----------------
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

# --- [ INICIO: NUEVAS VARIABLES PARA LOG DE ERRORES ] ---
GLOBAL_ERROR_LOG = {
    "PRESENCIAL": {},
    "VIRTUAL": {},
    "GUIAS": {}
}
ERROR_LOG_PATH = BASE_OUTPUT_PATH / "generation_error_report.json"
# --- [ FIN: NUEVAS VARIABLES PARA LOG DE ERRORES ] ---


# -------------------------------------------------------------
# -------------------[   FUNCIONES AUXILIARES   ]----------------
# -------------------------------------------------------------

# --- [ INICIO: NUEVAS FUNCIONES DE LOG ] ---
def log_joven_error(sheet_name, joven_name, acta_name, error_message):
    """
    Registra de forma segura un error en el recolector global.
    """
    if sheet_name not in GLOBAL_ERROR_LOG:
        print(f"  LOG: ⚠️ Clave de hoja desconocida '{sheet_name}' para log de error.")
        return

    if joven_name not in GLOBAL_ERROR_LOG[sheet_name]:
        GLOBAL_ERROR_LOG[sheet_name][joven_name] = []
    
    GLOBAL_ERROR_LOG[sheet_name][joven_name].append({
        "acta_fallida": acta_name,
        "error": str(error_message)
    })

def save_error_log():
    """
    Guarda el recolector de errores global en un archivo JSON.
    """
    print(f"\n{'-'*70}")
    print(f"Guardando log de errores en: {ERROR_LOG_PATH}")
    
    log_final = {hoja: jovenes for hoja, jovenes in GLOBAL_ERROR_LOG.items() if jovenes}
    
    if not log_final:
        print("✓ No se registraron errores.")
        if grand_total_failed > 0:
            print(f"⚠️ ADVERTENCIA: El contador final reportó {grand_total_failed} fallos, pero no se capturaron detalles.")
            print("   Esto puede indicar un error en el propio orquestador (no devuelve 'failure_details').")
        return

    try:
        with open(ERROR_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(log_final, f, indent=2, ensure_ascii=False)
        print(f"✓ Log de errores guardado.")
    except Exception as e:
        print(f"❌ No se pudo guardar el log de errores: {e}")
# --- [ FIN: NUEVAS FUNCIONES DE LOG ] ---

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
    """
    Ejecuta un trabajo individual y retorna el LOG COMPLETO del trabajo.
    """
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
        
        return job_log
        
    except Exception as e:
        print(f"  ❌ EXCEPCIÓN DURANTE LA EJECUCIÓN: {e}")
        error_summary = {
            "status": "error",
            "success_count": 0,
            "failure_count": 0,
            "total_skipped": 0,
            "error": str(e)
        }
        return {
            "job_summary": error_summary,
            "failure_details": [] 
        }

# -------------------------------------------------------------
# -------------------[   ACTA 1 - NUEVO   ]----------------------
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
            
            # --- [ INICIO DE CORRECCIÓN v10 ] ---
            # Se eliminan los placeholders {{MES_REGISTRO_APE}} y
            # {{AÑO_REGISTRO_APE}} porque no existen en la plantilla.
            "{{DIA_REGISTRO_APE}}": {
                "source_column": "E1 FECHA REGISTRO APE",
                "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%d"}]
            }
            # --- [ FIN DE CORRECCIÓN v10 ] ---
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
            # 1. El template USA los nombres de columna REALES del Excel
            "template": "{[E1 FECHA REGISTRO APE]}_ACTA 1 - APE - (USUARIO NUEVO) - {[NOMBRES]} {[APELLIDOS]}.docx",
            
            # 2. La lista 'columns' define las transformaciones para CADA
            #    columna usada en el template.
            "columns": [
                # 3. Definición para la columna de FECHA
                {
                    "name": "E1 FECHA REGISTRO APE", # <-- Nombre REAL de la columna Excel
                    "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "202510%d"}]
                },
                # 4. Definición para NOMBRES (la misma que en COMMON_FOLDER_PATTERN)
                {
                    "name": "NOMBRES",
                    "transforms": [
                        {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                        {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                },
                # 5. Definición para APELLIDOS (la misma que en COMMON_FOLDER_PATTERN)
                {
                    "name": "APELLIDOS",
                    "transforms": [
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                }
            ]
        }
    })
    
    return execute_acta_job("Acta 1 - Nuevo (APE)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[   ACTA 1 - ACTUALIZACIÓN   ]--------------
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
            # 1. El template USA los nombres de columna REALES del Excel
            "template": "{[FECHA HV]}_ACTA 1 - APE - (ACTUALIZACION) - {[NOMBRES]} {[APELLIDOS]}.docx",
            
            # 2. La lista 'columns' define las transformaciones para CADA
            #    columna usada en el template.
            "columns": [
                # 3. Definición para la columna de FECHA
                {
                    "name": "FECHA HV", # <-- Nombre REAL de la columna Excel
                    "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%Y%m%d"}]
                },
                # 4. Definición para NOMBRES (la misma que en COMMON_FOLDER_PATTERN)
                {
                    "name": "NOMBRES",
                    "transforms": [
                        {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                        {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                },
                # 5. Definición para APELLIDOS (la misma que en COMMON_FOLDER_PATTERN)
                {
                    "name": "APELLIDOS",
                    "transforms": [
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                }
            ]
        }
    })
    
    return execute_acta_job("Acta 1 - Actualización (APE)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[   ACTA 2 - PRESENCIAL   ]-----------------
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
            # Fecha estática añadida.
            # El orquestador usará las definiciones de COMMON_FOLDER_PATTERN
            # para resolver {[NOMBRES]} y {[APELLIDOS]}
            "template": "20251022_ACTA 2 - PRESENCIAL - {[NOMBRES]} {[APELLIDOS]}.pdf",
            "columns": [] # No se necesitan columnas ADICIONALES
        }
    })
    
    return execute_acta_job("Acta 2 - Hab. Presencial (PDF)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[   ACTA 2 - VIRTUAL   ]--------------------
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
            # Fecha estática añadida
            "template": "20251024_ACTA 2 - VIRTUAL - {[NOMBRES]} {[APELLIDOS]}.pdf",
            "columns": [] # No se necesitan columnas ADICIONALES
        }
    })
    
    return execute_acta_job("Acta 2 - Hab. Virtual (PDF)", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[   ACTA 3 - AUTOPOSTULACIÓN   ]------------
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
            # 1. El template USA los nombres de columna REALES del Excel
            "template": "{[E3.FECHA AUTOPOSTULACION]}_ACTA 3 - AUTOPOSTULACION - {[NOMBRES]} {[APELLIDOS]}.docx",
            
            # 2. La lista 'columns' define las transformaciones para CADA
            #    columna usada en el template.
            "columns": [
                # 3. Definición para la columna de FECHA
                {
                    "name": "E3.FECHA AUTOPOSTULACION", # <-- Nombre REAL de la columna Excel
                    "transforms": [{"type": "date_format", "input_format": "%Y-%m-%d %H:%M:%S", "output_template": "%Y%m%d"}]
                },
                # 4. Definición para NOMBRES (la misma que en COMMON_FOLDER_PATTERN)
                {
                    "name": "NOMBRES",
                    "transforms": [
                        {"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},
                        {"type": "regex_replace", "pattern": "\\s+", "replacement": " "},
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                },
                # 5. Definición para APELLIDOS (la misma que en COMMON_FOLDER_PATTERN)
                {
                    "name": "APELLIDOS",
                    "transforms": [
                        {"type": "trim"},
                        {"type": "uppercase"}
                    ]
                }
            ]
        }
    })
    
    return execute_acta_job("Acta 3 - Autopostulación", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[   ACTA 3 - FERIA   ]----------------------
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
            # Fecha estática añadida
            "template": "20251023_ACTA 3 - FERIA EXPOEMPLEO OCT23 - {[NOMBRES]} {[APELLIDOS]}.docx",
            "columns": [] # No se necesitan columnas ADICIONALES
        }
    })
    
    return execute_acta_job("Acta 3 - Feria ExpoEmpleo", config, sheet_job["name"])

# -------------------------------------------------------------
# -------------------[   EJECUCIÓN PRINCIPAL   ]-----------------
# -------------------------------------------------------------

# Variable global para el contador de fallos
grand_total_failed = 0

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
    # grand_total_failed ya está definido como global
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
                # 1. Ejecutar el trabajo
                job_log = generator_func(sheet_job, target_dir)
                summary = job_log.get("job_summary", {})

                # 2. Actualizar contadores
                failure_count_from_summary = summary.get('failure_count', 0)
                grand_total_success += summary.get('success_count', 0)
                grand_total_failed += failure_count_from_summary
                grand_total_skipped += summary.get('total_skipped', 0)

                # 3. --- [INICIO] Captura de Errores Detallados ---
                failure_details = job_log.get("failure_details", [])
                
                if failure_details:
                    print(f"    LOG: Registrando {len(failure_details)} fallos individuales...")
                    for failure in failure_details:
                        # El 'identifier' es el nombre de la carpeta (ej. "JOHN DOE")
                        joven_name = failure.get("identifier", "NOMBRE_DESCONOCIDO")
                        error_msg = failure.get("error", "Error desconocido")
                        log_joven_error(sheet_name, joven_name, acta_name, error_msg)
                
                # --- [INICIO DE LA CORRECCIÓN v8] ---
                # Captura la discrepancia: el resumen reporta fallos,
                # pero la lista de detalles está vacía.
                elif failure_count_from_summary > 0 and not failure_details:
                    print(f"    LOG: ¡ALERTA! El orquestador reportó {failure_count_from_summary} fallos pero no devolvió detalles.")
                    log_joven_error(
                        sheet_name, 
                        "ERROR_DE_REPORTE_DEL_ORQUESTADOR", 
                        acta_name, 
                        f"El resumen del trabajo reportó {failure_count_from_summary} fallos, pero la lista 'failure_details' vino vacía."
                    )
                # --- [FIN DE LA CORRECCIÓN v8] ---

                # 4. Capturar si el TRABAJO ENTERO falló
                if summary.get('status') == 'error':
                     log_joven_error(sheet_name, "ERROR_CRITICO_DEL_LOTE", acta_name, summary.get('error'))
                # --- [FIN] Captura de Errores Detallados ---

            except Exception as e:
                print(f"  ❌ EXCEPCIÓN NO CONTROLADA: {e}")
                grand_total_failed += 1
                # 5. Loggear la excepción no controlada
                log_joven_error(sheet_name, "ERROR_CRITICO_DE_FUNCION", acta_name, str(e))
    
    # Reporte Final
    print(f"\n{'='*70}")
    print("TODOS LOS TRABAJOS HAN FINALIZADO.")
    print(f"📊 RESUMEN TOTAL (TODAS LAS ACTAS, TODAS LAS HOJAS):")
    print(f"  ✓ Total Archivos Creados: {grand_total_success}")
    print(f"  ✗ Total Fallos: {grand_total_failed}")
    print(f"  ⊘ Total Omitidos (por filtro): {grand_total_skipped}")
    print(f"\nDestino final: {BASE_OUTPUT_PATH}")
    
    # --- [INICIO] Guardar el log de errores ---
    save_error_log()
    # --- [FIN] Guardar el log de errores ---
    
    print(f"\n╔═══════════════════════════════════════════════════════════════╗")
    print(f"║              PROCESO FINALIZADO EXITOSAMENTE                  ║")
    print(f"╚═══════════════════════════════════════════════════════════════╝")
