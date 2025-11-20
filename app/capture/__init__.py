"""
Capture Layer

Component responsible for capturing screen content using plugin-based subprocess isolation.
Uses DirectX (DXCam) or Screenshot capture methods via isolated worker processes.
"""

# Import NEW plugin-based capture layer (recommended)
try:
    from .plugin_capture_layer import PluginCaptureLayer
except ImportError as e:
    print(f"Warning: Could not import PluginCaptureLayer: {e}")
    PluginCaptureLayer = None

# Import plugin manager
try:
    from .capture_plugin_manager import CapturePluginManager
except ImportError as e:
    print(f"Warning: Could not import CapturePluginManager: {e}")
    CapturePluginManager = None

# Import legacy capture layer (deprecated - kept for backward compatibility)
try:
    from .capture_layer import CaptureLayer, CaptureLayerError, CaptureBackend, AdaptiveCaptureController, FallbackDetectionSystem
except ImportError as e:
    print(f"Warning: Could not import legacy CaptureLayer: {e}")
    CaptureLayer = None
    CaptureLayerError = Exception
    CaptureBackend = None

# Import DirectX capture components (used by legacy system)
try:
    from .directx_capture import DirectXCaptureLayer, DirectXDesktopCapture, DirectXCaptureError, CaptureStatus
except ImportError as e:
    DirectXCaptureLayer = None
    DirectXDesktopCapture = None
    DirectXCaptureError = Exception
    CaptureStatus = None

# Import multi-monitor support
try:
    from .multi_monitor_support import MultiMonitorManager, MonitorInfo, MonitorOrientation
except ImportError as e:
    print(f"Warning: Could not import multi-monitor support: {e}")
    MultiMonitorManager = None

# Import screenshot capture (used by legacy system)
try:
    from .screenshot_capture import FallbackScreenshotCapture, ScreenshotCaptureError, ScreenshotMethod, ScreenshotMethodDetector
except ImportError as e:
    print(f"Warning: Could not import screenshot capture: {e}")
    FallbackScreenshotCapture = None

__all__ = [
    # NEW plugin-based system (recommended)
    'PluginCaptureLayer',
    'CapturePluginManager',
    
    # Legacy system (deprecated)
    'CaptureLayer',
    'CaptureLayerError', 
    'CaptureBackend',
    'AdaptiveCaptureController',
    'FallbackDetectionSystem',
    
    # DirectX components
    'DirectXCaptureLayer',
    'DirectXDesktopCapture', 
    'DirectXCaptureError',
    'CaptureStatus',
    
    # Multi-monitor support
    'MultiMonitorManager',
    'MonitorInfo',
    'MonitorOrientation',
    
    # Screenshot components
    'FallbackScreenshotCapture',
    'ScreenshotCaptureError',
    'ScreenshotMethod',
    'ScreenshotMethodDetector'
]