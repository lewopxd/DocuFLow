#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Word to PDF Converter Module
High-performance, resilient conversion with LibreOffice CLI
Uses safe temporary copies and applies metadata to final PDFs
"""

import os
import sys
import shutil
import subprocess
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import multiprocessing as mp

# Import logger
try:
    from core.logger import Logger
except ImportError:
    # Fallback logger
    class Logger:
        @staticmethod
        def warn(msg): print(f"WARN: {msg}")
        @staticmethod
        def error(msg): print(f"ERROR: {msg}")


try:
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    Logger.warn("WARNING: PyPDF2 not installed. PDF validation and metadata will be unavailable.")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Logger.warn("WARNING: python-docx not installed. Word validation will be limited.")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Import safe copy utility
try:
    from ..utils.path_utils import create_safe_temp_copy
    SAFE_COPY_AVAILABLE = True
except ImportError:
    SAFE_COPY_AVAILABLE = False
    Logger.warn("WARNING: path_utils not available. Will use basic copy method.")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Task:
    """
    Conversion task with all necessary information
    
    Attributes:
        source: Path to source Word file
        output: Path to output PDF file
        filename: Final filename for the PDF (optional, uses output if None)
        metadata: Dictionary with PDF metadata (optional)
            Expected keys: /Author, /Title, /Subject, /Creator, /Producer, etc.
    """
    source: Path
    output: Path
    filename: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        self.source = Path(self.source)
        self.output = Path(self.output)
        
        # If filename not provided, use output filename
        if self.filename is None:
            self.filename = self.output.name


@dataclass
class ValidationConfig:
    """Validation settings"""
    min_size_kb: int = 5
    verify_pages: bool = True
    compute_hash: bool = True


@dataclass
class ParallelConfig:
    """Parallelization settings"""
    workers: int = None  # None = auto
    batch_size: int = 100


@dataclass
class QualityConfig:
    """PDF quality settings"""
    dpi: int = 150
    compression: str = "medium"  # none, low, medium, high


@dataclass
class ResilienceConfig:
    """Error handling settings"""
    max_retries: int = 2
    retry_delay_seconds: float = 1.0


@dataclass
class CallbackConfig:
    """Progress callbacks"""
    on_progress: Optional[Callable] = None
    on_error: Optional[Callable] = None
    on_complete: Optional[Callable] = None


@dataclass
class Config:
    """Main configuration"""
    parallel: ParallelConfig = field(default_factory=ParallelConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)
    callbacks: CallbackConfig = field(default_factory=CallbackConfig)


@dataclass
class FileResult:
    """Result for a single file conversion"""
    task: Task
    status: str  # success, failed, skipped
    duration_ms: int = 0
    size_kb: int = 0
    pages: int = 0
    hash_sha256: Optional[str] = None
    retries: int = 0
    error: Optional[str] = None
    validation_details: Dict[str, bool] = field(default_factory=dict)
    metadata_applied: bool = False


@dataclass
class Report:
    """Final conversion report"""
    summary: Dict[str, Any] = field(default_factory=dict)
    files: List[FileResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================================
# FALLBACK SAFE COPY (if path_utils not available)
# ============================================================================

def _fallback_safe_copy(source_path: Path, temp_dir: Path) -> Optional[Path]:
    """Fallback safe copy if path_utils module not available"""
    try:
        import tempfile
        
        suffix = source_path.suffix
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="docuflow_", dir=str(temp_dir))
        os.close(fd)
        
        shutil.copy2(str(source_path), temp_path)
        return Path(temp_path)
    except Exception as e:
        Logger.error(f"ERROR: Failed to create safe copy: {e}")
        return None


# ============================================================================
# CORE CONVERTER CLASS
# ============================================================================

class WordToPdfConverter:
    """
    Professional Word to PDF converter using LibreOffice CLI
    """
    
    def __init__(self, libreoffice_path: Optional[str] = None):
        """
        Initialize converter
        
        Args:
            libreoffice_path: Custom path to LibreOffice executable
        """
        self.libreoffice_path = libreoffice_path or self._find_libreoffice()
        self.start_time = None
        self.completed_files = 0
        self.total_files = 0
        
    @staticmethod
    def _find_libreoffice() -> Optional[str]:
        """Find LibreOffice executable in common locations"""
        common_paths = [
            # Windows
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            # Linux
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            # macOS
            "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Try PATH
        if shutil.which("soffice"):
            return "soffice"
        
        return None
    
    def _validate_setup(self) -> bool:
        """
        PHASE 0: Validate LibreOffice installation and functionality
        
        Returns:
            True if setup is valid
        """
        if not self.libreoffice_path:
            raise RuntimeError(
                "LibreOffice not found. Install LibreOffice or provide custom path."
            )
        
        if not os.path.exists(self.libreoffice_path) and not shutil.which(self.libreoffice_path):
            raise RuntimeError(
                f"LibreOffice executable not found at: {self.libreoffice_path}"
            )
        
        # Test execution
        try:
            result = subprocess.run(
                [self.libreoffice_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("LibreOffice version check failed")
        except Exception as e:
            raise RuntimeError(f"LibreOffice execution test failed: {e}")
        
        return True
    
    @staticmethod
    def _calculate_optimal_workers(
        num_files: int,
        avg_file_size_mb: float,
        config: ParallelConfig
    ) -> int:
        """
        Calculate optimal number of workers based on system resources
        
        Args:
            num_files: Total number of files
            avg_file_size_mb: Average file size in MB
            config: Parallel configuration
        
        Returns:
            Optimal number of workers
        """
        if config.workers is not None:
            return config.workers
        
        cpu_cores = mp.cpu_count()
        
        # RAM-based limit (500 MB per worker)
        ram_workers = 8  # Default safe value
        if PSUTIL_AVAILABLE:
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
            ram_workers = int(available_ram_gb / 0.5)
        
        # File-based limit
        file_workers = max(1, num_files // config.batch_size)
        
        # Calculate optimal
        optimal = min(
            cpu_cores - 1,  # Leave one core for OS
            ram_workers,
            file_workers,
            8  # Maximum reasonable limit
        )
        
        return max(1, optimal)
    
    @staticmethod
    def _validate_word_file(source: Path) -> tuple[bool, Optional[str]]:
        """
        PHASE 1: Validate Word file before conversion
        
        Args:
            source: Path to Word file
        
        Returns:
            (is_valid, error_message)
        """
        # Check existence
        if not source.exists():
            return False, f"File not found: {source}"
        
        # Check extension
        if source.suffix.lower() not in ['.docx', '.doc']:
            return False, f"Invalid extension: {source.suffix}"
        
        # Check size
        if source.stat().st_size == 0:
            return False, "File is empty"
        
        # Try opening with python-docx (only for .docx)
        if DOCX_AVAILABLE and source.suffix.lower() == '.docx':
            try:
                doc = Document(str(source))
                # Basic integrity check
                _ = len(doc.paragraphs)
            except Exception as e:
                return False, f"Corrupted Word file: {str(e)}"
        
        return True, None
    
    @staticmethod
    def _apply_pdf_metadata(pdf_path: Path, metadata: Dict[str, str]) -> bool:
        """
        Apply metadata to PDF file using PyPDF2
        
        Args:
            pdf_path: Path to PDF file
            metadata: Dictionary with metadata fields
        
        Returns:
            True if metadata was applied successfully
        """
        if not PYPDF2_AVAILABLE:
            Logger.warn("WARNING: PyPDF2 not available. Skipping metadata application.")
            return False
        
        if not metadata:
            return False
        
        try:
            # Read existing PDF
            reader = PdfReader(str(pdf_path))
            writer = PdfWriter()
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Apply metadata
            writer.add_metadata(metadata)
            
            # Write to temporary file first
            temp_path = pdf_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as output_file:
                writer.write(output_file)
            
            # Replace original with modified version
            temp_path.replace(pdf_path)
            
            return True
            
        except Exception as e:
            Logger.error(f"ERROR: Failed to apply metadata: {e}")
            return False
    
    def _convert_single_file(
        self,
        task: Task,
        config: Config,
        temp_dir: Path
    ) -> FileResult:
        """
        PHASE 2: Convert single Word file to PDF
        
        Args:
            task: Conversion task
            config: Configuration
            temp_dir: Temporary directory for conversion
        
        Returns:
            FileResult with conversion outcome
        """
        start_time = time.time()
        result = FileResult(task=task, status="failed")
        temp_word_copy = None
        
        try:
            # PHASE 1: Validate source
            is_valid, error = self._validate_word_file(task.source)
            if not is_valid:
                result.error = error
                result.status = "skipped"
                return result
            
            # PHASE 2: Create safe temporary copy
            if SAFE_COPY_AVAILABLE:
                # Use context manager from path_utils
                from ..utils.path_utils import create_safe_temp_copy
                
                with create_safe_temp_copy(str(task.source)) as temp_copy_path:
                    if not temp_copy_path:
                        result.error = "Failed to create safe temporary copy"
                        return result
                    
                    temp_word_copy = Path(temp_copy_path)
                    # Conversion happens inside context
                    result = self._perform_conversion(
                        task, config, temp_dir, temp_word_copy, start_time
                    )
            else:
                # Fallback: manual temp copy
                temp_word_copy = _fallback_safe_copy(task.source, temp_dir)
                if not temp_word_copy:
                    result.error = "Failed to create temporary copy"
                    return result
                
                try:
                    result = self._perform_conversion(
                        task, config, temp_dir, temp_word_copy, start_time
                    )
                finally:
                    # Manual cleanup
                    if temp_word_copy and temp_word_copy.exists():
                        try:
                            temp_word_copy.unlink()
                        except:
                            pass
            
            return result
            
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
            result.status = "failed"
            return result
    
    def _perform_conversion(
        self,
        task: Task,
        config: Config,
        temp_dir: Path,
        temp_word_copy: Path,
        start_time: float
    ) -> FileResult:
        """
        Perform actual conversion from temporary Word copy
        
        Args:
            task: Conversion task
            config: Configuration
            temp_dir: Temporary directory
            temp_word_copy: Path to temporary Word copy
            start_time: Conversion start time
        
        Returns:
            FileResult with outcome
        """
        result = FileResult(task=task, status="failed")
        
        # Prepare temporary output with task's filename
        temp_output = temp_dir / task.filename
        
        # PHASE 2: Conversion with retry logic
        for attempt in range(config.resilience.max_retries + 1):
            try:
                # Execute LibreOffice conversion on TEMP COPY (not original)
                cmd = [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf:writer_pdf_Export",
                    "--outdir", str(temp_dir),
                    str(temp_word_copy)  # CRITICAL: Use temp copy, not original
                ]
                
                process_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # LibreOffice creates PDF with same name as input
                expected_pdf = temp_dir / f"{temp_word_copy.stem}.pdf"
                
                if process_result.returncode == 0 and expected_pdf.exists():
                    # Rename to task's desired filename if different
                    if expected_pdf != temp_output:
                        expected_pdf.rename(temp_output)
                    break
                else:
                    error_msg = process_result.stderr or "Conversion failed"
                    if attempt < config.resilience.max_retries:
                        result.retries += 1
                        time.sleep(config.resilience.retry_delay_seconds)
                        continue
                    else:
                        result.error = f"Conversion failed after {attempt + 1} attempts: {error_msg}"
                        return result
                        
            except subprocess.TimeoutExpired:
                if attempt < config.resilience.max_retries:
                    result.retries += 1
                    time.sleep(config.resilience.retry_delay_seconds)
                    continue
                else:
                    result.error = f"Timeout after {attempt + 1} attempts"
                    return result
                    
            except Exception as e:
                if attempt < config.resilience.max_retries:
                    result.retries += 1
                    time.sleep(config.resilience.retry_delay_seconds)
                    continue
                else:
                    result.error = f"Error: {str(e)}"
                    return result
        
        # PHASE 3: Validation
        validation_ok, validation_details = self._validate_pdf(
            temp_output,
            config.validation
        )
        
        result.validation_details = validation_details
        
        if not validation_ok:
            result.error = "PDF validation failed: " + ", ".join(
                [k for k, v in validation_details.items() if not v]
            )
            return result
        
        # PHASE 4: Apply metadata (if provided)
        if task.metadata:
            metadata_success = self._apply_pdf_metadata(temp_output, task.metadata)
            result.metadata_applied = metadata_success
            if not metadata_success:
                Logger.warn(f"WARNING: Metadata application failed for {task.filename}")
        
        # PHASE 5: Post-processing (only if validation passed)
        try:
            # Create output directory (only now that we know conversion succeeded)
            task.output.parent.mkdir(parents=True, exist_ok=True)
            
            # Move to final location
            shutil.move(str(temp_output), str(task.output))
            
            # Collect metadata
            result.size_kb = int(task.output.stat().st_size / 1024)
            result.duration_ms = int((time.time() - start_time) * 1000)
            
            if PYPDF2_AVAILABLE:
                try:
                    reader = PdfReader(str(task.output))
                    result.pages = len(reader.pages)
                except:
                    pass
            
            if config.validation.compute_hash:
                result.hash_sha256 = self._compute_hash(task.output)
            
            result.status = "success"
            
        except Exception as e:
            result.error = f"Post-processing failed: {str(e)}"
            result.status = "failed"
        
        return result
    
    @staticmethod
    def _validate_pdf(pdf_path: Path, validation_config: ValidationConfig) -> tuple[bool, Dict[str, bool]]:
        """
        PHASE 3: Validate generated PDF
        
        Args:
            pdf_path: Path to PDF file
            validation_config: Validation settings
        
        Returns:
            (is_valid, validation_details)
        """
        details = {
            "exists": False,
            "size_ok": False,
            "openable": False,
            "has_pages": False
        }
        
        # Check existence
        if not pdf_path.exists():
            return False, details
        details["exists"] = True
        
        # Check size
        size_kb = pdf_path.stat().st_size / 1024
        if size_kb < validation_config.min_size_kb:
            return False, details
        details["size_ok"] = True
        
        # Try opening with PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                reader = PdfReader(str(pdf_path))
                details["openable"] = True
                
                # Check pages
                if validation_config.verify_pages:
                    if len(reader.pages) > 0:
                        details["has_pages"] = True
                    else:
                        return False, details
                else:
                    details["has_pages"] = True
                    
            except Exception:
                return False, details
        else:
            # If PyPDF2 not available, assume openable
            details["openable"] = True
            details["has_pages"] = True
        
        return all(details.values()), details
    
    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _process_batch(
        self,
        tasks: List[Task],
        config: Config,
        temp_base: Path
    ) -> List[FileResult]:
        """Process a batch of files"""
        results = []
        
        # Create temporary directory for this batch
        batch_temp = temp_base / f"batch_{id(tasks)}"
        batch_temp.mkdir(parents=True, exist_ok=True)
        
        try:
            for task in tasks:
                result = self._convert_single_file(task, config, batch_temp)
                results.append(result)
                
                # Update progress
                self.completed_files += 1
                if config.callbacks.on_progress:
                    try:
                        config.callbacks.on_progress(
                            self.completed_files,
                            self.total_files,
                            task.source.name
                        )
                    except Exception:
                        pass
                
                # Handle errors
                if result.status == "failed" and config.callbacks.on_error:
                    try:
                        config.callbacks.on_error(task, result.error, result.retries)
                    except Exception:
                        pass
        
        finally:
            # Cleanup temporary directory
            if batch_temp.exists():
                shutil.rmtree(batch_temp, ignore_errors=True)
        
        return results
    
    def convert(
        self,
        tasks: List[Task],
        config: Optional[Config] = None
    ) -> Report:
        """
        Convert Word files to PDF
        
        Args:
            tasks: List of conversion tasks
            config: Configuration (uses defaults if None)
        
        Returns:
            Conversion report
        """
        if config is None:
            config = Config()
        
        self.start_time = time.time()
        self.completed_files = 0
        self.total_files = len(tasks)
        
        # PHASE 0: Setup validation
        self._validate_setup()
        
        # Calculate optimal workers
        avg_size_mb = 0.5  # Assume average 500KB
        workers = self._calculate_optimal_workers(
            len(tasks),
            avg_size_mb,
            config.parallel
        )
        
        # Divide into batches
        batches = [
            tasks[i:i + config.parallel.batch_size]
            for i in range(0, len(tasks), config.parallel.batch_size)
        ]
        
        # Create temporary directory
        temp_base = Path("temp_conversion_" + str(int(time.time())))
        temp_base.mkdir(exist_ok=True)
        
        all_results = []
        
        try:
            # PHASE 2: Parallel conversion
            if workers > 1 and len(batches) > 1:
                with ProcessPoolExecutor(max_workers=workers) as executor:
                    futures = {
                        executor.submit(self._process_batch, batch, config, temp_base): batch
                        for batch in batches
                    }
                    
                    for future in as_completed(futures):
                        try:
                            results = future.result()
                            all_results.extend(results)
                        except Exception as e:
                            # Handle batch failure
                            batch = futures[future]
                            for task in batch:
                                all_results.append(
                                    FileResult(
                                        task=task,
                                        status="failed",
                                        error=f"Batch processing error: {str(e)}"
                                    )
                                )
            else:
                # Sequential processing
                for batch in batches:
                    results = self._process_batch(batch, config, temp_base)
                    all_results.extend(results)
        
        finally:
            # Cleanup
            if temp_base.exists():
                shutil.rmtree(temp_base, ignore_errors=True)
        
        # PHASE 5: Generate report
        duration_seconds = time.time() - self.start_time
        
        success_count = sum(1 for r in all_results if r.status == "success")
        failed_count = sum(1 for r in all_results if r.status == "failed")
        skipped_count = sum(1 for r in all_results if r.status == "skipped")
        
        report = Report(
            summary={
                "total_files": len(tasks),
                "successful": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "duration_seconds": round(duration_seconds, 2),
                "files_per_second": round(len(tasks) / duration_seconds, 2) if duration_seconds > 0 else 0,
                "workers_used": workers
            },
            files=all_results,
            errors=[
                {
                    "task": r.task,
                    "error_type": "conversion_error",
                    "message": r.error,
                    "retry_count": r.retries,
                    "timestamp": datetime.now()
                }
                for r in all_results if r.status == "failed"
            ]
        )
        
        # Final callback
        if config.callbacks.on_complete:
            try:
                config.callbacks.on_complete(report)
            except Exception:
                pass
        
        return report


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_report(report: Report):
    """Print formatted conversion report"""
    print("\n" + "=" * 70)
    Logger.debug("CONVERSION REPORT")
    print("=" * 70)
    
    Logger.debug(f"\nSummary:")
    Logger.debug(f"  Total files:    {report.summary['total_files']}")
    Logger.debug(f"  Successful:     {report.summary['successful']}")
    Logger.debug(f"  Failed:         {report.summary['failed']}")
    Logger.debug(f"  Skipped:        {report.summary['skipped']}")
    Logger.debug(f"  Duration:       {report.summary['duration_seconds']} seconds")
    Logger.debug(f"  Speed:          {report.summary['files_per_second']} files/second")
    Logger.debug(f"  Workers used:   {report.summary['workers_used']}")
    
    if report.errors:
        Logger.error(f"\nErrors ({len(report.errors)}):")
        for error in report.errors[:5]:  # Show first 5
            Logger.debug(f"  - {error['task'].source.name}: {error['message']}")
        if len(report.errors) > 5:
            Logger.debug(f"  ... and {len(report.errors) - 5} more errors")
    
    print("\n" + "=" * 70)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Convert files with custom configuration
    
    # Define tasks with metadata
    tasks = [
        Task(
            source=Path("document1.docx"),
            output=Path("output/folder1/report.pdf"),
            filename="report.pdf",
            metadata={
                "/Author": "Jose Barreto",
                "/Title": "Monthly Report",
                "/Subject": "Business Report",
                "/Creator": "DocuFlow System",
                "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S")
            }
        ),
        Task(
            source=Path("document2.docx"),
            output=Path("output/folder2/invoice.pdf"),
            filename="invoice.pdf",
            metadata={
                "/Author": "DocuFlow",
                "/Title": "Invoice #12345"
            }
        ),
        Task(
            source=Path("document3.docx"),
            output=Path("output/simple.pdf"),
            # No metadata - will skip metadata phase
        )
    ]
    
    # Configure
    config = Config(
        parallel=ParallelConfig(
            workers=4,
            batch_size=50
        ),
        validation=ValidationConfig(
            min_size_kb=5,
            verify_pages=True,
            compute_hash=True
        ),
        quality=QualityConfig(
            dpi=150,
            compression="medium"
        ),
        resilience=ResilienceConfig(
            max_retries=2,
            retry_delay_seconds=1.0
        ),
        callbacks=CallbackConfig(
            on_progress=lambda current, total, name: Logger.debug(f"Progress: {current}/{total} - {name}"),
            on_error=lambda task, error, retries: Logger.error(f"Error on {task.source.name}: {error}"),
            on_complete=lambda report: Logger.debug("Conversion complete!")
        )
    )
    
    # Convert
    converter = WordToPdfConverter()
    report = converter.convert(tasks, config)
    
    # Print report
    print_report(report)