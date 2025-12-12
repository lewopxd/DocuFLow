#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test aislado de MSOfficeConverter para diagnosticar problemas
"""

import sys
from pathlib import Path

# Añadir src al path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

print("=" * 60)
print("🧪 TEST: MSOfficeConverter (Aislado)")
print("=" * 60)

# ============================================
# CONFIGURACIÓN - AJUSTAR SEGÚN TU SISTEMA
# ============================================
TEST_DOCX = Path(r"C:\Users\Admin\Desktop\PLAYGROUND_7\F2 CURSOS CORTOS\OUTPUT\CERTIFICADOS\ADRIANA MORENO JIMENEZ")
OUTPUT_DIR = Path(r"C:\Users\Admin\Desktop\TEST_PDF_OUTPUT")

# ============================================
# FASE 1: Verificar que existe archivo de prueba
# ============================================
docx_files = list(TEST_DOCX.glob("*.docx"))
if not docx_files:
    print(f"❌ No hay archivos .docx en: {TEST_DOCX}")
    sys.exit(1)

test_file = docx_files[0]
print(f"📄 Archivo de prueba: {test_file.name}")
print(f"📂 Ruta: {test_file}")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_pdf = OUTPUT_DIR / f"{test_file.stem}_TEST.pdf"
print(f"📝 Salida esperada: {output_pdf}")
print()

# ============================================
# FASE 2: Probar MSOfficeConverter
# ============================================
print("🔧 Importando MSOfficeConverter...")
try:
    from core.pdf_helpers.word_to_pdf_converter_msOffice import MSOfficeConverter
    print("✅ Importación exitosa")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    sys.exit(1)

print()
print("🚀 Iniciando conversión...")
print("-" * 40)

converter = MSOfficeConverter()
try:
    result = converter.convert_single(test_file, output_pdf, timeout_seconds=60)
    
    print("-" * 40)
    print(f"📊 RESULTADO:")
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    print(f"   Source: {result.source_path}")
    print(f"   Target: {result.target_path}")
    
    if result.success and output_pdf.exists():
        size_kb = output_pdf.stat().st_size / 1024
        print(f"   Size: {size_kb:.1f} KB")
        print()
        print("✅ ¡CONVERSIÓN EXITOSA!")
    else:
        print()
        print("❌ CONVERSIÓN FALLIDA")
        if result.error:
            print(f"   Detalle del error: {result.error}")
        else:
            print("   (Sin mensaje de error)")
            
finally:
    print()
    print("🧹 Limpiando recursos...")
    converter.cleanup()

print()
print("=" * 60)
print("🏁 Test completado")
print("=" * 60)
