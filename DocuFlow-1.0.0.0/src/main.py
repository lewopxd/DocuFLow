"""
============================================
DocuFlow 1.0 - HTML detrás de barra nativa
============================================
SOLUCIÓN: Usar MARGINS con cyTopHeight específico
para que el HTML se extienda detrás de la barra.
"""

import webview
from pathlib import Path
import sys
import ctypes
from ctypes import wintypes, byref


class WindowAPI:
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


def customize_window_chrome(window):
    """
    TÉCNICA CORRECTA: Extender SOLO el área superior (titlebar)
    para que el HTML se renderice detrás.
    """
    try:
        import time
        time.sleep(0.5)
        
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "DocuFlow")
        
        if not hwnd:
            print("⚠️ No se pudo encontrar el handle de la ventana")
            return False
        
        print(f"✓ Handle de ventana: {hwnd}")
        
        dwmapi = ctypes.windll.dwmapi
        
        # 1. Modo oscuro
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        use_dark_mode = wintypes.BOOL(True)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(use_dark_mode), ctypes.sizeof(use_dark_mode)
        )
        print("✓ Modo oscuro aplicado")
        
        # 2. Caption color transparente
        DWMWA_CAPTION_COLOR = 35
        transparent = wintypes.DWORD(0xFFFFFFFE)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR,
            byref(transparent), ctypes.sizeof(transparent)
        )
        print("✓ Caption transparente")
        
        # 3. Border color
        DWMWA_BORDER_COLOR = 34
        border = wintypes.DWORD(0x00302D2D)
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR,
            byref(border), ctypes.sizeof(border)
        )
        print("✓ Border oscuro")
        
        # 4. CLAVE: Extender SOLO el top margin
        # Esto hace que el HTML se renderice detrás de la titlebar
        class MARGINS(ctypes.Structure):
            _fields_ = [
                ("cxLeftWidth", ctypes.c_int),
                ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int),
                ("cyBottomHeight", ctypes.c_int),
            ]
        
        # Solo extendemos la parte superior (32px = altura de titlebar)
        margins = MARGINS(0, 0, 32, 0)  # Solo top=32
        result = dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))
        
        if result == 0:
            print("✅ HTML extendido detrás de la barra (32px)")
        else:
            print(f"⚠️ DwmExtendFrameIntoClientArea falló: {result}")
        
        # 5. Redibuja
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        
        user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
        )
        
        print("✅ Configuración aplicada")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if sys.platform != 'win32':
        print("⚠️ Solo Windows 10/11")
        sys.exit(1)
    
    ui_path = Path(__file__).parent / "ui" / "index.html"
    
    if not ui_path.exists():
        print(f"❌ No se encuentra: {ui_path}")
        sys.exit(1)
    
    # IMPORTANTE: background_color claro para ver si funciona
    window = webview.create_window(
        title='DocuFlow',
        url=str(ui_path),
        width=1080,
        height=600,
        resizable=True,
        frameless=False,
        min_size=(400, 200),
        background_color='#ffffff',  # BLANCO temporal para debug
        confirm_close=False,
    )
    
    api = WindowAPI(window)
    window.expose(api.minimize, api.maximize, api.close)
    
    def on_loaded():
        import threading
        thread = threading.Thread(target=customize_window_chrome, args=(window,))
        thread.daemon = True
        thread.start()
    
    window.events.loaded += on_loaded
    
    webview.start(debug=True)  # Debug=True para ver errores


if __name__ == '__main__':
    main()