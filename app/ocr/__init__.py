"""
OCR Module

This module provides OCR (Optical Character Recognition) functionality
for the Translation System with a comprehensive plugin system for
supporting multiple OCR engines.
"""

from .ocr_engine_interface import (
    IOCREngine,
    OCREngineType,
    OCREngineStatus,
    OCREngineCapabilities,
    OCREngineMetrics,
    OCRProcessingOptions,
    OCREnginePlugin,
    OCRBenchmarkResult,
    OCREngineBenchmarker
)

from .ocr_plugin_manager import (
    OCRPluginManager,
    OCRPluginRegistry,
    PluginInfo,
    PluginLoadStatus
)

from .ocr_layer import (
    OCRLayer,
    OCRLayerConfig,
    OCRLayerStatus,
    OCRResult,
    OCRCache
)

__all__ = [
    # Engine Interface
    "IOCREngine",
    "OCREngineType", 
    "OCREngineStatus",
    "OCREngineCapabilities",
    "OCREngineMetrics",
    "OCRProcessingOptions",
    "OCREnginePlugin",
    "OCRBenchmarkResult",
    "OCREngineBenchmarker",
    
    # Plugin Management
    "OCRPluginManager",
    "OCRPluginRegistry", 
    "PluginInfo",
    "PluginLoadStatus",
    
    # Main OCR Layer
    "OCRLayer",
    "OCRLayerConfig",
    "OCRLayerStatus", 
    "OCRResult",
    "OCRCache"
]