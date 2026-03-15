"""
Startup Pipeline

Handles initialization of all components when the app starts.
Loads OCR engines, translation engines, and overlay system.

This is the "Initialization Pipeline" that runs once at startup.
It also serves as the primary QObject integration layer, exposing
Qt signals for pipeline lifecycle events (started, stopped, error,
loaded, translation_received) so that MainWindow can connect
directly without a separate PipelineManager wrapper.
"""
from __future__ import annotations

import logging
import sys
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal

from .pipeline import BasePipeline, PipelineConfig
from .pipeline_factory import PipelineFactory

try:
    from app.models import CaptureRegion, Rectangle, Translation
except ImportError:
    from models import CaptureRegion, Rectangle, Translation

from app.overlay.intelligent_positioning import (
    IntelligentPositioningEngine, PositioningContext, PositioningMode
)


class StartupPipeline(QObject):
    """
    Startup Pipeline - Initializes all components at app startup and
    manages the runtime translation pipeline lifecycle.
    
    Responsibilities:
    - Load OCR engines (EasyOCR, Tesseract, etc.)
    - Load translation engines (MarianMT)
    - Initialize overlay system (PyQt6)
    - Create and manage runtime pipeline for translation
    - Emit Qt signals for pipeline lifecycle events
    - Multi-region capture support
    - OCR engine switching
    """

    pipeline_started = pyqtSignal()
    pipeline_stopped = pyqtSignal()
    pipeline_error = pyqtSignal(str)
    pipeline_loaded = pyqtSignal()
    translation_received = pyqtSignal(dict)

    def __init__(self, config_manager=None, parent=None):
        """
        Initialize pipeline integration.
        
        Args:
            config_manager: Configuration manager
            parent: Parent QObject (optional)
        """
        QObject.__init__(self, parent)

        self.config_manager = config_manager
        self.logger = logging.getLogger('optikr.pipeline.startup')
        
        # Enable debug mode if configured
        self.debug_mode = False
        if config_manager:
            self.debug_mode = config_manager.get_setting('advanced.debug_mode', False)
            if self.debug_mode:
                self.logger.setLevel(logging.DEBUG)
                self.logger.debug("Debug mode enabled - verbose logging active")
        
        # Components
        self.capture_layer = None
        self.ocr_layer = None
        self.translation_layer = None
        self.llm_layer = None
        self.vision_layer = None
        
        # Runtime Pipeline (for translation loop)
        self.pipeline: BasePipeline | None = None
        self.capture_region: CaptureRegion | None = None
        
        # Overlay system
        self.overlay_system = None
        self._positioning_engine: IntelligentPositioningEngine | None = None

        # Auto-hide-on-disappear state tracking
        self._overlay_last_seen: dict[str, float] = {}
        self._active_overlay_ids: set[str] = set()

        # Cached OCR reference dimensions — locked after the first
        # successful frame so that overlay positions stay stable even
        # when preprocessing produces a differently-sized output
        # (e.g. because overlays got captured in the next frame).
        self._ocr_ref_size: tuple[int, int] | None = None  # (width, height)

        self._init_overlay_system()
        
        # Multi-region support (merged from PipelineIntegration)
        self.multi_region_enabled = False
        self.multi_region_config: 'MultiRegionConfig' | None = None
        self.multi_region_manager: 'MultiRegionCaptureManager' | None = None

        # OCR engine tracking
        self._current_ocr_engine: str | None = None

        # Subprocess manager (created when subprocess mode is selected)
        self._subprocess_manager = None
        self._vision_single_frame_lock = threading.Lock()
        
        self.logger.info("Startup pipeline initialized")
    
    def _init_overlay_system(self):
        """Initialize the overlay system and intelligent positioning engine."""
        try:
            from ui.overlays.thread_safe_overlay import create_thread_safe_overlay_system
            self.overlay_system = create_thread_safe_overlay_system(self.config_manager)
            self.logger.info("Thread-safe overlay system initialized")
        except Exception as e:
            self.logger.error("Failed to initialize overlay system: %s", e)

        try:
            collision_padding = 5
            screen_margin = 10
            if self.config_manager:
                collision_padding = self.config_manager.get_setting('overlay.collision_padding', 5)
                screen_margin = self.config_manager.get_setting('overlay.screen_margin', 10)

            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            screen = app.primaryScreen() if app else None
            if screen:
                geom = screen.geometry()
                ctx = PositioningContext(screen_width=geom.width(), screen_height=geom.height())
            else:
                ctx = PositioningContext()

            self._positioning_engine = IntelligentPositioningEngine(
                context=ctx,
                collision_padding=collision_padding,
                screen_margin=screen_margin,
            )
            self.logger.info(
                "Intelligent positioning engine initialized (padding=%d, margin=%d)",
                collision_padding, screen_margin,
            )
        except Exception as e:
            self.logger.warning("Failed to create positioning engine: %s", e)
    
    def initialize_components(self) -> bool:
        """Initialize pipeline components."""
        try:
            self.logger.info("Initializing components...")
            
            # Create capture layer
            self.logger.info("Creating capture layer...")
            self.capture_layer = self._create_capture_layer()
            if not self.capture_layer:
                raise Exception("Failed to create capture layer")
            self.logger.info("Capture layer created")
            
            pipeline_mode = "text"
            if self.config_manager:
                pipeline_mode = self.config_manager.get_setting("pipeline.mode", "text")
                if (
                    pipeline_mode == "vision"
                    and not self.config_manager.get_setting("vision.enabled", True)
                ):
                    self.logger.warning(
                        "pipeline.mode=vision but vision.enabled is False; "
                        "falling back to text-mode component initialization"
                    )
                    pipeline_mode = "text"

            # Create translation layer BEFORE OCR layer.
            # MarianMT imports transformers submodules that manga_ocr also
            # needs (ViTImageProcessor, AutoTokenizer).  Loading translation
            # first warms the import cache so the OCR init is ~3 s faster.
            self.logger.info("Creating translation layer...")
            self.translation_layer = self._create_translation_layer()
            if not self.translation_layer and pipeline_mode != "vision":
                raise Exception("Failed to create translation layer")
            if self.translation_layer:
                self.logger.info("Translation layer created")
            else:
                self.logger.warning(
                    "Translation layer unavailable in vision mode; continuing "
                    "(vision pipeline does not require text translation engine)"
                )

            # Create OCR layer only when not in vision mode (vision uses VL model, no OCR)
            if pipeline_mode != "vision":
                self.logger.info("Creating OCR layer...")
                self.ocr_layer = self._create_ocr_layer()
                if not self.ocr_layer:
                    raise Exception("Failed to create OCR layer")
                self.logger.info("OCR layer created")
            else:
                self.logger.info("OCR layer skipped (pipeline.mode=vision — OCR loads on switch to text)")

            # Create LLM layer (optional — returns None when disabled)
            self.logger.info("Creating LLM layer...")
            self.llm_layer = self._create_llm_layer()
            if self.llm_layer:
                self.logger.info("LLM layer created")
            else:
                self.logger.info("LLM layer not enabled or not available")

            # Create vision layer when pipeline mode is "vision"
            if pipeline_mode == "vision":
                self.logger.info("Creating vision layer (pipeline.mode=vision)...")
                self.vision_layer = self._init_vision_layer()
                if self.vision_layer:
                    self.logger.info("Vision layer created")
                else:
                    self.logger.warning("Vision layer not available — will fall back to text pipeline")
            
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
            fallback_enabled = True
            
            if self.config_manager:
                capture_mode = self.config_manager.get_setting('capture.method', 'auto')
                capture_fps = self.config_manager.get_setting('capture.fps', 30)
                capture_quality = self.config_manager.get_setting('capture.quality', 'high')
                fallback_enabled = self.config_manager.get_setting('capture.fallback_enabled', True)
                
                self.logger.info("Capture settings: mode=%s, fps=%s, quality=%s, fallback=%s",
                                capture_mode, capture_fps, capture_quality, fallback_enabled)
                self.logger.debug("Capture layer will use %s mode at %s FPS", capture_mode, capture_fps)
            
            # Use plugin-based capture layer to support different capture modes
            from app.capture.plugin_capture_layer import PluginCaptureLayer
            
            self.logger.info("Creating plugin-based capture layer (mode: %s)", capture_mode)
            
            # Create capture layer with config manager
            capture = PluginCaptureLayer(config_manager=self.config_manager)
            
            # Set capture mode (directx/screenshot/auto)
            if not capture.set_capture_mode(capture_mode):
                self.logger.warning("Failed to set capture mode '%s', using fallback", capture_mode)
                # Try fallback modes
                if capture_mode == 'directx' and fallback_enabled:
                    self.logger.info("Falling back to screenshot mode")
                    capture.set_capture_mode('screenshot')
                elif capture_mode == 'auto':
                    pass
            
            # Configure FPS
            if not capture.configure_capture_rate(capture_fps):
                self.logger.warning("Failed to set FPS to %s, using default", capture_fps)
            
            # Store quality setting for later use (quality affects image preprocessing)
            capture._quality = capture_quality
            
            self.logger.info(f"Capture layer created: mode={capture_mode}, fps={capture_fps}, quality={capture_quality}")
            return capture
            
        except Exception as e:
            self.logger.error("Failed to create capture layer: %s", e, exc_info=True)
            
            # Fallback to simple capture layer if plugin system fails
            try:
                self.logger.info("Falling back to simple capture layer")
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
            
            self.logger.info("OCR engine configured: %s", ocr_engine)
            
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
            self.logger.info("Discovering OCR plugins...")
            discovered = ocr_layer.plugin_manager.discover_plugins()
            
            if not discovered:
                self.logger.error("No OCR plugins found! User needs to install an OCR engine")
                # Return None to trigger installation dialog in the UI
                return None
            
            # Get plugin names from discovered list
            discovered_names = [plugin.name for plugin in discovered]
            self.logger.info("Found %d OCR plugin(s): %s", len(discovered), ', '.join(discovered_names))

            # Normalize legacy OCR engine aliases from config.
            # Tesseract users on Windows can run via windows_ocr plugin even
            # when optional tesserocr bindings are not installed.
            alias_map = {
                'winocr': 'windows_ocr',
            }
            if ocr_engine in alias_map:
                mapped = alias_map[ocr_engine]
                self.logger.info("Normalized OCR engine alias: %s -> %s", ocr_engine, mapped)
                ocr_engine = mapped
            if ocr_engine == 'tesseract' and 'tesseract' not in discovered_names and 'windows_ocr' in discovered_names:
                self.logger.info("Selected 'tesseract' unavailable, using 'windows_ocr' fallback")
                ocr_engine = 'windows_ocr'
            
            # Verify the selected engine exists
            if ocr_engine not in discovered_names:
                self.logger.warning("Selected engine '%s' not found! Available: %s",
                                    ocr_engine, ', '.join(discovered_names))
                preferred_order = [
                    'rapidocr', 'windows_ocr', 'tesseract', 'paddleocr',
                    'easyocr', 'doctr', 'surya_ocr', 'hybrid_ocr', 'judge_ocr', 'mokuro',
                ]
                ocr_engine = next((name for name in preferred_order if name in discovered_names), discovered_names[0])
                self.logger.info("Falling back to: %s", ocr_engine)
                # Save the fallback engine to config
                if self.config_manager:
                    self.config_manager.set_setting('ocr.engine', ocr_engine)
                    self.config_manager.save_config()
            
            # Load ONLY the selected engine (not all engines)
            self.logger.info("Loading %s engine (others load on-demand)...", ocr_engine)
            
            # Get GPU setting from config - DEFAULT TO TRUE for better performance
            use_gpu = True  # Default to GPU enabled
            
            if self.config_manager:
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
                enable_gpu = self.config_manager.get_setting('performance.enable_gpu_acceleration', True)
                # Also check OCR-specific GPU setting
                ocr_gpu = self.config_manager.get_setting('ocr.easyocr_config.gpu', True)
                
                # Use GPU if any of these conditions are true (or if explicitly disabled)
                use_gpu = (runtime_mode == 'gpu' or enable_gpu or ocr_gpu == True)
                
                self.logger.info("GPU mode: %s (runtime_mode=%s, enable_gpu=%s, ocr_gpu=%s)",
                                 use_gpu, runtime_mode, enable_gpu, ocr_gpu)
            else:
                self.logger.info("GPU mode: %s (no config_manager, using default)", use_gpu)
            
            # Prepare OCR config with GPU setting
            ocr_config = {
                'gpu': use_gpu,
                'language': 'en'  # Default language
            }
            
            self.logger.debug("Calling plugin_manager.load_plugin('%s', config=%s)...", ocr_engine, ocr_config)
            
            ssl_blocked_engines: set[str] = set()

            try:
                success = ocr_layer.plugin_manager.load_plugin(ocr_engine, config=ocr_config)
                self.logger.debug("load_plugin returned: %s", success)
            except Exception as e:
                self.logger.error("Exception loading %s: %s", ocr_engine, e, exc_info=True)
                success = False

            if not success and self._ocr_plugin_failed_with_ssl(ocr_layer, ocr_engine):
                ssl_blocked_engines.add(ocr_engine)
                self.logger.warning(
                    "Blocking OCR engine '%s' for this session due to SSL/certificate download failure",
                    ocr_engine,
                )
            
            if success:
                ocr_layer.set_default_engine(ocr_engine)
                self.logger.info("%s engine loaded and set as default", ocr_engine)
            else:
                self.logger.warning("Failed to load %s engine", ocr_engine)
                preferred_order = [
                    'rapidocr', 'windows_ocr', 'tesseract', 'paddleocr',
                    'easyocr', 'doctr', 'surya_ocr', 'hybrid_ocr', 'judge_ocr', 'mokuro',
                ]
                fallback_candidates = [e for e in preferred_order if e in discovered_names and e != ocr_engine]
                fallback_candidates.extend([e for e in discovered_names if e not in fallback_candidates and e != ocr_engine])
                for fallback_engine in fallback_candidates:
                    if fallback_engine in ssl_blocked_engines:
                        self.logger.info(
                            "Skipping fallback engine '%s' (blocked this session after SSL failure)",
                            fallback_engine,
                        )
                        continue

                    self.logger.info("Trying fallback engine: %s", fallback_engine)
                    if ocr_layer.plugin_manager.load_plugin(fallback_engine, config=ocr_config):
                        ocr_layer.set_default_engine(fallback_engine)
                        self.logger.info("Fallback to %s successful", fallback_engine)
                        ocr_engine = fallback_engine
                        success = True
                        break

                    if self._ocr_plugin_failed_with_ssl(ocr_layer, fallback_engine):
                        ssl_blocked_engines.add(fallback_engine)
                        self.logger.warning(
                            "Blocking fallback engine '%s' for this session due to SSL/certificate failure",
                            fallback_engine,
                        )
            
            if not success:
                self.logger.error("Failed to load any OCR engine")
                return None
            
            # Set status to ready (import the enum properly)
            from app.ocr.ocr_layer import OCRLayerStatus
            ocr_layer.status = OCRLayerStatus.READY
            
            return ocr_layer
            
        except Exception as e:
            self.logger.error("Failed to create OCR layer: %s", e, exc_info=True)
            return None

    @staticmethod
    def _is_ssl_or_cert_error(text: str) -> bool:
        """Return True when error text indicates SSL/certificate failure."""
        if not text:
            return False
        low = text.lower()
        needles = (
            "certificate_verify_failed",
            "certificate verify failed",
            "ssl:",
            "unable to get local issuer certificate",
            "urlopen error",
        )
        return any(n in low for n in needles)

    def _ocr_plugin_failed_with_ssl(self, ocr_layer, plugin_name: str) -> bool:
        """Check plugin registry load_error for SSL/certificate failures."""
        try:
            info = ocr_layer.plugin_manager.registry.get_plugin_info(plugin_name)
            if not info:
                return False
            return self._is_ssl_or_cert_error(getattr(info, "load_error", "") or "")
        except Exception:
            return False
    
    def _create_translation_layer(self):
        """Create translation layer with plugin support."""
        try:
            # Standard translation layer with plugin support
            # Per-language-pair routing is handled by the translation_chain plugin
            from app.text_translation.layer import TranslationLayer
            translation = TranslationLayer(config_manager=self.config_manager)
            self.logger.info("Translation layer created with plugin support")
            
            # Get runtime mode and GPU settings
            runtime_mode = 'auto'
            enable_gpu = True
            if self.config_manager:
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
                enable_gpu = self.config_manager.get_setting('performance.enable_gpu', True)
            
            # Determine which engine the user selected in settings
            engine_name = 'marianmt_gpu'
            if self.config_manager:
                engine_name = self.config_manager.get_setting('translation.engine', 'marianmt_gpu')
            if engine_name == 'marianmt':
                engine_name = 'marianmt_gpu'
                if self.config_manager:
                    self.config_manager.set_setting('translation.engine', 'marianmt_gpu')
                    self.config_manager.save_config()
                self.logger.info("Normalized translation engine alias: marianmt -> marianmt_gpu")
            self.logger.info("Configured translation engine: %s", engine_name)

            # API key mapping for cloud engines
            _API_KEY_CONFIG = {
                'google_api': 'translation.google_api_key',
                'deepl': 'translation.deepl_api_key',
                'azure': 'translation.azure_api_key',
            }

            if engine_name == 'marianmt_gpu':
                # MarianMT: direct import path (most common, keeps startup fast)
                try:
                    self.logger.info("Registering MarianMT translation engine...")
                    from plugins.stages.translation.marianmt_gpu.marianmt_engine import TranslationEngine

                    marianmt_engine = TranslationEngine()

                    engine_config = {}
                    if self.config_manager:
                        engine_config = {
                            'gpu': self.config_manager.get_setting('performance.enable_gpu', True),
                            'runtime_mode': self.config_manager.get_setting('performance.runtime_mode', 'auto'),
                        }

                    if marianmt_engine.initialize(engine_config) and marianmt_engine.is_available():
                        translation.register_engine(marianmt_engine, is_default=True, is_fallback=True)
                        self.logger.info("MarianMT engine registered (model will load on first translation)")
                    else:
                        self.logger.warning("MarianMT engine not available (transformers library missing?)")

                except Exception as engine_error:
                    self.logger.error("MarianMT engine registration failed: %s", engine_error, exc_info=True)
                    self.logger.info("Translation will use fallback/dummy mode")
            else:
                # Non-MarianMT engine: load via plugin manager
                try:
                    plugin_config = {}
                    if self.config_manager:
                        plugin_config['gpu'] = self.config_manager.get_setting('performance.enable_gpu', True)
                        plugin_config['runtime_mode'] = self.config_manager.get_setting('performance.runtime_mode', 'auto')

                        # Pass multilingual model variant only to seq2seq
                        # engines that share the multilingual_model_name
                        # setting (NLLB, M2M, mBART).  LLM-based engines
                        # like Qwen3 use their own default from plugin.json.
                        _SEQ2SEQ_ENGINES = {'nllb200', 'm2m100', 'mbart'}
                        if engine_name in _SEQ2SEQ_ENGINES:
                            ml_model = self.config_manager.get_setting(
                                'translation.multilingual_model_name', '',
                            )
                            if ml_model:
                                plugin_config['model_name'] = ml_model

                        # Wire API key from config for cloud engines
                        api_key_setting = _API_KEY_CONFIG.get(engine_name)
                        if api_key_setting:
                            api_key = self.config_manager.get_setting(api_key_setting, '')
                            if api_key:
                                plugin_config['api_key'] = api_key
                            else:
                                self.logger.warning(
                                    "No API key configured for engine '%s' (config key: %s)",
                                    engine_name, api_key_setting,
                                )

                    if translation.load_engine(engine_name, plugin_config):
                        self.logger.info("Translation engine '%s' loaded via plugin manager", engine_name)
                    else:
                        self.logger.warning(
                            "Failed to load engine '%s', falling back to MarianMT", engine_name,
                        )
                        # Fallback: try loading MarianMT so we don't leave the user with no engine
                        try:
                            from plugins.stages.translation.marianmt_gpu.marianmt_engine import TranslationEngine
                            fallback = TranslationEngine()
                            fb_config = {}
                            if self.config_manager:
                                fb_config = {
                                    'gpu': self.config_manager.get_setting('performance.enable_gpu', True),
                                    'runtime_mode': self.config_manager.get_setting('performance.runtime_mode', 'auto'),
                                }
                            if fallback.initialize(fb_config) and fallback.is_available():
                                translation.register_engine(fallback, is_default=True, is_fallback=True)
                                self.logger.info("MarianMT fallback engine registered")
                                if self.config_manager:
                                    self.config_manager.set_setting('translation.engine', 'marianmt_gpu')
                                    self.config_manager.save_config()
                                    self.logger.info(
                                        "Config updated: translation.engine -> marianmt_gpu "
                                        "(was '%s' which failed to load)", engine_name,
                                    )
                        except Exception as fb_err:
                            self.logger.error("MarianMT fallback also failed: %s", fb_err)

                except Exception as engine_error:
                    self.logger.error(
                        "Engine '%s' registration failed: %s", engine_name, engine_error, exc_info=True,
                    )
                    self.logger.info("Translation will use fallback/dummy mode")
            
            self.logger.info("Dictionary functionality available via translation layer")

            # Restore persisted translation cache from disk
            try:
                loaded = translation.load_cache_from_disk()
                if loaded > 0:
                    self.logger.info("Loaded %d cached translations from disk", loaded)
                else:
                    self.logger.info("No cached translations to restore")
            except Exception as cache_err:
                self.logger.warning("Failed to load translation cache from disk: %s", cache_err)

            return translation
            
        except Exception as e:
            self.logger.error("Failed to create translation layer: %s", e, exc_info=True)
            return None
    
    def _create_llm_layer(self):
        """Create the LLM layer when enabled in config.

        Returns ``None`` when the LLM stage is disabled or no LLM
        plugins are available, causing the ``LLMStage`` in the pipeline
        to act as a transparent pass-through.

        Includes conflict detection: when both the translation engine and
        the LLM engine are Qwen3 with the same model variant, the LLM
        plugin will share the already-loaded model via
        :class:`SharedModelRegistry` instead of allocating it twice.
        """
        llm_enabled = False
        if self.config_manager:
            llm_enabled = self.config_manager.get_setting('llm.enabled', False)

        if not llm_enabled:
            self.logger.info("LLM stage disabled by config (llm.enabled=false)")
            return None

        try:
            from app.llm.llm_layer import LLMLayer, LLMLayerConfig
            from app.llm.llm_engine_interface import LLMProcessingMode

            llm_engine = "qwen3"
            llm_mode = "refine"
            llm_temperature = 0.7
            llm_max_tokens = 512
            if self.config_manager:
                llm_engine = self.config_manager.get_setting('llm.engine', 'qwen3')
                llm_mode = self.config_manager.get_setting('llm.mode', 'refine')
                llm_temperature = self.config_manager.get_setting('llm.temperature', 0.7)
                llm_max_tokens = self.config_manager.get_setting('llm.max_tokens', 512)

            # --- Conflict detection: same Qwen3 model for both stages ---------
            if self.config_manager and llm_engine == "qwen3":
                trans_engine = self.config_manager.get_setting('translation.engine', 'marianmt_gpu')
                if trans_engine == "qwen3":
                    trans_model = self.config_manager.get_setting(
                        'translation.multilingual_model_name',
                        'Qwen/Qwen3-1.7B',
                    )
                    llm_model = self.config_manager.get_setting(
                        'llm.model_name', 'Qwen/Qwen3-1.7B',
                    )
                    if trans_model == llm_model:
                        self.logger.info(
                            "Qwen3 already loaded as translation engine (%s) — "
                            "LLM stage will share the model instance via "
                            "SharedModelRegistry (no extra memory used)",
                            llm_model,
                        )
                    else:
                        self.logger.info(
                            "Translation uses Qwen3 model '%s', LLM stage "
                            "uses '%s' — both will be loaded independently",
                            trans_model, llm_model,
                        )

            mode_map = {
                "refine": LLMProcessingMode.REFINE,
                "translate": LLMProcessingMode.TRANSLATE,
                "custom": LLMProcessingMode.CUSTOM,
            }

            config = LLMLayerConfig(
                default_engine=llm_engine,
                default_mode=mode_map.get(llm_mode, LLMProcessingMode.REFINE),
                default_temperature=llm_temperature,
                default_max_tokens=llm_max_tokens,
            )

            llm_layer = LLMLayer(config=config, config_manager=self.config_manager)

            self.logger.info("Initializing LLM layer (engine=%s)...", llm_engine)
            if llm_layer.initialize(auto_discover=True, auto_load=True):
                self.logger.info("LLM layer initialized successfully")
                return llm_layer
            else:
                self.logger.warning("LLM layer initialization failed — LLM stage will be skipped")
                return None

        except Exception as e:
            self.logger.warning("Failed to create LLM layer: %s", e)
            return None

    def _init_vision_layer(self):
        """Create the Qwen3-VL vision translation engine when vision mode is selected.

        Returns the engine instance on success, or ``None`` when the
        dependencies are missing or configuration disables it.
        """
        try:
            from plugins.stages.vision.qwen3_vl.worker import VisionTranslationEngine

            engine = VisionTranslationEngine()

            vision_config: dict[str, Any] = {}
            if self.config_manager:
                vision_config = {
                    "model_name": self.config_manager.get_setting(
                        "vision.model_name", "Qwen/Qwen3-VL-2B-Instruct"
                    ),
                    "max_tokens": self.config_manager.get_setting(
                        "vision.max_tokens", 256
                    ),
                    "temperature": self.config_manager.get_setting(
                        "vision.temperature", 0.3
                    ),
                    "quantization": self.config_manager.get_setting(
                        "vision.quantization", "none"
                    ),
                    "use_gpu": self.config_manager.get_setting(
                        "vision.use_gpu", True
                    ),
                    "prompt_template": self.config_manager.get_setting(
                        "vision.prompt_template", ""
                    ),
                    "context": self.config_manager.get_setting(
                        "vision.context", ""
                    ),
                    "exclude_sfx": self.config_manager.get_setting(
                        "vision.exclude_sfx", False
                    ),
                }
                if not vision_config["prompt_template"]:
                    del vision_config["prompt_template"]
                if not (vision_config.get("context") or "").strip():
                    vision_config.pop("context", None)

            if engine.initialize(vision_config) and engine.is_available():
                self.logger.info("Vision translation engine initialised")
                return engine

            self.logger.warning("Vision engine not available (missing torch/transformers?)")
            return None

        except Exception as exc:
            self.logger.warning("Failed to create vision layer: %s", exc)
            return None

    def create_pipeline(self) -> bool:
        """Create the runtime pipeline for translation via PipelineFactory."""
        try:
            pipeline_mode = "text"
            if self.config_manager:
                pipeline_mode = self.config_manager.get_setting("pipeline.mode", "text")
                if (
                    pipeline_mode == "vision"
                    and not self.config_manager.get_setting("vision.enabled", True)
                ):
                    self.logger.warning(
                        "Vision mode requested but vision.enabled=False; "
                        "falling back to text pipeline"
                    )
                    pipeline_mode = "text"
            if pipeline_mode == "vision":
                if self.capture_layer is None:
                    self.logger.error("Components not initialized (vision mode)")
                    return False
            elif pipeline_mode == "audio":
                if self.translation_layer is None:
                    self.translation_layer = self._create_translation_layer()
                if self.translation_layer is None:
                    self.logger.error("Components not initialized (audio mode)")
                    return False
            else:
                if self.translation_layer is None:
                    self.translation_layer = self._create_translation_layer()
                if self.ocr_layer is None:
                    self.ocr_layer = self._create_ocr_layer()
                if not all([self.capture_layer, self.ocr_layer, self.translation_layer]):
                    self.logger.error("Components not initialized")
                    return False

            # Get languages and capture settings from config
            source_lang = "en"
            target_lang = "de"
            capture_fps = 30
            
            if self.config_manager:
                source_lang = self.config_manager.get_setting('translation.source_language', 'en')
                target_lang = self.config_manager.get_setting('translation.target_language', 'de')
                capture_fps = self.config_manager.get_setting('capture.fps', 30)

                # In vision mode, prefer a much lower capture FPS to reduce latency
                # and redundant processing. A separate vision.capture_fps setting
                # allows text mode to keep its usual capture rate.
                if pipeline_mode == "vision":
                    capture_fps = self.config_manager.get_setting('vision.capture_fps', 1)

                # If source language is still the schema default, check
                # whether the OCR engine constrains it (e.g. Manga OCR → ja).
                if source_lang == "en":
                    ocr_langs = self.config_manager.get_setting('ocr.languages', [])
                    if ocr_langs and len(ocr_langs) == 1 and ocr_langs[0] != "en":
                        source_lang = ocr_langs[0]
                        self.logger.info(
                            "Source language overridden by OCR language: %s",
                            source_lang,
                        )
            
            self.logger.info("Translation: %s -> %s, Capture FPS: %s", source_lang, target_lang, capture_fps)
            
            enable_all_plugins = False
            if self.config_manager:
                enable_all_plugins = self.config_manager.get_setting('pipeline.enable_optimizer_plugins', False)
                self.logger.info("Optimizer plugins: %s", 'all enabled' if enable_all_plugins else 'essential only')
            
            # Load overlay region constraint from config
            overlay_region = None
            if self.config_manager:
                or_cfg = self.config_manager.get_setting('overlay.region', None)
                if or_cfg and isinstance(or_cfg, dict):
                    overlay_region = or_cfg

            config = PipelineConfig(
                capture_region=self.capture_region,
                overlay_region=overlay_region,
                target_fps=capture_fps,
                source_language=source_lang,
                target_language=target_lang,
            )

            # Determine execution preset from config (pipeline_mode already set above)
            preset = "sequential"
            stage_modes = None
            subprocess_manager = None

            if pipeline_mode == "vision":
                preset = "vision"
                if self.vision_layer is None:
                    self.logger.info("Initialising vision layer for vision pipeline mode...")
                    self.vision_layer = self._init_vision_layer()
                if self.vision_layer is None:
                    self.logger.warning(
                        "Vision mode requested but engine unavailable; "
                        "falling back to text pipeline"
                    )
                    pipeline_mode = "text"
                    preset = "sequential"
                    if self.translation_layer is None:
                        self.translation_layer = self._create_translation_layer()
                    if self.ocr_layer is None:
                        self.ocr_layer = self._create_ocr_layer()
                    if self.translation_layer is None or self.ocr_layer is None:
                        self.logger.error(
                            "Failed to initialize text-mode dependencies during "
                            "vision fallback (translation=%s, ocr=%s)",
                            bool(self.translation_layer),
                            bool(self.ocr_layer),
                        )
                        return False
            elif pipeline_mode == "audio":
                preset = "audio"

            if pipeline_mode == "text" and self.config_manager:
                mode_setting = self.config_manager.get_setting('pipeline.execution_mode', 'sequential')
                if mode_setting in ("sequential", "async", "custom", "subprocess"):
                    preset = mode_setting
                if preset == "custom":
                    from app.workflow.pipeline.types import ExecutionMode
                    raw_modes = self.config_manager.get_setting('pipeline.stage_modes', {})
                    mode_str_map = {
                        "sequential": ExecutionMode.SEQUENTIAL,
                        "async": ExecutionMode.ASYNC,
                    }
                    stage_modes = {
                        k: mode_str_map.get(v, ExecutionMode.SEQUENTIAL)
                        for k, v in raw_modes.items()
                    }
                if preset == "subprocess":
                    subprocess_manager = self._create_subprocess_manager()
                    if subprocess_manager is None:
                        self.logger.warning(
                            "Subprocess mode requested but manager failed to start; "
                            "falling back to sequential"
                        )
                        preset = "sequential"

            factory = PipelineFactory(config_manager=self.config_manager)
            self.pipeline = factory.create(
                preset,
                capture_layer=self.capture_layer,
                ocr_layer=self.ocr_layer,
                translation_layer=self.translation_layer,
                llm_layer=self.llm_layer,
                vision_layer=self.vision_layer,
                overlay_renderer=self.overlay_system,
                config=config,
                stage_modes=stage_modes,
                subprocess_manager=subprocess_manager,
                enable_all_plugins=enable_all_plugins,
            )
            
            # Set callbacks
            self.pipeline.on_translation = self._on_translation
            self.pipeline.on_error = self._on_error
            
            # Store config reference for UI compatibility
            self.config = config

            # Track current OCR engine
            try:
                self._current_ocr_engine = self.get_current_ocr_engine()
            except Exception as e:
                self.logger.debug("Could not track current OCR engine: %s", e)

            # Restore saved capture region so the pipeline is ready on startup
            self._restore_capture_region_from_config()

            # Register SmartDictionary as a facade-level engine for direct lookups
            self._register_dictionary_engine()
            
            self.logger.info(f"Pipeline created (preset={preset}, plugins={'all' if enable_all_plugins else 'essential'})")
            self.pipeline_loaded.emit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {e}")
            self.pipeline_error.emit(f"Failed to create pipeline: {e}")
            return False
    
    def set_capture_region(self, x: int, y: int, width: int, height: int, monitor_id: int = 0):
        """
        Set the capture region (single region mode).

        Disables multi-region mode if it was previously active.
        """
        rectangle = Rectangle(x=x, y=y, width=width, height=height)
        self.capture_region = CaptureRegion(rectangle=rectangle, monitor_id=monitor_id)

        self.multi_region_enabled = False
        self._ocr_ref_size = None  # Reset so next frame re-locks
        
        if self.pipeline:
            self.pipeline.config.capture_region = self.capture_region
        
        self.logger.info(f"Capture region set: {width}x{height} at ({x}, {y})")
    
    def _sync_ocr_engine(self) -> None:
        """Reload OCR engine if config has changed since last run.

        Unloads the old engine first to free GPU/RAM before loading the
        new one.
        """
        if not self.ocr_layer or not self.config_manager:
            return
        
        config_engine = self.config_manager.get_setting('ocr.engine', 'easyocr')
        current_engine = self.ocr_layer.config.default_engine
        
        if config_engine == current_engine:
            return
        
        self.logger.info("OCR engine changed: %s -> %s, reloading...", current_engine, config_engine)
        
        try:
            if current_engine:
                self.logger.info("Unloading previous OCR engine: %s", current_engine)
                self.ocr_layer.plugin_manager.unload_plugin(current_engine)

            ocr_config = {'gpu': True, 'language': 'en'}
            success = self.ocr_layer.plugin_manager.load_plugin(config_engine, config=ocr_config)
            
            if success:
                self.ocr_layer.set_default_engine(config_engine)
                self.ocr_layer.config.default_engine = config_engine
                self.logger.info("OCR engine reloaded: %s", config_engine)
            else:
                self.logger.warning("Failed to reload OCR engine, keeping %s", current_engine)
        except Exception as e:
            self.logger.warning("Error reloading OCR engine: %s", e)
    
    def _ensure_pipeline(self) -> bool:
        """Create the pipeline if it doesn't exist yet.
        
        Returns:
            True if pipeline is ready, False if creation failed.
        """
        if self.pipeline:
            return True
        
        self.logger.info("Pipeline not created, creating now...")
        if not self.create_pipeline():
            self.logger.error("Failed to create pipeline")
            return False
        self.logger.info("Pipeline created successfully")
        return True
    
    def _validate_capture_region(self) -> bool:
        """Check that a capture region is set.
        
        Returns:
            True if capture region exists, False otherwise.
        """
        if not self.capture_region:
            self.logger.error("No capture region set")
            return False
        return True
    
    def start_translation(self) -> bool:
        """
        Start the translation pipeline.

        In multi-region mode the ``MultiRegionCaptureManager`` handles capture
        and calls ``_on_multi_region_frame()`` per region.  In single-region
        mode the pipeline's own capture loop runs.

        Emits ``pipeline_started`` on success, ``pipeline_error`` on failure.
        """
        self.logger.info("start_translation called")
        
        self._sync_ocr_engine()
        
        if not self._ensure_pipeline():
            return False

        if self.multi_region_enabled:
            if not self.multi_region_config or not self.multi_region_config.get_enabled_regions():
                msg = "Cannot start: no enabled regions in multi-region mode"
                self.logger.error(msg)
                self.pipeline_error.emit(msg)
                return False

            if self.multi_region_manager:
                self.logger.info("Starting multi-region manager")
                if not self.multi_region_manager.start():
                    msg = "Failed to start multi-region capture"
                    self.logger.error(msg)
                    self.pipeline_error.emit(msg)
                    return False
                self.logger.info("Multi-region capture started successfully")
            else:
                self.logger.error("multi_region_manager is None — cannot start multi-region capture")

            self.pipeline_started.emit()
            return True

        if not self._validate_capture_region():
            return False

        if self.capture_layer and hasattr(self.capture_layer, 'force_refresh'):
            monitor_id = 0
            if self.capture_region:
                monitor_id = getattr(self.capture_region, 'monitor_id', 0)
            self.capture_layer.force_refresh(monitor_id)

        self.logger.info(f"Starting pipeline with region: {self.capture_region}")

        self._compile_context_manager()

        result = self.pipeline.start()
        self.logger.info(f"Pipeline start result: {result}")

        if result:
            self.pipeline_started.emit()
        return result
    
    def stop_translation(self):
        """
        Stop the translation pipeline.

        Stops the multi-region manager (if active) and the underlying
        runtime pipeline.  Hides all overlays and emits ``pipeline_stopped``.
        """
        self._end_context_session()

        if self.multi_region_enabled and self.multi_region_manager:
            self.multi_region_manager.stop()
            self.logger.info("Multi-region capture stopped")

        if self.pipeline:
            self.pipeline.stop()

        if self.capture_layer and hasattr(self.capture_layer, 'force_refresh'):
            monitor_id = 0
            if self.capture_region:
                monitor_id = getattr(self.capture_region, 'monitor_id', 0)
            self.capture_layer.force_refresh(monitor_id)

        # Hide all overlays immediately so nothing lingers on screen
        if self.overlay_system:
            try:
                if hasattr(self.overlay_system, 'hide_all_translations'):
                    self.overlay_system.hide_all_translations(immediate=True)
                elif hasattr(self.overlay_system, 'hide_all'):
                    self.overlay_system.hide_all()
            except Exception as e:
                self.logger.warning("Failed to hide overlays on stop: %s", e)

        # Clear overlay tracking state
        self._overlay_last_seen.clear()
        self._active_overlay_ids.clear()
        self._ocr_ref_size = None

        self.pipeline_stopped.emit()
    
    def toggle(self) -> None:
        """Toggle the translation pipeline on/off."""
        if self.is_running():
            self.stop_translation()
        else:
            if not self.start_translation():
                self.pipeline_error.emit(
                    "Failed to start translation. Try stopping and starting again, or check the capture region."
                )

    _recording_flash_active = False

    def flash_overlays_for_recording(self, duration: float = 5.0) -> bool:
        """Make overlays visible to screen capture for *duration* seconds.

        The pipeline is paused while overlays are exposed so no new
        frames are captured and the OCR feedback loop cannot occur.
        A ``QTimer`` re-hides the overlays and resumes the pipeline
        automatically.

        Returns ``False`` if the flash is already active or there is
        nothing to flash.
        """
        if self._recording_flash_active:
            self.logger.info("Recording flash already active, ignoring")
            return False
        if not self.overlay_system:
            self.logger.warning("No overlay system for recording flash")
            return False

        was_running = self.is_running()
        if was_running and self.pipeline:
            self.pipeline.pause()

        self.overlay_system.set_all_capture_visible(True)
        self._recording_flash_active = True
        self.logger.info("Recording flash: overlays visible for %.1fs", duration)

        from PyQt6.QtCore import QTimer

        def _end_flash():
            if self.overlay_system:
                self.overlay_system.set_all_capture_visible(False)
            self.logger.info("Recording flash ended, waiting for compositor...")

            def _resume_after_compositor():
                self._recording_flash_active = False
                if was_running and self.pipeline:
                    self.pipeline.resume()
                self.logger.info("Pipeline resumed after compositor settle")

            QTimer.singleShot(400, _resume_after_compositor)

        QTimer.singleShot(int(duration * 1000), _end_flash)
        return True

    def capture_screenshot_with_overlays(self) -> "QPixmap | None":
        """Capture a screenshot of the capture region with overlays composited.

        Temporarily makes overlay windows visible to screen-capture APIs,
        grabs the region, then re-hides them.  The pipeline is paused for
        the duration so the brief WDA_NONE window cannot cause a feedback
        frame.

        Returns a ``QPixmap`` on success, *None* on failure.
        """
        if not self.overlay_system or not self.capture_region:
            self.logger.warning("Cannot take screenshot: no overlay system or capture region")
            return None

        was_running = self.is_running()
        try:
            if was_running and self.pipeline:
                self.pipeline.pause()

            self.overlay_system.set_all_capture_visible(True)

            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()

            import time as _time
            _time.sleep(0.15)

            if app:
                app.processEvents()

            r = self.capture_region.rectangle
            self.logger.info(
                "Taking screenshot at (%d, %d) %dx%d",
                r.x, r.y, r.width, r.height,
            )

            pixmap = self._grab_region(r.x, r.y, r.width, r.height)
            if pixmap is None or pixmap.isNull():
                self.logger.warning("Screenshot grab returned null pixmap")
                return None

            self.logger.info("Screenshot captured: %dx%d", pixmap.width(), pixmap.height())
            return pixmap
        except Exception as exc:
            self.logger.error("Screenshot failed: %s", exc, exc_info=True)
            return None
        finally:
            if self.overlay_system:
                self.overlay_system.set_all_capture_visible(False)
            if was_running and self.pipeline:
                self.pipeline.resume()

    @staticmethod
    def _grab_region(x: int, y: int, w: int, h: int):
        """Grab a screen region, trying native Win32 first then Qt fallback."""
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                from PyQt6.QtGui import QImage, QPixmap

                gdi32 = ctypes.windll.gdi32
                user32 = ctypes.windll.user32

                hdc_screen = user32.GetDC(0)
                hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
                hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
                gdi32.SelectObject(hdc_mem, hbmp)
                gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020)

                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ("biSize", wintypes.DWORD),
                        ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD),
                        ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD),
                        ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG),
                        ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD),
                    ]

                bmi = BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.biWidth = w
                bmi.biHeight = -h  # top-down
                bmi.biPlanes = 1
                bmi.biBitCount = 32
                bmi.biCompression = 0

                buf = (ctypes.c_ubyte * (w * h * 4))()
                gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

                gdi32.DeleteObject(hbmp)
                gdi32.DeleteDC(hdc_mem)
                user32.ReleaseDC(0, hdc_screen)

                img = QImage(bytes(buf), w, h, w * 4, QImage.Format.Format_ARGB32)
                return QPixmap.fromImage(img.copy())
            except Exception:
                pass  # fall through to Qt method

        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.grabWindow(0, x, y, w, h)

    def run_vision_single_frame(self) -> tuple[bool, int, str]:
        """Capture and process exactly one frame in vision mode.

        Returns
        -------
        tuple[bool, int, str]
            (success, translated_block_count, error_message)
        """
        if not self._vision_single_frame_lock.acquire(blocking=False):
            return False, 0, "Vision single-frame processing is already running"

        try:
            mode = "text"
            if self.config_manager:
                mode = self.config_manager.get_setting("pipeline.mode", "text")
            if mode != "vision":
                return False, 0, "Vision single-frame trigger requires pipeline.mode=vision"

            if self.is_running():
                self.stop_translation()

            if self.capture_layer is None:
                return False, 0, "Capture layer is not initialized"

            if self.vision_layer is None:
                self.vision_layer = self._init_vision_layer()
            if self.vision_layer is None:
                return False, 0, "Vision layer is not available"

            source_lang = "en"
            target_lang = "de"
            if self.config_manager:
                source_lang = self.config_manager.get_setting("translation.source_language", "en")
                target_lang = self.config_manager.get_setting("translation.target_language", "de")

            args = []
            if self.capture_region is not None:
                args.extend(["custom_region", self.capture_region])
            frame = (
                self.capture_layer.capture_frame(*args)
                if args
                else self.capture_layer.capture_frame()
            )
            if frame is None:
                return False, 0, "Failed to capture frame"

            frame_data = frame.data if hasattr(frame, "data") else frame
            results = self.vision_layer.translate_frame(frame_data, source_lang, target_lang)
            if not results:
                return False, 0, "No translation blocks returned for this frame"

            translations = []
            text_blocks = []
            for item in results:
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                original = str(item.get("original", "")).strip()
                bbox = item.get("bbox", [0, 0, 100, 30])
                if not isinstance(bbox, list) or len(bbox) < 4:
                    bbox = [0, 0, 100, 30]

                block_source_text = original if original else text
                text_blocks.append({
                    "text": block_source_text,
                    "position": Rectangle(
                        x=int(bbox[0]),
                        y=int(bbox[1]),
                        width=int(bbox[2]),
                        height=int(bbox[3]),
                    ),
                    "confidence": 1.0,
                    "source": "vision",
                })
                translations.append(text)

            if not translations:
                return False, 0, "No non-empty translated text blocks returned"

            self._on_translation({
                "translations": translations,
                "text_blocks": text_blocks,
                "frame": frame,
                "source_lang": source_lang,
                "target_lang": target_lang,
            })
            return True, len(translations), ""
        except Exception as exc:
            self.logger.error("Vision single-frame execution failed: %s", exc, exc_info=True)
            return False, 0, str(exc)
        finally:
            self._vision_single_frame_lock.release()

    def set_pipeline_mode(self, mode: str) -> bool:
        """Switch the active pipeline mode at runtime.

        Stops the current pipeline (if running), tears it down, updates
        the config key ``pipeline.mode``, and recreates the pipeline with
        the new preset.

        Parameters
        ----------
        mode:
            One of ``"text"``, ``"vision"``, or ``"audio"``.

        Returns
        -------
        bool
            True if the pipeline was successfully recreated.
        """
        if mode not in ("text", "vision", "audio"):
            self.logger.error("Invalid pipeline mode: %s", mode)
            return False
        if mode == "vision" and self.config_manager is not None:
            if not self.config_manager.get_setting("vision.enabled", True):
                self.logger.error("Cannot switch to vision mode while vision.enabled is False")
                return False

        was_running = self.is_running()
        if was_running:
            self.logger.info("Stopping pipeline for mode switch to '%s'...", mode)
            self.stop_translation()

        if self.pipeline:
            try:
                self.pipeline.cleanup()
            except Exception as exc:
                self.logger.warning("Pipeline cleanup failed during mode switch: %s", exc)
            self.pipeline = None

        if self.config_manager:
            self.config_manager.set_setting("pipeline.mode", mode)
            self.config_manager.save_config()

        self.logger.info("Switching pipeline mode to '%s'", mode)

        if mode == "vision" and self.vision_layer is None:
            self.vision_layer = self._init_vision_layer()

        if mode == "text" and self.ocr_layer is None:
            self.logger.info("Creating OCR layer for text mode...")
            self.ocr_layer = self._create_ocr_layer()
            if not self.ocr_layer:
                self.logger.error("Failed to create OCR layer when switching to text mode")
                return False

        success = self.create_pipeline()

        if success and mode == "text":
            self.logger.info("Warming up OCR and translation for text mode...")
            self.warm_up_components()

        if success and was_running:
            self.start_translation()

        return success

    # ------------------------------------------------------------------
    # Context Manager lifecycle helpers
    # ------------------------------------------------------------------

    def _get_context_manager(self):
        """Return the context_manager plugin instance or None."""
        if not self.pipeline:
            return None
        loader = getattr(self.pipeline, "_optimizer_loader", None)
        if loader is None:
            return None
        plugins = getattr(loader, "plugins", {})
        cm_info = plugins.get("context_manager")
        if cm_info is None:
            return None
        return cm_info.get("optimizer")

    def _compile_context_manager(self):
        """Compile the context manager profile at session start.

        Reloads the active profile from disk so that any changes made
        in the UI tab (which uses its own plugin instance) are picked
        up by the pipeline's context manager before compilation.
        """
        if self.config_manager:
            enabled = self.config_manager.get_setting(
                "plugins.context_manager.enabled", True)
            if not enabled:
                self.logger.info("Context Manager disabled by config")
                return
        cm = self._get_context_manager()
        if cm is None:
            return
        try:
            if self.config_manager and hasattr(cm, "load_profile"):
                active_name = self.config_manager.get_setting(
                    "plugins.context_manager.active_profile", "")
                if active_name:
                    cm.load_profile(active_name)
                    self.logger.info(
                        "Context Manager reloaded profile '%s' from disk",
                        active_name,
                    )
            if hasattr(cm, "compile"):
                cm.compile()
                self.logger.info("Context Manager compiled for session")
        except Exception as exc:
            self.logger.warning("Context Manager compile failed: %s", exc)

    def _end_context_session(self):
        """End the context manager session on pipeline stop."""
        cm = self._get_context_manager()
        if cm is not None and hasattr(cm, "end_session"):
            try:
                cm.end_session()
                self.logger.info("Context Manager session ended")
            except Exception as exc:
                self.logger.warning("Context Manager end_session failed: %s", exc)

    # ------------------------------------------------------------------
    # Smart Dictionary helpers
    # ------------------------------------------------------------------

    def _register_dictionary_engine(self) -> None:
        """Register the pipeline's SmartDictionary as a ``"dictionary"`` engine in the facade.

        This lets ``TranslationFacade.translate()`` check the dictionary
        before calling the main AI engine, providing fast lookups for
        known translations even outside the optimizer plugin path.
        """
        if not self.pipeline or not self.translation_layer:
            return
        cache_mgr = getattr(self.pipeline, "cache_manager", None)
        if cache_mgr is None:
            return
        smart_dict = getattr(cache_mgr, "persistent_dictionary", None)
        if smart_dict is None:
            return
        try:
            from app.text_translation.smart_dictionary_engine import SmartDictionaryEngine

            engine = SmartDictionaryEngine(dictionary=smart_dict)
            self.translation_layer.register_engine(
                engine, is_default=False, is_fallback=False,
            )
            self.logger.info(
                "SmartDictionary registered as 'dictionary' engine in facade"
            )
        except Exception as exc:
            self.logger.warning("Failed to register dictionary engine: %s", exc)

    def _get_learning_dictionary_optimizer(self):
        """Return the ``learning_dictionary`` optimizer plugin instance or ``None``."""
        if not self.pipeline:
            return None
        loader = getattr(self.pipeline, "_optimizer_loader", None)
        if loader is None:
            return None
        plugins = getattr(loader, "plugins", {})
        ld_info = plugins.get("learning_dictionary")
        if ld_info is None:
            return None
        return ld_info.get("optimizer")

    def get_session_learned_count(self) -> int:
        """Return the number of translations the optimizer learned so far."""
        optimizer = self._get_learning_dictionary_optimizer()
        if optimizer is None:
            return 0
        return getattr(optimizer, "saved_translations", 0)

    def save_translation_cache(self) -> bool:
        """Persist the translation cache to disk.

        Returns True on success, False on failure.
        """
        if self.translation_layer and hasattr(self.translation_layer, 'save_cache_to_disk'):
            try:
                return self.translation_layer.save_cache_to_disk()
            except Exception as e:
                self.logger.warning("Failed to save translation cache: %s", e)
                return False
        return False

    @property
    def cache_manager(self):
        """Expose the pipeline's ``PipelineCacheManager`` for UI access."""
        if self.pipeline:
            return getattr(self.pipeline, "cache_manager", None)
        return None

    # ------------------------------------------------------------------
    # Subprocess manager helpers
    # ------------------------------------------------------------------

    def _create_subprocess_manager(self):
        """Create and start a SubprocessManager for the current OCR plugin.

        Returns the manager on success, or ``None`` on failure (missing
        worker script, subprocess crash, etc.).
        """
        try:
            from app.workflow.managers.subprocess_manager import SubprocessManager
        except ImportError:
            self.logger.warning("SubprocessManager import failed")
            return None

        if not self.ocr_layer:
            self.logger.warning("Cannot create SubprocessManager: no OCR layer")
            return None

        ocr_engine = "easyocr"
        if self.config_manager:
            ocr_engine = self.config_manager.get_setting("ocr.engine", "easyocr")

        plugin_path = self._resolve_ocr_plugin_path(ocr_engine)
        if plugin_path is None:
            self.logger.warning(
                "Cannot create SubprocessManager: no plugin path for %s", ocr_engine,
            )
            return None

        manager = SubprocessManager(config_manager=self.config_manager)
        if manager.start(ocr_engine, plugin_path):
            self._subprocess_manager = manager
            self.logger.info("SubprocessManager started for %s", ocr_engine)
            return manager

        self.logger.warning("SubprocessManager failed to start for %s", ocr_engine)
        return None

    def _resolve_ocr_plugin_path(self, engine_name: str) -> str | None:
        """Return the absolute directory path for the given OCR plugin."""
        try:
            from app.utils.path_utils import get_plugin_stages_dir
            plugin_dir = get_plugin_stages_dir("ocr") / engine_name
            if plugin_dir.is_dir():
                return str(plugin_dir)
        except Exception:
            pass

        from pathlib import Path
        fallback_candidates = [
            Path.cwd() / "plugins" / "stages" / "ocr" / engine_name,
            Path(__file__).resolve().parent.parent.parent / "plugins" / "stages" / "ocr" / engine_name,
        ]
        if getattr(sys, "frozen", False):
            fallback_candidates.append(
                Path(sys.executable).resolve().parent / "plugins" / "stages" / "ocr" / engine_name
            )

        for candidate in fallback_candidates:
            if candidate.is_dir():
                return str(candidate.resolve())

        return None

    def cleanup(self):
        """
        Full cleanup of pipeline and all its subsystems.

        Stops the pipeline if running, then cleans up subprocess manager,
        overlay system, cache manager, and the pipeline itself.
        Safe to call multiple times.
        """
        if self.is_running():
            self.stop_translation()

        # Stop subprocess manager
        if self._subprocess_manager is not None:
            try:
                self._subprocess_manager.stop()
            except Exception as e:
                self.logger.warning("Failed to stop subprocess manager: %s", e)
            self._subprocess_manager = None

        # Persist translation cache before tearing down resources
        self.save_translation_cache()

        pipeline = self.pipeline
        if pipeline:
            # Clean up the cache manager (saves dictionaries + frees memory)
            try:
                cache = getattr(pipeline, 'cache_manager', None)
                if cache is not None:
                    cache.cleanup()
            except Exception as e:
                self.logger.warning("Failed to cleanup cache manager: %s", e)

            try:
                if hasattr(pipeline, 'cleanup'):
                    pipeline.cleanup()
            except Exception as e:
                self.logger.warning("Failed to cleanup pipeline: %s", e)

        if self.vision_layer is not None:
            try:
                self.vision_layer.cleanup()
            except Exception as e:
                self.logger.warning("Failed to cleanup vision layer: %s", e)
            self.vision_layer = None

        if self.overlay_system:
            try:
                if hasattr(self.overlay_system, 'cleanup'):
                    self.overlay_system.cleanup()
                elif hasattr(self.overlay_system, 'hide_all'):
                    self.overlay_system.hide_all()
            except Exception as e:
                self.logger.warning("Failed to cleanup overlay system: %s", e)

        # Release GPU memory so VRAM is reclaimed without restarting the app
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.info("GPU cache cleared")
        except Exception:
            pass

        self.logger.info("Startup pipeline cleaned up")
    
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        if self.multi_region_enabled and self.multi_region_manager:
            return getattr(self.multi_region_manager, 'is_running', False)
        return bool(self.pipeline and self.pipeline.is_running())

    def update_runtime_config(
        self,
        plugin_class_name: str,
        config: dict,
        **kwargs,
    ) -> bool:
        """Forward runtime config update to the inner BasePipeline."""
        if self.pipeline is not None:
            return self.pipeline.update_runtime_config(
                plugin_class_name, config, **kwargs)
        return False

    def get_metrics(self) -> 'PipelineStats':
        """Return combined metrics from BasePipeline stats and translation layer.

        Computes ``average_fps`` and ``average_latency_ms`` from the raw
        pipeline counters, and pulls ``total_translations`` / ``cache_hits``
        from the translation layer's performance tracking.
        """
        from .pipeline.types import PipelineStats

        if not self.pipeline:
            return PipelineStats()

        stats = self.pipeline.get_stats()

        if stats.frames_processed > 0 and stats.total_duration_ms > 0:
            total_seconds = stats.total_duration_ms / 1000.0
            stats.average_fps = stats.frames_processed / total_seconds
            stats.average_latency_ms = stats.total_duration_ms / stats.frames_processed
        else:
            stats.average_fps = 0.0
            stats.average_latency_ms = 0.0

        if self.translation_layer and hasattr(self.translation_layer, '_performance_stats'):
            perf = self.translation_layer._performance_stats
            stats.total_translations = perf.get('total_translations', 0)
            stats.cache_hits = perf.get('cache_hits', 0)
        elif self.translation_layer and hasattr(self.translation_layer, 'get_performance_stats'):
            try:
                perf = self.translation_layer.get_performance_stats()
                t_stats = perf.get('translation_stats', {})
                stats.total_translations = t_stats.get('total_translations', 0)
                stats.cache_hits = t_stats.get('cache_hits', 0)
            except Exception as e:
                self.logger.debug("Could not fetch translation performance stats: %s", e)

        return stats

    def set_ocr_engine(self, engine_name: str) -> bool:
        """
        Switch OCR engine using plugin system.

        Unloads the previously active engine first so its PyTorch models
        are freed from GPU/RAM before the new engine is loaded.
        
        Args:
            engine_name: Name of OCR engine to switch to
            
        Returns:
            True if switch successful, False otherwise
        """
        _console = logging.getLogger('optikr')
        try:
            _console.info("Switching OCR engine to: %s", engine_name)
            
            if not self.ocr_layer:
                _console.error("OCR layer not initialized")
                return False

            old_engine = self.ocr_layer.config.default_engine

            previous_config_engine = None
            if self.config_manager:
                try:
                    previous_config_engine = self.config_manager.get_setting('ocr.engine', old_engine or 'easyocr')
                    # Ensure requested engine is visible during discovery filters.
                    self.config_manager.set_setting('ocr.engine', engine_name)
                except Exception:
                    previous_config_engine = None

            if self.ocr_layer.plugin_manager.registry.get_plugin_info(engine_name) is None:
                _console.info("OCR plugin %s not in registry, rediscovering plugins…", engine_name)
                self.ocr_layer.plugin_manager.discover_plugins()
                if self.ocr_layer.plugin_manager.registry.get_plugin_info(engine_name) is None:
                    if self.config_manager and previous_config_engine:
                        self.config_manager.set_setting('ocr.engine', previous_config_engine)
                    try:
                        from app.ocr.ocr_plugin_manager import inspect_ocr_plugin_dependencies
                        exists_on_disk, missing = inspect_ocr_plugin_dependencies(engine_name)
                        if exists_on_disk and missing:
                            _console.error(
                                "Plugin %s exists but is not installable on this PC. Missing dependencies: %s",
                                engine_name,
                                ", ".join(missing),
                            )
                        elif exists_on_disk:
                            _console.error(
                                "Plugin %s exists on disk but could not be registered (manifest/import issue)",
                                engine_name,
                            )
                        else:
                            _console.error("Plugin %s still not found after rediscovery", engine_name)
                    except Exception:
                        _console.error("Plugin %s still not found after rediscovery", engine_name)
                    return False

            _console.info("Loading %s plugin…", engine_name)
            success = self.ocr_layer.plugin_manager.load_plugin(engine_name)
            
            if success:
                if old_engine and old_engine != engine_name:
                    self.logger.info("Unloading previous OCR engine: %s", old_engine)
                    self.ocr_layer.plugin_manager.unload_plugin(old_engine)

                self.ocr_layer.config.default_engine = engine_name
                self.ocr_layer.set_default_engine(engine_name)
                self._current_ocr_engine = engine_name

                if self.config_manager:
                    self.config_manager.set_setting('ocr.engine', engine_name)
                    self.config_manager.save_config()
                
                _console.info("OCR engine switched to %s", engine_name)
                return True
            else:
                if self.config_manager and previous_config_engine:
                    self.config_manager.set_setting('ocr.engine', previous_config_engine)
                _console.error("Failed to load %s plugin", engine_name)
                return False
                
        except Exception as e:
            _console.error("Error switching OCR engine: %s", e, exc_info=True)
            return False

    def set_translation_engine(self, engine_name: str) -> bool:
        """
        Switch translation engine at runtime.

        Unloads the previously active engine first so its models are
        freed from GPU/RAM before the new engine is loaded.

        Args:
            engine_name: Name of translation engine to switch to

        Returns:
            True if switch successful, False otherwise
        """
        _console = logging.getLogger('optikr')
        try:
            _console.info("Switching translation engine to: %s", engine_name)

            if not self.translation_layer:
                _console.error("Translation layer not initialized")
                return False

            old_engine = self.translation_layer._engine_mgr.default_engine
            if old_engine and old_engine != engine_name:
                self.logger.info("Unloading previous translation engine: %s", old_engine)
                self.translation_layer.unload_engine(old_engine)

            _console.info("Loading %s translation engine…", engine_name)
            success = self.translation_layer.load_engine(engine_name)

            if success:
                self.translation_layer.set_default_engine(engine_name)

                if self.config_manager:
                    self.config_manager.set_setting('translation.engine', engine_name)
                    self.config_manager.save_config()

                _console.info("Translation engine switched to %s", engine_name)
                return True
            else:
                _console.error("Failed to load %s translation engine", engine_name)
                return False

        except Exception as e:
            _console.error("Error switching translation engine: %s", e, exc_info=True)
            return False

    def set_multi_region_config(self, config):
        """
        Set multi-region configuration.

        Creates a ``MultiRegionCaptureManager`` if a capture layer exists and
        sets up callbacks for per-region frame processing.  The first enabled
        region is also stored as the primary ``capture_region`` so that the
        runtime pipeline's ``start()`` guard is satisfied.

        Args:
            config: MultiRegionConfig instance
        """
        from app.capture.multi_region_manager import create_multi_region_manager

        self.multi_region_config = config
        self.multi_region_enabled = True

        enabled_regions = config.get_enabled_regions()
        if enabled_regions:
            first_region = enabled_regions[0]
            self.capture_region = CaptureRegion(
                rectangle=first_region.rectangle,
                monitor_id=first_region.monitor_id,
            )

            if self.pipeline and hasattr(self.pipeline, 'config'):
                self.pipeline.config.capture_region = self.capture_region

            self.logger.info(
                "Set primary capture region from multi-region config: "
                f"{first_region.rectangle.width}x{first_region.rectangle.height} "
                f"at ({first_region.rectangle.x}, {first_region.rectangle.y})"
            )

        if self.capture_layer:
            self.logger.info(
                f"Creating multi-region manager with capture layer: "
                f"{type(self.capture_layer).__name__}"
            )
            self.multi_region_manager = create_multi_region_manager(
                self.capture_layer, config
            )

            if self.multi_region_manager:
                self.multi_region_manager.on_frame_captured = self._on_multi_region_frame
                self.multi_region_manager.on_capture_error = self._on_multi_region_error
                self.logger.info("Multi-region manager created and callbacks set")
            else:
                self.logger.error("Failed to create multi-region manager!")
        else:
            self.logger.error("Cannot create multi-region manager: capture_layer is None!")

        enabled_count = len(enabled_regions)
        self.logger.info(f"Multi-region mode enabled: {enabled_count} active regions")
    
    # ------------------------------------------------------------------
    # Multi-region frame processing (merged from PipelineIntegration)
    # ------------------------------------------------------------------

    def _on_multi_region_frame(self, region_id: str, frame):
        """
        Handle a frame captured by the multi-region manager.

        Runs OCR and translation on *frame*, adjusts translation
        coordinates to absolute screen positions using the region offset,
        then forwards to the translation callback / overlay system.
        """
        if not self.pipeline:
            self.logger.warning("_on_multi_region_frame called but pipeline is None")
            return

        try:
            if not hasattr(self, '_frame_count'):
                self._frame_count = 0
            self._frame_count += 1

            if self._frame_count % 30 == 1:
                self.logger.info(
                    f"[MULTI-REGION] Processing frame #{self._frame_count} from region {region_id}"
                )

            region_config = None
            if self.multi_region_config:
                for region in self.multi_region_config.regions:
                    if region.region_id == region_id:
                        region_config = region
                        break

            if not region_config:
                self.logger.warning(f"No configuration found for region {region_id}")
                return

            frame_data = {
                'frame': frame.data if hasattr(frame, 'data') else frame,
                'timestamp': frame.timestamp if hasattr(frame, 'timestamp') else 0,
                'region': CaptureRegion(
                    rectangle=region_config.rectangle,
                    monitor_id=region_config.monitor_id,
                ),
            }

            # Run OCR and translation stages directly (skip capture stage
            # since multi-region manager already provides the frame).
            stages = self.pipeline.stages
            ocr_stage = stages[1] if len(stages) > 1 else None
            translation_stage = stages[2] if len(stages) > 2 else None

            if not ocr_stage:
                self.logger.warning("Pipeline has no OCR stage for multi-region")
                return

            ocr_result = ocr_stage.execute(frame_data)
            if not ocr_result.success:
                self.logger.debug(f"No text detected in region {region_id}")
                return

            if not translation_stage:
                self.logger.warning("Pipeline has no translation stage for multi-region")
                return

            translation_result = translation_stage.execute(ocr_result.data)
            if not translation_result.success:
                self.logger.debug(f"No translations produced for region {region_id}")
                return

            translations = translation_result.data.get('translations', [])
            for translation in translations:
                if hasattr(translation, 'position') and translation.position:
                    translation.position.x += region_config.rectangle.x
                    translation.position.y += region_config.rectangle.y

            if translations:
                self._on_translation({'translations': translations})

        except Exception as e:
            self.logger.error("Error processing multi-region frame from %s: %s", region_id, e, exc_info=True)
            self.pipeline_error.emit(f"Region {region_id}: {e}")

    def _on_multi_region_error(self, region_id: str, error: str):
        """Handle capture error from the multi-region manager."""
        self.logger.error(f"Capture error for region {region_id}: {error}")
        error_msg = f"Region {region_id}: {error}"
        self.pipeline_error.emit(error_msg)

    # ------------------------------------------------------------------
    # Config restoration (absorbed from PipelineManager)
    # ------------------------------------------------------------------

    def _restore_capture_region_from_config(self) -> None:
        """Restore the capture region from saved config so the pipeline has it on startup."""
        if not self.config_manager or not self.pipeline:
            return
        try:
            region_type = self.config_manager.get_setting('capture.region', 'full_screen')
            if region_type == 'custom':
                cr = self.config_manager.get_setting('capture.custom_region', None)
                if cr and isinstance(cr, dict):
                    monitor_id = self.config_manager.get_setting('capture.monitor_index', 0)
                    self.set_capture_region(
                        x=cr.get('x', 0), y=cr.get('y', 0),
                        width=cr.get('width', 800), height=cr.get('height', 600),
                        monitor_id=monitor_id,
                    )
                    self.logger.info("Restored capture region from config: %s (monitor %s)", cr, monitor_id)

            overlay_region = self.config_manager.get_setting('overlay.region', None)
            if overlay_region and isinstance(overlay_region, dict):
                if self.pipeline and hasattr(self.pipeline, 'config'):
                    self.pipeline.config.overlay_region = overlay_region
                    self.logger.info("Restored overlay region from config: %s", overlay_region)
        except Exception as e:
            self.logger.warning("Could not restore capture region from config: %s", e)

    # ------------------------------------------------------------------
    # Pipeline callbacks -> Qt signal bridges
    # ------------------------------------------------------------------

    def _on_translation(self, data):
        """Handle translations from pipeline and display overlays.

        Integrates:
        - Intelligent positioning (collision avoidance) when configured
        - Auto-hide-on-disappear with configurable timeout
        - Stable overlay IDs based on spatial grid for cross-frame tracking

        Args:
            data: Dict with 'translations' key from BasePipeline callback.
        """
        translations = data.get('translations', []) if isinstance(data, dict) else data
        try:
            if self.overlay_system:
                # Read overlay behaviour settings
                auto_hide_on_disappear = True
                disappear_timeout = 2.0
                positioning_mode = 'intelligent'
                grid_cell_size = 50
                if self.config_manager:
                    auto_hide_on_disappear = self.config_manager.get_setting(
                        'overlay.auto_hide_on_disappear', True)
                    disappear_timeout = self.config_manager.get_setting(
                        'overlay.disappear_timeout_seconds', 2.0)
                    positioning_mode = self.config_manager.get_setting(
                        'overlay.positioning_mode', 'intelligent')
                    grid_cell_size = self.config_manager.get_setting(
                        'overlay.grid_cell_size', 50)

                # Capture region offset for coordinate conversion
                region_x, region_y = 0, 0
                capture_monitor_id = None
                if self.capture_region:
                    region_x = self.capture_region.rectangle.x
                    region_y = self.capture_region.rectangle.y
                    capture_monitor_id = self.capture_region.monitor_id

                # --- Phase 1: compute absolute screen positions ---------------
                text_blocks = (
                    data.get('text_blocks', []) if isinstance(data, dict) else []
                )

                # Determine the coordinate space of OCR positions.
                # When preprocessing downscales the frame, OCR coords are
                # relative to the *processed* (smaller) image, not the
                # original capture region.  We need the processed frame
                # dimensions to scale correctly into screen space.
                #
                # We lock the reference size after the first successful
                # frame so that subsequent frames (which may have a
                # different preprocessed size due to the overlay-capture
                # feedback loop) still produce the same screen positions.
                ocr_frame_w, ocr_frame_h = 0, 0
                frame_obj = data.get('frame') if isinstance(data, dict) else None
                if frame_obj is not None:
                    meta = getattr(frame_obj, 'metadata', None) or {}
                    processed_shape = meta.get('processed_shape')
                    if processed_shape is not None and len(processed_shape) >= 2:
                        ocr_frame_h, ocr_frame_w = processed_shape[0], processed_shape[1]
                    else:
                        # Vision pipeline (no preprocessing): use raw frame shape
                        # so overlay reference matches the image vision bbox is in.
                        raw = getattr(frame_obj, 'data', frame_obj)
                        if hasattr(raw, 'shape') and len(getattr(raw, 'shape', ())) >= 2:
                            ocr_frame_h, ocr_frame_w = int(raw.shape[0]), int(raw.shape[1])

                if ocr_frame_w > 0 and ocr_frame_h > 0:
                    if self._ocr_ref_size is None:
                        # First frame — lock the reference dimensions.
                        self._ocr_ref_size = (ocr_frame_w, ocr_frame_h)
                        self.logger.info(
                            "OCR reference size locked: %dx%d",
                            ocr_frame_w, ocr_frame_h,
                        )
                    elif (ocr_frame_w, ocr_frame_h) != self._ocr_ref_size:
                        self.logger.debug(
                            "OCR frame size changed %dx%d -> %dx%d, "
                            "using locked reference %dx%d",
                            self._ocr_ref_size[0], self._ocr_ref_size[1],
                            ocr_frame_w, ocr_frame_h,
                            self._ocr_ref_size[0], self._ocr_ref_size[1],
                        )

                positioned = []
                for i, translation in enumerate(translations):
                    pos = self._resolve_position(translation, text_blocks, i)

                    if hasattr(translation, 'position') and translation.position is not None:
                        pos_source = 'translation.position'
                    elif i < len(text_blocks) and getattr(text_blocks[i], 'position', None) is not None:
                        pos_source = f'text_blocks[{i}].position'
                    else:
                        pos_source = 'None'

                    ocr_x = getattr(pos, 'x', 0) if pos else 0
                    ocr_y = getattr(pos, 'y', 0) if pos else 0
                    pos_w = getattr(pos, 'width', 0) if pos else 0
                    pos_h = getattr(pos, 'height', 0) if pos else 0

                    self.logger.debug(
                        "Translation[%d] pos_source=%s ocr_relative=(%d,%d,%d,%d)",
                        i, pos_source, ocr_x, ocr_y, pos_w, pos_h,
                    )

                    # Scale OCR coords from frame pixel space to the
                    # capture region's logical screen space.  The captured
                    # frame may differ in resolution from the logical region
                    # (e.g. due to DPI scaling), so we normalise by the
                    # reference frame size and map into the capture region.
                    if self._ocr_ref_size is not None:
                        ref_w, ref_h = self._ocr_ref_size
                    elif ocr_frame_w > 0 and ocr_frame_h > 0:
                        ref_w, ref_h = ocr_frame_w, ocr_frame_h
                    else:
                        ref_w, ref_h = 0, 0

                    cap_w = self.capture_region.rectangle.width if self.capture_region else 0
                    cap_h = self.capture_region.rectangle.height if self.capture_region else 0

                    if ref_w > 0 and ref_h > 0 and cap_w > 0 and cap_h > 0:
                        abs_x = int(region_x + (ocr_x / ref_w) * cap_w)
                        abs_y = int(region_y + (ocr_y / ref_h) * cap_h)
                    else:
                        abs_x = region_x + ocr_x
                        abs_y = region_y + ocr_y

                    if cap_w > 0 and cap_h > 0:
                        clamp_w = max(pos_w, 50)
                        clamp_h = max(pos_h, 30)
                        abs_x = max(region_x, min(abs_x, region_x + cap_w - clamp_w))
                        abs_y = max(region_y, min(abs_y, region_y + cap_h - clamp_h))

                    self.logger.debug(
                        "Translation[%d] screen_pos=(%d,%d) region=(%d,%d,%dx%d) ref=%dx%d",
                        i, abs_x, abs_y, region_x, region_y, cap_w, cap_h, ref_w, ref_h,
                    )

                    text = translation.translated_text if hasattr(translation, 'translated_text') else str(translation)
                    positioned.append((translation, text, abs_x, abs_y, ocr_x, ocr_y))

                # --- Phase 2: intelligent positioning (collision avoidance) ---
                if (positioning_mode == 'intelligent'
                        and self._positioning_engine
                        and len(positioned) > 1):
                    cap_bounds = None
                    if self.capture_region:
                        r = self.capture_region.rectangle
                        cap_bounds = {'x': r.x, 'y': r.y,
                                      'width': r.width, 'height': r.height}
                    positioned = self._apply_intelligent_positions(
                        positioned, cap_bounds, text_blocks,
                    )

                # --- Phase 3: show overlays with stable IDs -------------------
                # Build IDs from OCR-relative positions (the coordinates
                # in the preprocessed frame).  These are far more stable
                # across frames than the final screen-mapped positions
                # because small capture/preprocessing jitter doesn't get
                # amplified by the overlay-region scaling factor.
                stable_cell = max(grid_cell_size * 2, 80)
                now = time.monotonic()
                current_ids: set[str] = set()

                for entry in positioned:
                    if len(entry) == 6:
                        translation, text, x, y, ocr_id_x, ocr_id_y = entry
                    else:
                        # Fallback (e.g. from _apply_intelligent_positions)
                        translation, text, x, y = entry[:4]
                        ocr_id_x, ocr_id_y = x, y

                    overlay_id = f"tr_{ocr_id_x // stable_cell}_{ocr_id_y // stable_cell}"
                    base_id = overlay_id
                    suffix = 0
                    while overlay_id in current_ids:
                        suffix += 1
                        overlay_id = f"{base_id}_{suffix}"
                    current_ids.add(overlay_id)
                    self._overlay_last_seen[overlay_id] = now
                    self.logger.info(
                        "[Overlay] '%s' at screen(%d, %d)  id=%s",
                        text[:50], x, y, overlay_id,
                    )
                    self.overlay_system.show_translation(
                        text, (x, y), translation_id=overlay_id,
                        monitor_id=capture_monitor_id)

                # --- Phase 4: manage stale overlays ---------------------------
                if auto_hide_on_disappear:
                    stale = [
                        oid for oid, last_seen in self._overlay_last_seen.items()
                        if oid not in current_ids and (now - last_seen) >= disappear_timeout
                    ]
                    if stale:
                        self.logger.debug(
                            "Hiding %d stale overlays (timeout=%.1fs): %s",
                            len(stale), disappear_timeout, stale,
                        )
                    for oid in stale:
                        self.overlay_system.hide_translation(oid)
                        del self._overlay_last_seen[oid]
                else:
                    gone = [oid for oid in self._overlay_last_seen if oid not in current_ids]
                    if gone:
                        self.logger.debug(
                            "Hiding %d disappeared overlays (auto_hide off): %s",
                            len(gone), gone,
                        )
                    for oid in gone:
                        self.overlay_system.hide_translation(oid)
                        del self._overlay_last_seen[oid]

                self._active_overlay_ids = current_ids
                self.logger.debug("Displayed %d overlays", len(positioned))
            else:
                self.logger.warning("No overlay system available")

            try:
                self.translation_received.emit({'translations': translations})
            except Exception as e:
                self.logger.debug("Could not emit translation_received signal: %s", e)

        except Exception as e:
            self.logger.error("Error in translation callback: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # Position resolution helper
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_position(translation, text_blocks, index):
        """Resolve the spatial position for a translation result.

        Translation objects (e.g. ``_DictionaryTranslation``) carry their
        own ``.position`` attribute.  Plain strings returned by the
        translation engine do not -- in that case fall back to the
        corresponding ``TextBlock`` from the OCR stage.

        Handles both ``TextBlock`` objects (with ``.position`` as a
        ``Rectangle``) and normalised dicts produced by post-processors
        like ``TextBlockMerger`` (with ``'bbox'`` or ``'position'`` keys).
        Returns a ``Rectangle`` or ``None``.
        """
        from app.models import Rectangle as _Rect

        def _to_rect(raw):
            """Coerce *raw* into a Rectangle if possible."""
            if raw is None:
                return None
            if isinstance(raw, _Rect):
                return raw
            if isinstance(raw, (list, tuple)) and len(raw) >= 4:
                return _Rect(x=int(raw[0]), y=int(raw[1]),
                             width=int(raw[2]), height=int(raw[3]))
            if isinstance(raw, dict):
                if 'x' in raw and 'y' in raw:
                    return _Rect(
                        x=int(raw.get('x', 0)), y=int(raw.get('y', 0)),
                        width=int(raw.get('width', 0)),
                        height=int(raw.get('height', 0)),
                    )
            # Object with .x / .y attributes (e.g. Rectangle-like)
            x = getattr(raw, 'x', None)
            y = getattr(raw, 'y', None)
            if x is not None and y is not None:
                return _Rect(
                    x=int(x), y=int(y),
                    width=int(getattr(raw, 'width', 0)),
                    height=int(getattr(raw, 'height', 0)),
                )
            return None

        # 1. Translation object's own position
        if hasattr(translation, 'position') and translation.position is not None:
            return _to_rect(translation.position)

        # 2. Corresponding text block
        if index < len(text_blocks):
            block = text_blocks[index]
            if isinstance(block, dict):
                # Normalised dict from TextBlockMerger / other post-processors
                raw = block.get('position') or block.get('bbox')
                rect = _to_rect(raw)
                if rect is not None:
                    return rect
            else:
                pos = getattr(block, 'position', None)
                rect = _to_rect(pos)
                if rect is not None:
                    return rect

        return None

    # ------------------------------------------------------------------
    # Intelligent positioning helper
    # ------------------------------------------------------------------

    def _apply_intelligent_positions(self, positioned, overlay_region=None,
                                     text_blocks=None):
        """Run translations through IntelligentPositioningEngine for collision avoidance.

        Args:
            positioned: List of (translation, text, abs_x, abs_y, ocr_x, ocr_y) tuples.
            overlay_region: Optional overlay region dict constraining bounds.
            text_blocks: OCR text blocks carrying position/size from detection.

        Returns:
            Updated list with adjusted positions (preserving ocr_x/ocr_y for ID generation).
        """
        if text_blocks is None:
            text_blocks = []
        try:
            if overlay_region and self._positioning_engine:
                self._positioning_engine.overlay_region = overlay_region

            abs_translations = []
            for i, entry in enumerate(positioned):
                if len(entry) == 6:
                    translation, text, abs_x, abs_y, ocr_id_x, ocr_id_y = entry
                else:
                    translation, text, abs_x, abs_y = entry[:4]
                    ocr_id_x, ocr_id_y = abs_x, abs_y

                pos = self._resolve_position(translation, text_blocks, i)
                w = getattr(pos, 'width', 0) if pos else 0
                h = getattr(pos, 'height', 0) if pos else 0
                if w <= 0:
                    w = min(len(text) * 12, 600)
                if h <= 0:
                    h = 30

                abs_trans = Translation(
                    original_text=getattr(translation, 'original_text', text) or text,
                    translated_text=text,
                    source_language=getattr(translation, 'source_language', 'ja'),
                    target_language=getattr(translation, 'target_language', 'en'),
                    position=Rectangle(x=abs_x, y=abs_y, width=w, height=h),
                    confidence=getattr(translation, 'confidence', 0.9),
                    engine_used=getattr(translation, 'engine_used', ''),
                )
                abs_translations.append((abs_trans, translation, text, ocr_id_x, ocr_id_y))

            adjusted = self._positioning_engine.calculate_optimal_positions(
                [t for t, _, _, _, _ in abs_translations],
                mode=PositioningMode.INTELLIGENT,
            )

            result = []
            for adj, (abs_trans, orig, text, ocr_id_x, ocr_id_y) in zip(adjusted, abs_translations):
                orig_x, orig_y = abs_trans.position.x, abs_trans.position.y
                adj_x, adj_y = adj.position.x, adj.position.y
                if orig_x != adj_x or orig_y != adj_y:
                    self.logger.debug(
                        "Intelligent positioning moved overlay: (%d,%d) -> (%d,%d) text=%.50s",
                        orig_x, orig_y, adj_x, adj_y, text,
                    )
                result.append((orig, text, adj_x, adj_y, ocr_id_x, ocr_id_y))
            return result
        except Exception as e:
            self.logger.warning("Intelligent positioning failed, using original positions: %s", e)
            return positioned
    
    def _on_error(self, error: str):
        """Handle errors from pipeline — bridges to ``pipeline_error`` signal."""
        self.pipeline_error.emit(str(error))
    
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
        Get the currently active/loaded OCR engine or pipeline mode.

        When pipeline.mode is "vision", returns "vision" so the UI can show
        "Vision" instead of "Unknown" (no OCR engine is loaded in vision mode).

        Returns:
            Name of the currently loaded OCR engine, 'vision' when in vision
            mode, or 'unknown' if none loaded.
        """
        if self.config_manager:
            pipeline_mode = self.config_manager.get_setting("pipeline.mode", "text")
            if pipeline_mode == "vision":
                return "vision"
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

    def warm_up_components(self):
        """
        Warm up components with dummy translation.
        Makes first real translation much faster by pre-loading models.
        """
        try:
            self.logger.info("Running component warm-up...")
            
            import numpy as np
            dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
            from app.models import Frame, CaptureRegion, Rectangle
            
            dummy_region = CaptureRegion(
                rectangle=Rectangle(x=0, y=0, width=100, height=100),
                monitor_id=0
            )
            
            dummy_frame = Frame(data=dummy_image, timestamp=0.001, source_region=dummy_region)
            
            if self.ocr_layer:
                try:
                    text_blocks = self.ocr_layer.extract_text(dummy_frame)
                    self.logger.info("OCR layer warmed up")
                except Exception as e:
                    self.logger.debug("OCR warm-up skipped: %s", e)

            if self.translation_layer:
                source_lang = "ja"
                target_lang = "en"
                if self.config_manager:
                    source_lang = self.config_manager.get_setting(
                        "translation.source_language", "ja"
                    )
                    target_lang = self.config_manager.get_setting(
                        "translation.target_language", "en"
                    )
                try:
                    if hasattr(self.translation_layer, "preload_models"):
                        if self.translation_layer.preload_models(source_lang, target_lang):
                            self.logger.info("Translation layer warmed up")
                        else:
                            self.logger.debug("Translation preload not required or failed")
                    else:
                        self.logger.debug("Translation warm-up skipped (no preload_models)")
                except Exception as e:
                    self.logger.debug("Translation warm-up skipped: %s", e)

            self.logger.info("Components ready - first translation will be fast!")
            
        except Exception as e:
            self.logger.warning("Warm-up failed: %s", e, exc_info=True)
    
