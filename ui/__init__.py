"""
UI Components Package

This package contains isolated, reusable UI components extracted from the main application.
Each component is designed to be independent and can be used across different projects.
"""

# PyQt6 Overlay System
from .overlay_pyqt6 import (
    TranslationOverlay,
    OverlayManager,
    OverlayStyle,
    OverlayConfig,
    OverlayPresets,
    OverlayPosition,
    AnimationType
)
from .overlay_integration import (
    PyQt6OverlayAdapter,
    create_overlay_system
)

__all__ = [
    # PyQt6 Overlay System
    'TranslationOverlay',
    'OverlayManager',
    'OverlayStyle',
    'OverlayConfig',
    'OverlayPresets',
    'OverlayPosition',
    'AnimationType',
    'PyQt6OverlayAdapter',
    'create_overlay_system',
]
