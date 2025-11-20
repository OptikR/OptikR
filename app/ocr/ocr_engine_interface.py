"""
OCR Engine Interface and Plugin System

This module provides the abstract base classes and interfaces for OCR engines,
along with a comprehensive plugin management system for registering and managing
different OCR implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable
from enum import Enum
import time
import threading
from pathlib import Path
import importlib.util
import inspect
import logging

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.models import Frame, TextBlock, Rectangle, PerformanceProfile
    from app.interfaces import IPlugin
except ImportError:
    from app.models import Frame, TextBlock, Rectangle, PerformanceProfile
    from app.interfaces import IPlugin


class OCREngineType(Enum):
    """OCR engine type enumeration."""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    ONNX_RUNTIME = "onnx_runtime"
    MANGA_OCR = "manga_ocr"
    HYBRID_OCR = "hybrid_ocr"
    CUSTOM = "custom"


class OCREngineStatus(Enum):
    """OCR engine status enumeration."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class OCREngineCapabilities:
    """OCR engine capabilities and features."""
    supported_languages: List[str] = field(default_factory=list)
    supports_gpu: bool = False
    supports_batch_processing: bool = False
    supports_confidence_scores: bool = True
    supports_text_formatting: bool = False
    supports_text_orientation: bool = False
    max_image_size: Tuple[int, int] = (4096, 4096)
    min_image_size: Tuple[int, int] = (32, 32)
    supported_image_formats: List[str] = field(default_factory=lambda: ["RGB", "GRAY"])
    memory_requirements_mb: int = 512
    initialization_time_ms: int = 1000


@dataclass
class OCREngineMetrics:
    """OCR engine performance metrics."""
    total_processed: int = 0
    total_processing_time_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    accuracy_score: float = 0.0
    confidence_score: float = 0.0
    last_processing_time_ms: float = 0.0
    peak_memory_usage_mb: float = 0.0
    
    def update_processing_time(self, processing_time_ms: float) -> None:
        """Update processing time metrics."""
        self.total_processed += 1
        self.total_processing_time_ms += processing_time_ms
        self.average_processing_time_ms = self.total_processing_time_ms / self.total_processed
        self.last_processing_time_ms = processing_time_ms
    
    def record_success(self, confidence: float = 0.0) -> None:
        """Record successful OCR operation."""
        self.success_count += 1
        if confidence > 0:
            # Update running average of confidence
            total_confidence = self.confidence_score * (self.success_count - 1) + confidence
            self.confidence_score = total_confidence / self.success_count
    
    def record_error(self) -> None:
        """Record OCR error."""
        self.error_count += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 0.0


@dataclass
class OCRProcessingOptions:
    """OCR processing configuration options."""
    language: str = "en"
    confidence_threshold: float = 0.5
    preprocessing_enabled: bool = True
    gpu_acceleration: bool = False
    batch_size: int = 1
    timeout_ms: int = 5000
    custom_config: Dict[str, Any] = field(default_factory=dict)


class IOCREngine(ABC):
    """Abstract base class for OCR engines."""
    
    def __init__(self, engine_name: str, engine_type: OCREngineType):
        """Initialize OCR engine with name and type."""
        self.engine_name = engine_name
        self.engine_type = engine_type
        self.status = OCREngineStatus.UNINITIALIZED
        self.capabilities = OCREngineCapabilities()
        self.metrics = OCREngineMetrics()
        self._lock = threading.RLock()
        self._logger = logging.getLogger(f"ocr.{engine_name}")
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the OCR engine with configuration.
        
        Args:
            config: Engine-specific configuration parameters
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """
        Extract text from frame using this OCR engine.
        
        Args:
            frame: Input frame containing image data
            options: Processing options and configuration
            
        Returns:
            List of extracted text blocks with positions and confidence
        """
        pass
    
    @abstractmethod
    def extract_text_batch(self, frames: List[Frame], options: OCRProcessingOptions) -> List[List[TextBlock]]:
        """
        Extract text from multiple frames in batch.
        
        Args:
            frames: List of input frames
            options: Processing options and configuration
            
        Returns:
            List of text block lists, one for each input frame
        """
        pass
    
    @abstractmethod
    def set_language(self, language: str) -> bool:
        """
        Set the expected language for OCR processing.
        
        Args:
            language: Language code (e.g., 'en', 'zh', 'ja')
            
        Returns:
            True if language is supported and set successfully
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages.
        
        Returns:
            List of supported language codes
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up engine resources and shutdown."""
        pass
    
    def get_capabilities(self) -> OCREngineCapabilities:
        """Get engine capabilities."""
        return self.capabilities
    
    def get_metrics(self) -> OCREngineMetrics:
        """Get engine performance metrics."""
        with self._lock:
            return self.metrics
    
    def get_status(self) -> OCREngineStatus:
        """Get current engine status."""
        return self.status
    
    def is_ready(self) -> bool:
        """Check if engine is ready for processing."""
        return self.status == OCREngineStatus.READY
    
    def validate_frame(self, frame: Frame) -> bool:
        """
        Validate if frame is suitable for this engine.
        
        Args:
            frame: Frame to validate
            
        Returns:
            True if frame is valid for processing
        """
        if frame.data is None or frame.data.size == 0:
            return False
        
        height, width = frame.data.shape[:2]
        min_w, min_h = self.capabilities.min_image_size
        max_w, max_h = self.capabilities.max_image_size
        
        return (min_w <= width <= max_w and min_h <= height <= max_h)
    
    def _record_processing_start(self) -> float:
        """Record processing start time."""
        with self._lock:
            self.status = OCREngineStatus.PROCESSING
        return time.time() * 1000  # Return timestamp in milliseconds
    
    def _record_processing_end(self, start_time_ms: float, success: bool, confidence: float = 0.0) -> None:
        """Record processing completion."""
        end_time_ms = time.time() * 1000
        processing_time = end_time_ms - start_time_ms
        
        with self._lock:
            self.metrics.update_processing_time(processing_time)
            if success:
                self.metrics.record_success(confidence)
                self.status = OCREngineStatus.READY
            else:
                self.metrics.record_error()
                self.status = OCREngineStatus.ERROR


class OCREnginePlugin(IPlugin):
    """Base class for OCR engine plugins."""
    
    def __init__(self, engine_class: type, plugin_info: Dict[str, Any]):
        """
        Initialize OCR engine plugin.
        
        Args:
            engine_class: OCR engine class that implements IOCREngine
            plugin_info: Plugin metadata and information
        """
        self.engine_class = engine_class
        self.plugin_info = plugin_info
        self._engine_instance: Optional[IOCREngine] = None
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin and create engine instance."""
        try:
            # Validate engine class has required methods (duck typing)
            required_methods = ['initialize', 'extract_text', 'get_status', 'is_ready']
            for method in required_methods:
                if not hasattr(self.engine_class, method):
                    raise ValueError(f"Engine class must implement {method} method")
            
            # Create engine instance
            engine_name = self.plugin_info.get("name", "unknown")
            engine_type = self.plugin_info.get("type", "custom")
            
            # Try to create instance with different signatures
            try:
                self._engine_instance = self.engine_class(engine_name, engine_type)
            except TypeError:
                # Try without engine_type
                try:
                    self._engine_instance = self.engine_class(engine_name)
                except TypeError:
                    # Try with no arguments
                    self._engine_instance = self.engine_class()
            
            # Initialize engine
            return self._engine_instance.initialize(config)
            
        except Exception as e:
            logging.error(f"Failed to initialize OCR engine plugin: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        if self._engine_instance:
            self._engine_instance.cleanup()
            self._engine_instance = None
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        return self.plugin_info.copy()
    
    def get_engine_instance(self) -> Optional[IOCREngine]:
        """Get the OCR engine instance."""
        return self._engine_instance


@dataclass
class OCRBenchmarkResult:
    """OCR engine benchmark results."""
    engine_name: str
    total_frames_processed: int
    total_processing_time_ms: float
    average_processing_time_ms: float
    accuracy_score: float
    confidence_score: float
    success_rate: float
    memory_usage_mb: float
    error_count: int
    benchmark_timestamp: float = field(default_factory=lambda: time.time())


class OCREngineBenchmarker:
    """OCR engine benchmarking system."""
    
    def __init__(self):
        """Initialize benchmarker."""
        self._logger = logging.getLogger("ocr.benchmarker")
    
    def benchmark_engine(self, engine: IOCREngine, test_frames: List[Frame], 
                        options: OCRProcessingOptions) -> OCRBenchmarkResult:
        """
        Benchmark OCR engine performance.
        
        Args:
            engine: OCR engine to benchmark
            test_frames: List of test frames for benchmarking
            options: Processing options for benchmarking
            
        Returns:
            Benchmark results
        """
        if not engine.is_ready():
            raise ValueError(f"Engine {engine.engine_name} is not ready for benchmarking")
        
        start_time = time.time() * 1000
        total_confidence = 0.0
        successful_extractions = 0
        error_count = 0
        
        # Reset engine metrics for clean benchmark
        engine.metrics = OCREngineMetrics()
        
        self._logger.info(f"Starting benchmark for engine {engine.engine_name} with {len(test_frames)} frames")
        
        for i, frame in enumerate(test_frames):
            try:
                text_blocks = engine.extract_text(frame, options)
                if text_blocks:
                    successful_extractions += 1
                    # Calculate average confidence for this frame
                    frame_confidence = sum(block.confidence for block in text_blocks) / len(text_blocks)
                    total_confidence += frame_confidence
                
            except Exception as e:
                error_count += 1
                self._logger.warning(f"Benchmark error on frame {i}: {e}")
        
        end_time = time.time() * 1000
        total_time = end_time - start_time
        
        # Calculate metrics
        avg_processing_time = total_time / len(test_frames) if test_frames else 0
        accuracy_score = successful_extractions / len(test_frames) if test_frames else 0
        confidence_score = total_confidence / successful_extractions if successful_extractions > 0 else 0
        success_rate = (len(test_frames) - error_count) / len(test_frames) * 100 if test_frames else 0
        
        result = OCRBenchmarkResult(
            engine_name=engine.engine_name,
            total_frames_processed=len(test_frames),
            total_processing_time_ms=total_time,
            average_processing_time_ms=avg_processing_time,
            accuracy_score=accuracy_score,
            confidence_score=confidence_score,
            success_rate=success_rate,
            memory_usage_mb=engine.metrics.peak_memory_usage_mb,
            error_count=error_count
        )
        
        self._logger.info(f"Benchmark completed for {engine.engine_name}: "
                         f"avg_time={avg_processing_time:.2f}ms, "
                         f"accuracy={accuracy_score:.2f}, "
                         f"success_rate={success_rate:.1f}%")
        
        return result
    
    def compare_engines(self, engines: List[IOCREngine], test_frames: List[Frame], 
                       options: OCRProcessingOptions) -> Dict[str, OCRBenchmarkResult]:
        """
        Compare multiple OCR engines.
        
        Args:
            engines: List of OCR engines to compare
            test_frames: Test frames for comparison
            options: Processing options
            
        Returns:
            Dictionary mapping engine names to benchmark results
        """
        results = {}
        
        for engine in engines:
            if engine.is_ready():
                try:
                    result = self.benchmark_engine(engine, test_frames, options)
                    results[engine.engine_name] = result
                except Exception as e:
                    self._logger.error(f"Failed to benchmark engine {engine.engine_name}: {e}")
        
        return results
    
    def get_best_engine(self, benchmark_results: Dict[str, OCRBenchmarkResult], 
                       criteria: str = "balanced") -> Optional[str]:
        """
        Get the best performing engine based on criteria.
        
        Args:
            benchmark_results: Results from engine comparison
            criteria: Selection criteria ("speed", "accuracy", "balanced")
            
        Returns:
            Name of best performing engine or None if no results
        """
        if not benchmark_results:
            return None
        
        if criteria == "speed":
            return min(benchmark_results.keys(), 
                      key=lambda name: benchmark_results[name].average_processing_time_ms)
        elif criteria == "accuracy":
            return max(benchmark_results.keys(), 
                      key=lambda name: benchmark_results[name].accuracy_score)
        elif criteria == "balanced":
            # Balanced score: normalize speed and accuracy, then combine
            def balanced_score(result: OCRBenchmarkResult) -> float:
                # Lower processing time is better (invert for scoring)
                speed_score = 1.0 / (result.average_processing_time_ms + 1)
                accuracy_score = result.accuracy_score
                return (speed_score + accuracy_score) / 2
            
            return max(benchmark_results.keys(), 
                      key=lambda name: balanced_score(benchmark_results[name]))
        else:
            raise ValueError(f"Unknown criteria: {criteria}")