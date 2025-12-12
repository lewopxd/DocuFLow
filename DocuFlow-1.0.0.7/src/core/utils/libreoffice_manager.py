#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: libreoffice_manager.py
Created: 2025-12-09
Modified: 2025-12-10
Author: @lewopxd

Description:
Simple LibreOffice detection for DocuFlow.
- Auto-detects installed LibreOffice (system or portable)
- Provides path to soffice executable
- No automatic download - LibreOffice must be pre-installed
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

# Import Logger with fallback
try:
    from core.logger import Logger
except ImportError:
    class Logger:
        @staticmethod
        def debug(msg): print(f"DEBUG: {msg}")
        @staticmethod
        def info(msg): print(f"INFO: {msg}")
        @staticmethod
        def warn(msg): print(f"WARN: {msg}")
        @staticmethod
        def error(msg): print(f"ERROR: {msg}")


# =============================================================================
# Constants
# =============================================================================

# DocuFlow portable installation path
DEFAULT_INSTALL_PATH = Path.home() / "Documents" / "DocuFlow" / "libreoffice"

# Known installation locations
KNOWN_INSTALL_PATHS = [
    Path("C:/Program Files/LibreOffice/program"),
    Path("C:/Program Files (x86)/LibreOffice/program"),
    Path.home() / "AppData" / "Local" / "Programs" / "LibreOffice" / "program",
]


# =============================================================================
# LibreOffice Manager
# =============================================================================

class LibreOfficeManager:
    """
    Simple LibreOffice detection for DocuFlow.
    
    Usage:
        # Check if available
        if LibreOfficeManager.is_available():
            soffice = LibreOfficeManager.get_soffice_path()
            
        # Get path (raises if not found)
        soffice = LibreOfficeManager.ensure_available()
    """
    
    install_path: Path = DEFAULT_INSTALL_PATH
    
    # -------------------------------------------------------------------------
    # Detection
    # -------------------------------------------------------------------------
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if LibreOffice is available (any source)."""
        return cls.get_soffice_path() is not None
    
    @classmethod
    def get_soffice_path(cls) -> Optional[Path]:
        """
        Find soffice executable.
        
        Search order:
        1. DocuFlow install folder (Documents/DocuFlow/libreoffice)
        2. System PATH
        3. Standard Windows install locations
        
        Returns:
            Path to soffice.exe or None if not found
        """
        # Check DocuFlow portable install
        docuflow_soffice = cls._find_in_docuflow_install()
        if docuflow_soffice:
            return docuflow_soffice
        
        # Check system PATH
        path_soffice = cls._find_in_path()
        if path_soffice:
            return path_soffice
        
        # Check known install locations
        for known_path in KNOWN_INSTALL_PATHS:
            soffice = known_path / "soffice.exe"
            if soffice.exists():
                return soffice
        
        return None
    
    @classmethod
    def _find_in_docuflow_install(cls) -> Optional[Path]:
        """Find soffice in DocuFlow's portable install."""
        if not cls.install_path.exists():
            return None
        
        # LibreOffice Portable structure varies by version
        direct_paths = [
            cls.install_path / "LibreOfficePortable" / "App" / "libreoffice" / "program" / "soffice.exe",
            cls.install_path / "LibreOfficePortablePrevious" / "App" / "libreoffice" / "program" / "soffice.exe",
            cls.install_path / "LibreOfficePortableStill" / "App" / "libreoffice" / "program" / "soffice.exe",
            cls.install_path / "App" / "libreoffice" / "program" / "soffice.exe",
            cls.install_path / "program" / "soffice.exe",
        ]
        
        for path in direct_paths:
            if path.exists():
                return path
        
        # Glob fallback: search any LibreOffice* subfolder
        try:
            for folder in cls.install_path.glob("LibreOffice*"):
                if folder.is_dir():
                    soffice = folder / "App" / "libreoffice" / "program" / "soffice.exe"
                    if soffice.exists():
                        return soffice
        except Exception:
            pass
        
        return None
    
    @classmethod
    def _find_in_path(cls) -> Optional[Path]:
        """Find soffice in system PATH."""
        try:
            # Use 'where' on Windows
            result = subprocess.run(
                ["where", "soffice.exe"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode == 0:
                first_line = result.stdout.strip().split('\n')[0]
                return Path(first_line)
        except Exception:
            pass
        
        return None
    
    # -------------------------------------------------------------------------
    # Ensure Available
    # -------------------------------------------------------------------------
    
    @classmethod
    def ensure_available(cls) -> Path:
        """
        Ensure LibreOffice is available.
        
        Returns:
            Path to soffice.exe
            
        Raises:
            FileNotFoundError if not available
        """
        soffice = cls.get_soffice_path()
        
        if soffice:
            return soffice
        
        raise FileNotFoundError(
            "LibreOffice no encontrado. Instale LibreOffice manualmente antes de usar la conversión."
        )
    
    # -------------------------------------------------------------------------
    # Version Detection
    # -------------------------------------------------------------------------
    
    @classmethod
    def get_version(cls) -> Optional[str]:
        """
        Get LibreOffice version from version files.
        
        Reads version from config files (no subprocess - no console window).
        
        Returns:
            Version string (e.g., "LibreOffice 24.8") or None
        """
        soffice = cls.get_soffice_path()
        if not soffice:
            return None
        
        # Files to check for version info
        version_files = [
            soffice.parent / "versionrc",
            soffice.parent / "version.ini",
            soffice.parent.parent / "share" / "versionrc",
        ]
        
        for version_file in version_files:
            if version_file.exists():
                try:
                    content = version_file.read_text(encoding='utf-8', errors='ignore')
                    for line in content.split('\n'):
                        line = line.strip()
                        # Look for: ProductVersion=24.8.7.1
                        if line.startswith('ProductVersion='):
                            version = line.split('=', 1)[1].strip()
                            if version:
                                return f"LibreOffice {version}"
                        # Alternative: OOOBaseVersion=24.8
                        elif line.startswith('OOOBaseVersion='):
                            version = line.split('=', 1)[1].strip()
                            if version:
                                return f"LibreOffice {version}"
                except Exception:
                    continue
        
        # Fallback: if soffice exists, return generic version
        return "LibreOffice (instalado)"


# =============================================================================
# Convenience Functions
# =============================================================================

def get_libreoffice() -> Path:
    """Get path to LibreOffice soffice executable."""
    return LibreOfficeManager.ensure_available()


def is_libreoffice_available() -> bool:
    """Check if LibreOffice is available."""
    return LibreOfficeManager.is_available()
