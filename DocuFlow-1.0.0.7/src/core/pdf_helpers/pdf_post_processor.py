#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File: pdf_post_processor.py
Created: 2025-12-09
Author: @lewopxd

Description:
Post-processor for PDFs: applies compression and metadata after conversion.
Uses pikepdf for robust stream manipulation and metadata handling.
"""

import os
import io
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

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

# Compression quality levels - JPEG quality and Flate compression level
COMPRESSION_LEVELS = {
    "low": {"jpeg_quality": 90, "flate_level": 3},      # Minimal compression, max quality
    "medium": {"jpeg_quality": 75, "flate_level": 6},   # Balance
    "high": {"jpeg_quality": 60, "flate_level": 9}      # Max compression, acceptable quality
}


@dataclass
class CompressionConfig:
    """Configuration for PDF compression."""
    enabled: bool = True
    level: str = "high"  # low | medium | high
    max_size_kb: Optional[int] = None  # None = disabled
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CompressionConfig':
        """Create config from dictionary."""
        if not data:
            return cls()
        return cls(
            enabled=data.get("enabled", True),
            level=data.get("level", "high").lower(),
            max_size_kb=data.get("max_size_kb")
        )
    
    def get_jpeg_quality(self) -> int:
        """Get JPEG quality for current level."""
        return COMPRESSION_LEVELS.get(self.level, COMPRESSION_LEVELS["high"])["jpeg_quality"]
    
    def get_flate_level(self) -> int:
        """Get Flate compression level for current level."""
        return COMPRESSION_LEVELS.get(self.level, COMPRESSION_LEVELS["high"])["flate_level"]


@dataclass
class MetadataConfig:
    """Configuration for PDF metadata."""
    author: str = ""
    creator: str = "MSWORD"
    producer: str = "MSWORD"
    creation_date: Optional[datetime] = None  # None = auto (current time)
    custom: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MetadataConfig':
        """Create config from dictionary."""
        if not data:
            return cls()
        return cls(
            author=data.get("author", ""),
            creator=data.get("creator", "MSWORD"),
            producer=data.get("producer", "MSWORD"),
            creation_date=data.get("creation_date"),
            custom=data.get("custom", {})
        )


@dataclass
class PostProcessResult:
    """Result of post-processing a PDF."""
    success: bool
    original_size_bytes: int = 0
    final_size_bytes: int = 0
    compression_applied: bool = False
    metadata_applied: bool = False
    error: Optional[str] = None
    
    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage."""
        if self.original_size_bytes == 0:
            return 0.0
        return (1 - self.final_size_bytes / self.original_size_bytes) * 100


# =============================================================================
# PDF Post Processor
# =============================================================================

# Class-level availability cache (checked once per session)
_PIKEPDF_AVAILABLE: Optional[bool] = None
_PILLOW_AVAILABLE: Optional[bool] = None

class PdfPostProcessor:
    """
    Applies compression and metadata to existing PDFs.
    
    Usage:
        processor = PdfPostProcessor(compression_config, metadata_config)
        result = processor.process(pdf_path, row_data)
    """
    
    def __init__(
        self, 
        compression: Optional[CompressionConfig] = None,
        metadata: Optional[MetadataConfig] = None
    ):
        self._compression = compression or CompressionConfig()
        self._metadata = metadata or MetadataConfig()
        self._pikepdf_available = self._check_pikepdf()
        self._pillow_available = self._check_pillow()
    
    @staticmethod
    def _check_pikepdf() -> bool:
        """Check if pikepdf is available (cached at class level)."""
        global _PIKEPDF_AVAILABLE
        if _PIKEPDF_AVAILABLE is None:
            try:
                import pikepdf
                _PIKEPDF_AVAILABLE = True
                Logger.debug("[PostProcessor] pikepdf disponible para compresión")
            except ImportError:
                _PIKEPDF_AVAILABLE = False
                Logger.warn("[PostProcessor] pikepdf no disponible - compresión deshabilitada")
        return _PIKEPDF_AVAILABLE
    
    @staticmethod
    def _check_pillow() -> bool:
        """Check if Pillow is available (cached at class level)."""
        global _PILLOW_AVAILABLE
        if _PILLOW_AVAILABLE is None:
            try:
                from PIL import Image
                _PILLOW_AVAILABLE = True
            except ImportError:
                _PILLOW_AVAILABLE = False
                Logger.warn("[PostProcessor] Pillow no disponible - compresión de imágenes deshabilitada")
        return _PILLOW_AVAILABLE
    
    # -------------------------------------------------------------------------
    # Placeholder Resolution
    # -------------------------------------------------------------------------
    
    def _resolve_placeholders(self, text: str, row_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Resolve {COLUMN_NAME} placeholders in text using row_data.
        
        Args:
            text: Text containing placeholders
            row_data: Dictionary with column values
            
        Returns:
            Text with placeholders resolved
        """
        if not text or not row_data:
            return text or ""
        
        result = text
        # Find all placeholders like {COLUMN_NAME}
        placeholders = re.findall(r'\{([^}]+)\}', text)
        
        for placeholder in placeholders:
            # Try exact match first, then case-insensitive
            value = row_data.get(placeholder)
            if value is None:
                # Try case-insensitive
                for key, val in row_data.items():
                    if key.upper() == placeholder.upper():
                        value = val
                        break
            
            if value is not None:
                result = result.replace(f"{{{placeholder}}}", str(value))
        
        return result
    
    # -------------------------------------------------------------------------
    # Compression Methods
    # -------------------------------------------------------------------------
    
    def _compress_images_in_pdf(self, pdf_path: Path) -> Tuple[bool, int, int]:
        """
        Compress JPEG images in PDF.
        
        Returns:
            Tuple of (success, original_size, new_size)
        """
        if not self._pikepdf_available or not self._pillow_available:
            return False, 0, 0
        
        try:
            import pikepdf
            from PIL import Image
            
            original_size = pdf_path.stat().st_size
            jpeg_quality = self._compression.get_jpeg_quality()
            
            # Open PDF
            pdf = pikepdf.open(pdf_path, allow_overwriting_input=True)
            images_processed = 0
            
            # Iterate through all pages
            for page in pdf.pages:
                # Get resources
                if '/Resources' not in page:
                    continue
                    
                resources = page['/Resources']
                if '/XObject' not in resources:
                    continue
                
                xobjects = resources['/XObject']
                
                for name in list(xobjects.keys()):
                    xobj = xobjects[name]
                    
                    # Check if it's an image
                    if xobj.get('/Subtype') != '/Image':
                        continue
                    
                    # Get image data
                    try:
                        # Check if it's a DCT (JPEG) encoded image
                        filter_type = xobj.get('/Filter')
                        if filter_type == '/DCTDecode' or (
                            isinstance(filter_type, pikepdf.Array) and 
                            '/DCTDecode' in [str(f) for f in filter_type]
                        ):
                            # Extract raw stream data
                            raw_data = xobj.read_raw_bytes()
                            
                            # Open with Pillow
                            img = Image.open(io.BytesIO(raw_data))
                            
                            # Re-compress with specified quality
                            output_buffer = io.BytesIO()
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            img.save(output_buffer, format='JPEG', quality=jpeg_quality, optimize=True)
                            
                            # Only replace if smaller
                            new_data = output_buffer.getvalue()
                            if len(new_data) < len(raw_data):
                                xobj.write(new_data, filter=pikepdf.Name('/DCTDecode'))
                                images_processed += 1
                    
                    except Exception as img_err:
                        Logger.debug(f"[PostProcessor] No se pudo comprimir imagen: {img_err}")
                        continue
            
            # Save with Flate compression for streams
            flate_level = self._compression.get_flate_level()
            pikepdf.settings.set_flate_compression_level(flate_level)
            
            pdf.save(pdf_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
            pdf.close()
            
            new_size = pdf_path.stat().st_size
            reduction = (1 - new_size / original_size) * 100 if original_size > 0 else 0
            
            Logger.info(f"[PostProcessor] Compresión: {original_size/1024:.0f}KB → {new_size/1024:.0f}KB ({reduction:.0f}% reducido)")
            
            return True, original_size, new_size
            
        except Exception as e:
            Logger.error(f"[PostProcessor] Error comprimiendo PDF: {e}")
            return False, 0, 0
    
    # -------------------------------------------------------------------------
    # Metadata Methods
    # -------------------------------------------------------------------------
    
    def _apply_metadata_to_pdf(
        self, 
        pdf_path: Path, 
        row_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Apply metadata to PDF.
        
        Args:
            pdf_path: Path to PDF file
            row_data: Optional row data for placeholder resolution
            
        Returns:
            True if successful
        """
        if not self._pikepdf_available:
            return False
        
        try:
            import pikepdf
            
            pdf = pikepdf.open(pdf_path, allow_overwriting_input=True)
            
            # Build metadata dictionary
            with pdf.open_metadata() as meta:
                # Author
                author = self._resolve_placeholders(self._metadata.author, row_data)
                if author:
                    meta['dc:creator'] = [author]
                
                # Creator (application)
                creator = self._resolve_placeholders(self._metadata.creator, row_data)
                if creator:
                    meta['xmp:CreatorTool'] = creator
                
                # Producer
                producer = self._resolve_placeholders(self._metadata.producer, row_data)
                if producer:
                    meta['pdf:Producer'] = producer
                
                # Creation date
                if self._metadata.creation_date:
                    meta['xmp:CreateDate'] = self._metadata.creation_date.isoformat()
                else:
                    meta['xmp:CreateDate'] = datetime.now().isoformat()
            
            # Also set document info in PDF info dict for compatibility
            docinfo = pdf.docinfo
            if author:
                docinfo['/Author'] = author
            if creator:
                docinfo['/Creator'] = creator
            if producer:
                docinfo['/Producer'] = producer
            
            # Custom fields - add to docinfo
            for key, value in self._metadata.custom.items():
                resolved_value = self._resolve_placeholders(value, row_data)
                # Custom keys need to be valid PDF name objects
                safe_key = '/' + re.sub(r'[^a-zA-Z0-9_]', '_', key)
                docinfo[safe_key] = resolved_value
            
            pdf.save(pdf_path)
            pdf.close()
            
            Logger.info(f"[PostProcessor] Metadata aplicada: author={author or 'N/A'}")
            return True
            
        except Exception as e:
            Logger.error(f"[PostProcessor] Error aplicando metadata: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # Main Process Method
    # -------------------------------------------------------------------------
    
    def process(
        self, 
        pdf_path: Path, 
        row_data: Optional[Dict[str, Any]] = None
    ) -> PostProcessResult:
        """
        Apply compression and metadata to a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            row_data: Optional row data for placeholder resolution in metadata
            
        Returns:
            PostProcessResult with details
        """
        if not pdf_path.exists():
            return PostProcessResult(
                success=False,
                error=f"Archivo no encontrado: {pdf_path}"
            )
        
        original_size = pdf_path.stat().st_size
        compression_applied = False
        metadata_applied = False
        error = None
        
        try:
            # Apply compression if enabled
            if self._compression.enabled and self._pikepdf_available:
                success, orig, new = self._compress_images_in_pdf(pdf_path)
                compression_applied = success
                
                # Check max_size_kb constraint
                if self._compression.max_size_kb:
                    max_bytes = self._compression.max_size_kb * 1024
                    current_size = pdf_path.stat().st_size
                    
                    if current_size > max_bytes:
                        Logger.warn(f"[PostProcessor] PDF {pdf_path.name} excede max_size_kb " +
                                   f"({current_size/1024:.1f}KB > {self._compression.max_size_kb}KB)")
            
            # Apply metadata
            if self._pikepdf_available:
                metadata_applied = self._apply_metadata_to_pdf(pdf_path, row_data)
            
            final_size = pdf_path.stat().st_size
            
            return PostProcessResult(
                success=True,
                original_size_bytes=original_size,
                final_size_bytes=final_size,
                compression_applied=compression_applied,
                metadata_applied=metadata_applied
            )
            
        except Exception as e:
            Logger.error(f"[PostProcessor] Error procesando {pdf_path.name}: {e}")
            return PostProcessResult(
                success=False,
                original_size_bytes=original_size,
                error=str(e)
            )


# =============================================================================
# Convenience Functions
# =============================================================================

def compress_pdf(
    pdf_path: Path, 
    level: str = "high",
    max_size_kb: Optional[int] = None
) -> PostProcessResult:
    """
    Convenience function to compress a PDF.
    
    Args:
        pdf_path: Path to PDF
        level: Compression level (low/medium/high)
        max_size_kb: Optional max size constraint
        
    Returns:
        PostProcessResult
    """
    config = CompressionConfig(enabled=True, level=level, max_size_kb=max_size_kb)
    processor = PdfPostProcessor(compression=config)
    return processor.process(Path(pdf_path))


def set_pdf_metadata(
    pdf_path: Path,
    author: str = "",
    creator: str = "MSWORD",
    producer: str = "MSWORD",
    custom: Optional[Dict[str, str]] = None,
    row_data: Optional[Dict[str, Any]] = None
) -> PostProcessResult:
    """
    Convenience function to set PDF metadata.
    
    Args:
        pdf_path: Path to PDF
        author: Author name (supports placeholders)
        creator: Creator application
        producer: Producer application
        custom: Custom metadata fields
        row_data: Data for placeholder resolution
        
    Returns:
        PostProcessResult
    """
    config = MetadataConfig(
        author=author,
        creator=creator,
        producer=producer,
        custom=custom or {}
    )
    comp_config = CompressionConfig(enabled=False)
    processor = PdfPostProcessor(compression=comp_config, metadata=config)
    return processor.process(Path(pdf_path), row_data)
