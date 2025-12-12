#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  media_document_assembler.py
Created: 2025-11-06
Author: @lewopxd

Description:
El orquestador principal (Ensamblador) para la generación de documentos.

v4 (FEATURE): Añadida la neutralización del "párrafo fantasma"
             para prevenir páginas en blanco al final.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path 
from typing import Dict, Any, Optional, Set, List, Tuple
from uuid import uuid4
import docx
from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx.shared import Pt  # <-- [NUEVA IMPORTACIÓN]

# --- [ INICIO: AJUSTE DE PYTHONPATH ] ---
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
    # El guardián para leer el archivo de forma segura
    from core.file_helpers.safe_file_handler import create_safe_temp_copy
    
    # El motor de inserción de imágenes (lo tratamos como caja negra)
    from core.ms_word.image_inserter_manual import generate_document_with_images_manual
    
    # El nuevo conversor de PDF
    from core.pdf_helpers.pdf_to_image_converter import convert_pdf_to_images
    
except ImportError as e:
    Logger.error(f"(DocumentAssembler): No se pudieron importar módulos del Core. Error: {e}")
    sys.exit(1)


# -------------------------------------------------------------
# ----------------[   HELPERS DE MANIPULACIÓN   ]---------------
# -------------------------------------------------------------

def _find_and_expand_pdf_placeholder(
    doc: DocxDocument,
    pdf_placeholder: str,
    new_img_placeholders: List[str]
) -> bool:
    """
    Busca un placeholder de PDF y lo reemplaza con nuevos párrafos
    que contienen los nuevos placeholders de imagen, en el orden correcto.
    """
    
    # Lista de todos los párrafos (cuerpo, headers, footers, tablas)
    all_paragraphs: List[Paragraph] = list(doc.paragraphs)
    
    for section in doc.sections:
        for p in section.header.paragraphs:
            all_paragraphs.append(p)
        for t in section.header.tables:
            for r in t.rows:
                for c in r.cells:
                    for p in c.paragraphs:
                        all_paragraphs.append(p)
        
        for p in section.footer.paragraphs:
            all_paragraphs.append(p)
        for t in section.footer.tables:
            for r in t.rows:
                for c in r.cells:
                    for p in c.paragraphs:
                        all_paragraphs.append(p)
    
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    all_paragraphs.append(p)

    anchor_paragraph = None
    
    # 1. Encontrar el párrafo ancla
    for p in all_paragraphs:
        if p.text.strip() == pdf_placeholder:
            anchor_paragraph = p
            break
            
    if not anchor_paragraph:
        return False # No se encontró el placeholder
    
    if not new_img_placeholders:
        # No hay nada que insertar, solo borrar el placeholder
        anchor_paragraph.text = ""
        return True

    # 2. Iterar en REVERSA por la lista de placeholders
    current_anchor = anchor_paragraph
    
    for placeholder_text in reversed(new_img_placeholders):
        new_p = current_anchor.insert_paragraph_before(placeholder_text)
        new_p.paragraph_format.alignment = current_anchor.paragraph_format.alignment
        current_anchor = new_p

    # 3. Limpiar el párrafo ancla original
    anchor_paragraph.text = ""
    while anchor_paragraph.runs:
        r_to_remove = anchor_paragraph.runs[0]
        anchor_paragraph._p.remove(r_to_remove._r)
        
    return True


# --- [ INICIO: NUEVA FUNCIÓN HELPER ] ---
def _neuter_trailing_empty_paragraph(doc: DocxDocument):
    """
    Encuentra el último párrafo del documento y, si está vacío,
    reduce su tamaño y espaciado para evitar que cree una
    página en blanco al final.
    """
    try:
        # doc.paragraphs solo busca en el cuerpo principal, que es
        # donde suele estar este párrafo fantasma.
        if not doc.paragraphs:
            return # No hay párrafos
            
        last_p = doc.paragraphs[-1]
        
        # Es "vacío" si no tiene texto (ignorando espacios)
        # y si no contiene un dibujo (como un <w:drawing>)
        # (Esto es una suposición segura, ya que los dibujos se 
        # insertan *antes* de este párrafo final)
        is_empty = not last_p.text.strip()
        has_drawing = '<w:drawing' in last_p._p.xml
        
        if is_empty and not has_drawing:
            # ¡Es un párrafo fantasma! Neutralizarlo.
            last_p.paragraph_format.space_before = Pt(0)
            last_p.paragraph_format.space_after = Pt(0)
            
            # Asegurarse de que haya al menos un 'run' para setear la fuente
            if not last_p.runs:
                run = last_p.add_run()
            else:
                run = last_p.runs[0]
            
            run.font.size = Pt(1)
            
    except Exception as e:
        # Ser silencioso. Esto es una optimización, no debe
        # detener el proceso si falla.
        Logger.warn(f"Advertencia: Falló al neutralizar párrafo fantasma: {e}")
# --- [ FIN: NUEVA FUNCIÓN HELPER ] ---


# -------------------------------------------------------------
# -------------------[   EL ENSAMBLADOR   ]--------------------
# -------------------------------------------------------------

def assemble_document_with_media(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Punto de entrada principal para generar un documento con
    imágenes y anexos PDF.
    """
    
    debug = config.get("debug", False)
    if debug: Logger.debug(f"--- [INICIO TRABAJO ENSAMBLADOR (DEBUG)] ---")

    source_path = config.get("source_path")
    pdf_map = config.get("pdf_map", [])
    
    main_temp_dir = tempfile.mkdtemp(prefix="docuflow_asm_")
    
    source_for_inserter = source_path
    final_image_map = list(config.get("image_map", []))
    
    pdf_preprocessing_report = {
        "processed": [],
        "failed": []
    }
    
    try:
        # --- [ ETAPA 1: PRE-PROCESAMIENTO DE PDF ] ---
        if pdf_map:
            if debug: Logger.debug(f"  [ASM] Detectados {len(pdf_map)} trabajos PDF. Iniciando pre-procesamiento.")
            
            with create_safe_temp_copy(source_path) as temp_doc_path:
                if not temp_doc_path:
                    raise FileNotFoundError("Fallo al crear copia segura del documento fuente.")
                
                doc = docx.Document(temp_doc_path)
                
                for pdf_job in pdf_map:
                    placeholder = pdf_job.get("placeholder")
                    pdf_file_path = pdf_job.get("pdf_path")
                    layout_policy = pdf_job.get("layout_policy", {})
                    
                    try:
                        # ... (lógica de conversión de PDF)...
                        if not all([placeholder, pdf_file_path, layout_policy]):
                            raise ValueError("Trabajo PDF incompleto (falta placeholder, pdf_path o layout_policy)")
                        
                        if debug: Logger.debug(f"    [ASM] Procesando PDF: '{placeholder}'")
                        
                        pdf_config = {
                            "pdf_path": pdf_file_path,
                            "temp_dir": main_temp_dir,
                            "policy": layout_policy.get("pdf_options", {})
                        }
                        pdf_report = convert_pdf_to_images(pdf_config)
                        
                        if not pdf_report["success"]:
                            raise Exception(f"Fallo en pdf_converter: {pdf_report['error']}")
                        
                        new_img_placeholders = []
                        new_img_jobs = []
                        
                        for img_data in pdf_report["generated_images"]:
                            page_num = img_data["page_number"]
                            img_path = img_data["path"]
                            job_id = uuid4().hex[:8]
                            new_placeholder = f"$IMG{{__PDF_{placeholder.strip('${{}}')}_pg{page_num}_{job_id}}}"
                            new_img_placeholders.append(new_placeholder)
                            new_img_jobs.append({
                                "placeholder": new_placeholder,
                                "image_path": img_path,
                                "layout_policy": layout_policy
                            })

                        success_expand = _find_and_expand_pdf_placeholder(
                            doc,
                            placeholder,
                            new_img_placeholders
                        )
                        
                        if not success_expand:
                            raise Exception(f"No se pudo encontrar el placeholder '{placeholder}' en el documento.")

                        final_image_map.extend(new_img_jobs)
                        pdf_preprocessing_report["processed"].append(placeholder)
                        if debug: Logger.info(f"    [ASM] PDF '{placeholder}' expandido en {len(new_img_jobs)} imágenes.")

                    except Exception as e:
                        pdf_preprocessing_report["failed"].append({"placeholder": placeholder, "error": str(e)})
                        if debug: Logger.error(f"    [ASM] FALLO PDF '{placeholder}': {e}")
                        raise
                
                
                # --- [ INICIO DE MODIFICACIÓN ] ---
                # Justo antes de guardar el documento expandido,
                # aplicar la neutralización si está configurada.
                if config.get("remove_trailing_blank_page", False):
                    if debug: Logger.debug("  [ASM] Aplicando neutralización de página en blanco...")
                    _neuter_trailing_empty_paragraph(doc)
                # --- [ FIN DE MODIFICACIÓN ] ---

                
                # 7. Guardar el documento expandido
                expanded_doc_path = str(Path(main_temp_dir) / "expanded_document.docx")
                doc.save(expanded_doc_path)
                source_for_inserter = expanded_doc_path
                if debug: Logger.debug(f"  [ASM] Pre-procesamiento PDF completado. Documento expandido guardado.")

        # --- [ FIN ETAPA 1 ] ---
        
    except Exception as pdf_error:
        # --- [ FALLBACK DE SEGURIDAD ] ---
        if debug: 
            Logger.error(f"  [ASM] 🔥 ERROR CRÍTICO en pre-procesamiento PDF: {pdf_error}")
            Logger.debug(f"  [ASM] REVIRTIENDO a modo 'solo-imágenes'.")
            
        source_for_inserter = source_path
        final_image_map = list(config.get("image_map", [])) 
        
        fallback_report = {
            "success": False,
            "error": f"Fallo en pre-procesamiento de PDF: {pdf_error}. Se revirtió a inserción de imágenes estándar.",
            "details": {"images_processed": [], "images_failed": [], "pdf_preprocessing": pdf_preprocessing_report}
        }
        
        try:
            inserter_config = config.copy() 
            inserter_config["source_path"] = source_for_inserter
            inserter_config["image_map"] = final_image_map
            
            full_target_path_str = config.get("target_path")
            if not full_target_path_str:
                 raise ValueError("Configuración incompleta: 'target_path' no fue proveído al ensamblador.")
            
            full_target_path_obj = Path(full_target_path_str)
            inserter_config["target_directory"] = str(full_target_path_obj.parent)
            inserter_config["target_filename"] = str(full_target_path_obj.name)
            if "target_path" in inserter_config:
                del inserter_config["target_path"]

            fallback_report = generate_document_with_images_manual(inserter_config)
            fallback_report["error"] = f"Éxito parcial (solo imágenes). Fallo en PDF: {pdf_error}"
            fallback_report["details"]["pdf_preprocessing"] = pdf_preprocessing_report
            
            return fallback_report
            
        except Exception as inserter_error:
            fallback_report["error"] = f"Fallo en PDF ({pdf_error}) Y fallo en inserción de imágenes ({inserter_error})."
            return fallback_report
            

    # --- [ ETAPA 2: INSERCIÓN FINAL ] ---
    final_report = {}
    try:
        if debug:
            Logger.debug(f"  [ASM] Iniciando Etapa 2: Inserción Final.")
            Logger.debug(f"    [ASM] Fuente: {source_for_inserter}")
            Logger.debug(f"    [ASM] Destino: {config.get('target_path')}")
            Logger.debug(f"    [ASM] Total trabajos de imagen: {len(final_image_map)}")
        
        inserter_config = config.copy()
        inserter_config["source_path"] = source_for_inserter
        inserter_config["image_map"] = final_image_map

        full_target_path_str = config.get("target_path")
        if not full_target_path_str:
             raise ValueError("Configuración incompleta: 'target_path' no fue proveído al ensamblador.")
            
        full_target_path_obj = Path(full_target_path_str)
        inserter_config["target_directory"] = str(full_target_path_obj.parent)
        inserter_config["target_filename"] = str(full_target_path_obj.name)
        if "target_path" in inserter_config:
            del inserter_config["target_path"]
        
        final_report = generate_document_with_images_manual(inserter_config)
        
        if "details" in final_report:
            final_report["details"]["pdf_preprocessing"] = pdf_preprocessing_report
        else:
            final_report["details"] = {"pdf_preprocessing": pdf_preprocessing_report}

        if debug: Logger.debug(f"  [ASM] Inserción final completada.")
        
    except Exception as e:
        if debug: Logger.error(f"  [ASM] ERROR CRÍTICO en Etapa 2 (Inserción): {e}")
        final_report = {
            "success": False,
            "error": f"Fallo durante la inserción final de imágenes: {e}",
            "details": {"pdf_preprocessing": pdf_preprocessing_report}
        }
        
    finally:
        if os.path.exists(main_temp_dir):
            try:
                shutil.rmtree(main_temp_dir)
                if debug: Logger.debug(f"  [ASM] Directorio temporal principal eliminado.")
            except OSError as e:
                if debug: Logger.warn(f"  [ASM] No se pudo eliminar el temp dir: {e}")

    if debug: Logger.debug(f"--- [FIN TRABAJO ENSAMBLADOR (DEBUG)] ---")
    
    return final_report