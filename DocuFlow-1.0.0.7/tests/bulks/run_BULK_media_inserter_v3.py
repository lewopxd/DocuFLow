#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  run_BULK_media_inserter_v6_FINAL.py
Created: 2025-11-06
Author: @lewopxd

Description:
Script de "PASO 2" (ETL de Medios) para la generación de actas.

v6 (ULTIMATE FIX):
- ✅ Variantes de nombres de archivo (ej: "CERTIFICADO REGISTRO APE" vs "REGISTRO APE")
- ✅ Extensiones flexibles (si busca PDF pero encuentra JPG, lo mapea como imagen)
- ✅ Log JSON simplificado solo con errores
- ✅ Estructura jerárquica por grupo/joven
"""

import sys
import os
import shutil
import re
import unicodedata
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple 


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
    from core.ms_word.template_parser import get_template_info
except ImportError as e:
    print(f"❌ CRITICAL: No se pudo importar el 'document_assembler' o 'template_parser'.")
    print(f"   Asegúrate de que la carpeta 'src' está en el PYTHONPATH.")
    print(f"   Error: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[   CONFIGURACIÓN GLOBAL   ]----------------
# -------------------------------------------------------------

ACTA_SOURCE_ROOT = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\OUTPUT_ALL_BULK_2")
SOPORTES_ROOT = Path(r"C:\Users\Admin\Desktop\JOSE\CARPETAS JOVENES\CARPETAS JOVENES\JOVENES")
FINAL_OUTPUT_ROOT = Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\FINAL_OUTPUT")
ERROR_LOG_PATH = FINAL_OUTPUT_ROOT / "error_report.json"
ACTA_SUBFOLDER_TARGET = "FASE 3 - INTERMEDIACION"

SUPPORTED_IMAGE_EXT = ('.png', '.jpg', '.jpeg')
SUPPORTED_PDF_EXT = ('.pdf',)
ALL_SUPPORTED_EXT = SUPPORTED_IMAGE_EXT + SUPPORTED_PDF_EXT

ERROR_LOG: Dict[str, Dict[str, List[Dict]]] = {}  # {grupo: {joven: [errores]}}


# -------------------------------------------------------------
# -------------------[   FUNCIONES HELPER   ]-------------------
# -------------------------------------------------------------

def sanitize_key(text: str) -> str:
    """Sanitización ligera: minúsculas, sin tildes, un solo espacio."""
    try:
        text = str(text).lower()
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception:
        return ""

def sanitize_for_comparison(text: str) -> str:
    """Sanitización AGRESIVA: elimina TODOS los símbolos y espacios."""
    try:
        text = str(text).lower()
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = re.sub(r'[^a-z0-9]+', '', text)
        return text
    except Exception:
        return ""


# 🆕 DICCIONARIO DE VARIANTES DE NOMBRES
FILE_NAME_VARIANTS = {
    "01 - CERTIFICADO REGISTRO APE": [
        "01 - CERTIFICADO REGISTRO APE",
        "01 - REGISTRO APE",  # ← Variante común sin "CERTIFICADO"
        "01 - CERTIFICADO APE",
    ],
    "01 - HV": [
        "01 - HV",
        "HV",  # ← Algunos solo tienen "HV"
        "01 - HOJA DE VIDA",
        "HOJA DE VIDA APE",
    ],
    "01 - ACTUALIZACION": [
        "01 - ACTUALIZACION",
    ],
    "03 - AUTOPOSTULACION": [
        "03 - AUTOPOSTULACION",
    ]
}

# Mapeo de Placeholder → Lista de nombres a buscar
PLACEHOLDER_TO_FILE_MAP = {
    "$IMG{{ADJUNTO CERTIFICACION APE}}": FILE_NAME_VARIANTS["01 - CERTIFICADO REGISTRO APE"],
    "$IMG{{ADJUNTO_CERTIFICADO_APE}}": FILE_NAME_VARIANTS["01 - CERTIFICADO REGISTRO APE"],
    "$IMG{{PANTALLAZO ACTUALIZACION}}": FILE_NAME_VARIANTS["01 - ACTUALIZACION"],
    "$PDF{{PDF HV}}": FILE_NAME_VARIANTS["01 - HV"],
    "$IMG{{Anexo: Pantallazo de postulación a vacante}}": FILE_NAME_VARIANTS["03 - AUTOPOSTULACION"],
}

PLACEHOLDER_DEFINITIONS = [
    {"type": "img", "prefix": "$IMG{{", "suffix": "}}"},
    {"type": "pdf", "prefix": "$PDF{{", "suffix": "}}"}
]

POLICY_AUTO: Dict[str, Any] = {
    "width": "auto", "height": "auto", "orientation_match_scale": 0.85,
    "allow_upscale": False, "alignment": "CENTER", "output_format": "PNG"
}
POLICY_PDF: Dict[str, Any] = {
    "width": "auto", "height": "auto", "orientation_match_scale": 0.85,
    "allow_upscale": False, "alignment": "CENTER", "output_format": "PNG",
    "pdf_options": {"dpi": 150, "page_ranges": None}
}


def log_error(grupo: str, joven_name: str, error_info: Dict[str, Any]):
    """Agrega un error al log estructurado."""
    if grupo not in ERROR_LOG:
        ERROR_LOG[grupo] = {}
    if joven_name not in ERROR_LOG[grupo]:
        ERROR_LOG[grupo][joven_name] = []
    
    ERROR_LOG[grupo][joven_name].append(error_info)
    
    # También imprimir en consola
    print(f"  [FAIL] {error_info.get('message', 'Error desconocido')}")


def save_error_log():
    """Guarda el log de errores en formato JSON simplificado."""
    try:
        ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Contar totales
        total_errors = sum(len(errors) for grupo_errors in ERROR_LOG.values() 
                          for errors in grupo_errors.values())
        
        output = {
            "generated_at": datetime.now().isoformat(),
            "total_jovenes_with_errors": sum(len(jovenes) for jovenes in ERROR_LOG.values()),
            "total_errors": total_errors,
            "errors_by_group": ERROR_LOG
        }
        
        with open(ERROR_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 Error log guardado en: {ERROR_LOG_PATH}")
    except Exception as e:
        print(f"\n⚠️ No se pudo guardar el error log: {e}")


def find_joven_soportes_folder(grupo_name: str, joven_name_original: str) -> Optional[Path]:
    """Encuentra la carpeta raíz de un joven en SOPORTES_ROOT."""
    sanitized_joven_name = sanitize_key(joven_name_original)
    
    grupo_path = SOPORTES_ROOT / grupo_name
    if not grupo_path.exists():
        return None
        
    for folder in grupo_path.iterdir():
        if folder.is_dir():
            if sanitize_key(folder.name) == sanitized_joven_name:
                return folder 
    return None


def find_support_file_flexible(
    joven_root_path: Path, 
    file_name_variants: List[str],
    preferred_extensions: Tuple[str, ...],
    placeholder: str,
    grupo: str,
    joven_name: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Busca un archivo usando variantes de nombre y extensiones flexibles.
    
    Returns:
        (ruta_encontrada_REAL, tipo_encontrado: "image"|"pdf"|None)
    """
    
    search_paths = [
        joven_root_path / "FASE 3 - INTERMEDIACION" / "SOPORTES",
        joven_root_path / "FASE 3 - INTERMEDIACION" / "soporte",
        joven_root_path / "FASE 3 - INTERMEDIACION" / "SORTE",
        joven_root_path
    ]
    
    # Sanitizar variantes para comparación
    variants_sanitized = [sanitize_for_comparison(v) for v in file_name_variants]
    
    # 🆕 Recolectar TODOS los archivos disponibles para el log de errores
    all_files_found = []
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        # Recolectar archivos
        for f in search_path.iterdir():
            if f.is_file() and f.suffix.lower() in ALL_SUPPORTED_EXT:
                all_files_found.append(f.name)
        
        # 1️⃣ PRIMERO: Buscar con las extensiones PREFERIDAS
        for f in search_path.iterdir():
            if f.is_file() and f.suffix.lower() in preferred_extensions:
                sanitized_stem = sanitize_for_comparison(f.stem)
                
                if sanitized_stem in variants_sanitized:
                    # ✅ MATCH con extensión preferida
                    file_type = "image" if f.suffix.lower() in SUPPORTED_IMAGE_EXT else "pdf"
                    return str(f), file_type
        
        # 2️⃣ SEGUNDO: Si NO se encontró, buscar con CUALQUIER extensión válida
        for f in search_path.iterdir():
            if f.is_file() and f.suffix.lower() in ALL_SUPPORTED_EXT:
                sanitized_stem = sanitize_for_comparison(f.stem)
                
                if sanitized_stem in variants_sanitized:
                    # ✅ MATCH con extensión NO preferida (pero aceptable)
                    file_type = "image" if f.suffix.lower() in SUPPORTED_IMAGE_EXT else "pdf"
                    
                    # 🆕 Log de advertencia (pero NO falla)
                    print(f"  [WARN] '{placeholder}': Encontrado '{f.name}' (extensión no preferida pero válida)")
                    
                    return str(f), file_type
    
    # ❌ NO se encontró ninguna variante
    log_error(grupo, joven_name, {
        "placeholder": placeholder,
        "searched_variants": file_name_variants,
        "files_available": all_files_found[:10],  # Máximo 10 para no llenar el log
        "message": f"No se encontró archivo para '{placeholder}'"
    })
    
    return None, None


def get_placeholders_from_doc(doc_path: str) -> dict:
    config = { "source_path": doc_path, "definitions": PLACEHOLDER_DEFINITIONS }
    report = get_template_info(config)
    if report.get("success"):
        return report.get("placeholders", {})
    return {}

def copy_file_to_destination(source_path: Path, dest_path: Path):
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
    except Exception as e:
        print(f"  [FAIL] No se pudo copiar {source_path.name}: {e}")
        raise


# -------------------------------------------------------------
# -------------------[   EJECUCIÓN PRINCIPAL   ]-----------------
# -------------------------------------------------------------

def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   SCRIPT DE INSERCIÓN DE MEDIOS v6 (ULTIMATE FIX)       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"\n(E) Leyendo Actas desde: {ACTA_SOURCE_ROOT}")
    print(f"(T) Buscando Soportes en: {SOPORTES_ROOT}")
    print(f"(L) Escribiendo Salida en: {FINAL_OUTPUT_ROOT}")
    print(f"📋 Error Log: {ERROR_LOG_PATH}\n")

    if not ACTA_SOURCE_ROOT.exists() or not SOPORTES_ROOT.exists():
        print("❌ ERROR: Faltan directorios (Fuente de Actas o Soportes). Abortando.")
        return

    FINAL_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    stats = {"processed": 0, "copied": 0, "failed": 0, "media_inserted": 0}

    for grupo_path in ACTA_SOURCE_ROOT.iterdir():
        if not grupo_path.is_dir():
            continue
        grupo_joven = grupo_path.name
        
        for joven_path in grupo_path.iterdir():
            if not joven_path.is_dir():
                continue
            
            nombre_joven = joven_path.name
            print(f"\n{'-'*60}\nProcessing Joven: {nombre_joven} (Grupo: {grupo_joven})")

            try:
                joven_soportes_root = find_joven_soportes_folder(grupo_joven, nombre_joven)
                
                for acta_filename in joven_path.iterdir():
                    if not acta_filename.is_file():
                        continue
                        
                    source_acta_path = acta_filename
                    filename = acta_filename.name

                    final_destination_folder = (FINAL_OUTPUT_ROOT / grupo_joven / nombre_joven / 
                                                ACTA_SUBFOLDER_TARGET)
                    final_destination_path = final_destination_folder / filename

                    # Lógica "Pass-Through"
                    is_docx = filename.lower().endswith(".docx")
                    is_acta_2 = "ACTA 2" in filename.upper()
                    
                    if not is_docx or is_acta_2:
                        print(f"  [COPY] {filename} copiado tal cual.")
                        copy_file_to_destination(source_acta_path, final_destination_path)
                        stats["copied"] += 1
                        continue

                    # Es un DOCX con placeholders
                    stats["processed"] += 1
                    placeholders_in_doc = get_placeholders_from_doc(str(source_acta_path))
                    all_tags = (placeholders_in_doc.get("img", []) + 
                                placeholders_in_doc.get("pdf", []))

                    if not all_tags:
                        print(f"  [COPY] {filename} (sin placeholders). Copiado tal cual.")
                        copy_file_to_destination(source_acta_path, final_destination_path)
                        stats["copied"] += 1
                        continue
                        
                    print(f"  [PROCESS] {filename}: Encontrados {len(all_tags)} placeholders.")

                    if not joven_soportes_root:
                        raise Exception(f"No se encontró la carpeta de soportes para '{nombre_joven}' en {grupo_joven}")

                    # 🆕 Construcción de mapas con búsqueda flexible
                    image_map: List[Dict[str, Any]] = []
                    pdf_map: List[Dict[str, Any]] = []
                    has_missing_files = False
                    
                    for tag in all_tags:
                        file_name_variants = PLACEHOLDER_TO_FILE_MAP.get(tag)
                        
                        if not file_name_variants:
                            print(f"  [WARN] No hay mapeo definido para el tag: {tag}")
                            continue
                        
                        # Determinar extensiones preferidas
                        is_pdf_placeholder = tag.startswith("$PDF")
                        preferred_ext = SUPPORTED_PDF_EXT if is_pdf_placeholder else SUPPORTED_IMAGE_EXT
                        
                        # 🆕 Búsqueda flexible
                        found_file, found_type = find_support_file_flexible(
                            joven_soportes_root,
                            file_name_variants,
                            preferred_ext,
                            tag,
                            grupo_joven,
                            nombre_joven
                        )
                        
                        if not found_file:
                            has_missing_files = True
                            continue
                        
                        print(f"  [FOUND] {tag} → {Path(found_file).name} (tipo: {found_type})")
                        
                        # 🆕 Mapear según el tipo REAL del archivo encontrado
                        if found_type == "pdf":
                            pdf_map.append({
                                "placeholder": tag,
                                "pdf_path": found_file,
                                "layout_policy": POLICY_PDF
                            })
                        else:  # found_type == "image"
                            image_map.append({
                                "placeholder": tag,
                                "image_path": found_file,
                                "layout_policy": POLICY_AUTO
                            })

                    if has_missing_files:
                        raise Exception(f"Acta '{filename}': Faltan soportes, se aborta inserción.")

                    # Llamar al Ensamblador
                    assembler_config = {
                        "source_path": str(source_acta_path),
                        "target_path": str(final_destination_path),
                        "overwrite": True, "debug": False,
                        "remove_trailing_blank_page": True,
                        "image_map": image_map, "pdf_map": pdf_map
                    }
                    
                    print(f"  [LOAD] Ensamblando {len(image_map)} IMG y {len(pdf_map)} PDF...")
                    report = assemble_document_with_media(assembler_config)
                    
                    if report.get("success"):
                        print(f"  [SUCCESS] Acta procesada y guardada.")
                        stats["media_inserted"] += len(report["details"]["images_processed"])
                    else:
                        raise Exception(f"Falló el ensamblador: {report.get('error')}")

            except Exception as e:
                log_error(grupo_joven, nombre_joven, {
                    "type": "general_error",
                    "message": str(e)
                })
                stats["failed"] += 1
                
                print(f"  [FALLBACK] Copiando archivos originales...")
                for acta_filename in joven_path.iterdir():
                    if not acta_filename.is_file(): continue
                    final_dest = (FINAL_OUTPUT_ROOT / grupo_joven / nombre_joven / 
                                  ACTA_SUBFOLDER_TARGET / acta_filename.name)
                    copy_file_to_destination(acta_filename, final_dest)

    # Guardar log de errores
    save_error_log()

    # Reporte Final
    print(f"\n{'='*70}")
    print("PROCESO DE INSERCIÓN DE MEDIOS (ETL) FINALIZADO")
    print(f"{'='*70}")
    print(f"  Actas Procesadas (DOCX): {stats['processed']}")
    print(f"  Actas Copiadas (PDF/Acta 2): {stats['copied']}")
    print(f"  Actas con Fallos: {stats['failed']}")
    print(f"  Total Medios Insertados: {stats['media_inserted']}")
    print(f"\nDestino final: {FINAL_OUTPUT_ROOT}")
    print(f"📋 Error log: {ERROR_LOG_PATH}")
    
    if ERROR_LOG:
        print(f"\n{'='*70}")
        print("🚨 RESUMEN DE ERRORES")
        print(f"{'='*70}")
        for grupo, jovenes in ERROR_LOG.items():
            print(f"\n▼ GRUPO: {grupo}")
            for joven, errors in jovenes.items():
                print(f"  ├─ {joven}: {len(errors)} error(es)")
    else:
        print(f"\n{'='*70}")
        print("🎉 ¡Proceso finalizado sin errores! 🎉")
        print(f"{'='*70}")

if __name__ == "__main__":
    main()