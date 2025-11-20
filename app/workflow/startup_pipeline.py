"""
Startup Pipeline

Handles initialization of all components when the app starts.
Loads OCR engines, translation engines, and overlay system.

This is the "Initialization Pipeline" that runs once at startup.
"""

import logging
from typing import Optional, Callable
from pathlib import Path

from .runtime_pipeline import RuntimePipeline, RuntimePipelineConfig, create_runtime_pipeline
from .runtime_pipeline_optimized import OptimizedRuntimePipeline, OptimizedRuntimePipelineConfig, create_optimized_runtime_pipeline

try:
    from app.models import CaptureRegion, Rectangle
except ImportError:
    from models import CaptureRegion, Rectangle


class StartupPipeline:
    """
    Startup Pipeline - Initializes all components at app startup.
    
    Responsibilities:
    - Load OCR engines (EasyOCR, Tesseract, etc.)
    - Load translation engines (MarianMT)
    - Initialize overlay system (PyQt6)
    - Create runtime pipeline for translation
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize minimal pipeline integration.
        
        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Enable debug mode if configured
        self.debug_mode = False
        if config_manager:
            self.debug_mode = config_manager.get_setting('advanced.debug_mode', False)
            if self.debug_mode:
                self.logger.setLevel(logging.DEBUG)
                print("[DEBUG MODE] ✓ Enabled - Verbose logging active")
                print("[DEBUG MODE] All component operations will be logged in detail")
        
        # Components
        self.capture_layer = None
        self.ocr_layer = None
        self.translation_layer = None
        
        # Runtime Pipeline (for translation loop)
        self.pipeline: Optional[RuntimePipeline] = None
        self.capture_region: Optional[CaptureRegion] = None
        
        # Overlay system
        self.overlay_system = None
        self._init_overlay_system()
        
        # Callbacks
        self.on_translation_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        self.logger.info("Startup pipeline initialized")
    
    def _init_overlay_system(self):
        """Initialize the overlay system."""
        try:
            # CRITICAL: Use thread-safe overlay system since pipeline runs in background thread
            from ui.overlay_factory import create_thread_safe_overlay_system
            self.overlay_system = create_thread_safe_overlay_system(self.config_manager)
            self.logger.info("Thread-safe overlay system initialized")
            print("[MINIMAL] Thread-safe overlay system initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize overlay system: {e}")
            print(f"[MINIMAL] WARNING: Overlay system failed to initialize: {e}")
    
    def initialize_components(self) -> bool:
        """Initialize pipeline components."""
        try:
            self.logger.info("Initializing components...")
            
            # Create capture layer
            print("      → Creating capture layer...")
            self.capture_layer = self._create_capture_layer()
            if not self.capture_layer:
                print("      ✗ Capture layer creation failed")
                raise Exception("Failed to create capture layer")
            print("      ✓ Capture layer created")
            
            # Create OCR layer
            print("      → Creating OCR layer...")
            self.ocr_layer = self._create_ocr_layer()
            if not self.ocr_layer:
                print("      ✗ OCR layer creation failed")
                raise Exception("Failed to create OCR layer")
            print("      ✓ OCR layer created")
            
            # Create translation layer
            print("      → Creating translation layer...")
            self.translation_layer = self._create_translation_layer()
            if not self.translation_layer:
                print("      ✗ Translation layer creation failed")
                raise Exception("Failed to create translation layer")
            print("      ✓ Translation layer created")
            
            self.logger.info("Components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False
    
    def _create_capture_layer(self):
        """Create capture layer using configured settings."""
        try:
            # Read capture settings from config
            capture_mode = 'auto'
            capture_fps = self.config_manager.get_setting('capture.fps', 30) if self.config_manager else 30
            capture_quality = 'high'
            adaptive_enabled = True
            fallback_enabled = True
            
            if self.config_manager:
                capture_mode = self.config_manager.get_setting('capture.mode', 'auto')
                capture_fps = self.config_manager.get_setting('capture.fps', 30)
                capture_quality = self.config_manager.get_setting('capture.quality', 'high')
                adaptive_enabled = self.config_manager.get_setting('capture.adaptive', True)
                fallback_enabled = self.config_manager.get_setting('capture.fallback_enabled', True)
                
                print(f"[STARTUP] Capture settings loaded from config:")
                print(f"  Mode: {capture_mode}")
                print(f"  FPS: {capture_fps}")
                print(f"  Quality: {capture_quality}")
                print(f"  Adaptive: {adaptive_enabled}")
                print(f"  Fallback: {fallback_enabled}")
                
                if self.debug_mode:
                    print(f"[DEBUG] Capture layer will use {capture_mode} mode at {capture_fps} FPS")
            
            # Use plugin-based capture layer to support different capture modes
            from app.capture.plugin_capture_layer import PluginCaptureLayer
            
            print(f"[STARTUP] Creating plugin-based capture layer (mode: {capture_mode})")
            
            # Create capture layer with config manager
            capture = PluginCaptureLayer(config_manager=self.config_manager)
            
            # Set capture mode (directx/screenshot/auto)
            if not capture.set_capture_mode(capture_mode):
                print(f"[STARTUP] ⚠ Failed to set capture mode '{capture_mode}', using fallback")
                # Try fallback modes
                if capture_mode == 'directx' and fallback_enabled:
                    print("[STARTUP] Falling back to screenshot mode")
                    capture.set_capture_mode('screenshot')
                elif capture_mode == 'auto':
                    # Auto mode already handles fallback internally
                    pass
            
            # Configure FPS
            if not capture.configure_capture_rate(capture_fps):
                print(f"[STARTUP] ⚠ Failed to set FPS to {capture_fps}, using default")
            
            # Store quality setting for later use (quality affects image preprocessing)
            capture._quality = capture_quality
            
            self.logger.info(f"Capture layer created: mode={capture_mode}, fps={capture_fps}, quality={capture_quality}")
            return capture
            
        except Exception as e:
            self.logger.error(f"Failed to create capture layer: {e}")
            print(f"[STARTUP] ✗ Capture layer creation failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to simple capture layer if plugin system fails
            try:
                print("[STARTUP] Falling back to simple capture layer")
                from app.capture.simple_capture_layer import SimpleCaptureLayer
                capture = SimpleCaptureLayer()
                self.logger.info("Fallback to simple capture layer successful")
                return capture
            except Exception as fallback_error:
                self.logger.error(f"Fallback capture layer also failed: {fallback_error}")
                return None
    
    def _create_ocr_layer(self):
        """Create OCR layer with plugin system and load only the selected engine."""
        try:
            # Get configured OCR engine (defaults to easyocr for first-time users)
            ocr_engine = 'easyocr'
            if self.config_manager:
                ocr_engine = self.config_manager.get_setting('ocr.engine', 'easyocr')
            
            print(f"[STARTUP] OCR engine configured: {ocr_engine}")
            
            # Create OCR layer with plugin system
            from app.ocr.ocr_layer import OCRLayer, OCRLayerConfig
            
            config = OCRLayerConfig(
                default_engine=ocr_engine,
                auto_fallback_enabled=True,
                cache_enabled=True,
                parallel_processing=False
            )
            
            # Create OCR layer with config manager for runtime mode
            ocr_layer = OCRLayer(config=config, config_manager=self.config_manager)
            
            # Discover plugins (fast - just scans directories)
            print(f"[STARTUP] Discovering OCR plugins...")
            discovered = ocr_layer.plugin_manager.discover_plugins()
            
            if not discovered:
                print(f"[STARTUP] ⚠ No OCR plugins found!")
                print(f"[STARTUP] User needs to install an OCR engine")
                self.logger.error("No OCR plugins discovered - installation required")
                # Return None to trigger installation dialog in the UI
                return None
            
            # Get plugin names from discovered list
            discovered_names = [plugin.name for plugin in discovered]
            print(f"[STARTUP] Found {len(discovered)} OCR plugin(s): {', '.join(discovered_names)}")
            
            # Verify the selected engine exists
            if ocr_engine not in discovered_names:
                print(f"[STARTUP] ⚠ Selected engine '{ocr_engine}' not found!")
                print(f"[STARTUP] Available engines: {', '.join(discovered_names)}")
                # Fallback to first available engine
                ocr_engine = discovered_names[0]
                print(f"[STARTUP] Falling back to: {ocr_engine}")
                # Save the fallback engine to config
                if self.config_manager:
                    self.config_manager.set_setting('ocr.engine', ocr_engine)
                    self.config_manager.save_config()
            
            # Load ONLY the selected engine (not all engines)
            print(f"[STARTUP] Loading {ocr_engine} engine...")
            print(f"[STARTUP] (Other engines will load on-demand when you switch to them)")
            
            # Get GPU setting from config - DEFAULT TO TRUE for better performance
            use_gpu = True  # Default to GPU enabled
            
            if self.config_manager:
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'gpu')
                enable_gpu = self.config_manager.get_setting('performance.enable_gpu_acceleration', True)
                # Also check OCR-specific GPU setting
                ocr_gpu = self.config_manager.get_setting('ocr.easyocr_config.gpu', True)
                
                # Use GPU if any of these conditions are true (or if explicitly disabled)
                use_gpu = (runtime_mode == 'gpu' or enable_gpu or ocr_gpu == True)
                
                print(f"[STARTUP] GPU mode: {use_gpu} (runtime_mode={runtime_mode}, enable_gpu={enable_gpu}, ocr_gpu={ocr_gpu})")
            else:
                print(f"[STARTUP] GPU mode: {use_gpu} (no config_manager, using default)")
            
            # Prepare OCR config with GPU setting
            ocr_config = {
                'gpu': use_gpu,
                'language': 'en'  # Default language
            }
            
            print(f"[STARTUP] Calling plugin_manager.load_plugin('{ocr_engine}', config={ocr_config})...")
            
            try:
                success = ocr_layer.plugin_manager.load_plugin(ocr_engine, config=ocr_config)
                print(f"[STARTUP] load_plugin returned: {success}")
            except Exception as e:
                print(f"[STARTUP] ❌ Exception during plugin loading: {e}")
                self.logger.error(f"Exception loading {ocr_engine}: {e}")
                import traceback
                traceback.print_exc()
                success = False
            
            if success:
                # Set as default engine
                ocr_layer.set_default_engine(ocr_engine)
                print(f"[STARTUP] ✓ {ocr_engine} engine loaded and set as default")
                self.logger.info(f"OCR layer initialized with engine: {ocr_engine}")
            else:
                print(f"[STARTUP] ⚠ Failed to load {ocr_engine} engine")
                self.logger.warning(f"Failed to load {ocr_engine} engine")
                # Try to load any available engine as fallback
                for fallback_engine in discovered_names:
                    if fallback_engine != ocr_engine:
                        print(f"[STARTUP] Trying fallback engine: {fallback_engine}")
                        if ocr_layer.plugin_manager.load_plugin(fallback_engine, config=ocr_config):
                            ocr_layer.set_default_engine(fallback_engine)
                            print(f"[STARTUP] ✓ Fallback to {fallback_engine} successful and set as default")
                            ocr_engine = fallback_engine
                            success = True
                            break
            
            if not success:
                print(f"[STARTUP] ✗ Failed to load any OCR engine")
                self.logger.error("Failed to load any OCR engine")
                return None
            
            # Set status to ready (import the enum properly)
            from app.ocr.ocr_layer import OCRLayerStatus
            ocr_layer.status = OCRLayerStatus.READY
            
            return ocr_layer
            
        except Exception as e:
            self.logger.error(f"Failed to create OCR layer: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_translation_layer(self):
        """Create translation layer with plugin support."""
        try:
            # Check if multi-engine mode is enabled
            multi_engine_enabled = False
            if self.config_manager:
                multi_engine_enabled = self.config_manager.get_setting('translation.multi_engine_enabled', False)
            
            if multi_engine_enabled:
                # Use multi-engine translation layer
                print("[STARTUP] Multi-engine translation layer enabled")
                from app.translation.multi_engine_layer import create_multi_engine_translation_layer
                translation = create_multi_engine_translation_layer(self.config_manager)
                self.logger.info("Multi-engine translation layer created")
            else:
                # Use standard translation layer with plugin support
                print("[STARTUP] Standard translation layer (plugin-based)")
                from app.translation.translation_layer import TranslationLayer
                translation = TranslationLayer(config_manager=self.config_manager)
                self.logger.info("Standard translation layer created with plugin support")
            
            # Get runtime mode and GPU settings
            runtime_mode = 'auto'
            enable_gpu = True
            if self.config_manager:
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
                enable_gpu = self.config_manager.get_setting('performance.enable_gpu', True)
            
            # Load MarianMT engine directly (no subprocess, no plugin complexity)
            # Model will be loaded lazily on first translation (not at startup to avoid UI freeze)
            try:
                print("[STARTUP] Registering MarianMT translation engine...")
                from app.translation.engines.marianmt_engine import MarianMTEngine
                
                # Create and initialize MarianMT engine
                marianmt_engine = MarianMTEngine()
                
                if marianmt_engine.is_available():
                    # Register with translation layer
                    translation.register_engine(marianmt_engine, is_default=True, is_fallback=False)
                    print(f"[STARTUP] ✓ MarianMT engine registered (model will load on first translation)")
                    self.logger.info("MarianMT engine registered for lazy loading")
                else:
                    print(f"[STARTUP] ⚠ MarianMT not available (transformers library missing?)")
                    self.logger.warning("MarianMT engine not available")
                
            except Exception as engine_error:
                print(f"[STARTUP] MarianMT engine registration failed: {engine_error}")
                print("[STARTUP] Translation will use fallback/dummy mode")
                self.logger.error(f"MarianMT engine registration failed: {engine_error}")
                import traceback
                traceback.print_exc()
            
            # Dictionary functionality is now integrated into the translation layer
            # via smart_dictionary.py - no separate engine registration needed
            print("[STARTUP] Dictionary functionality available via translation layer")
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Failed to create translation layer: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_pipeline(self) -> bool:
        """Create the runtime pipeline for translation."""
        try:
            if not all([self.capture_layer, self.ocr_layer, self.translation_layer]):
                self.logger.error("Components not initialized")
                return False
            
            # Get languages and capture settings from config
            source_lang = "en"  # Default source
            target_lang = "de"  # Default target
            capture_fps = 30  # Default FPS (will be overridden by config below)
            
            if self.config_manager:
                source_lang = self.config_manager.get_setting('translation.source_language', 'en')
                target_lang = self.config_manager.get_setting('translation.target_language', 'de')
                capture_fps = self.config_manager.get_setting('capture.fps', 30)
            
            print(f"[STARTUP] Translation: {source_lang} -> {target_lang}")
            print(f"[STARTUP] Capture FPS: {capture_fps}")
            
            # IMPORTANT: Plugin system is ALWAYS enabled (essential plugins must load)
            # The enable_optimizer_plugins setting only controls OPTIONAL plugins
            enable_plugins = True  # Always enable plugin system
            if self.config_manager:
                # This setting controls whether to load ALL plugins or just ESSENTIAL ones
                enable_all_plugins = self.config_manager.get_setting('pipeline.enable_optimizer_plugins', False)
                print(f"[STARTUP] Optimizer plugins: {'all enabled' if enable_all_plugins else 'essential only'}")
            else:
                enable_all_plugins = False  # Default: essential only
            
            # Create optimized config with plugin support
            config = OptimizedRuntimePipelineConfig(
                capture_region=self.capture_region,
                fps=capture_fps,  # Use FPS from config
                source_language=source_lang,
                target_language=target_lang,
                enable_plugins=enable_plugins,  # Always True
                load_all_plugins=enable_all_plugins,  # User setting: all or essential only
                plugins_dir="plugins/optimizers"  # Fixed: was "dev/plugins/optimizers"
            )
            
            # Create optimized runtime pipeline with plugins and overlay system
            self.pipeline = create_optimized_runtime_pipeline(
                self.capture_layer,
                self.ocr_layer,
                self.translation_layer,
                config,
                overlay_system=self.overlay_system,
                config_manager=self.config_manager
            )
            
            # Set callbacks
            self.pipeline.on_translation = self._on_translation
            self.pipeline.on_error = self._on_error
            
            # Configure overlay tracker based on settings
            if hasattr(self.pipeline, 'overlay_tracker') and self.pipeline.overlay_tracker:
                auto_hide_enabled = self.config_manager.get_setting('overlay.auto_hide_on_disappear', True) if self.config_manager else True
                self.pipeline.overlay_tracker.set_enabled(auto_hide_enabled)
                print(f"[STARTUP] Overlay auto-hide on disappear: {'enabled' if auto_hide_enabled else 'disabled'}")
            
            # Store config reference for UI compatibility
            self.config = config
            
            self.logger.info(f"Optimized runtime pipeline created (plugins: {'enabled' if enable_plugins else 'disabled'})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {e}")
            return False
    
    def set_capture_region(self, x: int, y: int, width: int, height: int, monitor_id: int = 0):
        """Set capture region."""
        rectangle = Rectangle(x=x, y=y, width=width, height=height)
        self.capture_region = CaptureRegion(rectangle=rectangle, monitor_id=monitor_id)
        
        if self.pipeline:
            self.pipeline.config.capture_region = self.capture_region
        
        self.logger.info(f"Capture region set: {width}x{height} at ({x}, {y})")
    
    def start_translation(self) -> bool:
        """Start translation."""
        self.logger.info("start_translation called")
        
        # Check if OCR engine changed in config and reload if needed
        if self.ocr_layer and self.config_manager:
            config_engine = self.config_manager.get_setting('ocr.engine', 'tesseract')
            current_engine = self.ocr_layer.config.default_engine
            
            if config_engine != current_engine:
                print(f"[STARTUP] OCR engine changed: {current_engine} → {config_engine}")
                print(f"[STARTUP] Reloading OCR engine...")
                
                # Reload the OCR engine
                try:
                    ocr_config = {'gpu': True, 'language': 'en'}
                    success = self.ocr_layer.plugin_manager.load_plugin(config_engine, config=ocr_config)
                    
                    if success:
                        self.ocr_layer.set_default_engine(config_engine)
                        self.ocr_layer.config.default_engine = config_engine
                        print(f"[STARTUP] ✓ OCR engine reloaded: {config_engine}")
                    else:
                        print(f"[STARTUP] ⚠ Failed to reload OCR engine, keeping {current_engine}")
                except Exception as e:
                    print(f"[STARTUP] ⚠ Error reloading OCR engine: {e}")
        
        if not self.pipeline:
            self.logger.info("Pipeline not created, creating now...")
            if not self.create_pipeline():
                self.logger.error("Failed to create pipeline")
                return False
            self.logger.info("Pipeline created successfully")
        
        if not self.capture_region:
            self.logger.error("No capture region set")
            return False
        
        self.logger.info(f"Starting pipeline with region: {self.capture_region}")
        result = self.pipeline.start()
        self.logger.info(f"Pipeline start result: {result}")
        return result
    
    def stop_translation(self):
        """Stop translation."""
        if self.pipeline:
            self.pipeline.stop()
    
    def cleanup(self):
        """Clean up pipeline resources."""
        try:
            if self.pipeline:
                self.pipeline.stop()
            self.logger.info("Startup pipeline cleaned up")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self.pipeline and self.pipeline.is_running
    
    def set_ocr_engine(self, engine_name: str) -> bool:
        """
        Switch OCR engine using plugin system.
        
        Args:
            engine_name: Name of OCR engine to switch to
            
        Returns:
            True if switch successful, False otherwise
        """
        try:
            print(f"[STARTUP] Switching OCR engine to: {engine_name}")
            
            if not self.ocr_layer:
                print(f"[STARTUP] ✗ OCR layer not initialized")
                return False
            
            # Update OCR layer config
            self.ocr_layer.config.default_engine = engine_name
            
            # Load the new engine plugin if not already loaded
            print(f"[STARTUP] Loading {engine_name} plugin...")
            success = self.ocr_layer.plugin_manager.load_plugin(engine_name)
            
            if success:
                # Update config
                if self.config_manager:
                    self.config_manager.set_setting('ocr.engine', engine_name)
                    self.config_manager.save_config()
                
                print(f"[STARTUP] ✓ OCR engine switched to: {engine_name}")
                self.logger.info(f"OCR engine switched to {engine_name}")
                return True
            else:
                print(f"[STARTUP] ✗ Failed to load {engine_name} plugin")
                return False
                
        except Exception as e:
            print(f"[STARTUP] Error switching OCR engine: {e}")
            self.logger.error(f"Error switching OCR engine: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_multi_region_config(self, config):
        """
        Set multi-region config (runtime pipeline uses first region only).
        
        Args:
            config: MultiRegionConfig instance
        """
        # Get first enabled region
        enabled_regions = config.get_enabled_regions()
        if enabled_regions:
            first_region = enabled_regions[0]
            # Set as single capture region
            self.set_capture_region(
                first_region.rectangle.x,
                first_region.rectangle.y,
                first_region.rectangle.width,
                first_region.rectangle.height,
                first_region.monitor_id
            )
            self.logger.info(f"Using first region: {first_region.name} (multi-region not yet supported in runtime pipeline)")
        else:
            self.logger.warning("No enabled regions in multi-region config")
    
    def _on_translation(self, translations):
        """Handle translations from pipeline and display overlays."""
        try:
            # Display overlays
            if self.overlay_system:
                # Hide old overlays first
                self.overlay_system.hide_all_translations()
                
                # Get capture region offset for coordinate conversion
                region_x = 0
                region_y = 0
                if self.capture_region:
                    region_x = self.capture_region.rectangle.x
                    region_y = self.capture_region.rectangle.y
                
                # Show new overlays
                for i, translation in enumerate(translations):
                    # Get position from translation (OCR coordinates - relative to capture region)
                    if hasattr(translation, 'position'):
                        pos = translation.position
                        ocr_x = pos.x if hasattr(pos, 'x') else 0
                        ocr_y = pos.y if hasattr(pos, 'y') else 0
                    else:
                        ocr_x, ocr_y = 0, 0
                    
                    # Convert from capture-region-relative to absolute screen coordinates
                    abs_x = region_x + ocr_x
                    abs_y = region_y + ocr_y
                    
                    if i == 0:
                        print(f"[MINIMAL] Overlay coordinate conversion:")
                        print(f"  Capture region: ({region_x}, {region_y})")
                        print(f"  OCR relative: ({ocr_x}, {ocr_y})")
                        print(f"  Screen absolute: ({abs_x}, {abs_y})")
                    
                    # Get monitor ID from capture region
                    monitor_id = self.capture_region.monitor_id if self.capture_region else 0
                    
                    # Show overlay at absolute screen position
                    text = translation.translated_text if hasattr(translation, 'translated_text') else str(translation)
                    self.overlay_system.show_translation(text, (abs_x, abs_y), monitor_id=None)  # Use absolute coords, not monitor-relative
                
                print(f"[MINIMAL] Displayed {len(translations)} overlays")
            else:
                print("[MINIMAL] No overlay system available")
            
            # Call external callback if set
            if self.on_translation_callback:
                self.on_translation_callback(translations)
                
        except Exception as e:
            self.logger.error(f"Error in translation callback: {e}")
            print(f"[MINIMAL] Error displaying overlays: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_error(self, error: str):
        """Handle errors from pipeline."""
        if self.on_error_callback:
            try:
                self.on_error_callback(error)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")
    
    def get_available_ocr_engines(self) -> list:
        """
        Get list of available OCR engines.
        
        Returns:
            List of available OCR engine names (includes discovered engines, loaded or not)
        """
        if not self.ocr_layer:
            return []
        
        try:
            # Get all discovered plugins (includes both loaded and not-yet-loaded)
            all_plugins = self.ocr_layer.plugin_manager.registry.get_all_plugins()
            # Return plugin names (which are the engine names)
            return list(all_plugins.keys())
        except Exception as e:
            self.logger.error(f"Error getting available OCR engines: {e}")
            return []
    
    def get_current_ocr_engine(self) -> str:
        """
        Get the currently active/loaded OCR engine.
        
        Returns:
            Name of the currently loaded OCR engine, or 'unknown' if none loaded
        """
        if not self.ocr_layer:
            return "unknown"
        
        try:
            # Get the current engine from OCR layer config
            if hasattr(self.ocr_layer, 'config') and hasattr(self.ocr_layer.config, 'default_engine'):
                return self.ocr_layer.config.default_engine
            
            # Fallback: get first loaded engine
            loaded_engines = self.ocr_layer.get_available_engines()
            if loaded_engines:
                return loaded_engines[0] if isinstance(loaded_engines, list) else list(loaded_engines.keys())[0]
            
            return "unknown"
        except Exception as e:
            self.logger.error(f"Error getting current OCR engine: {e}")
            return "unknown"

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
    
    def warm_up_components(self):
        """
        Warm up components with dummy translation.
        Makes first real translation much faster by pre-loading models.
        """
        try:
            print("[WARMUP] Running component warm-up...")
            
            # Create dummy frame (small black image)
            import numpy as np
            dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
            from app.models import Frame, CaptureRegion, Rectangle
            
            # Create dummy capture region
            dummy_region = CaptureRegion(
                rectangle=Rectangle(x=0, y=0, width=100, height=100),
                monitor_id=0
            )
            
            dummy_frame = Frame(data=dummy_image, timestamp=0.001, source_region=dummy_region)
            
            # Run dummy OCR (fast - just initializes)
            if self.ocr_layer:
                try:
                    text_blocks = self.ocr_layer.extract_text(dummy_frame)
                    print("[WARMUP] ✓ OCR layer warmed up")
                except Exception as e:
                    print(f"[WARMUP] OCR warm-up skipped: {e}")
            
            # Skip translation warm-up to avoid UI freeze
            # Model will load on first actual translation (takes 3-5 seconds)
            if self.translation_layer:
                print("[WARMUP] Translation warm-up skipped (model loads on first use)")
            
            print("[WARMUP] ✓ Components ready - first translation will be fast!")
            
        except Exception as e:
            print(f"[WARMUP] Warning: Warm-up failed: {e}")
            # Not critical - continue anyway
            import traceback
            traceback.print_exc()
    
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
