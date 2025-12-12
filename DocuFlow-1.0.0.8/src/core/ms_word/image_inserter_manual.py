#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  image_inserter_manual.py
Created: 2025-11-06
Author: @lewopxd
Last Updated: 2025-12-07

Description:
The "Nuclear Option" for image insertion - v6.
(100% Functional, Error-Proof, with alignment support and robust placeholder search)

v6 CHANGELOG:
- Added `on_missing` policy for image placeholders (analogous to text replacement)
- Supports: "REMOVE_PLACEHOLDER" | "KEEP_PLACEHOLDER" | "FAIL"
- If image_path is None/invalid and on_missing="REMOVE_PLACEHOLDER", the placeholder
  paragraph is removed from the document.

This module replaces python-docx's saving mechanism entirely.
It performs a manual ZIP-to-ZIP transformation with:
- Robust placeholder search (buffer-based, handles stitched runs)
- Full alignment support (LEFT/CENTER/RIGHT/JUSTIFY)
- Search in body, headers, footers, and tables
- Complete layout_policy integration
- Missing image handling with on_missing policy
"""

import os
import tempfile
import shutil
import zipfile
import io
import random
from pathlib import Path
from typing import Dict, Any, Optional, Set, List, Tuple
from lxml import etree

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

# Importar Logger centralizado
try:
    from core.logger import Logger
except ImportError:
    class Logger:
        @staticmethod
        def debug(msg): Logger.debug(f"DEBUG: {msg}")
        @staticmethod
        def info(msg): Logger.debug(f"INFO: {msg}")
        @staticmethod
        def warn(msg): Logger.debug(f"WARN: {msg}")
        @staticmethod
        def error(msg): Logger.error(f"ERROR: {msg}")

try:
    from core.file_helpers.safe_file_handler import create_safe_temp_copy
    from core.ms_word.layout_engine import get_page_available_space, calculate_final_dimensions
    from core.image_helpers.image_sanitizer import sanitize_image
    from core.image_helpers.auto_rotate_policy import resolve_transform_policy
    import docx
    from docx.document import Document as DocxDocument
except ImportError as e:
    Logger.error(f"(ImageInserterManual): No se pudieron importar módulos del Core. Error: {e}")
    sys.exit(1)

# --- [ INICIO: DEFINICIONES XML Y NAMESPACES ] ---

XML_NS_MAP = {
    'ct': "http://schemas.openxmlformats.org/package/2006/content-types",
    'rel': "http://schemas.openxmlformats.org/package/2006/relationships",
    'w': "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    'a': "http://schemas.openxmlformats.org/drawingml/2006/main",
    'pic': "http://schemas.openxmlformats.org/drawingml/2006/picture",
    'r': "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    'wp': "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
}

MIME_TYPES = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "gif": "image/gif", "bmp": "image/bmp", "tif": "image/tiff", "tiff": "image/tiff"
}

# Mapeo de alineación de texto a valores XML
ALIGNMENT_XML_MAP = {
    "LEFT": "left",
    "CENTER": "center",
    "RIGHT": "right",
    "JUSTIFY": "both"
}

# Template XML con soporte de alineación
DRAWING_XML_TEMPLATE = """
<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:jc w:val="{alignment}"/>
  </w:pPr>
  <w:r>
    <w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
        <wp:extent cx="{width_emu}" cy="{height_emu}"/>
        <wp:effectExtent l="0" t="0" r="0" b="0"/>
        <wp:docPr id="{doc_id}" name="{name}"/>
        <wp:cNvGraphicFramePr>
          <a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>
        </wp:cNvGraphicFramePr>
        <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:nvPicPr>
                <pic:cNvPr id="{pic_id}" name="{name}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{rId}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
                <a:stretch>
                  <a:fillRect/>
                </a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm>
                  <a:off x="0" y="0"/>
                  <a:ext cx="{width_emu}" cy="{height_emu}"/>
                </a:xfrm>
                <a:prstGeom prst="rect">
                  <a:avLst/>
                </a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>
"""

# --- [ FIN: DEFINICIONES XML ] ---


# --- [ INICIO: HELPERS QUIRÚRGICOS ] ---

def _get_next_rId(rels_root: etree._Element) -> Tuple[int, str]:
    """Encuentra el rId numérico más alto y devuelve el siguiente."""
    max_id = 0
    ids = rels_root.xpath("//rel:Relationship", namespaces=XML_NS_MAP)
    for rel in ids:
        rId_str = rel.get("Id")
        if rId_str and rId_str.startswith("rId"):
            try:
                num = int(rId_str[3:])
                if num > max_id:
                    max_id = num
            except ValueError:
                continue
    next_id_num = max_id + 1
    return next_id_num, f"rId{next_id_num}"

def _add_manifest_content_type(types_root: etree._Element, ext: str, debug: bool = False):
    """Parchea el XML de [Content_Types] en memoria."""
    ext = ext.lower()
    if ext not in MIME_TYPES:
        return
    
    xpath_query = f'.//ct:Default[@Extension="{ext}"]'
    found = types_root.xpath(xpath_query, namespaces=XML_NS_MAP)
    
    if not found:
        if debug:
            Logger.debug(f"    [DEBUG] MANIFEST: Añadiendo ContentType para: {ext}")
        
        tag_name = "{" + XML_NS_MAP['ct'] + "}Default"
        etree.SubElement(
            types_root,
            tag_name,
            Extension=ext,
            ContentType=MIME_TYPES[ext]
        )

def _add_manifest_relationship(rels_root: etree._Element, target: str, debug: bool = False) -> str:
    """Añade una nueva relación de imagen a document.xml.rels y devuelve el nuevo rId."""
    next_id_num, next_rId = _get_next_rId(rels_root)
    if debug:
        Logger.debug(f"    [DEBUG] RELS: Añadiendo {target} como {next_rId}")
    
    tag_name = "{" + XML_NS_MAP['rel'] + "}Relationship"
    etree.SubElement(
        rels_root,
        tag_name,
        Id=next_rId,
        Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        Target=target
    )
    return next_rId

def _reconstruct_text_with_buffer(text_nodes: List[etree._Element]) -> Tuple[str, List[Tuple[etree._Element, int, int]]]:
    """
    Reconstruye el texto completo de un conjunto de nodos <w:t> y mapea
    cada nodo a su rango de caracteres en el texto completo.
    
    Returns:
        (texto_completo, [(nodo, start_idx, end_idx), ...])
    """
    full_text = ""
    node_map = []
    
    for t_node in text_nodes:
        text_content = t_node.text or ""
        start_idx = len(full_text)
        end_idx = start_idx + len(text_content)
        node_map.append((t_node, start_idx, end_idx))
        full_text += text_content
    
    return full_text, node_map

def _find_and_replace_placeholder_p_robust(
    root: etree._Element, 
    placeholder_text: str, 
    drawing_xml: str, 
    debug: bool = False
) -> bool:
    """
    Búsqueda ROBUSTA de placeholder con manejo de stitches (buffer-based).
    Busca en TODO el árbol XML (body, headers, footers, tablas).
    """
    all_paragraphs = root.xpath(".//w:p", namespaces=XML_NS_MAP)
    
    for p in all_paragraphs:
        text_nodes = p.xpath(".//w:t", namespaces=XML_NS_MAP)
        
        if not text_nodes:
            continue
        
        full_text, node_map = _reconstruct_text_with_buffer(text_nodes)
        
        if placeholder_text not in full_text:
            continue
        
        # ¡Placeholder encontrado!
        if debug:
            Logger.debug(f"    [DEBUG] DOC_XML: Placeholder '{placeholder_text}' encontrado en párrafo.")
            Logger.debug(f"    [DEBUG]   Texto reconstruido: '{full_text[:80]}...'")
        
        # Encontrar índices del placeholder
        start_idx = full_text.find(placeholder_text)
        end_idx = start_idx + len(placeholder_text)
        
        # Determinar qué nodos <w:t> deben modificarse
        nodes_to_clear = []
        first_node = None
        last_node = None
        text_before = ""
        text_after = ""
        
        for t_node, node_start, node_end in node_map:
            # ¿Este nodo contiene el inicio del placeholder?
            if node_start <= start_idx < node_end:
                first_node = t_node
                text_before = (t_node.text or "")[:start_idx - node_start]
            
            # ¿Este nodo está completamente dentro del placeholder?
            if start_idx <= node_start and node_end <= end_idx:
                nodes_to_clear.append(t_node)
            
            # ¿Este nodo contiene el final del placeholder?
            if node_start < end_idx <= node_end:
                last_node = t_node
                text_after = (t_node.text or "")[end_idx - node_start:]
        
        # Limpiar todos los nodos afectados
        for node in nodes_to_clear:
            node.text = ""
        
        # Caso especial: placeholder en un solo nodo
        if first_node is not None and first_node == last_node:
            first_node.text = text_before + text_after
        else:
            if first_node is not None:
                first_node.text = text_before
            if last_node is not None and last_node != first_node:
                last_node.text = text_after
        
        # Reemplazar el <w:p> completo con el drawing
        parent_of_p = p.getparent()
        if parent_of_p is None:
            if debug:
                Logger.debug(f"    [DEBUG] DOC_XML: No se pudo encontrar el padre del párrafo.")
            return False
        
        parser = etree.XMLParser(recover=True)
        drawing_element = etree.fromstring(drawing_xml, parser)
        parent_of_p.replace(p, drawing_element)
        
        if debug:
            Logger.debug(f"    [DEBUG] DOC_XML: Párrafo placeholder reemplazado por <w:drawing>.")
        
        return True
    
    if debug:
        Logger.debug(f"    [DEBUG] DOC_XML: No se encontró el párrafo con el placeholder '{placeholder_text}'")
    
    return False


# --- [ INICIO: NUEVA FUNCIÓN v6 - REMOVER PLACEHOLDER ] ---

def _remove_placeholder_paragraph(
    root: etree._Element, 
    placeholder_text: str, 
    debug: bool = False
) -> bool:
    """
    NUEVA FUNCIÓN v6: Busca y ELIMINA completamente el párrafo que contiene el placeholder.
    Usado cuando on_missing="REMOVE_PLACEHOLDER".
    
    Returns:
        True si encontró y eliminó el placeholder, False si no lo encontró.
    """
    all_paragraphs = root.xpath(".//w:p", namespaces=XML_NS_MAP)
    
    for p in all_paragraphs:
        text_nodes = p.xpath(".//w:t", namespaces=XML_NS_MAP)
        
        if not text_nodes:
            continue
        
        full_text, _ = _reconstruct_text_with_buffer(text_nodes)
        
        if placeholder_text not in full_text:
            continue
        
        # ¡Placeholder encontrado! - ELIMINAR el párrafo completo
        if debug:
            Logger.debug(f"    [DEBUG] REMOVE: Placeholder '{placeholder_text}' encontrado - ELIMINANDO párrafo completo.")
        
        parent_of_p = p.getparent()
        if parent_of_p is None:
            if debug:
                Logger.debug(f"    [DEBUG] REMOVE: No se pudo encontrar el padre del párrafo.")
            return False
        
        # Eliminar el párrafo del documento
        parent_of_p.remove(p)
        
        if debug:
            Logger.debug(f"    [DEBUG] REMOVE: Párrafo con placeholder '{placeholder_text}' eliminado exitosamente.")
        
        return True
    
    if debug:
        Logger.debug(f"    [DEBUG] REMOVE: No se encontró el párrafo con el placeholder '{placeholder_text}'")
    
    return False

# --- [ FIN: NUEVA FUNCIÓN v6 - REMOVER PLACEHOLDER ] ---


def _process_xml_part(
    zip_read: zipfile.ZipFile,
    part_name: str,
    placeholder_to_data: Dict[str, Tuple[str, str, int, int, str]],
    placeholders_to_remove: Set[str],  # ← NUEVO v6: Set de placeholders a eliminar
    doc_id_counter: int,
    pic_id_counter: int,
    placeholder_to_rId: Dict[str, str],
    failed_list: List[Dict[str, str]],
    processed_list: List[str],
    debug: bool = False
) -> Tuple[bytes, int, int]:
    """
    Procesa una parte XML (document.xml, header.xml, footer.xml) y reemplaza/elimina placeholders.
    
    v6 CAMBIO: Ahora acepta `placeholders_to_remove` para eliminar placeholders sin imagen.
    
    Returns:
        (xml_bytes_modificado, nuevo_doc_id_counter, nuevo_pic_id_counter)
    """
    if part_name not in zip_read.namelist():
        return None, doc_id_counter, pic_id_counter
    
    parser = etree.XMLParser(recover=True)
    xml_bytes = zip_read.read(part_name)
    xml_root = etree.fromstring(xml_bytes, parser)
    
    modified = False
    
    # --- PASO 1: REEMPLAZAR placeholders con imágenes ---
    for placeholder, (clean_path, _, width, height, alignment) in placeholder_to_data.items():
        # Saltar si ya falló en otro documento
        if placeholder in [f["placeholder"] for f in failed_list]:
            continue
        
        # Saltar si ya fue procesado
        if placeholder in processed_list:
            continue
        
        rId = placeholder_to_rId[placeholder]
        img_name = Path(clean_path).name
        alignment_xml = ALIGNMENT_XML_MAP.get(alignment.upper(), "center")
        
        drawing_xml = DRAWING_XML_TEMPLATE.format(
            rId=rId,
            width_emu=width,
            height_emu=height,
            pic_id=pic_id_counter,
            doc_id=doc_id_counter,
            name=img_name,
            alignment=alignment_xml
        )
        
        success = _find_and_replace_placeholder_p_robust(xml_root, placeholder, drawing_xml, debug)
        
        if success:
            processed_list.append(placeholder)
            pic_id_counter += 1
            doc_id_counter += 1
            modified = True
            if debug:
                Logger.info(f"    [DEBUG] Placeholder '{placeholder}' procesado en {part_name}")
    
    # --- PASO 2: ELIMINAR placeholders sin imagen (on_missing="REMOVE_PLACEHOLDER") ---
    for placeholder in placeholders_to_remove:
        if placeholder in processed_list:
            continue  # Ya fue procesado con imagen
        
        success = _remove_placeholder_paragraph(xml_root, placeholder, debug)
        
        if success:
            processed_list.append(placeholder)
            modified = True
            if debug:
                Logger.debug(f"    [DEBUG] 🗑️  Placeholder '{placeholder}' ELIMINADO en {part_name}")
    
    if modified:
        return etree.tostring(xml_root, encoding="UTF-8", xml_declaration=True), doc_id_counter, pic_id_counter
    else:
        return xml_bytes, doc_id_counter, pic_id_counter

# --- [ FIN: HELPERS QUIRÚRGICOS ] ---


# -------------------------------------------------------------
# ----------------[   LA FUNCIÓN MONOLÍTICA   ]-----------------
# -------------------------------------------------------------

def generate_document_with_images_manual(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de inserción manual (Opción Nuclear) - v6.
    100% funcional, a prueba de errores, con soporte completo de layout_policy.
    
    v6 NUEVA CARACTERÍSTICA:
    Cada job en image_map puede tener un parámetro `on_missing`:
    
    job = {
        "placeholder": "$IMG{{...}}",
        "image_path": "/path/to/image.png",  # Puede ser None
        "layout_policy": {...},
        "on_missing": "REMOVE_PLACEHOLDER" | "KEEP_PLACEHOLDER" | "FAIL"  # ← NUEVO v6
    }
    
    - "REMOVE_PLACEHOLDER": Elimina el párrafo placeholder del documento
    - "KEEP_PLACEHOLDER": Deja el placeholder visible en el documento (default)
    - "FAIL": Lanza excepción y detiene el proceso
    """
    status_report = {
        "success": False,
        "source_path": config.get("source_path"),
        "target_path": None,
        "error": None,
        "details": {"images_processed": [], "images_failed": [], "images_removed": []}  # ← NUEVO v6: images_removed
    }
    
    debug = config.get("debug", False)
    if debug: Logger.debug(f"--- [INICIO TRABAJO MANUAL DE IMAGEN v6 (DEBUG)] ---")

    source_path = config.get("source_path")
    target_dir = config.get("target_directory")
    target_filename = config.get("target_filename")
    image_map = config.get("image_map", [])
    
    temp_dir = None
    
    try:
        if not all([source_path, target_dir, target_filename]):
            raise ValueError("Config incompleta (falta source_path, target_directory o target_filename).")

        target_path = Path(target_dir) / target_filename
        status_report["target_path"] = str(target_path)
        dir_path = target_path.parent
        dir_path.mkdir(parents=True, exist_ok=True)
        
        overwrite = config.get("overwrite", False)
        if target_path.exists() and not overwrite:
            raise FileExistsError(f"Destino '{target_path}' ya existe.")

        temp_dir = tempfile.mkdtemp(prefix="docuflow_img_")
        if debug: Logger.debug(f"  Directorio Temp: {temp_dir}")
        
        # --- Pre-procesamiento de Imágenes ---
        placeholder_to_data = {}  # tag -> (clean_path, ext, width, height, alignment)
        placeholders_to_remove = set()  # ← NUEVO v6: Placeholders a eliminar
        
        with create_safe_temp_copy(source_path) as temp_doc_path:
            if not temp_doc_path:
                raise FileNotFoundError("Archivo fuente no existe o no es un archivo.")
            
            doc_for_reading = docx.Document(temp_doc_path)
            section = doc_for_reading.sections[0]
            page_dims = get_page_available_space(section)
            if debug: Logger.debug(f"  [DEBUG] Espacio página medido (EMU): {page_dims}")
            
            for job in image_map:
                placeholder = job.get("placeholder")
                dirty_path = job.get("image_path")
                policy = job.get("layout_policy", {})
                on_missing = job.get("on_missing", "KEEP_PLACEHOLDER")  # ← NUEVO v6: Default policy
                
                # --- NUEVA LÓGICA v6: Validar image_path ---
                if not dirty_path or not os.path.exists(dirty_path):
                    # Imagen faltante o path inválido
                    
                    if on_missing == "FAIL":
                        # Política FAIL: Detener todo el proceso
                        raise FileNotFoundError(
                            f"Imagen crítica no encontrada para placeholder '{placeholder}': {dirty_path}"
                        )
                    
                    elif on_missing == "REMOVE_PLACEHOLDER":
                        # Política REMOVE: Marcar para eliminación
                        placeholders_to_remove.add(placeholder)
                        status_report["details"]["images_removed"].append(placeholder)
                        if debug:
                            Logger.debug(f"  [DEBUG] Imagen no encontrada '{placeholder}' - Marcado para ELIMINACIÓN")
                        continue  # No procesar imagen
                    
                    elif on_missing == "KEEP_PLACEHOLDER":
                        # Política KEEP: Dejar placeholder en el documento
                        status_report["details"]["images_failed"].append({
                            "placeholder": placeholder, 
                            "error": f"Imagen no encontrada (KEEP_PLACEHOLDER): {dirty_path}"
                        })
                        if debug:
                            Logger.debug(f"  [DEBUG] Imagen no encontrada '{placeholder}' - MANTENIENDO placeholder")
                        continue  # No procesar imagen
                    
                    else:
                        # Política desconocida: Usar KEEP como fallback
                        if debug:
                            Logger.debug(f"  [DEBUG] on_missing desconocido '{on_missing}' - usando KEEP_PLACEHOLDER")
                        status_report["details"]["images_failed"].append({
                            "placeholder": placeholder, 
                            "error": f"Imagen no encontrada: {dirty_path}"
                        })
                        continue
                
                # --- LÓGICA ORIGINAL: Imagen existe, procesarla ---
                try:
                    # Primero, abrir la imagen para obtener dimensiones originales
                    from PIL import Image
                    with Image.open(dirty_path) as temp_img:
                        original_dims = temp_img.size
                    
                    # Resolver la política de transformación
                    transform_policy = resolve_transform_policy(original_dims, page_dims, policy)
                    
                    if debug:
                        Logger.debug(f"  [DEBUG] Transform policy para '{placeholder}':")
                        Logger.debug(f"    Rotate: {transform_policy.get('rotate')}°")
                        Logger.debug(f"    Flip H/V: {transform_policy.get('flip_horizontal')}/{transform_policy.get('flip_vertical')}")
                        Logger.debug(f"    Turn-to-fit applied: {transform_policy.get('turn_to_fit_applied')}")
                        if transform_policy.get('fit_improvement'):
                            Logger.debug(f"    Fit improvement: {transform_policy['fit_improvement']:.1f}%")
                    
                    # Sanitizar CON transformaciones
                    clean_path, img_dims = sanitize_image(dirty_path, temp_dir, transform_policy)
                    
                    ext = Path(clean_path).suffix.lstrip('.').lower()
                    width, height = calculate_final_dimensions(img_dims, page_dims, policy)
                    alignment = policy.get("alignment", "CENTER")
                    placeholder_to_data[placeholder] = (clean_path, ext, width, height, alignment)
                    if debug:
                        Logger.debug(f"  [DEBUG] Job '{placeholder}' preparado: {width}x{height} EMU, align={alignment}")
                except Exception as e:
                    status_report["details"]["images_failed"].append({
                        "placeholder": placeholder, "error": f"Fallo en Sanitizar/Layout: {e}"
                    })

        # --- Transformación ZIP-a-ZIP ---
        if debug: Logger.debug(f"  [DEBUG] Iniciando transformación ZIP-a-ZIP...")
        
        doc_id_counter = random.randint(1000, 5000)
        pic_id_counter = random.randint(5000, 9999)

        zip_buffer = io.BytesIO()
        parser = etree.XMLParser(recover=True)

        with zipfile.ZipFile(source_path, 'r') as zip_read, \
             zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zip_write:

            # 1. Procesar el manifiesto de tipos
            types_xml_bytes = zip_read.read("[Content_Types].xml")
            types_root = etree.fromstring(types_xml_bytes, parser)
            for _, ext, _, _, _ in placeholder_to_data.values():
                _add_manifest_content_type(types_root, ext, debug)
            zip_write.writestr("[Content_Types].xml", 
                             etree.tostring(types_root, encoding="UTF-8", xml_declaration=True))
            
            # 2. Procesar el manifiesto de relaciones
            rels_xml_bytes = zip_read.read("word/_rels/document.xml.rels")
            rels_root = etree.fromstring(rels_xml_bytes, parser)
            
            placeholder_to_rId = {}
            for placeholder, (clean_path, _, _, _, _) in placeholder_to_data.items():
                img_filename = Path(clean_path).name
                media_target_path = f"media/{img_filename}"
                
                zip_write.write(clean_path, f"word/{media_target_path}")
                
                rId = _add_manifest_relationship(rels_root, media_target_path, debug)
                placeholder_to_rId[placeholder] = rId
            
            zip_write.writestr("word/_rels/document.xml.rels", 
                             etree.tostring(rels_root, encoding="UTF-8", xml_declaration=True))

            # 3. Procesar TODOS los documentos XML (body, headers, footers)
            processed_placeholders = []
            
            # 3a. Documento principal
            doc_xml, doc_id_counter, pic_id_counter = _process_xml_part(
                zip_read, "word/document.xml",
                placeholder_to_data, placeholders_to_remove,  # ← NUEVO v6: Pasar placeholders_to_remove
                doc_id_counter, pic_id_counter,
                placeholder_to_rId, status_report["details"]["images_failed"],
                processed_placeholders, debug
            )
            if doc_xml:
                zip_write.writestr("word/document.xml", doc_xml)
            
            # 3b. Headers y Footers
            for item in zip_read.namelist():
                if item.startswith("word/header") or item.startswith("word/footer"):
                    if item.endswith(".xml"):
                        part_xml, doc_id_counter, pic_id_counter = _process_xml_part(
                            zip_read, item,
                            placeholder_to_data, placeholders_to_remove,  # ← NUEVO v6: Pasar placeholders_to_remove
                            doc_id_counter, pic_id_counter,
                            placeholder_to_rId, status_report["details"]["images_failed"],
                            processed_placeholders, debug
                        )
                        if part_xml:
                            zip_write.writestr(item, part_xml)
            
            # Actualizar reporte
            for placeholder in placeholder_to_data.keys():
                if placeholder in processed_placeholders:
                    status_report["details"]["images_processed"].append(placeholder)
                elif placeholder not in [f["placeholder"] for f in status_report["details"]["images_failed"]]:
                    status_report["details"]["images_failed"].append({
                        "placeholder": placeholder,
                        "error": "No se pudo encontrar el párrafo placeholder en ningún XML"
                    })
            
            # Verificar placeholders eliminados
            for placeholder in placeholders_to_remove:
                if placeholder not in processed_placeholders:
                    if debug:
                        Logger.warn(f"  [DEBUG]  Placeholder '{placeholder}' marcado para eliminación pero no encontrado en XML")
            
            # 4. Copiar todos los demás archivos
            written_files = {"[Content_Types].xml", "word/_rels/document.xml.rels", "word/document.xml"}
            written_files.update({item for item in zip_read.namelist() 
                                if item.startswith("word/header") or item.startswith("word/footer")})
            
            for item in zip_read.infolist():
                if item.filename not in written_files and not item.filename.startswith("word/media/"):
                    zip_write.writestr(item, zip_read.read(item.filename))
            
            # Copiar media original que no fue reemplazada
            source_media = {f.filename for f in zip_read.infolist() if f.filename.startswith("word/media/")}
            written_media = {f"word/media/{Path(v[0]).name}" for v in placeholder_to_data.values()}
            for media_file in source_media - written_media:
                zip_write.writestr(media_file, zip_read.read(media_file))

        # 5. Guardar el ZIP de memoria en el disco
        with open(target_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        if debug: Logger.debug(f"  [DEBUG] Transformación ZIP-a-ZIP completada. Archivo guardado en: {target_path}")
        
        # Determinar éxito
        if not status_report["details"]["images_failed"]:
            status_report["success"] = True
        else:
            status_report["success"] = (len(status_report["details"]["images_processed"]) > 0)
            status_report["error"] = "Algunas imágenes fallaron al insertarse."
            
    except Exception as e:
        status_report["error"] = str(e)
        status_report["success"] = False
        if debug: 
            import traceback
            Logger.error(f"  [ERROR CRÍTICO] {e}")
            traceback.print_exc()
    
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                if debug: Logger.debug(f"  [DEBUG] Directorio temporal eliminado.")
            except OSError as e:
                Logger.error(f"  [ERROR] No se pudo eliminar el directorio temporal: {e}")
    
    if debug: 
        Logger.debug(f"  [RESUMEN v6]")
        Logger.debug(f"    Imágenes procesadas: {len(status_report['details']['images_processed'])}")
        Logger.debug(f"    Imágenes fallidas: {len(status_report['details']['images_failed'])}")
        Logger.debug(f"    Placeholders eliminados: {len(status_report['details']['images_removed'])}")
        Logger.debug(f"--- [FIN TRABAJO MANUAL DE IMAGEN v6 (DEBUG)] ---")
    
    return status_report