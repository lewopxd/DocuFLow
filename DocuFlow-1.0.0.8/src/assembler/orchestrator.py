#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  orchestrator.py
Created: 2025-11-05
Author: @lewopxd

Description:
Main orchestrator for complex, multi-step backend jobs.
Combines core functions to perform bulk operations, such as
reading from an Excel sheet and generating multiple Word documents.

MODIFICADO (v2 - BUGFIX de Trazabilidad):
- Añadida la lista 'failure_details_list' para registrar
  correctamente los errores que solo se estaban contando
  en 'failure_count' pero no se estaban reportando.

MODIFICADO (v3 - BUGFIX Lógica de Filtros):
- Se reemplazó el 'raise Exception' en la lógica de filtros
  por un 'continue'. Lanzar una excepción por una fila
  omitida era un anti-patrón que generaba falsos
  positivos en el log de errores.
"""

import os
import sys
import re
import math
import shutil  # <--- [ ADICIÓN 1/3 ] Importar el módulo de copia de archivos
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime

# Import centralized Logger
try:
    from core.logger import Logger
except ImportError:
    # Fallback if Logger not available
    class Logger:
        @staticmethod
        def debug(msg): Logger.debug(f"DEBUG: {msg}")
        @staticmethod
        def info(msg): Logger.debug(f"INFO: {msg}")
        @staticmethod
        def warn(msg): Logger.debug(f"WARN: {msg}")
        @staticmethod
        def error(msg): Logger.error(f"ERROR: {msg}")
        @staticmethod
        def job_start(job_id, total_items, description=""): Logger.debug(f"JOB START: {description} ({total_items} items)")
        @staticmethod
        def job_progress(current, total, item_name="", step=""): pass
        @staticmethod
        def job_item_result(item_name, status, details=None): pass
        @staticmethod
        def job_complete(summary): Logger.debug(f"JOB COMPLETE: {summary}")

# -------------------------------------------------------------
# -------------------[   CORE IMPORTS   ]----------------------
# -------------------------------------------------------------

try:
    # Importar el lector de filas de Excel
    from core.data_sheet.data_sheet_parser import get_row_data_sheet
    
    # Importar el generador de documentos Word
    from core.ms_word.replace_holders_text import generate_document_from_template
    
except ImportError as e:
    Logger.error(f"CRITICAL (Orchester): No se pudieron importar los módulos del Core.")
    Logger.error(f"   Error: {e}")
    get_row_data_sheet = None
    generate_document_from_template = None

# Optional: PDF converter engine
try:
    from core.pdf_helpers.pdf_converter_engine import (
        PdfConverterEngine, 
        PdfConverterConfig,
        ConversionTask
    )
    PDF_CONVERTER_AVAILABLE = True
except ImportError:
    PDF_CONVERTER_AVAILABLE = False
    Logger.warn("(Orchester) PdfConverterEngine no disponible - conversión PDF deshabilitada")

# -------------------------------------------------------------
# -------------------[   TRANSFORMS SYSTEM   ]-----------------
# -------------------------------------------------------------

def _transform_trim(value: str, config: Dict[str, Any]) -> str:
    """Elimina espacios al inicio y final."""
    return value.strip()

def _transform_uppercase(value: str, config: Dict[str, Any]) -> str:
    """Convierte a mayúsculas."""
    return value.upper()

def _transform_lowercase(value: str, config: Dict[str, Any]) -> str:
    """Convierte a minúsculas."""
    return value.lower()

def _transform_sentence_case(value: str, config: Dict[str, Any]) -> str:
    """Primera letra mayúscula, resto minúsculas."""
    return value.capitalize()

def _transform_title_case(value: str, config: Dict[str, Any]) -> str:
    """Primera letra de cada palabra en mayúscula."""
    return value.title()

def _transform_replace(value: str, config: Dict[str, Any]) -> str:
    """Reemplaza texto simple."""
    from_text = config.get("from", "")
    to_text = config.get("to", "")
    return value.replace(from_text, to_text)

def _transform_regex_replace(value: str, config: Dict[str, Any]) -> str:
    """Reemplaza usando expresiones regulares."""
    pattern = config.get("pattern", "")
    replacement = config.get("replacement", "")
    flags = config.get("flags", 0)
    
    try:
        if flags:
            return re.sub(pattern, replacement, value, flags=flags)
        else:
            return re.sub(pattern, replacement, value)
    except re.error as e:
        Logger.error(f"⚠️ Error en regex_replace: {e}. Devolviendo valor original.")
        return value

def _transform_truncate(value: str, config: Dict[str, Any]) -> str:
    """Limita la longitud del texto."""
    max_length = config.get("max_length", 100)
    suffix = config.get("suffix", "")
    
    if len(value) <= max_length:
        return value
    
    return value[:max_length] + suffix

def _transform_pad_left(value: str, config: Dict[str, Any]) -> str:
    """Rellena con caracteres a la izquierda."""
    width = config.get("width", 10)
    fillchar = config.get("fillchar", " ")
    
    if len(fillchar) != 1:
        Logger.warn(f"pad_left requiere fillchar de 1 carácter. Usando espacio.")
        fillchar = " "
    
    return value.rjust(width, fillchar)

def _transform_pad_right(value: str, config: Dict[str, Any]) -> str:
    """Rellena con caracteres a la derecha."""
    width = config.get("width", 10)
    fillchar = config.get("fillchar", " ")
    
    if len(fillchar) != 1:
        Logger.warn(f"pad_right requiere fillchar de 1 carácter. Usando espacio.")
        fillchar = " "
    
    return value.ljust(width, fillchar)

def _transform_substring(value: str, config: Dict[str, Any]) -> str:
    """Extrae una porción del texto."""
    start = config.get("start", 0)
    end = config.get("end", None)
    
    if end is None:
        return value[start:]
    else:
        return value[start:end]


def _transform_date_format(value: str, config: Dict[str, Any]) -> str:
    """
    Formatea fechas con plantillas personalizadas muy flexibles.
    Soporta tanto códigos estándar (%Y, %m, %d) como códigos personalizados
    en español (ej. %mes_es).
    """

    SPANISH_MONTHS = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
        7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    SPANISH_MONTHS_SHORT = {
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"
    }

    if not value or not str(value).strip():
        # Si el valor es vacío, no podemos formatear.
        # Lanzar un error claro que será atrapado por el 'except' principal.
        raise ValueError("El valor de fecha para 'date_format' está vacío o nulo.")
        
    input_format = config.get("input_format", None)
    output_template = config.get("output_template", "%d/%m/%Y")
    
    value_to_parse = str(value).strip()
    
    try:
        if input_format is None:
            common_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%m-%d-%Y",
                "%Y%m%d",
                "%d.%m.%Y",
                "%Y.%m.%d"
            ]
            
            date_obj = None
            for fmt in common_formats:
                try:
                    date_obj = datetime.strptime(value_to_parse, fmt)
                    break 
                except ValueError:
                    continue 
            
            if date_obj is None:
                raise ValueError(f"No se pudo detectar el formato de fecha para '{value_to_parse}'")
        else:
            date_obj = datetime.strptime(value_to_parse, input_format)
        
        result = output_template
        month_num = date_obj.month
        
        if "%mes_es" in result:
            result = result.replace("%mes_es", SPANISH_MONTHS[month_num])
        
        if "%b_es" in result:
            result = result.replace("%b_es", SPANISH_MONTHS_SHORT[month_num])

        result = date_obj.strftime(result)
        
        return result
        
    except Exception as e:
        Logger.error(f"⚠️ Error en date_format: {e}. Devolviendo valor original.")
        # Propagar el error para que el 'except' principal lo atrape y lo
        # registre en 'failure_details_list'.
        raise e


def _transform_number_format(value: str, config: Dict[str, Any]) -> str:
    """Formatea números con decimales y separadores."""
    decimals = config.get("decimals", 2)
    decimal_sep = config.get("decimal_sep", ".")
    thousands_sep = config.get("thousands_sep", ",")
    
    try:
        num = float(value)
        formatted = f"{num:.{decimals}f}"
        parts = formatted.split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else ""
        
        if thousands_sep:
            integer_part = "{:,}".format(int(integer_part)).replace(",", thousands_sep)
        
        if decimal_part:
            return f"{integer_part}{decimal_sep}{decimal_part}"
        else:
            return integer_part
            
    except ValueError as e:
        Logger.error(f"⚠️ Error en number_format: {e}. Devolviendo valor original.")
        return value

def _transform_round(value: str, config: Dict[str, Any]) -> str:
    """Redondea un número."""
    decimals = config.get("decimals", 0)
    
    try:
        num = float(value)
        rounded = round(num, decimals)
        
        if decimals == 0:
            return str(int(rounded))
        else:
            return str(rounded)
            
    except ValueError as e:
        Logger.error(f"⚠️ Error en round: {e}. Devolviendo valor original.")
        return value

def _transform_ceil(value: str, config: Dict[str, Any]) -> str:
    """Redondea hacia arriba."""
    try:
        num = float(value)
        return str(int(math.ceil(num)))
    except ValueError as e:
        Logger.error(f"⚠️ Error en ceil: {e}. Devolviendo valor original.")
        return value

def _transform_floor(value: str, config: Dict[str, Any]) -> str:
    """Redondea hacia abajo."""
    try:
        num = float(value)
        return str(int(math.floor(num)))
    except ValueError as e:
        Logger.error(f"⚠️ Error en floor: {e}. Devolviendo valor original.")
        return value

def _transform_default_if_empty(value: str, config: Dict[str, Any]) -> str:
    """Devuelve un valor por defecto si el valor está vacío."""
    default = config.get("default", "")
    
    if value is None or value.strip() == "":
        return default
    
    return value

def _transform_validate_regex(value: str, config: Dict[str, Any]) -> str:
    """Valida contra un patrón regex, devuelve fallback si no coincide."""
    pattern = config.get("pattern", ".*")
    fallback = config.get("fallback", "")
    
    try:
        if re.match(pattern, value):
            return value
        else:
            Logger.warn(f"Valor '{value}' no coincide con patrón '{pattern}'. Usando fallback.")
            return fallback
    except re.error as e:
        Logger.error(f"⚠️ Error en validate_regex: {e}. Devolviendo fallback.")
        return fallback

# Registry de transformaciones
TRANSFORM_REGISTRY = {
    "trim": _transform_trim,
    "uppercase": _transform_uppercase,
    "lowercase": _transform_lowercase,
    "sentence_case": _transform_sentence_case,
    "title_case": _transform_title_case,
    "replace": _transform_replace,
    "regex_replace": _transform_regex_replace,
    "truncate": _transform_truncate,
    "pad_left": _transform_pad_left,
    "pad_right": _transform_pad_right,
    "substring": _transform_substring,
    "date_format": _transform_date_format,
    "number_format": _transform_number_format,
    "round": _transform_round,
    "ceil": _transform_ceil,
    "floor": _transform_floor,
    "default_if_empty": _transform_default_if_empty,
    "validate_regex": _transform_validate_regex
}

def apply_transforms(value: Any, transforms: List[Dict[str, Any]], debug: bool = False) -> str:
    """Aplica una secuencia de transformaciones a un valor."""
    if value is None:
        current_value = ""
    else:
        current_value = str(value)
    
    if not transforms:
        return current_value
    
    for i, transform_config in enumerate(transforms):
        transform_type = transform_config.get("type")
        
        if not transform_type:
            Logger.warn(f"Transformación sin 'type' especificado: {transform_config}")
            continue
        
        transform_func = TRANSFORM_REGISTRY.get(transform_type)
        
        if not transform_func:
            Logger.warn(f"Tipo de transformación desconocido: '{transform_type}'")
            continue
        
        try:
            previous_value = current_value
            current_value = transform_func(current_value, transform_config)
            
            if debug:
                Logger.debug(f"   Transform #{i+1} ({transform_type}): '{previous_value}' → '{current_value}'")
                
        except Exception as e:
            Logger.error(f"Error aplicando transformación '{transform_type}': {e}")
            Logger.debug(f"   Configuración: {transform_config}")
            Logger.debug(f"   Manteniendo valor anterior: '{current_value}'")
            # Propagar el error para que sea atrapado por el 'except'
            # principal y se registre en 'failure_details_list'.
            raise e
    
    return current_value

# -------------------------------------------------------------
# -------------------[   HELPER: FILTERING   ]-----------------
# -------------------------------------------------------------

def _evaluate_row(row_data: dict, rules: dict) -> bool:
    """Evalúa recursivamente si una fila de datos cumple con el árbol de reglas."""
    try:
        if "AND" in rules:
            return all(_evaluate_row(row_data, rule) for rule in rules["AND"])
        
        if "OR" in rules:
            return any(_evaluate_row(row_data, rule) for rule in rules["OR"])

        column = rules.get("column")
        op = rules.get("operator")
        value = rules.get("value")
        
        cell_value = row_data.get(column)
        
        if cell_value is not None:
             cell_value = str(cell_value)

        if op == "equal":
            return cell_value == value
        if op == "not_equal":
            return cell_value != value
        if op == "contains":
            return value in (cell_value or "")
        if op == "is_empty":
            return cell_value is None or cell_value == ""
        if op == "is_not_empty":
            return cell_value is not None and cell_value != ""
        
        Logger.warn(f"Advertencia de Filtro: Operador desconocido '{op}'. La regla fallará.")
        return False
        
    except Exception as e:
        Logger.error(f"Error evaluando regla de filtro {rules}: {e}")
        return False

# -------------------------------------------------------------
# -------------------[   HELPER: MAPPING   ]-------------------
# -------------------------------------------------------------

def _build_replacements(
    row_data: Dict[str, Any], 
    job_config: Dict[str, Any], 
    debug: bool = False
) -> Dict[str, str]:
    """
    Construye el diccionario de reemplazos para Word a partir de una fila de Excel.
    """
    replacements_dict = {}

    direct_mapping = job_config.get("direct_mapping", {})
    computed_mapping = job_config.get("computed_mapping", [])
    
    # 1. Obtener el default global, con un fallback final a KEEP_PLACEHOLDER
    global_on_missing = job_config.get("on_missing_data", "KEEP_PLACEHOLDER")

    # --- 1. Mapeo Directo (1:1) con Transforms ---
    if direct_mapping:
        for word_tag, config in direct_mapping.items():
            if isinstance(config, str):
                excel_column = config
                transforms = []
                local_on_missing = None 
            elif isinstance(config, dict):
                excel_column = config.get("source_column")
                transforms = config.get("transforms", [])
                local_on_missing = config.get("on_missing")
            else:
                Logger.warn(f"Configuración inválida para placeholder '{word_tag}': {config}")
                continue
            
            # 3. Determinar la política final
            on_missing = local_on_missing if local_on_missing else global_on_missing
            
            cell_value = row_data.get(excel_column)
            
            # 4. Aplicar la política de datos faltantes
            if cell_value is None:
                if debug:
                    Logger.warn(f"Advertencia de Mapeo: Columna '{excel_column}' no encontrada o nula.")

                if on_missing == "FAIL":
                    raise ValueError(f"Dato faltante (FAIL): La columna '{excel_column}' (para el tag '{word_tag}') es nula y la política es 'FAIL'.")
                
                elif on_missing == "REPLACE_EMPTY":
                    final_value = apply_transforms("", transforms, debug=debug)
                    replacements_dict[word_tag] = final_value
                
                elif on_missing == "KEEP_PLACEHOLDER":
                    if debug:
                        Logger.debug(f"   → Política 'KEEP_PLACEHOLDER': El tag '{word_tag}' se mantendrá en el documento.")
                    continue 
            
            else:
                final_value = apply_transforms(cell_value, transforms, debug=debug)
                replacements_dict[word_tag] = final_value

    # --- 2. Mapeo Calculado (Lógica) con Transforms ---
    if computed_mapping:
        for item in computed_mapping:
            placeholder = item.get("placeholder")
            rule = item.get("rule")
            transforms = item.get("transforms", [])
            
            if not placeholder or not rule:
                continue

            rule_type = rule.get("type")
            
            try:
                computed_value = ""
                
                if rule_type == "concatenate":
                    columns = rule.get("columns", [])
                    separator = rule.get("separator", " ")
                    values = [str(row_data.get(col, "")) for col in columns]
                    computed_value = separator.join(values)
                
                elif rule_type == "conditional_map":
                    on_column = rule.get("on_column")
                    value_map = rule.get("map", {})
                    
                    key_value = str(row_data.get(on_column, "")).strip().upper()
                    
                    safe_map = {str(k).upper(): v for k, v in value_map.items()}

                    if key_value in safe_map:
                        computed_value = safe_map[key_value]
                    else:
                        computed_value = safe_map.get("DEFAULT", "")
                
                else:
                    Logger.warn(f"Tipo de regla calculada desconocido: '{rule_type}'")
                    computed_value = "[REGLA DESCONOCIDA]"
                
                final_value = apply_transforms(computed_value, transforms, debug=debug)
                replacements_dict[placeholder] = final_value
                        
            except Exception as e:
                Logger.error(f"Error procesando regla calculada para '{placeholder}': {e}")
                replacements_dict[placeholder] = "[ERROR DE REGLA]"

    # --- [ DEBUG MEJORADO ] ---
    if debug:
        Logger.debug(f"\n   =================================================")
        Logger.debug(f"   [DEBUG] Diccionario de Reemplazos (Fila {row_data.get('row_index', 'N/A')}) Creado:")
        Logger.debug(f"   -------------------------------------------------")
        if replacements_dict:
            max_key_len = max(len(k) for k in replacements_dict.keys())
            for key, value in sorted(replacements_dict.items()):
                Logger.debug(f"     > {key.ljust(max_key_len)} : '{value}'")
        else:
            Logger.debug("     > (Vacío)")
        Logger.debug(f"   =================================================\n")
    # --- [ FIN DEBUG MEJORADO ] ---

    return replacements_dict

# -------------------------------------------------------------
# -------------------[   HELPER: FORMATTING   ]----------------
# -------------------------------------------------------------

def _sanitize_filename(filename: str) -> str:
    """Elimina caracteres inválidos para nombres de archivo en Windows."""
    invalid_chars = r'[*?:"<>|]'
    return re.sub(invalid_chars, '_', filename)

def _process_pattern_with_columns(
    pattern_config: Dict[str, Any],
    row_data: Dict[str, Any],
    debug: bool = False
) -> str:
    """Procesa un patrón con columnas usando la sintaxis {[COLUMNA]}."""
    template = pattern_config.get("template", "")
    columns_config = pattern_config.get("columns", [])
    
    transforms_map = {}
    for col_config in columns_config:
        col_name = col_config.get("name")
        col_transforms = col_config.get("transforms", [])
        
        if not col_transforms and "format" in col_config:
            old_format = col_config.get("format")
            if old_format:
                format_mapping = {
                    "MAYUSCULAS": "uppercase",
                    "MINUSCULAS": "lowercase",
                    "TIPO_FRASE": "sentence_case"
                }
                transform_type = format_mapping.get(old_format.upper())
                if transform_type:
                    col_transforms = [{"type": transform_type}]
        
        if col_name:
            transforms_map[col_name] = col_transforms
    
    pattern = r"\{\[([^\]]+)\]\}"
    matches = re.finditer(pattern, template)
    
    result = template
    processed_replacements = {}
    
    for match in matches:
        full_match = match.group(0)
        col_name = match.group(1)
        
        if full_match in processed_replacements:
            continue
        
        cell_value = row_data.get(col_name)
        
        if cell_value is None:
            if debug:
                Logger.warn(f"Advertencia: Columna '{col_name}' no encontrada en datos. Usando string vacío.")
            cell_value = ""
        
        transforms = transforms_map.get(col_name, [])
        value = apply_transforms(cell_value, transforms, debug=debug)
        value = _sanitize_filename(value)
        processed_replacements[full_match] = value
    
    for placeholder, value in processed_replacements.items():
        result = result.replace(placeholder, value)
    
    return result

def _build_output_path(
    folder_config: Dict[str, Any],
    filename_config: Dict[str, Any],
    base_directory: str,
    row_data: Dict[str, Any],
    debug: bool = False
) -> str:
    """Construye la ruta completa de salida (carpeta + archivo)."""
    try:
        folder_path = _process_pattern_with_columns(folder_config, row_data, debug=debug)
        
        # --- [ INICIO: CORRECCIÓN LÓGICA ] ---
        # El orquestador debe ser lo suficientemente inteligente como para
        # fusionar las columnas de 'folder_config' y 'filename_config'
        # para que el 'filename_pattern' pueda usar columnas (como NOMBRES)
        # definidas en el 'folder_pattern'.
        
        # 1. Obtener transformaciones del folder_pattern
        folder_cols_map = {}
        for col_cfg in folder_config.get("columns", []):
            folder_cols_map[col_cfg["name"]] = col_cfg.get("transforms", [])
        
        # 2. Obtener transformaciones del filename_pattern
        filename_cols_list = filename_config.get("columns", [])
        
        # 3. Crear un config combinado SOLO para el nombre de archivo
        combined_filename_config = {
            "template": filename_config.get("template", "documento.docx"),
            "columns": []
        }
        
        # 4. Añadir columnas del filename_config (tienen prioridad)
        filename_cols_names = set()
        for col_cfg in filename_cols_list:
            col_name = col_cfg.get("name")
            if col_name:
                filename_cols_names.add(col_name)
                combined_filename_config["columns"].append(col_cfg)
        
        # 5. Añadir columnas FALTANTES del folder_config
        for col_name, transforms in folder_cols_map.items():
            if col_name not in filename_cols_names:
                combined_filename_config["columns"].append({
                    "name": col_name,
                    "transforms": transforms
                })
        
        # 6. Procesar el nombre de archivo usando el config combinado
        filename = _process_pattern_with_columns(combined_filename_config, row_data, debug=debug)
        # --- [ FIN: CORRECCIÓN LÓGICA ] ---

        if folder_path:
            folder_path = folder_path.replace("/", os.sep).replace("\\", os.sep)
            full_path = os.path.join(folder_path, filename)
        else:
            full_path = filename
        
        return full_path
        
    except Exception as e:
        Logger.error(f"Error construyendo ruta de salida: {e}")
        # Si la construcción de la ruta falla (ej. un date_format en una
        # columna del nombre de archivo), esta excepción será
        # atrapada por el 'except' principal (línea 547).
        raise e

# -------------------------------------------------------------
# -------------------[   PDF CONVERSION HELPERS   ]-------------
# -------------------------------------------------------------

def _build_pdf_output_path(
    docx_path: Path,
    pdf_config: Dict[str, Any],
    row_data: Dict[str, Any],
    base_directory: str,
    debug: bool = False
) -> Path:
    """
    Construye la ruta de salida del PDF.
    
    Si pdf_config tiene 'output_pattern', usa ese patrón con placeholders.
    Si no, simplemente cambia la extensión del DOCX a .pdf.
    """
    output_pattern = pdf_config.get("output_pattern")
    
    if output_pattern and output_pattern.get("template"):
        # Usar patrón personalizado
        folder_pattern = {"template": "", "columns": []}
        filename_pattern = output_pattern
        
        # Separar folder y filename si el template incluye path
        template = output_pattern.get("template", "")
        if "/" in template or "\\" in template:
            parts = template.replace("\\", "/").rsplit("/", 1)
            folder_pattern = {
                "template": parts[0],
                "columns": output_pattern.get("columns", [])
            }
            filename_pattern = {
                "template": parts[1] if len(parts) > 1 else template,
                "columns": output_pattern.get("columns", [])
            }
        
        relative_path = _build_output_path(
            folder_pattern,
            filename_pattern,
            base_directory,
            row_data,
            debug=debug
        )
        
        # Asegurar extensión .pdf
        if not relative_path.lower().endswith(".pdf"):
            relative_path = Path(relative_path).with_suffix(".pdf")
        else:
            relative_path = Path(relative_path)
        
        return Path(base_directory) / relative_path
    else:
        # Default: usar misma ubicación que DOCX
        return docx_path.with_suffix(".pdf")


def _convert_single_to_pdf(
    docx_path: Path,
    pdf_path: Path,
    pdf_engine: 'PdfConverterEngine',
    debug: bool = False
) -> Dict[str, Any]:
    """
    Convierte un solo archivo DOCX a PDF.
    Devuelve un diccionario con el resultado.
    """
    try:
        result = pdf_engine.convert_single(docx_path, pdf_path)
        
        return {
            "success": result.success,
            "source_path": str(result.source_path),
            "target_path": str(result.target_path),
            "error": result.error,
            "duration_seconds": result.duration_seconds
        }
    except Exception as e:
        Logger.error(f"Error en conversión PDF: {e}")
        return {
            "success": False,
            "source_path": str(docx_path),
            "target_path": str(pdf_path),
            "error": str(e)
        }


# -------------------------------------------------------------
# -------------------[   MAIN ORCHESTRATOR   ]-----------------
# -------------------------------------------------------------

def execute_bulk_document_job(config: Dict[str, Any]) -> Dict[str, Any]:
    """Función principal de orquestación."""
    
    job_summary = {
        "status": "pending",
        "total_rows_processed": 0,
        "success_count": 0,
        "failure_count": 0,
        "total_skipped": 0
    }
    job_results = []
    
    try:
        if not get_row_data_sheet or not generate_document_from_template:
            raise ImportError("Funciones críticas del Core (Excel o Word) no están disponibles.")

        excel_config = config.get("excel_config")
        template_config = config.get("template_config")
        job_config = config.get("job_config")
        
        if not all([excel_config, template_config, job_config]):
            raise ValueError("Configuración inválida. Faltan 'excel_config', 'template_config' o 'job_config'.")
            
        folder_pattern = job_config.get("folder_pattern", {"template": "", "columns": []})
        filename_pattern = job_config.get("filename_pattern", {"template": "documento.docx", "columns": []})
        overwrite = job_config.get("overwrite_existing", False)
        debug = job_config.get("debug", False)
        filter_rules = job_config.get("filter_rules")
        
        # --- [ PDF CONVERSION CONFIG ] ---
        pdf_config = job_config.get("convert_to_pdf", {})
        pdf_enabled = pdf_config.get("enabled", False) and PDF_CONVERTER_AVAILABLE
        pdf_timing = pdf_config.get("timing", "IMMEDIATE").upper()  # IMMEDIATE | AFTER_ROW | BATCH_END
        pdf_keep_docx = pdf_config.get("keep_docx", True)
        pdf_engine = None
        pdf_pending_tasks: List[Tuple[Path, Path, Dict[str, Any]]] = []  # (docx_path, pdf_path, row_data)
        pdf_results = []
        
        if pdf_enabled:
            try:
                engine_config = PdfConverterConfig.from_dict(pdf_config)
                pdf_method = pdf_config.get("method", "office").lower()
                
                # --- [ LIBREOFFICE VALIDATION ] ---
                if pdf_method == "libreoffice":
                    from core.file_helpers.storage import AppStorage
                    from core.utils.environment_validator import EnvironmentValidator
                    from core.utils.libreoffice_manager import LibreOfficeManager
                    
                    storage = AppStorage()
                    
                    # Check cached state first (fast path)
                    if storage.is_libreoffice_cached_available():
                        cached_path = storage.get_libreoffice_status().get("libreoffice_path")
                        if cached_path and Path(cached_path).exists():
                            Logger.info(f"[Orchestrator] LibreOffice disponible: {cached_path}")
                        else:
                            storage.invalidate_libreoffice_status()
                    
                    # Actual check if not cached as available
                    if not storage.is_libreoffice_cached_available():
                        is_available, lo_path, error = EnvironmentValidator.check_libreoffice()
                        
                        if not is_available:
                            Logger.error(f"[Orchestrator] LibreOffice no disponible: {error}")
                            job_summary["status"] = "error"
                            job_summary["error"] = "LibreOffice no está instalado. Instálelo manualmente para usar este método de conversión."
                            return {
                                "job_summary": job_summary,
                                "job_results": [],
                                "failure_details": []
                            }
                        
                        # Update cached state
                        version = LibreOfficeManager.get_version()
                        storage.set_libreoffice_status(
                            available=True,
                            path=str(lo_path) if lo_path else None,
                            version=version
                        )
                # --- [ FIN LIBREOFFICE VALIDATION ] ---
                
                if pdf_enabled:
                    pdf_engine = PdfConverterEngine(engine_config)
                    
                    # VALIDATION: Check environment once at start
                    is_valid, validation_error = pdf_engine.validate_environment()
                    if not is_valid:
                        Logger.error(f"[Orchestrator] Error validando entorno PDF: {validation_error}")
                        Logger.warn("[Orchestrator] Se deshabilitará la conversión a PDF para este trabajo.")
                        pdf_enabled = False
                        pdf_engine = None
                    else:
                        Logger.info(f"[Orchestrator] Conversión PDF habilitada (timing={pdf_timing})")
                    
            except Exception as e:
                Logger.error(f"[Orchestrator] Error inicializando PDF engine: {e}")
                pdf_enabled = False
        # --- [ FIN PDF CONVERSION CONFIG ] ---
        
        base_directory = template_config.get("target_directory")
        if not base_directory:
            raise ValueError("Falta 'target_directory' en template_config.")

        # --- Logger: Job Start ---
        Logger.info(f"Extrayendo datos de Excel: {excel_config.get('filePath')}")
        
        row_data_list = get_row_data_sheet(excel_config)
        
        if row_data_list is None:
            raise Exception("Falla al leer datos de Excel. El trabajo no puede continuar.")
        
        if not row_data_list:
            Logger.info("No se encontraron filas en el rango especificado. Trabajo finalizado.")
            job_summary["status"] = "complete_success"
            return {"job_summary": job_summary, "job_results": [], "failure_details": []}

        Logger.job_start(
            job_id=f"bulk_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            total_items=len(row_data_list),
            description=f"Generación bulk desde {Path(excel_config.get('filePath', '')).name}"
        )
        
        if debug:
            Logger.set_level("DEBUG") if hasattr(Logger, 'set_level') else None
            Logger.debug("Modo DEBUG activado: Se mostrará información detallada.")
        
        success_count = 0
        failure_count = 0
        skipped_count = 0
        
        # --- [ CAMBIO 1/5 ] ---
        # Inicializar la lista de fallos que el script maestro espera
        failure_details_list = []
        
        total_rows = len(row_data_list)
        for idx, row_data in enumerate(row_data_list, 1):
            row_index = row_data.get("row_index", "N/A")
            generation_log = {}
            relative_path = "N/A"
            status = "pending"
            full_target_path = None
            
            try:
                # --- Logger: Progress Update ---
                item_name = f"{row_data.get('NOMBRES', '')} {row_data.get('APELLIDOS', '')}" if 'NOMBRES' in row_data else f"Fila {row_index}"
                Logger.job_progress(idx, total_rows, item_name.strip(), "Procesando...")
                
                if debug:
                    Logger.debug(f"Procesando Fila {row_index}")
                
                if filter_rules:
                    if not _evaluate_row(row_data, filter_rules):
                        skipped_count += 1
                        status = "skipped"
                        if debug:
                            Logger.debug(f"   ⊘ Fila {row_index} omitida (no cumple filter_rules)")
                        
                        # --- [ INICIO: CORRECCIÓN v3 ] ---
                        # Antes: raise Exception("La fila no cumplió con las 'filter_rules'.")
                        # Esto era un anti-patrón. Ahora usamos 'continue'
                        # para saltar limpiamente a la siguiente fila.
                        # El 'except' ya no se activará para esto.
                        job_results.append({
                            "row_index": row_index,
                            "input_data": row_data,
                            "filename_generated": "N/A",
                            "status": "skipped",
                            "output_log": {"success": False, "error": "Fila omitida por filter_rules"}
                        })
                        continue 
                        # --- [ FIN: CORRECCIÓN v3 ] ---

                if debug:
                    Logger.debug(f"   Mapeando datos para placeholders Word...")
                
                replacements_dict = _build_replacements(row_data, job_config, debug=debug)
                
                if debug:
                    Logger.debug(f"   Construyendo ruta de salida...")
                relative_path = _build_output_path(
                    folder_pattern,
                    filename_pattern,
                    base_directory,
                    row_data,
                    debug=debug
                )
                
                if debug:
                    Logger.debug(f"   → Ruta generada: {relative_path}")
                
                full_target_path = Path(base_directory) / relative_path
                if full_target_path.exists() and not overwrite:
                    raise FileExistsError(f"El archivo '{relative_path}' ya existe y 'overwrite_existing' es False.")

                # --- [ Lógica de Copia vs. Reemplazo ] ---
                
                # Caso 1: Diccionario de reemplazo VACÍO (Trabajo de Copia)
                if not replacements_dict:
                    if debug:
                        Logger.debug("   Diccionario de reemplazos vacío. Ejecutando copia simple de archivo...")
                    
                    # Obtener la plantilla original
                    source_path = template_config.get("source_path")
                    
                    # Asegurarse de que el directorio de destino existe
                    full_target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copiar el archivo (shutil.copy2 preserva metadatos)
                    shutil.copy2(source_path, full_target_path)
                    
                    # Crear un log de éxito simple
                    generation_log = {
                        "success": True, 
                        "target_path": str(full_target_path), 
                        "details": {
                            "placeholder_status": {"not_found": []}, # No se buscó ninguno
                            "message": "Simple file copy."
                        }
                    }

                # Caso 2: Diccionario de reemplazo LLENO (Trabajo de Reemplazo)
                else:
                    if debug:
                        Logger.debug(f"   Generando documento Word con {len(replacements_dict)} reemplazos...")
                    
                    word_config = template_config.copy()
                    word_config["target_filename"] = relative_path
                    word_config["replacements"] = replacements_dict
                    word_config["overwrite"] = overwrite
                    
                    generation_log = generate_document_from_template(word_config)
                
                # --- [ FIN Lógica de Copia vs. Reemplazo ] ---

                
                # Lógica de fallo estricta (funciona para ambos casos)
                placeholder_status = generation_log.get("details", {}).get("placeholder_status", {})
                not_found_tags = placeholder_status.get("not_found", [])
                
                if generation_log.get("success") and not_found_tags:
                    status = "failure" 
                    failure_count += 1
                    generation_log["success"] = False
                    error_msg = f"Archivo creado, pero faltaron placeholders: {not_found_tags}" # <-- El error
                    generation_log["error"] = error_msg
                    
                    # --- [ CAMBIO 2/5 ] ---
                    # Registrar el fallo de placeholder faltante
                    folder_name = _process_pattern_with_columns(folder_pattern, row_data, debug=False)
                    failure_details_list.append({
                        "identifier": folder_name,
                        "row_index": row_index,
                        "error": error_msg
                    })
                    # --- [ FIN DE LA ADICIÓN ] ---

                    if debug:
                        Logger.debug(f"   ✗ Fila {row_index} falló: Faltaron placeholders {not_found_tags}")
                
                elif generation_log.get("success"):
                    success_count += 1
                    status = "success"
                    Logger.job_item_result(item_name, "success", {"file": str(relative_path)})
                    if debug:
                        Logger.debug(f"Fila {row_index} procesada exitosamente")
                    
                    # --- [ PDF CONVERSION - IMMEDIATE/QUEUE ] ---
                    if pdf_enabled and full_target_path and full_target_path.exists():
                        pdf_path = _build_pdf_output_path(
                            full_target_path, pdf_config, row_data, base_directory, debug
                        )
                        
                        if pdf_timing == "IMMEDIATE":
                            # Convertir inmediatamente
                            if debug:
                                Logger.debug(f"   [PDF] Convirtiendo a PDF: {pdf_path.name}")
                            
                            pdf_result = _convert_single_to_pdf(
                                full_target_path, pdf_path, pdf_engine, debug
                            )
                            pdf_results.append(pdf_result)
                            
                            if pdf_result.get("success"):
                                generation_log["pdf_path"] = str(pdf_path)
                                if not pdf_keep_docx:
                                    try:
                                        full_target_path.unlink()
                                        if debug:
                                            Logger.debug(f"   [PDF] DOCX eliminado (keep_docx=False)")
                                    except Exception as del_e:
                                        Logger.warn(f"No se pudo eliminar DOCX: {del_e}")
                            else:
                                Logger.warn(f"   [PDF] Error: {pdf_result.get('error')}")
                        else:
                            # Queue for AFTER_ROW or BATCH_END
                            pdf_pending_tasks.append((full_target_path, pdf_path, row_data.copy()))
                    # --- [ FIN PDF CONVERSION ] ---
                
                else:
                    failure_count += 1
                    status = "failure"

                    # --- [ CAMBIO 3/5 ] ---
                    # Registrar el fallo de generación
                    error_msg = generation_log.get('error', 'Error desconocido en generate_document_from_template')
                    folder_name = _process_pattern_with_columns(folder_pattern, row_data, debug=False)
                    failure_details_list.append({
                        "identifier": folder_name,
                        "row_index": row_index,
                        "error": error_msg
                    })
                    # --- [ FIN DE LA ADICIÓN ] ---

                    Logger.job_item_result(item_name, "error", {"error": generation_log.get('error', 'Error desconocido')})
                    if debug:
                        Logger.debug(f"Fila {row_index} falló: {generation_log.get('error', 'Error desconocido')}")
                
            except Exception as e:
                # --- [ INICIO: CORRECCIÓN v3 ] ---
                # Si el status es 'skipped', ya lo manejamos y no es un error.
                # Solo procesar esto si es un error REAL ('pending').
                if status == "skipped":
                    continue # El 'job_results' para 'skipped' ya se añadió
                # --- [ FIN: CORRECCIÓN v3 ] ---

                if status == "pending":
                    failure_count += 1
                    status = "failure"
                
                error_message = str(e)
                generation_log = {
                    "success": False,
                    "target_path": str(full_target_path) if full_target_path else None,
                    "error": f"Error del Orquestador (Fila {row_index}): {error_message}",
                    "details": None
                }

                # --- [ CAMBIO 4/5 ] ---
                # Registrar el fallo principal del orquestador (el que probablemente está ocurriendo)
                try:
                    folder_name = _process_pattern_with_columns(folder_pattern, row_data, debug=False)
                except Exception:
                    # Fallback si el error fue JUSTO al crear el nombre de la carpeta
                    folder_name = f"ERROR_AL_OBTENER_NOMBRE (Fila {row_index})"
                
                failure_details_list.append({
                    "identifier": folder_name,
                    "row_index": row_index,
                    "error": f"Error del Orquestador: {error_message}"
                })
                # --- [ FIN DE LA ADICIÓN ] ---
                
                if debug and status != "skipped":
                    Logger.error(f"   ✗ Error en Fila {row_index}: {error_message}")
            
            job_results.append({
                "row_index": row_index,
                "input_data": row_data,
                "filename_generated": relative_path,
                "status": status,
                "output_log": generation_log
            })

        job_summary["total_rows_processed"] = len(row_data_list)
        job_summary["success_count"] = success_count
        job_summary["failure_count"] = failure_count
        job_summary["total_skipped"] = skipped_count
        
        # --- [ PDF BATCH_END PROCESSING ] ---
        if pdf_enabled and pdf_pending_tasks and pdf_timing == "BATCH_END":
            Logger.info(f"[Orchestrator] Procesando {len(pdf_pending_tasks)} conversiones PDF (BATCH_END)")
            
            for docx_path, pdf_path, task_row_data in pdf_pending_tasks:
                if not docx_path.exists():
                    Logger.warn(f"[PDF] DOCX no encontrado: {docx_path}")
                    continue
                
                pdf_result = _convert_single_to_pdf(docx_path, pdf_path, pdf_engine, debug)
                pdf_results.append(pdf_result)
                
                if pdf_result.get("success") and not pdf_keep_docx:
                    try:
                        docx_path.unlink()
                    except Exception as del_e:
                        Logger.warn(f"No se pudo eliminar DOCX: {del_e}")
            
            # Update corresponding job_results with pdf_path
            pdf_paths_map = {str(r.get("source_path")): r.get("target_path") 
                           for r in pdf_results if r.get("success")}
            for jr in job_results:
                docx_target = jr.get("output_log", {}).get("target_path")
                if docx_target and docx_target in pdf_paths_map:
                    jr["output_log"]["pdf_path"] = pdf_paths_map[docx_target]
        
        # Cleanup PDF engine
        if pdf_engine:
            try:
                pdf_engine.cleanup()
            except Exception as e:
                Logger.warn(f"[PDF] Error en cleanup: {e}")
        # --- [ FIN PDF BATCH_END ] ---
        
        if failure_count == 0 and skipped_count == 0:
            job_summary["status"] = "complete_success"
        elif success_count > 0:
            job_summary["status"] = "partial_success"
        elif skipped_count == len(row_data_list):
            job_summary["status"] = "skipped_all"
        else:
            job_summary["status"] = "total_failure"
        
        # Add PDF conversion summary
        if pdf_enabled:
            pdf_success = sum(1 for r in pdf_results if r.get("success"))
            job_summary["pdf_conversions"] = {
                "total": len(pdf_results),
                "success": pdf_success,
                "failed": len(pdf_results) - pdf_success,
                "timing": pdf_timing
            }
            
        # --- Logger: Job Complete ---
        Logger.job_complete({
            "total": len(row_data_list),
            "success": success_count,
            "failed": failure_count,
            "skipped": skipped_count
        })

    except Exception as e:
        Logger.error(f"ERROR CRÍTICO DEL TRABAJO: {e}")
        job_summary["status"] = "total_failure"
        job_summary["error"] = str(e)
        
        # Cleanup PDF engine en caso de error
        if pdf_engine:
            try:
                pdf_engine.cleanup()
            except:
                pass
        
    # --- [ CAMBIO 5/5 ] ---
    # Devolver la lista de fallos junto con el resumen
    return {"job_summary": job_summary, "job_results": job_results, "failure_details": failure_details_list, "pdf_results": pdf_results}

# --------------------------------------> END [ MAIN ORCHESTRATOR ... ]