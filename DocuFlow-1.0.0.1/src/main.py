"""
============================================
DocuFlow - Bridge System (Python Side)
============================================
Arquitectura de Splash Screen con Aislamiento de Procesos (Corregida)

- Proceso 1 (Padre): Ligero. Muestra splash (tkinter).
- Proceso 2 (Hijo): Pesado. Carga app (webview) como proceso NO-DAEMON.
- Importaciones pesadas (webview, tkinter) están aisladas
  dentro de sus respectivas funciones para un inicio rápido del Padre.
  
- v1.1: Añadido handler "open_file_dialog" a BridgeAPI.
"""

# --- IMPORTACIONES GLOBALES LIGERAS ---
import sys
import multiprocessing
import threading
import time
from pathlib import Path
import os

# --- Lógica del Splash Screen (Proceso Padre) ---

def show_error_dialog(message: str):
    """Muestra un diálogo de error nativo si la app principal falla."""
    # Importaciones aisladas: solo el Padre carga tkinter
    import tkinter as tk
    from tkinter import messagebox
    try:
        root = tk.Tk()
        root.withdraw()  # Ocultar la ventana raíz
        messagebox.showerror("DocuFlow - Error Fatal", message)
        root.destroy()
    except Exception as e:
        print(f"Error al mostrar el diálogo de error: {e}")

def create_splash_screen(handshake_event: multiprocessing.Event, main_app_process: multiprocessing.Process):
    """
    Crea y ejecuta el mainloop de tkinter en el HILO PRINCIPAL del Proceso Padre.
    Sondea el 'handshake_event' o si el 'main_app_process' muere.
    """
    # Importaciones aisladas: solo el Padre carga tkinter
    import tkinter as tk
    from tkinter import font as tkFont

    splash_root = tk.Tk()
    splash_root.title("DocuFlow Loader")
    
    BG_COLOR = "#1e1e1e"
    FONT_COLOR = "#cccccc"
    TITLE_FONT = tkFont.Font(family="Segoe UI", size=24, weight="bold")
    SUB_FONT = tkFont.Font(family="Segoe UI", size=12)
    
    splash_root.config(bg=BG_COLOR)
    splash_root.overrideredirect(True)
    
    if sys.platform == "win32":
        splash_root.attributes('-toolwindow', True)
        
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    window_width = 300
    window_height = 150
    x_pos = (screen_width // 2) - (window_width // 2)
    y_pos = (screen_height // 2) - (window_height // 2)
    
    splash_root.geometry(f'{window_width}x{window_height}+{x_pos}+{y_pos}')
    
    main_frame = tk.Frame(splash_root, bg=BG_COLOR)
    main_frame.pack(expand=True)
    
    tk.Label(main_frame, text="DocuFlow", font=TITLE_FONT, fg=FONT_COLOR, bg=BG_COLOR).pack(pady=(10, 5))
    tk.Label(main_frame, text="Loading...", font=SUB_FONT, fg=FONT_COLOR, bg=BG_COLOR).pack(pady=(0, 20))
    
    def check_status():
        """
        Sondea el estado:
        1. ¿Handshake completado? (Camino feliz)
        2. ¿Proceso hijo muerto? (Camino de error)
        """
        if handshake_event.is_set():
            # Camino feliz: El hijo está listo. Destruir el loader.
            splash_root.destroy()
            return
            
        if not main_app_process.is_alive():
            # Camino de error: El hijo murió inesperadamente.
            splash_root.destroy()
            print("❌ ERROR: El proceso principal (webview) falló al iniciar.")
            show_error_dialog("DocuFlow no pudo iniciarse.\n\n"
                              "El proceso principal falló. Verifique los logs.")
            return

        # Ninguna señal, seguir sondeando
        splash_root.after(100, check_status)

    splash_root.after(100, check_status)
    
    try:
        splash_root.mainloop()
    except Exception as e:
        print(f"ℹ️ Splash screen cerrado: {e}")

# --- Lógica de la Aplicación Principal (Proceso Hijo) ---

def start_webview_app(handshake_event: multiprocessing.Event):
    """
    Función que inicia la aplicación DocuFlow (pywebview).
    Esta función se ejecuta en el HILO PRINCIPAL del Proceso Hijo.
    Todas las importaciones pesadas están aisladas aquí.
    """
    
    # --- IMPORTACIONES PESADAS (AISLADAS EN EL HIJO) ---
    import webview
    import ctypes
    from ctypes import wintypes, byref
    import uuid
    import json
    from typing import Dict, Any, Callable
    from datetime import datetime

    # --- CLASES Y FUNCIONES INTERNAS (SOLO PARA EL HIJO) ---
    class BridgeAPI:
        def __init__(self, window: webview.Window, handshake_event: multiprocessing.Event, show_window_callback: Callable):
            self.window = window
            self.is_ready = False
            self.handlers: Dict[str, Callable] = {}
            self.handshake_event = handshake_event
            self.show_window = show_window_callback
            self._register_default_handlers()
        
        def _register_default_handlers(self):
            """Registra los handlers básicos del sistema"""
            self.register_handler("handshake", self._handle_handshake)
            self.register_handler("ping", self._handle_ping)
            # --- NUEVO HANDLER AÑADIDO ---
            self.register_handler("open_file_dialog", self._handle_open_file_dialog)
        
        def _handle_handshake(self, content: dict) -> dict:
            self.is_ready = True
            print("✅ Handshake completado - JS listo")
            self.show_window()
            # Activa el evento para que el Padre (Loader) se cierre
            self.handshake_event.set() 
            return {"status": "ready", "timestamp": datetime.now().isoformat(), "version": "1.0"}
        
        def _handle_ping(self, content: dict) -> dict:
            return {"pong": True, "timestamp": datetime.now().isoformat()}

        # --- NUEVO MÉTODO AÑADIDO ---
        def _handle_open_file_dialog(self, content: dict) -> dict:
            """
            Handler para abrir un diálogo de selección de archivo nativo.
            Utiliza el 'window' de la instancia de la API.
            """
            try:
                # Obtener tipos de archivo desde JS, o usar un default
                file_types = tuple(content.get('file_types', ('Todos los archivos (*.*)', '*.*')))
                
                # Llamar al diálogo de pywebview
                result = self.window.create_file_dialog(
                    webview.OPEN_DIALOG, 
                    allow_multiple=False,
                    file_types=file_types
                )
                
                if result and len(result) > 0:
                    # Devolver la ruta del primer archivo seleccionado
                    return {"filePath": result[0]}
                
                # El usuario canceló
                return {"filePath": None}
                
            except Exception as e:
                print(f"❌ Error en _handle_open_file_dialog: {e}")
                return {"filePath": None, "error": str(e)}
        
        def register_handler(self, msg_name: str, handler: Callable):
            self.handlers[msg_name] = handler
            print(f"✓ Handler registrado: {msg_name}")
        
        def handle_message(self, message: dict) -> dict:
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
            if not self.is_ready: print("⚠️ JavaScript aún no está listo"); return
            message = {"id": str(uuid.uuid4()), "msg": msg_name, "content": content or {}}
            js_code = f"window.bridgePy.receiveFromPython({json.dumps(message)})"
            self.window.evaluate_js(js_code)

    class WindowAPI:
        def __init__(self, window):
            self.window = window; self._is_maximized = False
        def minimize(self): self.window.minimize(); return True
        def maximize(self):
            if self._is_maximized: self.window.restore(); self._is_maximized = False
            else: self.window.maximize(); self._is_maximized = True
            return self._is_maximized
        def close(self): self.window.destroy(); return True

    def customize_window_chrome(window, icon_path=None):
        try:
            time.sleep(0.5) 
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "DocuFlow") 
            if not hwnd: print("⚠️ No se pudo encontrar el handle"); return False
            
            print(f"✓ Handle de ventana encontrado: {hwnd}")
            
            if icon_path and icon_path.exists():
                try:
                    IMAGE_ICON = 1; LR_LOADFROMFILE = 0x0010; WM_SETICON = 0x0080
                    ICON_SMALL = 0; ICON_BIG = 1
                    hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    hicon_small = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if hicon_big: user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                    if hicon_small: user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                    
                    shell32 = ctypes.windll.shell32
                    try: shell32.SetCurrentProcessExplicitAppUserModelID("Anthropic.DocuFlow.1.0")
                    except: pass
                    
                    GWL_EXSTYLE = -20; old_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, old_style)
                    SWP_FLAGS = 0x0020 | 0x0002 | 0x0001 | 0x0004
                    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)
                except Exception as e: print(f"⚠️ Error al aplicar icono: {e}")
            
            dwmapi = ctypes.windll.dwmapi
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            use_dark_mode = wintypes.BOOL(True)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(use_dark_mode), ctypes.sizeof(use_dark_mode))
            
            DWMWA_CAPTION_COLOR = 35; caption_color = wintypes.DWORD(0x001E1E1E)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, byref(caption_color), ctypes.sizeof(caption_color))
            
            DWMWA_BORDER_COLOR = 34; border_color = wintypes.DWORD(0x001E1E1E)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, byref(border_color), ctypes.sizeof(border_color))
            
            SWP_FLAGS = 0x0020 | 0x0002 | 0x0001 | 0x0004
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS)
            print("✅ Barra de título personalizada aplicada correctamente")
            return True
        except Exception as e:
            print(f"⚠️ No se pudo personalizar la barra: {e}"); return False

    # --- LÓGICA DE ARRANQUE DEL HIJO ---
    try:
        if sys.platform != 'win32':
            print("⚠️ Optimizado solo para Windows"); sys.exit(1)
        
        # Determinar rutas (asumiendo que main.py está en src/)
        base_path = Path(__file__).parent
        if not (base_path / "ui").exists():
             base_path = base_path.parent # Ajuste para ejecución de script

        ui_path = base_path / "ui" / "index.html"
        icon_path = base_path / "ui" / "assets" / "icon.ico"
        
        if not ui_path.exists():
            raise FileNotFoundError(f"Error: No se encuentra UI en: {ui_path}")
        
        if not icon_path.exists():
            print(f"⚠️ Icono no encontrado en: {icon_path}"); icon_path = None
        else:
            print(f"✓ Icono encontrado: {icon_path.name}")
        
        window = webview.create_window(
            title='DocuFlow', url=str(ui_path), width=1080, height=600,
            resizable=True, frameless=False, min_size=(400, 200),
            background_color='#1e1e1E', confirm_close=False, hidden=True 
        )
        
        bridge = BridgeAPI(window, handshake_event, window.show)
        window_api = WindowAPI(window)
        
        # === HANDLERS PERSONALIZADOS DEL USUARIO ===
        def handle_save_file(content: dict) -> dict:
            print(f"Guardando: {content.get('filepath')}"); return {"success": True}
        def handle_load_file(content: dict) -> dict:
            print(f"Cargando: {content.get('filepath')}"); return {"success": True, "data": "..."}
        
        bridge.register_handler("save_file", handle_save_file)
        bridge.register_handler("load_file", handle_load_file)
        
        window.expose(bridge.handle_message, window_api.minimize, window_api.maximize, window_api.close)
        
        def on_loaded():
            threading.Thread(target=customize_window_chrome, args=(window, icon_path), daemon=True).start()
            print("✅ DocuFlow (webview) iniciado correctamente")
            print("⏳ Esperando handshake desde JavaScript...")
        
        window.events.loaded += on_loaded
        
        webview.start(debug=True)
        print("✓ DocuFlow (webview) cerrado.")
        
    except Exception as e:
        print(f"❌ ERROR FATAL (Proceso Hijo): {e}")
        import traceback
        traceback.print_exc()
        # El Proceso Padre detectará esta muerte y mostrará el error.
        sys.exit(1)


# --- Lógica de Orquestación (Proceso Padre) ---
def main():
    """
    Función principal de orquestación (Proceso Padre).
    - Lanza el Proceso Hijo (webview).
    - Ejecuta el Proceso Padre (splash).
    """
    
    # 1. Crear el evento de comunicación entre procesos
    handshake_event = multiprocessing.Event()
    
    # 2. Configurar y lanzar el Proceso Hijo
    main_app_process = multiprocessing.Process(
        target=start_webview_app,
        args=(handshake_event,),
        # El hijo es independiente y sobrevive al padre.
        daemon=False 
    )
    
    try:
        main_app_process.start()
        
        # 3. Ejecutar el Splash Screen en el Hilo Principal del Proceso Padre
        create_splash_screen(handshake_event, main_app_process)
        
    except KeyboardInterrupt:
        print("\nℹ️ Cierre solicitado (Ctrl+C). Terminando app...")
        # Si el usuario cierra el loader, debemos matar al hijo
        if main_app_process.is_alive():
            main_app_process.terminate()
            main_app_process.join()
    
    # 4. Limpieza
    print("ℹ️ Proceso del Loader finalizado.")
    sys.exit(0)


if __name__ == '__main__':
    # Esta guarda es OBLIGATORIA en Windows para multiprocessing
    multiprocessing.freeze_support()
    main()