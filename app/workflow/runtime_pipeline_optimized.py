"""
Optimized Runtime Translation Pipeline with Plugin Support

Enhanced version of RuntimePipeline that supports optimizer plugins.
Loads and applies optimizer plugins for improved performance.

Author: Niklas Verhasselt
Date: 2025-11-12
"""

import time
import threading
import logging
import json
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

try:
    from app.models import Frame, CaptureRegion, Rectangle
    from app.interfaces import CaptureSource
except ImportError:
    from models import Frame, CaptureRegion, Rectangle
    from interfaces import CaptureSource


@dataclass
class OptimizedRuntimePipelineConfig:
    """Configuration for optimized runtime translation pipeline."""
    capture_region: Optional[CaptureRegion] = None
    fps: int = 10
    source_language: str = "ja"
    target_language: str = "de"
    enable_plugins: bool = True  # Always True (plugin system enabled)
    load_all_plugins: bool = True  # If False, only load essential plugins
    plugins_dir: str = "plugins/optimizers"


class TextProcessorPluginLoader:
    """Loads and manages text processor plugins."""
    
    def __init__(self, plugins_dir: str):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def load_plugins(self) -> Dict[str, Any]:
        """Load all text processor plugins from directory."""
        if not self.plugins_dir.exists():
            self.logger.warning(f"Text processor plugins directory not found: {self.plugins_dir}")
            return {}
        
        loaded_count = 0
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            plugin_json = plugin_dir / "plugin.json"
            processor_py = plugin_dir / "processor.py"
            
            if not plugin_json.exists() or not processor_py.exists():
                continue
            
            try:
                # Load plugin metadata
                with open(plugin_json, 'r') as f:
                    metadata = json.load(f)
                
                # Check if enabled
                if not metadata.get('enabled', True):
                    self.logger.info(f"Text processor plugin {metadata['name']} is disabled")
                    continue
                
                # Load processor module
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"processor_{metadata['name']}", 
                    processor_py
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Initialize processor
                settings = metadata.get('settings', {})
                config = {k: v.get('default') for k, v in settings.items()}
                processor = module.initialize(config)
                
                self.plugins[metadata['name']] = {
                    'metadata': metadata,
                    'processor': processor,
                    'config': config
                }
                
                loaded_count += 1
                self.logger.info(f"Loaded text processor plugin: {metadata['display_name']}")
                
            except Exception as e:
                self.logger.error(f"Failed to load text processor plugin {plugin_dir.name}: {e}")
        
        self.logger.info(f"Loaded {loaded_count} text processor plugins")
        return self.plugins
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """Get processor by name."""
        plugin = self.plugins.get(name)
        return plugin['processor'] if plugin else None


class OptimizerPluginLoader:
    """Loads and manages optimizer plugins."""
    
    def __init__(self, plugins_dir: str, config_manager=None):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
    
    def load_plugins(self, enable_all: bool = True) -> Dict[str, Any]:
        """
        Load optimizer plugins from directory.
        
        Args:
            enable_all: If True, load all enabled plugins. If False, only load essential plugins.
        """
        if not self.plugins_dir.exists():
            self.logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return {}
        
        loaded_count = 0
        skipped_count = 0
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            plugin_json = plugin_dir / "plugin.json"
            optimizer_py = plugin_dir / "optimizer.py"
            
            if not plugin_json.exists() or not optimizer_py.exists():
                continue
            
            try:
                # Load plugin metadata with UTF-8 encoding
                with open(plugin_json, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check if enabled
                if not metadata.get('enabled', True):
                    self.logger.info(f"Plugin {metadata['name']} is disabled")
                    continue
                
                # Check if essential (always load) or optional (only load if enable_all=True)
                is_essential = metadata.get('essential', False)
                if not enable_all and not is_essential:
                    self.logger.info(f"Plugin {metadata['name']} skipped (not essential)")
                    skipped_count += 1
                    continue
                
                # Load optimizer module
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"optimizer_{metadata['name']}", 
                    optimizer_py
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Initialize optimizer
                settings = metadata.get('settings', {})
                config = {k: v.get('default') for k, v in settings.items()}
                
                # Pass runtime_mode from config_manager to plugins
                if hasattr(self, 'config_manager') and self.config_manager:
                    runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
                    config['runtime_mode'] = runtime_mode
                
                optimizer = module.initialize(config)
                
                self.plugins[metadata['name']] = {
                    'metadata': metadata,
                    'optimizer': optimizer,
                    'config': config
                }
                
                loaded_count += 1
                essential_tag = " (essential)" if is_essential else ""
                self.logger.info(f"Loaded optimizer plugin: {metadata['display_name']}{essential_tag}")
                
            except Exception as e:
                self.logger.error(f"Failed to load plugin {plugin_dir.name}: {e}")
                print(f"Failed to load plugin {plugin_dir.name}: {e}")
                import traceback
                traceback.print_exc()
        
        if skipped_count > 0:
            self.logger.info(f"Loaded {loaded_count} optimizer plugins ({skipped_count} optional plugins skipped)")
        else:
            self.logger.info(f"Loaded {loaded_count} optimizer plugins")
        return self.plugins
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """Get optimizer by name."""
        plugin = self.plugins.get(name)
        return plugin['optimizer'] if plugin else None


class OptimizedRuntimePipeline:
    """
    Optimized Runtime Translation Pipeline with Plugin Support.
    
    Enhances the basic RuntimePipeline with:
    - Optimizer plugin loading
    - Frame skip optimization
    - Translation cache
    - Batch processing
    - Performance metrics
    """
    
    def __init__(self, capture_layer, ocr_layer, translation_layer, 
                 config: OptimizedRuntimePipelineConfig, overlay_system=None, config_manager=None, cache_manager=None):
        """Initialize optimized runtime pipeline."""
        self.capture_layer = capture_layer
        self.ocr_layer = ocr_layer
        self.translation_layer = translation_layer
        self.config = config
        self.overlay_system = overlay_system
        self.config_manager = config_manager
        self.cache_manager = cache_manager  # NEW: PipelineCacheManager with persistent dictionary
        self.active_overlays = []  # Track active overlays for positioning system
        
        self.logger = logging.getLogger(__name__)
        
        # Enable debug mode and performance monitoring if configured
        self.debug_mode = False
        self.performance_monitoring = False
        if config_manager:
            self.debug_mode = config_manager.get_setting('advanced.debug_mode', False)
            self.performance_monitoring = config_manager.get_setting('advanced.enable_monitoring', False)
            
            if self.debug_mode:
                self.logger.setLevel(logging.DEBUG)
                print("[DEBUG MODE] ✓ Enabled in runtime pipeline")
            
            if self.performance_monitoring:
                print("[PERFORMANCE MONITORING] ✓ Enabled - Metrics will be tracked")
                self._init_performance_tracker()
        
        # Load text processor plugins (always load - they're essential)
        print("[OPTIMIZED PIPELINE] Loading text processor plugins...")
        self.text_processor_loader = TextProcessorPluginLoader("plugins/text_processors")
        self.text_processors = {}
        # Always load text processors (spell checker is essential)
        self.text_processors = self.text_processor_loader.load_plugins()
        print(f"[OPTIMIZED PIPELINE] Loaded {len(self.text_processors)} text processor plugins")
        
        # Get spell corrector plugin
        self.spell_corrector = self.text_processor_loader.get_plugin('spell_corrector')
        if self.spell_corrector:
            # Connect persistent dictionary (SmartDictionary)
            try:
                if hasattr(self, 'cache_manager') and self.cache_manager and self.cache_manager.persistent_dictionary:
                    self.spell_corrector.set_dictionary_engine(self.cache_manager.persistent_dictionary)
                    print("[OPTIMIZED PIPELINE] Spell corrector connected to persistent dictionary")
                else:
                    print("[OPTIMIZED PIPELINE] Warning: Persistent dictionary not available for spell corrector")
            except Exception as e:
                print(f"[OPTIMIZED PIPELINE] Warning: Could not connect spell corrector to dictionary: {e}")
            print("[OPTIMIZED PIPELINE] Spell corrector plugin loaded")
        else:
            print("[OPTIMIZED PIPELINE] Spell corrector plugin not available")
        
        # Load optimizer plugins
        print("[OPTIMIZED PIPELINE] Creating plugin loader...")
        self.plugin_loader = OptimizerPluginLoader(config.plugins_dir, config_manager=self.config_manager)
        self.plugins = {}
        if config.enable_plugins:
            if config.load_all_plugins:
                print("[OPTIMIZED PIPELINE] Loading all plugins (essential + optional)...")
                self.plugins = self.plugin_loader.load_plugins(enable_all=True)
                print(f"[OPTIMIZED PIPELINE] Loaded {len(self.plugins)} plugins")
                print(f"[DEBUG] Plugin names: {list(self.plugins.keys())}")
            else:
                print("[OPTIMIZED PIPELINE] Loading essential plugins only...")
                self.plugins = self.plugin_loader.load_plugins(enable_all=False)
                print(f"[OPTIMIZED PIPELINE] Loaded {len(self.plugins)} essential plugins")
                if self.plugins:
                    print(f"[ESSENTIAL PLUGINS] {', '.join(self.plugins.keys())}")
        else:
            print("[OPTIMIZED PIPELINE] Plugin system disabled (not recommended)")
        
        # Get specific optimizers
        print("[OPTIMIZED PIPELINE] Getting frame_skip plugin...")
        self.frame_skip = self.plugin_loader.get_plugin('frame_skip')
        print(f"[DEBUG] Frame skip loaded: {self.frame_skip is not None}")
        print("[OPTIMIZED PIPELINE] Getting translation_cache plugin...")
        self.translation_cache = self.plugin_loader.get_plugin('translation_cache')
        print(f"[DEBUG] Translation cache loaded: {self.translation_cache is not None}")
        print("[OPTIMIZED PIPELINE] Getting motion_tracker plugin...")
        self.motion_tracker = self.plugin_loader.get_plugin('motion_tracker')
        print(f"[DEBUG] Motion tracker loaded: {self.motion_tracker is not None}")
        print("[OPTIMIZED PIPELINE] Getting text_block_merger plugin...")
        self.text_block_merger = self.plugin_loader.get_plugin('text_block_merger')
        print(f"[DEBUG] Text block merger loaded: {self.text_block_merger is not None}")
        print("[OPTIMIZED PIPELINE] Getting text_validator plugin...")
        self.text_validator_plugin = self.plugin_loader.get_plugin('text_validator')
        print(f"[DEBUG] Text validator plugin loaded: {self.text_validator_plugin is not None}")
        
        # Get async_pipeline plugin (NEW - Phase 2)
        print("[OPTIMIZED PIPELINE] Getting async_pipeline plugin...")
        self.async_pipeline = self.plugin_loader.get_plugin('async_pipeline')
        print(f"[DEBUG] Async pipeline loaded: {self.async_pipeline is not None}")
        
        # Get parallel_translation plugin (NEW - Phase 2, wired but disabled)
        print("[OPTIMIZED PIPELINE] Getting parallel_translation plugin...")
        self.parallel_translation = self.plugin_loader.get_plugin('parallel_translation')
        print(f"[DEBUG] Parallel translation loaded: {self.parallel_translation is not None}")
        
        # Warm start parallel translation in background (if enabled)
        if self.parallel_translation:
            print("[OPTIMIZED PIPELINE] Scheduling parallel translation warm start...")
            self._schedule_parallel_translation_warmup()
        
        print("[OPTIMIZED PIPELINE] Plugins loaded")
        
        # Load and apply plugin configurations from config manager
        self._apply_plugin_configurations()
        
        # Dictionary engine is managed by translation_layer
        print("[OPTIMIZED PIPELINE] Using dictionary engine from translation layer...")
        
        # Ensure dictionary file exists for current language pair
        self._ensure_dictionary_exists()
        
        # Initialize smart positioning system
        print("[OPTIMIZED PIPELINE] Initializing positioning system...")
        self.positioning_system = None
        try:
            from app.overlay.automatic_positioning import (
                AutomaticPositioningSystem, AutomaticPositioningConfig,
                PositioningStrategy, WrappingStrategy
            )
            
            pos_config = AutomaticPositioningConfig()
            pos_config.positioning_strategy = PositioningStrategy.SMART_PLACEMENT
            pos_config.text_sizing.adaptive_scaling = True
            pos_config.text_sizing.content_aware_sizing = True
            pos_config.wrapping.strategy = WrappingStrategy.INTELLIGENT_WRAP
            pos_config.collision_detection.enabled = True
            pos_config.dynamic_adaptation.movement_tracking = True
            
            self.positioning_system = AutomaticPositioningSystem(pos_config)
            self.active_overlays = []
            self.logger.info("Smart positioning system initialized")
            print("[OPTIMIZED PIPELINE] Positioning system initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize positioning system: {e}")
            print(f"[OPTIMIZED PIPELINE] Positioning system failed: {e}")
        
        # Initialize overlay tracker for auto-hide functionality
        print("[OPTIMIZED PIPELINE] Initializing overlay tracker...")
        self.overlay_tracker = None
        try:
            from app.workflow.overlay_tracker import OverlayTracker
            # Get disappear timeout from config (default 2.0 seconds)
            disappear_timeout = 2.0
            if self.config_manager:
                disappear_timeout = self.config_manager.get_setting('overlay.disappear_timeout', 2.0)
            self.overlay_tracker = OverlayTracker(disappear_threshold=disappear_timeout)
            self.logger.info(f"Overlay tracker initialized (disappear_timeout={disappear_timeout}s)")
            print(f"[OPTIMIZED PIPELINE] Overlay tracker initialized (disappear after {disappear_timeout}s)")
        except Exception as e:
            self.logger.warning(f"Failed to initialize overlay tracker: {e}")
            print(f"[OPTIMIZED PIPELINE] Overlay tracker failed: {e}")
        
        # State
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.on_translation: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Text validator is now loaded as an essential plugin (see self.text_validator_plugin above)
        
        # Stats
        self.frames_processed = 0
        self.frames_skipped = 0
        self.frames_dropped = 0
        self.translations_count = 0
        self.cache_hits = 0
        self.dictionary_hits = 0
        self.validator_filtered = 0
        
        # Overlay position tracking (to prevent OCR feedback loop)
        self.active_overlay_positions = []  # List of (x, y, width, height) tuples
        self.overlay_position_lock = threading.Lock()
        
        # Auto-save configuration
        self.save_interval = 5  # Save dictionary every 5 translations (for testing - change to 100 for production)
        self.translations_since_save = 0
        
        self.logger.info(f"Optimized runtime pipeline initialized with {len(self.plugins)} plugins")
    
    def _init_performance_tracker(self):
        """Initialize performance monitoring tracker."""
        self.perf_metrics = {
            'capture_times': [],
            'ocr_times': [],
            'translation_times': [],
            'overlay_times': [],
            'total_frame_times': [],
            'frames_processed': 0,
            'frames_skipped': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        print("[PERFORMANCE] Performance tracker initialized")
    
    def _log_performance_metric(self, metric_name, value):
        """Log a performance metric if monitoring is enabled."""
        if not self.performance_monitoring:
            return
        
        if metric_name in self.perf_metrics and isinstance(self.perf_metrics[metric_name], list):
            self.perf_metrics[metric_name].append(value)
            
            # Print every 10 frames
            if len(self.perf_metrics[metric_name]) % 10 == 0:
                avg = sum(self.perf_metrics[metric_name][-10:]) / 10
                print(f"[PERF] {metric_name}: {avg:.2f}ms (avg last 10)")
    
    def _apply_plugin_configurations(self):
        """Load and apply plugin configurations from config manager."""
        if not self.config_manager:
            print("[PLUGIN CONFIG] No config manager, using default plugin settings")
            return
        
        print("[PLUGIN CONFIG] Applying plugin configurations from settings...")
        
        # Motion Tracker Plugin Configuration
        if self.motion_tracker:
            motion_enabled = self.config_manager.get_setting('pipeline.plugins.motion_tracker.enabled', True)
            if motion_enabled:
                threshold = self.config_manager.get_setting('pipeline.plugins.motion_tracker.threshold', 0.3)
                smoothing = self.config_manager.get_setting('pipeline.plugins.motion_tracker.smoothing', 0.5)
                
                if hasattr(self.motion_tracker, 'configure'):
                    self.motion_tracker.configure({'threshold': threshold, 'smoothing': smoothing})
                    print(f"[PLUGIN CONFIG] Motion Tracker: threshold={threshold}, smoothing={smoothing}")
                else:
                    print("[PLUGIN CONFIG] Motion Tracker: No configure method available")
            else:
                print("[PLUGIN CONFIG] Motion Tracker: Disabled by user")
                self.motion_tracker = None
        
        # Intelligent Text Processor Plugin Configuration (ESSENTIAL)
        if hasattr(self, 'plugins') and 'intelligent_text_processor' in self.plugins:
            processor_plugin = self.plugins['intelligent_text_processor']
            processor = processor_plugin.get('processor') if isinstance(processor_plugin, dict) else None
            
            if processor:
                min_conf = self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.min_confidence', 0.55)
                min_word_len = self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.min_word_length', 3)
                enable_corrections = self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enable_corrections', True)
                enable_context = self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enable_context', True)
                enable_validation = self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enable_validation', True)
                
                if hasattr(processor, 'configure'):
                    processor.configure({
                        'min_confidence': min_conf,
                        'min_word_length': min_word_len,
                        'enable_corrections': enable_corrections,
                        'enable_context': enable_context,
                        'enable_validation': enable_validation
                    })
                    print(f"[PLUGIN CONFIG] Intelligent Text Processor: min_conf={min_conf}, min_word_len={min_word_len}")
                elif hasattr(processor, 'min_confidence'):
                    # Direct attribute setting if no configure method
                    processor.min_confidence = min_conf
                    if hasattr(processor, 'config'):
                        processor.config['min_confidence'] = min_conf
                        processor.config['min_word_length'] = min_word_len
                    print(f"[PLUGIN CONFIG] Intelligent Text Processor: min_conf={min_conf}, min_word_len={min_word_len} (direct)")
                else:
                    print("[PLUGIN CONFIG] Intelligent Text Processor: No configure method available")
        
        # Spell Corrector Plugin Configuration
        if self.spell_corrector:
            spell_enabled = self.config_manager.get_setting('pipeline.plugins.spell_corrector.enabled', True)
            if spell_enabled:
                aggressive = self.config_manager.get_setting('pipeline.plugins.spell_corrector.aggressive_mode', False)
                fix_caps = self.config_manager.get_setting('pipeline.plugins.spell_corrector.fix_capitalization', True)
                min_conf = self.config_manager.get_setting('pipeline.plugins.spell_corrector.min_confidence', 0.7)
                
                if hasattr(self.spell_corrector, 'configure'):
                    self.spell_corrector.configure({
                        'aggressive_mode': aggressive,
                        'fix_capitalization': fix_caps,
                        'min_confidence': min_conf
                    })
                    print(f"[PLUGIN CONFIG] Spell Corrector: aggressive={aggressive}, fix_caps={fix_caps}, min_conf={min_conf}")
                else:
                    print("[PLUGIN CONFIG] Spell Corrector: No configure method available")
            else:
                print("[PLUGIN CONFIG] Spell Corrector: Disabled by user")
                self.spell_corrector = None
        
        # Text Block Merger Plugin Configuration
        if self.text_block_merger:
            merger_enabled = self.config_manager.get_setting('pipeline.plugins.text_block_merger.enabled', True)
            if not merger_enabled:
                print("[PLUGIN CONFIG] Text Block Merger: Disabled by user")
                self.text_block_merger = None
            else:
                h_threshold = self.config_manager.get_setting('pipeline.plugins.text_block_merger.horizontal_threshold', 50)
                v_threshold = self.config_manager.get_setting('pipeline.plugins.text_block_merger.vertical_threshold', 30)
                strategy = self.config_manager.get_setting('pipeline.plugins.text_block_merger.merge_strategy', 'smart')
                
                if hasattr(self.text_block_merger, 'configure'):
                    self.text_block_merger.configure({
                        'horizontal_threshold': h_threshold,
                        'vertical_threshold': v_threshold,
                        'merge_strategy': strategy
                    })
                    print(f"[PLUGIN CONFIG] Text Block Merger: h={h_threshold}px, v={v_threshold}px, strategy={strategy}")
                else:
                    print("[PLUGIN CONFIG] Text Block Merger: No configure method available")
        
        # Text Validator Plugin Configuration
        if self.text_validator_plugin:
            min_conf = self.config_manager.get_setting('pipeline.plugins.text_validator.min_confidence', 0.5)
            smart_grammar = self.config_manager.get_setting('pipeline.plugins.text_validator.enable_smart_grammar', False)
            
            if hasattr(self.text_validator_plugin, 'configure'):
                self.text_validator_plugin.configure({
                    'min_confidence': min_conf,
                    'enable_smart_grammar': smart_grammar
                })
                print(f"[PLUGIN CONFIG] Text Validator: min_conf={min_conf}, smart_grammar={smart_grammar}")
            else:
                print("[PLUGIN CONFIG] Text Validator: No configure method available")
        
        # Translation Chain Plugin Configuration
        chain_enabled = self.config_manager.get_setting('pipeline.plugins.translation_chain.enabled', False)
        if chain_enabled:
            intermediate_lang = self.config_manager.get_setting('pipeline.plugins.translation_chain.intermediate_language', 'en')
            print(f"[PLUGIN CONFIG] Translation Chain: enabled, intermediate_lang={intermediate_lang}")
            # Note: Translation chain would need to be implemented in translation layer
        
        # Parallel Capture Configuration
        parallel_capture_enabled = self.config_manager.get_setting('pipeline.parallel_capture.enabled', False)
        if parallel_capture_enabled:
            workers = self.config_manager.get_setting('pipeline.parallel_capture.workers', 2)
            print(f"[PLUGIN CONFIG] Parallel Capture: enabled, workers={workers}")
            # Note: Would need to configure capture layer for parallel processing
        
        # Parallel Translation Configuration
        if self.parallel_translation:
            parallel_trans_enabled = self.config_manager.get_setting('pipeline.parallel_translation.enabled', False)
            if parallel_trans_enabled:
                workers = self.config_manager.get_setting('pipeline.parallel_translation.workers', 2)
                if hasattr(self.parallel_translation, 'configure'):
                    self.parallel_translation.configure({'workers': workers})
                    print(f"[PLUGIN CONFIG] Parallel Translation: enabled, workers={workers}")
            else:
                print("[PLUGIN CONFIG] Parallel Translation: Disabled by user")
                self.parallel_translation = None
        
        print("[PLUGIN CONFIG] Plugin configurations applied")
    
    def _schedule_parallel_translation_warmup(self):
        """
        Schedule parallel translation warm start in background thread.
        This pre-loads translation models without blocking pipeline initialization.
        
        IMPORTANT: This actually loads the MarianMT model in the subprocess,
        not just cache/dictionary lookups.
        """
        def warmup_worker():
            try:
                print("[WARMUP] Starting parallel translation warm start in background...")
                print("[WARMUP] This will load the MarianMT model (5-10 seconds)...")
                
                # Create a dummy translation function for warm start
                # This just warms up the worker threads, actual translation uses cache
                def dummy_translate(text, source_lang, target_lang):
                    # Just return dummy result - cache will handle real translations
                    return {
                        'translated_text': 'warmup',
                        'confidence': 1.0,
                        'source': 'warmup'
                    }
                
                # Perform warm start - this just warms up the worker threads
                # Real speed comes from cache/dictionary, not subprocess pool
                success = self.parallel_translation.warm_start(
                    self.config.source_language,
                    self.config.target_language,
                    dummy_translate
                )
                
                if success:
                    print("[WARMUP] ✓ Parallel translation warm start complete - model loaded!")
                else:
                    print("[WARMUP] ⚠ Parallel translation warm start failed (will use fallback)")
                    
            except Exception as e:
                print(f"[WARMUP] Error during parallel translation warm start: {e}")
                import traceback
                traceback.print_exc()
        
        # Start warm up in background thread
        warmup_thread = threading.Thread(
            target=warmup_worker,
            name="ParallelTranslationWarmup",
            daemon=True
        )
        warmup_thread.start()
        print("[WARMUP] Parallel translation warm start scheduled (running in background)")
    
    def _ensure_dictionary_exists(self):
        """
        Ensure dictionary file exists for current language pair.
        Creates an empty dictionary file with example entry if it doesn't exist.
        """
        try:
            from pathlib import Path
            from app.utils.path_utils import get_app_path
            import gzip
            import json
            from datetime import datetime
            
            # Get dictionary directory
            dict_dir = get_app_path("dictionary")
            dict_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if dictionary file exists
            dict_file = dict_dir / f"learned_dictionary_{self.config.source_language}_{self.config.target_language}.json.gz"
            
            if not dict_file.exists():
                print(f"[DICTIONARY] Creating new dictionary file: {dict_file}")
                
                # Create empty dictionary with example entry
                example_dict = {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "total_entries": 1,
                    "compressed": True,
                    "source_language": self.config.source_language,
                    "target_language": self.config.target_language,
                    "translations": {
                        "example": {
                            "original": "example",
                            "translation": "Beispiel" if self.config.target_language == "de" else "example",
                            "usage_count": 1,
                            "confidence": 1.0,
                            "last_used": datetime.now().isoformat(),
                            "engine": "manual"
                        }
                    }
                }
                
                # Save to compressed JSON
                with gzip.open(dict_file, 'wt', encoding='utf-8') as f:
                    json.dump(example_dict, f, indent=2, ensure_ascii=False)
                
                print(f"[DICTIONARY] ✓ Created dictionary with example entry")
                self.logger.info(f"Created new dictionary file: {dict_file}")
                
                # Reload dictionary in SmartDictionary if it exists
                if hasattr(self, 'cache_manager') and self.cache_manager and self.cache_manager.persistent_dictionary:
                    self.cache_manager.persistent_dictionary.load_dictionary(
                        str(dict_file),
                        self.config.source_language,
                        self.config.target_language
                    )
                    print(f"[DICTIONARY] ✓ Loaded into SmartDictionary")
            else:
                print(f"[DICTIONARY] Dictionary file exists: {dict_file}")
                
        except Exception as e:
            self.logger.warning(f"Failed to ensure dictionary exists: {e}")
            print(f"[DICTIONARY] Warning: Could not create dictionary file: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_async_pipeline(self):
        """
        Set up async pipeline with stage registration.
        This enables parallel processing of pipeline stages.
        """
        if not self.async_pipeline:
            return
        
        try:
            print("[ASYNC] Registering pipeline stages...")
            
            # Register stages in order: capture → ocr → translation → display
            # Each stage will run in its own worker thread
            
            # Stage 1: Capture
            self.async_pipeline.register_stage(
                stage_name='capture',
                stage_func=self._async_capture_wrapper,
                next_stage='ocr'
            )
            print("[ASYNC] ✓ Registered capture stage")
            
            # Stage 2: OCR
            self.async_pipeline.register_stage(
                stage_name='ocr',
                stage_func=self._async_ocr_wrapper,
                next_stage='translation'
            )
            print("[ASYNC] ✓ Registered OCR stage")
            
            # Stage 3: Translation
            self.async_pipeline.register_stage(
                stage_name='translation',
                stage_func=self._async_translation_wrapper,
                next_stage='display'
            )
            print("[ASYNC] ✓ Registered translation stage")
            
            # Stage 4: Display (final stage, no next stage)
            self.async_pipeline.register_stage(
                stage_name='display',
                stage_func=self._async_display_wrapper,
                next_stage=None
            )
            print("[ASYNC] ✓ Registered display stage")
            
            print("[ASYNC] All stages registered successfully")
            self.logger.info("Async pipeline stages registered")
            
        except Exception as e:
            self.logger.error(f"Failed to set up async pipeline: {e}")
            print(f"[ASYNC] ERROR: Failed to register stages: {e}")
            import traceback
            traceback.print_exc()
    
    def _async_capture_wrapper(self, data):
        """Wrapper for capture stage in async pipeline."""
        try:
            frame_data = self._capture_frame()
            if frame_data:
                return frame_data
        except Exception as e:
            self.logger.error(f"Async capture error: {e}")
        return None
    
    def _async_ocr_wrapper(self, frame_data):
        """Wrapper for OCR stage in async pipeline."""
        if not frame_data:
            return None
        try:
            # Apply frame skip
            if self.frame_skip:
                frame_data = self.frame_skip.process(frame_data)
                if frame_data.get('skip_processing', False):
                    return None
            
            # Apply motion tracker
            if self.motion_tracker:
                frame_data = self.motion_tracker.process(frame_data)
                if frame_data.get('skip_ocr', False):
                    return None
            
            # Run OCR
            ocr_result = self._run_ocr(frame_data)
            return ocr_result
        except RuntimeError as e:
            # OCR layer busy (expected during frame skipping) - don't spam logs
            if "not ready" in str(e):
                self.logger.debug(f"OCR busy, skipping frame: {e}")
            else:
                self.logger.error(f"Async OCR error: {e}")
        except Exception as e:
            self.logger.error(f"Async OCR error: {e}")
        return None
    
    def _async_translation_wrapper(self, ocr_result):
        """Wrapper for translation stage in async pipeline."""
        if not ocr_result:
            return None
        try:
            translation_result = self._run_translation(ocr_result)
            return translation_result
        except Exception as e:
            self.logger.error(f"Async translation error: {e}")
        return None
    
    def _async_display_wrapper(self, translation_result):
        """Wrapper for display stage in async pipeline."""
        if not translation_result:
            return None
        try:
            # Check if still running before displaying
            if self.is_running and not self.stop_event.is_set():
                self._display_overlays(translation_result)
            return translation_result
        except Exception as e:
            self.logger.error(f"Async display error: {e}")
        return None
    
    def start(self) -> bool:
        """Start the pipeline."""
        if self.is_running:
            self.logger.warning("Pipeline already running")
            return False
        
        if not self.config.capture_region:
            self.logger.error("No capture region set")
            return False
        
        self.logger.info("Starting optimized pipeline...")
        self.logger.info(f"Active plugins: {', '.join(self.plugins.keys())}")
        
        # NOTE: Using subprocess-based translation to avoid Qt threading crashes
        # No need to pre-load models since subprocess handles it independently
        print(f"[OPTIMIZED] Using subprocess-based translation (crash-safe)")
        
        self.is_running = True
        self.stop_event.clear()
        
        # Set up and start async_pipeline if enabled (NEW - Phase 2)
        if self.async_pipeline:
            try:
                # Register stages first
                self._setup_async_pipeline()
                
                # Then start workers
                print("[OPTIMIZED] Starting async pipeline workers...")
                self.async_pipeline.start()
                self.logger.info("Async pipeline workers started")
            except Exception as e:
                self.logger.error(f"Failed to start async pipeline: {e}")
                print(f"[OPTIMIZED] Warning: Async pipeline failed to start: {e}")
                import traceback
                traceback.print_exc()
                # Continue without async pipeline
                self.async_pipeline = None
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._pipeline_loop,
            name="OptimizedPipeline",
            daemon=True
        )
        self.capture_thread.start()
        
        self.logger.info("Optimized pipeline thread started")
        return True
    
    def stop(self):
        """Stop the pipeline."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping optimized pipeline...")
        
        # CRITICAL: Set flags FIRST to prevent any new work from being queued
        self.is_running = False
        self.stop_event.set()
        
        # Stop async_pipeline if enabled (NEW - Phase 2)
        if self.async_pipeline:
            try:
                print("[OPTIMIZED] Stopping async pipeline workers...")
                self.async_pipeline.stop()
                self.logger.info("Async pipeline workers stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop async pipeline: {e}")
                print(f"[OPTIMIZED] Warning: Async pipeline failed to stop cleanly: {e}")
        
        # Cleanup parallel_translation if enabled (NEW - Phase 2)
        if self.parallel_translation:
            try:
                print("[OPTIMIZED] Cleaning up parallel translation...")
                self.parallel_translation.cleanup()
                self.logger.info("Parallel translation cleaned up")
            except Exception as e:
                self.logger.error(f"Failed to cleanup parallel translation: {e}")
                print(f"[OPTIMIZED] Warning: Parallel translation cleanup failed: {e}")
        
        # Wait for capture thread to finish current iteration (with longer timeout)
        # This ensures the thread stops creating new overlays
        if self.capture_thread and self.capture_thread.is_alive():
            self.logger.info("Waiting for pipeline thread to stop...")
            self.capture_thread.join(timeout=5.0)  # Increased timeout
            if self.capture_thread.is_alive():
                self.logger.warning("Capture thread did not stop within timeout - forcing stop")
                # Thread is stuck, but flags are set so it won't create new overlays
        
        # Clear overlay tracker
        if self.overlay_tracker:
            try:
                self.overlay_tracker.clear_all()
                self.logger.info("Overlay tracker cleared")
            except Exception as e:
                self.logger.warning(f"Failed to clear overlay tracker: {e}")
        
        # Clear overlay position tracking
        with self.overlay_position_lock:
            self.active_overlays.clear()
            print("[STOP] Cleared overlay position tracking")
        
        # Log statistics
        self._log_statistics()
        
        self.logger.info("Optimized pipeline stopped")
    
    def cleanup(self):
        """Clean up pipeline resources."""
        try:
            # Stop pipeline if still running
            if self.is_running:
                self.stop()
            
            # Clear overlay tracker
            if self.overlay_tracker:
                self.overlay_tracker.clear_all()
            
            # Clear active overlays list
            if hasattr(self, 'active_overlays'):
                self.active_overlays.clear()
            
            # Cleanup plugins
            if hasattr(self, 'plugins') and self.plugins:
                for plugin_name, plugin_data in self.plugins.items():
                    try:
                        optimizer = plugin_data.get('optimizer')
                        if optimizer and hasattr(optimizer, 'cleanup'):
                            optimizer.cleanup()
                    except Exception as e:
                        self.logger.warning(f"Failed to cleanup plugin {plugin_name}: {e}")
            
            # Clear positioning system
            if hasattr(self, 'positioning_system') and self.positioning_system:
                try:
                    if hasattr(self.positioning_system, 'cleanup'):
                        self.positioning_system.cleanup()
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup positioning system: {e}")
            
            self.logger.info("Pipeline cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during pipeline cleanup: {e}")
    
    def _log_statistics(self):
        """Log pipeline statistics."""
        self.logger.info(f"Pipeline Statistics:")
        self.logger.info(f"  Frames processed: {self.frames_processed}")
        self.logger.info(f"  Frames skipped: {self.frames_skipped}")
        self.logger.info(f"  Translations: {self.translations_count}")
        self.logger.info(f"  Cache hits: {self.cache_hits}")
        self.logger.info(f"  Dictionary hits: {self.dictionary_hits}")
        self.logger.info(f"  Validator filtered: {self.validator_filtered}")
        
        # Plugin statistics
        if self.frame_skip:
            stats = self.frame_skip.get_stats()
            self.logger.info(f"  Frame Skip: {stats}")
        
        if self.text_validator_plugin:
            stats = self.text_validator_plugin.get_stats()
            self.logger.info(f"  Text Validator: {stats}")
        
        if self.translation_cache:
            stats = self.translation_cache.get_stats()
            self.logger.info(f"  Translation Cache: {stats}")
        
        # Async pipeline statistics (NEW - Phase 2)
        if self.async_pipeline:
            try:
                stats = self.async_pipeline.get_stats()
                self.logger.info(f"  Async Pipeline: {stats}")
            except Exception as e:
                self.logger.debug(f"Could not get async pipeline stats: {e}")
        
        # Parallel translation statistics (NEW - Phase 2)
        if self.parallel_translation:
            try:
                stats = self.parallel_translation.get_stats()
                self.logger.info(f"  Parallel Translation: {stats}")
            except Exception as e:
                self.logger.debug(f"Could not get parallel translation stats: {e}")
        
        # Dictionary is auto-saved by dict_engine (no manual save needed)
    
    def _pipeline_loop(self):
        """Main pipeline loop with optimizations."""
        try:
            self.logger.info(f"Optimized pipeline loop started (FPS: {self.config.fps})")
            print(f"[OPTIMIZED] Pipeline loop started with {len(self.plugins)} plugins")
            if self.plugins:
                plugin_names = ', '.join(self.plugins.keys())
                print(f"[OPTIMIZED] Active plugins: {plugin_names}")
            print(f"[OPTIMIZED] Capture region: {self.config.capture_region}")
            print(f"[OPTIMIZED] Source language: {self.config.source_language}")
            print(f"[OPTIMIZED] Target language: {self.config.target_language}")
            
            # Check if async pipeline is active and running
            use_async = self.async_pipeline is not None and self.async_pipeline.running
            if use_async:
                print(f"[OPTIMIZED] Using ASYNC pipeline (parallel stages with plugins)")
                self._async_pipeline_loop()
            else:
                print(f"[OPTIMIZED] Using SEQUENTIAL pipeline (normal mode)")
                self._sequential_pipeline_loop()
                
        except Exception as e:
            self.logger.error(f"Fatal error in pipeline loop: {e}")
            print(f"\n[OPTIMIZED] ✗ FATAL ERROR in pipeline loop:")
            print(f"[OPTIMIZED] Error type: {type(e).__name__}")
            print(f"[OPTIMIZED] Error message: {e}")
            import traceback
            print("[OPTIMIZED] Traceback:")
            traceback.print_exc()
            if self.on_error:
                self.on_error(e)
    
    def _async_pipeline_loop(self):
        """Async pipeline loop - workers handle all processing."""
        frame_interval = 1.0 / self.config.fps
        last_frame_time = 0.0
        
        print("[ASYNC] Async pipeline loop started")
        print("[ASYNC] Worker threads are processing stages in parallel")
        print("[ASYNC] Plugins are integrated in stage workers")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Check stop flag at the start of each iteration for quick exit
                if not self.is_running or self.stop_event.is_set():
                    break
                
                # FPS limiting
                current_time = time.time()
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)
                    continue
                
                last_frame_time = current_time
                
                # Submit trigger to capture stage
                # Worker threads will handle: capture → frame_skip → motion_tracker → ocr → translation_cache → translation → display
                submitted = self.async_pipeline.submit('capture', {'timestamp': current_time})
                
                if not submitted:
                    # Queue full - frame dropped
                    self.frames_dropped += 1
                    if self.frames_processed % 30 == 1:
                        print(f"[ASYNC] Queue full, dropped frame (queue size: {self.async_pipeline.stage_queues.get('capture', None).qsize() if self.async_pipeline.stage_queues.get('capture') else 'N/A'})")
                else:
                    self.frames_processed += 1
                    
                    # Log progress periodically
                    if self.frames_processed % 30 == 1:
                        stats = self.async_pipeline.get_stats()
                        print(f"[ASYNC] Processed {self.frames_processed} frames, dropped {self.frames_dropped}")
                        print(f"[ASYNC] Queue sizes: {stats.get('queue_sizes', {})}")
                        print(f"[ASYNC] Avg stage times: {stats.get('avg_stage_times', {})}")
                
            except Exception as e:
                self.logger.error(f"Error in async pipeline loop: {e}")
                print(f"[ASYNC] Error: {e}")
                import traceback
                traceback.print_exc()
                if self.on_error:
                    self.on_error(e)
                time.sleep(0.1)
    
    def _sequential_pipeline_loop(self):
        """Sequential pipeline loop - original synchronous processing."""
        frame_interval = 1.0 / self.config.fps
        last_frame_time = 0.0
        
        while self.is_running and not self.stop_event.is_set():
                try:
                    # Check stop flag at the start of each iteration for quick exit
                    if not self.is_running or self.stop_event.is_set():
                        break
                    
                    # FPS limiting
                    current_time = time.time()
                    if current_time - last_frame_time < frame_interval:
                        time.sleep(0.01)
                        continue
                    
                    last_frame_time = current_time
                    
                    # SEQUENTIAL MODE: Process synchronously
                    # Step 1: Capture frame
                    frame_data = self._capture_frame()
                    if not frame_data:
                        continue
                    
                    # Step 2: Apply frame skip optimizer
                    # Note: Overlay masking for frame skip is complex and may cause issues
                    # For now, rely on high similarity threshold (0.98) to handle minor variations
                    if self.frame_skip:
                        frame_data = self.frame_skip.process(frame_data)
                        if frame_data.get('skip_processing', False):
                            self.frames_skipped += 1
                            # Frame is similar - keep showing existing overlays, don't run OCR
                            if self.frames_processed % 30 == 1:
                                print(f"[FRAME SKIP] Frame skipped (similar to previous)")
                            continue
                    
                    # Step 2.5: Apply motion tracker (for smooth scrolling)
                    if self.motion_tracker:
                        frame_data = self.motion_tracker.process(frame_data)
                        # If motion detected and OCR should be skipped
                        if frame_data.get('skip_ocr', False):
                            # Motion tracker wants to skip OCR and just move overlays
                            overlay_offset = frame_data.get('overlay_offset', (0, 0))
                            if overlay_offset != (0, 0):
                                # Update existing overlay positions
                                self._update_overlay_positions(overlay_offset)
                                if self.frames_processed % 10 == 1:
                                    print(f"[OPTIMIZED] Motion detected: offset={overlay_offset}, skipping OCR")
                            continue
                    
                    self.frames_processed += 1
                    
                    # Step 3: OCR
                    ocr_result = self._run_ocr(frame_data)
                    if not ocr_result:
                        continue
                    
                    text_blocks = ocr_result.get('text_blocks', [])
                    if self.frames_processed % 10 == 1:  # Log every 10th frame
                        print(f"[OPTIMIZED] Frame {self.frames_processed}: Found {len(text_blocks)} text blocks")
                    
                    # Step 4: Translation with cache
                    translation_result = self._run_translation(ocr_result)
                    if not translation_result:
                        continue
                    
                    translations = translation_result.get('translations', [])
                    if self.frames_processed % 10 == 1:
                        print(f"[OPTIMIZED] Frame {self.frames_processed}: Got {len(translations)} translations")
                        for i, trans in enumerate(translations[:3]):  # Show first 3
                            orig = trans.get('original', '')[:20]
                            transl = trans.get('translated', '')[:20]
                            src = trans.get('source', 'unknown')
                            print(f"[OPTIMIZED]   {i+1}. '{orig}' -> '{transl}' (source: {src})")
                        
                        # Check for empty translations
                        empty_count = sum(1 for t in translations if not t.get('translated') or not t.get('translated').strip())
                        if empty_count > 0:
                            print(f"[OPTIMIZED] WARNING: {empty_count}/{len(translations)} translations are empty!")
                    
                    self.translations_count += 1
                    
                    # Step 5: Display overlays with smart positioning
                    # Check if still running before displaying (prevent showing overlays after stop)
                    if self.is_running and not self.stop_event.is_set():
                        self._display_overlays(translation_result)
                    
                    # Step 5.5: Check for disappeared overlays (auto-hide feature)
                    if self.overlay_tracker and self.overlay_tracker.enabled and self.overlay_system:
                        disappeared = self.overlay_tracker.check_disappeared_overlays()
                        if disappeared:
                            for overlay_id in disappeared:
                                try:
                                    self.overlay_system.hide_translation(overlay_id)
                                    self.overlay_tracker.remove_overlay(overlay_id)
                                    if self.frames_processed % 10 == 1:
                                        print(f"[OPTIMIZED] Auto-hid overlay: {overlay_id}")
                                except Exception as e:
                                    self.logger.debug(f"Failed to hide overlay {overlay_id}: {e}")
                    
                    # Step 6: Callback (DISABLED - optimized pipeline handles overlays internally)
                    # The external callback expects Translation objects, but we use dicts
                    # Overlays are already displayed in _display_overlays() above
                    # if self.on_translation:
                    #     self.on_translation(translation_result)
                    
                except Exception as e:
                    self.logger.error(f"Error in sequential pipeline iteration: {e}")
                    print(f"[SEQUENTIAL] ✗ Error in pipeline iteration:")
                    print(f"[SEQUENTIAL] Error type: {type(e).__name__}")
                    print(f"[SEQUENTIAL] Error message: {e}")
                    import traceback
                    traceback.print_exc()
                    if self.on_error:
                        self.on_error(e)
                    time.sleep(0.1)
    
    def _capture_frame(self) -> Optional[Dict[str, Any]]:
        """Capture frame from screen."""
        try:
            frame = self.capture_layer.capture_frame(
                CaptureSource.CUSTOM_REGION,
                self.config.capture_region
            )
            
            if frame and frame.data is not None:
                return {
                    'frame': frame.data,
                    'timestamp': frame.timestamp,
                    'region': self.config.capture_region
                }
        except Exception as e:
            self.logger.error(f"Capture error: {e}")
        
        return None
    
    def _run_ocr(self, frame_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run OCR on frame with text validation."""
        try:
            # Mask overlay regions to prevent OCR feedback loop
            frame_image = frame_data['frame'].copy()  # Don't modify original
            
            # Get capture region offset
            region_x = 0
            region_y = 0
            if self.config.capture_region:
                region_x = self.config.capture_region.rectangle.x
                region_y = self.config.capture_region.rectangle.y
            
            # Mask out overlay positions (prevent OCR from detecting overlay text)
            masked_count = 0
            with self.overlay_position_lock:
                for overlay_rect in self.active_overlays:
                    try:
                        # Convert absolute screen coordinates to capture-region-relative
                        rel_x = overlay_rect.x - region_x
                        rel_y = overlay_rect.y - region_y
                        
                        # Check if overlay is within capture region
                        if (rel_x >= 0 and rel_y >= 0 and 
                            rel_x < frame_image.shape[1] and rel_y < frame_image.shape[0]):
                            
                            # Calculate mask bounds (ensure within frame)
                            x1 = max(0, rel_x)
                            y1 = max(0, rel_y)
                            x2 = min(frame_image.shape[1], rel_x + overlay_rect.width)
                            y2 = min(frame_image.shape[0], rel_y + overlay_rect.height)
                            
                            # Mask overlay area (set to black to prevent OCR detection)
                            if x2 > x1 and y2 > y1:
                                frame_image[y1:y2, x1:x2] = 0
                                masked_count += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to mask overlay region: {e}")
            
            if masked_count > 0:
                if self.frames_processed % 10 == 1:
                    print(f"[OCR] Masked {masked_count} overlay regions to prevent feedback loop")
            elif len(self.active_overlays) > 0:
                # Overlays exist but weren't masked - debug this
                print(f"[OCR WARNING] {len(self.active_overlays)} overlays tracked but 0 masked! Check coordinates.")
            
            # Create Frame object from masked frame_data
            from app.models import Frame
            frame = Frame(
                data=frame_image,  # Use masked image
                timestamp=frame_data['timestamp'],
                source_region=frame_data['region']
            )
            
            # Extract text using OCR (language is handled by the OCR engine internally)
            text_blocks = self.ocr_layer.extract_text(frame)
            
            # Apply intelligent text processor for OCR error correction (| → I, etc.)
            if text_blocks:
                intelligent_processor = self.plugin_loader.get_plugin('intelligent_text_processor')
                if intelligent_processor:
                    try:
                        # Convert TextBlock objects to dict format expected by plugin
                        texts_data = [{
                            'text': block.text,
                            'bbox': [block.position.x, block.position.y, block.position.width, block.position.height],
                            'confidence': block.confidence
                        } for block in text_blocks]
                        
                        processor_data = {'texts': texts_data}
                        processed_data = intelligent_processor.process(processor_data)
                        
                        if processed_data and 'texts' in processed_data:
                            # Convert back to TextBlock objects with corrected text
                            from app.models import TextBlock, Rectangle
                            text_blocks = [
                                TextBlock(
                                    text=item['text'],  # This is the corrected text
                                    position=Rectangle(
                                        x=item['bbox'][0],
                                        y=item['bbox'][1],
                                        width=item['bbox'][2],
                                        height=item['bbox'][3]
                                    ),
                                    confidence=item.get('confidence', block.confidence)
                                )
                                for item, block in zip(processed_data['texts'], text_blocks)
                            ]
                            print(f"[INTELLIGENT_PROCESSOR] Processed {len(text_blocks)} text blocks")
                    except Exception as e:
                        self.logger.error(f"Intelligent text processor error: {e}")
                        import traceback
                        traceback.print_exc()
            
            # Use text block merger plugin (simpler, more reliable)
            if self.text_block_merger and text_blocks:
                merger_data = {
                    'texts': [{
                        'text': block.text,
                        'bbox': [block.position.x, block.position.y, block.position.width, block.position.height],
                        'confidence': block.confidence
                    } for block in text_blocks]
                }
                merged_data = self.text_block_merger.process(merger_data)
                
                # Convert back to TextBlock objects
                from app.models import TextBlock, Rectangle
                text_blocks = [
                    TextBlock(
                        text=item['text'],
                        position=Rectangle(
                            x=item['bbox'][0],
                            y=item['bbox'][1],
                            width=item['bbox'][2],
                            height=item['bbox'][3]
                        ),
                        confidence=item.get('confidence', 1.0)
                    )
                    for item in merged_data.get('texts', [])
                ]
            
            if text_blocks:
                return {
                    'text_blocks': text_blocks,
                    'frame_data': frame_data
                }
        except RuntimeError as e:
            # OCR layer busy (expected during frame skipping) - don't spam logs
            if "not ready" in str(e):
                self.logger.debug(f"OCR busy, skipping frame: {e}")
            else:
                self.logger.error(f"OCR error: {e}")
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
        
        return None
    
    def _run_translation(self, ocr_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run translation with intelligent dictionary lookup and cache support."""
        try:
            text_blocks = ocr_result['text_blocks']
            translations = []
            
            # Apply text processor plugins (spell correction, etc.)
            if self.spell_corrector:
                text_blocks = self.spell_corrector.process(text_blocks)
            
            # PARALLEL TRANSLATION: Process multiple texts simultaneously (NEW - Phase 2, wired but disabled)
            if self.parallel_translation and len(text_blocks) > 1:
                try:
                    print(f"[PARALLEL_TRANSLATION] Processing {len(text_blocks)} texts in parallel...")
                    
                    # Prepare texts for parallel processing
                    texts_data = []
                    for i, block in enumerate(text_blocks):
                        texts_data.append({
                            'id': i,
                            'text': block.text,
                            'source_lang': self.config.source_language,
                            'target_lang': self.config.target_language,
                            'block': block  # Keep reference to original block
                        })
                    
                    # Create translation function wrapper with cache/dictionary lookup
                    def translate_func(text, source_lang, target_lang):
                        # Step 1: Try translation cache (fastest)
                        if self.translation_cache:
                            cache_data = {
                                'text': text,
                                'source_lang': source_lang,
                                'target_lang': target_lang
                            }
                            cache_result = self.translation_cache.process(cache_data)
                            
                            if cache_result.get('cache_hit', False):
                                return {
                                    'translated_text': cache_result['translated_text'],
                                    'confidence': 1.0,
                                    'source': 'cache'
                                }
                        
                        # Step 2: Try persistent dictionary
                        if hasattr(self, 'cache_manager') and self.cache_manager and self.cache_manager.persistent_dictionary:
                            try:
                                dict_entry = self.cache_manager.persistent_dictionary.lookup(
                                    text,
                                    source_lang,
                                    target_lang
                                )
                                
                                if dict_entry:
                                    translated_text = dict_entry.translation
                                    
                                    # Store in memory cache for next time
                                    if self.translation_cache:
                                        cache_data = {
                                            'text': text,
                                            'source_lang': source_lang,
                                            'target_lang': target_lang,
                                            'translated_text': translated_text
                                        }
                                        self.translation_cache.post_process(cache_data)
                                    
                                    return {
                                        'translated_text': translated_text,
                                        'confidence': 1.0,
                                        'source': 'dictionary'
                                    }
                            except Exception as e:
                                pass  # Continue to subprocess
                        
                        # Step 3: Use subprocess translation (only if not in cache/dictionary)
                        # Note: Using one-shot subprocess for stability
                        # Cache/dictionary provide speed for repeated translations
                        from app.translation.engines.marianmt_subprocess import translate_in_subprocess
                        
                        result = translate_in_subprocess(
                            text,
                            source_lang,
                            target_lang,
                            timeout=15.0
                        )
                        
                        if result.get('error'):
                            return {'translated_text': text, 'confidence': 0.0, 'source': 'error'}
                        else:
                            translated_text = result.get('translated_text', '').strip()
                            
                            # Save to cache and dictionary for next time
                            if translated_text:
                                # Save to cache
                                if self.translation_cache:
                                    cache_data = {
                                        'text': text,
                                        'source_lang': source_lang,
                                        'target_lang': target_lang,
                                        'translated_text': translated_text
                                    }
                                    self.translation_cache.post_process(cache_data)
                                
                                # Save to dictionary
                                if hasattr(self, 'cache_manager') and self.cache_manager and self.cache_manager.persistent_dictionary:
                                    try:
                                        self.cache_manager.persistent_dictionary.add_entry(
                                            source_text=text,
                                            translated_text=translated_text,
                                            source_lang=source_lang,
                                            target_lang=target_lang,
                                            confidence=1.0
                                        )
                                    except Exception as e:
                                        pass  # Non-critical
                            
                            return {
                                'translated_text': translated_text if translated_text else text,
                                'confidence': 1.0,
                                'source': 'subprocess'
                            }
                    
                    # Process in parallel
                    parallel_data = {
                        'texts': texts_data,
                        'translation_function': translate_func
                    }
                    result_data = self.parallel_translation.process(parallel_data)
                    
                    # Extract results and create translations
                    if 'translation_results' in result_data:
                        for result in result_data['translation_results']:
                            text_id = result.get('text_id', 0)
                            if text_id < len(text_blocks):
                                block = text_blocks[text_id]
                                translated_text = result.get('translated_text', '')
                                
                                if translated_text and translated_text.strip():
                                    # Get position from block
                                    bbox = None
                                    if hasattr(block, 'bbox'):
                                        bbox = block.bbox
                                    elif hasattr(block, 'position'):
                                        bbox = block.position
                                    elif hasattr(block, 'bounding_box'):
                                        bbox = block.bounding_box
                                    
                                    translations.append({
                                        'original': block.text,
                                        'translated': translated_text,
                                        'bbox': bbox,
                                        'confidence': result.get('confidence', 1.0),
                                        'source': 'parallel_translation'
                                    })
                        
                        # If parallel translation succeeded, skip sequential processing
                        if translations:
                            print(f"[PARALLEL_TRANSLATION] Successfully translated {len(translations)} texts")
                            return {
                                'translations': translations,
                                'frame_data': ocr_result['frame_data']
                            }
                    
                except Exception as e:
                    self.logger.error(f"Parallel translation failed: {e}")
                    print(f"[PARALLEL_TRANSLATION] Error: {e}, falling back to sequential")
                    import traceback
                    traceback.print_exc()
                    # Fall through to sequential processing
            
            # SEQUENTIAL TRANSLATION: Process one text at a time (fallback or if parallel disabled)
            for block in text_blocks:
                text = block.text
                translated_text = None
                source = None
                
                # PRE-PROCESS: Check if Translation Chain plugin should be used
                # Get persistent dictionary (SmartDictionary)
                persistent_dict = None
                if hasattr(self, 'cache_manager') and self.cache_manager:
                    persistent_dict = self.cache_manager.persistent_dictionary
                
                translation_data = {
                    'text': text,
                    'source_lang': self.config.source_language,
                    'target_lang': self.config.target_language,
                    'dictionary_engine': persistent_dict,  # Pass SmartDictionary instance
                    'translation_layer': self.translation_layer
                }
                
                # Apply Translation Chain pre-processing
                chain_plugin = self.plugins.get('translation_chain')
                if chain_plugin and chain_plugin.get('enabled', False):
                    optimizer = chain_plugin.get('optimizer')
                    if optimizer:
                        translation_data = optimizer.process(translation_data)
                        
                        # Check if chain wants to skip normal translation
                        if translation_data.get('skip_translation', False):
                            translated_text = translation_data.get('translated_text')
                            source = translation_data.get('translation_source', 'chain')
                            # Skip to next block
                            if translated_text:
                                bbox = None
                                if hasattr(block, 'bbox'):
                                    bbox = block.bbox
                                elif hasattr(block, 'position'):
                                    bbox = block.position
                                elif hasattr(block, 'bounding_box'):
                                    bbox = block.bounding_box
                                
                                translations.append({
                                    'original': text,
                                    'translated': translated_text,
                                    'bbox': bbox,
                                    'confidence': block.confidence if hasattr(block, 'confidence') else 1.0,
                                    'source': source
                                })
                            continue
                
                # Step 1: Try translation cache (fastest)
                if self.translation_cache:
                    cache_data = {
                        'text': text,
                        'source_lang': self.config.source_language,
                        'target_lang': self.config.target_language
                    }
                    cache_result = self.translation_cache.process(cache_data)
                    
                    if cache_result.get('cache_hit', False):
                        translated_text = cache_result['translated_text']
                        source = 'cache'
                        self.cache_hits += 1
                
                # Step 2: Try persistent dictionary (fast, survives restarts)
                if not translated_text:
                    try:
                        # Use PipelineCacheManager's persistent dictionary (NEW SYSTEM)
                        if hasattr(self, 'cache_manager') and self.cache_manager and self.cache_manager.persistent_dictionary:
                            dict_entry = self.cache_manager.persistent_dictionary.lookup(
                                text,
                                self.config.source_language,
                                self.config.target_language
                            )
                            
                            if dict_entry:
                                translated_text = dict_entry.translation
                                source = 'dictionary'
                                self.dictionary_hits += 1
                                self.logger.debug(f"Dictionary hit: '{text[:20]}...' -> '{translated_text[:20]}...'")
                                
                                # Also store in memory cache for even faster access next time
                                if self.translation_cache:
                                    cache_data = {
                                        'text': text,
                                        'source_lang': self.config.source_language,
                                        'target_lang': self.config.target_language,
                                        'translated_text': translated_text
                                    }
                                    self.translation_cache.post_process(cache_data)
                    except Exception as e:
                        self.logger.debug(f"Dictionary lookup failed: {e}")
                
                # Step 3: Use translation engine (subprocess)
                # Cache and dictionary provide speed for repeated translations
                if not translated_text:
                    try:
                        # Use subprocess-based translation (stable, cache provides speed)
                        from app.translation.engines.marianmt_subprocess import translate_in_subprocess
                        
                        if self.frames_processed == 1:
                            print(f"[OPTIMIZED] First subprocess call: '{text[:30]}' ({self.config.source_language}->{self.config.target_language})")
                        
                        result = translate_in_subprocess(
                            text,
                            self.config.source_language,
                            self.config.target_language,
                            timeout=15.0
                        )
                        
                        if result.get('error'):
                            if self.frames_processed == 1:
                                print(f"[OPTIMIZED] Subprocess ERROR: {result['error']}")
                            self.logger.warning(f"Subprocess translation failed for '{text[:30]}': {result['error']}")
                            translated_text = None
                        else:
                            translated_text = result.get('translated_text', '').strip()
                            if translated_text:
                                source = 'subprocess'
                                if self.frames_processed == 1:
                                    print(f"[OPTIMIZED] Subprocess SUCCESS: '{text[:20]}' -> '{translated_text[:20]}'")
                            else:
                                if self.frames_processed == 1:
                                    print(f"[OPTIMIZED] Subprocess returned EMPTY for: '{text[:30]}'")
                                    print(f"[OPTIMIZED] Full result: {result}")
                                self.logger.warning(f"Subprocess returned empty translation for: '{text[:30]}'")
                    except Exception as e:
                        self.logger.error(f"Subprocess translation error: {e}")
                        translated_text = None
                        source = None
                    
                    # POST-PROCESS: Execute Translation Chain if needed
                    if translation_data.get('use_translation_chain', False):
                        chain_plugin = self.plugins.get('translation_chain')
                        if chain_plugin and chain_plugin.get('enabled', False):
                            optimizer = chain_plugin.get('optimizer')
                            if optimizer:
                                # Update translation_data with result
                                translation_data['translated_text'] = translated_text
                                translation_data = optimizer.post_process(translation_data)
                                
                                # Get chained translation result
                                if translation_data.get('translated_text'):
                                    translated_text = translation_data['translated_text']
                                    source = 'translation_chain'
                    
                    if translated_text:
                        print(f"[DICT DEBUG] Attempting to save translation: '{text[:30]}' -> '{translated_text[:30]}'")
                        # Store in persistent dictionary for future use (with quality filter)
                        try:
                            # Use cache_manager's persistent dictionary (SmartDictionary)
                            persistent_dict = None
                            if hasattr(self, 'cache_manager') and self.cache_manager:
                                persistent_dict = self.cache_manager.persistent_dictionary
                                print(f"[DICT DEBUG] cache_manager exists, persistent_dict={persistent_dict is not None}")
                            else:
                                print(f"[DICT DEBUG] cache_manager not available! hasattr={hasattr(self, 'cache_manager')}, cache_manager={getattr(self, 'cache_manager', None)}")
                            
                            if not persistent_dict:
                                self.logger.warning(f"[DICT DEBUG] Persistent dictionary not available! cache_manager={self.cache_manager}")
                                if self.cache_manager:
                                    self.logger.warning(f"[DICT DEBUG] cache_manager.persistent_dictionary={self.cache_manager.persistent_dictionary}")
                            
                            if persistent_dict:
                                # FORCE DISABLE quality filter to save all translations
                                quality_filter_enabled = False
                                filter_mode = 'balanced'
                                
                                # Commented out to force disable quality filter
                                # try:
                                #     # Get settings from config manager
                                #     if hasattr(self, 'config_manager') and self.config_manager:
                                #         quality_filter_enabled = self.config_manager.get_setting(
                                #             'translation.quality_filter_enabled', True
                                #         )
                                #         filter_mode_index = self.config_manager.get_setting(
                                #             'translation.quality_filter_mode', 0
                                #         )
                                #         filter_mode = 'strict' if filter_mode_index == 1 else 'balanced'
                                # except Exception:
                                #     pass  # Use defaults
                                
                                confidence = block.confidence if hasattr(block, 'confidence') else 0.9
                                
                                if quality_filter_enabled:
                                    # Quality filter - only save good translations
                                    from app.translation.translation_quality_filter import (
                                        default_quality_filter, strict_quality_filter
                                    )
                                    
                                    quality_filter = strict_quality_filter if filter_mode == 'strict' else default_quality_filter
                                    
                                    should_save, reason = quality_filter.should_save(
                                        text,
                                        translated_text,
                                        confidence,
                                        self.config.source_language,
                                        self.config.target_language
                                    )
                                    
                                    if should_save:
                                        # Add entry to persistent dictionary
                                        persistent_dict.add_entry(
                                            source_text=text,
                                            translation=translated_text,
                                            source_language=self.config.source_language,
                                            target_language=self.config.target_language,
                                            confidence=confidence,
                                            source_engine='marianmt',
                                            auto_merge=True
                                        )
                                        print(f"[DICTIONARY] ✓ Saved: '{text[:30]}' -> '{translated_text[:30]}'")
                                        self.logger.info(f"Saved to dictionary: '{text[:30]}' -> '{translated_text[:30]}'")
                                    else:
                                        print(f"[DICTIONARY] ✗ Quality filter rejected: {reason}")
                                        self.logger.debug(f"Quality filter rejected: {reason}")
                                else:
                                    # Quality filter disabled - save all translations
                                    persistent_dict.add_entry(
                                        source_text=text,
                                        translation=translated_text,
                                        source_language=self.config.source_language,
                                        target_language=self.config.target_language,
                                        confidence=confidence,
                                        source_engine='marianmt',
                                        auto_merge=True
                                    )
                                    print(f"[DICTIONARY] ✓ Saved (no filter): '{text[:30]}' -> '{translated_text[:30]}'")
                                    self.logger.info(f"Saved to dictionary: '{text[:30]}' -> '{translated_text[:30]}'")
                                
                                # Auto-save periodically
                                self.translations_since_save += 1
                                if self.translations_since_save >= self.save_interval:
                                    self.logger.info(f"Auto-saving dictionary ({self.translations_since_save} new translations)...")
                                    # Save dictionary to file
                                    from pathlib import Path
                                    from app.utils.path_utils import get_app_path
                                    
                                    # Use app-relative path for EXE compatibility
                                    dict_dir = get_app_path("dictionary")
                                    dict_dir.mkdir(parents=True, exist_ok=True)
                                    dict_file = dict_dir / f"learned_dictionary_{self.config.source_language}_{self.config.target_language}.json.gz"
                                    persistent_dict.save_dictionary(
                                        str(dict_file),
                                        self.config.source_language,
                                        self.config.target_language
                                    )
                                    self.translations_since_save = 0
                                    self.logger.info(f"Dictionary saved to: {dict_file}")
                                    print(f"[DICTIONARY] Auto-saved {self.save_interval} translations to {dict_file}")
                        except Exception as e:
                            print(f"[DICT DEBUG] Exception while saving to dictionary: {e}")
                            self.logger.warning(f"Failed to save to dictionary: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        # Store in cache
                        if self.translation_cache:
                            cache_data = {
                                'text': text,
                                'source_lang': self.config.source_language,
                                'target_lang': self.config.target_language,
                                'translated_text': translated_text
                            }
                            self.translation_cache.post_process(cache_data)
                
                # Only add if translated_text is not empty (strict check)
                if translated_text and translated_text.strip():
                    # Get position/bbox from block (different OCR engines use different attributes)
                    bbox = None
                    if hasattr(block, 'bbox'):
                        bbox = block.bbox
                    elif hasattr(block, 'position'):
                        bbox = block.position
                    elif hasattr(block, 'bounding_box'):
                        bbox = block.bounding_box
                    
                    translations.append({
                        'original': text,
                        'translated': translated_text,
                        'bbox': bbox,
                        'confidence': block.confidence if hasattr(block, 'confidence') else 1.0,
                        'source': source,  # Track where translation came from
                        'estimated_font_size': block.estimated_font_size if hasattr(block, 'estimated_font_size') else None
                    })
                else:
                    # Log skipped empty translations for debugging
                    if text:
                        self.logger.debug(f"Skipped empty translation for: '{text[:30]}...'")
            
            if translations:
                return {
                    'translations': translations,
                    'frame_data': ocr_result['frame_data']
                }
        
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
        
        return None
    
    def _update_overlay_positions(self, offset: tuple):
        """
        Update overlay positions based on motion offset (for smooth scrolling).
        
        Args:
            offset: (dx, dy) offset to apply to all overlays
        """
        if not self.overlay_system:
            return
        
        try:
            # Check if overlay system supports position updates
            if hasattr(self.overlay_system, 'update_all_positions'):
                self.overlay_system.update_all_positions(offset)
            else:
                # Fallback: Just log that we can't update positions
                # This is not critical - overlays will just stay in place until next OCR
                pass
        except Exception as e:
            self.logger.debug(f"Failed to update overlay positions: {e}")
    
    def _display_overlays(self, translation_result: Dict[str, Any]):
        """Display overlays with smart positioning."""
        # CRITICAL: Check if pipeline is still running before showing overlays
        if not self.is_running or self.stop_event.is_set():
            return
        
        if not self.overlay_system:
            return
        
        try:
            translations = translation_result.get('translations', [])
            if not translations:
                return
            
            # DON'T hide old overlays every frame - this causes flashing!
            # Only hide if we have new content (frame skip will prevent unnecessary updates)
            # self.overlay_system.hide_all_translations()  # DISABLED - causes flashing
            
            # Get capture region offset for coordinate conversion
            region_x = 0
            region_y = 0
            if self.config.capture_region:
                region_x = self.config.capture_region.rectangle.x
                region_y = self.config.capture_region.rectangle.y
            
            # Apply smart positioning if available
            if self.positioning_system:
                # Convert to format expected by positioning system (Translation objects)
                from app.models import Translation, Rectangle
                
                positioned_translations = []
                skipped_empty = 0
                for trans in translations:
                    # Skip empty translations (strict check)
                    translated = trans.get('translated', '')
                    if not translated or not translated.strip():
                        skipped_empty += 1
                        if skipped_empty <= 2:  # Only log first 2
                            self.logger.debug(f"Skipping empty translation for: {trans.get('original', 'unknown')[:30]}")
                        continue
                    
                    # Extract position from bbox (handle different formats)
                    bbox = trans.get('bbox')
                    if bbox:
                        if isinstance(bbox, (list, tuple)) and len(bbox) >= 2:
                            x, y = int(bbox[0]), int(bbox[1])  # Convert to int
                            w = int(bbox[2]) if len(bbox) > 2 else 100
                            h = int(bbox[3]) if len(bbox) > 3 else 30
                        elif hasattr(bbox, 'x') and hasattr(bbox, 'y'):
                            x, y = int(bbox.x), int(bbox.y)  # Convert to int
                            w = int(bbox.width) if hasattr(bbox, 'width') else 100
                            h = int(bbox.height) if hasattr(bbox, 'height') else 30
                        else:
                            x, y, w, h = 0, 0, 100, 30
                    else:
                        x, y, w, h = 0, 0, 100, 30
                    
                    # Create proper Translation object with Rectangle position
                    translation_obj = Translation(
                        original_text=trans['original'],
                        translated_text=trans['translated'],
                        source_language=self.config.source_language,
                        target_language=self.config.target_language,
                        position=Rectangle(x=x, y=y, width=w, height=h),
                        confidence=trans.get('confidence', 1.0),
                        engine_used=trans.get('source', 'unknown'),
                        estimated_font_size=trans.get('estimated_font_size')
                    )
                    positioned_translations.append(translation_obj)
                
                if skipped_empty > 0 and self.frames_processed % 10 == 1:
                    print(f"[OPTIMIZED] Skipped {skipped_empty} empty translations")
                
                # Calculate optimal positions (only if we have valid translations)
                if positioned_translations:
                    try:
                        positioned_translations = self.positioning_system.calculate_optimal_overlay_positions(
                            positioned_translations,
                            frame=None,  # Frame not needed for basic positioning
                            existing_overlays=self.active_overlays if self.active_overlays else [],
                            ui_elements=[]
                        )
                    except Exception as e:
                        # Silently fall back to original positions
                        # Don't log "empty text" errors as they're expected
                        error_msg = str(e).lower()
                        if "empty" not in error_msg and "cannot be empty" not in error_msg:
                            self.logger.warning(f"Smart positioning failed: {e}")
                        # On error, just use the translations we already created
                        pass
                else:
                    self.logger.debug("No valid translations to position")
            else:
                # Use original positions from OCR (no smart positioning)
                positioned_translations = []
                for trans in translations:
                    # Skip empty translations
                    if not trans.get('translated') or not trans['translated'].strip():
                        continue
                    
                    bbox = trans.get('bbox')
                    # Handle different bbox formats
                    if bbox:
                        if isinstance(bbox, (list, tuple)) and len(bbox) >= 2:
                            x, y = int(bbox[0]), int(bbox[1])  # Convert to int
                        elif hasattr(bbox, 'x') and hasattr(bbox, 'y'):
                            x, y = int(bbox.x), int(bbox.y)  # Convert to int
                        else:
                            x, y = 0, 0
                    else:
                        x, y = 0, 0
                    
                    # Create simple object with position
                    class TranslationObj:
                        def __init__(self, text, x, y):
                            self.translated_text = text
                            self.position = type('Position', (), {'x': int(x), 'y': int(y)})()
                    
                    positioned_translations.append(TranslationObj(trans['translated'], x, y))
            
            # Display overlays
            self.active_overlays = []
            displayed_count = 0
            
            # Get screen bounds for boundary checking
            # Note: These are fallback values; actual positioning uses capture region bounds
            screen_width = 2560
            screen_height = 1440
            
            for i, trans in enumerate(positioned_translations):
                # Get position (ensure integers)
                ocr_x = int(trans.position.x) if hasattr(trans.position, 'x') else 0
                ocr_y = int(trans.position.y) if hasattr(trans.position, 'y') else 0
                
                # Convert to absolute screen coordinates (ensure integers)
                abs_x = int(region_x + ocr_x)
                abs_y = int(region_y + ocr_y)
                
                # Clamp to screen bounds (prevent overlays from going off-screen)
                abs_x = max(0, min(abs_x, screen_width - 100))  # Leave 100px margin
                abs_y = max(0, min(abs_y, screen_height - 50))  # Leave 50px margin
                
                # Get monitor ID
                monitor_id = self.config.capture_region.monitor_id if self.config.capture_region else 0
                
                # Show overlay
                text = trans.translated_text if hasattr(trans, 'translated_text') else str(trans)
                
                # Log first overlay for debugging
                if i == 0 and self.frames_processed % 10 == 1:
                    print(f"[OPTIMIZED] Overlay {i+1}: '{text[:30]}' at OCR({ocr_x},{ocr_y}) -> Screen({abs_x},{abs_y})")
                
                # Generate overlay ID based on text content (not position) to prevent duplicates
                # Use hash of text to create stable ID even if position changes slightly
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                overlay_id = f"translation_{text_hash}_{i}"
                
                # Show overlay
                self.overlay_system.show_translation(text, (abs_x, abs_y), translation_id=overlay_id, monitor_id=None)
                displayed_count += 1
                
                # Track overlay for auto-hide functionality
                if self.overlay_tracker and self.overlay_tracker.enabled:
                    # Get source region from original translation data
                    source_region = (ocr_x, ocr_y, 100, 30)  # Default size
                    if i < len(translations):
                        bbox = translations[i].get('bbox')
                        if bbox:
                            # Handle different bbox formats safely
                            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                                source_region = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
                            elif hasattr(bbox, 'x') and hasattr(bbox, 'y'):
                                w = bbox.width if hasattr(bbox, 'width') else 100
                                h = bbox.height if hasattr(bbox, 'height') else 30
                                source_region = (int(bbox.x), int(bbox.y), int(w), int(h))
                    
                    # Check if overlay is already tracked
                    if overlay_id in self.overlay_tracker.tracked_overlays:
                        # Update existing overlay (refresh last_seen timestamp)
                        self.overlay_tracker.update_overlay(overlay_id, still_visible=True)
                    else:
                        # Track new overlay
                        self.overlay_tracker.track_overlay(
                            overlay_id=overlay_id,
                            text=text,
                            position=(abs_x, abs_y),
                            source_region=source_region,
                            confidence=1.0
                        )
                
                # Track for collision detection (store as Rectangle for positioning system)
                from app.models import Rectangle
                if hasattr(trans.position, 'x') and hasattr(trans.position, 'y'):
                    # If position is already a Rectangle, use it directly
                    if isinstance(trans.position, Rectangle):
                        self.active_overlays.append(trans.position)
                    else:
                        # Create Rectangle from position attributes
                        width = trans.position.width if hasattr(trans.position, 'width') else 100
                        height = trans.position.height if hasattr(trans.position, 'height') else 30
                        self.active_overlays.append(Rectangle(trans.position.x, trans.position.y, width, height))
                else:
                    # Fallback: create Rectangle from absolute coordinates
                    self.active_overlays.append(Rectangle(abs_x, abs_y, 100, 30))
            
            if self.frames_processed % 10 == 1:
                print(f"[OPTIMIZED] Displayed {displayed_count} overlays")
            
        except Exception as e:
            self.logger.error(f"Error displaying overlays: {e}")


def create_optimized_runtime_pipeline(capture_layer, ocr_layer, translation_layer,
                                     config: OptimizedRuntimePipelineConfig,
                                     overlay_system=None, config_manager=None) -> OptimizedRuntimePipeline:
    """Create optimized runtime pipeline with plugin support and persistent dictionary."""
    # Create cache manager with persistent dictionary
    from .managers.pipeline_cache_manager import PipelineCacheManager
    cache_manager = PipelineCacheManager(enable_persistent_dictionary=True, config_manager=config_manager)
    
    return OptimizedRuntimePipeline(
        capture_layer=capture_layer,
        ocr_layer=ocr_layer,
        translation_layer=translation_layer,
        config=config,
        overlay_system=overlay_system,
        config_manager=config_manager,
        cache_manager=cache_manager
    )
