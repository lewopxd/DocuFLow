#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script: bulk_c1f2_CONVERT_TO_PDF.py
Propósito: Convierte documentos Word a PDF en lotes con renombrado según reglas CONTAINS

Uso:
    1. Configurar INPUT_PATH (carpeta con subcarpetas de jóvenes)
    2. Configurar FILE_RULES con el mapeo de nombres
    3. Ejecutar el script

El script:
    - Escanea recursivamente INPUT_PATH
    - Para cada archivo DOCX encontrado, aplica las reglas CONTAINS
    - Genera PDFs en la misma carpeta que el DOCX original
"""

import os
import sys
from pathlib import Path

# Añadir 'src' al path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
src_path = project_root / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
    print(f"✓ Ruta 'src' añadida a sys.path: {src_path}")

# Importar WordToPdfJob
try:
    from assembler.jobs.word_to_pdf_job import WordToPdfJob
except ImportError as e:
    print(f"❌ No se pudo importar WordToPdfJob: {e}")
    sys.exit(1)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Ruta de entrada (carpeta con subcarpetas de jóvenes que contienen DOCX)
INPUT_PATH = Path(r"C:\Users\Admin\Desktop\PLAYGROUND_7\F2 CURSOS CORTOS\OUTPUT\CERTIFICADOS")

# Reglas de conversión con CONTAINS
FILE_RULES = [
    {
        "comparator": "CONTAINS",
        "pattern": "ACTA 1",
        "ignore_case": True,
        "output": {"filename": "001ActaInicioRuta.pdf"}
    },
    {
        "comparator": "CONTAINS",
        "pattern": "ACTA 2",
        "ignore_case": True,
        "output": {"filename": "002ActaPermanenciaRuta.pdf"}
    },
    {
        "comparator": "CONTAINS",
        "pattern": "ACTA 3",
        "ignore_case": True,
        "output": {"filename": "003ActaFinalizacionRuta.pdf"}
    }
]

# Regla por defecto para archivos que no coincidan con ninguna regla
DEFAULT_RULE = {"action": "SKIP"}  # Opciones: "SKIP" | "CONVERT_SAME_NAME"

# Configuración de compresión
COMPRESSION_CONFIG = {
    "enabled": True,
    "level": "high",  # low | medium | high
    "max_size_kb": None
}

# Configuración de metadata
METADATA_CONFIG = {
    "author": "Marcela",
    "creator": "MSWORD",
    "producer": "MSWORD",
    "custom": {}
}

# Otras opciones
CONVERSION_METHOD = "office"   # "office" (MS Word) | "libreoffice" (CLI)
OVERWRITE_EXISTING = True      # Sobrescribir PDFs existentes

# =============================================================================
# EJECUCIÓN
# =============================================================================

def main():
    print("=" * 70)
    print("📄 CONVERSIÓN MASIVA WORD → PDF")
    print("=" * 70)
    print(f"📁 Carpeta entrada: {INPUT_PATH}")
    print(f"📋 Reglas: {len(FILE_RULES)} definidas")
    print(f"🔧 Método: {CONVERSION_METHOD.upper()}")
    print(f"🗜️  Compresión: {COMPRESSION_CONFIG['level'] if COMPRESSION_CONFIG['enabled'] else 'desactivada'}")
    print()
    
    # Verificar carpeta existe
    if not INPUT_PATH.exists():
        print(f"❌ La carpeta de entrada no existe: {INPUT_PATH}")
        sys.exit(1)
    
    # Buscar subcarpetas (cada joven)
    subdirs = [d for d in INPUT_PATH.iterdir() if d.is_dir()]
    
    if not subdirs:
        print("⚠️  No se encontraron subcarpetas en la ruta de entrada.")
        print("    Verificando archivos DOCX directamente en la carpeta raíz...")
        subdirs = [INPUT_PATH]  # Procesar la carpeta misma
    
    print(f"📂 {len(subdirs)} carpetas a procesar")
    print()
    
    total_success = 0
    total_failed = 0
    
    for subdir in subdirs:
        print(f"  📂 Procesando: {subdir.name}")
        
        # Configurar job para esta carpeta
        job_config = {
            "mode": "file_rules",
            "method": CONVERSION_METHOD,  # "office" | "libreoffice"
            "source": {
                "base_path": str(subdir),
                "scan_mode": "ALL"  # Procesar todos los archivos en esta carpeta
            },
            "file_rules": FILE_RULES,
            "default_rule": DEFAULT_RULE,
            "overwrite": OVERWRITE_EXISTING,
            "compression": COMPRESSION_CONFIG,
            "metadata": METADATA_CONFIG
        }
        
        # Ejecutar job
        job = WordToPdfJob(job_config)
        result = job.execute()
        
        # Contar resultados (JobResult usa .data dict para resultados)
        if result.success:
            data = result.data if hasattr(result, 'data') else {}
            job_summary = data.get("job_summary", {})
            success = job_summary.get("success_count", 0)
            failed = job_summary.get("failure_count", 0)
            total_success += success
            total_failed += failed
            print(f"    ✅ {success} PDFs generados")
        else:
            error_msg = result.error if hasattr(result, 'error') else 'desconocido'
            print(f"    ❌ Error: {error_msg}")
            total_failed += 1
    
    print()
    print("=" * 70)
    print("📄 CONVERSIÓN COMPLETADA")
    print("=" * 70)
    print(f"  ✅ PDFs exitosos: {total_success}")
    print(f"  ❌ PDFs fallidos: {total_failed}")
    print()


if __name__ == "__main__":
    main()
