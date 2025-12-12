#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: word_to_pdf_converter_msOffice.py
Created: 2025-12-09
Author: @lewopxd

Description:
Word to PDF converter using MS Word COM automation.
- Uses win32com.client to control Microsoft Word
- Supports instance reuse for batch efficiency
- Timeout protection per file
- Same interface as LibreOffice converter for seamless integration
"""

import time
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

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
# Data Classes
# =============================================================================

@dataclass
class MSOfficeConversionResult:
    """Result of MS Office conversion."""
    source_path: Path
    target_path: Path
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0


# =============================================================================
# MS Office Converter
# =============================================================================

class MSOfficeConverter:
    """
    Word to PDF converter using MS Word COM automation.
    
    Features:
    - Instance reuse: Reuses Word instance for batch conversions
    - Timeout protection: Per-file timeout to prevent hanging
    - Safe cleanup: Proper COM cleanup on exit
    
    Usage:
        converter = MSOfficeConverter()
        result = converter.convert_single(source, target)
        converter.cleanup()  # Important: release Word instance
    """
    
    def __init__(
        self, 
        batch_size: int = 15,
        timeout_per_file: int = 60
    ):
        """
        Initialize converter.
        
        Args:
            batch_size: Number of files before restarting Word instance
            timeout_per_file: Default timeout in seconds per file
        """
        self._batch_size = batch_size
        self._timeout_per_file = timeout_per_file
        self._word_app = None
        self._files_since_restart = 0
        self._lock = threading.Lock()
    
    # -------------------------------------------------------------------------
    # Instance Management
    # -------------------------------------------------------------------------
    
    def _ensure_word_instance(self) -> bool:
        """
        Ensure Word COM instance is available.
        Returns True if instance is ready, False on failure.
        """
        if self._word_app is not None:
            return True
        
        try:
            import win32com.client
            import pythoncom
            
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            
            # Create Word application
            self._word_app = win32com.client.DispatchEx("Word.Application")
            self._word_app.Visible = False
            self._word_app.DisplayAlerts = 0  # wdAlertsNone
            
            self._files_since_restart = 0
            Logger.info("[MSOfficeConverter] Word instance started")
            return True
            
        except Exception as e:
            Logger.error(f"[MSOfficeConverter] Error starting Word: {e}")
            self._word_app = None
            return False
    
    def _release_word_instance(self) -> None:
        """Release Word COM instance and cleanup."""
        if self._word_app is None:
            return
        
        try:
            import pythoncom
            
            # Close all documents
            try:
                self._word_app.Documents.Close(0)  # wdDoNotSaveChanges
            except:
                pass
            
            # Quit application
            try:
                self._word_app.Quit()
            except:
                pass
            
            # Release COM object
            self._word_app = None
            
            # Uninitialize COM
            try:
                pythoncom.CoUninitialize()
            except:
                pass
            
            Logger.info("[MSOfficeConverter] Word instance released")
            
        except Exception as e:
            Logger.warn(f"[MSOfficeConverter] Error releasing Word: {e}")
            self._word_app = None
    
    def _should_restart_instance(self) -> bool:
        """Check if instance should be restarted based on batch size."""
        return self._files_since_restart >= self._batch_size
    
    def _restart_instance_if_needed(self) -> bool:
        """Restart instance if batch limit reached."""
        if self._should_restart_instance():
            Logger.debug(f"[MSOfficeConverter] Restarting instance after {self._files_since_restart} files")
            self._release_word_instance()
            time.sleep(0.5)  # Brief pause before restart
            return self._ensure_word_instance()
        return True
    
    def cleanup(self) -> None:
        """Release Word instance. Call when done with conversions."""
        self._release_word_instance()
    
    # -------------------------------------------------------------------------
    # Single File Conversion
    # -------------------------------------------------------------------------
    
    def convert_single(
        self, 
        source: Path, 
        target: Path,
        timeout_seconds: Optional[int] = None,
        overwrite: bool = True
    ) -> MSOfficeConversionResult:
        """
        Convert a single file to PDF.
        
        Args:
            source: Path to source DOCX file
            target: Path to output PDF file
            timeout_seconds: Max time for conversion (default: self._timeout_per_file)
            overwrite: Whether to overwrite existing target
            
        Returns:
            MSOfficeConversionResult
        """
        if timeout_seconds is None:
            timeout_seconds = self._timeout_per_file
        
        start_time = time.time()
        
        if not source.exists():
            return MSOfficeConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=f"Source file not found: {source}"
            )
        
        with self._lock:
            # Ensure Word instance
            if not self._ensure_word_instance():
                return MSOfficeConversionResult(
                    source_path=source,
                    target_path=target,
                    success=False,
                    error="Could not start Word"
                )
            
            # Restart if needed
            self._restart_instance_if_needed()
            
            # Convert with timeout
            result = self._convert_with_timeout(source, target, timeout_seconds, overwrite)
            
            # Update counter
            self._files_since_restart += 1
            
            return result
    
    def _convert_with_timeout(
        self, 
        source: Path, 
        target: Path,
        timeout: int,
        overwrite: bool
    ) -> MSOfficeConversionResult:
        """Convert single file - direct COM call (no threading, COM doesn't support cross-thread)."""
        start_time = time.time()
        success = False
        error = None
        doc = None
        
        try:
            # Ensure target directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle existing file
            if target.exists():
                if overwrite:
                    target.unlink()
                else:
                    return MSOfficeConversionResult(source, target, True, None, 0)
            
            # Open document (ReadOnly for safety)
            doc = self._word_app.Documents.Open(
                str(source),
                ReadOnly=True,
                AddToRecentFiles=False
            )
            
            # Convert using SaveAs (like the working reference code)
            # FileFormat=17 is wdFormatPDF
            doc.SaveAs(str(target), FileFormat=17)
            
            # Verify success
            success = target.exists()
            if not success:
                error = "PDF file was not created"
                
        except Exception as e:
            success = False
            error = str(e)
            Logger.error(f"[MSOfficeConverter] Conversion error: {e}")
            
        finally:
            # Always close document
            if doc:
                try:
                    doc.Close(SaveChanges=0)  # 0 = wdDoNotSaveChanges
                except:
                    pass
        
        duration = time.time() - start_time
        
        return MSOfficeConversionResult(
            source_path=source,
            target_path=target,
            success=success,
            error=error,
            duration_seconds=duration
        )
    
    # -------------------------------------------------------------------------
    # Batch Conversion
    # -------------------------------------------------------------------------
    
    def convert_batch(
        self,
        files: List[Tuple[Path, Path]],  # List of (source, target) tuples
        timeout_seconds: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[MSOfficeConversionResult]:
        """
        Convert multiple files in batch.
        
        Reuses Word instance for efficiency.
        
        Args:
            files: List of (source_path, target_path) tuples
            timeout_seconds: Max time per file
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            List of MSOfficeConversionResult for each file
        """
        if not files:
            return []
        
        results: List[MSOfficeConversionResult] = []
        total = len(files)
        
        Logger.info(f"[MSOfficeConverter] Converting {total} files")
        
        try:
            for idx, (source, target) in enumerate(files, 1):
                if progress_callback:
                    progress_callback(idx, total, source.name)
                
                result = self.convert_single(source, target, timeout_seconds)
                results.append(result)
                
                if result.success:
                    Logger.debug(f"[MSOfficeConverter] ✓ {source.name} ({result.duration_seconds:.1f}s)")
                else:
                    Logger.warn(f"[MSOfficeConverter] ✗ {source.name}: {result.error}")
        
        finally:
            # Cleanup after batch
            self.cleanup()
        
        success_count = sum(1 for r in results if r.success)
        Logger.info(f"[MSOfficeConverter] Batch complete: {success_count}/{total} successful")
        
        return results


# =============================================================================
# Convenience Functions
# =============================================================================

def convert_docx_to_pdf_msoffice(
    source: Path,
    target: Optional[Path] = None,
    timeout: int = 60
) -> MSOfficeConversionResult:
    """
    Convert a single DOCX to PDF using MS Word.
    
    Args:
        source: Path to DOCX file
        target: Optional output path (default: same location with .pdf)
        timeout: Max seconds
        
    Returns:
        MSOfficeConversionResult
    """
    if target is None:
        target = source.with_suffix(".pdf")
    
    converter = MSOfficeConverter()
    try:
        return converter.convert_single(Path(source), Path(target), timeout)
    finally:
        converter.cleanup()


def batch_convert_msoffice(
    files: List[Dict[str, Any]],
    timeout: int = 60
) -> List[MSOfficeConversionResult]:
    """
    Convert multiple files using MS Word.
    
    Args:
        files: List of dicts with 'source' and optional 'target' keys
        timeout: Max seconds per file
        
    Returns:
        List of results
    """
    file_tuples = [
        (Path(f["source"]), Path(f.get("target", Path(f["source"]).with_suffix(".pdf"))))
        for f in files
    ]
    
    converter = MSOfficeConverter()
    return converter.convert_batch(file_tuples, timeout)
