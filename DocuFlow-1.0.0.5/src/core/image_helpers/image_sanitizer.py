#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  image_sanitizer.py
Created: 2025-11-06
Author: @lewopxd

Description:
Provides functions to safely validate, clean, and transcode image files 
before they are used in documents.
"""

import os
from pathlib import Path
from typing import Tuple, Optional
from uuid import uuid4

try:
    from PIL import Image, ImageOps
except ImportError:
    print("⚠️ CRITICAL: 'Pillow' library not found. pip install Pillow")
    Image = None
    ImageOps = None

# -------------------------------------------------------------
# ----------------[   CORE SANITIZATION LOGIC   ]---------------
# -------------------------------------------------------------

def sanitize_image(
    dirty_path: str, 
    temp_folder: str
) -> Optional[Tuple[str, tuple]]:
    """Validates, cleans, and transcodes a source image file.

    This function acts as a security gate. It opens the original file,
    verifies it's a valid image, and saves a new, clean PNG copy
    to the specified temporary folder. This process strips potentially
    harmful metadata and ensures a standard format.

    Args:
        dirty_path (str): The path to the original, untrusted image file.
        temp_folder (str): The directory where the sanitized PNG copy 
                           will be saved.

    Returns:
        Tuple[str, tuple]: A tuple containing:
            - (str): The full path to the new, clean PNG file.
            - (tuple): The (width_px, height_px) of the image.
        Returns None if 'Pillow' library is not installed.

    Raises:
        FileNotFoundError: If the 'dirty_path' file does not exist.
        IOError: If the file at 'dirty_path' cannot be opened by Pillow
                 (e.g., is corrupt, not an image, or unreadable).
    """
    if not Image:
        print("❌ Error: Pillow library is not available.")
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

        # 3. Get dimensions
        width_px, height_px = img.size
        
        # 4. Create a unique, clean path
        # Using UUID ensures no filename collisions
        clean_filename = f"clean_{uuid4().hex}.png"
        clean_path = os.path.join(temp_folder, clean_filename)

        # 5. Transcode and save as a new, clean file
        # This strips metadata and standardizes the format
        img.save(clean_path, format="PNG")
        
        # 6. Return the clean path and dimensions
        return (clean_path, (width_px, height_px))

    except Exception as e:
        # Re-raise as a standard IOError
        raise IOError(f"File is corrupt or not a valid image: {dirty_path}. Error: {e}")
    
    finally:
        # Ensure the image file handle is closed
        if img:
            img.close()

# --------------------------------------> END [ CORE SANITIZATION LOGIC ... ]