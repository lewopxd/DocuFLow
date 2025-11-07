#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  main_orchester.py
Created: 2025-11-05
Author: @lewopxd

Description:
Main orchestrator for complex, multi-step backend jobs.
Combines core functions to perform bulk operations, such as
reading from an Excel sheet and generating multiple Word documents.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# -------------------------------------------------------------
# -------------------[   CORE IMPORTS   ]----------------------
# -------------------------------------------------------------

try:
    # Importar el lector de filas de Excel
    from ..data_sheet.data_sheet_parser import get_row_data_sheet
    
    # Importar el generador de documentos Word
    from ..ms_word.replace_holders_text import generate_document_from_template
    
except ImportError as e:
    print(f"❌ CRITICAL (Orchester): No se pudieron importar los módulos del Core.")
    print(f"   Error: {e}")
    get_row_data_sheet = None
    generate_document_from_template = None

# -------------------------------------------------------------
# -------------------[   HELPER: FILTERING   ]-----------------
# -------------------------------------------------------------

def _evaluate_row(row_data: dict, rules: dict) -> bool:
    """
    Evalúa recursivamente si una fila de datos cumple con el árbol de reglas.
    """
    try:
        # --- Caso Lógico: AND ---
        if "AND" in rules:
            # Devuelve True solo si TODAS las sub-reglas son True
            return all(_evaluate_row(row_data, rule) for rule in rules["AND"])
        
        # --- Caso Lógico: OR ---
        if "OR" in rules:
            # Devuelve True si ALGUNA sub-regla es True
            return any(_evaluate_row(row_data, rule) for rule in rules["OR"])

        # --- Caso Base: Regla de Operador ---
        column = rules.get("column")
        op = rules.get("operator")
        value = rules.get("value")
        
        # Obtener el valor de la fila (None si no existe)
        cell_value = row_data.get(column)
        
        # Convertir a string para comparaciones seguras (excepto Nones)
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
        
        # (Se pueden añadir 'greater_than', 'less_than' con conversión a float)
        
        print(f"⚠️ Advertencia de Filtro: Operador desconocido '{op}'. La regla fallará.")
        return False
        
    except Exception as e:
        print(f"❌ Error evaluando regla de filtro {rules}: {e}")
        return False

# -------------------------------------------------------------
# -------------------[   HELPER: MAPPING   ]-------------------
# -------------------------------------------------------------

def _build_replacements(
    row_data: Dict[str, Any], 
    direct_mapping: Dict[str, str],
    computed_mapping: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Construye el diccionario de reemplazos para Word a partir de una fila de Excel,
    manejando mapeos directos y calculados (lógica de negocio).
    """
    replacements_dict = {}

    # --- 1. Mapeo Directo (1:1) ---
    if direct_mapping:
        for word_tag, excel_column in direct_mapping.items():
            cell_value = row_data.get(excel_column)
            if cell_value is None:
                replacements_dict[word_tag] = ""
                print(f"⚠️ Advertencia de Mapeo: Columna '{excel_column}' no encontrada. Usando string vacío.")
            else:
                replacements_dict[word_tag] = str(cell_value)

    # --- 2. Mapeo Calculado (Lógica) ---
    if computed_mapping:
        for item in computed_mapping:
            placeholder = item.get("placeholder")
            rule = item.get("rule")
            if not placeholder or not rule:
                continue

            rule_type = rule.get("type")
            
            try:
                # --- Lógica de Concatenación ---
                if rule_type == "concatenate":
                    columns = rule.get("columns", [])
                    separator = rule.get("separator", " ")
                    
                    values = [str(row_data.get(col, "")) for col in columns]
                    replacements_dict[placeholder] = separator.join(values)
                
                # --- Lógica Condicional ---
                elif rule_type == "conditional_map":
                    on_column = rule.get("on_column")
                    value_map = rule.get("map", {})
                    
                    # Obtener el valor de la celda que decide
                    key_value = str(row_data.get(on_column, "")).upper() # Normalizar a mayúsculas
                    
                    # Normalizar el mapa a mayúsculas
                    safe_map = {str(k).upper(): v for k, v in value_map.items()}

                    if key_value in safe_map:
                        replacements_dict[placeholder] = safe_map[key_value]
                    else:
                        replacements_dict[placeholder] = safe_map.get("DEFAULT", "") # Usar default
                        
            except Exception as e:
                print(f"❌ Error procesando regla calculada para '{placeholder}': {e}")
                replacements_dict[placeholder] = "[ERROR DE REGLA]"

    return replacements_dict

# -------------------------------------------------------------
# -------------------[   HELPER: FORMATTING   ]----------------
# -------------------------------------------------------------

def _apply_format(value: str, format_type: str) -> str:
    """
    Aplica formato de texto a un valor.
    
    Args:
        value: El texto a formatear
        format_type: "MAYUSCULAS", "MINUSCULAS", "TIPO_FRASE", o None
    
    Returns:
        El valor formateado
    """
    if not format_type:
        return value
    
    format_type = format_type.upper()
    
    if format_type == "MAYUSCULAS":
        return value.upper()
    elif format_type == "MINUSCULAS":
        return value.lower()
    elif format_type == "TIPO_FRASE":
        # Primera letra mayúscula, resto minúsculas
        return value.capitalize()
    else:
        print(f"⚠️ Formato desconocido '{format_type}'. Usando valor sin formato.")
        return value

def _sanitize_filename(filename: str) -> str:
    """
    Elimina caracteres inválidos para nombres de archivo en Windows.
    Mantiene los separadores de ruta (\ y /).
    """
    # Reemplazar caracteres prohibidos pero NO los separadores de ruta
    invalid_chars = r'[*?:"<>|]'
    return re.sub(invalid_chars, '_', filename)

def _process_pattern_with_columns(
    pattern_config: Dict[str, Any],
    row_data: Dict[str, Any]
) -> str:
    """
    Procesa un patrón con columnas formateadas usando la sintaxis {[COLUMNA]}.
    
    Args:
        pattern_config: Dict con "template" y "columns"
            - template: String con placeholders {[NOMBRE_COLUMNA]}
            - columns: Lista de dicts con {"name": str, "format": str (opcional)}
        row_data: Datos de la fila actual
    
    Returns:
        El patrón con los valores sustituidos y formateados
    """
    template = pattern_config.get("template", "")
    columns_config = pattern_config.get("columns", [])
    
    # Crear mapa de columna -> formato
    format_map = {}
    for col_config in columns_config:
        col_name = col_config.get("name")
        col_format = col_config.get("format")
        if col_name:
            format_map[col_name] = col_format
    
    # Encontrar todos los placeholders {[COLUMNA]}
    pattern = r"\{\[([^\]]+)\]\}"
    matches = re.finditer(pattern, template)
    
    result = template
    processed_replacements = {}  # Para evitar reemplazos duplicados
    
    for match in matches:
        full_match = match.group(0)  # {[COLUMNA]}
        col_name = match.group(1)    # COLUMNA
        
        # Evitar procesar el mismo placeholder múltiples veces
        if full_match in processed_replacements:
            continue
        
        # Obtener el valor de la columna
        cell_value = row_data.get(col_name)
        
        if cell_value is None:
            print(f"⚠️ Advertencia: Columna '{col_name}' no encontrada en datos. Usando string vacío.")
            value = ""
        else:
            value = str(cell_value)
        
        # Aplicar formato si existe
        format_type = format_map.get(col_name)
        if format_type:
            value = _apply_format(value, format_type)
        
        # Sanitizar el valor (eliminar caracteres inválidos)
        value = _sanitize_filename(value)
        
        processed_replacements[full_match] = value
    
    # Realizar todos los reemplazos
    for placeholder, value in processed_replacements.items():
        result = result.replace(placeholder, value)
    
    return result

def _build_output_path(
    folder_config: Dict[str, Any],
    filename_config: Dict[str, Any],
    base_directory: str,
    row_data: Dict[str, Any]
) -> str:
    """
    Construye la ruta completa de salida (carpeta + archivo).
    
    Args:
        folder_config: Configuración del patrón de carpeta
        filename_config: Configuración del patrón de archivo
        base_directory: Directorio base donde se creará la estructura
        row_data: Datos de la fila actual
    
    Returns:
        Ruta relativa completa (carpeta\subcarpeta\archivo.docx)
    """
    try:
        # Procesar el patrón de carpeta
        folder_path = _process_pattern_with_columns(folder_config, row_data)
        
        # Procesar el patrón de archivo
        filename = _process_pattern_with_columns(filename_config, row_data)
        
        # Construir la ruta completa
        if folder_path:
            # Normalizar separadores según el OS
            folder_path = folder_path.replace("/", os.sep).replace("\\", os.sep)
            full_path = os.path.join(folder_path, filename)
        else:
            full_path = filename
        
        return full_path
        
    except Exception as e:
        print(f"❌ Error construyendo ruta de salida: {e}")
        row_index = row_data.get("row_index", "000")
        return f"fallback_error_fila_{row_index}.docx"

# -------------------------------------------------------------
# -------------------[   MAIN ORCHESTRATOR   ]-----------------
# -------------------------------------------------------------

def execute_bulk_document_job(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función principal de orquestación.
    
    1. Lee datos de un archivo Excel.
    2. Filtra las filas según 'filter_rules'.
    3. Itera sobre cada fila válida.
    4. Genera un documento Word para cada fila usando una plantilla.
    
    Args:
        config: El diccionario de configuración "maestro" con estructura mejorada:
            - excel_config: Configuración de extracción de datos
            - template_config: Configuración de plantilla Word
            - job_config: Configuración del trabajo con:
                * filter_rules: Reglas de filtrado (opcional)
                * direct_mapping: Mapeo directo de columnas a placeholders
                * computed_mapping: Mapeo calculado con reglas
                * folder_pattern: {"template": str, "columns": [...]}
                * filename_pattern: {"template": str, "columns": [...]}
                * overwrite_existing: bool
                
    Returns:
        Un diccionario (JSON) con el log completo del trabajo (job).
    """
    
    # 1. Inicializar el Log de Respuesta
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

        # 3. Extraer Configuraciones
        excel_config = config.get("excel_config")
        template_config = config.get("template_config")
        job_config = config.get("job_config")
        
        if not all([excel_config, template_config, job_config]):
            raise ValueError("Configuración inválida. Faltan 'excel_config', 'template_config' o 'job_config'.")
            
        # --- [ Lógica de Mapeo ] ---
        direct_mapping = job_config.get("direct_mapping", {})
        computed_mapping = job_config.get("computed_mapping", [])
        
        # --- [ Configuración de Patrones (NUEVA ESTRUCTURA) ] ---
        folder_pattern = job_config.get("folder_pattern", {"template": "", "columns": []})
        filename_pattern = job_config.get("filename_pattern", {"template": "documento.docx", "columns": []})
        
        overwrite = job_config.get("overwrite_existing", False)
        
        # --- [ Lógica de Filtro ] ---
        filter_rules = job_config.get("filter_rules")
        
        base_directory = template_config.get("target_directory")
        if not base_directory:
            raise ValueError("Falta 'target_directory' en template_config.")

        # 4. === PASO 1: LEER DATOS DE EXCEL ===
        print(f"--- Iniciando Trabajo Bulk ---")
        print(f"Paso 1: Extrayendo datos de Excel: {excel_config.get('filePath')}")
        
        row_data_list = get_row_data_sheet(excel_config)
        
        if row_data_list is None:
            raise Exception("Falla al leer datos de Excel. El trabajo no puede continuar.")
        
        if not row_data_list:
            print("ℹ️ No se encontraron filas en el rango especificado. Trabajo finalizado.")
            job_summary["status"] = "complete_success"
            return {"job_summary": job_summary, "job_results": []}

        print(f"✓ Paso 1 Exitoso: {len(row_data_list)} filas extraídas.")
        print(f"Paso 2: Iniciando generación de documentos...")
        
        # 5. === PASO 2: BUCLE DE GENERACIÓN DE WORD ===
        success_count = 0
        failure_count = 0
        skipped_count = 0
        
        for row_data in row_data_list:
            row_index = row_data.get("row_index", "N/A")
            generation_log = {}
            relative_path = "N/A"
            status = "pending"
            full_target_path = None
            
            try:
                # a. === Lógica de Filtro ===
                if filter_rules:
                    if not _evaluate_row(row_data, filter_rules):
                        skipped_count += 1
                        status = "skipped"
                        raise Exception("La fila no cumplió con las 'filter_rules'.")
                
                # b. Mapear datos para reemplazos en Word
                replacements_dict = _build_replacements(row_data, direct_mapping, computed_mapping)
                
                # c. Construir ruta de salida (carpeta + archivo) usando la NUEVA lógica
                relative_path = _build_output_path(
                    folder_pattern,
                    filename_pattern,
                    base_directory,
                    row_data
                )
                
                # d. Construir la configuración para esta fila
                word_config = template_config.copy()
                word_config["target_filename"] = relative_path
                word_config["replacements"] = replacements_dict
                word_config["overwrite"] = overwrite
                
                # e. [Validación] Chequear 'overwrite'
                full_target_path = Path(base_directory) / relative_path
                if full_target_path.exists() and not overwrite:
                    raise FileExistsError(f"El archivo '{relative_path}' ya existe y 'overwrite_existing' es False.")

                # f. Llamar al generador de Word
                generation_log = generate_document_from_template(word_config)
                
                if generation_log.get("success"):
                    success_count += 1
                    status = "success"
                else:
                    failure_count += 1
                    status = "failure"
                    
            except Exception as e:
                # Capturar errores (Filtro, FileExistsError, etc.)
                if status == "pending":  # Si no fue omitido, es una falla
                    failure_count += 1
                    status = "failure"
                
                generation_log = {
                    "success": False,
                    "target_path": str(full_target_path) if full_target_path else None,
                    "error": f"Error del Orquestador (Fila {row_index}): {e}",
                    "details": None
                }
            
            # g. Registrar el resultado de esta fila
            job_results.append({
                "row_index": row_index,
                "input_data": row_data,
                "filename_generated": relative_path,
                "status": status,
                "output_log": generation_log
            })

        # 6. === PASO 3: FINALIZAR REPORTE ===
        job_summary["total_rows_processed"] = len(row_data_list)
        job_summary["success_count"] = success_count
        job_summary["failure_count"] = failure_count
        job_summary["total_skipped"] = skipped_count
        
        if failure_count == 0 and skipped_count == 0:
            job_summary["status"] = "complete_success"
        elif success_count > 0:
            job_summary["status"] = "partial_success"
        elif skipped_count == len(row_data_list):
            job_summary["status"] = "skipped_all"
        else:
            job_summary["status"] = "total_failure"
            
        print(f"--- Trabajo Bulk Finalizado ---")
        print(f"Resumen: {success_count} exitosos, {failure_count} fallidos, {skipped_count} omitidos.")

    except Exception as e:
        print(f"❌ ERROR CRÍTICO DEL TRABAJO: {e}")
        job_summary["status"] = "total_failure"
        job_summary["error"] = str(e)
        
    return {"job_summary": job_summary, "job_results": job_results}

# --------------------------------------> END [ MAIN ORCHESTRATOR ... ]