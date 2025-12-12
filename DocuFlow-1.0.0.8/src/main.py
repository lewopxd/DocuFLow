"""
============================================
Project: DocuFlow
File: main.py
Created: [YYYY-MM-DD]
Author: @lewopxd

Description:
Main entry point for the DocuFlow application.
Handles splash screen, process isolation, pywebview window creation,
and the Python-JS bridge (BridgeAPI).

This solution uses the native Windows API to precisely control
window geometry and state, bypassing pywebview's DPI scaling bugs.
============================================
"""

# --- IMPORTACIONES GLOBALES LIGERAS ---
import sys
import multiprocessing
import threading
import time
from pathlib import Path
import os

# --- [ INICIO: FIX DE PYTHONPATH ] ---
# Añadir el directorio 'src' (donde está este archivo) al sys.path
# para asegurar que 'from core...' funcione correctamente.
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
# --- [ FIN: FIX DE PYTHONPATH ] ---


# --- [ INICIO: LOGGER INITIALIZATION ] ---
# MUST be imported FIRST before any other core modules
try:
    from core.logger import Logger
    Logger.set_level("DEBUG")
    Logger.enable_colors(True)
    Logger.info("Logger inicializado correctamente")
except ImportError as e:
    # Fallback Logger if import fails
    class Logger:
        @staticmethod
        def debug(msg): Logger.debug(f"DEBUG: {msg}")
        @staticmethod
        def info(msg): Logger.debug(f"INFO: {msg}")
        @staticmethod
        def warn(msg): Logger.debug(f"WARN: {msg}")
        @staticmethod
        def error(msg): Logger.error(f"ERROR: {msg}")
    Logger.debug(f"WARN: No se pudo importar Logger: {e}")
# --- [ FIN: LOGGER INITIALIZATION ] ---

# Importar el sistema de storage desde /core
try:
    from core.file_helpers.storage import AppStorage
except ImportError as e:
    Logger.error(f"CRITICAL: No se pudo importar 'core.file_helpers.storage.AppStorage'.")
    Logger.error(f"   Error: {e}")
    Logger.debug(f"   sys.path: {sys.path}")
    AppStorage = None

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
APP_CONFIG = {
    "devTools_UI": True,
    "unicId_UI": True,
    "enableCache_UI": False
}

# --- [ VARIABLE DE CONTROL DE SESIÓN ] ---
# Controla si la app debe devolver la sesión previa (archivos abiertos) a la UI.
# Poner en False para deshabilitar la restauración de sesión durante el desarrollo.
LOAD_SAVED_SESSION = False
# --- [ FIN DE VARIABLE DE CONTROL ] ---

# --- [ INICIO: ENVIRONMENT VALIDATION ] ---
def _check_conversion_environment():
    """
    Verifica el entorno de conversión al inicio de la app.
    Ejecuta en background para no bloquear el splash screen.
    """
    try:
        from core.utils.environment_validator import EnvironmentValidator
        
        Logger.info("[Startup] Verificando entorno de conversión...")
        status = EnvironmentValidator.check_all()
        
        if status.ms_office_available:
            Logger.info(f"[Startup] ✓ MS Office: {status.ms_office_version}")
        else:
            Logger.debug(f"[Startup] ✗ MS Office: {status.ms_office_error}")
        
        if status.libreoffice_available:
            Logger.info(f"[Startup] ✓ LibreOffice: {status.libreoffice_path}")
        else:
            Logger.debug(f"[Startup] ✗ LibreOffice: {status.libreoffice_error}")
        
        if not status.has_any_converter:
            Logger.warn("[Startup] ⚠ No hay convertidores PDF disponibles")
            Logger.warn("[Startup]   La conversión a PDF no funcionará hasta que se instale")
            Logger.warn("[Startup]   MS Office o LibreOffice")
        else:
            Logger.info(f"[Startup] ✓ Método preferido: {status.preferred_method}")
            
    except ImportError:
        Logger.debug("[Startup] EnvironmentValidator no disponible, omitiendo verificación")
    except Exception as e:
        Logger.debug(f"[Startup] Error en verificación de entorno: {e}")

# Ejecutar verificación en hilo separado para no bloquear
threading.Thread(target=_check_conversion_environment, daemon=True).start()
# --- [ FIN: ENVIRONMENT VALIDATION ] ---

# -------------------------------------------------------------
# -------------------[   SPLASH SCREEN   ]---------------------
# -------------------------------------------------------------

def show_error_dialog(message: str):
    """Muestra un diálogo de error nativo si la app principal falla."""
    import tkinter as tk
    from tkinter import messagebox
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("DocuFlow - Error Fatal", message)
        root.destroy()
    except Exception as e:
        Logger.error(f"Error al mostrar el diálogo de error: {e}")

def create_splash_screen(handshake_event: multiprocessing.Event, main_app_process: multiprocessing.Process):
    """
    Crea y ejecuta el mainloop de tkinter en el HILO PRINCIPAL del Proceso Padre.
    """
    import tkinter as tk
    from tkinter import font as tkFont
    import ctypes

    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    splash_root = tk.Tk()
    splash_root.title("DocuFlow Loader")
    
    BG_COLOR = "#1e1e1e"
    FONT_COLOR = "#cccccc"
    TITLE_FONT = tkFont.Font(family="Segoe UI", size=24, weight="bold")
    SUB_FONT = tkFont.Font(family="Segoe UI", size=12)
    CREDIT_FONT = tkFont.Font(family="Segoe UI", size=8)
    
    splash_root.config(bg=BG_COLOR)
    splash_root.overrideredirect(True)
    
    if sys.platform == "win32":
        splash_root.attributes('-toolwindow', True)
        splash_root.attributes('-alpha', 1.0)
        
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    window_width = 450
    window_height = 220
    x_pos = (screen_width // 2) - (window_width // 2)
    y_pos = (screen_height // 2) - (window_height // 2)
    
    splash_root.geometry(f'{window_width}x{window_height}+{x_pos}+{y_pos}')
    splash_root.update_idletasks()
    
    main_frame = tk.Frame(splash_root, bg=BG_COLOR, width=window_width, height=window_height)
    main_frame.place(x=0, y=0, width=window_width, height=window_height)
    
    logo_label = None
    try:
        # El 'src_dir' ya está definido arriba
        base_path = src_dir
        
        logo_path = base_path / "ui" / "assets" / "images" / "ico-doculfow-transparent.png"
        
        if logo_path.exists():
            original_logo = tk.PhotoImage(file=str(logo_path))
            target_size = 150
            scale_factor = max(original_logo.width() // target_size, original_logo.height() // target_size)
            if scale_factor < 1:
                scale_factor = 1
            logo_photo = original_logo.subsample(scale_factor, scale_factor)
            
            logo_label = tk.Label(main_frame, image=logo_photo, bg=BG_COLOR)
            logo_label.image = logo_photo
            logo_y = (window_height - logo_photo.height()) // 2
            logo_label.place(x=20, y=logo_y)
        else:
            Logger.warn(f"Logo no encontrado en: {logo_path}")
    except Exception as e:
        Logger.error(f"⚠️ Error al cargar el logo: {e}")
    
    text_x = 20 + 150 + 25
    
    title_label = tk.Label(
        main_frame, text="DocuFlow", font=TITLE_FONT, fg=FONT_COLOR, bg=BG_COLOR
    )
    title_label.place(x=text_x, y=65)
    
    loading_label = tk.Label(
        main_frame, text="Loading...", font=SUB_FONT, fg=FONT_COLOR, bg=BG_COLOR
    )
    loading_label.place(x=text_x, y=115)
    
    credit_label = tk.Label(
        main_frame, text="powered by @lewop", font=CREDIT_FONT, fg="#666666", bg=BG_COLOR
    )
    credit_label.place(x=window_width-130, y=window_height-25)
    
    dots_sequence = ["   ", ".  ", ".. ", "..."]
    dots_index = [0]
    
    def animate_dots():
        if not splash_root.winfo_exists():
            return
        loading_label.config(text=f"Loading{dots_sequence[dots_index[0]]}")
        dots_index[0] = (dots_index[0] + 1) % len(dots_sequence)
        splash_root.after(400, animate_dots)
    
    animate_dots()
    
    def check_status():
        if handshake_event.is_set():
            splash_root.destroy()
            return
            
        if not main_app_process.is_alive():
            splash_root.destroy()
            Logger.error("ERROR: El proceso principal (webview) falló al iniciar.")
            show_error_dialog("DocuFlow no pudo iniciarse.\n\n"
                              "El proceso principal falló. Verifique los logs.")
            return

        splash_root.after(100, check_status)

    splash_root.after(100, check_status)
    
    try:
        splash_root.mainloop()
    except Exception as e:
        Logger.debug(f"ℹ️ Splash screen cerrado: {e}")

# --------------------------------------> END [ SPLASH SCREEN ... ]

# -------------------------------------------------------------
# -------------------[   APLICACIÓN WEBVIEW (HIJO)   ]---------
# -------------------------------------------------------------

def start_webview_app(handshake_event: multiprocessing.Event, config: dict):
    """
    Función que inicia la aplicación DocuFlow (pywebview).
    Esta función se ejecuta en el HILO PRINCIPAL del Proceso Hijo.
    """
    
    # --- IMPORTACIONES PESADAS (AISLADAS EN EL HIJO) ---
    import webview
    import ctypes
    from ctypes import wintypes, byref, Structure, POINTER
    import uuid
    import json
    from typing import Dict, Any, Callable, Optional, List
    from datetime import datetime
    
    # Importar el sistema de storage desde /core
    try:
        # Quitado 'src.'
        from core.file_helpers.storage import AppStorage
    except ImportError as e:
        Logger.error(f"CRITICAL (Hijo): No se pudo importar 'core.file_helpers.storage.AppStorage'.")
        Logger.error(f"   Error: {e}")
        AppStorage = None

    # --- [ IMPORTACIÓN DEL PARSER ] ---
    try:
        # Quitado 'src.'
        from core.data_sheet.data_sheet_parser import get_data_sheet_structure
    except ImportError as e:
        Logger.error(f"CRITICAL (Hijo): No se pudo importar 'core.data_sheet.data_sheet_parser.get_data_sheet_structure'.")
        Logger.error(f"   Error: {e}")
        get_data_sheet_structure = None # Fallback para evitar que la app crashee
    # --- [ FIN DE IMPORTACIÓN ] ---

    # --- [ IMPORTACIÓN DEL PROJECT MANAGER ] ---
    try:
        from core.file_helpers.project_manager import get_project_manager
    except ImportError as e:
        Logger.error(f"CRITICAL (Hijo): No se pudo importar 'core.file_helpers.project_manager'.")
        Logger.error(f"   Error: {e}")
        get_project_manager = None
    # --- [ FIN DE IMPORTACIÓN PROJECT MANAGER ] ---

    
    # --- ESTRUCTURAS DE WINDOWS API ---
    class RECT(Structure):
        _fields_ = [
            ('left', ctypes.c_long),
            ('top', ctypes.c_long),
            ('right', ctypes.c_long),
            ('bottom', ctypes.c_long)
        ]
    
    class WINDOWPLACEMENT(Structure):
        _fields_ = [
            ('length', wintypes.UINT),
            ('flags', wintypes.UINT),
            ('showCmd', wintypes.UINT),
            ('ptMinPosition', wintypes.POINT),
            ('ptMaxPosition', wintypes.POINT),
            ('rcNormalPosition', RECT)
        ]
    
    # --- DPI AWARENESS ---
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            Logger.info("Proceso hijo marcado como DPI-Aware (Modo 1)")
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                Logger.info("Proceso hijo marcado como DPI-Aware (Modo 2)")
            except Exception:
                Logger.warn("No se pudo establecer DPI Awareness en el proceso hijo")
    
    storage = None
    if AppStorage is not None:
        storage = AppStorage("DocuFlow")
        
        if not storage.was_closed_properly():
            Logger.warn("La aplicación no se cerró correctamente en la última sesión")
        else:
            Logger.info("Última sesión cerrada correctamente")
        
        storage.mark_improper_close()
    else:
        Logger.error("ERROR: No se pudo instanciar AppStorage. Persistencia deshabilitada.")

    # --- CLASES Y FUNCIONES INTERNAS (SOLO PARA EL HIJO) ---
    
    #-------------------------------------------------------------
    #-------------[   WINDOW API CLASS   ]------------------------
    #-------------------------------------------------------------

    class WindowAPI:
        """
        API interna para manejar el estado de la ventana, interactuando
        directamente con la Windows API para fiabilidad.
        """
        def __init__(self, window, storage_instance: AppStorage):
            self.window = window
            self._is_maximized = False # Estado interno, sincronizado por eventos
            self.storage = storage_instance
            self.hwnd = None # Handle de la ventana, establecido post-creación
            self.first_load_done = False # Flag para detectar F5 refresh
            
        def set_hwnd(self, hwnd):
            """Establece el handle de la ventana después de que esté creada."""
            self.hwnd = hwnd
            Logger.info(f"HWND establecido: {hwnd}")
            
        def minimize(self):
            """Minimiza la ventana."""
            self.window.minimize()
            return True
            
        def maximize(self):
            """Maximiza o restaura la ventana (vía UI)."""
            if self._is_maximized:
                self.window.restore()
            else:
                self.window.maximize()
            return True
        
        def _get_window_state_from_windows(self) -> Dict[str, Any]:
            """
            Obtiene el estado EXACTO de la ventana usando Windows API nativa.
            Esto captura la geometría de restauración correcta incluso si
            la ventana está maximizada.
            """
            if not self.hwnd:
                Logger.warn("HWND no disponible al guardar. Usando valores por defecto.")
                return {
                    'width': 1080, 'height': 600, 'x': None, 'y': None,
                    'maximized': self._is_maximized
                }
            
            try:
                user32 = ctypes.windll.user32
                
                # Obtener WINDOWPLACEMENT
                placement = WINDOWPLACEMENT()
                placement.length = ctypes.sizeof(WINDOWPLACEMENT)
                
                if not user32.GetWindowPlacement(self.hwnd, byref(placement)):
                    raise Exception("GetWindowPlacement falló")
                
                # SW_SHOWMAXIMIZED = 3
                is_maximized = (placement.showCmd == 3)
                
                # rcNormalPosition contiene la geometría de restauración
                rect = placement.rcNormalPosition
                
                # Obtener DPI de la ventana
                dpi = user32.GetDpiForWindow(self.hwnd)
                dpi_scale = dpi / 96.0
                
                # Convertir a coordenadas lógicas
                width = int((rect.right - rect.left) / dpi_scale)
                height = int((rect.bottom - rect.top) / dpi_scale)
                x = int(rect.left / dpi_scale)
                y = int(rect.top / dpi_scale)
                
                state = {
                    'width': width,
                    'height': height,
                    'x': x,
                    'y': y,
                    'maximized': is_maximized
                }
                
                Logger.debug(f"📐 Estado capturado de Windows:")
                Logger.debug(f"   DPI: {dpi} ({int(dpi_scale * 100)}%)")
                Logger.debug(f"   Físico (Restaurado): {rect.right - rect.left}x{rect.bottom - rect.top}")
                Logger.debug(f"   Lógico (Restaurado): {width}x{height} @ ({x}, {y})")
                Logger.debug(f"   Estado Maximizado: {is_maximized}")
                
                return state
                
            except Exception as e:
                Logger.error(f"⚠️ Error obteniendo estado de ventana: {e}")
                import traceback
                traceback.print_exc()
                # Fallback
                return {
                    'width': 1080, 'height': 600, 'x': None, 'y': None,
                    'maximized': self._is_maximized
                }
            
        def close(self, from_event=False):
            """
            Maneja la lógica de guardado y cierre.
            Llamado por el evento 'on_closing' o desde la UI.
            """
            if self.storage:
                try:
                    Logger.debug("💾 Preparando guardado de sesión...")
                    
                    # Esperar un instante para que Windows actualice el estado
                    time.sleep(0.05)
                    
                    # Obtener estado de Windows
                    final_window_state = self._get_window_state_from_windows()
                    
                    Logger.info(f"Guardando estado final: {final_window_state}")

                    # Guardar
                    self.storage.finalize_session_save(final_window_state)
                    
                except Exception as e:
                    Logger.error(f"⚠️ Error al guardar estado: {e}")
                    import traceback
                    traceback.print_exc()
            
            if not from_event:
                self.window.destroy()

    #--------------------------------------> END [ WINDOW API CLASS ... ]

    
    #-------------------------------------------------------------
    #-------------[   BRIDGE API CLASS   ]------------------------
    #-------------------------------------------------------------
    
    class BridgeAPI:
        """
        API interna para la comunicación entre Python y JavaScript.
        """
        def __init__(self, window: webview.Window, handshake_event: multiprocessing.Event, 
                       show_window_callback: Callable, storage_instance: AppStorage, 
                       window_api_instance: WindowAPI):
            
            self.window = window
            self.is_ready = False
            self.handlers: Dict[str, Callable] = {}
            self.handshake_event = handshake_event
            self.show_window = show_window_callback
            self.storage = storage_instance
            self.window_api = window_api_instance
            self._register_default_handlers()
        
        def _register_default_handlers(self):
            """Registra los handlers básicos del sistema"""
            self.register_handler("handshake", self._handle_handshake)
            self.register_handler("ping", self._handle_ping)
            self.register_handler("open_file_dialog", self._handle_open_file_dialog)
            self.register_handler("get_ui_settings", self._handle_get_ui_settings)
            self.register_handler("save_ui_setting", self._handle_save_ui_setting)
            self.register_handler("get_excel_structure", self._handle_get_excel_structure)
            self.register_handler("get_excel_sheet_data", self._handle_get_excel_sheet_data)
            self.register_handler("get_unified_excel_data", self._handle_get_unified_excel_data)
            self.register_handler("get_excel_full_data", self._handle_get_excel_full_data)  # Split API
            # Template parsing handler
            self.register_handler("get_template_placeholders", self._handle_get_template_placeholders)
            # Document viewer handler (sends docx as base64)
            self.register_handler("get_docx_file_data", self._handle_get_docx_file_data)
            # Job control handlers
            self.register_handler("job_cancel", self._handle_job_cancel)
            self.register_handler("job_pause", self._handle_job_pause)
            self.register_handler("job_resume", self._handle_job_resume)
            self.register_handler("job_list_active", self._handle_job_list_active)
            self.register_handler("job_list_resumable", self._handle_job_list_resumable)
            # Word to PDF conversion handlers
            self.register_handler("convert_to_pdf", self._handle_convert_to_pdf)
            self.register_handler("convert_existing_to_pdf", self._handle_convert_existing_to_pdf)
            # Project management handlers
            self.register_handler("get_project_info", self._handle_get_project_info)
            self.register_handler("load_project", self._handle_load_project)
            self.register_handler("save_project", self._handle_save_project)
            self.register_handler("new_project", self._handle_new_project)
        
        def _handle_handshake(self, content: dict) -> dict:
            """Maneja el saludo inicial de JS y muestra la ventana."""
            is_refresh = self.is_ready  # If already ready, this is a F5 refresh
            self.is_ready = True
            
            if is_refresh:
                Logger.info("Handshake (REFRESH detectado) - JS recargado")
                # Re-apply window state on refresh
                if self.window_api._is_maximized and self.window_api.hwnd:
                    Logger.info("Re-applying maximized state after refresh")
                    try:
                        SW_MAXIMIZE = 3
                        ctypes.windll.user32.ShowWindow(self.window_api.hwnd, SW_MAXIMIZE)
                    except Exception as e:
                        Logger.error(f"Error re-maximizing: {e}")
            else:
                Logger.info("Handshake completado - JS listo")
                # Mostrar la ventana (solo primera vez)
                self.show_window() 
                
                # Maximizar si es necesario (AHORA es el momento correcto)
                if self.window_api._is_maximized:
                    Logger.info("Ejecutando maximización post-handshake")
                    self.window.maximize()
                
                self.handshake_event.set() 
            
            return {"status": "ready", "timestamp": datetime.now().isoformat(), "version": "1.0", "was_refresh": is_refresh}
        
        def _handle_ping(self, content: dict) -> dict:
            """Responde a un ping de JS."""
            return {"pong": True, "timestamp": datetime.now().isoformat()}

        def _handle_open_file_dialog(self, content: dict) -> dict:
            """Handler para abrir un diálogo de selección de archivo nativo."""
            try:
                file_types = tuple(content.get('file_types', ('Todos los archivos (*.*)', '*.*')))
                
                result = self.window.create_file_dialog(
                    webview.OPEN_DIALOG, 
                    allow_multiple=False,
                    file_types=file_types
                )
                
                if result and len(result) > 0:
                    return {"filePath": result[0]}
                
                return {"filePath": None}
                
            except Exception as e:
                Logger.error(f"Error en _handle_open_file_dialog: {e}")
                return {"filePath": None, "error": str(e)}

        # --- [ MODIFICADO CON EL KILL SWITCH ] ---
        def _handle_get_ui_settings(self, content: dict) -> dict:
            """Obtiene de forma segura solo el diccionario 'uiData' del storage."""
            try:
                if not self.storage:
                    raise Exception("Storage no está inicializado")
                
                ui_settings = self.storage.get_ui_settings()
                
                # --- [ INICIO: LÓGICA DE DESACTIVACIÓN DE SESIÓN ] ---
                if not LOAD_SAVED_SESSION:
                    Logger.info("Desactivación de sesión: Purgando 'last_opened_sheet' y 'last_opened_template' antes de enviar a la UI.")
                    if "last_opened_sheet" in ui_settings:
                        ui_settings["last_opened_sheet"] = []
                    if "last_opened_template" in ui_settings:
                        ui_settings["last_opened_template"] = []
                # --- [ FIN: LÓGICA DE DESACTIVACIÓN ] ---
                
                return ui_settings
                
            except Exception as e:
                Logger.error(f"Error en _handle_get_ui_settings: {e}")
                
                if AppStorage:
                    # Aplicar la lógica de desactivación también al fallback
                    defaults = AppStorage.DEFAULTS.get("uiData", {}).copy()
                    if not LOAD_SAVED_SESSION:
                        defaults["last_opened_sheet"] = []
                        defaults["last_opened_template"] = []
                    return defaults
                return {} 
        # --- [ FIN DE LA MODIFICACIÓN ] ---

        def _handle_save_ui_setting(self, content: dict) -> dict:
            """Guarda un par clave/valor dentro del diccionario 'uiData'."""
            try:
                if not self.storage:
                    raise Exception("Storage no está inicializado")
                
                key = content.get("key")
                value = content.get("value")
                
                if key is None or value is None:
                    raise Exception("Clave (key) o valor (value) faltantes")

                success = self.storage.save_ui_setting(key, value)
                return {"success": success}
                
            except Exception as e:
                Logger.error(f"Error en _handle_save_ui_setting: {e}")
                return {"success": False, "error": str(e)}

        def _handle_get_excel_structure(self, content: dict) -> Optional[Dict[str, Any]]:
            """
            Handler para leer la estructura de un archivo Excel.
            Llama al parser de data_sheet de forma segura.
            """
            if not get_data_sheet_structure:
                raise Exception("El parser 'get_data_sheet_structure' no está disponible o falló al importar.")

            file_path = content.get("filePath")
            if not file_path:
                raise Exception("No se proporcionó 'filePath' en la solicitud 'get_excel_structure'.")
            
            Logger.info(f"Bridge: Solicitando estructura para: {file_path}")
            
            structure_data = get_data_sheet_structure(file_path)
            
            if structure_data is None:
                Logger.warn(f"Bridge: El parser devolvió None para: {file_path}")
            
            return structure_data

        def _handle_get_excel_sheet_data(self, content: dict) -> Optional[List[Dict[str, Any]]]:
            """
            Handler para leer DATOS REALES de una hoja.
            Llama a get_row_data_sheet del parser.
            """
            try:
                # Importación tardía para evitar ciclos o si no se cargó arriba
                from core.data_sheet.data_sheet_parser import get_row_data_sheet
                
                # content debe traer la config completa: filePath, sheetName, tableName, columns, etc.
                Logger.info(f"Bridge: Solicitando datos de fila para: {content.get('filePath')}")
                
                return get_row_data_sheet(content)
                
            except Exception as e:
                Logger.error(f"Error en _handle_get_excel_sheet_data: {e}")
                return [{"_error_message": str(e)}]

        def _handle_get_unified_excel_data(self, content: dict) -> Optional[Dict[str, Any]]:
            """
            Handler UNIFICADO.
            Retorna { "simple_data": ..., "full_data": ... }
            """
            try:
                from core.data_sheet.data_sheet_parser import get_unified_excel_data
                file_path = content.get("filePath")
                Logger.info(f"Bridge: Solicitud UNIFICADA para: {file_path}")
                return get_unified_excel_data(file_path)
            except Exception as e:
                Logger.error(f"Error en _handle_get_unified_excel_data: {e}")
                return None

        def _handle_get_excel_full_data(self, content: dict) -> Optional[Dict[str, Any]]:
            """
            Handler para Split API - Paso 2: Datos completos.
            Solo devuelve los datos de filas (sin estructura) con fechas serializadas.
            """
            try:
                from core.data_sheet.data_sheet_parser import get_unified_excel_data
                file_path = content.get("filePath")
                Logger.info(f"Bridge: Solicitud FULL DATA para: {file_path}")
                
                result = get_unified_excel_data(file_path)
                if result:
                    # Solo devolver full_data (los datos ya están serializados)
                    return result.get("full_data", {})
                return None
            except Exception as e:
                Logger.error(f"Error en _handle_get_excel_full_data: {e}")
                return None

        def _handle_get_template_placeholders(self, content: dict) -> Optional[Dict[str, Any]]:
            """
            Handler para parsear una plantilla Word y extraer placeholders.
            Usado por la UI para la pantalla de mapeo.
            """
            try:
                from core.ms_word.template_parser import get_template_placeholders
                
                source_path = content.get("source_path")
                if not source_path:
                    return {"success": False, "error": "No se proporcionó 'source_path'", "placeholders": []}
                
                Logger.info(f"Bridge: Parsing template placeholders: {source_path}")
                
                result = get_template_placeholders(content)
                
                Logger.info(f"Bridge: Found {result.get('total_count', 0)} placeholders")
                
                return result
                
            except Exception as e:
                Logger.error(f"Error en _handle_get_template_placeholders: {e}")
                return {"success": False, "error": str(e), "placeholders": []}

        def _handle_get_docx_file_data(self, content: dict) -> Optional[Dict[str, Any]]:
            """
            Handler para enviar un archivo docx como base64 para el viewer.
            Usado por la UI para mostrar la vista previa del documento.
            """
            try:
                import base64
                from pathlib import Path
                
                file_path = content.get("filePath")
                if not file_path:
                    return {"success": False, "error": "No se proporcionó 'filePath'"}
                
                path = Path(file_path)
                if not path.exists():
                    return {"success": False, "error": f"Archivo no encontrado: {file_path}"}
                
                if not path.suffix.lower() in ['.docx', '.doc']:
                    return {"success": False, "error": f"Tipo de archivo no soportado: {path.suffix}"}
                
                Logger.info(f"Bridge: Loading docx for viewer: {file_path}")
                
                # Read file as binary and encode to base64
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                
                base64_data = base64.b64encode(file_bytes).decode('utf-8')
                file_size_kb = len(file_bytes) / 1024
                
                Logger.info(f"Bridge: Encoded {file_size_kb:.1f}KB docx to base64")
                
                return {
                    "success": True,
                    "data": base64_data,
                    "filePath": file_path,
                    "fileName": path.name,
                    "fileSize": len(file_bytes),
                    "fileSizeKB": round(file_size_kb, 1)
                }
                
            except Exception as e:
                Logger.error(f"Error en _handle_get_docx_file_data: {e}")
                return {"success": False, "error": str(e)}

        # --- Job Control Handlers ---
        
        def _handle_job_cancel(self, content: dict) -> dict:
            """Cancel a running job by ID."""
            try:
                from assembler.job_manager import JobManager
                job_id = content.get("job_id")
                if not job_id:
                    return {"success": False, "error": "No job_id provided"}
                return JobManager.cancel(job_id)
            except Exception as e:
                Logger.error(f"Error en _handle_job_cancel: {e}")
                return {"success": False, "error": str(e)}
        
        def _handle_job_pause(self, content: dict) -> dict:
            """Pause a running job by ID."""
            try:
                from assembler.job_manager import JobManager
                job_id = content.get("job_id")
                if not job_id:
                    return {"success": False, "error": "No job_id provided"}
                return JobManager.pause(job_id)
            except Exception as e:
                Logger.error(f"Error en _handle_job_pause: {e}")
                return {"success": False, "error": str(e)}
        
        def _handle_job_resume(self, content: dict) -> dict:
            """Resume a paused job by ID."""
            try:
                from assembler.job_manager import JobManager
                job_id = content.get("job_id")
                if not job_id:
                    return {"success": False, "error": "No job_id provided"}
                return JobManager.resume(job_id)
            except Exception as e:
                Logger.error(f"Error en _handle_job_resume: {e}")
                return {"success": False, "error": str(e)}
        
        def _handle_job_list_active(self, content: dict) -> dict:
            """List all active (registered) jobs."""
            try:
                from assembler.job_manager import JobManager
                jobs = JobManager.list_active()
                return {"success": True, "jobs": jobs}
            except Exception as e:
                Logger.error(f"Error en _handle_job_list_active: {e}")
                return {"success": False, "error": str(e), "jobs": []}
        
        def _handle_job_list_resumable(self, content: dict) -> dict:
            """List jobs that can be resumed from checkpoints."""
            try:
                from assembler.job_manager import JobManager
                jobs = JobManager.list_resumable()
                return {"success": True, "jobs": jobs, "count": len(jobs)}
            except Exception as e:
                Logger.error(f"Error en _handle_job_list_resumable: {e}")
                return {"success": False, "error": str(e), "jobs": []}
        
        def _handle_convert_to_pdf(self, content: dict) -> dict:
            """Handle Word to PDF conversion requests.
            
            Expected content:
                - files: List of file paths or single path string
                - input_dir: Optional directory to scan for Word files
                - output_dir: Optional destination (default: same as input)
                - batch_size: Optional batch size (default: 5)
                - timeout_seconds: Optional per-file timeout (default: 60)
            """
            try:
                import threading
                from assembler.jobs.word_to_pdf_job import WordToPdfJob, WordToPdfConfig
                from assembler.job_manager import JobManager
                
                # Parse input - can be single file, list, or directory
                files = content.get("files", [])
                input_dir = content.get("input_dir")
                output_dir = content.get("output_dir")
                batch_size = content.get("batch_size", 5)
                timeout = content.get("timeout_seconds", 60)
                
                # Build config
                config = WordToPdfConfig(
                    batch_size=batch_size,
                    timeout_seconds=timeout,
                    output_directory=output_dir,
                    apply_metadata=content.get("apply_metadata", False)
                )
                
                # Determine input
                if input_dir:
                    job = WordToPdfJob(input_directory=input_dir, config=config)
                elif files:
                    if isinstance(files, str):
                        files = [files]
                    job = WordToPdfJob(input_files=files, config=config)
                else:
                    return {"success": False, "error": "No files or input_dir provided"}
                
                # Register and start in background thread
                JobManager.register(job)
                
                def run_job():
                    try:
                        job.run()
                    finally:
                        JobManager.unregister(job.job_id)
                
                thread = threading.Thread(target=run_job, daemon=True)
                thread.start()
                
                return {
                    "success": True,
                    "job_id": job.job_id,
                    "message": f"Conversion job started"
                }
                
            except Exception as e:
                Logger.error(f"Error en _handle_convert_to_pdf: {e}")
                return {"success": False, "error": str(e)}
        
        def _handle_convert_existing_to_pdf(self, content: dict) -> dict:
            """Handle conversion of existing Word files to PDF with file rules.
            
            Expected content:
                - source: { base_path, scan_mode, search_key }
                - file_rules: [{ comparator, pattern, ignore_case, output: {filename, subfolder} }]
                - default_rule: { action: "SKIP"|"CONVERT_SAME_NAME", subfolder }
                - policies: { overwrite, stop_on_error }
            
            Example:
            {
                "source": {
                    "base_path": "C:/Documents/OUTPUT",
                    "scan_mode": "SELECT",  // or "ALL"
                    "search_key": "ADRIANA MORENO"
                },
                "file_rules": [
                    {"comparator": "CONTAINS", "pattern": "ACTA 1", "output": {"filename": "001Acta.pdf"}}
                ],
                "default_rule": {"action": "SKIP"}
            }
            """
            try:
                import threading
                from assembler.jobs.word_to_pdf_job import WordToPdfJob
                from assembler.job_manager import JobManager
                
                # Build config for WordToPdfJob in file_rules mode
                job_config = {
                    "mode": "file_rules",
                    "source": content.get("source", {}),
                    "file_rules": content.get("file_rules", []),
                    "default_rule": content.get("default_rule", {"action": "SKIP"}),
                    "overwrite_existing": content.get("policies", {}).get("overwrite", True),
                    "metadata": content.get("metadata"),
                    "batch_size": content.get("batch_size", 10)
                }
                
                # Validate source
                if not job_config.get("source", {}).get("base_path"):
                    return {"success": False, "error": "Missing source.base_path"}
                
                job = WordToPdfJob(job_config)
                
                # Validate config
                valid, error = job.validate_config()
                if not valid:
                    return {"success": False, "error": error}
                
                # Register and start in background thread
                JobManager.register(job)
                
                def run_job():
                    try:
                        job.run()
                    finally:
                        JobManager.unregister(job.job_id)
                
                thread = threading.Thread(target=run_job, daemon=True)
                thread.start()
                
                return {
                    "success": True,
                    "job_id": job.job_id,
                    "message": "File rules conversion job started"
                }
                
            except Exception as e:
                Logger.error(f"Error en _handle_convert_existing_to_pdf: {e}")
                return {"success": False, "error": str(e)}

        # --- Project Management Handlers ---
        
        def _handle_get_project_info(self, content: dict) -> dict:
            """Gets project settings for startup flow."""
            try:
                if not self.storage:
                    return {"autoLoad": False, "path": None, "exists": False}
                
                settings = self.storage.get_project_settings()
                path = settings.get("lastProjectPath")
                
                return {
                    "autoLoad": settings.get("autoLoadLastProject", True),
                    "path": path,
                    "exists": path is not None and Path(path).exists(),
                    "autoSaveEnabled": settings.get("autoSaveEnabled", True),
                    "autoSaveIntervalSeconds": settings.get("autoSaveIntervalSeconds", 60)
                }
            except Exception as e:
                Logger.error(f"Error en _handle_get_project_info: {e}")
                return {"autoLoad": False, "path": None, "exists": False}

        def _handle_load_project(self, content: dict) -> dict:
            """Loads a project file."""
            try:
                if not get_project_manager:
                    return {"success": False, "error": "ProjectManager not available"}
                
                path = content.get("path")
                if not path:
                    return {"success": False, "error": "No path provided"}
                
                pm = get_project_manager()
                result = pm.load(path)
                
                # Update last project in storage
                if self.storage:
                    self.storage.set_last_project(path)
                
                Logger.info(f"[Bridge] Project loaded: {path}")
                return {
                    "success": True,
                    "project": result["project"],
                    "missingFiles": result["missingFiles"]
                }
            except FileNotFoundError as e:
                Logger.warn(f"[Bridge] Project file not found: {e}")
                return {"success": False, "error": str(e)}
            except Exception as e:
                Logger.error(f"Error en _handle_load_project: {e}")
                return {"success": False, "error": str(e)}

        def _handle_save_project(self, content: dict) -> dict:
            """Saves the current project."""
            try:
                if not get_project_manager:
                    return {"success": False, "error": "ProjectManager not available"}
                
                path = content.get("path")
                project_config = content.get("project")
                
                if not path or not project_config:
                    return {"success": False, "error": "Missing path or project data"}
                
                pm = get_project_manager()
                success = pm.save(path, project_config)
                
                Logger.info(f"[Bridge] Project saved: {path} (success={success})")
                return {"success": success}
            except Exception as e:
                Logger.error(f"Error en _handle_save_project: {e}")
                return {"success": False, "error": str(e)}

        def _handle_new_project(self, content: dict) -> dict:
            """Creates a new project file."""
            try:
                if not get_project_manager:
                    return {"success": False, "error": "ProjectManager not available"}
                
                path = content.get("path")
                name = content.get("name", "New Project")
                
                if not path:
                    return {"success": False, "error": "No path provided"}
                
                # Handle __DEFAULT__ special path - create in AppData folder
                if path == "__DEFAULT__":
                    if self.storage and self.storage.storage_dir:
                        path = str(Path(self.storage.storage_dir) / "default.bkproj")
                        Logger.info(f"[Bridge] Creating default project at: {path}")
                    else:
                        return {"success": False, "error": "Cannot determine AppData path"}
                
                pm = get_project_manager()
                project = pm.create(path, name)
                
                # Update last project in storage
                if self.storage:
                    self.storage.set_last_project(path)
                
                Logger.info(f"[Bridge] New project created: {path}")
                return {
                    "success": True,
                    "project": project,
                    "path": path  # Return actual path used
                }
            except Exception as e:
                Logger.error(f"Error en _handle_new_project: {e}")
                return {"success": False, "error": str(e)}

        # --- End Project Management Handlers ---

        def register_handler(self, msg_name: str, handler: Callable):
            """Registra un nuevo handler para mensajes de JS."""
            self.handlers[msg_name] = handler
            Logger.info(f"Handler registrado: {msg_name}")
        
        def handle_message(self, message: dict) -> dict:
            """Punto de entrada principal para todos los mensajes de JS."""
            try:
                msg_id = message.get("id")
                msg_name = message.get("msg")
                content = message.get("content", {})
                
                if not msg_id or not msg_name:
                    return {"id": msg_id or "unknown", "response": "error", "content": {"error": "Mensaje inválido: falta id o msg"}}
                
                handler = self.handlers.get(msg_name)
                
                if not handler:
                    return {"id": msg_id, "response": "error", "content": {"error": f"Handler no encontrado: {msg_name}"}}
                
                result = handler(content)
                
                return {"id": msg_id, "response": "ok", "content": result}
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                Logger.error(f"Error procesando mensaje: {e}\n{error_details}")
                return {"id": message.get("id", "unknown"), "response": "error", "content": {"error": str(e), "traceback": error_details}}
        
        def send_to_js(self, msg_name: str, content: dict = None):
            """Envía un mensaje de Python a JS."""
            if not self.is_ready: 
                Logger.warn("JavaScript aún no está listo")
                return
            message = {"id": str(uuid.uuid4()), "msg": msg_name, "content": content or {}}
            js_code = f"window.bridgePy.receiveFromPython({json.dumps(message)})"
            self.window.evaluate_js(js_code)

    #--------------------------------------> END [ BRIDGE API CLASS ... ]

    
    #-------------------------------------------------------------
    #-------------[   HELPERS NATIVOS (WINDOWS API)   ]-----------
    #-------------------------------------------------------------

    def force_window_geometry(hwnd, width, height, x, y, is_maximized):
        """
        Fuerza la geometría de la ventana usando Windows API DIRECTAMENTE.
        Esto evita los bugs de DPI de pywebview.
        """
        try:
            user32 = ctypes.windll.user32
            
            # Obtener DPI de la ventana
            dpi = user32.GetDpiForWindow(hwnd)
            dpi_scale = dpi / 96.0
            
            Logger.debug(f"🔧 Forzando geometría con DPI {dpi} ({int(dpi_scale * 100)}%):")
            Logger.debug(f"   Lógico solicitado: {width}x{height} @ ({x}, {y})")
            
            # Convertir coordenadas lógicas a físicas
            physical_width = int(width * dpi_scale)
            physical_height = int(height * dpi_scale)
            physical_x = int(x * dpi_scale) if x is not None else 100
            physical_y = int(y * dpi_scale) if y is not None else 100
            
            Logger.debug(f"   Físico calculado: {physical_width}x{physical_height} @ ({physical_x}, {physical_y})")
            
            # SWP flags
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            
            # Establecer posición y tamaño
            result = user32.SetWindowPos(
                hwnd,
                0,  # HWND_TOP
                physical_x,
                physical_y,
                physical_width,
                physical_height,
                SWP_NOZORDER | SWP_NOACTIVATE
            )
            
            if result:
                Logger.info(f"Geometría forzada correctamente")
            else:
                Logger.warn(f"SetWindowPos falló")
            
            # Si debe estar maximizada, maximizarla
            if is_maximized:
                SW_MAXIMIZE = 3
                user32.ShowWindow(hwnd, SW_MAXIMIZE)
                Logger.info(f"Ventana maximizada")
            
            return True
            
        except Exception as e:
            Logger.error(f"⚠️ Error forzando geometría: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def customize_window_chrome(window, icon_path, window_api_ref):
        """Personaliza la apariencia de la ventana en Windows."""
        try:
            time.sleep(0.5) 
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "DocuFlow") 
            if not hwnd: 
                Logger.warn("No se pudo encontrar el handle, reintentando...")
                time.sleep(0.3)
                hwnd = user32.FindWindowW(None, "DocuFlow")
                if not hwnd:
                    Logger.error("No se pudo encontrar el handle después de reintentar")
                    return False
            
            Logger.info(f"Handle de ventana encontrado: {hwnd}")
            
            # Establecer el HWND en WindowAPI
            window_api_ref.set_hwnd(hwnd)
            
            # FORZAR LA GEOMETRÍA GUARDADA (solo en primera carga, no en F5)
            if storage and saved_geometry and not window_api_ref.first_load_done:
                geom = saved_geometry
                force_window_geometry(
                    hwnd,
                    geom['width'],
                    geom['height'],
                    geom['x'],
                    geom['y'],
                    geom['is_maximized']
                )
                window_api_ref.first_load_done = True
            elif window_api_ref.first_load_done:
                Logger.debug("Skipping geometry forcing (F5 refresh detected)")
            
            if icon_path and icon_path.exists():
                try:
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x0010
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    
                    hicon_small = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 1024, 1024, LR_LOADFROMFILE)
                    
                    if not hicon_big: hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 512, 512, LR_LOADFROMFILE)
                    if not hicon_big: hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
                    if not hicon_big: hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                    
                    if hicon_small: user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                    if hicon_big: user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                    
                    shell32 = ctypes.windll.shell32
                    try:
                        app_id = "Anthropic.DocuFlow.1.0"
                        shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    except Exception as e:
                        Logger.error(f"⚠️ Error al establecer AppUserModelID: {e}")
                    
                    GWL_EXSTYLE = -20
                    old_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, old_style)
                    
                    SWP_FRAMECHANGED = 0x0020
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    SWP_NOZORDER = 0x0004
                    SWP_FLAGS = SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
                    
                    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)
                    
                except Exception as e:
                    Logger.error(f"⚠️ Error al aplicar icono: {e}")
            else:
                Logger.warn(f"Icono no encontrado o ruta inválida: {icon_path}")
            
            try:
                dwmapi = ctypes.windll.dwmapi
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                use_dark_mode = wintypes.BOOL(True)
                dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(use_dark_mode), ctypes.sizeof(use_dark_mode))
                
                DWMWA_CAPTION_COLOR = 35
                caption_color = wintypes.DWORD(0x001E1E1E)
                dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(caption_color), ctypes.sizeof(caption_color))
                
                DWMWA_BORDER_COLOR = 34
                border_color = wintypes.DWORD(0x001E1E1E)
                dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, byref(border_color), ctypes.sizeof(border_color))
                
                user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
                Logger.info("Barra de título personalizada aplicada correctamente")
            except Exception as e:
                Logger.error(f"⚠️ Error al personalizar tema: {e}")
            
            return True
            
        except Exception as e:
            Logger.warn(f"No se pudo personalizar la barra: {e}")
            return False

    #--------------------------------------> END [ HELPERS NATIVOS (WINDOWS API) ... ]


    #-------------------------------------------------------------
    #-------------[   HIJO: LÓGICA DE ARRANQUE   ]----------------
    #-------------------------------------------------------------
    try:
        if sys.platform != 'win32':
            Logger.warn("Optimizado solo para Windows")
            sys.exit(1)
        
        # 'src_dir' fue definido al inicio del script
        base_path = src_dir

        ui_path = base_path / "ui" / "index.html"
        icon_path = base_path / "ui" / "assets" / "icon.ico"
        
        if not ui_path.exists():
            raise FileNotFoundError(f"Error: No se encuentra UI en: {ui_path}")
        
        if icon_path.exists():
            Logger.info(f"Icono encontrado: {icon_path.name}")
        else:
            Logger.warn(f"Icono no encontrado en: {icon_path}")
            icon_path = None
        
        default_window_state = {}
        if AppStorage:
             default_window_state = AppStorage.DEFAULTS.get("providerData", {}).get("window", {})
        else:
             default_window_state = {"width": 1080, "height": 600, "x": None, "y": None, "maximized": False}

        window_state = storage.get_window_state() if storage else default_window_state
        
        window_width = window_state.get('width', 1080)
        window_height = window_state.get('height', 600)
        window_x = window_state.get('x') 
        window_y = window_state.get('y') 
        is_maximized = window_state.get('maximized', False)
        
        # Guardar globalmente para usar en customize_window_chrome
        saved_geometry = {
            'width': window_width,
            'height': window_height,
            'x': window_x if window_x is not None else 100,
            'y': window_y if window_y is not None else 100,
            'is_maximized': is_maximized
        }
        
        Logger.debug(f"📐 Estado de ventana cargado: {window_state}")
        
        url = str(ui_path)
        if config.get("unicId_UI", True):
            url = f"{url}?id={uuid.uuid4()}"
        
        # CREAR VENTANA CON VALORES POR DEFECTO
        # La geometría REAL se forzará después con Windows API
        window = webview.create_window(
            title='DocuFlow', 
            url=url, 
            width=800,  # Valor temporal, se sobreescribirá
            height=600, # Valor temporal, se sobreescribirá
            resizable=True, 
            frameless=False, 
            min_size=(400, 200),
            background_color='#1e1e1E', 
            confirm_close=False, 
            hidden=True 
        )
        
        # --- LÓGICA DE INICIALIZACIÓN ---
        window_api = WindowAPI(window, storage)
        if is_maximized:
            Logger.info("Flag de 'is_maximized' puesto en True")
            window_api._is_maximized = True

        bridge = BridgeAPI(window, handshake_event, window.show, storage, window_api)
        
        window.expose(bridge.handle_message, window_api.minimize, window_api.maximize, window_api.close)
        
        # --- INICIALIZAR LOG CHANNEL ---
        # Connect Logger events to console (future: to UI via window)
        try:
            from bridge.log_channel import initialize_log_channel
            # For now, use console fallback. Later: pass window for UI streaming
            log_channel = initialize_log_channel(
                window=None,  # TODO: Enable when UI is ready to receive logs
                console_fallback=True,
                connect_to_logger=True
            )
            Logger.info("LogChannel inicializado (modo consola)")
        except Exception as e:
            Logger.warn(f"No se pudo inicializar LogChannel: {e}")
        
        
        # --- EVENTOS DE VENTANA ---
        
        def on_closing():
            """Intercepta la [X] nativa."""
            Logger.info("Evento 'closing' interceptado. Guardando sesión...")
            window_api.close(from_event=True)
        
        def on_loaded():
            # Pasar window_api como parámetro
            threading.Thread(target=customize_window_chrome, args=(window, icon_path, window_api), daemon=True).start()
            Logger.info("DocuFlow (webview) iniciado correctamente")
            Logger.debug("⏳ Esperando handshake desde JavaScript...")
        
        def on_window_maximized(*args):
            """Evento cuando la ventana se maximiza."""
            Logger.info("Evento 'maximized' detectado.")
            window_api._is_maximized = True
        
        def on_window_restored(*args):
            """Evento cuando la ventana se restaura desde maximizado."""
            Logger.info("Evento 'restored' detectado.")
            window_api._is_maximized = False
            
        # Conectar los listeners de eventos de la ventana
        window.events.loaded += on_loaded
        window.events.closing += on_closing
        window.events.maximized += on_window_maximized
        window.events.restored += on_window_restored
        
        webview_debug = config.get("devTools_UI", False)
        Logger.info(f"DevTools habilitado: {webview_debug}")
        
        webview.start(debug=webview_debug)
        Logger.info("DocuFlow (webview) cerrado.")
        
    except Exception as e:
        Logger.error(f"ERROR FATAL (Proceso Hijo): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    #--------------------------------------> END [ HIJO: LÓGICA DE ARRANQUE ... ]

# -------------------------------------------------------------
# -------------------[   ORQUESTACIÓN (PADRE)   ]--------------
# -------------------------------------------------------------

def main():
    """
    Función principal de orquestación (Proceso Padre).
    """
    
    handshake_event = multiprocessing.Event()
    
    main_app_process = multiprocessing.Process(
        target=start_webview_app,
        args=(handshake_event, APP_CONFIG),
        daemon=False 
    )
    
    try:
        main_app_process.start()
        create_splash_screen(handshake_event, main_app_process)
        
    except KeyboardInterrupt:
        Logger.debug("\nℹ️ Cierre solicitado (Ctrl+C). Terminando app...")
        if main_app_process.is_alive():
            main_app_process.terminate()
            main_app_process.join()
    
    Logger.debug("ℹ️ Proceso del Loader finalizado.")
    sys.exit(0)

# --------------------------------------> END [ ORQUESTACIÓN (PADRE) ... ]


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()