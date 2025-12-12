#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: pdf_converter_engine.py
Created: 2025-12-09
Author: @lewopxd

Description:
Core PDF conversion engine with smart instance management.
Handles Word→PDF conversion using MS Word COM automation with:
- Automatic batch size calculation based on available RAM
- Manual batch size override option
- Per-file timeout protection
- Instance lifecycle management (reuse across batches)

Methods supported:
- "office" (default): Uses Microsoft Word COM automation
- "libreoffice": Future support for LibreOffice CLI
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable
from enum import Enum
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Import post-processor classes
try:
    from core.pdf_helpers.pdf_post_processor import (
        CompressionConfig, 
        MetadataConfig, 
        PdfPostProcessor,
        PostProcessResult
    )
except ImportError:
    # Fallback for direct execution
    try:
        from pdf_post_processor import (
            CompressionConfig, 
            MetadataConfig, 
            PdfPostProcessor,
            PostProcessResult
        )
    except ImportError:
        CompressionConfig = None
        MetadataConfig = None
        PdfPostProcessor = None
        PostProcessResult = None

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
# Configuration Classes
# =============================================================================

class ConversionMethod(Enum):
    """Supported conversion methods."""
    OFFICE = "office"       # MS Word COM automation
    LIBREOFFICE = "libreoffice"  # LibreOffice CLI

# Import LibreOffice converter (lazy to avoid circular imports)
LIBREOFFICE_CONVERTER_AVAILABLE = False
LibreOfficeConverter = None

def _get_libreoffice_converter():
    """Lazy import of LibreOfficeConverter."""
    global LIBREOFFICE_CONVERTER_AVAILABLE, LibreOfficeConverter
    if LibreOfficeConverter is not None:
        return LibreOfficeConverter
    try:
        from core.pdf_helpers.word_to_pdf_converter_LibreOffice import LibreOfficeConverter as LOConverter
        LibreOfficeConverter = LOConverter
        LIBREOFFICE_CONVERTER_AVAILABLE = True
        return LibreOfficeConverter
    except ImportError:
        try:
            from word_to_pdf_converter_LibreOffice import LibreOfficeConverter as LOConverter
            LibreOfficeConverter = LOConverter
            LIBREOFFICE_CONVERTER_AVAILABLE = True
            return LibreOfficeConverter
        except ImportError:
            LIBREOFFICE_CONVERTER_AVAILABLE = False
            return None


# Import MS Office converter (lazy to avoid circular imports)
MSOFFICE_CONVERTER_AVAILABLE = False
MSOfficeConverter = None

def _get_msoffice_converter():
    """Lazy import of MSOfficeConverter."""
    global MSOFFICE_CONVERTER_AVAILABLE, MSOfficeConverter
    if MSOfficeConverter is not None:
        return MSOfficeConverter
    try:
        from core.pdf_helpers.word_to_pdf_converter_msOffice import MSOfficeConverter as MOConverter
        MSOfficeConverter = MOConverter
        MSOFFICE_CONVERTER_AVAILABLE = True
        return MSOfficeConverter
    except ImportError:
        try:
            from word_to_pdf_converter_msOffice import MSOfficeConverter as MOConverter
            MSOfficeConverter = MOConverter
            MSOFFICE_CONVERTER_AVAILABLE = True
            return MSOfficeConverter
        except ImportError:
            MSOFFICE_CONVERTER_AVAILABLE = False
            return None


@dataclass
class InstanceManagementConfig:
    """Configuration for Word instance management."""
    mode: str = "auto"              # "auto" | "fixed"
    batch_size: int = 15            # Files per instance (if mode="fixed")
    max_memory_mb: int = 2048       # Max RAM before restart
    timeout_per_file_seconds: int = 60  # Timeout for single conversion
    safety_margin: float = 0.7      # Use 70% of available RAM
    min_batch_size: int = 5         # Minimum batch size
    max_batch_size: int = 50        # Maximum batch size


@dataclass
class PdfConverterConfig:
    """Main configuration for PDF converter engine."""
    method: ConversionMethod = ConversionMethod.OFFICE
    instance_management: InstanceManagementConfig = field(default_factory=InstanceManagementConfig)
    keep_source: bool = True        # Don't delete source files
    overwrite: bool = True          # Overwrite existing PDFs
    use_temp_copy: bool = True      # Work on temp copies
    # Post-processing options
    compression: Optional['CompressionConfig'] = None
    metadata: Optional['MetadataConfig'] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PdfConverterConfig':
        """Create config from dictionary."""
        im_data = data.get("instance_management", {})
        im_config = InstanceManagementConfig(
            mode=im_data.get("mode", "auto"),
            batch_size=im_data.get("batch_size", 15),
            max_memory_mb=im_data.get("max_memory_mb", 2048),
            timeout_per_file_seconds=im_data.get("timeout_per_file_seconds", 60),
            safety_margin=im_data.get("safety_margin", 0.7),
            min_batch_size=im_data.get("min_batch_size", 5),
            max_batch_size=im_data.get("max_batch_size", 50)
        )
        
        method_str = data.get("method", "office").lower()
        method = ConversionMethod(method_str) if method_str in [m.value for m in ConversionMethod] else ConversionMethod.OFFICE
        
        # Parse compression config (default: enabled=true, level=high)
        compression_data = data.get("compression", {})
        compression_config = None
        if CompressionConfig is not None:
            compression_config = CompressionConfig.from_dict(compression_data) if compression_data else CompressionConfig()
        
        # Parse metadata config (default: author="", creator=MSWORD, producer=MSWORD)
        metadata_data = data.get("metadata", {})
        metadata_config = None
        if MetadataConfig is not None:
            metadata_config = MetadataConfig.from_dict(metadata_data) if metadata_data else MetadataConfig()
        
        return cls(
            method=method,
            instance_management=im_config,
            keep_source=data.get("keep_source", True),
            overwrite=data.get("overwrite", True),
            use_temp_copy=data.get("use_temp_copy", True),
            compression=compression_config,
            metadata=metadata_config
        )


@dataclass
class ConversionTask:
    """Represents a single file conversion task."""
    source_path: Path
    target_path: Path
    metadata: Optional[Dict[str, str]] = None
    row_data: Optional[Dict[str, Any]] = None  # For placeholder resolution


@dataclass
class ConversionResult:
    """Result of a single conversion."""
    source_path: Path
    target_path: Path
    success: bool
    error: Optional[str] = None
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    # Post-processing stats
    original_size_bytes: int = 0
    compression_applied: bool = False
    metadata_applied: bool = False
    
    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage from compression."""
        if self.original_size_bytes == 0:
            return 0.0
        return (1 - self.file_size_bytes / self.original_size_bytes) * 100


# =============================================================================
# Smart Batch Size Calculator
# =============================================================================

def calculate_optimal_batch_size(config: InstanceManagementConfig) -> int:
    """
    Calcula el tamaño óptimo de batch basado en recursos del sistema.
    
    MS Word típicamente usa:
    - Base: ~100-200MB por instancia
    - Por documento: ~5-15MB adicionales (depende del tamaño)
    """
    try:
        import psutil
        
        # 1. Obtener memoria disponible
        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 * 1024)
        
        # 2. Estimar uso por archivo (valores empíricos conservadores)
        base_office_memory = 180  # MB - baseline Word + COM overhead
        per_file_overhead = 10    # MB - promedio por documento
        
        # 3. Aplicar margen de seguridad y límite de config
        usable_memory = min(available_mb * config.safety_margin, config.max_memory_mb)
        
        # 4. Calcular batch size
        if usable_memory <= base_office_memory:
            batch_size = config.min_batch_size  # Poca RAM, mínimo batch
        else:
            batch_size = int((usable_memory - base_office_memory) / per_file_overhead)
        
        # 5. Aplicar límites
        batch_size = max(config.min_batch_size, min(batch_size, config.max_batch_size))
        
        Logger.debug(f"[ConverterEngine] RAM disponible: {available_mb:.0f}MB, " +
                    f"Batch size calculado: {batch_size}")
        
        return batch_size
        
    except ImportError:
        Logger.warn("[ConverterEngine] psutil no disponible, usando batch_size por defecto")
        return config.batch_size
    except Exception as e:
        Logger.warn(f"[ConverterEngine] Error calculando batch size: {e}")
        return config.batch_size


# =============================================================================
# PDF Converter Engine
# =============================================================================

class PdfConverterEngine:
    """
    Motor principal de conversión Word→PDF con gestión inteligente de instancias.
    
    Uso:
        engine = PdfConverterEngine(config)
        results = engine.convert_batch(tasks)
        engine.cleanup()
    """
    
    def __init__(self, config: Optional[PdfConverterConfig] = None):
        self._config = config or PdfConverterConfig()
        self._word_app = None
        self._files_since_restart = 0
        self._batch_size = self._determine_batch_size()
        self._temp_dir: Optional[Path] = None
        self._lock = threading.Lock()
        self._is_cancelled = threading.Event()
        self._is_paused = threading.Event()
        self._is_paused.set()  # Start unblocked (not paused)
    
    def pause(self) -> None:
        """Signal pause."""
        self._is_paused.clear()
    
    def resume(self) -> None:
        """Signal resume."""
        self._is_paused.set()
    
    def _check_cancelled(self) -> bool:
        """Check if cancelled."""
        return self._is_cancelled.is_set()
    
    def _wait_if_paused(self) -> None:
        """Block if paused until resumed or cancelled."""
        while not self._is_paused.is_set() and not self._is_cancelled.is_set():
            time.sleep(0.1)
    
    def validate_environment(self) -> Tuple[bool, Optional[str]]:
        """
        Valida que el entorno esté listo para conversiones.
        
        Debe llamarse UNA VEZ antes de iniciar un batch de conversiones.
        Verifica que el método de conversión configurado (office/libreoffice)
        esté disponible.
        
        NOTE: This method no longer downloads LibreOffice automatically.
        The orchestrator should handle installation via LibreOfficeSetupDialog.
        
        Returns:
            Tuple[is_valid, error_message]
            - is_valid: True si el entorno está listo
            - error_message: Mensaje de error si is_valid=False, None si OK
        """
        try:
            from core.utils.environment_validator import EnvironmentValidator
        except ImportError:
            try:
                from environment_validator import EnvironmentValidator
            except ImportError:
                # Fallback: basic check without validator
                Logger.warn("[ConverterEngine] EnvironmentValidator no disponible, usando verificación básica")
                return self._basic_environment_check()
        
        method = self._config.method.value  # "office" o "libreoffice"
        
        Logger.info(f"[ConverterEngine] Validando entorno para método: {method}")
        
        return EnvironmentValidator.validate_for_method(method)
    
    def _basic_environment_check(self) -> Tuple[bool, Optional[str]]:
        """Verificación básica cuando EnvironmentValidator no está disponible."""
        if self._config.method == ConversionMethod.OFFICE:
            try:
                import win32com.client
                return True, None
            except ImportError:
                return False, "pywin32 no disponible para MS Office COM"
        elif self._config.method == ConversionMethod.LIBREOFFICE:
            LOConverter = _get_libreoffice_converter()
            if LOConverter is None:
                return False, "LibreOffice converter no disponible"
            return True, None
        else:
            return False, f"Método desconocido: {self._config.method}"
    
    def _determine_batch_size(self) -> int:
        """Determine batch size based on config mode."""
        if self._config.instance_management.mode == "fixed":
            return self._config.instance_management.batch_size
        else:
            return calculate_optimal_batch_size(self._config.instance_management)
    
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
            Logger.debug("[ConverterEngine] Instancia de Word iniciada")
            return True
            
        except Exception as e:
            Logger.error(f"[ConverterEngine] Error iniciando Word: {e}")
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
            
            Logger.debug("[ConverterEngine] Instancia de Word liberada")
            
        except Exception as e:
            Logger.warn(f"[ConverterEngine] Error liberando Word: {e}")
            self._word_app = None
    
    def _should_restart_instance(self) -> bool:
        """Check if instance should be restarted based on batch size."""
        return self._files_since_restart >= self._batch_size
    
    def _restart_instance_if_needed(self) -> bool:
        """Restart instance if batch limit reached."""
        if self._should_restart_instance():
            Logger.debug(f"[ConverterEngine] Reiniciando instancia después de {self._files_since_restart} archivos")
            self._release_word_instance()
            time.sleep(0.5)  # Brief pause before restart
            return self._ensure_word_instance()
        return True
    
    # -------------------------------------------------------------------------
    # Temp Directory Management
    # -------------------------------------------------------------------------
    
    def _get_temp_dir(self) -> Path:
        """Get or create temp directory."""
        if self._temp_dir is None or not self._temp_dir.exists():
            self._temp_dir = Path(tempfile.mkdtemp(prefix="docuflow_pdf_"))
        return self._temp_dir
    
    def _cleanup_temp_dir(self) -> None:
        """Remove temp directory if exists."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
            except Exception as e:
                Logger.warn(f"[ConverterEngine] Error limpiando temp: {e}")
    
    # -------------------------------------------------------------------------
    # Single File Conversion
    # -------------------------------------------------------------------------
    
    def _convert_single_with_timeout(
        self, 
        source: Path, 
        target: Path,
        timeout: int
    ) -> ConversionResult:
        """
        Convert single file with timeout protection.
        Uses ThreadPoolExecutor for timeout handling.
        """
        start_time = time.time()
        
        def do_conversion() -> Tuple[bool, Optional[str]]:
            """Inner conversion function."""
            try:
                # Ensure target directory exists
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Handle existing file
                if target.exists():
                    if self._config.overwrite:
                        target.unlink()
                    else:
                        return True, None  # Already exists, skip
                
                # Open document
                doc = self._word_app.Documents.Open(
                    str(source),
                    ReadOnly=True,
                    AddToRecentFiles=False
                )
                
                try:
                    # Export to PDF
                    # wdExportFormatPDF = 17
                    doc.ExportAsFixedFormat(
                        str(target),
                        17,  # wdExportFormatPDF
                        False,  # OpenAfterExport
                        0,  # wdExportOptimizeForPrint
                        0,  # Range - wdExportAllDocument
                        1,  # From
                        1,  # To
                        0,  # Item - wdExportDocumentContent
                        True,  # IncludeDocProps
                        True,  # KeepIRM
                        1,  # CreateBookmarks - wdExportCreateHeadingBookmarks
                    )
                finally:
                    doc.Close(0)  # wdDoNotSaveChanges
                
                return True, None
                
            except Exception as e:
                return False, str(e)
        
        # Run with timeout
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_conversion)
                success, error = future.result(timeout=timeout)
        except FuturesTimeoutError:
            success = False
            error = f"Timeout después de {timeout}s"
            # Try to recover Word instance
            self._release_word_instance()
        except Exception as e:
            success = False
            error = str(e)
        
        duration = time.time() - start_time
        file_size = target.stat().st_size if target.exists() else 0
        
        return ConversionResult(
            source_path=source,
            target_path=target,
            success=success,
            error=error,
            duration_seconds=duration,
            file_size_bytes=file_size
        )
    
    def convert_single(
        self, 
        source: Path, 
        target: Path,
        timeout: Optional[int] = None,
        row_data: Optional[Dict[str, Any]] = None
    ) -> ConversionResult:
        """
        Convert a single Word file to PDF.
        
        Args:
            source: Path to source .docx file
            target: Path to output .pdf file
            timeout: Override default timeout (seconds)
            row_data: Optional row data for placeholder resolution in metadata
            
        Returns:
            ConversionResult with success/error status
        """
        if timeout is None:
            timeout = self._config.instance_management.timeout_per_file_seconds
        
        # Validate source
        if not source.exists():
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=f"Archivo no encontrado: {source}"
            )
        
        # Work on temp copy if configured
        working_source = source
        if self._config.use_temp_copy:
            temp_dir = self._get_temp_dir()
            working_source = temp_dir / source.name
            shutil.copy2(source, working_source)
        
        try:
            # ---- DISPATCH BY METHOD ----
            if self._config.method == ConversionMethod.LIBREOFFICE:
                # Use LibreOffice CLI
                result = self._convert_single_libreoffice(working_source, target, timeout)
            else:
                # Use MS Word COM (default)
                result = self._convert_single_office(working_source, target, timeout)
            
            # Apply post-processing if conversion was successful
            if result.success and target.exists():
                result = self._apply_post_processing(result, row_data)
            
            return result
            
        finally:
            # Cleanup temp copy
            if self._config.use_temp_copy and working_source != source:
                try:
                    working_source.unlink()
                except:
                    pass
    
    def _convert_single_office(
        self, 
        source: Path, 
        target: Path, 
        timeout: int
    ) -> ConversionResult:
        """Convert using MS Word COM automation."""
        start_time = time.time()
        
        MOConverter = _get_msoffice_converter()
        if MOConverter is None:
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error="MS Office converter not available"
            )
        
        try:
            # Use shared converter instance
            if not hasattr(self, '_msoffice_converter') or self._msoffice_converter is None:
                batch_size = self._config.instance_management.batch_size
                self._msoffice_converter = MOConverter(
                    batch_size=batch_size,
                    timeout_per_file=timeout
                )
            
            mo_result = self._msoffice_converter.convert_single(source, target, timeout)
            
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=mo_result.success,
                error=mo_result.error,
                duration_seconds=mo_result.duration_seconds
            )
            
        except Exception as e:
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )
    
    def _convert_single_libreoffice(
        self, 
        source: Path, 
        target: Path, 
        timeout: int
    ) -> ConversionResult:
        """Convert using LibreOffice CLI."""
        start_time = time.time()
        
        LOConverter = _get_libreoffice_converter()
        if LOConverter is None:
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error="LibreOffice converter not available"
            )
        
        try:
            # LibreOffice availability should be validated by orchestrator
            converter = LOConverter()
            lo_result = converter.convert_single(source, target, timeout)
            
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=lo_result.success,
                error=lo_result.error,
                duration_seconds=lo_result.duration_seconds
            )
            
        except Exception as e:
            return ConversionResult(
                source_path=source,
                target_path=target,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )
    
    def _apply_post_processing(
        self, 
        result: ConversionResult, 
        row_data: Optional[Dict[str, Any]] = None
    ) -> ConversionResult:
        """
        Apply compression and metadata to converted PDF.
        
        Args:
            result: The conversion result with target PDF path
            row_data: Optional row data for placeholder resolution
            
        Returns:
            Updated ConversionResult with post-processing stats
        """
        if PdfPostProcessor is None:
            # Post-processor not available
            return result
        
        original_size = result.file_size_bytes
        compression_applied = False
        metadata_applied = False
        
        try:
            # Create post-processor with config
            processor = PdfPostProcessor(
                compression=self._config.compression,
                metadata=self._config.metadata
            )
            
            # Apply post-processing
            pp_result = processor.process(result.target_path, row_data)
            
            if pp_result.success:
                compression_applied = pp_result.compression_applied
                metadata_applied = pp_result.metadata_applied
                
                # Update file size after processing
                final_size = result.target_path.stat().st_size if result.target_path.exists() else 0
                
                return ConversionResult(
                    source_path=result.source_path,
                    target_path=result.target_path,
                    success=True,
                    error=None,
                    duration_seconds=result.duration_seconds,
                    file_size_bytes=final_size,
                    original_size_bytes=original_size,
                    compression_applied=compression_applied,
                    metadata_applied=metadata_applied
                )
            else:
                Logger.warn(f"[ConverterEngine] Post-processing falló: {pp_result.error}")
                # Return original result, conversion was still successful
                return result
                
        except Exception as e:
            Logger.warn(f"[ConverterEngine] Error en post-processing: {e}")
            # Return original result, conversion was still successful
            return result
    
    # -------------------------------------------------------------------------
    # Batch Conversion
    # -------------------------------------------------------------------------
    
    def convert_batch(
        self, 
        tasks: List[ConversionTask],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[ConversionResult]:
        """
        Convert multiple files in batch with instance management.
        
        Args:
            tasks: List of ConversionTask objects
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            List of ConversionResult objects
        """
        results: List[ConversionResult] = []
        total = len(tasks)
        
        if total == 0:
            return results
        
        Logger.info(f"[ConverterEngine] Iniciando conversión de {total} archivos " +
                   f"(batch_size={self._batch_size})")
        
        # Resume event starts set (not paused)
        self._is_paused.set()
        self._is_cancelled.clear()
        
        try:
            for idx, task in enumerate(tasks, 1):
                # Check cancellation
                if self._check_cancelled():
                    Logger.info("[ConverterEngine] Conversión cancelada")
                    break
                
                # Wait if paused
                self._wait_if_paused()
                if self._check_cancelled():
                    break
                
                # Progress callback
                if progress_callback:
                    progress_callback(idx, total, task.source_path.name)
                
                # Convert (pass row_data for metadata placeholders)
                result = self.convert_single(
                    task.source_path, 
                    task.target_path,
                    row_data=task.row_data
                )
                results.append(result)
                
                if result.success:
                    Logger.debug(f"[ConverterEngine] ✓ {task.source_path.name} " +
                               f"({result.duration_seconds:.1f}s)")
                else:
                    Logger.warn(f"[ConverterEngine] ✗ {task.source_path.name}: {result.error}")
            
        finally:
            # Always release instance at end of batch
            self._release_word_instance()
            self._cleanup_temp_dir()
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        Logger.info(f"[ConverterEngine] Batch completado: {success_count}/{len(results)} exitosos")
        
        return results
    
    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    
    def cleanup(self) -> None:
        """Release all resources."""
        self._release_word_instance()
        self._cleanup_temp_dir()


# =============================================================================
# Convenience Functions
# =============================================================================

def convert_word_to_pdf(
    source: Path,
    target: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None
) -> ConversionResult:
    """
    Convenience function to convert a single Word file to PDF.
    
    Args:
        source: Path to .docx file
        target: Optional output path (default: same location with .pdf extension)
        config: Optional configuration dict
        
    Returns:
        ConversionResult
    """
    if target is None:
        target = source.with_suffix(".pdf")
    
    engine_config = PdfConverterConfig.from_dict(config or {})
    engine = PdfConverterEngine(engine_config)
    
    try:
        return engine.convert_single(Path(source), Path(target))
    finally:
        engine.cleanup()


def convert_batch_to_pdf(
    tasks: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[ConversionResult]:
    """
    Convenience function to convert multiple Word files to PDF.
    
    Args:
        tasks: List of dicts with 'source' and optional 'target' keys
        config: Optional configuration dict
        progress_callback: Optional callback(current, total, filename)
        
    Returns:
        List of ConversionResult
    """
    conversion_tasks = []
    for t in tasks:
        source = Path(t["source"])
        target = Path(t.get("target", source.with_suffix(".pdf")))
        conversion_tasks.append(ConversionTask(source_path=source, target_path=target))
    
    engine_config = PdfConverterConfig.from_dict(config or {})
    engine = PdfConverterEngine(engine_config)
    
    try:
        return engine.convert_batch(conversion_tasks, progress_callback)
    finally:
        engine.cleanup()
