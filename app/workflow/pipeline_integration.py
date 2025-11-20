"""
Pipeline Integration Module

This module provides easy integration of the complete pipeline into the UI.
It handles initialization, configuration, and lifecycle management.

Author: Niklas Verhasselt
Date: November 2025
"""

import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path

# Modern pipeline imports
from .runtime_pipeline_optimized import OptimizedRuntimePipeline, OptimizedRuntimePipelineConfig
from .runtime_pipeline import RuntimePipeline, RuntimePipelineConfig
from .pipeline_factory import PipelineFactory
from enum import Enum
from dataclasses import dataclass, field

# Type aliases for compatibility
CompletePipeline = OptimizedRuntimePipeline
PipelineConfig = OptimizedRuntimePipelineConfig
ModularPipelineConfig = OptimizedRuntimePipelineConfig

# Pipeline state enum
class PipelineState(Enum):
    """Pipeline state enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

# Pipeline metrics dataclass
@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    frames_processed: int = 0
    frames_skipped: int = 0
    ocr_calls: int = 0
    translations_completed: int = 0
    avg_frame_time_ms: float = 0.0
    avg_ocr_time_ms: float = 0.0
    avg_translation_time_ms: float = 0.0
    fps: float = 0.0
    errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    stage_times: Dict[str, float] = field(default_factory=dict)

try:
    from app.models import CaptureRegion, Rectangle
    from app.interfaces import (
        ICaptureLayer, IPreprocessingLayer, IOCRLayer,
        ITranslationLayer, IOverlayRenderer
    )
except ImportError:
    from app.models import CaptureRegion, Rectangle
    from app.interfaces import (
        ICaptureLayer, IPreprocessingLayer, IOCRLayer,
        ITranslationLayer, IOverlayRenderer
    )


class PipelineIntegration:
    """
    High-level integration class for the translation pipeline
    
    Provides a simple interface for UI components to interact with the pipeline.
    """
    
    def __init__(self, config_manager=None, use_modular=None):
        """
        Initialize pipeline integration
        
        Args:
            config_manager: Configuration manager instance
            use_modular: Use modular pipeline (True) or classic (False). 
                        If None, reads from config (default: classic for stability)
        """
        self.config_manager = config_manager
        
        # Determine pipeline type from config or parameter
        if use_modular is None and config_manager:
            # Read from config (default to optimized)
            pipeline_type = config_manager.get_setting('pipeline.type', 'optimized')
            self.pipeline_type = pipeline_type
        elif use_modular is None:
            # No config, default to optimized
            self.pipeline_type = 'optimized'
        else:
            # Legacy parameter support: use_modular=True -> optimized, False -> runtime
            self.pipeline_type = 'optimized' if use_modular else 'runtime'
        
        self.pipeline: Optional[CompletePipeline] = None
        self.pipeline_factory = PipelineFactory(config_manager=config_manager)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Pipeline Integration initialized (mode: {self.pipeline_type.upper()})")
        
        # Component instances
        self.capture_layer: Optional[ICaptureLayer] = None
        self.preprocessing_layer: Optional[IPreprocessingLayer] = None
        self.ocr_layer: Optional[IOCRLayer] = None
        self.translation_layer: Optional[ITranslationLayer] = None
        self.overlay_renderer: Optional[IOverlayRenderer] = None
        
        # Callbacks
        self.on_translation_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        self.on_metrics_callback: Optional[Callable] = None
        
        # State
        self.is_initialized = False
        self.capture_region: Optional[CaptureRegion] = None
        
        # Multi-region support
        self.multi_region_enabled = False
        self.multi_region_config: Optional['MultiRegionConfig'] = None
        self.multi_region_manager: Optional['MultiRegionCaptureManager'] = None
    
    def initialize_components(self) -> bool:
        """
        Initialize all pipeline components
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info("Initializing pipeline components...")
            print("[DEBUG] Starting component initialization...")
            
            # Initialize capture layer
            print("[DEBUG] Creating capture layer...")
            self.capture_layer = self._create_capture_layer()
            if not self.capture_layer:
                raise Exception("Failed to create capture layer")
            print("[DEBUG] ✓ Capture layer created")
            
            # Initialize preprocessing layer
            print("[DEBUG] Creating preprocessing layer...")
            self.preprocessing_layer = self._create_preprocessing_layer()
            if not self.preprocessing_layer:
                raise Exception("Failed to create preprocessing layer")
            print("[DEBUG] ✓ Preprocessing layer created")
            
            # Initialize OCR layer
            print("[DEBUG] Creating OCR layer...")
            self.ocr_layer = self._create_ocr_layer()
            if not self.ocr_layer:
                raise Exception("Failed to create OCR layer")
            print("[DEBUG] ✓ OCR layer created")
            
            # Initialize translation layer
            print("[DEBUG] Creating translation layer...")
            self.translation_layer = self._create_translation_layer()
            if not self.translation_layer:
                raise Exception("Failed to create translation layer")
            print("[DEBUG] ✓ Translation layer created")
            
            # Initialize overlay renderer
            print("[DEBUG] Creating overlay renderer...")
            self.overlay_renderer = self._create_overlay_renderer()
            if not self.overlay_renderer:
                raise Exception("Failed to create overlay renderer")
            print("[DEBUG] ✓ Overlay renderer created")
            
            self.is_initialized = True
            print("[DEBUG] All components initialized successfully!")
            self.logger.info("Pipeline components initialized successfully")
            return True
            
        except Exception as e:
            print(f"[DEBUG] ✗ Exception caught: {e}")
            self.logger.error(f"Failed to initialize components: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_capture_layer(self) -> Optional[ICaptureLayer]:
        """Create and configure capture layer"""
        try:
            # Get capture mode from config
            capture_mode = 'auto'
            if self.config_manager:
                capture_mode = self.config_manager.get_setting('capture.mode', 'auto')
            
            # Use NEW plugin-based capture layer with subprocess isolation
            try:
                try:
                    from capture.plugin_capture_layer import PluginCaptureLayer
                except ImportError:
                    from app.capture.plugin_capture_layer import PluginCaptureLayer
                
                self.logger.info(f"Using PluginCaptureLayer (subprocess isolation)")
                
                # Get runtime mode from config
                runtime_mode = 'auto'
                if self.config_manager:
                    runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
                
                # Create plugin-based capture layer
                capture_layer = PluginCaptureLayer(config_manager=self.config_manager)
                
                # Set capture mode based on runtime mode
                if runtime_mode == 'cpu':
                    capture_layer.set_capture_mode('screenshot')
                elif capture_mode == 'directx':
                    capture_layer.set_capture_mode('directx')
                else:
                    capture_layer.set_capture_mode('auto')
                
                # Apply configuration
                if self.config_manager:
                    fps = self.config_manager.get_setting('capture.fps', 30)
                    if hasattr(capture_layer, 'configure_capture_rate'):
                        capture_layer.configure_capture_rate(fps)
                
                return capture_layer
                
            except Exception as e:
                self.logger.error(f"Failed to create PluginCaptureLayer: {e}")
                import traceback
                traceback.print_exc()
                raise
            
        except Exception as e:
            self.logger.error(f"Failed to create capture layer: {e}")
            return None
    
    def _create_preprocessing_layer(self) -> Optional[IPreprocessingLayer]:
        """Create and configure preprocessing layer"""
        try:
            try:
                from preprocessing.preprocessing_layer import PreprocessingLayer
            except ImportError:
                from app.preprocessing.preprocessing_layer import PreprocessingLayer
            
            preprocessing_layer = PreprocessingLayer()
            
            # Configure small text enhancement if enabled in config
            if self.config_manager:
                enhance_small_text = self.config_manager.get_setting('capture.enhance_small_text', False)
                if enhance_small_text:
                    # Get sub-options
                    denoise = self.config_manager.get_setting('capture.enhance_denoise', False)
                    binarize = self.config_manager.get_setting('capture.enhance_binarize', False)
                    
                    preprocessing_layer.set_small_text_enhancement_enabled(True, denoise=denoise, binarize=binarize)
                    
                    options = []
                    if denoise:
                        options.append("denoise")
                    if binarize:
                        options.append("binarize")
                    
                    options_str = f" ({', '.join(options)})" if options else ""
                    self.logger.info(f"✓ Small text enhancement enabled{options_str}")
            
            return preprocessing_layer
            
        except Exception as e:
            self.logger.warning(f"Failed to create preprocessing layer: {e}")
            self.logger.info("Using passthrough preprocessing (no preprocessing)")
            
            # Create a simple passthrough preprocessing layer
            class PassthroughPreprocessing:
                def preprocess(self, frame, profile=None):
                    """Pass frame through without modification"""
                    return frame
                
                def detect_roi(self, frame):
                    """Return None for ROI (process full frame)"""
                    return None
                
                def configure(self, **kwargs):
                    pass
            
            return PassthroughPreprocessing()
    
    def _get_engine_specific_language(self, base_language: str, engine: str) -> str:
        """
        Get engine-specific language code.
        Uses LanguageCodeMapper to convert between formats.
        
        Args:
            base_language: Base language code (any format)
            engine: OCR engine name
            
        Returns:
            Engine-specific language code
        """
        try:
            try:
                from utils.language_mapper import LanguageCodeMapper
            except ImportError:
                from app.utils.language_mapper import LanguageCodeMapper
            return LanguageCodeMapper.normalize(base_language, engine)
        except Exception as e:
            self.logger.warning(f"Failed to use LanguageCodeMapper: {e}, using fallback")
            # Fallback: simple conversion
            tesseract_to_iso = {
                'eng': 'en', 'deu': 'de', 'fra': 'fr', 'spa': 'es',
                'ita': 'it', 'por': 'pt', 'rus': 'ru', 'jpn': 'ja',
                'chi_sim': 'zh', 'chi_tra': 'zh', 'kor': 'ko',
                'ara': 'ar', 'hin': 'hi', 'tha': 'th', 'vie': 'vi',
                'tur': 'tr', 'pol': 'pl', 'nld': 'nl', 'swe': 'sv',
                'ind': 'id'
            }
            
            if engine == 'tesseract':
                # Convert to Tesseract format
                iso_to_tesseract = {v: k for k, v in tesseract_to_iso.items()}
                return iso_to_tesseract.get(base_language, base_language)
            else:
                # Convert to ISO format for other engines
                return tesseract_to_iso.get(base_language, base_language)
    
    def _create_ocr_layer(self) -> Optional[IOCRLayer]:
        """Create and configure OCR layer"""
        try:
            try:
                from ocr.ocr_layer import OCRLayer
            except ImportError:
                from app.ocr.ocr_layer import OCRLayer
            

            
            # Prepare GPU configuration from config manager
            if self.config_manager:
                # Check runtime mode and GPU settings
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
                enable_gpu = self.config_manager.get_setting('performance.enable_gpu_acceleration', True)
                
                # Determine if GPU should be used
                use_gpu = (runtime_mode == 'gpu' or runtime_mode == 'auto') and enable_gpu
                
                # Get engine-specific GPU configs
                easyocr_gpu = self.config_manager.get_setting('ocr.easyocr_config.gpu', use_gpu)
                paddleocr_gpu = self.config_manager.get_setting('ocr.paddleocr_config.use_gpu', use_gpu)
                
                # Get base language code from config
                base_language = self.config_manager.get_setting('ocr.language', 'en')
                
                # Convert language codes for each engine
                easyocr_lang = self._get_engine_specific_language(base_language, 'easyocr')
                paddleocr_lang = self._get_engine_specific_language(base_language, 'paddleocr')
                tesseract_lang = self._get_engine_specific_language(base_language, 'tesseract')
                manga_ocr_lang = self._get_engine_specific_language(base_language, 'manga_ocr')
                
                # Set default config for plugin manager with engine-specific settings
                ocr_layer = OCRLayer(config_manager=self.config_manager)
                ocr_layer.plugin_manager._default_config = {
                    # GPU settings (will be overridden by runtime_mode in plugin manager)
                    'gpu': easyocr_gpu,
                    'use_gpu': paddleocr_gpu,
                    # Language settings (will be overridden per engine)
                    'language': easyocr_lang,  # Default to EasyOCR format
                }
                
                # Store engine-specific language codes in plugin manager
                ocr_layer.plugin_manager._engine_languages = {
                    'easyocr': easyocr_lang,
                    'paddleocr': paddleocr_lang,
                    'tesseract': tesseract_lang,
                    'manga_ocr': manga_ocr_lang,
                    'onnx': easyocr_lang,  # ONNX uses ISO format
                }
            else:
                ocr_layer = OCRLayer(config_manager=self.config_manager)
            
            # Initialize OCR layer with full loading
            self.logger.info("Loading OCR engines (this may take a few seconds)...")
            
            # DO NOT suppress output - we need to see errors!
            # Temporarily disabled suppression for debugging
            success = ocr_layer.initialize(auto_discover=True, auto_load=True)
            
            if not success:
                self.logger.error("Failed to initialize OCR layer")
                return None
            
            # Apply configuration
            if self.config_manager:
                # Set default engine
                default_engine = self.config_manager.get_setting('ocr.default_engine', 'easyocr')
                if default_engine:
                    ocr_layer.set_default_engine(default_engine)
                
                # Set language for current engine
                current_engine = ocr_layer.get_current_engine()
                if current_engine and current_engine in ocr_layer.plugin_manager._engine_languages:
                    engine_lang = ocr_layer.plugin_manager._engine_languages[current_engine]
                    ocr_layer.set_language(engine_lang)
                else:
                    ocr_layer.set_language(easyocr_lang)
            return ocr_layer
            
        except Exception as e:
            self.logger.error(f"Failed to create OCR layer: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_translation_layer(self) -> Optional[ITranslationLayer]:
        """Create and configure translation layer"""
        try:
            try:
                from translation.translation_layer import TranslationLayer
                from translation.engine_registry_init import initialize_translation_engines
            except ImportError:
                from app.translation.translation_layer import TranslationLayer
                from app.translation.engine_registry_init import initialize_translation_engines
            
            translation_layer = TranslationLayer()
            
            # Initialize and register all translation engines
            self.logger.info("Registering translation engines...")
            engine_results = initialize_translation_engines(translation_layer, self.config_manager)
            
            # Log results
            successful_engines = [name for name, success in engine_results.items() if success]
            if successful_engines:
                self.logger.info(f"Translation engines ready: {', '.join(successful_engines)}")
            else:
                self.logger.warning("No translation engines were successfully initialized")
            
            return translation_layer
            
        except Exception as e:
            self.logger.warning(f"Failed to create translation layer: {e}")
            self.logger.info("Using stub translation (returns original text)")
            
            # Create a simple stub translation layer
            class StubTranslation:
                def translate(self, text_blocks):
                    """Return text blocks as-is without translation"""
                    try:
                        from models import Translation
                    except ImportError:
                        from app.models import Translation
                    if isinstance(text_blocks, list):
                        return [Translation(
                            original_text=tb.text if hasattr(tb, 'text') else str(tb),
                            translated_text=tb.text if hasattr(tb, 'text') else str(tb),
                            source_language="en",
                            target_language="en",
                            confidence=1.0
                        ) for tb in text_blocks]
                    else:
                        text = text_blocks.text if hasattr(text_blocks, 'text') else str(text_blocks)
                        return Translation(
                            original_text=text,
                            translated_text=text,
                            source_language="en",
                            target_language="en",
                            confidence=1.0
                        )
                
                def configure(self, **kwargs):
                    pass
                
                def set_languages(self, source, target):
                    pass
            
            return StubTranslation()
    
    def _create_overlay_renderer(self) -> Optional[IOverlayRenderer]:
        """Create and configure overlay renderer"""
        try:
            try:
                from overlay.overlay_renderer import OverlayRenderer
            except ImportError:
                from app.overlay.overlay_renderer import OverlayRenderer
            
            overlay_renderer = OverlayRenderer(config_manager=self.config_manager)
            
            # Apply configuration
            if self.config_manager:
                style = {
                    'font_family': self.config_manager.get_setting('overlay.font_family', 'Arial'),
                    'font_size': self.config_manager.get_setting('overlay.font_size', 14),
                    'opacity': self.config_manager.get_setting('overlay.background_opacity', 0.7),
                    'fg_color': self.config_manager.get_setting('overlay.font_color', '#ffffff'),
                    'bg_color': self.config_manager.get_setting('overlay.background_color', '#000000')
                }
                overlay_renderer.set_overlay_style(style)
            
            return overlay_renderer
            
        except Exception as e:
            self.logger.warning(f"Failed to create overlay renderer: {e}")
            self.logger.info("Using stub overlay (prints to console)")
            
            # Create a simple stub overlay renderer
            class StubOverlay:
                def render(self, translations, frame=None):
                    """Print translations to console"""
                    if isinstance(translations, list):
                        for t in translations:
                            if hasattr(t, 'translated_text'):
                                print(f"[OVERLAY] {t.translated_text}")
                    elif hasattr(translations, 'translated_text'):
                        print(f"[OVERLAY] {translations.translated_text}")
                
                def set_overlay_style(self, style):
                    pass
                
                def clear(self):
                    pass
                
                def show(self):
                    pass
                
                def hide(self):
                    pass
            
            return StubOverlay()
    
    def create_pipeline(self) -> bool:
        """
        Create the translation pipeline (classic or modular based on config)
        
        Returns:
            bool: True if pipeline created successfully
        """
        if not self.is_initialized:
            self.logger.error("Components not initialized. Call initialize_components() first.")
            return False
        
        try:
            # Create configuration
            config = self._create_pipeline_config()
            
            # Create pipeline using factory
            self.pipeline = self.pipeline_factory.create_pipeline(
                pipeline_type=self.pipeline_type,
                capture_layer=self.capture_layer,
                preprocessing_layer=self.preprocessing_layer,
                ocr_layer=self.ocr_layer,
                translation_layer=self.translation_layer,
                overlay_renderer=self.overlay_renderer,
                config=config
            )
            
            # Set callbacks
            if self.on_translation_callback:
                self.pipeline.on_translation_callback = self.on_translation_callback
            if self.on_error_callback:
                self.pipeline.on_error_callback = self.on_error_callback
            if self.on_metrics_callback:
                self.pipeline.on_metrics_callback = self.on_metrics_callback
            
            self.logger.info(f"Pipeline created successfully ({self.pipeline_type.upper()} mode)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_pipeline_config(self) -> OptimizedRuntimePipelineConfig:
        """Create pipeline configuration from config manager"""
        config = OptimizedRuntimePipelineConfig()
        
        if self.config_manager:
            # Capture settings
            config.capture_fps = self.config_manager.get_setting('capture.fps', 30)
            config.capture_region = self.capture_region
            
            # OCR settings
            config.ocr_confidence_threshold = self.config_manager.get_setting(
                'ocr.confidence_threshold', 0.7
            )
            config.ocr_language = self.config_manager.get_setting('ocr.language', 'en')
            
            # Translation settings
            config.source_language = self.config_manager.get_setting(
                'translation.source_language', 'en'
            )
            config.target_language = self.config_manager.get_setting(
                'translation.target_language', 'de'
            )
            config.translation_confidence_threshold = self.config_manager.get_setting(
                'translation.confidence_threshold', 0.75
            )
            config.enable_dictionary = self.config_manager.get_setting(
                'translation.enable_dictionary', True
            )
            config.enable_caching = self.config_manager.get_setting(
                'translation.enable_caching', True
            )
            
            # Overlay settings
            config.enable_overlay = self.config_manager.get_setting('overlay.enabled', True)
            config.auto_size_text = self.config_manager.get_setting(
                'overlay.auto_size_text', True
            )
            config.auto_position_overlay = self.config_manager.get_setting(
                'overlay.auto_position', True
            )
            
            # Performance settings
            config.enable_multithreading = self.config_manager.get_setting(
                'performance.enable_multithreading', True
            )
            config.max_worker_threads = self.config_manager.get_setting(
                'performance.max_worker_threads', 4
            )
            config.enable_frame_skip = self.config_manager.get_setting(
                'performance.enable_frame_skip', True
            )
            
            # Optimization settings
            config.enable_roi_detection = self.config_manager.get_setting(
                'performance.enable_roi_detection', True
            )
            config.enable_parallel_ocr = self.config_manager.get_setting(
                'performance.enable_parallel_ocr', True
            )
            config.batch_translation = self.config_manager.get_setting(
                'performance.batch_translation', True
            )
            
            # Experimental features
            config.experimental_features = self.config_manager.get_setting(
                'advanced.experimental_features', []
            )
        
        return config
    

    
    def set_capture_region(self, x: int, y: int, width: int, height: int, monitor_id: int = 0):
        """
        Set the capture region (single region mode)
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Width of region
            height: Height of region
            monitor_id: Monitor ID (default: 0)
        """
        rectangle = Rectangle(x=x, y=y, width=width, height=height)
        self.capture_region = CaptureRegion(rectangle=rectangle, monitor_id=monitor_id)
        
        # Disable multi-region mode
        self.multi_region_enabled = False
        
        if self.pipeline:
            self.pipeline.set_capture_region(self.capture_region)
        
        self.logger.info(f"Capture region set: {width}x{height} at ({x}, {y})")
    
    def set_multi_region_config(self, config: 'MultiRegionConfig'):
        """
        Set multi-region configuration
        
        Args:
            config: MultiRegionConfig instance
        """
        from app.models import MultiRegionConfig
        from app.capture.multi_region_manager import create_multi_region_manager
        
        self.multi_region_config = config
        self.multi_region_enabled = True
        
        # Set the first enabled region as the primary capture region for the pipeline
        # This is needed because CompletePipeline.start() checks for capture_region
        enabled_regions = config.get_enabled_regions()
        if enabled_regions:
            first_region = enabled_regions[0]
            self.capture_region = CaptureRegion(
                rectangle=first_region.rectangle,
                monitor_id=first_region.monitor_id
            )
            
            # Also set it directly on the pipeline's config (bypass set_capture_region to preserve multi-region mode)
            if self.pipeline and hasattr(self.pipeline, 'config'):
                self.pipeline.config.capture_region = self.capture_region
            
            self.logger.info(f"Set primary capture region from multi-region config: "
                           f"{first_region.rectangle.width}x{first_region.rectangle.height} "
                           f"at ({first_region.rectangle.x}, {first_region.rectangle.y})")
        
        # Create multi-region manager if capture layer exists
        if self.capture_layer:
            self.logger.info(f"Creating multi-region manager with capture layer: {type(self.capture_layer).__name__}")
            self.multi_region_manager = create_multi_region_manager(
                self.capture_layer,
                config
            )
            
            # Set up callbacks
            if self.multi_region_manager:
                self.multi_region_manager.on_frame_captured = self._on_multi_region_frame
                self.multi_region_manager.on_capture_error = self._on_multi_region_error
                self.logger.info(f"Multi-region manager created and callbacks set")
            else:
                self.logger.error("Failed to create multi-region manager!")
        else:
            self.logger.error("Cannot create multi-region manager: capture_layer is None!")
        
        enabled_count = len(config.get_enabled_regions())
        self.logger.info(f"Multi-region mode enabled: {enabled_count} active regions")
    
    def _on_multi_region_frame(self, region_id: str, frame):
        """
        Handle frame captured from multi-region manager.
        
        This processes frames through the complete pipeline:
        1. Preprocessing
        2. OCR
        3. Text validation
        4. Translation
        5. Overlay display
        
        Args:
            region_id: ID of the region this frame came from
            frame: Captured frame to process
        """
        if not self.pipeline:
            self.logger.warning("_on_multi_region_frame called but pipeline is None!")
            return
        
        try:
            # Log that we received a frame (important for debugging)
            if not hasattr(self, '_frame_count'):
                self._frame_count = 0
            self._frame_count += 1
            
            if self._frame_count % 30 == 1:  # Log every 30 frames
                self.logger.info(f"[MULTI-REGION] Processing frame #{self._frame_count} from region {region_id}")
            
            # Get the region configuration for coordinate conversion
            region_config = None
            if self.multi_region_config:
                for region in self.multi_region_config.regions:
                    if region.region_id == region_id:
                        region_config = region
                        break
            
            if not region_config:
                self.logger.warning(f"No configuration found for region {region_id}")
                return
            
            self.logger.debug(f"Processing frame from region {region_id}: {frame.data.shape if hasattr(frame, 'data') else 'no data'}")
            
            # Step 1: Preprocess frame
            processed_frame = self.pipeline._preprocess_frame(frame)
            
            # Step 2: OCR - Extract text
            text_blocks = self.pipeline._process_ocr(processed_frame)
            
            if not text_blocks:
                self.logger.debug(f"No text detected in region {region_id}")
                return
            
            self.logger.debug(f"Detected {len(text_blocks)} text blocks in region {region_id}")
            
            # Step 3: Validate text blocks
            validated_blocks = self.pipeline._validate_text_blocks(text_blocks)
            
            if not validated_blocks:
                self.logger.debug(f"No valid text blocks in region {region_id}")
                return
            
            self.logger.debug(f"Validated {len(validated_blocks)} text blocks in region {region_id}")
            
            # Step 4: Translate text blocks
            translations = self.pipeline._translate_text_blocks(validated_blocks)
            
            if not translations:
                self.logger.debug(f"No translations produced for region {region_id}")
                return
            
            self.logger.info(f"Produced {len(translations)} translations for region {region_id}")
            
            # Step 5: Adjust translation coordinates for region offset
            # Translations have coordinates relative to the captured frame
            # We need to add the region's offset to get screen coordinates
            for translation in translations:
                if hasattr(translation, 'position') and translation.position:
                    # Add region offset to translation position
                    translation.position.x += region_config.rectangle.x
                    translation.position.y += region_config.rectangle.y
                    
                    # Store region info for overlay display
                    if not hasattr(translation, 'region_id'):
                        translation.region_id = region_id
                    if not hasattr(translation, 'monitor_id'):
                        translation.monitor_id = region_config.monitor_id
            
            # Step 6: Notify callback with translations
            if self.on_translation_callback:
                try:
                    self.on_translation_callback(translations)
                except Exception as e:
                    self.logger.error(f"Error in translation callback: {e}")
            
            # Update metrics
            if hasattr(self.pipeline, 'metrics'):
                self.pipeline.metrics.frames_processed += 1
                self.pipeline.metrics.translations_completed += len(translations)
            
        except Exception as e:
            self.logger.error(f"Error processing multi-region frame from {region_id}: {e}")
            import traceback
            traceback.print_exc()
            
            if self.on_error_callback:
                try:
                    self.on_error_callback(f"Region {region_id}: {str(e)}")
                except:
                    pass
    
    def _on_multi_region_error(self, region_id: str, error: str):
        """Handle capture error from multi-region manager."""
        self.logger.error(f"Capture error for region {region_id}: {error}")
        if self.on_error_callback:
            self.on_error_callback(f"Region {region_id}: {error}")
    
    def start_translation(self) -> bool:
        """
        Start the translation pipeline
        
        Returns:
            bool: True if started successfully
        """
        if not self.pipeline:
            if not self.create_pipeline():
                return False
        
        # Check if we have regions configured
        if self.multi_region_enabled:
            if not self.multi_region_config or not self.multi_region_config.get_enabled_regions():
                self.logger.error("Cannot start: No enabled regions in multi-region mode")
                return False
            
            # Start multi-region capture
            if self.multi_region_manager:
                self.logger.info(f"Starting multi-region manager (manager exists: {self.multi_region_manager is not None})")
                if not self.multi_region_manager.start():
                    self.logger.error("Failed to start multi-region capture")
                    return False
                self.logger.info("Multi-region capture started successfully!")
            else:
                self.logger.error("Cannot start multi-region capture: manager is None!")
                
                # In multi-region mode, DON'T start the pipeline's capture loop
                # The multi-region manager handles capture and calls _on_multi_region_frame()
                # Just mark the pipeline as running
                if hasattr(self.pipeline, 'state'):
                    from .complete_pipeline import PipelineState
                    self.pipeline.state = PipelineState.RUNNING
                    self.pipeline.is_running = True
                
                self.logger.info("Multi-region mode: Pipeline ready (capture handled by multi-region manager)")
                return True
        else:
            if not self.capture_region:
                self.logger.error("Cannot start: No capture region defined")
                return False
            
            # Single-region mode: Start the pipeline's own capture loop
            return self.pipeline.start()
    
    def stop_translation(self):
        """Stop the translation pipeline"""
        # Stop multi-region capture if enabled
        if self.multi_region_enabled and self.multi_region_manager:
            self.multi_region_manager.stop()
            self.logger.info("Multi-region capture stopped")
        
        if self.pipeline:
            self.pipeline.stop()
    
    def pause_translation(self):
        """Pause the translation pipeline"""
        if self.pipeline:
            self.pipeline.pause()
    
    def resume_translation(self):
        """Resume the translation pipeline"""
        if self.pipeline:
            self.pipeline.resume()
    
    def get_state(self) -> Optional[PipelineState]:
        """Get current pipeline state"""
        if self.pipeline:
            return self.pipeline.get_state()
        return None
    
    def get_metrics(self) -> Optional[PipelineMetrics]:
        """Get current pipeline metrics"""
        if self.pipeline:
            return self.pipeline.get_metrics()
        return None
    
    def is_running(self) -> bool:
        """Check if pipeline is running"""
        if self.pipeline:
            state = self.pipeline.get_state()
            return state == PipelineState.RUNNING
        return False
    
    def set_ocr_engine(self, engine_name: str) -> bool:
        """
        Change the OCR engine without restarting the pipeline.
        
        This allows hot-swapping between different OCR engines (EasyOCR, Tesseract,
        PaddleOCR, ONNX) without stopping the translation pipeline.
        
        Args:
            engine_name: Name of OCR engine ('easyocr', 'tesseract', 'paddleocr', 'onnx')
            
        Returns:
            True if engine changed successfully, False otherwise
        """
        if not self.ocr_layer:
            self.logger.error("OCR layer not initialized")
            return False
        
        # Get available engines
        available = self.ocr_layer.get_available_engines()
        if engine_name not in available:
            self.logger.error(f"OCR engine '{engine_name}' not available. Available: {available}")
            return False
        
        # Check if pipeline is running
        was_running = self.is_running()
        if was_running:
            self.logger.info(f"Pausing pipeline to change OCR engine to: {engine_name}")
            self.pause_translation()
        
        try:
            # Change engine
            success = self.ocr_layer.set_default_engine(engine_name)
            
            if success:
                self.logger.info(f"OCR engine changed to: {engine_name}")
                
                # Re-apply language setting with new engine (handles code conversion)
                if self.config_manager:
                    language = self.config_manager.get_setting('ocr.language', 'en')
                    self.ocr_layer.set_language(language)
                    self.logger.info(f"Re-applied language setting: {language}")
                
                # Update config
                if self.config_manager:
                    self.config_manager.set_setting('ocr.default_engine', engine_name)
                    self.config_manager.save_config()
                    self.logger.info(f"Saved OCR engine to config: {engine_name}")
                
                # Resume if was running
                if was_running:
                    self.logger.info("Resuming pipeline after engine change")
                    self.resume_translation()
                
                return True
            else:
                self.logger.error(f"Failed to change OCR engine to: {engine_name}")
                
                # Resume if was running
                if was_running:
                    self.resume_translation()
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error changing OCR engine: {e}")
            
            # Resume if was running
            if was_running:
                self.resume_translation()
            
            return False
    
    def get_available_ocr_engines(self) -> list:
        """
        Get list of available OCR engines.
        
        Returns:
            List of available OCR engine names
        """
        if self.ocr_layer:
            return self.ocr_layer.get_available_engines()
        return []
    
    def get_current_ocr_engine(self) -> Optional[str]:
        """
        Get currently active OCR engine.
        
        Returns:
            Name of current OCR engine, or None if not initialized
        """
        if self.ocr_layer:
            return self.ocr_layer.get_current_engine()
        return None
    
    def get_ocr_engine_info(self, engine_name: str) -> Optional[Dict]:
        """
        Get information about a specific OCR engine.
        
        Args:
            engine_name: Name of the OCR engine
            
        Returns:
            Dictionary with engine information, or None if not available
        """
        if self.ocr_layer:
            return self.ocr_layer.get_engine_info(engine_name)
        return None
    
    def get_current_language_pair(self) -> tuple:
        """
        Get current source and target language pair.
        
        Returns:
            Tuple of (source_lang, target_lang)
        """
        if self.config_manager:
            source = self.config_manager.get_setting('translation.source_language', 'en')
            target = self.config_manager.get_setting('translation.target_language', 'de')
            return (source, target)
        return ('en', 'de')
    
    def get_available_language_pairs(self) -> list:
        """
        Get list of all available language-pair dictionaries.
        
        Returns:
            List of tuples: (source_lang, target_lang, dict_path, entry_count)
        """
        try:
            from app.translation.smart_dictionary import SmartDictionary
            from pathlib import Path
            from app.utils.path_utils import get_app_path
            
            # Check both dev/dictionary (legacy) and dictionary folders
            dict_folders = [
                Path("dev/dictionary"),  # Legacy location
                get_app_path("dictionary")  # Current location
            ]
            
            pairs = []
            seen_pairs = set()  # Track unique language pairs
            
            for dict_folder in dict_folders:
                if not dict_folder.exists():
                    continue
                
                # Find all dictionary files
                for dict_file in dict_folder.glob("learned_dictionary_*_*.json.gz"):
                    try:
                        # Parse filename: learned_dictionary_en_de.json.gz
                        filename = dict_file.stem  # Remove .gz
                        if filename.endswith('.json'):
                            filename = filename[:-5]  # Remove .json
                        
                        name_parts = filename.split('_')
                        if len(name_parts) >= 4:  # learned_dictionary_XX_YY
                            source_lang = name_parts[2]
                            target_lang = name_parts[3]
                            
                            # Skip if we've already seen this pair
                            pair_key = (source_lang, target_lang)
                            if pair_key in seen_pairs:
                                continue
                            seen_pairs.add(pair_key)
                            
                            # Load dictionary to get entry count
                            smart_dict = SmartDictionary(dictionary_path=str(dict_file))
                            stats = smart_dict.get_stats(source_lang, target_lang)
                            entry_count = stats.total_entries
                            
                            pairs.append((source_lang, target_lang, str(dict_file), entry_count))
                    except Exception as e:
                        self.logger.warning(f"Failed to parse dictionary file {dict_file}: {e}")
            
            return pairs
        except Exception as e:
            self.logger.error(f"Failed to get available language pairs: {e}")
            return []
    
    def cleanup(self):
        """Cleanup pipeline resources"""
        if self.pipeline:
            self.pipeline.stop()
            self.pipeline = None
        
        self.is_initialized = False
        self.logger.info("Pipeline integration cleaned up")


def create_pipeline_integration(config_manager=None) -> PipelineIntegration:
    """
    Factory function to create a pipeline integration instance
    
    Args:
        config_manager: Configuration manager instance
    
    Returns:
        PipelineIntegration: Configured pipeline integration instance
    """
    integration = PipelineIntegration(config_manager=config_manager)
    
    # Initialize components
    if not integration.initialize_components():
        logging.error("Failed to initialize pipeline components")
        return None
    
    return integration
