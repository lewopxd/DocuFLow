#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: run_BULK_Marcela_Cursos_Cortos_v18_FIXED.py
Created: 2025-12-07
Author: @lewopxd

Description:
Script de generación masiva de actas para Marcela - Cursos Cortos F2
Genera 3 actas por joven (Inicio, Permanencia, Finalización)
con soporte de imágenes, texto personalizado y búsqueda dual de cronogramas.

v18: CORRECCIÓN COMPLETA - Búsqueda dual de cronogramas funcional
"""

import sys
import unicodedata
from pathlib import Path

# --- [ INICIO: AJUSTE DE PYTHONPATH ] ---
try:
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent 
    src_path = project_root / 'src'

    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        
    print(f"✓ Ruta 'src' añadida a sys.path: {src_path}")
        
except NameError:
    print("⚠️ Advertencia: No se pudo ajustar el sys.path automáticamente.")
    pass
# --- [ FIN: AJUSTE DE PYTHONPATH ] ---

try:
    from assembler.orchestrator import execute_bulk_document_job
    from core.ms_word.media_document_assembler import assemble_document_with_media
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from datetime import datetime
except ImportError as e:
    print(f"❌ CRITICAL: No se pudieron importar los módulos del Core.")
    print(f"   Asegúrate de que la carpeta 'src' está en el PYTHONPATH.")
    print(f"   Error: {e}")
    sys.exit(1)

# -------------------------------------------------------------
# -------------------[  CONFIGURACIÓN GLOBAL  ]----------------
# -------------------------------------------------------------

EXCEL_FILE_PATH = r"C:\Users\Admin\Desktop\PLAYGROUND_7\F2 CURSOS CORTOS\DB_C1F2_MARCELA.xlsx"
BASE_TEMPLATE_PATH = Path(r"C:\Users\Admin\Desktop\PLAYGROUND_7\F2 CURSOS CORTOS\plantillas")
BASE_IMAGES_PATH = Path(r"C:\Users\Admin\Documents\MARCELA SDIS\JÓVENES JCO COHORTE 1 V2\JÓVENES JCO COHORTE 1 V2\JÓVENES JCO COHORTE 1 - V2")
BASE_OUTPUT_PATH = Path(r"C:\Users\Admin\Desktop\PLAYGROUND_7\F2 CURSOS CORTOS\OUTPUT\CERTIFICADOS")

# Ruta de cronogramas compartidos
CRONOGRAMAS_SHARED_PATH = Path(r"C:\Users\Admin\Desktop\PLAYGROUND_7\F2 CURSOS CORTOS\CRONOGRAMAS")

# Configuración de hoja Excel
EXCEL_CONFIG = {
    "sheet": "COHORTE 1",
    "table": "Tabla_1",
    "range_config": {"type": "multiple_row", "data": "2-14"}
}

# Política de layout para imágenes
IMAGE_LAYOUT_POLICY = {
    "width": "auto",
    "height": "auto",
    "alignment": "CENTER",
    "allow_upscale": False,
    "orientation_match_scale": 0.85
}

# -------------------------------------------------------------
# -------------------[  FUNCIONES AUXILIARES  ]----------------
# -------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """
    Normaliza un nombre para búsqueda de carpetas y archivos:
    - Elimina tildes
    - Convierte a minúsculas
    - Elimina espacios extra
    - Elimina caracteres prohibidos en sistema de archivos (:, ., <, >, ", /, \\, |, ?, *)
    - Trim
    """
    if not name:
        return ""
    
    # Eliminar tildes
    normalized = unicodedata.normalize('NFKD', name)
    normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')
    
    # Lowercase
    normalized = normalized.lower()
    
    # Eliminar caracteres prohibidos explícitos (solicitado: ':' y '.') 
    # más los reservados del sistema de archivos Windows
    forbidden_chars = [':', '.', '<', '>', '"', '/', '\\', '|', '?', '*']
    for char in forbidden_chars:
        normalized = normalized.replace(char, "")
    
    # Limpiar espacios extra (por si quedaron huecos tras borrar símbolos)
    normalized = ' '.join(normalized.split())
    
    return normalized.strip()



def _find_image_with_fallback(base_images_path: Path, nombres: str, apellidos: str, image_name: str, debug: bool = False) -> str:
    """
    Busca una imagen con múltiples extensiones en la carpeta normalizada del joven.
    """
    # Construir nombre normalizado de carpeta
    full_name = f"{nombres} {apellidos}"
    normalized_folder = _normalize_name(full_name)
    
    # Probar múltiples variantes de carpeta (normalizada, uppercase, original)
    folder_variants = [
        normalized_folder,
        normalized_folder.upper(),
        full_name.upper().strip(),
        full_name.strip()
    ]
    
    # Extensiones a probar
    extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    
    # Buscar en cada variante de carpeta
    for folder_name in folder_variants:
        folder_path = base_images_path / folder_name / "F2 - CURSOS CORTOS" / "SOPORTES"
        
        if not folder_path.exists():
            continue
            
        if debug:
            print(f"    🔍 Buscando en: {folder_path}")
        
        # Probar cada extensión
        for ext in extensions:
            image_path = folder_path / f"{image_name}{ext}"
            if image_path.exists():
                if debug:
                    print(f"    ✅ Imagen encontrada: {image_path}")
                return str(image_path)
    
    if debug:
        print(f"    ⚠️ Imagen NO encontrada: {image_name} (carpeta: {normalized_folder})")
    
    return None

def _find_cronograma(base_images_path: Path, nombres: str, apellidos: str, curso_reportado: str, debug: bool = False) -> tuple:
    """
    Busca el cronograma con lógica especial de búsqueda dual:
    1. Primero busca en la carpeta personal del joven: 02_CRONOGRAMA.{ext}
    2. Si no existe, busca en carpeta compartida CRONOGRAMAS con nombre del curso normalizado
    
    Returns:
        tuple: (ruta_imagen, tipo_fuente)
        - ruta_imagen: str con la ruta completa o None
        - tipo_fuente: "Personal" | "Compartido" | None
    """
    # 1. Buscar en carpeta personal del joven (comportamiento estándar)
    personal_path = _find_image_with_fallback(base_images_path, nombres, apellidos, "02_CRONOGRAMA", debug=False)
    
    if personal_path:
        if debug:
            print(f"    ✅ Cronograma encontrado en carpeta personal")
        return personal_path, "Personal"
    
    # 2. FALLBACK: Buscar en carpeta compartida CRONOGRAMAS
    if debug:
        print(f"    🔍 Cronograma no encontrado en carpeta personal, buscando en CRONOGRAMAS compartidos...")
    
    # Normalizar nombre del curso para búsqueda
    curso_normalizado = _normalize_name(curso_reportado)
    
    if debug:
        print(f"       Curso normalizado: '{curso_normalizado}'")
    
    # Extensiones a probar
    extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    
    # Buscar archivo con nombre del curso normalizado
    for ext in extensions:
        cronograma_path = CRONOGRAMAS_SHARED_PATH / f"{curso_normalizado}{ext}"
        if cronograma_path.exists():
            if debug:
                print(f"    ✅ Cronograma compartido encontrado: {cronograma_path}")
            return str(cronograma_path), "Compartido"
    
    # También probar sin normalizar (por si el archivo tiene tildes/mayúsculas)
    curso_original = curso_reportado.strip()
    for ext in extensions:
        cronograma_path = CRONOGRAMAS_SHARED_PATH / f"{curso_original}{ext}"
        if cronograma_path.exists():
            if debug:
                print(f"    ✅ Cronograma compartido encontrado (original): {cronograma_path}")
            return str(cronograma_path), "Compartido"
    
    if debug:
        print(f"    ⚠️ Cronograma NO encontrado (ni personal ni compartido)")
        print(f"       Buscado como: '{curso_normalizado}' en {CRONOGRAMAS_SHARED_PATH}")
    
    return None, None

def _build_image_map_for_acta(acta_num: int, row_data: dict, debug: bool = False):
    """
    Construye el image_map para una acta específica y reporta el estado.
    
    v19 CAMBIO: Ahora usa la política on_missing del image_inserter v6
    - Si la imagen existe: se inserta normalmente
    - Si NO existe: on_missing="REMOVE_PLACEHOLDER" → elimina el placeholder del documento
    
    Returns:
        tuple: (image_map, images_status)
    """
    nombres = row_data.get("NOMBRES", "")
    apellidos = row_data.get("APELLIDOS", "")
    curso_reportado = row_data.get("CURSO REPORTADO SENA", "")
    
    image_map = []
    images_status = {}
    
    # Definir placeholders por acta
    placeholders_by_acta = {
        1: ["01_PANTALLAZO_INSCRIPCION", "01_DETALLE_INSCRIPCION"],
        2: ["02_CRONOGRAMA"],
        3: ["03_CORREO_APROBADO", "03_CERTIFICADO_SENA"]
    }
    
    image_names = placeholders_by_acta.get(acta_num, [])
    
    if debug:
        print(f"  📷 Construyendo image_map para Acta {acta_num}...")
    
    for img_name in image_names:
        placeholder = f"$IMG{{{{{img_name}}}}}"
        
        # ✅ CASO ESPECIAL: CRONOGRAMA con búsqueda dual
        if img_name == "02_CRONOGRAMA":
            image_path, source_type = _find_cronograma(
                BASE_IMAGES_PATH,
                nombres,
                apellidos,
                curso_reportado,
                debug=debug
            )
            
            # ✅ v19 CAMBIO: SIEMPRE agregar al image_map con política on_missing
            if image_path:
                image_map.append({
                    "placeholder": placeholder,
                    "image_path": image_path,
                    "layout_policy": IMAGE_LAYOUT_POLICY.copy(),
                    "on_missing": "REMOVE_PLACEHOLDER"  # SE ELIMINA PARA EL CASO EN QUE PUEDE SER UNO U OTRO
                })
                images_status[img_name] = f"✓ {source_type}"
            else:
                # ✅ NUEVO: Agregar con on_missing="REMOVE_PLACEHOLDER"
                image_map.append({
                    "placeholder": placeholder,
                    "image_path": None,
                    "layout_policy": IMAGE_LAYOUT_POLICY.copy(),
                    "on_missing": "REMOVE_PLACEHOLDER"  # ← Eliminar placeholder del documento
                })
                images_status[img_name] = "✗ No encontrado (será eliminado)"
                if debug:
                    print(f"    ⚠️ ADVERTENCIA: Cronograma no encontrado - Placeholder será ELIMINADO del documento")
        else:
            # Búsqueda normal para otras imágenes
            image_path = _find_image_with_fallback(
                BASE_IMAGES_PATH,
                nombres,
                apellidos,
                img_name,
                debug=debug
            )
            
            # ✅ v19 CAMBIO: SIEMPRE agregar al image_map con política on_missing
            if image_path:
                image_map.append({
                    "placeholder": placeholder,
                    "image_path": image_path,
                    "layout_policy": IMAGE_LAYOUT_POLICY.copy(),
                    "on_missing": "KEEP_PLACEHOLDER"  # No debería fallar, pero por seguridad
                })
                images_status[img_name] = "✓ Encontrada"
            else:
                # ✅ NUEVO: Agregar con on_missing="REMOVE_PLACEHOLDER"
                image_map.append({
                    "placeholder": placeholder,
                    "image_path": None,
                    "layout_policy": IMAGE_LAYOUT_POLICY.copy(),
                    "on_missing": "REMOVE_PLACEHOLDER"  # ← Eliminar placeholder del documento
                })
                images_status[img_name] = "✗ No encontrada (será eliminado)"
                if debug:
                    print(f"    ⚠️ ADVERTENCIA: Imagen '{img_name}' no encontrada - Placeholder será ELIMINADO del documento")
    
    return image_map, images_status


def _create_base_config_for_row(row_data: dict, target_dir: Path, debug: bool = False) -> dict:
    """
    Crea la configuración base común para todas las actas de una fila.
    """
    # Construir diccionario de reemplazos
    nombres = row_data.get("NOMBRES", "")
    apellidos = row_data.get("APELLIDOS", "")
    
    # Concatenar y limpiar nombre completo
    nombre_completo = f"{nombres} {apellidos}"
    nombre_completo = ' '.join(nombre_completo.split())
    nombre_completo = nombre_completo.strip().upper()
    
    # EL/LA normalizado
    el_la = row_data.get("EL/LA", "").strip().lower()
    
    replacements = {
        "{{NOMBRE_JOVEN}}": nombre_completo,
        "{{EL/LA}}": el_la,
        "{{TIPO_DOCUMENTO}}": str(row_data.get("TIPO DE DOCUMENTO", "")).strip(),
        "{{NUM_DOCUMENTO}}": str(row_data.get("NUM_DOCUMENTO", "")).strip(),
        "{{NOMBRE_CURSO}}": str(row_data.get("CURSO REPORTADO SENA", "")).strip(),
        "{{APRENDIZAJE}}": str(row_data.get("APRENDIZAJE", "")).strip()
    }
    
    return {
        "replacements": replacements,
        "target_directory": str(target_dir),
        "clear_highlight": True,
        "overwrite": True,
        "author": "Angie Marcela Fierro",
        "last_modified_by": "Angie Marcela Fierro",
        "on_missing_data": "REPLACE_EMPTY"
    }

# -------------------------------------------------------------
# -------------------[  GENERADORES DE ACTAS  ]-----------------
# -------------------------------------------------------------

def generate_acta_1_inicio(row_data: dict, target_dir: Path, debug: bool = False) -> dict:
    """Genera ACTA 1 - INICIO RUTA"""
    
    nombres = row_data.get("NOMBRES", "")
    apellidos = row_data.get("APELLIDOS", "")
    
    if debug:
        print(f"\n  {'='*60}")
        print(f"  ACTA 1 - INICIO RUTA: {nombres} {apellidos}")
        print(f"  {'='*60}")
    
    template_path = BASE_TEMPLATE_PATH / "ACTA 1 - INICIO RUTA.docx"
    
    if not template_path.exists():
        error_msg = f"Plantilla no encontrada: {template_path}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "images_status": {},
            "placeholders_found": "0/6"
        }
    
    base_config = _create_base_config_for_row(row_data, target_dir, debug)
    base_config["source_path"] = str(template_path)
    
    image_map, images_status = _build_image_map_for_acta(1, row_data, debug)
    
    nombres_upper = nombres.strip().upper()
    apellidos_upper = apellidos.strip().upper()
    output_filename = f"ACTA 1 - INICIO RUTA - {nombres_upper} {apellidos_upper}.docx"
    
    full_target_path = target_dir / output_filename
    
    assembler_config = {
        "source_path": str(template_path),
        "target_path": str(full_target_path),
        "image_map": image_map,
        "pdf_map": [],
        "overwrite": True,
        "debug": debug
    }
    
    if debug:
        print(f"  🎯 Archivo salida: {output_filename}")
        print(f"  📝 Reemplazos: {len(base_config['replacements'])}")
        print(f"  🖼️  Imágenes: {len(image_map)}")
    
    try:
        from core.ms_word.replace_holders_text import generate_document_from_template
        
        temp_config = base_config.copy()
        temp_config["target_filename"] = f"temp_{output_filename}"
        
        text_report = generate_document_from_template(temp_config)
        
        if not text_report.get("success"):
            raise Exception(f"Fallo en reemplazo de texto: {text_report.get('error')}")
        
        placeholder_status = text_report.get("details", {}).get("placeholder_status", {})
        total_placeholders = placeholder_status.get("total_requested", 6)
        found_placeholders = placeholder_status.get("total_found", 0)
        placeholders_text = f"{found_placeholders}/{total_placeholders}"
        
        temp_doc_path = Path(temp_config["target_directory"]) / temp_config["target_filename"]
        
        if image_map:
            assembler_config["source_path"] = str(temp_doc_path)
            image_report = assemble_document_with_media(assembler_config)
            
            if temp_doc_path.exists():
                temp_doc_path.unlink()
            
            if not image_report.get("success"):
                raise Exception(f"Fallo en inserción de imágenes: {image_report.get('error')}")
            
            if debug:
                print(f"  ✅ Acta 1 generada exitosamente")
            
            return {
                "success": True,
                "images_status": images_status,
                "placeholders_found": placeholders_text,
                "report": image_report
            }
        else:
            if full_target_path.exists():
                full_target_path.unlink()
            temp_doc_path.rename(full_target_path)
            
            if debug:
                print(f"  ✅ Acta 1 generada exitosamente (sin imágenes)")
            
            return {
                "success": True,
                "images_status": images_status,
                "placeholders_found": placeholders_text,
                "report": text_report
            }
        
    except Exception as e:
        error_msg = f"Error generando Acta 1: {e}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "images_status": images_status,
            "placeholders_found": "0/6"
        }

def generate_acta_2_permanencia(row_data: dict, target_dir: Path, debug: bool = False) -> dict:
    """Genera ACTA 2 - PERMANENCIA"""
    
    nombres = row_data.get("NOMBRES", "")
    apellidos = row_data.get("APELLIDOS", "")
    
    if debug:
        print(f"\n  {'='*60}")
        print(f"  ACTA 2 - PERMANENCIA: {nombres} {apellidos}")
        print(f"  {'='*60}")
    
    template_path = BASE_TEMPLATE_PATH / "ACTA 2 - PERMANENCIA.docx"
    
    if not template_path.exists():
        error_msg = f"Plantilla no encontrada: {template_path}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "images_status": {},
            "placeholders_found": "0/6"
        }
    
    base_config = _create_base_config_for_row(row_data, target_dir, debug)
    base_config["source_path"] = str(template_path)
    
    image_map, images_status = _build_image_map_for_acta(2, row_data, debug)
    
    nombres_upper = nombres.strip().upper()
    apellidos_upper = apellidos.strip().upper()
    output_filename = f"ACTA 2 - PERMANENCIA - {nombres_upper} {apellidos_upper}.docx"
    
    full_target_path = target_dir / output_filename
    
    assembler_config = {
        "source_path": str(template_path),
        "target_path": str(full_target_path),
        "image_map": image_map,
        "pdf_map": [],
        "overwrite": True,
        "debug": debug
    }
    
    if debug:
        print(f"  🎯 Archivo salida: {output_filename}")
        print(f"  📝 Reemplazos: {len(base_config['replacements'])}")
        print(f"  🖼️  Imágenes: {len(image_map)}")
    
    try:
        from core.ms_word.replace_holders_text import generate_document_from_template
        
        temp_config = base_config.copy()
        temp_config["target_filename"] = f"temp_{output_filename}"
        
        text_report = generate_document_from_template(temp_config)
        
        if not text_report.get("success"):
            raise Exception(f"Fallo en reemplazo de texto: {text_report.get('error')}")
        
        placeholder_status = text_report.get("details", {}).get("placeholder_status", {})
        total_placeholders = placeholder_status.get("total_requested", 6)
        found_placeholders = placeholder_status.get("total_found", 0)
        placeholders_text = f"{found_placeholders}/{total_placeholders}"
        
        temp_doc_path = Path(temp_config["target_directory"]) / temp_config["target_filename"]
        
        if image_map:
            assembler_config["source_path"] = str(temp_doc_path)
            image_report = assemble_document_with_media(assembler_config)
            
            if temp_doc_path.exists():
                temp_doc_path.unlink()
            
            if not image_report.get("success"):
                raise Exception(f"Fallo en inserción de imágenes: {image_report.get('error')}")
            
            if debug:
                print(f"  ✅ Acta 2 generada exitosamente")
            
            return {
                "success": True,
                "images_status": images_status,
                "placeholders_found": placeholders_text,
                "report": image_report
            }
        else:
            if full_target_path.exists():
                full_target_path.unlink()
            temp_doc_path.rename(full_target_path)
            
            if debug:
                print(f"  ✅ Acta 2 generada exitosamente (sin imágenes)")
            
            return {
                "success": True,
                "images_status": images_status,
                "placeholders_found": placeholders_text,
                "report": text_report
            }
        
    except Exception as e:
        error_msg = f"Error generando Acta 2: {e}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "images_status": images_status,
            "placeholders_found": "0/6"
        }

def generate_acta_3_finalizacion(row_data: dict, target_dir: Path, debug: bool = False) -> dict:
    """Genera ACTA 3 - FINALIZACIÓN"""
    
    nombres = row_data.get("NOMBRES", "")
    apellidos = row_data.get("APELLIDOS", "")
    
    if debug:
        print(f"\n  {'='*60}")
        print(f"  ACTA 3 - FINALIZACIÓN: {nombres} {apellidos}")
        print(f"  {'='*60}")
    
    template_path = BASE_TEMPLATE_PATH / "ACTA 3 - FINALIZACION.docx"
    
    if not template_path.exists():
        error_msg = f"Plantilla no encontrada: {template_path}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "images_status": {},
            "placeholders_found": "0/6"
        }
    
    base_config = _create_base_config_for_row(row_data, target_dir, debug)
    base_config["source_path"] = str(template_path)
    
    image_map, images_status = _build_image_map_for_acta(3, row_data, debug)
    
    nombres_upper = nombres.strip().upper()
    apellidos_upper = apellidos.strip().upper()
    output_filename = f"ACTA 3 - FINALIZACION - {nombres_upper} {apellidos_upper}.docx"
    
    full_target_path = target_dir / output_filename
    
    assembler_config = {
        "source_path": str(template_path),
        "target_path": str(full_target_path),
        "image_map": image_map,
        "pdf_map": [],
        "overwrite": True,
        "debug": debug
    }
    
    if debug:
        print(f"  🎯 Archivo salida: {output_filename}")
        print(f"  📝 Reemplazos: {len(base_config['replacements'])}")
        print(f"  🖼️  Imágenes: {len(image_map)}")
    
    try:
        from core.ms_word.replace_holders_text import generate_document_from_template
        
        temp_config = base_config.copy()
        temp_config["target_filename"] = f"temp_{output_filename}"
        
        text_report = generate_document_from_template(temp_config)
        
        if not text_report.get("success"):
            raise Exception(f"Fallo en reemplazo de texto: {text_report.get('error')}")
        
        placeholder_status = text_report.get("details", {}).get("placeholder_status", {})
        total_placeholders = placeholder_status.get("total_requested", 6)
        found_placeholders = placeholder_status.get("total_found", 0)
        placeholders_text = f"{found_placeholders}/{total_placeholders}"
        
        temp_doc_path = Path(temp_config["target_directory"]) / temp_config["target_filename"]
        
        if image_map:
            assembler_config["source_path"] = str(temp_doc_path)
            image_report = assemble_document_with_media(assembler_config)
            
            if temp_doc_path.exists():
                temp_doc_path.unlink()
            
            if not image_report.get("success"):
                raise Exception(f"Fallo en inserción de imágenes: {image_report.get('error')}")
            
            if debug:
                print(f"  ✅ Acta 3 generada exitosamente")
            
            return {
                "success": True,
                "images_status": images_status,
                "placeholders_found": placeholders_text,
                "report": image_report
            }
        else:
            if full_target_path.exists():
                full_target_path.unlink()
            temp_doc_path.rename(full_target_path)
            
            if debug:
                print(f"  ✅ Acta 3 generada exitosamente (sin imágenes)")
            
            return {
                "success": True,
                "images_status": images_status,
                "placeholders_found": placeholders_text,
                "report": text_report
            }
        
    except Exception as e:
        error_msg = f"Error generando Acta 3: {e}"
        print(f"  ❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "images_status": images_status,
            "placeholders_found": "0/6"
        }

# -------------------------------------------------------------
# -------------------[  GENERADOR DE REPORTE  ]-----------------
# -------------------------------------------------------------

def generate_excel_report(report_data: list, output_path: Path):
    """Genera un archivo Excel con el reporte detallado del proceso bulk."""
    print(f"\n📊 Generando reporte Excel...")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Bulk"
    
    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Encabezados
    headers = [
        "Fila Excel", "Nombres", "Apellidos", "Reporte SENA",
        "Acta 1 Creada", "Acta 1 - Placeholders", "Acta 1 - Imagen 1", "Acta 1 - Imagen 2", "Acta 1 - Estado",
        "Acta 2 Creada", "Acta 2 - Placeholders", "Acta 2 - Cronograma", "Acta 2 - Estado",
        "Acta 3 Creada", "Acta 3 - Placeholders", "Acta 3 - Imagen 1", "Acta 3 - Imagen 2", "Acta 3 - Estado",
        "Estado Final", "Observaciones"
    ]
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
    
    # Datos
    for row_num, data in enumerate(report_data, 2):
        ws.cell(row=row_num, column=1, value=data.get("fila_excel", "N/A"))
        ws.cell(row=row_num, column=2, value=data.get("nombres", ""))
        ws.cell(row=row_num, column=3, value=data.get("apellidos", ""))
        ws.cell(row=row_num, column=4, value=data.get("reporte_sena", ""))
        
        ws.cell(row=row_num, column=5, value=data.get("acta1_creada", "NO"))
        ws.cell(row=row_num, column=6, value=data.get("acta1_placeholders", "0/6"))
        ws.cell(row=row_num, column=7, value=data.get("acta1_img1", "✗"))
        ws.cell(row=row_num, column=8, value=data.get("acta1_img2", "✗"))
        ws.cell(row=row_num, column=9, value=data.get("acta1_estado", ""))
        
        ws.cell(row=row_num, column=10, value=data.get("acta2_creada", "NO"))
        ws.cell(row=row_num, column=11, value=data.get("acta2_placeholders", "0/6"))
        ws.cell(row=row_num, column=12, value=data.get("acta2_cronograma", "✗"))
        ws.cell(row=row_num, column=13, value=data.get("acta2_estado", ""))
        
        ws.cell(row=row_num, column=14, value=data.get("acta3_creada", "NO"))
        ws.cell(row=row_num, column=15, value=data.get("acta3_placeholders", "0/6"))
        ws.cell(row=row_num, column=16, value=data.get("acta3_img1", "✗"))
        ws.cell(row=row_num, column=17, value=data.get("acta3_img2", "✗"))
        ws.cell(row=row_num, column=18, value=data.get("acta3_estado", ""))
        
        estado_final = data.get("estado_final", "❌ ERROR")
        cell = ws.cell(row=row_num, column=19, value=estado_final)
        
        if "✅" in estado_final:
            cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        elif "⚠️" in estado_final:
            cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        else:
            cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        
        ws.cell(row=row_num, column=20, value=data.get("observaciones", ""))
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"reporte_bulk_{timestamp}.xlsx"
    report_path = output_path / report_filename
    
    wb.save(report_path)
    print(f"✅ Reporte generado: {report_path}")
    
    return report_path

# -------------------------------------------------------------
# -------------------[  EJECUCIÓN PRINCIPAL  ]-----------------
# -------------------------------------------------------------

if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║    SCRIPT BULK - MARCELA CURSOS CORTOS v18 (FIXED)       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"\nFuente Excel: {EXCEL_FILE_PATH}")
    print(f"Directorio Salida: {BASE_OUTPUT_PATH}")
    print(f"Cronogramas Compartidos: {CRONOGRAMAS_SHARED_PATH}")
    print(f"Rango: Filas {EXCEL_CONFIG['range_config']['data']}")
    
    BASE_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    total_jóvenes = 0
    total_actas_success = 0
    total_actas_failed = 0
    report_data = []
    
    try:
        from core.data_sheet.data_sheet_parser import get_row_data_sheet
        
        excel_read_config = {
            "filePath": EXCEL_FILE_PATH,
            "sheetName": EXCEL_CONFIG["sheet"],
            "tableName": EXCEL_CONFIG["table"],
            "rangeConfig": EXCEL_CONFIG["range_config"],
            "columns": [
                "NOMBRES", "APELLIDOS", "EL/LA", "TIPO DE DOCUMENTO",
                "NUM_DOCUMENTO", "CURSO REPORTADO SENA", "APRENDIZAJE", "REPORTE SENA"
            ]
        }
        
        print(f"\n📊 Leyendo datos del Excel...")
        row_data_list = get_row_data_sheet(excel_read_config)
        
        if not row_data_list:
            print("❌ No se pudieron leer datos del Excel.")
            sys.exit(1)
        
        print(f"✓ {len(row_data_list)} filas leídas del Excel")
        
        filtered_rows = [
            row for row in row_data_list
            if str(row.get("REPORTE SENA", "")).strip().upper() == "CERTIFICADO"
        ]
        
        print(f"✓ {len(filtered_rows)} filas filtradas (REPORTE SENA = 'CERTIFICADO')")
        
        if not filtered_rows:
            print("⚠️ No hay filas que cumplan con el filtro.")
            sys.exit(0)
        
        for row_data in filtered_rows:
            total_jóvenes += 1
            row_index = row_data.get("row_index", "N/A")
            nombres = row_data.get("NOMBRES", "")
            apellidos = row_data.get("APELLIDOS", "")
            reporte_sena = row_data.get("REPORTE SENA", "")
            
            print(f"\n{'='*70}")
            print(f"PROCESANDO JOVEN {total_jóvenes}/{len(filtered_rows)}: {nombres} {apellidos} (Fila {row_index})")
            print(f"{'='*70}")
            
            nombres_upper = nombres.strip().upper()
            apellidos_upper = apellidos.strip().upper()
            nombres_upper = ' '.join(nombres_upper.split())
            apellidos_upper = ' '.join(apellidos_upper.split())
            
            joven_folder_name = f"{nombres_upper} {apellidos_upper}"
            joven_output_dir = BASE_OUTPUT_PATH / joven_folder_name
            joven_output_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Carpeta de salida: {joven_folder_name}")
            
            joven_report = {
                "fila_excel": row_index,
                "nombres": nombres,
                "apellidos": apellidos,
                "reporte_sena": reporte_sena,
                "acta1_creada": "NO",
                "acta1_placeholders": "0/6",
                "acta1_img1": "✗",
                "acta1_img2": "✗",
                "acta1_estado": "",
                "acta2_creada": "NO",
                "acta2_placeholders": "0/6",
                "acta2_cronograma": "✗",
                "acta2_estado": "",
                "acta3_creada": "NO",
                "acta3_placeholders": "0/6",
                "acta3_img1": "✗",
                "acta3_img2": "✗",
                "acta3_estado": "",
                "estado_final": "❌ ERROR",
                "observaciones": ""
            }
            
            actas_creadas = 0
            alertas = []
            
            actas = [
                ("Acta 1", generate_acta_1_inicio, 1),
                ("Acta 2", generate_acta_2_permanencia, 2),
                ("Acta 3", generate_acta_3_finalizacion, 3)
            ]
            
            for acta_name, generator_func, acta_num in actas:
                try:
                    report = generator_func(row_data, joven_output_dir, debug=True)
                    
                    if report.get("success"):
                        total_actas_success += 1
                        actas_creadas += 1
                        print(f"  ✅ {acta_name} generada exitosamente")
                        
                        images_status = report.get("images_status", {})
                        placeholders_found = report.get("placeholders_found", "0/6")
                        
                        if acta_num == 1:
                            joven_report["acta1_creada"] = "SI"
                            joven_report["acta1_placeholders"] = placeholders_found
                            joven_report["acta1_img1"] = images_status.get("01_PANTALLAZO_INSCRIPCION", "✗")
                            joven_report["acta1_img2"] = images_status.get("01_DETALLE_INSCRIPCION", "✗")
                            
                            imgs_found = sum(1 for v in images_status.values() if "✓" in v)
                            if imgs_found == 0:
                                joven_report["acta1_estado"] = "⚠️ Sin imágenes"
                                alertas.append("Acta 1: Sin imágenes")
                            else:
                                joven_report["acta1_estado"] = "✅ OK"
                        
                        elif acta_num == 2:
                            joven_report["acta2_creada"] = "SI"
                            joven_report["acta2_placeholders"] = placeholders_found
                            crono = images_status.get("02_CRONOGRAMA", "✗")
                            joven_report["acta2_cronograma"] = crono
                            
                            if "✗" in crono:
                                joven_report["acta2_estado"] = "❌ FALTA CRONOGRAMA"
                                alertas.append("Acta 2: Cronograma faltante (CRÍTICO)")
                            else:
                                joven_report["acta2_estado"] = f"✅ OK ({crono})"
                        
                        elif acta_num == 3:
                            joven_report["acta3_creada"] = "SI"
                            joven_report["acta3_placeholders"] = placeholders_found
                            joven_report["acta3_img1"] = images_status.get("03_CORREO_APROBADO", "✗")
                            joven_report["acta3_img2"] = images_status.get("03_CERTIFICADO_SENA", "✗")
                            
                            imgs_found = sum(1 for v in images_status.values() if "✓" in v)
                            if imgs_found == 0:
                                joven_report["acta3_estado"] = "⚠️ Sin imágenes"
                                alertas.append("Acta 3: Sin imágenes")
                            else:
                                joven_report["acta3_estado"] = "✅ OK"
                    else:
                        total_actas_failed += 1
                        error_msg = report.get("error", "Error desconocido")
                        print(f"  ❌ {acta_name} falló: {error_msg}")
                        alertas.append(f"{acta_name}: {error_msg}")
                        
                except Exception as e:
                    total_actas_failed += 1
                    print(f"  ❌ Excepción en {acta_name}: {e}")
                    alertas.append(f"{acta_name}: Excepción - {e}")
            
            if actas_creadas == 3 and not alertas:
                joven_report["estado_final"] = "✅ ÉXITO"
            elif actas_creadas == 3 and alertas:
                joven_report["estado_final"] = "⚠️ ÉXITO CON ALERTAS"
            else:
                joven_report["estado_final"] = "❌ ERROR"
            
            joven_report["observaciones"] = " | ".join(alertas) if alertas else "Ninguna"
            report_data.append(joven_report)
        
        generate_excel_report(report_data, BASE_OUTPUT_PATH)
        
        print(f"\n{'='*70}")
        print("PROCESO FINALIZADO")
        print(f"{'='*70}")
        print(f"📊 ESTADÍSTICAS:")
        print(f"  👥 Jóvenes procesados: {total_jóvenes}")
        print(f"  ✅ Actas exitosas: {total_actas_success}")
        print(f"  ❌ Actas fallidas: {total_actas_failed}")
        print(f"\n📂 Directorio de salida: {BASE_OUTPUT_PATH}")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)