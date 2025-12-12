#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  auto_rotate_policy.py
Created: 2025-11-06
Author: @lewopxd

Description:
Centralized business logic for image transformation decisions.
This module analyzes image properties, page context, and user policies
to generate a complete transformation policy for the sanitizer.

This is the "brain" that decides:
- Should the image be rotated to fit better?
- Should it be compressed?
- What format should be used?
"""

from typing import Tuple, Dict, Any, Optional
from docx.shared import Emu

# -------------------------------------------------------------
# ----------------[   HELPER FUNCTIONS   ]----------------------
# -------------------------------------------------------------

def _px_to_emu(px: int, dpi: int = 96) -> Emu:
    """Converts pixels to EMU (for comparison)."""
    return Emu(px * 914400 // dpi)

def _get_orientation(width: float, height: float) -> str:
    """Determines orientation: 'portrait', 'landscape', or 'square'."""
    if height > width * 1.1:  # 10% tolerance
        return "portrait"
    elif width > height * 1.1:
        return "landscape"
    else:
        return "square"

def _calculate_fit_ratio(
    img_w: float, 
    img_h: float, 
    container_w: float, 
    container_h: float
) -> float:
    """
    Calculates the 'contain' ratio (how much the image must shrink to fit).
    Higher ratio = better fit.
    """
    if img_w == 0 or img_h == 0:
        return 0.0
    
    ratio_w = container_w / img_w
    ratio_h = container_h / img_h
    return min(ratio_w, ratio_h)

# -------------------------------------------------------------
# ----------------[   CORE POLICY RESOLVER   ]------------------
# -------------------------------------------------------------

def resolve_transform_policy(
    img_dims_px: Tuple[int, int],
    page_dims_emu: Tuple[Emu, Emu],
    user_policy: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyzes the image and context to generate a complete transform_policy.
    
    This function implements intelligent decision-making:
    - "turn_to_fit": Auto-rotate if it improves the fit
    - "compression": Apply smart compression based on image size
    - Manual transformations: Pass through user-specified rotations/flips
    
    Args:
        img_dims_px (Tuple[int, int]): Original image (width_px, height_px)
        page_dims_emu (Tuple[Emu, Emu]): Available page space (width_emu, height_emu)
        user_policy (Dict[str, Any]): The layout_policy from the job config.
            Supports:
            - "turn_to_fit": bool (default: False)
            - "rotate": 90 | -90 | 180 (manual rotation)
            - "flip_horizontal": bool
            - "flip_vertical": bool
            - "compression": {...}
            - "output_format": "PNG" | "JPEG"
    
    Returns:
        Dict[str, Any]: Complete transform_policy for sanitize_image():
            {
                "rotate": int,
                "flip_horizontal": bool,
                "flip_vertical": bool,
                "compression": {...},
                "output_format": str,
                "turn_to_fit_applied": bool,
                "fit_improvement": float  # (informational)
            }
    """
    
    img_w_px, img_h_px = img_dims_px
    page_w_emu, page_h_emu = page_dims_emu
    
    # Convert image dimensions to EMU for comparison
    img_w_emu = _px_to_emu(img_w_px)
    img_h_emu = _px_to_emu(img_h_px)
    
    # Initialize transform policy
    transform_policy = {
        "rotate": 0,
        "flip_horizontal": False,
        "flip_vertical": False,
        "compression": {},
        "output_format": "PNG",
        "turn_to_fit_applied": False,
        "fit_improvement": 0.0
    }
    
    # --- [ 1. MANUAL TRANSFORMATIONS ] ---
    # (These override turn_to_fit)
    
    manual_rotate = user_policy.get("rotate")
    if manual_rotate and manual_rotate in [90, -90, 180, 270, -270]:
        transform_policy["rotate"] = manual_rotate
    
    if user_policy.get("flip_horizontal"):
        transform_policy["flip_horizontal"] = True
    
    if user_policy.get("flip_vertical"):
        transform_policy["flip_vertical"] = True
    
    # --- [ 2. TURN TO FIT (Intelligent Auto-Rotation) ] ---
    
    turn_to_fit = user_policy.get("turn_to_fit", False)
    
    if turn_to_fit and transform_policy["rotate"] == 0:
        # Only apply if no manual rotation was specified
        
        img_orientation = _get_orientation(img_w_emu, img_h_emu)
        page_orientation = _get_orientation(page_w_emu, page_h_emu)
        
        # Calculate fit in both orientations
        ratio_normal = _calculate_fit_ratio(img_w_emu, img_h_emu, page_w_emu, page_h_emu)
        ratio_rotated = _calculate_fit_ratio(img_h_emu, img_w_emu, page_w_emu, page_h_emu)
        
        # If rotated fit is significantly better (>5% improvement)
        if ratio_rotated > ratio_normal * 1.05:
            transform_policy["rotate"] = 90
            transform_policy["turn_to_fit_applied"] = True
            transform_policy["fit_improvement"] = (ratio_rotated / ratio_normal - 1.0) * 100
    
    # --- [ 3. COMPRESSION POLICY ] ---
    
    user_compression = user_policy.get("compression", {})
    
    if user_compression:
        # Pass through user-specified compression settings
        transform_policy["compression"] = user_compression.copy()
    else:
        # Apply smart defaults based on image size
        
        # Large images (>4K): compress aggressively
        if img_w_px > 4000 or img_h_px > 4000:
            transform_policy["compression"] = {
                "max_width_px": 3840,
                "max_height_px": 3840,
                "max_file_size_kb": 1000,
                "quality": 85
            }
        
        # Medium images (>2K): moderate compression
        elif img_w_px > 2000 or img_h_px > 2000:
            transform_policy["compression"] = {
                "max_width_px": 2560,
                "max_height_px": 2560,
                "max_file_size_kb": 500,
                "quality": 90
            }
        
        # Small images: minimal compression (just optimize)
        else:
            transform_policy["compression"] = {
                "quality": 95
            }
    
    # --- [ 4. OUTPUT FORMAT ] ---
    
    output_format = user_policy.get("output_format", "PNG").upper()
    
    # Smart format selection based on content
    if output_format == "AUTO":
        # If image is large and has no transparency, use JPEG
        if (img_w_px * img_h_px > 2000000) and not user_policy.get("preserve_transparency"):
            transform_policy["output_format"] = "JPEG"
        else:
            transform_policy["output_format"] = "PNG"
    else:
        transform_policy["output_format"] = output_format
    
    return transform_policy


# -------------------------------------------------------------
# ----------------[   CONVENIENCE FUNCTIONS   ]------------------
# -------------------------------------------------------------

def create_smart_policy(
    width: str = "auto",
    height: str = "auto",
    orientation_match_scale: float = 0.5,
    allow_upscale: bool = True,
    alignment: str = "CENTER",
    turn_to_fit: bool = False,
    compress: bool = True,
    output_format: str = "AUTO"
) -> Dict[str, Any]:
    """
    Creates a complete, smart layout_policy with sensible defaults.
    
    This is a convenience function for users who don't want to manually
    configure every option.
    
    Args:
        width, height: Layout dimensions ("auto", "100%", "5.5cm")
        orientation_match_scale: Scale factor for matching orientations
        allow_upscale: Allow image to be scaled up
        alignment: "LEFT", "CENTER", "RIGHT", "JUSTIFY"
        turn_to_fit: Auto-rotate to improve fit
        compress: Apply smart compression
        output_format: "PNG", "JPEG", or "AUTO"
    
    Returns:
        Dict: A complete layout_policy ready for use
    """
    
    policy = {
        "width": width,
        "height": height,
        "orientation_match_scale": orientation_match_scale,
        "allow_upscale": allow_upscale,
        "alignment": alignment,
        "turn_to_fit": turn_to_fit,
        "output_format": output_format
    }
    
    if compress:
        # Smart compression will be applied by resolve_transform_policy
        policy["compression"] = "smart"
    
    return policy


def create_minimal_policy(alignment: str = "CENTER") -> Dict[str, Any]:
    """
    Creates a minimal policy: no transformations, just layout.
    Useful for pre-processed images or when you want full control.
    """
    return {
        "width": "auto",
        "height": "auto",
        "orientation_match_scale": 1.0,
        "allow_upscale": False,
        "alignment": alignment,
        "turn_to_fit": False,
        "output_format": "PNG"
    }


def create_aggressive_compression_policy(
    max_size_kb: int = 200,
    alignment: str = "CENTER"
) -> Dict[str, Any]:
    """
    Creates a policy optimized for file size (e.g., for email attachments).
    """
    return {
        "width": "auto",
        "height": "auto",
        "orientation_match_scale": 0.7,
        "allow_upscale": False,
        "alignment": alignment,
        "turn_to_fit": True,
        "compression": {
            "max_width_px": 1920,
            "max_height_px": 1920,
            "max_file_size_kb": max_size_kb,
            "quality": 80
        },
        "output_format": "JPEG"
    }

# --------------------------------------> END [ POLICY RESOLVER ... ]