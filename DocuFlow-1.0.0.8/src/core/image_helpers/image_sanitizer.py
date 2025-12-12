#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  image_sanitizer.py
Created: 2025-11-06
Author: @lewopxd
Last Updated: 2025-11-06

Description:
Provides functions to safely validate, clean, transcode, and TRANSFORM 
image files before they are used in documents.

v2: Added support for:
- Rotation (90°, -90°, 180°)
- Flipping (horizontal/vertical mirror)
- Compression (file size and dimensions limits)
v3 (BUGFIX): Force-set DPI to 96 on save to normalize all images
             for the layout_engine.
"""

import os
import io
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from uuid import uuid4

try:
    from PIL import Image, ImageOps
except ImportError:
    Logger.error("⚠️ CRITICAL: 'Pillow' library not found. pip install Pillow")
    Image = None
    ImageOps = None

# -------------------------------------------------------------
# ----------------[   COMPRESSION HELPERS   ]-------------------
# -------------------------------------------------------------

def _compress_image_to_target(
    img: Image.Image,
    max_file_size_kb: int,
    quality_start: int = 95,
    quality_min: int = 20,
    format: str = "PNG"
) -> Tuple[Image.Image, int]:
    """
    Comprime una imagen iterativamente hasta alcanzar el tamaño objetivo.
    
    Returns:
        (imagen_comprimida, calidad_final_usada)
    """
    quality = quality_start
    
    while quality >= quality_min:
        buffer = io.BytesIO()
        
        if format.upper() == "PNG":
            # PNG usa 'optimize' en lugar de 'quality'
            img.save(buffer, format="PNG", optimize=True)
        else:
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
        
        size_kb = buffer.tell() / 1024
        
        if size_kb <= max_file_size_kb:
            return img, quality
        
        quality -= 5
    
    # Si llegamos aquí, no se pudo comprimir suficiente
    return img, quality_min

def _resize_if_exceeds(
    img: Image.Image,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None
) -> Image.Image:
    """
    Redimensiona la imagen si excede los límites especificados.
    Mantiene la relación de aspecto.
    """
    width, height = img.size
    
    if max_width is None:
        max_width = width
    if max_height is None:
        max_height = height
    
    if width > max_width or height > max_height:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    
    return img

# -------------------------------------------------------------
# ----------------[   CORE SANITIZATION LOGIC   ]---------------
# -------------------------------------------------------------

def sanitize_image(
    dirty_path: str, 
    temp_folder: str,
    transform_policy: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, tuple]]:
    """Validates, cleans, transforms, and transcodes a source image file.

    This function acts as a security gate AND transformation pipeline. 
    It opens the original file, verifies it's a valid image, applies 
    transformations (rotation, flip, compression), and saves a new, 
    clean PNG/JPEG copy to the specified temporary folder.

    Args:
        dirty_path (str): The path to the original, untrusted image file.
        temp_folder (str): The directory where the sanitized copy will be saved.
        transform_policy (Dict, optional): Transformation instructions:
            {
                "rotate": 90 | -90 | 180,  # Degrees (clockwise positive)
                "flip_horizontal": bool,
                "flip_vertical": bool,
                "compression": {
                    "max_file_size_kb": int,
                    "min_file_size_kb": int,  # (not enforced, informational)
                    "max_width_px": int,
                    "max_height_px": int,
                    "quality": int  # 1-100 for JPEG
                },
                "output_format": "PNG" | "JPEG"  # Default: "PNG"
            }

    Returns:
        Tuple[str, tuple]: A tuple containing:
            - (str): The full path to the new, clean image file.
            - (tuple): The (width_px, height_px) of the FINAL image 
                      (after transformations).
        Returns None if 'Pillow' library is not installed.

    Raises:
        FileNotFoundError: If the 'dirty_path' file does not exist.
        IOError: If the file at 'dirty_path' cannot be opened by Pillow.
    """
    if not Image:
        Logger.error("Error: Pillow library is not available.")
        return None

    # 1. Validate existence
    if not os.path.exists(dirty_path):
        raise FileNotFoundError(f"Source image file not found: {dirty_path}")

    img = None
    try:
        # 2. Validate format (open in memory)
        img = Image.open(dirty_path)
        
        # 2a. Handle rotation based on EXIF data (common from phones)
        img = ImageOps.exif_transpose(img)
        
        # 2b. Convert to RGB if necessary (for JPEG compatibility)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        # --- [ TRANSFORMATION PIPELINE ] ---
        
        if transform_policy:
            
            # 3. ROTATION
            rotation = transform_policy.get("rotate", 0)
            if rotation in [90, -90, 180, 270, -270]:
                # Pillow usa rotación antihoraria, invertimos el signo
                img = img.rotate(-rotation, expand=True)
            
            # 4. FLIP HORIZONTAL (espejo)
            if transform_policy.get("flip_horizontal", False):
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            
            # 5. FLIP VERTICAL
            if transform_policy.get("flip_vertical", False):
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
            # 6. COMPRESSION
            compression = transform_policy.get("compression", {})
            
            if compression:
                # 6a. Resize if exceeds max dimensions
                max_w = compression.get("max_width_px")
                max_h = compression.get("max_height_px")
                
                if max_w or max_h:
                    img = _resize_if_exceeds(img, max_w, max_h)
                
                # 6b. Compress to target file size
                max_size_kb = compression.get("max_file_size_kb")
                quality = compression.get("quality", 95)
                
                if max_size_kb:
                    output_format = transform_policy.get("output_format", "PNG").upper()
                    img, final_quality = _compress_image_to_target(
                        img, max_size_kb, quality, format=output_format
                    )
        
        # --- [ END TRANSFORMATION PIPELINE ] ---
        
        # 7. Get FINAL dimensions (after all transformations)
        width_px, height_px = img.size
        
        # 8. Determine output format
        output_format = "PNG"
        if transform_policy:
            output_format = transform_policy.get("output_format", "PNG").upper()
        
        # 9. Create a unique, clean path
        ext = "png" if output_format == "PNG" else "jpg"
        clean_filename = f"clean_{uuid4().hex}.{ext}"
        clean_path = os.path.join(temp_folder, clean_filename)
        
        # --- [ INICIO DE CORRECCIÓN DPI ] ---
        # El layout_engine asume 96 DPI. Forzamos todas las imágenes
        # a guardarse con esta metadata para normalizarlas.
        dpi_setting = (96, 96)
        # --- [ FIN DE CORRECCIÓN DPI ] ---

        # 10. Save the transformed, clean file
        if output_format == "PNG":
            # PNG: preserve transparency if exists
            if img.mode == "RGBA":
                img.save(clean_path, format="PNG", optimize=True, dpi=dpi_setting)
            else:
                img.save(clean_path, format="PNG", optimize=True, dpi=dpi_setting)
        else:
            # JPEG: convert RGBA to RGB (JPEG doesn't support alpha)
            if img.mode == "RGBA":
                # Create white background
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                img = background
            
            quality = 95
            if transform_policy and transform_policy.get("compression"):
                quality = transform_policy["compression"].get("quality", 95)
            
            img.save(clean_path, format="JPEG", quality=quality, optimize=True, dpi=dpi_setting)
        
        # 11. Return the clean path and FINAL dimensions
        return (clean_path, (width_px, height_px))

    except Exception as e:
        # Re-raise as a standard IOError
        raise IOError(f"File is corrupt or not a valid image: {dirty_path}. Error: {e}")
    
    finally:
        # Ensure the image file handle is closed
        if img:
            img.close()

# --------------------------------------> END [ CORE SANITIZATION LOGIC ... ]