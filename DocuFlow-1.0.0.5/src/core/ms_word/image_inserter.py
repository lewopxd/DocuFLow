#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  image_inserter.py
Created: 2025-11-06
Author: @lewopxd
Last Updated: 2025-11-06

Description:
Main module for inserting images into .docx documents.
Includes a mandatory post-processing step to patch the .docx
manifest [Content_Types].xml to prevent file corruption.
(v9: Uses paragraph clearing instead of deletion for stability.)
"""

import os
import tempfile
import shutil
import zipfile
import io
from pathlib import Path
from typing import Dict, Any, Optional, Set, List
import docx
from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx.table import _Cell
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

# Importar lxml para la reparación del manifiesto
try:
    from lxml import etree
except ImportError:
    print("❌ CRITICAL: 'lxml' library not found. (Debería ser una dependencia de python-docx)")
    etree = None

# --- [ INICIO: AJUSTE DE PYTHONPATH ] ---
import sys
try:
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    src_path = project_root
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
except NameError:
    pass
# --- [ FIN: AJUSTE DE PYTHONPATH ] ---

try:
    from core.file_helpers.path_utils import create_safe_temp_copy
    from core.ms_word.layout_engine import get_page_available_space, calculate_final_dimensions
    from core.image_helpers.image_sanitizer import sanitize_image
except ImportError as e:
    print(f"❌ CRITICAL (ImageInserter): No se pudieron importar módulos del Core.")
    print(f"   Error: {e}")
    create_safe_temp_copy = None
    get_page_available_space = None
    calculate_final_dimensions = None
    sanitize_image = None
    
# Mapeo de alineación
ALIGNMENT_MAP = {
    "LEFT": WD_ALIGN_PARAGRAPH.LEFT,
    "CENTER": WD_ALIGN_PARAGRAPH.CENTER,
    "RIGHT": WD_ALIGN_PARAGRAPH.RIGHT,
    "JUSTIFY": WD_ALIGN_PARAGRAPH.JUSTIFY
}

# --- [ INICIO: LÓGICA DE PARCHEO DE MANIFIESTO ] ---

# Definiciones de Namespace y MIME para el parche
XML_NS_MAP = {
    'ct': "http://schemas.openxmlformats.org/package/2006/content-types"
}
MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tif": "image/tiff",
    "tiff": "image/tiff"
}

def _patch_manifest(docx_path: str, extensions_added: Set[str], debug: bool = False) -> None:
    """
    Audita y repara el manifiesto [Content_Types].xml dentro del .docx.
    (Versión corregida que usa 'types_root' correctamente).
    """
    if not etree:
        raise ImportError("lxml es requerido para la reparación del manifiesto.")

    if debug:
        print(f"    [DEBUG] Iniciando parcheo de manifiesto para: {docx_path}")
        print(f"    [DEBUG] Asegurando tipos de contenido para: {extensions_added}")

    zip_data_buffer = {}
    manifest_xml_bytes = None
    manifest_filename = "[Content_Types].xml"

    # 1. Lectura en Memoria
    try:
        with zipfile.ZipFile(docx_path, 'r') as zip_read:
            for info in zip_read.infolist():
                if info.filename == manifest_filename:
                    manifest_xml_bytes = zip_read.read(info.filename)
                else:
                    zip_data_buffer[info.filename] = zip_read.read(info.filename)
    except Exception as e:
        raise IOError(f"No se pudo leer el paquete .docx para parchear. Error: {e}")

    if manifest_xml_bytes is None:
        raise FileNotFoundError("Manifiesto '[Content_Types].xml' no encontrado. El archivo no es un .docx válido.")

    # 2. Reparación del Manifiesto
    parser = etree.XMLParser(recover=True, remove_blank_text=True)
    types_root = etree.fromstring(manifest_xml_bytes, parser) # Corregido

    tags_added = 0
    for ext in extensions_added:
        if ext.lower() not in MIME_TYPES:
            continue
        
        mime_type = MIME_TYPES[ext.lower()]
        
        xpath_query = f'.//ct:Default[@Extension="{ext.lower()}"]'
        found = types_root.xpath(xpath_query, namespaces=XML_NS_MAP)
        
        if not found:
            # 3. Si no existe, la creamos
            if debug:
                print(f"    [DEBUG] -> Manifiesto corrupto. Añadiendo tag para: {ext}")
            
            new_tag = etree.SubElement(
                types_root,
                f"{{{XML_NS_MAP['ct']}}}Default",
                Extension=ext.lower(),
                ContentType=mime_type
            )
            tags_added += 1
    
    if tags_added == 0:
        if debug:
            print("    [DEBUG] -> Manifiesto ya era válido. No se requiere parche.")
        return # No es necesario re-escribir

    # 4. Re-escritura Atómica
    repaired_manifest_bytes = etree.tostring(
        types_root, # Usar 'types_root' directamente
        pretty_print=False, 
        xml_declaration=True, 
        encoding="UTF-8", 
        standalone=True
    )
    
    try:
        with zipfile.ZipFile(docx_path, 'w', compression=zipfile.ZIP_DEFLATED) as zip_write:
            # Escribir el manifiesto reparado
            zip_write.writestr(manifest_filename, repaired_manifest_bytes)
            # Escribir todos los demás archivos de vuelta
            for filename, data in zip_data_buffer.items():
                zip_write.writestr(filename, data)
    except Exception as e:
        raise IOError(f"No se pudo re-escribir el .docx reparado. Error: {e}")

    if debug:
        print(f"    [DEBUG] -> Parcheo completado. {tags_added} tipo(s) de contenido añadidos.")

# --- [ FIN: LÓGICA DE PARCHEO DE MANIFIESTO ] ---


# -------------------------------------------------------------
# ----------------[   PLACEHOLDER SEARCH LOGIC   ]--------------
# -------------------------------------------------------------

def _scan_paragraphs_for_tag(
    paragraphs: List[Paragraph], 
    placeholder_tag: str
) -> Optional[Paragraph]:
    """
    Escanea una lista de párrafos y devuelve el primero que contenga el tag.
    """
    for p in paragraphs:
        if placeholder_tag not in p.text:
            continue  # Búsqueda rápida fallida

        # Búsqueda compleja
        text_buffer = ""
        for run in p.runs:
            text_buffer += run.text
            if placeholder_tag in text_buffer:
                return p  # ¡Encontrado!
            
            if not placeholder_tag.startswith(text_buffer):
                text_buffer = run.text if placeholder_tag.startswith(run.text) else ""

    return None

def find_placeholder_paragraph(
    doc: DocxDocument, 
    placeholder_tag: str
) -> Optional[Paragraph]:
    """
    Encuentra el primer párrafo en todo el documento que contiene el tag.
    """
    
    # 1. Buscar en el cuerpo principal (párrafos)
    found_p = _scan_paragraphs_for_tag(doc.paragraphs, placeholder_tag)
    if found_p:
        return found_p

    # 2. Buscar en tablas del cuerpo principal
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                found_p = _scan_paragraphs_for_tag(cell.paragraphs, placeholder_tag)
                if found_p:
                    return found_p

    # 3. Buscar en encabezados y pies de página
    for section in doc.sections:
        # Encabezado
        found_p = _scan_paragraphs_for_tag(section.header.paragraphs, placeholder_tag)
        if found_p:
            return found_p
        for table in section.header.tables:
            for row in table.rows:
                for cell in row.cells:
                    found_p = _scan_paragraphs_for_tag(cell.paragraphs, placeholder_tag)
                    if found_p:
                        return found_p
        
        # Pie de página
        found_p = _scan_paragraphs_for_tag(section.footer.paragraphs, placeholder_tag)
        if found_p:
            return found_p
        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    found_p = _scan_paragraphs_for_tag(cell.paragraphs, placeholder_tag)
                    if found_p:
                        return found_p
    
    return None

# --------------------------------------> END [ PLACEHOLDER SEARCH LOGIC ... ]


# -------------------------------------------------------------
# ----------------[   CORE EXECUTION LOGIC (v9)   ]-------------
# -------------------------------------------------------------

def _execute_insertion(
    paragraph: Paragraph,
    clean_path: str,
    width_emu: int,
    height_emu: int,
    alignment: str,
    debug: bool = False
) -> None:
    """
    Realiza la inserción quirúrgica en un párrafo (prístino).
    """
    if debug:
        print(f"    [DEBUG] Ejecutando inserción en párrafo...")
        
    paragraph.clear()
    
    align_enum = ALIGNMENT_MAP.get(alignment.upper(), WD_ALIGN_PARAGRAPH.CENTER)
    paragraph.alignment = align_enum
    if debug:
        print(f"    [DEBUG] -> Alineación aplicada: {alignment.upper()}")
        
    run = paragraph.add_run()
    run.add_picture(clean_path, width=width_emu, height=height_emu)
    if debug:
        print(f"    [DEBUG] -> add_picture() llamada con {width_emu}x{height_emu} EMU.")


def generate_document_with_images(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función principal de entrada (Generador de Documentos con Imágenes).
    
    (v9: Usa "vaciado" de párrafo en lugar de "borrado".)
    """
    
    status_report = {
        "success": False,
        "source_path": config.get("source_path"),
        "target_path": None,
        "error": None,
        "details": {
            "images_processed": [],
            "images_failed": []
        }
    }
    
    debug = config.get("debug", False)
    if debug:
        print(f"--- [INICIO TRABAJO DE IMAGEN (DEBUG)] ---")
        print(f"  Archivo Fuente: {config.get('source_path')}")

    if not all([create_safe_temp_copy, get_page_available_space, 
                calculate_final_dimensions, sanitize_image, etree]):
        status_report["error"] = "Módulos del Core (o lxml) no disponibles."
        if debug: print(f"  [ERROR] Módulos del Core (o lxml) no disponibles.")
        return status_report

    source_path = config.get("source_path")
    target_dir = config.get("target_directory")
    target_filename = config.get("target_filename")
    image_map = config.get("image_map", [])
    
    temp_dir = None
    sanitized_extensions_added = set()

    try:
        if not all([source_path, target_dir, target_filename, image_map]):
            raise ValueError("Config incompleta (faltan source, target o image_map).")

        target_path = Path(target_dir) / target_filename
        status_report["target_path"] = str(target_path)
        if debug: print(f"  Archivo Destino: {target_path}")
        
        dir_path = target_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)

        overwrite = config.get("overwrite", False)
        if target_path.exists() and not overwrite:
            raise FileExistsError(f"Destino '{target_path}' ya existe.")

        temp_dir = tempfile.mkdtemp(prefix="docuflow_img_")
        if debug: print(f"  Directorio Temp: {temp_dir}")

        with create_safe_temp_copy(source_path) as temp_doc_path:
            if not temp_doc_path:
                raise FileNotFoundError("Archivo fuente no existe o no es un archivo.")
            
            if debug: print(f"  Copia Segura Creada: {temp_doc_path}")
            doc: DocxDocument = docx.Document(temp_doc_path)
            
            for job in image_map:
                placeholder = job.get("placeholder")
                dirty_path = job.get("image_path")
                policy = job.get("layout_policy", {})
                
                if debug: 
                    print(f"\n  Procesando Job: '{placeholder}'")
                    print(f"    [DEBUG] Imagen 'sucia': {dirty_path}")
                
                try:
                    if not all([placeholder, dirty_path, policy]):
                        raise ValueError(f"Trabajo de imagen incompleto para {placeholder}")
                    
                    # 5a. Sanitizar Imagen
                    clean_path, img_dims = sanitize_image(dirty_path, temp_dir)
                    
                    ext = Path(clean_path).suffix.lstrip('.').lower()
                    sanitized_extensions_added.add(ext)

                    if debug:
                        print(f"    [DEBUG] -> Sanitizada en: {clean_path} (ext: {ext})")
                        print(f"    [DEBUG] -> Dimensiones (px): {img_dims}")
                    
                    # 5b. Encontrar Placeholder
                    p_old = find_placeholder_paragraph(doc, placeholder)
                    if not p_old:
                        raise ValueError(f"Placeholder tag '{placeholder}' no encontrado.")
                    if debug: 
                        print(f"    [DEBUG] -> Placeholder encontrado en párrafo (texto: '{p_old.text[:50]}...')")
                        
                    # 5c. Medir Contexto (Sección)
                    section = doc.sections[0] # Fallback
                    page_dims = get_page_available_space(section)
                    if debug:
                        print(f"    [DEBUG] -> Espacio página (EMU): {page_dims}")
                    
                    # 5d. Calcular Layout
                    width, height = calculate_final_dimensions(img_dims, page_dims, policy)
                    if debug:
                        print(f"    [DEBUG] -> Layout Engine v6: {policy}")
                        print(f"    [DEBUG] -> Dimensiones finales (EMU): ({width}, {height})")
                    
                    # 5e. Lógica de Trasplante (v9: Vaciado)
                    p_new = p_old.insert_paragraph_before()
                    align = policy.get("alignment", "CENTER")
                    _execute_insertion(p_new, clean_path, width, height, align, debug=debug)
                    
                    # VACIAR el párrafo antiguo
                    p_old.clear()
                    if debug:
                        print(f"    [DEBUG] -> Párrafo de placeholder vaciado.")
                    
                    status_report["details"]["images_processed"].append(placeholder)
                    
                except Exception as e:
                    print(f"    [ERROR] Fallo en Job '{placeholder}': {e}")
                    status_report["details"]["images_failed"].append({
                        "placeholder": placeholder,
                        "error": str(e)
                    })
            
            # 6. Actualizar Metadatos
            new_author = config.get("author")
            if new_author:
                doc.core_properties.author = new_author

            # 7. Guardar el nuevo documento
            doc.save(target_path)
            if debug: print(f"\n  [DEBUG] Documento guardado en: {target_path}")
            
            # 8. PASO ESENCIAL: Parchear el manifiesto
            if sanitized_extensions_added:
                _patch_manifest(str(target_path), sanitized_extensions_added, debug=debug)

            # 9. Actualizar el log de estado
            if not status_report["details"]["images_failed"]:
                status_report["success"] = True
            else:
                status_report["success"] = (len(status_report["details"]["images_processed"]) > 0)
                status_report["error"] = "Algunas imágenes fallaron al insertarse."

    except Exception as e:
        status_report["error"] = str(e)
        status_report["success"] = False
        if debug: print(f"  [ERROR CRÍTICO] {e}")
    
    finally:
        # 10. Limpieza Absoluta
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                if debug: print(f"  [DEBUG] Directorio temporal eliminado.")
            except OSError as e:
                print(f"  [ERROR] No se pudo eliminar el directorio temporal: {e}")
    
    if debug: print(f"--- [FIN TRABAJO DE IMAGEN (DEBUG)] ---")
    return status_report

# --------------------------------------> END [ CORE EXECUTION LOGIC (v9) ]