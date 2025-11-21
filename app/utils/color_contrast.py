"""
Color Contrast Utilities

Provides functions for calculating color contrast and determining optimal
text/background colors for readability.
"""

import numpy as np
from typing import Tuple, Optional


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    Convert RGB tuple to hex color string.
    
    Args:
        rgb: Tuple of (r, g, b) values (0-255)
        
    Returns:
        Hex color string (e.g., "#FFFFFF")
    """
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.
    
    Args:
        hex_color: Hex color string (e.g., "#FFFFFF" or "FFFFFF")
        
    Returns:
        Tuple of (r, g, b) values (0-255)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def calculate_luminance(rgb: Tuple[int, int, int]) -> float:
    """
    Calculate relative luminance of a color according to WCAG 2.0.
    
    Args:
        rgb: Tuple of (r, g, b) values (0-255)
        
    Returns:
        Relative luminance (0.0 to 1.0)
    """
    # Convert to 0-1 range
    r, g, b = [x / 255.0 for x in rgb]
    
    # Apply gamma correction
    def gamma_correct(channel):
        if channel <= 0.03928:
            return channel / 12.92
        else:
            return ((channel + 0.055) / 1.055) ** 2.4
    
    r = gamma_correct(r)
    g = gamma_correct(g)
    b = gamma_correct(b)
    
    # Calculate luminance using WCAG formula
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(color1: Tuple[int, int, int], 
                            color2: Tuple[int, int, int]) -> float:
    """
    Calculate contrast ratio between two colors according to WCAG 2.0.
    
    Args:
        color1: First color as RGB tuple (0-255)
        color2: Second color as RGB tuple (0-255)
        
    Returns:
        Contrast ratio (1.0 to 21.0)
    """
    lum1 = calculate_luminance(color1)
    lum2 = calculate_luminance(color2)
    
    # Ensure lighter color is in numerator
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)


def is_light_color(rgb: Tuple[int, int, int]) -> bool:
    """
    Determine if a color is light or dark.
    
    Args:
        rgb: Color as RGB tuple (0-255)
        
    Returns:
        True if color is light, False if dark
    """
    luminance = calculate_luminance(rgb)
    return luminance > 0.5


def get_contrasting_color(background_rgb: Tuple[int, int, int],
                         prefer_white: bool = True) -> Tuple[int, int, int]:
    """
    Get a contrasting text color for a given background color.
    
    Args:
        background_rgb: Background color as RGB tuple (0-255)
        prefer_white: If True, prefer white text on dark backgrounds
        
    Returns:
        Contrasting text color as RGB tuple (0-255)
    """
    is_light = is_light_color(background_rgb)
    
    if is_light:
        # Light background -> dark text
        return (0, 0, 0)  # Black
    else:
        # Dark background -> light text
        return (255, 255, 255)  # White


def get_optimal_colors(background_rgb: Tuple[int, int, int],
                      min_contrast_ratio: float = 4.5) -> Tuple[Tuple[int, int, int], 
                                                                 Tuple[int, int, int]]:
    """
    Get optimal text and background colors for maximum readability.
    
    Args:
        background_rgb: Detected background color as RGB tuple (0-255)
        min_contrast_ratio: Minimum acceptable contrast ratio (WCAG AA = 4.5, AAA = 7.0)
        
    Returns:
        Tuple of (text_color, adjusted_background_color) as RGB tuples
    """
    is_light = is_light_color(background_rgb)
    
    if is_light:
        # Light background detected
        text_color = (0, 0, 0)  # Black text
        
        # Check if we need to darken the background for better contrast
        contrast = calculate_contrast_ratio(text_color, background_rgb)
        if contrast < min_contrast_ratio:
            # Lighten background more
            bg_color = (255, 255, 255)  # Pure white
        else:
            # Use semi-transparent light background
            bg_color = (245, 245, 245)  # Very light gray
    else:
        # Dark background detected
        text_color = (255, 255, 255)  # White text
        
        # Check if we need to lighten the background for better contrast
        contrast = calculate_contrast_ratio(text_color, background_rgb)
        if contrast < min_contrast_ratio:
            # Darken background more
            bg_color = (0, 0, 0)  # Pure black
        else:
            # Use semi-transparent dark background
            bg_color = (30, 30, 30)  # Very dark gray
    
    return text_color, bg_color


def detect_background_color_from_image(image: np.ndarray,
                                      position: Tuple[int, int],
                                      sample_size: int = 20) -> Tuple[int, int, int]:
    """
    Detect the background color at a specific position in an image.
    
    Args:
        image: Image as numpy array (BGR or RGB format)
        position: (x, y) position to sample
        sample_size: Size of the area to sample around the position
        
    Returns:
        Average background color as RGB tuple (0-255)
    """
    x, y = position
    height, width = image.shape[:2]
    
    # Ensure we don't go out of bounds
    x1 = max(0, x - sample_size // 2)
    y1 = max(0, y - sample_size // 2)
    x2 = min(width, x + sample_size // 2)
    y2 = min(height, y + sample_size // 2)
    
    # Extract region
    region = image[y1:y2, x1:x2]
    
    # Calculate average color
    if len(region.shape) == 3:
        # Color image
        avg_color = np.mean(region, axis=(0, 1))
        
        # Convert BGR to RGB if needed (OpenCV uses BGR)
        if image.shape[2] == 3:
            avg_color = avg_color[::-1]  # Reverse to RGB
        
        return tuple(int(c) for c in avg_color[:3])
    else:
        # Grayscale image
        avg_gray = int(np.mean(region))
        return (avg_gray, avg_gray, avg_gray)


def adjust_colors_for_contrast(text_color: str,
                               bg_color: str,
                               detected_bg_rgb: Tuple[int, int, int]) -> Tuple[str, str]:
    """
    Adjust text and background colors based on detected background color.
    
    Args:
        text_color: Current text color as hex string
        bg_color: Current background color as hex string
        detected_bg_rgb: Detected background color as RGB tuple
        
    Returns:
        Tuple of (adjusted_text_color, adjusted_bg_color) as hex strings
    """
    # Get optimal colors based on detected background
    optimal_text, optimal_bg = get_optimal_colors(detected_bg_rgb)
    
    # Convert to hex
    text_hex = rgb_to_hex(optimal_text)
    bg_hex = rgb_to_hex(optimal_bg)
    
    return text_hex, bg_hex
