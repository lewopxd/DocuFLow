"""
============================================
DocuFlow - Bridge System (Python Side)
============================================
Sistema de comunicación bidireccional robusto
con handshake, cola de mensajes y reintentos.
"""

import webview
from pathlib import Path
import sys
import ctypes
from ctypes import wintypes, byref
import uuid
import json
from typing import Dict, Any, Callable
from datetime import datetime


class BridgeAPI:
    """
    API de comunicación entre Python y JavaScript.
    Maneja handshake, mensajes con ID único y respuestas.
    """
    
    def __init__(self, window):
        self.window = window
        self.is_ready = False
        self.handlers: Dict[str, Callable] = {}
        
        # Registrar handlers por defecto
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Registra los handlers básicos del sistema"""
        self.register_handler("handshake", self._handle_handshake)
        self.register_handler("ping", self._handle_ping)
    
    def _handle_handshake(self, content: dict) -> dict:
        """Handler del handshake inicial"""
        self.is_ready = True
        print("✅ Handshake completado - JS listo")
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def _handle_ping(self, content: dict) -> dict:
        """Handler para verificar que Python está escuchando"""
        return {"pong": True, "timestamp": datetime.now().isoformat()}
    
    def register_handler(self, msg_name: str, handler: Callable):
        """
        Registra un handler para un tipo de mensaje.
        
        Args:
            msg_name: Nombre del mensaje (ej: "save_file", "load_data")
            handler: Función que procesa el mensaje y retorna respuesta
                     Firma: handler(content: dict) -> dict
        """
        self.handlers[msg_name] = handler
        print(f"✓ Handler registrado: {msg_name}")
    
    def handle_message(self, message: dict) -> dict:
        """
        Procesa un mensaje desde JavaScript.
        
        Args:
            message: {id: str, msg: str, content: dict}
        
        Returns:
            {id: str, response: "ok"/"error", content: dict}
        """
        try:
            msg_id = message.get("id")
            msg_name = message.get("msg")
            content = message.get("content", {})
            
            if not msg_id or not msg_name:
                return {
                    "id": msg_id or "unknown",
                    "response": "error",
                    "content": {"error": "Mensaje inválido: falta id o msg"}
                }
            
            # Buscar handler
            handler = self.handlers.get(msg_name)
            
            if not handler:
                return {
                    "id": msg_id,
                    "response": "error",
                    "content": {"error": f"Handler no encontrado: {msg_name}"}
                }
            
            # Ejecutar handler
            result = handler(content)
            
            return {
                "id": msg_id,
                "response": "ok",
                "content": result
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Error procesando mensaje: {e}")
            print(error_details)
            
            return {
                "id": message.get("id", "unknown"),
                "response": "error",
                "content": {
                    "error": str(e),
                    "traceback": error_details
                }
            }
    
    def send_to_js(self, msg_name: str, content: dict = None):
        """
        Envía un mensaje a JavaScript (sin esperar respuesta).
        
        Args:
            msg_name: Nombre del mensaje
            content: Contenido opcional
        """
        if not self.is_ready:
            print("⚠️ JavaScript aún no está listo")
            return
        
        message = {
            "id": str(uuid.uuid4()),
            "msg": msg_name,
            "content": content or {}
        }
        
        # Evaluar JavaScript para enviar el mensaje
        js_code = f"window.bridgePy.receiveFromPython({json.dumps(message)})"
        self.window.evaluate_js(js_code)


class WindowAPI:
    """API para controlar la ventana"""
    
    def __init__(self, window):
        self.window = window
        self._is_maximized = False
    
    def minimize(self):
        self.window.minimize()
        return True
    
    def maximize(self):
        if self._is_maximized:
            self.window.restore()
            self._is_maximized = False
        else:
            self.window.maximize()
            self._is_maximized = True
        return self._is_maximized
    
    def close(self):
        self.window.destroy()
        return True


def customize_window_chrome(window, icon_path=None):
    """Personaliza la barra de título nativa"""
    try:
        import time
        time.sleep(0.5)
        
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "DocuFlow")
        
        if not hwnd:
            print("⚠️ No se pudo encontrar el handle de la ventana")
            return False
        
        print(f"✓ Handle de ventana encontrado: {hwnd}")
        
        # Aplicar icono
        if icon_path and icon_path.exists():
            try:
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x0010
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                
                hicon_big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                hicon_small = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                
                if hicon_big:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                    print("✓ Icono grande aplicado (taskbar)")
                    
                if hicon_small:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                    print("✓ Icono pequeño aplicado (titlebar)")
                
                # Forzar actualización en taskbar
                shell32 = ctypes.windll.shell32
                try:
                    app_id = "Anthropic.DocuFlow.1.0"
                    shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                    print("✓ App ID establecido")
                except:
                    pass
                
                GWL_EXSTYLE = -20
                old_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, old_style)
                
                SWP_FRAMECHANGED = 0x0020
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                   SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
                
                print("✓ Icono de taskbar actualizado")
                    
            except Exception as e:
                print(f"⚠️ Error al aplicar icono: {e}")
        
        dwmapi = ctypes.windll.dwmapi
        
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        use_dark_mode = wintypes.BOOL(True)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(use_dark_mode), ctypes.sizeof(use_dark_mode)
        )
        print("✓ Modo oscuro aplicado")
        
        DWMWA_CAPTION_COLOR = 35
        caption_color = wintypes.DWORD(0x001E1E1E)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR,
            byref(caption_color), ctypes.sizeof(caption_color)
        )
        print("✓ Caption color #1e1e1e aplicado")
        
        DWMWA_BORDER_COLOR = 34
        border_color = wintypes.DWORD(0x001E1E1E)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR,
            byref(border_color), ctypes.sizeof(border_color)
        )
        print("✓ Border color #1e1e1e aplicado")
        
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        
        user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
        )
        
        print("✅ Barra de título personalizada aplicada correctamente")
        return True
        
    except Exception as e:
        print(f"⚠️ No se pudo personalizar la barra: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal que inicia DocuFlow"""
    
    if sys.platform != 'win32':
        print("⚠️ DocuFlow está optimizado solo para Windows 10/11")
        sys.exit(1)
    
    ui_path = Path(__file__).parent / "ui" / "index.html"
    icon_path = Path(__file__).parent / "ui" / "assets" / "icon.ico"
    
    if not ui_path.exists():
        print(f"❌ Error: No se encuentra el archivo UI en: {ui_path}")
        sys.exit(1)
    
    if not icon_path.exists():
        print(f"⚠️ Icono no encontrado en: {icon_path}")
        icon_path = None
    else:
        print(f"✓ Icono encontrado: {icon_path.name}")
    
    # Crear ventana
    window = webview.create_window(
        title='DocuFlow',
        url=str(ui_path),
        width=1080,
        height=600,
        resizable=True,
        frameless=False,
        min_size=(400, 200),
        background_color='#1e1e1e',
        confirm_close=False,
    )
    
    # Crear APIs
    bridge = BridgeAPI(window)
    window_api = WindowAPI(window)
    
    # ===================================
    # REGISTRAR TUS HANDLERS AQUÍ
    # ===================================
    
    def handle_save_file(content: dict) -> dict:
        """Ejemplo: Handler para guardar archivos"""
        filepath = content.get("filepath")
        data = content.get("data")
        
        # Tu lógica aquí
        print(f"Guardando archivo: {filepath}")
        
        return {
            "success": True,
            "filepath": filepath,
            "bytes_written": len(str(data))
        }
    
    def handle_load_file(content: dict) -> dict:
        """Ejemplo: Handler para cargar archivos"""
        filepath = content.get("filepath")
        
        # Tu lógica aquí
        print(f"Cargando archivo: {filepath}")
        
        return {
            "success": True,
            "data": "contenido del archivo",
            "filepath": filepath
        }
    
    # Registrar handlers personalizados
    bridge.register_handler("save_file", handle_save_file)
    bridge.register_handler("load_file", handle_load_file)
    
    # Exponer APIs a JavaScript
    window.expose(
        bridge.handle_message,
        window_api.minimize,
        window_api.maximize,
        window_api.close
    )
    
    # Evento cuando la ventana esté lista
    def on_loaded():
        import threading
        thread = threading.Thread(target=customize_window_chrome, args=(window, icon_path))
        thread.daemon = True
        thread.start()
        print("✅ DocuFlow iniciado correctamente")
        print("⏳ Esperando handshake desde JavaScript...")
    
    window.events.loaded += on_loaded
    
    # Iniciar aplicación
    webview.start(debug=False)


if __name__ == '__main__':
    main()