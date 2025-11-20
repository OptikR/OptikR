"""
OCR Layer Implementation

This module provides the main OCR layer that integrates with the plugin system
to provide unified OCR functionality across multiple engines.
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .ocr_engine_interface import (
    IOCREngine, OCREngineType, OCREngineStatus, OCRProcessingOptions,
    OCRBenchmarkResult, OCREngineBenchmarker
)
from .ocr_plugin_manager import OCRPluginManager, PluginLoadStatus
from .parallel_processor import ParallelOCRProcessor, create_parallel_processor, OCRResult as ParallelOCRResult
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.models import Frame, TextBlock, Rectangle, PerformanceProfile
    from app.interfaces import IOCRLayer
except ImportError:
    from models import Frame, TextBlock, Rectangle, PerformanceProfile
    from interfaces import IOCRLayer


class OCRLayerStatus(Enum):
    """OCR layer status enumeration."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class OCRLayerConfig:
    """OCR layer configuration."""
    default_engine: str = "easyocr_gpu"
    fallback_engines: List[str] = field(default_factory=list)
    auto_fallback_enabled: bool = True
    benchmark_on_startup: bool = False
    cache_enabled: bool = True
    cache_size_limit: int = 1000
    processing_timeout_ms: int = 10000
    parallel_processing: bool = False
    max_parallel_workers: int = 4


@dataclass
class OCRResult:
    """OCR processing result with metadata."""
    text_blocks: List[TextBlock]
    engine_used: str
    processing_time_ms: float
    success: bool
    error_message: Optional[str] = None
    confidence_score: float = 0.0


class OCRCache:
    """Simple LRU cache for OCR results."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize cache with maximum size."""
        self.max_size = max_size
        self._cache: Dict[str, OCRResult] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()
    
    def _generate_key(self, frame: Frame, options: OCRProcessingOptions) -> str:
        """Generate cache key from frame and options."""
        # Use frame timestamp and hash of options for key
        options_hash = hash(f"{options.language}_{options.confidence_threshold}_{options.preprocessing_enabled}")
        return f"{frame.timestamp}_{options_hash}"
    
    def get(self, frame: Frame, options: OCRProcessingOptions) -> Optional[OCRResult]:
        """Get cached result if available."""
        key = self._generate_key(frame, options)
        
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
        
        return None
    
    def put(self, frame: Frame, options: OCRProcessingOptions, result: OCRResult) -> None:
        """Cache OCR result."""
        key = self._generate_key(frame, options)
        
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                self._access_order.remove(key)
            
            # Add to cache
            self._cache[key] = result
            self._access_order.append(key)
            
            # Evict oldest if over limit
            while len(self._cache) > self.max_size:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]
    
    def clear(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0
            }


class OCRLayer(IOCRLayer):
    """Main OCR layer implementation with plugin system integration."""
    
    def __init__(self, config: Optional[OCRLayerConfig] = None, 
                 plugin_directories: Optional[List[str]] = None,
                 config_manager=None):
        """
        Initialize OCR layer.
        
        Args:
            config: OCR layer configuration
            plugin_directories: Directories to search for OCR plugins
            config_manager: Configuration manager for runtime settings
        """
        self.config = config or OCRLayerConfig()
        self.plugin_manager = OCRPluginManager(plugin_directories, config_manager)
        self.benchmarker = OCREngineBenchmarker()
        
        self.status = OCRLayerStatus.UNINITIALIZED
        self._current_engine: Optional[str] = None
        self._benchmark_results: Dict[str, OCRBenchmarkResult] = {}
        self._cache = OCRCache(self.config.cache_size_limit) if self.config.cache_enabled else None
        
        self._lock = threading.RLock()
        self._logger = logging.getLogger("ocr.layer")
        
        # Parallel processing
        self._parallel_processor: Optional[ParallelOCRProcessor] = None
        self._parallel_enabled = config.parallel_processing if config else False
        
        # Event handlers
        self._error_handlers: List[Callable[[str, Exception], None]] = []
        self._processing_handlers: List[Callable[[str, OCRResult], None]] = []
    
    def initialize(self, auto_discover: bool = True, auto_load: bool = True) -> bool:
        """
        Initialize OCR layer and plugin system.
        
        Args:
            auto_discover: Automatically discover available plugins
            auto_load: Automatically load discovered plugins
            
        Returns:
            True if initialization successful
        """
        try:
            self.status = OCRLayerStatus.INITIALIZING
            self._logger.info("Initializing OCR layer...")
            
            # Discover plugins
            if auto_discover:
                discovered = self.plugin_manager.discover_plugins()
                self._logger.info(f"Discovered {len(discovered)} OCR plugins")
            
            # Load plugins
            if auto_load:
                load_results = self.plugin_manager.load_all_plugins()
                successful_loads = sum(1 for success in load_results.values() if success)
                self._logger.info(f"Successfully loaded {successful_loads}/{len(load_results)} plugins")
            
            # Set default engine
            available_engines = self.plugin_manager.get_available_engines()
            if available_engines:
                if self.config.default_engine in available_engines:
                    self._current_engine = self.config.default_engine
                else:
                    self._current_engine = available_engines[0]
                    self._logger.warning(f"Default engine {self.config.default_engine} not available, "
                                       f"using {self._current_engine}")
            else:
                self._logger.error("No OCR engines available after initialization")
                self.status = OCRLayerStatus.ERROR
                return False
            
            # Run benchmark if configured
            if self.config.benchmark_on_startup and available_engines:
                self._logger.info("Running startup benchmark...")
                # Note: Would need test frames for actual benchmarking
                # self._benchmark_results = self.plugin_manager.benchmark_engines(test_frames)
            
            self.status = OCRLayerStatus.READY
            self._logger.info(f"OCR layer initialized successfully with {len(available_engines)} engines")
            return True
            
        except Exception as e:
            self.status = OCRLayerStatus.ERROR
            self._logger.error(f"Failed to initialize OCR layer: {e}")
            return False
    
    def extract_text(self, frame: Frame, engine: Optional[str] = None, 
                    options: Optional[OCRProcessingOptions] = None) -> List[TextBlock]:
        """
        Extract text from frame using specified or default OCR engine.
        
        Args:
            frame: Input frame containing image data
            engine: Optional specific engine name to use
            options: Optional processing options
            
        Returns:
            List of extracted text blocks
        """
        if self.status != OCRLayerStatus.READY:
            raise RuntimeError(f"OCR layer not ready (status: {self.status})")
        
        # Use default options if not provided
        if options is None:
            options = OCRProcessingOptions()
        
        # Check cache first
        if self._cache:
            cached_result = self._cache.get(frame, options)
            if cached_result and cached_result.success:
                self._logger.debug(f"Returning cached OCR result for frame {frame.timestamp}")
                return cached_result.text_blocks
        
        # Determine engine to use
        target_engine = engine or self._current_engine
        if not target_engine:
            raise ValueError("No OCR engine specified and no default engine set")
        
        # Process with primary engine
        result = self._process_with_engine(frame, target_engine, options)
        
        # Try fallback engines if primary failed and auto-fallback enabled
        if not result.success and self.config.auto_fallback_enabled:
            for fallback_engine in self.config.fallback_engines:
                if fallback_engine != target_engine:
                    self._logger.info(f"Trying fallback engine: {fallback_engine}")
                    result = self._process_with_engine(frame, fallback_engine, options)
                    if result.success:
                        break
        
        # Cache result if successful
        if self._cache and result.success:
            self._cache.put(frame, options, result)
        
        # Trigger processing handlers
        for handler in self._processing_handlers:
            try:
                handler(target_engine, result)
            except Exception as e:
                self._logger.error(f"Error in processing handler: {e}")
        
        if not result.success:
            error_msg = result.error_message or "OCR processing failed"
            self._logger.error(f"OCR extraction failed: {error_msg}")
            # Trigger error handlers
            for handler in self._error_handlers:
                try:
                    handler(target_engine, Exception(error_msg))
                except Exception as e:
                    self._logger.error(f"Error in error handler: {e}")
        
        return result.text_blocks
    
    def _process_with_engine(self, frame: Frame, engine_name: str, 
                           options: OCRProcessingOptions) -> OCRResult:
        """
        Process frame with specific OCR engine.
        
        Args:
            frame: Input frame
            engine_name: Name of OCR engine to use
            options: Processing options
            
        Returns:
            OCR processing result
        """
        start_time = time.time() * 1000
        
        try:
            # Get engine instance
            engine = self.plugin_manager.get_engine(engine_name)
            if not engine:
                return OCRResult(
                    text_blocks=[],
                    engine_used=engine_name,
                    processing_time_ms=0,
                    success=False,
                    error_message=f"Engine {engine_name} not available"
                )
            
            if not engine.is_ready():
                return OCRResult(
                    text_blocks=[],
                    engine_used=engine_name,
                    processing_time_ms=0,
                    success=False,
                    error_message=f"Engine {engine_name} not ready (status: {engine.get_status()})"
                )
            
            # Validate frame
            if not engine.validate_frame(frame):
                return OCRResult(
                    text_blocks=[],
                    engine_used=engine_name,
                    processing_time_ms=0,
                    success=False,
                    error_message="Frame validation failed for engine"
                )
            
            # Extract text
            self.status = OCRLayerStatus.PROCESSING
            text_blocks = engine.extract_text(frame, options)
            self.status = OCRLayerStatus.READY
            
            end_time = time.time() * 1000
            processing_time = end_time - start_time
            
            # Calculate confidence score
            confidence_score = 0.0
            if text_blocks:
                confidence_score = sum(block.confidence for block in text_blocks) / len(text_blocks)
            
            return OCRResult(
                text_blocks=text_blocks,
                engine_used=engine_name,
                processing_time_ms=processing_time,
                success=True,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            self.status = OCRLayerStatus.READY  # Reset status
            end_time = time.time() * 1000
            processing_time = end_time - start_time
            
            return OCRResult(
                text_blocks=[],
                engine_used=engine_name,
                processing_time_ms=processing_time,
                success=False,
                error_message=str(e)
            )
    
    def register_engine(self, engine_name: str, engine_instance: IOCREngine) -> bool:
        """
        Register a new OCR engine instance.
        
        Args:
            engine_name: Name for the engine
            engine_instance: OCR engine instance
            
        Returns:
            True if registration successful
        """
        return self.plugin_manager.registry.register_engine(engine_instance)
    
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engine names."""
        return self.plugin_manager.get_available_engines()
    
    def benchmark_engines(self, test_frames: List[Frame], 
                         options: Optional[OCRProcessingOptions] = None) -> Dict[str, OCRBenchmarkResult]:
        """
        Benchmark all available OCR engines.
        
        Args:
            test_frames: Test frames for benchmarking
            options: Processing options for benchmarking
            
        Returns:
            Dictionary mapping engine names to benchmark results
        """
        if not options:
            options = OCRProcessingOptions()
        
        self._benchmark_results = self.plugin_manager.benchmark_engines(test_frames, options)
        return self._benchmark_results.copy()
    
    def set_language(self, language: str) -> bool:
        """
        Set the expected language for OCR processing.
        
        Automatically converts language codes to the format expected by the current engine:
        - Tesseract: 3-letter codes (eng, deu, spa, etc.)
        - EasyOCR/PaddleOCR/ONNX: ISO 639-1 codes (en, de, es, etc.)
        
        Args:
            language: Language code in any format (e.g., 'en', 'eng', 'de', 'deu')
            
        Returns:
            True if language is supported by current engine
        """
        if not self._current_engine:
            return False
        
        # Import language mapper
        try:
            from app.utils.language_mapper import LanguageCodeMapper
            
            # Get current engine name
            engine_name = self._current_engine.value if hasattr(self._current_engine, 'value') else str(self._current_engine)
            
            # Normalize language code for the current engine
            normalized_language = LanguageCodeMapper.normalize(language, engine_name)
            
            if normalized_language != language:
                self._logger.info(f"Language code converted: {language} -> {normalized_language} (for {engine_name})")
            
            # Set language on engine
            engine = self.plugin_manager.get_engine(self._current_engine)
            if engine:
                return engine.set_language(normalized_language)
            
        except Exception as e:
            self._logger.error(f"Failed to normalize language code: {e}")
            # Fallback to original behavior
            engine = self.plugin_manager.get_engine(self._current_engine)
            if engine:
                return engine.set_language(language)
        
        return False
    
    def set_default_engine(self, engine_name: str) -> bool:
        """
        Set the default OCR engine.
        
        Args:
            engine_name: Name of engine to set as default
            
        Returns:
            True if engine is available and set successfully
        """
        available_engines = self.get_available_engines()
        if engine_name in available_engines:
            self._current_engine = engine_name
            self.config.default_engine = engine_name
            self._logger.info(f"Set default OCR engine to: {engine_name}")
            return True
        
        self._logger.error(f"Engine {engine_name} not available for setting as default")
        return False
    
    def get_current_engine(self) -> Optional[str]:
        """Get the current default engine name."""
        return self._current_engine
    
    def get_engine_info(self, engine_name: str) -> Dict[str, Any]:
        """
        Get information about a specific engine.
        
        Args:
            engine_name: Name of engine
            
        Returns:
            Dictionary containing engine information
        """
        engine = self.plugin_manager.get_engine(engine_name)
        if not engine:
            return {}
        
        capabilities = engine.get_capabilities()
        metrics = engine.get_metrics()
        
        return {
            "name": engine.engine_name,
            "type": engine.engine_type.value,
            "status": engine.get_status().value,
            "capabilities": capabilities.__dict__,
            "metrics": metrics.__dict__,
            "is_ready": engine.is_ready()
        }
    
    def get_layer_statistics(self) -> Dict[str, Any]:
        """Get comprehensive OCR layer statistics."""
        plugin_stats = self.plugin_manager.get_plugin_statistics()
        cache_stats = self._cache.get_stats() if self._cache else {"enabled": False}
        
        engine_stats = {}
        for engine_name in self.get_available_engines():
            engine_info = self.get_engine_info(engine_name)
            engine_stats[engine_name] = engine_info
        
        return {
            "status": self.status.value,
            "current_engine": self._current_engine,
            "plugin_system": plugin_stats,
            "cache": cache_stats,
            "engines": engine_stats,
            "benchmark_results": len(self._benchmark_results),
            "config": self.config.__dict__
        }
    
    def add_error_handler(self, handler: Callable[[str, Exception], None]) -> None:
        """Add error event handler."""
        self._error_handlers.append(handler)
    
    def add_processing_handler(self, handler: Callable[[str, OCRResult], None]) -> None:
        """Add processing event handler."""
        self._processing_handlers.append(handler)
    
    def clear_cache(self) -> None:
        """Clear OCR result cache."""
        if self._cache:
            self._cache.clear()
            self._logger.info("OCR cache cleared")
    
    def reload_engine(self, engine_name: str) -> bool:
        """
        Reload a specific OCR engine.
        
        Args:
            engine_name: Name of engine to reload
            
        Returns:
            True if reload successful
        """
        # Find plugin that provides this engine
        for plugin_name, plugin_info in self.plugin_manager.registry.get_all_plugins().items():
            if plugin_info.load_status == PluginLoadStatus.LOADED:
                plugin_instance = self.plugin_manager.registry._plugin_instances.get(plugin_name)
                if plugin_instance:
                    engine = plugin_instance.get_engine_instance()
                    if engine and engine.engine_name == engine_name:
                        return self.plugin_manager.reload_plugin(plugin_name)
        
        self._logger.error(f"Could not find plugin for engine {engine_name}")
        return False
    
    def enable_parallel_processing(self, max_workers: Optional[int] = None, use_gpu: bool = True) -> bool:
        """
        Enable parallel OCR processing for multiple text blocks.
        
        Args:
            max_workers: Number of parallel workers (None for auto-detect)
            use_gpu: Whether GPU is being used
        
        Returns:
            True if parallel processing enabled successfully
        """
        try:
            if not self._current_engine:
                self._logger.error("Cannot enable parallel processing: no engine selected")
                return False
            
            # Get current engine instance
            engine = self.plugin_manager.get_engine(self._current_engine)
            if not engine:
                self._logger.error(f"Cannot enable parallel processing: engine {self._current_engine} not available")
                return False
            
            # Create parallel processor
            self._parallel_processor = create_parallel_processor(
                engine,
                max_workers=max_workers,
                use_gpu=use_gpu,
                adaptive=False
            )
            
            self._parallel_enabled = True
            self._logger.info(f"Parallel OCR processing enabled with {self._parallel_processor.max_workers} workers")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to enable parallel processing: {e}")
            return False
    
    def disable_parallel_processing(self) -> None:
        """Disable parallel OCR processing."""
        self._parallel_processor = None
        self._parallel_enabled = False
        self._logger.info("Parallel OCR processing disabled")
    
    def extract_text_from_regions(
        self,
        image,
        text_regions: List[Dict[str, Any]],
        options: Optional[OCRProcessingOptions] = None,
        show_progress: bool = False
    ) -> List[ParallelOCRResult]:
        """
        Extract text from multiple regions in parallel.
        
        This is the main method for parallel OCR processing. It processes
        multiple text regions simultaneously for maximum speed.
        
        Args:
            image: Source image (numpy array)
            text_regions: List of dicts with 'id' and 'bbox' (x, y, w, h)
            options: Optional processing options
            show_progress: Whether to log progress
        
        Returns:
            List of OCRResult objects with text and metadata
        
        Example:
            regions = [
                {'id': 0, 'bbox': (10, 10, 100, 30)},
                {'id': 1, 'bbox': (10, 50, 100, 30)},
            ]
            results = ocr_layer.extract_text_from_regions(image, regions)
        """
        if not self._parallel_enabled or not self._parallel_processor:
            self._logger.warning("Parallel processing not enabled, processing sequentially")
            return self._extract_text_sequential(image, text_regions, options)
        
        # Prepare text blocks for parallel processing
        text_blocks = []
        for region in text_regions:
            text_blocks.append({
                'id': region['id'],
                'bbox': region['bbox'],
                'image': image
            })
        
        # Process in parallel
        try:
            results = self._parallel_processor.process_all_blocks(
                text_blocks,
                show_progress=show_progress
            )
            return results
            
        except Exception as e:
            self._logger.error(f"Parallel processing failed: {e}")
            # Fallback to sequential
            return self._extract_text_sequential(image, text_regions, options)
    
    def _extract_text_sequential(
        self,
        image,
        text_regions: List[Dict[str, Any]],
        options: Optional[OCRProcessingOptions] = None
    ) -> List[ParallelOCRResult]:
        """Fallback sequential processing for text regions."""
        results = []
        
        for region in text_regions:
            try:
                x, y, w, h = region['bbox']
                region_image = image[y:y+h, x:x+w]
                
                # Create frame from region
                # Note: This is a simplified version, adjust based on your Frame class
                from app.models import Frame
                frame = Frame(
                    data=region_image,
                    timestamp=time.time(),
                    width=w,
                    height=h
                )
                
                # Extract text
                text_blocks = self.extract_text(frame, options=options)
                
                # Convert to ParallelOCRResult format
                text = ' '.join([block.text for block in text_blocks])
                confidence = sum([block.confidence for block in text_blocks]) / len(text_blocks) if text_blocks else 0.0
                
                results.append(ParallelOCRResult(
                    block_id=region['id'],
                    bbox=region['bbox'],
                    text=text,
                    confidence=confidence,
                    success=True,
                    processing_time=0.0
                ))
                
            except Exception as e:
                results.append(ParallelOCRResult(
                    block_id=region['id'],
                    bbox=region.get('bbox', (0, 0, 0, 0)),
                    text="",
                    confidence=0.0,
                    success=False,
                    processing_time=0.0,
                    error=str(e)
                ))
        
        return results
    
    def shutdown(self) -> None:
        """Shutdown OCR layer and cleanup resources."""
        self._logger.info("Shutting down OCR layer...")
        
        # Unload all plugins
        for plugin_name in self.plugin_manager.get_loaded_plugins():
            self.plugin_manager.unload_plugin(plugin_name)
        
        # Clear cache
        if self._cache:
            self._cache.clear()
        
        # Clear handlers
        self._error_handlers.clear()
        self._processing_handlers.clear()
        
        self.status = OCRLayerStatus.UNINITIALIZED
        self._current_engine = None
        
        self._logger.info("OCR layer shutdown complete")