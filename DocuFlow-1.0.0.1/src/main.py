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

# Importar el sistema de storage desde /core
try:
    from core.storage import AppStorage
except ImportError:
    print("⚠️ No se pudo importar core/storage.py - Sistema de persistencia deshabilitado")
    AppStorage = None

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
APP_CONFIG = {
    "devTools_UI": False,
    "unicId_UI": True,
    "enableCache_UI": False
}

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
        print(f"Error al mostrar el diálogo de error: {e}")

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
        base_path = Path(__file__).parent
        if not (base_path / "ui").exists():
            base_path = base_path.parent
        
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
            print(f"⚠️ Logo no encontrado en: {logo_path}")
    except Exception as e:
        print(f"⚠️ Error al cargar el logo: {e}")
    
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
            print("❌ ERROR: El proceso principal (webview) falló al iniciar.")
            show_error_dialog("DocuFlow no pudo iniciarse.\n\n"
                              "El proceso principal falló. Verifique los logs.")
            return

        splash_root.after(100, check_status)

    splash_root.after(100, check_status)
    
    try:
        splash_root.mainloop()
    except Exception as e:
        print(f"ℹ️ Splash screen cerrado: {e}")

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
    from typing import Dict, Any, Callable
    from datetime import datetime
    
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
            print("✓ Proceso hijo marcado como DPI-Aware (Modo 1)")
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                print("✓ Proceso hijo marcado como DPI-Aware (Modo 2)")
            except Exception:
                print("⚠️ No se pudo establecer DPI Awareness en el proceso hijo")
    
    storage = None
    if AppStorage is not None:
        storage = AppStorage("DocuFlow")
        
        if not storage.was_closed_properly():
            print("⚠️ La aplicación no se cerró correctamente en la última sesión")
        else:
            print("✓ Última sesión cerrada correctamente")
        
        storage.mark_improper_close()
    else:
        print("❌ ERROR: No se pudo instanciar AppStorage. Persistencia deshabilitada.")

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
            
        def set_hwnd(self, hwnd):
            """Establece el handle de la ventana después de que esté creada."""
            self.hwnd = hwnd
            print(f"✓ HWND establecido: {hwnd}")
            
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
                print("⚠️ HWND no disponible al guardar. Usando valores por defecto.")
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
                
                print(f"📐 Estado capturado de Windows:")
                print(f"   DPI: {dpi} ({int(dpi_scale * 100)}%)")
                print(f"   Físico (Restaurado): {rect.right - rect.left}x{rect.bottom - rect.top}")
                print(f"   Lógico (Restaurado): {width}x{height} @ ({x}, {y})")
                print(f"   Estado Maximizado: {is_maximized}")
                
                return state
                
            except Exception as e:
                print(f"⚠️ Error obteniendo estado de ventana: {e}")
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
                    print("💾 Preparando guardado de sesión...")
                    
                    # Esperar un instante para que Windows actualice el estado
                    time.sleep(0.05)
                    
                    # Obtener estado de Windows
                    final_window_state = self._get_window_state_from_windows()
                    
                    print(f"✓ Guardando estado final: {final_window_state}")

                    # Guardar
                    self.storage.finalize_session_save(final_window_state)
                    
                except Exception as e:
                    print(f"⚠️ Error al guardar estado: {e}")
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
        
        def _handle_handshake(self, content: dict) -> dict:
            """Maneja el saludo inicial de JS y muestra la ventana."""
            self.is_ready = True
            print("✅ Handshake completado - JS listo")
            
            # Mostrar la ventana
            self.show_window() 
            
            # Maximizar si es necesario (AHORA es el momento correcto)
            if self.window_api._is_maximized:
                print("✓ Ejecutando maximización post-handshake")
                self.window.maximize()
            
            self.handshake_event.set() 
            return {"status": "ready", "timestamp": datetime.now().isoformat(), "version": "1.0"}
        
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
                print(f"❌ Error en _handle_open_file_dialog: {e}")
                return {"filePath": None, "error": str(e)}

        def _handle_get_ui_settings(self, content: dict) -> dict:
            """Obtiene de forma segura solo el diccionario 'uiData' del storage."""
            try:
                if not self.storage:
                    raise Exception("Storage no está inicializado")
                
                ui_settings = self.storage.get_ui_settings()
                return ui_settings
                
            except Exception as e:
                print(f"❌ Error en _handle_get_ui_settings: {e}")
                
                if AppStorage:
                    return AppStorage.DEFAULTS.get("uiData", {})
                return {} 

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
                print(f"❌ Error en _handle_save_ui_setting: {e}")
                return {"success": False, "error": str(e)}
        
        def register_handler(self, msg_name: str, handler: Callable):
            """Registra un nuevo handler para mensajes de JS."""
            self.handlers[msg_name] = handler
            print(f"✓ Handler registrado: {msg_name}")
        
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
                print(f"❌ Error procesando mensaje: {e}\n{error_details}")
                return {"id": message.get("id", "unknown"), "response": "error", "content": {"error": str(e), "traceback": error_details}}
        
        def send_to_js(self, msg_name: str, content: dict = None):
            """Envía un mensaje de Python a JS."""
            if not self.is_ready: 
                print("⚠️ JavaScript aún no está listo")
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
            
            print(f"🔧 Forzando geometría con DPI {dpi} ({int(dpi_scale * 100)}%):")
            print(f"   Lógico solicitado: {width}x{height} @ ({x}, {y})")
            
            # Convertir coordenadas lógicas a físicas
            physical_width = int(width * dpi_scale)
            physical_height = int(height * dpi_scale)
            physical_x = int(x * dpi_scale) if x is not None else 100
            physical_y = int(y * dpi_scale) if y is not None else 100
            
            print(f"   Físico calculado: {physical_width}x{physical_height} @ ({physical_x}, {physical_y})")
            
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
                print(f"✅ Geometría forzada correctamente")
            else:
                print(f"⚠️ SetWindowPos falló")
            
            # Si debe estar maximizada, maximizarla
            if is_maximized:
                SW_MAXIMIZE = 3
                user32.ShowWindow(hwnd, SW_MAXIMIZE)
                print(f"✅ Ventana maximizada")
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error forzando geometría: {e}")
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
                print("⚠️ No se pudo encontrar el handle, reintentando...")
                time.sleep(0.3)
                hwnd = user32.FindWindowW(None, "DocuFlow")
                if not hwnd:
                    print("❌ No se pudo encontrar el handle después de reintentar")
                    return False
            
            print(f"✓ Handle de ventana encontrado: {hwnd}")
            
            # Establecer el HWND en WindowAPI
            window_api_ref.set_hwnd(hwnd)
            
            # FORZAR LA GEOMETRÍA GUARDADA
            if storage and saved_geometry:
                geom = saved_geometry
                force_window_geometry(
                    hwnd,
                    geom['width'],
                    geom['height'],
                    geom['x'],
                    geom['y'],
                    geom['is_maximized']
                )
            
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
                        print(f"⚠️ Error al establecer AppUserModelID: {e}")
                    
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
                    print(f"⚠️ Error al aplicar icono: {e}")
            else:
                print(f"⚠️ Icono no encontrado o ruta inválida: {icon_path}")
            
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
                print("✅ Barra de título personalizada aplicada correctamente")
            except Exception as e:
                print(f"⚠️ Error al personalizar tema: {e}")
            
            return True
            
        except Exception as e:
            print(f"⚠️ No se pudo personalizar la barra: {e}")
            return False

    #--------------------------------------> END [ HELPERS NATIVOS (WINDOWS API) ... ]


    #-------------------------------------------------------------
    #-------------[   HIJO: LÓGICA DE ARRANQUE   ]----------------
    #-------------------------------------------------------------
    try:
        if sys.platform != 'win32':
            print("⚠️ Optimizado solo para Windows")
            sys.exit(1)
        
        base_path = Path(__file__).parent
        if not (base_path / "ui").exists():
             base_path = base_path.parent

        ui_path = base_path / "ui" / "index.html"
        icon_path = base_path / "ui" / "assets" / "icon.ico"
        
        if not ui_path.exists():
            raise FileNotFoundError(f"Error: No se encuentra UI en: {ui_path}")
        
        if icon_path.exists():
            print(f"✓ Icono encontrado: {icon_path.name}")
        else:
            print(f"⚠️ Icono no encontrado en: {icon_path}")
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
        
        print(f"📐 Estado de ventana cargado: {window_state}")
        
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
            print("✓ Flag de 'is_maximized' puesto en True")
            window_api._is_maximized = True

        bridge = BridgeAPI(window, handshake_event, window.show, storage, window_api)
        
        window.expose(bridge.handle_message, window_api.minimize, window_api.maximize, window_api.close)
        
        
        # --- EVENTOS DE VENTANA ---
        
        def on_closing():
            """Intercepta la [X] nativa."""
            print("✓ Evento 'closing' interceptado. Guardando sesión...")
            window_api.close(from_event=True)
        
        def on_loaded():
            # Pasar window_api como parámetro
            threading.Thread(target=customize_window_chrome, args=(window, icon_path, window_api), daemon=True).start()
            print("✅ DocuFlow (webview) iniciado correctamente")
            print("⏳ Esperando handshake desde JavaScript...")
        
        def on_window_maximized(*args):
            """Evento cuando la ventana se maximiza."""
            print("✓ Evento 'maximized' detectado.")
            window_api._is_maximized = True
        
        def on_window_restored(*args):
            """Evento cuando la ventana se restaura desde maximizado."""
            print("✓ Evento 'restored' detectado.")
            window_api._is_maximized = False
            
        # Conectar los listeners de eventos de la ventana
        window.events.loaded += on_loaded
        window.events.closing += on_closing
        window.events.maximized += on_window_maximized
        window.events.restored += on_window_restored
        
        webview_debug = config.get("devTools_UI", False)
        print(f"✓ DevTools habilitado: {webview_debug}")
        
        webview.start(debug=webview_debug)
        print("✓ DocuFlow (webview) cerrado.")
        
    except Exception as e:
        print(f"❌ ERROR FATAL (Proceso Hijo): {e}")
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
        print("\nℹ️ Cierre solicitado (Ctrl+C). Terminando app...")
        if main_app_process.is_alive():
            main_app_process.terminate()
            main_app_process.join()
    
    print("ℹ️ Proceso del Loader finalizado.")
    sys.exit(0)

# --------------------------------------> END [ ORQUESTACIÓN (PADRE) ... ]


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()