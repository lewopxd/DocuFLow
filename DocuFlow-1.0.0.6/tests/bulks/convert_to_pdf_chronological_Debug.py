#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: convert_to_pdf_chronological_debug.py
Created: 2025-11-07
Author: @lewopxd

Description:
Script mejorado con logs detallados para debugging.
Convierte archivos Word a PDF, reorganiza por orden cronológico
y modifica metadata de los PDFs generados.
"""

import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# -------------------------------------------------------------
# -------------------[ IMPORTACIONES ]-------------------------
# -------------------------------------------------------------

try:
    from docx2pdf import convert
    print("✓ Librería docx2pdf importada correctamente.")
except ImportError:
    print("✗ ERROR: No se pudo importar docx2pdf.")
    print("   Instala con: pip install docx2pdf")
    sys.exit(1)

try:
    from PyPDF2 import PdfReader, PdfWriter
    print("✓ Librería PyPDF2 importada correctamente.")
except ImportError:
    print("✗ ERROR: No se pudo importar PyPDF2.")
    print("   Instala con: pip install PyPDF2")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[ CONFIGURACIÓN GLOBAL ]------------------
# -------------------------------------------------------------

CONFIG = {
    # Ruta base donde están los archivos generados por el script maestro
    "SOURCE_BASE_PATH": Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\FINAL_OUTPUT"),
    
    # Ruta donde se guardarán los PDFs convertidos
    "OUTPUT_BASE_PATH": Path(r"C:\Users\Admin\Desktop\FASE3-APROBADOS\OUTPUT_CONVERTED"),
    
    # Hojas a procesar (deben coincidir con las carpetas del script maestro)
    "SHEETS": ["PRESENCIAL", "VIRTUAL", "GUIAS"],
    
    # Metadata para los PDFs
    "PDF_AUTHOR": "JOSE BARRETO",
    "PDF_CREATOR": "DocuFlow - Sistema de Gestión Documental",
    
    # Patrones de archivo para identificar cada tipo de acta
    "ACTA_PATTERNS": {
        "ACTA_1": {
            "pattern": r"^(\d{8})_ACTA 1.*\.(docx|pdf)$",
            "output_name": "ActaRegistroAPE.pdf",
            "keywords": ["ACTA 1", "APE", "REGISTRO"]
        },
        "ACTA_2": {
            "pattern": r"^(\d{8})_ACTA 2.*\.(docx|pdf)$",
            "output_name": "ActaHabilidadesBlandas.pdf",
            "keywords": ["ACTA 2", "HABILIDADES", "PRESENCIAL", "VIRTUAL"]
        },
        "ACTA_3": {
            "pattern": r"^(\d{8})_ACTA 3.*\.(docx|pdf)$",
            "output_name": "ActaAutopostulacion_Feria.pdf",
            "keywords": ["ACTA 3", "AUTOPOSTULACION", "FERIA"]
        }
    }
}

# -------------------------------------------------------------
# -------------------[ FUNCIONES DE DEBUG ]--------------------
# -------------------------------------------------------------

def log_separator(char="=", length=70):
    """Imprime una línea separadora."""
    print(char * length)

def log_section(title: str):
    """Imprime un título de sección."""
    log_separator()
    print(f"  {title}")
    log_separator()

def log_subsection(title: str):
    """Imprime un subtítulo."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")

def explore_directory_structure(path: Path, max_depth: int = 3, current_depth: int = 0):
    """
    Explora y muestra la estructura de directorios de forma recursiva.
    
    Args:
        path: Ruta a explorar
        max_depth: Profundidad máxima de exploración
        current_depth: Profundidad actual (para recursión)
    """
    indent = "  " * current_depth
    
    if not path.exists():
        print(f"{indent}✗ No existe: {path}")
        return
    
    if not path.is_dir():
        print(f"{indent}✗ No es un directorio: {path}")
        return
    
    try:
        items = list(path.iterdir())
        dirs = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file()]
        
        print(f"{indent}📁 {path.name}/ ({len(dirs)} carpetas, {len(files)} archivos)")
        
        # Mostrar archivos
        if files and current_depth < max_depth:
            for file in sorted(files)[:5]:  # Mostrar solo los primeros 5
                print(f"{indent}  📄 {file.name}")
            if len(files) > 5:
                print(f"{indent}  ... y {len(files) - 5} archivos más")
        
        # Explorar subdirectorios
        if current_depth < max_depth:
            for directory in sorted(dirs)[:10]:  # Limitar a 10 carpetas
                explore_directory_structure(directory, max_depth, current_depth + 1)
            if len(dirs) > 10:
                print(f"{indent}  ... y {len(dirs) - 10} carpetas más")
    
    except Exception as e:
        print(f"{indent}✗ Error explorando {path}: {e}")

def list_all_files_in_folder(folder: Path) -> List[Path]:
    """
    Lista TODOS los archivos en una carpeta (recursivamente).
    
    Args:
        folder: Carpeta a explorar
    
    Returns:
        Lista de rutas de archivos
    """
    all_files = []
    try:
        for item in folder.rglob("*"):
            if item.is_file():
                all_files.append(item)
    except Exception as e:
        print(f"✗ Error listando archivos en {folder}: {e}")
    return all_files

# -------------------------------------------------------------
# -------------------[ FUNCIONES AUXILIARES ]------------------
# -------------------------------------------------------------

def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Extrae la fecha en formato YYYYMMDD del nombre del archivo.
    
    Args:
        filename: Nombre del archivo (ej: "20251103_ACTA 1 - APE...")
    
    Returns:
        Fecha en formato YYYYMMDD o None si no se encuentra
    """
    match = re.match(r'^(\d{8})_', filename)
    result = match.group(1) if match else None
    
    # Log detallado
    if result:
        print(f"      🔍 Fecha extraída de '{filename}': {result}")
    else:
        print(f"      ⚠ No se pudo extraer fecha de '{filename}'")
    
    return result

def parse_date_from_string(date_str: str) -> datetime:
    """
    Convierte una fecha en formato YYYYMMDD a objeto datetime.
    
    Args:
        date_str: Fecha en formato YYYYMMDD (ej: "20251103")
    
    Returns:
        Objeto datetime
    """
    return datetime.strptime(date_str, "%Y%m%d")

def identify_acta_type(filename: str) -> Optional[str]:
    """
    Identifica el tipo de acta basándose en el nombre del archivo.
    
    Args:
        filename: Nombre del archivo
    
    Returns:
        Clave del tipo de acta (ACTA_1, ACTA_2, ACTA_3) o None
    """
    print(f"      🔍 Analizando tipo de acta para: '{filename}'")
    
    for acta_type, config in CONFIG["ACTA_PATTERNS"].items():
        pattern = config["pattern"]
        print(f"         Probando patrón {acta_type}: {pattern}")
        
        if re.match(pattern, filename, re.IGNORECASE):
            print(f"         ✓ MATCH con {acta_type}")
            return acta_type
        else:
            print(f"         ✗ No match con {acta_type}")
    
    print(f"      ⚠ No se identificó tipo de acta para '{filename}'")
    return None

def get_files_in_person_folder(person_folder: Path) -> List[Dict]:
    """
    Obtiene todos los archivos Word/PDF de la carpeta de una persona.
    
    Args:
        person_folder: Ruta a la carpeta de la persona
    
    Returns:
        Lista de diccionarios con información de cada archivo
    """
    print(f"\n  🔍 Buscando archivos en: {person_folder}")
    print(f"     Ruta absoluta: {person_folder.absolute()}")
    print(f"     ¿Existe?: {person_folder.exists()}")
    print(f"     ¿Es directorio?: {person_folder.is_dir()}")
    
    files_info = []
    
    # Primero, listar TODO lo que hay en la carpeta
    print(f"\n  📋 CONTENIDO DE LA CARPETA:")
    try:
        all_items = list(person_folder.iterdir())
        print(f"     Total de items: {len(all_items)}")
        
        for item in all_items:
            item_type = "📁 DIR " if item.is_dir() else "📄 FILE"
            print(f"       {item_type}: {item.name}")
    except Exception as e:
        print(f"     ✗ Error listando contenido: {e}")
        return files_info
    
    # Buscar archivos .docx y .pdf
    print(f"\n  🔎 Buscando archivos .docx y .pdf...")
    
    for ext in ['*.docx', '*.pdf']:
        print(f"\n     Buscando con patrón: {ext}")
        found_files = list(person_folder.glob(ext))
        print(f"     Encontrados: {len(found_files)} archivos")
        
        for file_path in found_files:
            print(f"\n     📄 Procesando: {file_path.name}")
            
            date_str = extract_date_from_filename(file_path.name)
            acta_type = identify_acta_type(file_path.name)
            
            if date_str and acta_type:
                file_info = {
                    'path': file_path,
                    'name': file_path.name,
                    'date_str': date_str,
                    'date_obj': parse_date_from_string(date_str),
                    'acta_type': acta_type,
                    'extension': file_path.suffix.lower()
                }
                files_info.append(file_info)
                print(f"        ✓ VÁLIDO - Fecha: {date_str}, Tipo: {acta_type}")
            else:
                print(f"        ✗ DESCARTADO - Fecha: {date_str}, Tipo: {acta_type}")
    
    print(f"\n  📊 RESUMEN: {len(files_info)} archivos válidos encontrados")
    
    return files_info

def sort_files_chronologically(files_info: List[Dict]) -> List[Dict]:
    """
    Ordena los archivos cronológicamente por fecha.
    
    Args:
        files_info: Lista de diccionarios con información de archivos
    
    Returns:
        Lista ordenada por fecha (más antigua primero)
    """
    sorted_list = sorted(files_info, key=lambda x: x['date_obj'])
    
    print(f"\n  📅 Orden cronológico:")
    for idx, file_info in enumerate(sorted_list, start=1):
        print(f"     {idx}. {file_info['date_str']} - {file_info['name']}")
    
    return sorted_list

def convert_word_to_pdf_safe(word_path: Path, pdf_path: Path) -> bool:
    """
    Convierte un archivo Word a PDF de forma segura.
    
    Args:
        word_path: Ruta al archivo .docx
        pdf_path: Ruta donde guardar el PDF
    
    Returns:
        True si la conversión fue exitosa, False en caso contrario
    """
    try:
        print(f"    🔄 Convirtiendo: {word_path.name}")
        print(f"       Origen: {word_path}")
        print(f"       Destino: {pdf_path}")
        
        # Asegurar que el directorio de salida existe
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convertir a PDF
        convert(str(word_path), str(pdf_path))
        
        # Verificar que el archivo se creó correctamente
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            size_kb = pdf_path.stat().st_size / 1024
            print(f"    ✓ PDF creado: {pdf_path.name} ({size_kb:.2f} KB)")
            return True
        else:
            print(f"    ✗ Error: PDF vacío o no creado")
            return False
            
    except Exception as e:
        print(f"    ✗ Error en conversión: {type(e).__name__}: {e}")
        import traceback
        print(f"    Traceback: {traceback.format_exc()}")
        return False

def modify_pdf_metadata(pdf_path: Path, author: str, date_obj: datetime) -> bool:
    """
    Modifica el metadata de un archivo PDF.
    
    Args:
        pdf_path: Ruta al archivo PDF
        author: Nombre del autor
        date_obj: Fecha de creación/modificación
    
    Returns:
        True si la modificación fue exitosa, False en caso contrario
    """
    try:
        print(f"    📝 Modificando metadata de: {pdf_path.name}")
        
        # Leer el PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        
        # Copiar todas las páginas
        for page in reader.pages:
            writer.add_page(page)
        
        # Crear metadata
        metadata = {
            '/Author': author,
            '/Creator': CONFIG["PDF_CREATOR"],
            '/Producer': CONFIG["PDF_CREATOR"],
            '/Title': pdf_path.stem,
            '/CreationDate': date_obj.strftime("D:%Y%m%d%H%M%S"),
            '/ModDate': date_obj.strftime("D:%Y%m%d%H%M%S")
        }
        
        writer.add_metadata(metadata)
        
        # Crear archivo temporal
        temp_path = pdf_path.with_suffix('.tmp')
        
        # Escribir el nuevo PDF
        with open(temp_path, 'wb') as output_file:
            writer.write(output_file)
        
        # Reemplazar el archivo original
        temp_path.replace(pdf_path)
        
        print(f"    ✓ Metadata modificado: Autor={author}, Fecha={date_obj.strftime('%Y-%m-%d')}")
        return True
        
    except Exception as e:
        print(f"    ✗ Error modificando metadata: {type(e).__name__}: {e}")
        import traceback
        print(f"    Traceback: {traceback.format_exc()}")
        return False

def set_file_timestamps(file_path: Path, date_obj: datetime):
    """
    Modifica las fechas de creación y modificación del archivo.
    
    Args:
        file_path: Ruta al archivo
        date_obj: Fecha a establecer
    """
    try:
        timestamp = date_obj.timestamp()
        
        # Modificar fecha de modificación y acceso
        import os
        os.utime(file_path, (timestamp, timestamp))
        
        print(f"    ✓ Timestamps actualizados: {date_obj.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"    ⚠ Advertencia: No se pudieron modificar timestamps: {e}")

def process_person_folder(person_folder: Path, sheet_name: str, output_base: Path) -> Dict:
    """
    Procesa la carpeta de una persona: convierte, renombra y reorganiza archivos.
    
    Args:
        person_folder: Ruta a la carpeta de la persona
        sheet_name: Nombre de la hoja (PRESENCIAL, VIRTUAL, GUIAS)
        output_base: Ruta base de salida
    
    Returns:
        Diccionario con estadísticas del proceso
    """
    person_name = person_folder.name
    
    log_subsection(f"PROCESANDO: {person_name}")
    
    stats = {
        'person_name': person_name,
        'files_found': 0,
        'files_converted': 0,
        'files_copied': 0,
        'errors': []
    }
    
    # Obtener todos los archivos
    files_info = get_files_in_person_folder(person_folder)
    stats['files_found'] = len(files_info)
    
    if not files_info:
        print(f"\n  ⚠ NO SE ENCONTRARON ARCHIVOS VÁLIDOS")
        print(f"     Esto puede deberse a:")
        print(f"     1. Los archivos no tienen el formato de fecha correcto (YYYYMMDD_)")
        print(f"     2. Los archivos no coinciden con los patrones de ACTA")
        print(f"     3. No hay archivos .docx o .pdf en la carpeta")
        return stats
    
    print(f"\n  ✓ Archivos válidos encontrados: {len(files_info)}")
    
    # Ordenar cronológicamente
    sorted_files = sort_files_chronologically(files_info)
    
    # Crear carpeta de salida
    output_folder = output_base / sheet_name / person_name / "FASE 3 - INTERMEDIACION" / f"C1_F3_FINAL_PDFS_{person_name}"
    
    print(f"\n  📁 Carpeta de salida:")
    print(f"     {output_folder}")
    
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"     ✓ Carpeta creada/verificada")
    
    # Procesar cada archivo
    for idx, file_info in enumerate(sorted_files, start=1):
        try:
            print(f"\n  {'─' * 68}")
            print(f"  ARCHIVO {idx}/{len(sorted_files)}")
            print(f"  {'─' * 68}")
            
            # Determinar nombre de salida
            acta_config = CONFIG["ACTA_PATTERNS"][file_info['acta_type']]
            output_name = f"{idx:03d}{acta_config['output_name']}"
            output_path = output_folder / output_name
            
            print(f"  📄 Archivo origen: {file_info['name']}")
            print(f"  📄 Archivo destino: {output_name}")
            print(f"  📅 Fecha: {file_info['date_str']}")
            print(f"  🏷️  Tipo: {file_info['acta_type']}")
            print(f"  📦 Extensión: {file_info['extension']}")
            
            # Si es Word, convertir a PDF
            if file_info['extension'] == '.docx':
                print(f"\n  🔄 Proceso: Word → PDF")
                temp_pdf = output_folder / f"temp_{output_name}"
                
                if convert_word_to_pdf_safe(file_info['path'], temp_pdf):
                    # Modificar metadata
                    if modify_pdf_metadata(temp_pdf, CONFIG["PDF_AUTHOR"], file_info['date_obj']):
                        # Renombrar al nombre final
                        temp_pdf.rename(output_path)
                        stats['files_converted'] += 1
                        print(f"  ✓ CONVERSIÓN EXITOSA")
                    else:
                        error_msg = f"Error modificando metadata: {file_info['name']}"
                        stats['errors'].append(error_msg)
                        print(f"  ✗ ERROR EN METADATA")
                else:
                    error_msg = f"Error convirtiendo: {file_info['name']}"
                    stats['errors'].append(error_msg)
                    print(f"  ✗ ERROR EN CONVERSIÓN")
                    continue
            
            # Si ya es PDF, copiar y modificar metadata
            elif file_info['extension'] == '.pdf':
                print(f"\n  📋 Proceso: PDF → PDF (copia)")
                shutil.copy2(file_info['path'], output_path)
                modify_pdf_metadata(output_path, CONFIG["PDF_AUTHOR"], file_info['date_obj'])
                stats['files_copied'] += 1
                print(f"  ✓ COPIA EXITOSA")
            
            # Modificar timestamps del archivo
            set_file_timestamps(output_path, file_info['date_obj'])
            
        except Exception as e:
            error_msg = f"Error procesando {file_info['name']}: {type(e).__name__}: {e}"
            print(f"\n  ✗ ERROR CRÍTICO: {error_msg}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()}")
            stats['errors'].append(error_msg)
    
    # Resumen de la persona
    print(f"\n  {'═' * 68}")
    print(f"  RESUMEN: {person_name}")
    print(f"  {'═' * 68}")
    print(f"  ✓ Archivos encontrados: {stats['files_found']}")
    print(f"  ✓ Convertidos (Word→PDF): {stats['files_converted']}")
    print(f"  ✓ Copiados (PDF→PDF): {stats['files_copied']}")
    if stats['errors']:
        print(f"  ✗ Errores: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"     - {error}")
    
    return stats

# -------------------------------------------------------------
# -------------------[ EJECUCIÓN PRINCIPAL ]-------------------
# -------------------------------------------------------------

def main():
    """Función principal del script."""
    log_separator("═")
    print("     CONVERSIÓN A PDF Y REORGANIZACIÓN CRONOLÓGICA (DEBUG MODE)")
    log_separator("═")
    
    print(f"\n{'═' * 70}")
    print("  CONFIGURACIÓN INICIAL")
    print(f"{'═' * 70}")
    print(f"\n📂 Ruta de origen: {CONFIG['SOURCE_BASE_PATH']}")
    print(f"   Absoluta: {CONFIG['SOURCE_BASE_PATH'].absolute()}")
    print(f"   ¿Existe?: {CONFIG['SOURCE_BASE_PATH'].exists()}")
    
    print(f"\n📂 Ruta de salida: {CONFIG['OUTPUT_BASE_PATH']}")
    print(f"   Absoluta: {CONFIG['OUTPUT_BASE_PATH'].absolute()}")
    
    print(f"\n📋 Hojas a procesar: {', '.join(CONFIG['SHEETS'])}")
    
    print(f"\n📝 Metadata PDF:")
    print(f"   Autor: {CONFIG['PDF_AUTHOR']}")
    print(f"   Creador: {CONFIG['PDF_CREATOR']}")
    
    print(f"\n🏷️  Patrones de actas:")
    for acta_type, config in CONFIG['ACTA_PATTERNS'].items():
        print(f"   {acta_type}: {config['pattern']}")
    
    # Verificar que existe la ruta de origen
    if not CONFIG['SOURCE_BASE_PATH'].exists():
        print(f"\n{'✗' * 70}")
        print(f"ERROR CRÍTICO: La ruta de origen no existe")
        print(f"Ruta: {CONFIG['SOURCE_BASE_PATH']}")
        print(f"{'✗' * 70}")
        sys.exit(1)
    
    # Explorar estructura de directorios de origen
    log_section("EXPLORANDO ESTRUCTURA DE ORIGEN")
    explore_directory_structure(CONFIG['SOURCE_BASE_PATH'], max_depth=3)
    
    # Crear directorio de salida
    CONFIG['OUTPUT_BASE_PATH'].mkdir(parents=True, exist_ok=True)
    print(f"\n✓ Directorio de salida creado/verificado")
    
    # Estadísticas globales
    global_stats = {
        'total_persons': 0,
        'total_files_found': 0,
        'total_files_converted': 0,
        'total_files_copied': 0,
        'total_errors': 0,
        'processed_sheets': []
    }
    
    # Procesar cada hoja
    for sheet_name in CONFIG['SHEETS']:
        log_section(f"HOJA: {sheet_name}")
        
        sheet_path = CONFIG['SOURCE_BASE_PATH'] / sheet_name
        
        print(f"\n📁 Ruta de la hoja: {sheet_path}")
        print(f"   ¿Existe?: {sheet_path.exists()}")
        print(f"   ¿Es directorio?: {sheet_path.is_dir() if sheet_path.exists() else 'N/A'}")
        
        if not sheet_path.exists():
            print(f"\n⚠ ADVERTENCIA: No se encontró la carpeta {sheet_name}")
            print(f"   Ruta buscada: {sheet_path}")
            print(f"   Saltando a la siguiente hoja...")
            continue
        
        # Obtener todas las carpetas de personas
        print(f"\n🔍 Buscando carpetas de personas...")
        person_folders = [f for f in sheet_path.iterdir() if f.is_dir()]
        
        print(f"   Total encontradas: {len(person_folders)}")
        
        if not person_folders:
            print(f"\n⚠ No se encontraron carpetas de personas en {sheet_name}")
            continue
        
        print(f"\n📋 Lista de personas encontradas:")
        for idx, folder in enumerate(person_folders, start=1):
            print(f"   {idx}. {folder.name}")
        
        # Procesar cada persona
        sheet_stats = {
            'persons': 0,
            'files_found': 0,
            'files_converted': 0,
            'files_copied': 0,
            'errors': 0
        }
        
        for person_folder in person_folders:
            stats = process_person_folder(
                person_folder, 
                sheet_name, 
                CONFIG['OUTPUT_BASE_PATH']
            )
            
            # Actualizar estadísticas
            sheet_stats['persons'] += 1
            sheet_stats['files_found'] += stats['files_found']
            sheet_stats['files_converted'] += stats['files_converted']
            sheet_stats['files_copied'] += stats['files_copied']
            sheet_stats['errors'] += len(stats['errors'])
        
        # Resumen de la hoja
        print(f"\n{'═' * 70}")
        print(f"  RESUMEN HOJA: {sheet_name}")
        print(f"{'═' * 70}")
        print(f"  👥 Personas procesadas: {sheet_stats['persons']}")
        print(f"  📄 Archivos encontrados: {sheet_stats['files_found']}")
        print(f"  ✓ Convertidos: {sheet_stats['files_converted']}")
        print(f"  ✓ Copiados: {sheet_stats['files_copied']}")
        print(f"  ✗ Errores: {sheet_stats['errors']}")
        
        # Actualizar estadísticas globales
        global_stats['total_persons'] += sheet_stats['persons']
        global_stats['total_files_found'] += sheet_stats['files_found']
        global_stats['total_files_converted'] += sheet_stats['files_converted']
        global_stats['total_files_copied'] += sheet_stats['files_copied']
        global_stats['total_errors'] += sheet_stats['errors']
        global_stats['processed_sheets'].append(sheet_name)
    
    # Reporte final
    log_separator("═")
    print("     PROCESO FINALIZADO")
    log_separator("═")
    
    print(f"\n📊 ESTADÍSTICAS GLOBALES:")
    print(f"  {'─' * 66}")
    print(f"  👥 Total personas procesadas: {global_stats['total_persons']}")
    print(f"  📄 Total archivos encontrados: {global_stats['total_files_found']}")
    print(f"  ✓ Archivos convertidos (Word→PDF): {global_stats['total_files_converted']}")
    print(f"  ✓ Archivos copiados (PDF→PDF): {global_stats['total_files_copied']}")
    print(f"  ✗ Total errores: {global_stats['total_errors']}")
    print(f"  📋 Hojas procesadas: {', '.join(global_stats['processed_sheets'])}")
    print(f"  {'─' * 66}")
    
    print(f"\n📂 Resultado guardado en:")
    print(f"   {CONFIG['OUTPUT_BASE_PATH'].absolute()}")
    
    if global_stats['total_errors'] > 0:
        print(f"\n⚠ ATENCIÓN: Se encontraron {global_stats['total_errors']} errores")
        print(f"   Revisa los logs anteriores para más detalles")
    
    if global_stats['total_files_found'] == 0:
        print(f"\n{'⚠' * 70}")
        print(f"  ADVERTENCIA CRÍTICA:")
        print(f"  No se encontraron archivos válidos en ninguna carpeta")
        print(f"  {'⚠' * 70}")
        print(f"\n  Posibles causas:")
        print(f"  1. Los archivos no tienen el formato: YYYYMMDD_ACTA X...")
        print(f"  2. Los archivos están en subcarpetas no exploradas")
        print(f"  3. La ruta de origen no es la correcta")
        print(f"  4. Los patrones de ACTA no coinciden con los nombres reales")
        print(f"\n  Recomendaciones:")
        print(f"  1. Verifica la estructura de carpetas en la sección 'EXPLORANDO ESTRUCTURA'")
        print(f"  2. Revisa los nombres de archivos en los logs de cada persona")
        print(f"  3. Compara los patrones configurados con los nombres reales")
    
    log_separator("═")
    print("           CONVERSIÓN COMPLETADA")
    log_separator("═")

if __name__ == "__main__":
    main()