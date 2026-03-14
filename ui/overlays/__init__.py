"""
Overlay Rendering System

Translation overlay display, thread-safe access, and performance monitoring.
"""

from .overlay_manager import (
    TranslationOverlay,
    OverlayManager,
    OverlayStyle,
    OverlayConfig,
    OverlayPresets,
    OverlayPosition,
    AnimationType,
)
from .overlay_adapter import PyQt6OverlayAdapter, create_overlay_system
from .thread_safe_overlay import (
    ThreadSafeOverlaySystem,
    create_thread_safe_overlay_system,
)
from .performance_overlay import PerformanceOverlay
from .region_visualizer import RegionVisualizer

__all__ = [
    'TranslationOverlay',
    'OverlayManager',
    'OverlayStyle',
    'OverlayConfig',
    'OverlayPresets',
    'OverlayPosition',
    'AnimationType',
    'PyQt6OverlayAdapter',
    'create_overlay_system',
    'ThreadSafeOverlaySystem',
    'create_thread_safe_overlay_system',
    'PerformanceOverlay',
    'RegionVisualizer',
]
