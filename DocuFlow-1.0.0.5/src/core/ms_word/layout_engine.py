#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: DocuFlow
File:  layout_engine.py
Created: 2025-11-06
Author: @lewopxd

Description:
Calculates the final dimensions for an image based on a declarative
layout policy and the available space within a Word document section.
This module performs the "math" but does not modify the document.
"""

from typing import Tuple, Dict, Any, Optional
from docx.section import Section
from docx.shared import Emu, Inches, Cm

# Standard DPI assumption for pixel-to-EMU conversion
# 914400 EMU per Inch
DEFAULT_DPI = 96

# -------------------------------------------------------------
# -------------------[   HELPER FUNCTIONS   ]------------------
# -------------------------------------------------------------

def _px_to_emu(px: int, dpi: int = DEFAULT_DPI) -> Emu:
    """Converts a pixel value to English Metric Units (EMU)."""
    return Emu(Inches(px / dpi))

def _cm_to_emu(cm: float) -> Emu:
    """Converts a centimeter value to English Metric Units (EMU)."""
    return Emu(Cm(cm))

def _get_orientation(width: int, height: int) -> str:
    """Determines if dimensions are 'portrait', 'landscape', or 'square'."""
    if height > width:
        return "portrait"
    elif width > height:
        return "landscape"
    else:
        return "square"

def _parse_policy_dimension(
    policy_value: Any, 
    page_dimension_emu: Emu
) -> Emu:
    """
    Parses a layout policy value ("auto", "100%", "5.5cm") into EMU.
    
    Args:
        policy_value: The value from the layout policy (e.g., "auto").
        page_dimension_emu: The corresponding available page dimension.

    Returns:
        Emu: The calculated dimension in EMU.
    """
    if policy_value == "auto":
        return page_dimension_emu
    
    if isinstance(policy_value, str):
        if policy_value.endswith("%"):
            try:
                percent = float(policy_value.strip("%"))
                return Emu(page_dimension_emu * (percent / 100.0))
            except ValueError:
                return page_dimension_emu
        elif policy_value.endswith("cm"):
            try:
                cm = float(policy_value.strip("cm"))
                return _cm_to_emu(cm)
            except ValueError:
                return page_dimension_emu
                
    elif isinstance(policy_value, (int, float)):
        # Assume 'cm' if no unit is specified
        return _cm_to_emu(float(policy_value))
        
    return page_dimension_emu

# --------------------------------------> END [ HELPER FUNCTIONS ... ]


# -------------------------------------------------------------
# -------------------[   LAYOUT CALCULATIONS   ]---------------
# -------------------------------------------------------------

def get_page_available_space(section: Section) -> Tuple[Emu, Emu]:
    """
    Calculates the usable (content) width and height of a page section.

    Args:
        section (Section): The docx.section.Section object to measure.

    Returns:
        Tuple[Emu, Emu]: (available_width_emu, available_height_emu)
    """
    try:
        # Start with the full page size
        page_w = section.page_width
        page_h = section.page_height
        
        # Get margins
        margin_l = section.left_margin
        margin_r = section.right_margin
        margin_t = section.top_margin
        margin_b = section.bottom_margin
        
        # Calculate available space
        available_width = page_w - margin_l - margin_r
        available_height = page_h - margin_t - margin_b
        
        # Safety check for invalid dimensions
        if available_width <= 0:
            available_width = Emu(Inches(6.5)) # Fallback
        if available_height <= 0:
            available_height = Emu(Inches(9.0)) # Fallback
            
        return (available_width, available_height)
        
    except Exception:
        # Fallback to a standard US Letter page if properties are corrupt
        return (Emu(Inches(6.5)), Emu(Inches(9.0)))


def calculate_final_dimensions(
    img_dims_px: Tuple[int, int],
    page_dims_emu: Tuple[Emu, Emu],
    policy: Dict[str, Any]
) -> Tuple[Emu, Emu]:
    """
    Calculates the final width and height for an image based on a policy.

    This implements the "v6" logic:
    1. Define container from policy (auto, %, cm).
    2. Apply 'orientation_match_scale' to container.
    3. Calculate 'CONTAIN' ratio to fit image into container.
    4. Apply 'allow_upscale' lock to the ratio.
    5. Return final dimensions.

    Args:
        img_dims_px (Tuple[int, int]): (width_px, height_px) of the image.
        page_dims_emu (Tuple[Emu, Emu]): (width_emu, height_emu) of the 
                                         available page space.
        policy (Dict[str, Any]): The layout_policy object.

    Returns:
        Tuple[Emu, Emu]: (final_width_emu, final_height_emu)
    """
    
    # --- 0. Get Inputs ---
    img_w_px, img_h_px = img_dims_px
    page_w_emu, page_h_emu = page_dims_emu

    # Convert image dimensions to EMU
    img_w_emu = _px_to_emu(img_w_px)
    img_h_emu = _px_to_emu(img_h_px)
    
    # Get policy defaults
    policy_w = policy.get("width", "auto")
    policy_h = policy.get("height", "auto")
    match_scale = policy.get("orientation_match_scale", 1.0)
    allow_upscale = policy.get("allow_upscale", False)
    
    # --- 1. Calculate Container Base ---
    container_w = _parse_policy_dimension(policy_w, page_w_emu)
    container_h = _parse_policy_dimension(policy_h, page_h_emu)

    # --- 2. Apply 'orientation_match_scale' ---
    img_orientation = _get_orientation(img_w_emu, img_h_emu)
    page_orientation = _get_orientation(page_w_emu, page_h_emu)
    
    if img_orientation != "square" and (img_orientation == page_orientation):
        if page_orientation == "portrait":
            # If both are portrait, scale down the container height
            container_h = Emu(container_h * match_scale)
        else:
            # If both are landscape, scale down the container width
            container_w = Emu(container_w * match_scale)

    # --- 3. Calculate 'CONTAIN' ratio ---
    # Handle potential divide-by-zero
    if img_w_emu == 0 or img_h_emu == 0:
        return (Emu(0), Emu(0))
        
    ratio_width = container_w / img_w_emu
    ratio_height = container_h / img_h_emu
    
    final_ratio = min(ratio_width, ratio_height)

    # --- 4. Apply 'allow_upscale' lock ---
    if not allow_upscale and final_ratio > 1.0:
        final_ratio = 1.0
        
    # --- 5. Return Final Dimensions ---
    final_width = Emu(img_w_emu * final_ratio)
    final_height = Emu(img_h_emu * final_ratio)
    
    return (final_width, final_height)

# --------------------------------------> END [ LAYOUT CALCULATIONS ... ]