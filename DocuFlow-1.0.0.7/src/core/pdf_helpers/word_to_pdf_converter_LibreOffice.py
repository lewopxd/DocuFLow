#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: libreoffice_converter.py
Created: 2025-12-09
Author: @lewopxd

Description:
High-performance Word to PDF converter using LibreOffice CLI.
- Efficient batch mode (multiple files per command)
- Headless operation (no GUI)
- Timeout protection
- Same interface as office converter for seamless integration
"""

import os
import sys
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
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
class LibreOfficeConversionResult:
    """Result of LibreOffice conversion."""
    source_path: Path
    target_path: Path
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0


# =============================================================================
# LibreOffice Converter
# =============================================================================

class LibreOfficeConverter:
    """
    High-performance Word→PDF converter using LibreOffice CLI.
    
    Features:
    - Batch mode: Converts multiple files in single soffice invocation (~75% faster)
    - Headless: No GUI required
    - Timeout protection: Prevents hanging on problematic files
    
    Usage:
        converter = LibreOfficeConverter()
        results = converter.convert_batch(files, output_dir)
    """
    
    def __init__(self, soffice_path: Optional[Path] = None):
        """
        Initialize converter.
        
        NOTE: This class assumes LibreOffice has already been validated
        as available by the orchestrator. It does NOT download automatically.
        
        Args:
            soffice_path: Path to soffice.exe. If None, auto-detects.
        """
        self._soffice_path = soffice_path
        self._resolved_path: Optional[Path] = None
    
    def _get_soffice(self) -> Path:
        """Get path to soffice, resolving lazily."""
        if self._resolved_path:
            return self._resolved_path
        
        if self._soffice_path:
            self._resolved_path = self._soffice_path
        else:
            # Import manager here to avoid circular imports
            try:
                from core.utils.libreoffice_manager import LibreOfficeManager
            except ImportError:
                from libreoffice_manager import LibreOfficeManager
            
            # Just get path - orchestrator should have validated availability
            self._resolved_path = LibreOfficeManager.get_soffice_path()
            
            if not self._resolved_path:
                raise FileNotFoundError(
                    "LibreOffice no disponible. "
                    "El orquestador debería haber validado la disponibilidad antes de crear el conversor."
                )
        
        Logger.debug(f"[LibreOfficeConverter] Using soffice: {self._resolved_path}")
        return self._resolved_path
    
    # -------------------------------------------------------------------------
    # Single File Conversion
    # -------------------------------------------------------------------------
    
    def convert_single(
        self, 
        source: Path, 
        target: Path,
        timeout_seconds: int = 120
    ) -> LibreOfficeConversionResult:
        """
        Convert a single file to PDF.
        
        Args:
            source: Path to source DOCX file
            target: Path to output PDF file
            timeout_seconds: Max time for conversion
            
        Returns:
            LibreOfficeConversionResult
        """
        start_time = time.time()
        
        if not source.exists():
            return LibreOfficeConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=f"Source file not found: {source}"
            )
        
        # LibreOffice outputs to directory, not specific file
        # We convert to temp dir then rename
        output_dir = target.parent
        expected_output = output_dir / (source.stem + ".pdf")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            soffice = self._get_soffice()
            
            cmd = [
                str(soffice),
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(source)
            ]
            
            Logger.info(f"[LibreOffice] Convirtiendo: {source.name}")
            
            # Run with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            if result.returncode != 0:
                return LibreOfficeConversionResult(
                    source_path=source,
                    target_path=target,
                    success=False,
                    error=f"soffice failed: {result.stderr}",
                    duration_seconds=time.time() - start_time
                )
            
            # Check output exists
            if not expected_output.exists():
                return LibreOfficeConversionResult(
                    source_path=source,
                    target_path=target,
                    success=False,
                    error="Conversion produced no output",
                    duration_seconds=time.time() - start_time
                )
            
            # Rename if target path is different
            if expected_output != target:
                if target.exists():
                    target.unlink()
                shutil.move(str(expected_output), str(target))
            
            return LibreOfficeConversionResult(
                source_path=source,
                target_path=target,
                success=True,
                duration_seconds=time.time() - start_time
            )
            
        except subprocess.TimeoutExpired:
            return LibreOfficeConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=f"Timeout after {timeout_seconds}s",
                duration_seconds=timeout_seconds
            )
            
        except Exception as e:
            return LibreOfficeConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )
    
    # -------------------------------------------------------------------------
    # Batch Conversion (Efficient)
    # -------------------------------------------------------------------------
    
    def convert_batch(
        self,
        files: List[Tuple[Path, Path]],  # List of (source, target) tuples
        timeout_seconds: int = 300,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[LibreOfficeConversionResult]:
        """
        Convert multiple files efficiently.
        
        This method groups files by output directory and uses LibreOffice's
        native batch capability to convert multiple files in a single command.
        
        Args:
            files: List of (source_path, target_path) tuples
            timeout_seconds: Max time for entire batch
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            List of LibreOfficeConversionResult for each file
        """
        if not files:
            return []
        
        results: List[LibreOfficeConversionResult] = []
        start_time = time.time()
        
        # Group files by output directory for efficient batch processing
        by_output_dir: Dict[Path, List[Tuple[Path, Path]]] = {}
        for source, target in files:
            output_dir = target.parent
            if output_dir not in by_output_dir:
                by_output_dir[output_dir] = []
            by_output_dir[output_dir].append((source, target))
        
        Logger.info(f"[LibreOfficeConverter] Converting {len(files)} files in {len(by_output_dir)} batches")
        
        try:
            soffice = self._get_soffice()
        except FileNotFoundError as e:
            # Return failures for all files
            for source, target in files:
                results.append(LibreOfficeConversionResult(
                    source_path=source,
                    target_path=target,
                    success=False,
                    error=str(e)
                ))
            return results
        
        file_count = 0
        total_files = len(files)
        
        for output_dir, file_group in by_output_dir.items():
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract source files for this batch
            sources = [src for src, _ in file_group]
            
            # Build batch command
            cmd = [
                str(soffice),
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir)
            ] + [str(s) for s in sources]
            
            Logger.info(f"[LibreOffice] Procesando batch de {len(sources)} archivos...")
            
            batch_start = time.time()
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                
                batch_time = time.time() - batch_start
                
                # Check each file's result
                for source, target in file_group:
                    file_count += 1
                    
                    if progress_callback:
                        progress_callback(file_count, total_files, source.name)
                    
                    # Expected output file
                    expected = output_dir / (source.stem + ".pdf")
                    
                    if expected.exists():
                        # Rename if needed
                        if expected != target:
                            if target.exists():
                                target.unlink()
                            shutil.move(str(expected), str(target))
                        
                        results.append(LibreOfficeConversionResult(
                            source_path=source,
                            target_path=target,
                            success=True,
                            duration_seconds=batch_time / len(file_group)
                        ))
                    else:
                        results.append(LibreOfficeConversionResult(
                            source_path=source,
                            target_path=target,
                            success=False,
                            error="No output produced",
                            duration_seconds=batch_time / len(file_group)
                        ))
                
            except subprocess.TimeoutExpired:
                # All files in this batch failed
                for source, target in file_group:
                    file_count += 1
                    if progress_callback:
                        progress_callback(file_count, total_files, source.name)
                    
                    results.append(LibreOfficeConversionResult(
                        source_path=source,
                        target_path=target,
                        success=False,
                        error=f"Batch timeout after {timeout_seconds}s"
                    ))
                    
            except Exception as e:
                for source, target in file_group:
                    file_count += 1
                    if progress_callback:
                        progress_callback(file_count, total_files, source.name)
                    
                    results.append(LibreOfficeConversionResult(
                        source_path=source,
                        target_path=target,
                        success=False,
                        error=str(e)
                    ))
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.success)
        
        Logger.info(f"[LibreOfficeConverter] Batch complete: {success_count}/{len(results)} " +
                   f"in {total_time:.1f}s ({total_time/len(results):.2f}s per file)")
        
        return results
    
    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------
    
    def convert_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.docx",
        timeout_seconds: int = 300
    ) -> List[LibreOfficeConversionResult]:
        """
        Convert all matching files in a directory.
        
        Args:
            input_dir: Directory containing source files
            output_dir: Directory for output PDFs
            pattern: Glob pattern for files to convert
            timeout_seconds: Max time for batch
            
        Returns:
            List of results
        """
        sources = list(input_dir.glob(pattern))
        
        if not sources:
            Logger.warn(f"[LibreOfficeConverter] No files matching {pattern} in {input_dir}")
            return []
        
        files = [
            (src, output_dir / (src.stem + ".pdf"))
            for src in sources
        ]
        
        return self.convert_batch(files, timeout_seconds)


# =============================================================================
# Convenience Functions
# =============================================================================

def convert_docx_to_pdf_libreoffice(
    source: Path,
    target: Optional[Path] = None,
    timeout: int = 120
) -> LibreOfficeConversionResult:
    """
    Convert a single DOCX to PDF using LibreOffice.
    
    Args:
        source: Path to DOCX file
        target: Optional output path (default: same location with .pdf)
        timeout: Max seconds
        
    Returns:
        LibreOfficeConversionResult
    """
    if target is None:
        target = source.with_suffix(".pdf")
    
    converter = LibreOfficeConverter()
    return converter.convert_single(Path(source), Path(target), timeout)


def batch_convert_libreoffice(
    files: List[Dict[str, Any]],
    timeout: int = 300
) -> List[LibreOfficeConversionResult]:
    """
    Convert multiple files using LibreOffice batch mode.
    
    Args:
        files: List of dicts with 'source' and optional 'target' keys
        timeout: Max seconds for batch
        
    Returns:
        List of results
    """
    file_tuples = [
        (Path(f["source"]), Path(f.get("target", Path(f["source"]).with_suffix(".pdf"))))
        for f in files
    ]
    
    converter = LibreOfficeConverter()
    return converter.convert_batch(file_tuples, timeout)
