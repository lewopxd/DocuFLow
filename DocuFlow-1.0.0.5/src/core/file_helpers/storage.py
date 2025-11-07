"""
============================================
Project: DocuFlow
File: storage.py
Created: [2025-10-29]
Author: @lewopxd

Description:
Application data persistence system.
Manages reading, writing, and persisting configuration
and application state in JSON format.
============================================
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import os


class AppStorage:
    """
    Manages persistent storage for DocuFlow.
    Handles app configuration and state between sessions.
    """

    # --- CLASS VARIABLE: Static defaults for fallbacks ---
    DEFAULTS = {
        "providerData": {
            "window": {
                "width": 1080,
                "height": 600,
                "x": None,  # None = centered
                "y": None,
                "maximized": False
            },
            "app": {
                "last_closed_properly": False,
                "last_close_timestamp": None,
                "launch_count": 0,
                "version": "1.0.0"
            }
        },
        "uiData": {
            "theme": "dark",
            "language": "es",
            "last_opened_sheet": [],
            "last_opened_template": []
        }
    }

    #-------------------------------------------------------------
    #-------------[   INITIALIZATION   ]--------------------------
    #-------------------------------------------------------------
    
    def __init__(self, app_name: str = "DocuFlow"):
        """
        Initializes the storage system.
        
        Args:
            app_name: Name of the application (used for filenames)
        """
        self.app_name = app_name
        self.storage_dir = self._get_storage_directory()
        self.config_file = self.storage_dir / f"{app_name.lower()}_config.json"
        
        # Create directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # --- Use a copy of the static defaults for this instance ---
        self.defaults = self.DEFAULTS.copy()
        
        print(f"✓ Ruta del archivo de configuración: {self.config_file}")

    #--------------------------------------> END [ INITIALIZATION ... ]

    #-------------------------------------------------------------
    #-------------[   CORE I/O METHODS   ]------------------------
    #-------------------------------------------------------------
    
    def _get_storage_directory(self) -> Path:
        """
        Gets the appropriate OS-specific directory for app data.
        
        Returns:
            Path to the storage directory
        """
        if os.name == 'nt':  # Windows
            base = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif os.name == 'posix':
            if os.uname().sysname == 'Darwin':  # macOS
                base = Path.home() / 'Library' / 'Application Support'
            else:  # Linux
                base = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config'))
        else:
            base = Path.home()
        
        return base / self.app_name
    
    def load(self) -> Dict[str, Any]:
        """
        Loads the configuration from the JSON file.
        If it doesn't exist or is corrupt, it recreates it.
        
        Returns:
            Dictionary with the loaded configuration
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged = self._deep_merge(self.defaults.copy(), data)
                
                print(f"✓ Configuración cargada desde: {self.config_file.name}")
                return merged
            else:
                print(f"ℹ️ No se encontró configuración previa, creando archivo default...")
                # If it doesn't exist, create it with defaults
                self.save(self.DEFAULTS.copy()) 
                return self.DEFAULTS.copy()
                
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Configuración corrupta detectada en {self.config_file.name}.")
            print(f"   Detalle: {e}")
            print(f"ℹ️ Borrando archivo corrupto y restaurando valores por defecto.")
            try:
                # Intenta borrar el archivo corrupto
                self.config_file.unlink()
            except OSError as unlink_e:
                print(f"   ⚠️ No se pudo borrar el archivo corrupto: {unlink_e}")
            
            # Guarda un nuevo archivo limpio y lo retorna
            self.save(self.DEFAULTS.copy()) 
            return self.DEFAULTS.copy()
            
        except Exception as e:
            # Captura otros errores (ej. permisos)
            print(f"⚠️ Error inesperado al cargar configuración: {e}")
            print(f"ℹ️ Usando configuración por defecto (en memoria)")
            return self.DEFAULTS.copy()
    
    def save(self, data: Dict[str, Any]) -> bool:
        """
        Saves the configuration to the JSON file.
        
        Args:
            data: Dictionary with the data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # No guardamos metadata interna en el save principal
            # para mantener el archivo limpio
            clean_data = data.copy()
            if '_metadata' in clean_data:
                del clean_data['_metadata']
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False)
            
            # Solo imprimimos si no es un guardado de 'mark_improper_close'
            # para reducir el ruido al inicio
            if data.get('providerData', {}).get('app', {}).get('last_closed_properly', True):
                 print(f"✓ Configuración guardada en: {self.config_file.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error al guardar configuración: {e}")
            return False

    #--------------------------------------> END [ CORE I/O METHODS ... ]

    #-------------------------------------------------------------
    #-------------[   UI-SPECIFIC METHODS   ]---------------------
    #-------------------------------------------------------------

    def get_ui_settings(self) -> Dict[str, Any]:
        """
        Gets *only* the 'uiData' dictionary from the configuration.
        
        Returns:
            The 'uiData' settings dictionary or default 'uiData' settings.
        """
        try:
            data = self.load()
            return data.get("uiData", self.defaults.get("uiData", {}))
        except Exception as e:
            print(f"⚠️ Error al obtener uiData settings: {e}")
            return self.defaults.get("uiData", {})

    def save_ui_setting(self, key: str, value: Any) -> bool:
        """
        Saves a *single key* inside the 'uiData' dictionary.
        
        Args:
            key: The key to update (e.g., "last_opened_sheet")
            value: The new value to save
            
        Returns:
            True if saved successfully
        """
        try:
            data = self.load()
            
            if "uiData" not in data:
                data["uiData"] = self.defaults.get("uiData", {})
            
            data["uiData"][key] = value
            return self.save(data)
            
        except Exception as e:
            print(f"❌ Error al guardar uiData setting: {e}")
            return False

    def save_ui_settings_batch(self, settings: Dict[str, Any]) -> bool:
        """
        Updates the 'uiData' dictionary with multiple values at once.
        
        Args:
            settings: A dictionary of key/value pairs to update in 'uiData'
            
        Returns:
            True if saved successfully
        """
        try:
            data = self.load()
            
            if "uiData" not in data:
                data["uiData"] = self.defaults.get("uiData", {})
            
            for key, value in settings.items():
                data["uiData"][key] = value
                
            return self.save(data)
            
        except Exception as e:
            print(f"❌ Error al guardar uiData settings batch: {e}")
            return False

    #--------------------------------------> END [ UI-SPECIFIC METHODS ... ]

    #-------------------------------------------------------------
    #-------------[   GENERAL PURPOSE METHODS   ]-----------------
    #-------------------------------------------------------------

    def update(self, section: str, key: str, value: Any) -> bool:
        """
        Updates a specific value in a top-level section.
        
        Args:
            section: Top-level section ('providerData', 'uiData')
            key: Key to update
            value: New value
            
        Returns:
            True if updated successfully
        """
        try:
            data = self.load()
            
            if section not in data:
                data[section] = {}
            
            if section == "providerData" and key == "window":
                # Caso especial para 'window': fusionar, no reemplazar
                if 'window' not in data['providerData']:
                     data['providerData']['window'] = self.defaults['providerData']['window'].copy()
                data['providerData']['window'].update(value)
            else:
                data[section][key] = value
            
            return self.save(data)
            
        except Exception as e:
            print(f"❌ Error al actualizar configuración: {e}")
            return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Gets a specific value from a top-level section.
        
        Args:
            section: Top-level section
            key: Key to retrieve
            default: Value to return if not found
            
        Returns:
            The requested value or default
        """
        try:
            data = self.load()
            return data.get(section, {}).get(key, default)
        except Exception as e:
            print(f"⚠️ Error al obtener valor: {e}")
            return default
    
    def mark_proper_close(self) -> bool:
        """Marks that the application closed properly."""
        data = self.load()
        if 'providerData' not in data: data['providerData'] = self.defaults['providerData']
        if 'app' not in data['providerData']: data['providerData']['app'] = self.defaults['providerData']['app']
        
        data['providerData']['app']['last_closed_properly'] = True
        data['providerData']['app']['last_close_timestamp'] = datetime.now().isoformat()
        return self.save(data)
    
    def mark_improper_close(self) -> bool:
        """Marks that the application did NOT close properly (on launch)."""
        data = self.load()
        if 'providerData' not in data: data['providerData'] = self.defaults['providerData']
        if 'app' not in data['providerData']: data['providerData']['app'] = self.defaults['providerData']['app']

        data['providerData']['app']['last_closed_properly'] = False
        data['providerData']['app']['launch_count'] = data.get('providerData', {}).get('app', {}).get('launch_count', 0) + 1
        return self.save(data)
    
    def was_closed_properly(self) -> bool:
        """Checks if the last session closed properly."""
        data = self.load()
        return data.get('providerData', {}).get('app', {}).get('last_closed_properly', False)
    
    def save_window_state(self, width: int, height: int, x: int, y: int, maximized: bool = False) -> bool:
        """Saves the window's state."""
        data = self.load()
        if 'providerData' not in data: data['providerData'] = self.defaults['providerData']
        
        data['providerData']['window'] = {
            'width': width,
            'height': height,
            'x': x,
            'y': y,
            'maximized': maximized
        }
        return self.save(data)
    
    def get_window_state(self) -> Dict[str, Any]:
        """Gets the saved window state."""
        data = self.load()
        default_window = self.defaults.get('providerData', {}).get('window', {})
        # Fusionar el estado guardado con el default para evitar errores si faltan claves
        current_state = default_window.copy()
        current_state.update(data.get('providerData', {}).get('window', {}))
        return current_state
    
    # --- NUEVA FUNCIÓN ---
    def finalize_session_save(self, window_state: Dict[str, Any]) -> bool:
        """
        Carga la configuración, actualiza el estado de la ventana Y el estado
        de cierre de la app, y luego guarda el archivo UNA SOLA VEZ.
        """
        try:
            data = self.load()
            
            # 1. Actualizar estado de la ventana
            if 'providerData' not in data: data['providerData'] = self.defaults['providerData']
            data['providerData']['window'] = window_state
            
            # 2. Actualizar estado de la app (cierre correcto)
            if 'app' not in data['providerData']: data['providerData']['app'] = self.defaults['providerData']['app']
            data['providerData']['app']['last_closed_properly'] = True
            data['providerData']['app']['last_close_timestamp'] = datetime.now().isoformat()
            
            # 3. Guardar una sola vez
            print("✓ Guardando estado final de la sesión...")
            return self.save(data)
            
        except Exception as e:
            print(f"❌ Error al guardar sesión final: {e}")
            return False
    # --- FIN DE LA NUEVA FUNCIÓN ---
    
    def reset_to_defaults(self) -> bool:
        """Resets the configuration to defaults."""
        print("⚠️ Reseteando configuración a valores por defecto")
        return self.save(self.DEFAULTS.copy())
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merges two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def get_storage_path(self) -> str:
        """Returns the full path to the config file."""
        return str(self.config_file)
    
    def delete_config(self) -> bool:
        """Deletes the config file. This cannot be undone."""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
                print(f"✓ Configuración eliminada: {self.config_file}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error al eliminar configuración: {e}")
            return False

    #--------------------------------------> END [ GENERAL PURPOSE METHODS ... ]