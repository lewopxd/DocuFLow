#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  pdf_converter.py
Created: 2025-11-06
Author: @lewopxd

Description:
Un módulo especializado para convertir páginas de PDF en imágenes PNG
de alta fidelidad. Utiliza PyMuPDF (fitz) para un renderizado rápido.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any, Optional, Set, List, Tuple

try:
    # PyMuPDF es la biblioteca, fitz es el nombre de importación
    import fitz  
except ImportError:
    print("="*80)
    Logger.error("ERROR CRÍTICO (PDF_Converter): La biblioteca 'PyMuPDF' no está instalada.")
    Logger.debug("   Por favor, ejecute: pip install PyMuPDF")
    print("="*80)
    fitz = None

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


# -------------------------------------------------------------
# -------------------[   HELPER LÓGICO   ]---------------------
# -------------------------------------------------------------

def _parse_page_ranges(ranges_str: Optional[str], max_pages: int) -> List[int]:
    """
    Parsea un string de rangos (ej. "1, 3-5, 8") y devuelve una lista
    de índices de página (base-cero).
    """
    if not ranges_str:
        # Si no se especifica, renderizar todas las páginas
        return list(range(max_pages))

    indices_set: Set[int] = set()
    try:
        parts = ranges_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Es un rango (ej. "3-5")
                start, end = part.split('-')
                start_idx = int(start.strip()) - 1  # Convertir a base-cero
                end_idx = int(end.strip()) - 1      # Convertir a base-cero
                
                if start_idx < 0: start_idx = 0
                if end_idx >= max_pages: end_idx = max_pages - 1
                
                for i in range(start_idx, end_idx + 1):
                    indices_set.add(i)
            else:
                # Es un solo número (ej. "1")
                idx = int(part.strip()) - 1 # Convertir a base-cero
                if 0 <= idx < max_pages:
                    indices_set.add(idx)
        
        return sorted(list(indices_set))
        
    except Exception as e:
        Logger.error(f"⚠️ Error parseando rango de página '{ranges_str}': {e}. Usando todas las páginas.")
        return list(range(max_pages))


# -------------------------------------------------------------
# -------------------[   FUNCIÓN PRINCIPAL   ]-----------------
# -------------------------------------------------------------

def convert_pdf_to_images(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte las páginas especificadas de un PDF a imágenes PNG en un
    directorio temporal.

    Args:
        config (Dict):
            - "pdf_path" (str): Ruta al archivo PDF fuente.
            - "temp_dir" (str): Ruta al directorio temporal base.
            - "policy" (Dict):
                - "page_ranges" (str, opcional): Ej. "1, 3-5, 8". Si es None, todas.
                - "dpi" (int, opcional): Calidad de la imagen. Default: 150.
    
    Returns:
        Dict: Status report
            - "success" (bool)
            - "error" (str, opcional)
            - "image_output_dir" (str): Carpeta donde se guardaron los PNGs.
            - "generated_images" (List[Dict]):
                - "page_number" (int): El número de página (base-uno).
                - "path" (str): Ruta completa al PNG generado.
    """
    
    status_report = {
        "success": False,
        "error": None,
        "image_output_dir": None,
        "generated_images": []
    }

    if not fitz:
        status_report["error"] = "La biblioteca 'PyMuPDF' no está instalada o no se pudo importar."
        return status_report

    pdf_path = config.get("pdf_path")
    temp_dir = config.get("temp_dir")
    policy = config.get("policy", {})

    if not all([pdf_path, temp_dir]):
        status_report["error"] = "Configuración incompleta (faltan 'pdf_path' o 'temp_dir')."
        return status_report

    if not os.path.exists(pdf_path):
        status_report["error"] = f"Archivo PDF no encontrado: {pdf_path}"
        return status_report
        
    # Crear un subdirectorio único dentro de temp_dir para estas imágenes
    pdf_name = Path(pdf_path).stem
    job_id = uuid4().hex[:8]
    image_output_dir = Path(temp_dir) / f"pdf_imgs_{pdf_name}_{job_id}"
    
    doc = None
    
    try:
        image_output_dir.mkdir(parents=True, exist_ok=True)
        status_report["image_output_dir"] = str(image_output_dir)

        doc = fitz.open(pdf_path)
        
        # 1. Resolver qué páginas renderizar
        page_indices = _parse_page_ranges(
            policy.get("page_ranges"), 
            doc.page_count
        )
        
        dpi = policy.get("dpi", 150)
        
        if not page_indices:
            raise ValueError("No se encontraron páginas válidas para renderizar.")

        # 2. Renderizar cada página
        for page_index in page_indices:
            page_num_human = page_index + 1
            
            page = doc.load_page(page_index)
            
            # Definir la matriz de transformación para el DPI
            matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            
            # Renderizar a pixmap
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Guardar la imagen
            img_filename = f"{pdf_name}_pg_{page_num_human}.png"
            img_path = str(image_output_dir / img_filename)
            
            pix.save(img_path)
            
            status_report["generated_images"].append({
                "page_number": page_num_human,
                "path": img_path
            })

        status_report["success"] = True

    except Exception as e:
        status_report["error"] = f"Fallo al convertir PDF: {e}"
        status_report["success"] = False
        # Limpiar directorio temporal si fallamos
        if image_output_dir.exists():
            shutil.rmtree(image_output_dir)
            status_report["image_output_dir"] = None
            
    finally:
        if doc:
            doc.close()
            
    return status_report