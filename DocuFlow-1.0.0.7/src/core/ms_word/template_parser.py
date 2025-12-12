#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:    template_parser.py
Created: 2025-11-05
Author:  @lewopxd

Description:
Provides functions to safely scan and parse Word (.docx) templates,
extracting metadata and a unique list of placeholders.

v2 (BUGFIX): Corregida la Regex para permitir espacios y símbolos
             dentro de los placeholders.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple
import docx
from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph

# Importar el guardián de seguridad
try:
    from ..file_helpers.safe_file_handler import create_safe_temp_copy
except ImportError as e:
    Logger.error(f"CRITICAL: No se pudo importar 'create_safe_temp_copy' (ImportError: {e}).")
    from contextlib import contextmanager
    @contextmanager
    def create_safe_temp_copy(path):
        Logger.warn("USANDO FALLBACK NO SEGURO DE create_safe_temp_copy")
        if os.path.exists(path): yield path
        else: yield None

# -------------------------------------------------------------
# -------------------[   CORE HELPER LOGIC   ]-----------------
# -------------------------------------------------------------

def _build_regex_map(definitions: List[Dict[str, str]]) -> Dict[str, re.Pattern]:
    """
    Construye un mapa de Expresiones Regulares compiladas a partir de
    las definiciones de placeholders.
    
    Cada regex es simple: (escaped_prefix).+?(escaped_suffix)
    La eliminación de overlaps se maneja en el post-procesamiento.
    """
    regex_map = {}
    for definition in definitions:
        try:
            escaped_prefix = re.escape(definition["prefix"])
            escaped_suffix = re.escape(definition["suffix"])
            pattern_str = f"({escaped_prefix}.+?{escaped_suffix})"
            regex_map[definition["type"]] = re.compile(pattern_str)
        except (re.error, TypeError, KeyError) as e:
            Logger.error(f"⚠️ Error al construir Regex para la definición {definition}: {e}")
    return regex_map


def _eliminate_overlapping_matches(all_matches: List[Tuple[str, str, int, int]]) -> List[Tuple[str, str]]:
    """
    Elimina matches que están contenidos dentro de otros matches.
    
    El match más largo (específico) gana.
    Ejemplo: "$IMG{{NAME}}" gana sobre "{{NAME}}" si este último está contenido.
    
    Optimizado: O(n log n) usando ordenamiento por posición.
    """
    if not all_matches or len(all_matches) == 1:
        return [(m[0], m[1]) for m in all_matches]
    
    # Ordenar por posición de inicio, luego por longitud descendente
    sorted_matches = sorted(all_matches, key=lambda x: (x[2], -(x[3] - x[2])))
    
    kept_matches = []
    max_end = -1  # Máximo end de los matches aceptados hasta ahora
    
    for type_name, match_text, start, end in sorted_matches:
        # Si este match empieza después del último end aceptado, no hay overlap
        if start >= max_end:
            kept_matches.append((type_name, match_text))
            max_end = end
        # Si este match está completamente contenido en uno anterior, ignorarlo
        elif end <= max_end:
            continue
        # Overlap parcial - mantener el más largo (el primero por el ordenamiento)
        else:
            # Este match extiende más allá, lo aceptamos
            kept_matches.append((type_name, match_text))
            max_end = max(max_end, end)
    
    return kept_matches


def _scan_paragraphs(
    paragraphs: List[Paragraph], 
    regex_map: Dict[str, re.Pattern]
) -> Dict[str, Set[str]]:
    """
    Escanea una lista de párrafos y encuentra todos los placeholders.
    
    Usa post-procesamiento para eliminar matches contenidos dentro de otros
    (ej: "{{NAME}}" dentro de "$IMG{{NAME}}" se elimina).
    """
    found_placeholders = {type_name: set() for type_name in regex_map}
    
    for p in paragraphs:
        combined_text = p.text
        if not combined_text:
            continue

        # Paso 1: Obtener TODOS los matches con sus posiciones
        all_matches = []  # (type_name, match_text, start, end)
        
        for type_name, regex_pattern in regex_map.items():
            try:
                for match in regex_pattern.finditer(combined_text):
                    all_matches.append((
                        type_name,
                        match.group(1),
                        match.start(),
                        match.end()
                    ))
            except re.error as e:
                Logger.error(f"Error aplicando Regex en párrafo: {e}")
        
        # Paso 2: Eliminar matches contenidos en otros
        clean_matches = _eliminate_overlapping_matches(all_matches)
        
        # Paso 3: Agregar matches limpios al resultado
        for type_name, match_text in clean_matches:
            found_placeholders[type_name].add(match_text)
                
    return found_placeholders

def _extract_metadata(doc: DocxDocument, source_path: str) -> Dict[str, Any]:
    """Extrae metadatos básicos del documento."""
    
    created_date = None
    if doc.core_properties.created:
        created_date = doc.core_properties.created.isoformat()
        
    modified_date = None
    if doc.core_properties.modified:
        modified_date = doc.core_properties.modified.isoformat()

    metadata = {
        "source_path": source_path,
        "file_size_kb": 0,
        "paragraphs": len(doc.paragraphs),
        "tables": len(doc.tables),
        "sections": len(doc.sections),
        "author": doc.core_properties.author,
        "last_modified_by": doc.core_properties.last_modified_by,
        "created": created_date,
        "modified": modified_date,
        "title": doc.core_properties.title,
        "subject": doc.core_properties.subject,
    }
    
    try:
        size_bytes = os.path.getsize(source_path)
        metadata["file_size_kb"] = round(size_bytes / 1024, 2)
    except OSError:
        pass 
        
    return metadata

# --------------------------------------> END [ CORE HELPER LOGIC ... ]

# -------------------------------------------------------------
# -------------------[   MAIN FUNCTION   ]---------------------
# -------------------------------------------------------------

def get_template_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función principal de entrada (Inspector de Plantillas).
    
    Analiza una plantilla .docx de forma segura, extrae metadatos
    y todos los placeholders únicos que coincidan con las definiciones.

    Args:
        config: Diccionario de configuración.
            - "source_path" (str): Ruta a la plantilla .docx
            - "definitions" (List[dict]): Lista de tipos de placeholders.
              Ej: [{"type": "text", "prefix": "${{", "suffix": "}}"}, ...]

    Returns:
        Un diccionario (JSON) con los metadatos y placeholders.
    """
    
    status_report = {
        "success": False,
        "error": None,
        "metadata": None,
        "placeholders": {},
        "stats": {
            "total_unique_tags": 0,
            "all_tags_found": []
        }
    }
    
    source_path = config.get("source_path")
    definitions = config.get("definitions")

    try:
        if not source_path or not definitions:
            raise ValueError("Configuración incompleta (faltan 'source_path' o 'definitions').")
            
        regex_map = _build_regex_map(definitions)
        if not regex_map:
            raise ValueError("No se pudieron construir patrones Regex a partir de 'definitions'.")

        all_found_tags = set()
        placeholders_by_type = {type_name: set() for type_name in regex_map}
        
        with create_safe_temp_copy(source_path) as temp_path:
            if not temp_path:
                raise FileNotFoundError("Error de validación: El archivo fuente no existe o no es un archivo.")
            
            doc: DocxDocument = docx.Document(temp_path)
            
            status_report["metadata"] = _extract_metadata(doc, source_path)

            # --- Encabezados ---
            for section in doc.sections:
                found_in_header = _scan_paragraphs(section.header.paragraphs, regex_map)
                for type_name, tags_set in found_in_header.items():
                    placeholders_by_type[type_name].update(tags_set)
                
                for table in section.header.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            found_in_cell = _scan_paragraphs(cell.paragraphs, regex_map)
                            for type_name, tags_set in found_in_cell.items():
                                placeholders_by_type[type_name].update(tags_set)

            # --- Cuerpo (Párrafos y Tablas) ---
            found_in_body = _scan_paragraphs(doc.paragraphs, regex_map)
            for type_name, tags_set in found_in_body.items():
                placeholders_by_type[type_name].update(tags_set)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        found_in_cell = _scan_paragraphs(cell.paragraphs, regex_map)
                        for type_name, tags_set in found_in_cell.items():
                            placeholders_by_type[type_name].update(tags_set)
            
            # --- Pies de página ---
            for section in doc.sections:
                found_in_footer = _scan_paragraphs(section.footer.paragraphs, regex_map)
                for type_name, tags_set in found_in_footer.items():
                    placeholders_by_type[type_name].update(tags_set)

                for table in section.footer.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            found_in_cell = _scan_paragraphs(cell.paragraphs, regex_map)
                            for type_name, tags_set in found_in_cell.items():
                                placeholders_by_type[type_name].update(tags_set)
            
            status_report["success"] = True
            
            for type_name, tags_set in placeholders_by_type.items():
                sorted_tags = sorted(list(tags_set))
                status_report["placeholders"][type_name] = sorted_tags
                all_found_tags.update(sorted_tags)
                
            status_report["stats"]["all_tags_found"] = sorted(list(all_found_tags))
            status_report["stats"]["total_unique_tags"] = len(all_found_tags)

    except Exception as e:
        status_report["error"] = str(e)
        status_report["success"] = False

    return status_report

# --------------------------------------> END [ MAIN FUNCTION ... ]


# -------------------------------------------------------------
# -------------------[   UI API FUNCTION   ]-------------------
# -------------------------------------------------------------

def _normalize_for_matching(text: str) -> str:
    """
    Normaliza texto para comparación fuzzy:
    - Lowercase
    - Elimina tildes/acentos
    - Elimina espacios, guiones, guiones bajos
    """
    import unicodedata
    
    # Lowercase
    text = text.lower()
    
    # Remove accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Remove spaces, underscores, hyphens
    text = re.sub(r'[\s_-]+', '', text)
    
    return text.strip()


def _extract_placeholder_name(raw_placeholder: str, prefix: str, suffix: str) -> str:
    """
    Extrae el nombre interno de un placeholder quitando prefijo y sufijo.
    Ej: "${NOMBRE}" -> "NOMBRE"
    """
    name = raw_placeholder
    if name.startswith(prefix):
        name = name[len(prefix):]
    if name.endswith(suffix):
        name = name[:-len(suffix)]
    return name.strip()


def get_template_placeholders(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    API para la UI - Extrae placeholders de una plantilla Word.
    Usa get_template_info internamente y formatea la respuesta para la UI.
    
    Args:
        config: Diccionario con:
            - "source_path" (str): Ruta a la plantilla .docx
            - "definitions" (List[dict], opcional): Definiciones de placeholders.
              Default: 
                - {"type": "text", "prefix": "{{", "suffix": "}}"}
                - {"type": "image", "prefix": "$IMG{{", "suffix": "}}"}

    Returns:
        {
            "success": True/False,
            "error": str or None,
            "file_path": str,
            "file_name": str,
            "metadata": { ... },  # File metadata (size, author, dates, etc.)
            "placeholders": [
                {
                    "raw": "{{NOMBRE}}",
                    "name": "NOMBRE",
                    "normalized": "nombre",
                    "type": "text"
                },
                ...
            ],
            "total_count": int
        }
    """
    
    result = {
        "success": False,
        "error": None,
        "file_path": "",
        "file_name": "",
        "metadata": None,
        "placeholders": [],
        "total_count": 0
    }
    
    source_path = config.get("source_path")
    
    # Default definitions: {{TEXT}} for text, $IMG{{IMAGE}} for images
    definitions = config.get("definitions", [
        {"type": "text", "prefix": "{{", "suffix": "}}"},
        {"type": "image", "prefix": "$IMG{{", "suffix": "}}"}
    ])
    
    try:
        if not source_path:
            raise ValueError("Missing 'source_path' in config")
        
        result["file_path"] = source_path
        result["file_name"] = os.path.basename(source_path)
        
        # Use existing get_template_info to extract placeholders and metadata
        template_info = get_template_info({
            "source_path": source_path,
            "definitions": definitions
        })
        
        if not template_info.get("success"):
            raise Exception(template_info.get("error", "Unknown error parsing template"))
        
        # Include metadata from template_info
        result["metadata"] = template_info.get("metadata")
        
        # Build placeholder list with normalized names
        placeholders_list = []
        
        for type_name, raw_tags in template_info.get("placeholders", {}).items():
            # Find the definition for this type to get prefix/suffix
            definition = next((d for d in definitions if d.get("type") == type_name), None)
            prefix = definition.get("prefix", "{{") if definition else "{{"
            suffix = definition.get("suffix", "}}") if definition else "}}"
            
            for raw_tag in raw_tags:
                name = _extract_placeholder_name(raw_tag, prefix, suffix)
                normalized = _normalize_for_matching(name)
                
                placeholders_list.append({
                    "raw": raw_tag,
                    "name": name,
                    "normalized": normalized,
                    "type": type_name,
                    "prefix": prefix,
                    "suffix": suffix
                })
        
        # Sort by type then by name for consistent ordering
        placeholders_list.sort(key=lambda x: (x["type"], x["name"]))
        
        result["placeholders"] = placeholders_list
        result["total_count"] = len(placeholders_list)
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
    
    return result

# --------------------------------------> END [ UI API FUNCTION ... ]