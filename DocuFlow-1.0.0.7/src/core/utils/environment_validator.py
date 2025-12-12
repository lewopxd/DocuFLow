#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: environment_validator.py
Created: 2025-12-09
Modified: 2025-12-10
Author: @lewopxd

Description:
Centralized environment validation for DocuFlow.
- Checks MS Office COM availability
- Checks LibreOffice CLI availability
- Simple detection only - no automatic download

Usage (standalone):
    python environment_validator.py

Usage (module):
    from core.utils.environment_validator import EnvironmentValidator
    status = EnvironmentValidator.check_all()
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass, field

# Import Logger with fallback
try:
    from core.logger import Logger
except ImportError:
    class Logger:
        @staticmethod
        def _safe_print(prefix, msg):
            """Print with encoding fallback for Windows console."""
            try:
                print(f"{prefix}: {msg}")
            except UnicodeEncodeError:
                print(f"{prefix}: {msg.encode('ascii', 'replace').decode('ascii')}")
        
        @staticmethod
        def debug(msg): Logger._safe_print("DEBUG", msg)
        @staticmethod
        def info(msg): Logger._safe_print("INFO", msg)
        @staticmethod
        def warn(msg): Logger._safe_print("WARN", msg)
        @staticmethod
        def error(msg): Logger._safe_print("ERROR", msg)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EnvironmentStatus:
    """
    Estado completo del entorno de conversión.
    """
    ms_office_available: bool = False
    ms_office_version: Optional[str] = None
    ms_office_error: Optional[str] = None
    
    libreoffice_available: bool = False
    libreoffice_version: Optional[str] = None
    libreoffice_path: Optional[Path] = None
    libreoffice_error: Optional[str] = None
    
    errors: List[str] = field(default_factory=list)
    
    @property
    def has_any_converter(self) -> bool:
        """True if at least one converter is available."""
        return self.ms_office_available or self.libreoffice_available
    
    @property
    def preferred_method(self) -> Optional[str]:
        """Returns the preferred (available) conversion method."""
        if self.ms_office_available:
            return "office"
        if self.libreoffice_available:
            return "libreoffice"
        return None


# =============================================================================
# Environment Validator
# =============================================================================

class EnvironmentValidator:
    """
    Validador centralizado de entorno para DocuFlow.
    
    Verifica la disponibilidad de:
    - MS Office (Word COM automation)
    - LibreOffice (CLI headless)
    
    Uso:
        # Verificar todo
        status = EnvironmentValidator.check_all()
        
        # Verificar método específico
        is_valid, error = EnvironmentValidator.validate_for_method("libreoffice")
    """
    
    # -------------------------------------------------------------------------
    # MS Office Verification
    # -------------------------------------------------------------------------
    
    @classmethod
    def check_msoffice(cls) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verifica disponibilidad de MS Office COM.
        
        Returns:
            Tuple[available, version, error]
        """
        try:
            import win32com.client
            import pythoncom
            
            # Initialize COM
            pythoncom.CoInitialize()
            
            try:
                # Try to create Word application
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                
                # Get version
                version = word.Version
                
                # Cleanup immediately
                word.Quit()
                
                Logger.info(f"[EnvironmentValidator] MS Office disponible (Word {version})")
                return True, f"Word {version}", None
                
            finally:
                pythoncom.CoUninitialize()
                
        except ImportError:
            error = "pywin32 no está instalado (pip install pywin32)"
            Logger.warn(f"[EnvironmentValidator] {error}")
            return False, None, error
            
        except Exception as e:
            error = f"MS Office COM no disponible: {e}"
            Logger.warn(f"[EnvironmentValidator] {error}")
            return False, None, error
    
    # -------------------------------------------------------------------------
    # LibreOffice Verification
    # -------------------------------------------------------------------------
    
    @classmethod
    def check_libreoffice(cls) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Verifica disponibilidad de LibreOffice.
        
        Returns:
            Tuple[available, soffice_path, error]
        """
        try:
            from core.utils.libreoffice_manager import LibreOfficeManager
        except ImportError:
            try:
                from libreoffice_manager import LibreOfficeManager
            except ImportError:
                error = "LibreOfficeManager no disponible"
                Logger.warn(f"[EnvironmentValidator] {error}")
                return False, None, error
        
        # Check if available
        soffice_path = LibreOfficeManager.get_soffice_path()
        
        if soffice_path:
            version = LibreOfficeManager.get_version() or "Unknown"
            Logger.info(f"[EnvironmentValidator] LibreOffice disponible: {soffice_path}")
            return True, soffice_path, None
        
        # Not found
        error = "LibreOffice no encontrado. Instale LibreOffice manualmente."
        Logger.debug(f"[EnvironmentValidator] {error}")
        return False, None, error
    
    # -------------------------------------------------------------------------
    # Combined Verification
    # -------------------------------------------------------------------------
    
    @classmethod
    def check_all(cls) -> EnvironmentStatus:
        """
        Verifica todo el entorno de conversión.
        
        Returns:
            EnvironmentStatus con el estado completo
        """
        status = EnvironmentStatus()
        
        # Check MS Office
        ms_available, ms_version, ms_error = cls.check_msoffice()
        status.ms_office_available = ms_available
        status.ms_office_version = ms_version
        status.ms_office_error = ms_error
        if ms_error:
            status.errors.append(f"MS Office: {ms_error}")
        
        # Check LibreOffice
        lo_available, lo_path, lo_error = cls.check_libreoffice()
        status.libreoffice_available = lo_available
        status.libreoffice_path = lo_path
        status.libreoffice_error = lo_error
        if lo_error:
            status.errors.append(f"LibreOffice: {lo_error}")
        
        return status
    
    # -------------------------------------------------------------------------
    # Method Validation (for pre-job checks)
    # -------------------------------------------------------------------------
    
    @classmethod
    def validate_for_method(cls, method: str) -> Tuple[bool, Optional[str]]:
        """
        Valida que un método de conversión específico esté disponible.
        
        Args:
            method: "office" | "libreoffice"
            
        Returns:
            Tuple[is_valid, error_message]
        """
        method_lower = method.lower() if method else ""
        
        if method_lower == "office":
            available, version, error = cls.check_msoffice()
            if available:
                Logger.info(f"[EnvironmentValidator] Método 'office' validado ({version})")
                return True, None
            else:
                return False, f"MS Office no disponible: {error}"
        
        elif method_lower == "libreoffice":
            available, path, error = cls.check_libreoffice()
            if available:
                Logger.info(f"[EnvironmentValidator] Método 'libreoffice' validado ({path})")
                return True, None
            else:
                return False, f"LibreOffice no disponible: {error}"
        
        else:
            return False, f"Método de conversión desconocido: '{method}'"
    
    # -------------------------------------------------------------------------
    # Quick Check (for startup)
    # -------------------------------------------------------------------------
    
    @classmethod
    def quick_check(cls) -> dict:
        """
        Verificación rápida para ejecutar al inicio de la app.
        
        Returns:
            Dict con resumen del estado
        """
        status = cls.check_all()
        
        return {
            "has_any_converter": status.has_any_converter,
            "preferred_method": status.preferred_method,
            "ms_office": {
                "available": status.ms_office_available,
                "version": status.ms_office_version
            },
            "libreoffice": {
                "available": status.libreoffice_available,
                "path": str(status.libreoffice_path) if status.libreoffice_path else None
            },
            "errors": status.errors
        }


# =============================================================================
# Standalone Execution
# =============================================================================

def main():
    """
    Ejecutar verificación de entorno como script standalone.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DocuFlow Environment Validator - Verifica disponibilidad de MS Office y LibreOffice"
    )
    parser.add_argument(
        "--json",
        action="store_true", 
        help="Salida en formato JSON"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  DocuFlow Environment Validator")
    print("=" * 60)
    print()
    
    # Run full check
    status = EnvironmentValidator.check_all()
    
    if args.json:
        import json
        result = {
            "ms_office": {
                "available": status.ms_office_available,
                "version": status.ms_office_version,
                "error": status.ms_office_error
            },
            "libreoffice": {
                "available": status.libreoffice_available,
                "path": str(status.libreoffice_path) if status.libreoffice_path else None,
                "version": status.libreoffice_version,
                "error": status.libreoffice_error
            },
            "has_any_converter": status.has_any_converter,
            "preferred_method": status.preferred_method,
            "errors": status.errors
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        print("MS Office (Word COM):")
        if status.ms_office_available:
            print(f"  [OK] Disponible: {status.ms_office_version}")
        else:
            print(f"  [X] No disponible: {status.ms_office_error}")
        
        print()
        print("LibreOffice (CLI):")
        if status.libreoffice_available:
            print(f"  [OK] Disponible: {status.libreoffice_path}")
            if status.libreoffice_version:
                print(f"  [OK] Version: {status.libreoffice_version}")
        else:
            print(f"  [X] No disponible: {status.libreoffice_error}")
        
        print()
        print("-" * 60)
        if status.has_any_converter:
            print(f"[OK] Entorno listo. Metodo preferido: {status.preferred_method}")
        else:
            print("[X] No hay convertidores disponibles.")
            print("    Instale MS Office o LibreOffice para la conversion a PDF.")
        print("-" * 60)
    
    # Exit code based on availability
    sys.exit(0 if status.has_any_converter else 1)


if __name__ == "__main__":
    main()
