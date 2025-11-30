"""
Base Interfaces and Abstract Classes

Defines the core interfaces that all major components must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

try:
    from .models import (
        Frame, TextBlock, Translation, PerformanceMetrics, CaptureRegion,
        RuntimeMode, PerformanceProfile, Rectangle
    )
except ImportError:
    from app.models import (
        Frame, TextBlock, Translation, PerformanceMetrics, CaptureRegion,
        RuntimeMode, PerformanceProfile, Rectangle
    )


class CaptureSource(Enum):
    """Source types for screen capture."""
    FULL_SCREEN = "full_screen"
    WINDOW = "window"
    CUSTOM_REGION = "custom_region"


class OCREngine(Enum):
    """Available OCR engines."""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    ONNX = "onnx"


class TranslationEngine(Enum):
    """Available translation engines."""
    MARIANMT = "marianmt"
    MARIANMT_GPU = "marianmt_gpu"  # Plugin-based MarianMT (supports both GPU and CPU)
    DICTIONARY = "dictionary"
    GOOGLE_TRANSLATE = "google_translate"
    GOOGLE_FREE = "google_free"
    GOOGLE = "google"
    LIBRETRANSLATE = "libretranslate"
    DEEPL = "deepl"
    AZURE_TRANSLATOR = "azure_translator"
    AZURE = "azure"


class RenderMode(Enum):
    """Overlay rendering modes."""
    DIRECTX = "directx"
    WINDOW = "window"


# Core Component Interfaces

class ICaptureLayer(ABC):
    """Interface for screen capture functionality."""
    
    @abstractmethod
    def capture_frame(self, source: CaptureSource, region: CaptureRegion) -> Frame:
        """Capture a frame from the specified source and region."""
        pass
    
    @abstractmethod
    def set_capture_mode(self, mode: str) -> bool:
        """Set the capture mode (DirectX, Screenshot, etc.)."""
        pass
    
    @abstractmethod
    def get_supported_modes(self) -> List[str]:
        """Get list of supported capture modes."""
        pass
    
    @abstractmethod
    def configure_capture_rate(self, fps: int) -> bool:
        """Configure the capture frame rate."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if capture functionality is available."""
        pass


class IPreprocessingLayer(ABC):
    """Interface for image preprocessing functionality."""
    
    @abstractmethod
    def preprocess(self, frame: Frame, profile: PerformanceProfile) -> Frame:
        """Preprocess frame for optimal OCR accuracy."""
        pass
    
    @abstractmethod
    def detect_roi(self, frame: Frame) -> List[Rectangle]:
        """Detect regions of interest containing text."""
        pass
    
    @abstractmethod
    def apply_filters(self, frame: Frame, filters: List[str]) -> Frame:
        """Apply specified image filters to frame."""
        pass
    
    @abstractmethod
    def get_frame_diff(self, current: Frame, previous: Frame) -> Frame:
        """Calculate difference between frames for change detection."""
        pass


class IOCRLayer(ABC):
    """Interface for OCR functionality."""
    
    @abstractmethod
    def extract_text(self, frame: Frame, engine: OCREngine, options: Dict[str, Any]) -> List[TextBlock]:
        """Extract text from frame using specified OCR engine."""
        pass
    
    @abstractmethod
    def register_engine(self, engine_name: str, engine_instance: Any) -> bool:
        """Register a new OCR engine."""
        pass
    
    @abstractmethod
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engines."""
        pass
    
    @abstractmethod
    def benchmark_engines(self, test_frames: List[Frame]) -> Dict[str, PerformanceMetrics]:
        """Benchmark performance of available OCR engines."""
        pass
    
    @abstractmethod
    def set_language(self, language: str) -> bool:
        """Set the expected language for OCR processing."""
        pass


class ITranslationLayer(ABC):
    """Interface for translation functionality."""
    
    @abstractmethod
    def translate(self, text: str, engine: TranslationEngine, src_lang: str, 
                 tgt_lang: str, options: Dict[str, Any]) -> str:
        """Translate text using specified engine and language pair."""
        pass
    
    @abstractmethod
    def translate_batch(self, texts: List[str], engine: TranslationEngine, 
                       src_lang: str, tgt_lang: str) -> List[str]:
        """Translate multiple texts in batch for efficiency."""
        pass
    
    @abstractmethod
    def get_supported_languages(self, engine: TranslationEngine) -> List[str]:
        """Get supported languages for specified engine."""
        pass
    
    @abstractmethod
    def cache_translation(self, source: str, target: str, translation: str) -> None:
        """Cache translation result for future use."""
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """Clear translation cache."""
        pass


class IOverlayRenderer(ABC):
    """Interface for overlay rendering functionality."""
    
    @abstractmethod
    def render_overlay(self, frame: Frame, translations: List[Translation], 
                      mode: RenderMode) -> None:
        """Render translated text overlay on screen."""
        pass
    
    @abstractmethod
    def set_overlay_style(self, style: Dict[str, Any]) -> None:
        """Configure overlay appearance and styling."""
        pass
    
    @abstractmethod
    def toggle_overlay(self, visible: bool) -> None:
        """Show or hide the overlay."""
        pass
    
    @abstractmethod
    def update_positions(self, translations: List[Translation]) -> None:
        """Update overlay text positions."""
        pass
    
    @abstractmethod
    def is_overlay_active(self) -> bool:
        """Check if overlay is currently active."""
        pass


class ISystemController(ABC):
    """Interface for system coordination and control."""
    
    @abstractmethod
    def start_system(self) -> bool:
        """Start the translation system."""
        pass
    
    @abstractmethod
    def stop_system(self) -> bool:
        """Stop the translation system."""
        pass
    
    @abstractmethod
    def set_runtime_mode(self, mode: RuntimeMode) -> bool:
        """Set system runtime mode (GPU/CPU)."""
        pass
    
    @abstractmethod
    def set_performance_profile(self, profile: PerformanceProfile) -> bool:
        """Set system performance profile."""
        pass
    
    @abstractmethod
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and metrics."""
        pass
    
    @abstractmethod
    def register_component(self, name: str, component: Any) -> bool:
        """Register a system component."""
        pass


class IConfigurationManager(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def load_configuration(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load system configuration from file."""
        pass
    
    @abstractmethod
    def save_configuration(self, config: Dict[str, Any], 
                          config_path: Optional[str] = None) -> bool:
        """Save system configuration to file."""
        pass
    
    @abstractmethod
    def get_default_configuration(self) -> Dict[str, Any]:
        """Get default system configuration."""
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration parameters."""
        pass
    
    @abstractmethod
    def update_setting(self, key: str, value: Any) -> bool:
        """Update a specific configuration setting."""
        pass


class IDependencyManager(ABC):
    """Interface for dependency management."""
    
    @abstractmethod
    def check_dependencies(self) -> Dict[str, bool]:
        """Check status of all required dependencies."""
        pass
    
    @abstractmethod
    def install_missing_dependencies(self) -> Dict[str, bool]:
        """Install any missing dependencies."""
        pass
    
    @abstractmethod
    def verify_installation(self, dependency: str) -> bool:
        """Verify that a dependency is properly installed."""
        pass
    
    @abstractmethod
    def get_dependency_manifest(self) -> Dict[str, Any]:
        """Get manifest of all dependencies and their versions."""
        pass


class IPerformanceMonitor(ABC):
    """Interface for performance monitoring."""
    
    @abstractmethod
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        pass
    
    @abstractmethod
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        pass
    
    @abstractmethod
    def get_metrics_history(self, duration_seconds: int) -> List[PerformanceMetrics]:
        """Get performance metrics history for specified duration."""
        pass
    
    @abstractmethod
    def set_alert_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Set performance alert thresholds."""
        pass


class ILogger(ABC):
    """Interface for logging functionality."""
    
    @abstractmethod
    def log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a message with specified level and optional context."""
        pass
    
    @abstractmethod
    def set_log_level(self, level: str) -> None:
        """Set minimum logging level."""
        pass
    
    @abstractmethod
    def add_handler(self, handler: Any) -> None:
        """Add a log handler."""
        pass
    
    @abstractmethod
    def get_logs(self, level: Optional[str] = None, 
                limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve logged messages."""
        pass


# Event System Interfaces

class IEventHandler(ABC):
    """Interface for event handling."""
    
    @abstractmethod
    def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle a system event."""
        pass


class IEventEmitter(ABC):
    """Interface for event emission."""
    
    @abstractmethod
    def emit_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Emit a system event."""
        pass
    
    @abstractmethod
    def register_handler(self, event_type: str, handler: IEventHandler) -> None:
        """Register an event handler for specific event type."""
        pass
    
    @abstractmethod
    def unregister_handler(self, event_type: str, handler: IEventHandler) -> None:
        """Unregister an event handler."""
        pass


# Plugin System Interfaces

class IPlugin(ABC):
    """Base interface for system plugins."""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information and metadata."""
        pass


class IPluginManager(ABC):
    """Interface for plugin management."""
    
    @abstractmethod
    def load_plugin(self, plugin_path: str) -> bool:
        """Load a plugin from specified path."""
        pass
    
    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin by name."""
        pass
    
    @abstractmethod
    def get_loaded_plugins(self) -> List[str]:
        """Get list of currently loaded plugins."""
        pass
    
    @abstractmethod
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Get information about a specific plugin."""
        pass