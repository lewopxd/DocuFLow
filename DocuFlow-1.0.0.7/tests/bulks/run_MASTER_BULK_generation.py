#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  run_MASTER_BULK_generation.py
Created: 2025-11-06
Author: @lewopxd

Description:
Script "Maestro" de producción para generar TODAS las actas (6 tipos)
para todas las hojas (3) en un solo proceso.

La salida se consolida en 'OUTPUT_ALL_BULK'.
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
BASE_TEMPLATE_PATH = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\FASE 3 - INTERMEDIACION LABORAL\PLANTILLAS ACTAS")
BASE_OUTPUT_PATH = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\OUTPUT_ALL_BULK") # <--- ¡NUEVA RUTA DE SALIDA!

# --- 2. Definir las HOJAS a procesar ---
SHEETS_TO_RUN = [
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

# --- 3. Definir TODAS las configuraciones de ACTAS ---
# Esta es la lista maestra de todos los trabajos que hemos creado.

ALL_ACTA_CONFIGS = [
    
    # --- [ ACTA 1 - NUEVO (DOCX) ] ---
    {
        "job_name": "Acta 1 - Nuevo (APE)",
        "excel_config": {
            "columns": [
                "ACTUALIZACION", "ESTADO INTERMEDIACION", "E1 FECHA REGISTRO APE",
                "NOMBRES", "APELLIDOS", "PRONOMBRE", "TIPO DE DOCUMENTO", "NUM_DOCUMENTO"
            ]
        },
        "template_config": {
            "source_path": str(BASE_TEMPLATE_PATH / "ACTA 1 - REGISTRO APE" / "01a - Intermediación laboral – Registro APE (USUARIOS NUEVOS).docx")
        },
        "job_config": {
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
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "el", "ELLA": "la", "DEFAULT": "el/la" }},
                    "transforms": [{"type": "sentence_case"}]
                },
                {
                    "placeholder": "{{IDENTIFICADO_A}}",
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a" }},
                    "transforms": []
                }
            ],
            "filename_pattern": {
                "template": "ACTA 1 - APE - (USUARIO NUEVO) - {[NOMBRES]} {[APELLIDOS]}.docx",
                "columns": [
                    {"name": "NOMBRES", "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},{"type": "regex_replace", "pattern": "\\s+", "replacement": " "},{"type": "trim"},{"type": "uppercase"}]},
                    {"name": "APELLIDOS", "transforms": [{"type": "trim"},{"type": "uppercase"}]}
                ]
            }
        }
    },
    
    # --- [ ACTA 1 - ACTUALIZACIÓN (DOCX) ] ---
    {
        "job_name": "Acta 1 - Actualización (APE)",
        "excel_config": {
            "columns": [
                "ACTUALIZACION", "ESTADO INTERMEDIACION", "FECHA HV", "E1 FECHA REGISTRO APE",
                "NOMBRES", "APELLIDOS", "PRONOMBRE", "NUM_DOCUMENTO", "TIPO DE DOCUMENTO"
            ]
        },
        "template_config": {
            "source_path": str(BASE_TEMPLATE_PATH / "ACTA 1 - REGISTRO APE" / "01b - Intermediación laboral – Registro APE (ACTUALIZACIÓN).docx")
        },
        "job_config": {
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
                    "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""}, {"type": "regex_replace", "pattern": "\\s+", "replacement": " "}, {"type": "trim"}]
                },
                {
                    "placeholder": "{{EL_LA}}",
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "el", "ELLA": "la", "DEFAULT": "el/la" }},
                    "transforms": [{"type": "sentence_case"}]
                },
                {
                    "placeholder": "{{REGISTRADO_A}}",
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "registrado", "ELLA": "registrada", "DEFAULT": "registrado/a" }},
                    "transforms": []
                },
                {
                    "placeholder": "{{IDENTIFICADO_A}}",
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a" }},
                    "transforms": []
                }
            ],
            "filename_pattern": {
                "template": "ACTA 1 - APE - (ACTUALIZACION) - {[NOMBRES]} {[APELLIDOS]}.docx",
                "columns": [
                    {"name": "NOMBRES", "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},{"type": "regex_replace", "pattern": "\\s+", "replacement": " "},{"type": "trim"},{"type": "uppercase"}]},
                    {"name": "APELLIDOS", "transforms": [{"type": "trim"},{"type": "uppercase"}]}
                ]
            }
        }
    },

    # --- [ ACTA 2 - PRESENCIAL (PDF) ] ---
    {
        "job_name": "Acta 2 - Hab. Presencial (PDF)",
        "excel_config": {
            "columns": ["E2. HABILIDADES BLANDAS", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS"]
        },
        "template_config": {
            # --- [ CORRECCIÓN: Añadido doble espacio ] ---
            "source_path": str(BASE_TEMPLATE_PATH / "ACTA 2 - HABILIDADES BLANDAS" / "02 - Intermediación laboral – Habilidades blandas  - PRESENCIAL (TODOS).pdf")
        },
        "job_config": {
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
                "columns": [
                    {"name": "NOMBRES", "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},{"type": "regex_replace", "pattern": "\\s+", "replacement": " "},{"type": "trim"},{"type": "uppercase"}]},
                    {"name": "APELLIDOS", "transforms": [{"type": "trim"},{"type": "uppercase"}]}
                ]
            }
        }
    },

    # --- [ ACTA 2 - VIRTUAL (PDF) ] ---
    {
        "job_name": "Acta 2 - Hab. Virtual (PDF)",
        "excel_config": {
            "columns": ["E2. HABILIDADES BLANDAS", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS"]
        },
        "template_config": {
            # --- [ CORRECCIÓN: Añadido doble espacio ] ---
            "source_path": str(BASE_TEMPLATE_PATH / "ACTA 2 - HABILIDADES BLANDAS" / "02 - Intermediación laboral – Habilidades blandas  - VIRTUAL (TODOS)adj.pdf")
        },
        "job_config": {
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
                "columns": [
                    {"name": "NOMBRES", "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},{"type": "regex_replace", "pattern": "\\s+", "replacement": " "},{"type": "trim"},{"type": "uppercase"}]},
                    {"name": "APELLIDOS", "transforms": [{"type": "trim"},{"type": "uppercase"}]}
                ]
            }
        }
    },

    # --- [ ACTA 3 - AUTOPOSTULACIÓN (DOCX) ] ---
    {
        "job_name": "Acta 3 - Autopostulación",
        "excel_config": {
            "columns": [
                "E3. FERIA O AUTOPOSTULACION", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS",
                "PRONOMBRE", "NUM_DOCUMENTO", "TIPO DE DOCUMENTO", "E3.FECHA AUTOPOSTULACION"
            ]
        },
        "template_config": {
            "source_path": str(BASE_TEMPLATE_PATH / "ACTA 3 - POSTULACION VACANTE" / "03 -Intermediación laboral - auto postulación a vacante laboral.docx")
        },
        "job_config": {
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
                    "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""}, {"type": "regex_replace", "pattern": "\\s+", "replacement": " "}, {"type": "trim"}]
                },
                {
                    "placeholder": "{{EL_LA}}",
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "el", "ELLA": "la", "DEFAULT": "el/la" }},
                    "transforms": [{"type": "sentence_case"}]
                },
                {
                    "placeholder": "{{IDENTIFICADO_A}}",
                    "rule": {"type": "conditional_map", "on_column": "PRONOMBRE", "map": { "EL": "identificado", "ELLA": "identificada", "DEFAULT": "identificado/a" }},
                    "transforms": []
                }
            ],
            "filename_pattern": {
                "template": "ACTA 3 - AUTOPOSTULACION - {[NOMBRES]} {[APELLIDOS]}.docx",
                "columns": [
                    {"name": "NOMBRES", "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},{"type": "regex_replace", "pattern": "\\s+", "replacement": " "},{"type": "trim"},{"type": "uppercase"}]},
                    {"name": "APELLIDOS", "transforms": [{"type": "trim"},{"type": "uppercase"}]}
                ]
            }
        }
    },

    # --- [ ACTA 3 - FERIA (DOCX) ] ---
    {
        "job_name": "Acta 3 - Feria ExpoEmpleo",
        "excel_config": {
            "columns": ["E3. FERIA O AUTOPOSTULACION", "ESTADO INTERMEDIACION", "NOMBRES", "APELLIDOS"]
        },
        "template_config": {
            "source_path": str(BASE_TEMPLATE_PATH / "ACTA 3 - POSTULACION VACANTE" / "03 - Intermediacion laboral - Feria ExpoEmpleo (TODOS).docx")
        },
        "job_config": {
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
                "columns": [
                    {"name": "NOMBRES", "transforms": [{"type": "regex_replace", "pattern": "\\b(NA|na)\\b", "replacement": ""},{"type": "regex_replace", "pattern": "\\s+", "replacement": " "},{"type": "trim"},{"type": "uppercase"}]},
                    {"name": "APELLIDOS", "transforms": [{"type": "trim"},{"type": "uppercase"}]}
                ]
            }
        }
    }
]

# --- Configuración base común para todos los trabajos ---
COMMON_BASE_CONFIG = {
    "excel_config": {
        "filePath": EXCEL_FILE_PATH,
        "sheetName": None, # Inyectado por el bucle
        "tableName": None, # Inyectado por el bucle
        "rangeConfig": {
            "type": "all", 
            "data": None
        }
    },
    "template_config": {
        "target_directory": None, # Inyectado por el bucle
        "clear_highlight": True,
        "author": "Jose Barreto",
        "last_modified_by": "Jose Barreto"
    },
    "job_config": {
        # Carpeta común para todos
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
        "overwrite_existing": True,
        "debug": False # Poner en True para depuración masiva
    }
}

# -------------------------------------------------------------
# -------------------[   EJECUCIÓN MAESTRA   ]-----------------
# -------------------------------------------------------------

def deep_merge(dict1, dict2):
    """Combina dos diccionarios recursivamente."""
    result = copy.deepcopy(dict1)
    for key, value in dict2.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║            SCRIPT DE GENERACIÓN MAESTRA (BULK)               ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print(f"\nGenerando {len(ALL_ACTA_CONFIGS)} tipos de actas para {len(SHEETS_TO_RUN)} hojas.")
    print(f"Fuente Excel: {EXCEL_FILE_PATH}")
    print(f"Directorio Raíz de Salida: {BASE_OUTPUT_PATH}")
    
    grand_total_success = 0
    grand_total_failed = 0
    grand_total_skipped = 0

    # Bucle Externo: Iterar por cada HOJA (PRESENCIAL, VIRTUAL, GUIAS)
    for sheet_job in SHEETS_TO_RUN:
        sheet_name = sheet_job["name"]
        print(f"\n{'='*70}")
        print(f"INICIANDO PROCESAMIENTO DE HOJA: \"{sheet_name}\"")
        print(f"{'='*70}")

        # Bucle Interno: Iterar por cada TIPO DE ACTA (6 actas)
        for acta_config in ALL_ACTA_CONFIGS:
            job_name = acta_config["job_name"]
            print(f"\n{'-'*70}")
            print(f"EJECUTANDO LOTE: \"{job_name}\" para la hoja \"{sheet_name}\"")
            print(f"{'-'*70}")
            
            # 1. Combinar la configuración base común con la config específica del acta
            current_config = deep_merge(COMMON_BASE_CONFIG, acta_config)
            
            # 2. Inyectar los valores específicos del bucle
            current_config["excel_config"]["sheetName"] = sheet_job["sheet"]
            current_config["excel_config"]["tableName"] = sheet_job["table"]
            
            target_dir_for_job = str(BASE_OUTPUT_PATH / sheet_name)
            current_config["template_config"]["target_directory"] = target_dir_for_job
            
            # 3. Imprimir resumen y ejecutar
            print(f"   Plantilla: {current_config['template_config']['source_path']}")
            print(f"   Destino: {target_dir_for_job}")
            print(f"   Filtro: {current_config['job_config']['filter_rules']}")
            print("\n   🚀 Ejecutando orquestador...")

            job_log = execute_bulk_document_job(current_config)
            summary = job_log.get("job_summary", {})
            status = summary.get("status", "unknown")

            if status.startswith("complete") or status.startswith("partial"):
                print("   ... Lote completado.")
                print(f"   RESUMEN DEL LOTE ({job_name} @ {sheet_name}):")
                print(f"     ✓ Exitosos: {summary.get('success_count', 0)}")
                print(f"     ✗ Fallidos: {summary.get('failure_count', 0)}")
                print(f"     ⊝ Omitidos: {summary.get('total_skipped', 0)}")
                
                grand_total_success += summary.get('success_count', 0)
                grand_total_failed += summary.get('failure_count', 0)
                grand_total_skipped += summary.get('total_skipped', 0)

            else: 
                print(f"   ❌ ERROR CRÍTICO EN EL LOTE ({job_name} @ {sheet_name}).")
                print(f"     Error: {summary.get('error', 'Error desconocido.')}")
                # Asumir que todas las filas de esa hoja fallaron para este trabajo
                grand_total_failed += summary.get('total_rows_processed', 0) 

    # Reporte Final
    print(f"\n{'='*70}")
    print("TODOS LOS TRABAJOS HAN FINALIZADO.")
    print(f"📊 RESUMEN TOTAL (TODAS LAS ACTAS, TODAS LAS HOJAS):")
    print(f" B ✓ Total Archivos Creados: {grand_total_success}")
    print(f"   ✗ Total Fallos: {grand_total_failed}")
    print(f"   ⊝ Total Omitidos (por filtro): {grand_total_skipped}")
    print(f"\nDestino final: {BASE_OUTPUT_PATH}")
    print(f"\n╔══════════════════════════════════════════════════════════════╗")
    print(f"║                    PROCESO FINALIZADO                        ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")