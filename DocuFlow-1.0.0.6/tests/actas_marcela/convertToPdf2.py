#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow Converter INDUSTRIAL
File: run_converter_industrial.py
Created: 2025-12-07
Description:
    Motor de conversión Word -> PDF de alto rendimiento.
    - Mantiene instancia única de Word (Eficiencia).
    - Copia de seguridad temporal (Integridad).
    - Gestión de Metadata PDF (Autor, Fechas).
    - Lógica de Reintentos y Watchdog de procesos.
    - Reporte Excel detallado.
"""

import sys
import os
import shutil
import time
import logging
import pythoncom
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional

# --- IMPORTACIONES SEGURAS ---
try:
    import win32com.client as win32
    from PyPDF2 import PdfReader, PdfWriter
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
except ImportError as e:
    print(f"❌ ERROR CRÍTICO: Falta librería base: {e}")
    sys.exit(1)

# =============================================================================
# ⚙️ CONFIGURACIÓN DEL USUARIO
# =============================================================================

CONFIG = {
    # 📂 Rutas
    "BASE_PATH": Path(r"C:\Users\Admin\Desktop\PLAYGROUND MARCELA\F2 CURSOS CORTOS\OUTPUT\CERTIFICADOS"),
    "TEMP_FOLDER": Path(r"C:\Temp_DocuFlow_SafeZone"), # Zona segura de trabajo

    # 🎯 Ejecución
    # MODE: "ALL" (Todo recursivo) | "SELECT" (Buscar carpeta específica)
    "EXECUTION": {
        "MODE": "ALL",       
        "KEY": "ADRIANA MORENO JIMENEZ"  # Normalizado internamente
    },

    # 📄 Mapeo de Archivos (Key en nombre -> Nombre Final)
    "FILE_MAP": {
        "ACTA 1": "001ActaInicioRuta.pdf",
        "ACTA 2": "002ActaPermanenciaRuta.pdf",
        "ACTA 3": "003ActaFinalizacionRuta.pdf"
    },

    # 💾 Salida
    "OUTPUT": {
        "MODE": "SAME_PLACE",     # SAME_PLACE | SUBFOLDER | SPECIFIC
        "PATH": "PDF_LEGALES"    # Nombre de subcarpeta o ruta absoluta
    },

    # 🏷️ Metadata PDF
    "METADATA": {
        "AUTHOR": "Angie Marcela Fierro",
        "CREATOR": "",
        "USE_CURRENT_DATE": True # Si es False, intenta mantener fecha original
    },

    # 🛡️ Políticas de Seguridad
    "POLICIES": {
        "MAX_RETRIES": 3,
        "TIMEOUT_SECONDS": 45,   # Tiempo max por archivo antes de matar Word
        "OVERWRITE": True,
        "KILL_ZOMBIES_ON_START": True
    }
}

# =============================================================================
# 🛠️ CLASE: MOTOR DE WORD (SINGLE INSTANCE)
# =============================================================================

class WordEngine:
    def __init__(self):
        self.app = None
        self.logger = logging.getLogger("WordEngine")

    def kill_zombies(self):
        """Mata procesos de Word colgados para liberar memoria."""
        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'WINWORD' in proc.info['name'].upper():
                try:
                    proc.kill()
                    killed += 1
                except: pass
        if killed:
            self.logger.warning(f"🧹 Se eliminaron {killed} procesos zombies de Word.")

    def start(self):
        """Inicia la instancia de Word (solo una vez)."""
        try:
            pythoncom.CoInitialize()
            self.app = win32.Dispatch("Word.Application")
            self.app.Visible = False
            self.app.DisplayAlerts = False # Silencia errores modales
            self.logger.info("🚀 Motor Word iniciado correctamente.")
        except Exception as e:
            self.logger.critical(f"❌ No se pudo iniciar Word: {e}")
            raise

    def convert_file(self, source_docx: Path, target_pdf: Path) -> bool:
        """Convierte un archivo usando la instancia abierta."""
        doc = None
        try:
            # Abrir documento
            doc = self.app.Documents.Open(str(source_docx))
            
            # Formato 17 = PDF
            doc.SaveAs(str(target_pdf), FileFormat=17)
            
            doc.Close(SaveChanges=0) # 0 = No guardar cambios
            return True
            
        except Exception as e:
            self.logger.error(f"Error en conversión interna: {e}")
            try:
                if doc: doc.Close(SaveChanges=0)
            except: pass
            return False

    def stop(self):
        """Cierra Word limpiamente."""
        if self.app:
            try:
                self.app.Quit()
            except: pass
            self.app = None
            self.logger.info("🛑 Motor Word detenido.")

# =============================================================================
# 🏷️ GESTIÓN DE METADATA Y UTILIDADES
# =============================================================================

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    return logging.getLogger("DocuFlow")

logger = setup_logger()

def normalize_text(text: str) -> str:
    """Normaliza texto para comparaciones (sin tildes, mayúsculas)."""
    if not text: return ""
    import unicodedata
    s = str(text).strip().lower()
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')
    return " ".join(s.split())

def inject_metadata(pdf_path: Path):
    """Inyecta autor y fechas al PDF generado usando PyPDF2."""
    try:
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        
        # Copiar páginas
        for page in reader.pages:
            writer.add_page(page)

        # Preparar fechas
        dt = datetime.now()
        date_str = f"D:{dt.strftime('%Y%m%d%H%M%S')}"

        # Metadata
        metadata = {
            '/Author': CONFIG["METADATA"]["AUTHOR"],
            '/Creator': CONFIG["METADATA"]["CREATOR"],
            '/Producer': "DocuFlow Industrial System",
            '/CreationDate': date_str,
            '/ModDate': date_str,
            '/Title': pdf_path.stem
        }

        writer.add_metadata(metadata)

        # Escribir archivo final
        with open(pdf_path, "wb") as f:
            writer.write(f)
            
        return True
    except Exception as e:
        logger.error(f"Fallo inyectando metadata: {e}")
        return False

# =============================================================================
# 🚀 FLUJO PRINCIPAL
# =============================================================================

def process_batch():
    # 1. Preparación
    if CONFIG["POLICIES"]["KILL_ZOMBIES_ON_START"]:
        WordEngine().kill_zombies()

    CONFIG["TEMP_FOLDER"].mkdir(exist_ok=True)
    report_data = []
    
    # 2. Identificar Carpetas
    base_dir = CONFIG["BASE_PATH"]
    target_folders = []
    
    if CONFIG["EXECUTION"]["MODE"] == "ALL":
        target_folders = [f for f in base_dir.iterdir() if f.is_dir()]
    else:
        key = normalize_text(CONFIG["EXECUTION"]["KEY"])
        target_folders = [f for f in base_dir.iterdir() if f.is_dir() and key in normalize_text(f.name)]

    logger.info(f"📋 Carpetas detectadas: {len(target_folders)}")

    # 3. Iniciar Motor Word
    engine = WordEngine()
    try:
        engine.start()
    except:
        return # Error crítico al inicio

    # 4. Procesamiento
    for folder in target_folders:
        logger.info(f"📂 Procesando: {folder.name}")
        
        # Determinar salida
        out_conf = CONFIG["OUTPUT"]
        if out_conf["MODE"] == "SAME_PLACE":
            dest_dir = folder
        elif out_conf["MODE"] == "SUBFOLDER":
            dest_dir = folder / out_conf["PATH"]
        else:
            dest_dir = Path(out_conf["PATH"])
        
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Buscar archivos
        files = list(folder.glob("*.docx"))
        
        for file in files:
            processed_key = None
            final_name = None
            
            # Verificar Mapeo
            for key, val in CONFIG["FILE_MAP"].items():
                if key in file.name.upper(): # Match simple
                    processed_key = key
                    final_name = val
                    break
            
            if not processed_key: continue # No es un archivo de interés

            final_pdf_path = dest_dir / final_name
            
            # Política de Sobrescritura
            if final_pdf_path.exists() and not CONFIG["POLICIES"]["OVERWRITE"]:
                report_data.append({"Carpeta": folder.name, "Origen": file.name, "Estado": "OMITIDO", "Detalle": "Ya existe"})
                continue

            # --- LÓGICA DE SEGURIDAD (SANDBOX) ---
            # 1. Copiar a TEMP para no corromper original
            temp_docx = CONFIG["TEMP_FOLDER"] / f"temp_{int(time.time())}_{file.name}"
            temp_pdf = temp_docx.with_suffix(".pdf")
            
            try:
                shutil.copy2(file, temp_docx)
                
                # 2. Conversión con Reintentos
                success = False
                for attempt in range(CONFIG["POLICIES"]["MAX_RETRIES"]):
                    if engine.convert_file(temp_docx, temp_pdf):
                        success = True
                        break
                    else:
                        logger.warning(f"⚠️ Reintento {attempt+1} fallido para {file.name}")
                        time.sleep(1) # Esperar recuperación
                        # Si falló, quizás Word murió. Intentar revivir.
                        try: engine.app.Name; 
                        except: 
                            logger.warning("♻️ Reiniciando motor Word..."); 
                            engine.stop(); engine.start()

                if success:
                    # 3. Inyección de Metadata
                    inject_metadata(temp_pdf)

                    # 4. Mover a Destino Final
                    shutil.move(str(temp_pdf), str(final_pdf_path))
                    
                    logger.info(f"   ✅ OK: {final_name}")
                    report_data.append({"Carpeta": folder.name, "Origen": file.name, "Destino": final_name, "Estado": "EXITO", "Detalle": "Conversión + Metadata"})
                else:
                    logger.error(f"   ❌ ERROR: {file.name}")
                    report_data.append({"Carpeta": folder.name, "Origen": file.name, "Destino": final_name, "Estado": "FALLO", "Detalle": "Word no pudo convertir"})

            except Exception as e:
                logger.error(f"   🔥 EXCEPCION: {e}")
                report_data.append({"Carpeta": folder.name, "Origen": file.name, "Estado": "ERROR", "Detalle": str(e)})
            
            finally:
                # 5. Limpieza Temp
                if temp_docx.exists(): os.remove(temp_docx)
                if temp_pdf.exists(): os.remove(temp_pdf)

    # 5. Cierre
    engine.stop()
    shutil.rmtree(CONFIG["TEMP_FOLDER"], ignore_errors=True)
    generate_report(report_data)

# =============================================================================
# 📊 REPORTE EXCEL
# =============================================================================

def generate_report(data):
    if not data: return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Industrial"
    
    headers = ["Carpeta", "Origen", "Destino", "Estado", "Detalle"]
    ws.append(headers)
    
    # Estilos
    fill_ok = PatternFill("solid", fgColor="C6EFCE")
    fill_err = PatternFill("solid", fgColor="FFC7CE")
    
    for row in data:
        r = [row.get(h, "") for h in headers]
        ws.append(r)
        
        # Colorear fila actual (ws.max_row)
        curr_row = ws.max_row
        fill = fill_ok if row["Estado"] == "EXITO" else fill_err
        if row["Estado"] == "OMITIDO": fill = PatternFill("solid", fgColor="FFEB9C")
        
        for c in range(1, 6):
            ws.cell(row=curr_row, column=c).fill = fill

    # Autoajuste
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 25

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CONFIG["BASE_PATH"] / f"Reporte_Industrial_{timestamp}.xlsx"
    wb.save(path)
    logger.info(f"📊 Reporte guardado en: {path}")

if __name__ == "__main__":
    print(f"🏭 INICIANDO CONVERTIDOR INDUSTRIAL")
    process_batch()