"""
Configuration Schema for OptikR

This module defines the complete configuration schema with validation rules.
It provides ConfigOption dataclass for individual options and ConfigSchema
for managing all configuration options with type checking and constraint validation.

Requirements: 3.1, 3.2, 3.10
"""

from dataclasses import dataclass, field
from typing import Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigOption:
    """
    Definition of a single configuration option.
    
    Attributes:
        name: Dot-notation key for the option (e.g., 'capture.fps')
        type: Python type for the option value
        default: Default value if not specified
        min_value: Minimum allowed value (for numeric types)
        max_value: Maximum allowed value (for numeric types)
        choices: List of valid choices (for enum-like options)
        description: Human-readable description
        required: Whether the option must be present
        sensitive: Whether the option contains sensitive data (requires encryption)
    """
    name: str
    type: type
    default: Any
    min_value: Any | None = None
    max_value: Any | None = None
    choices: list[Any] | None = None
    description: str = ""
    required: bool = False
    sensitive: bool = False
    
    def validate(self, value: Any) -> tuple[bool, str | None]:
        """
        Validate a value against this option's constraints.
        
        Args:
            value: The value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
            If invalid, error_message describes the problem
        """
        # Check type - be strict about bool vs int
        if self.type == bool:
            # For bool, don't accept int (since bool is subclass of int in Python)
            if not isinstance(value, bool):
                return False, f"Value must be of type {self.type.__name__}, got {type(value).__name__}"
        elif self.type == int:
            # For int, don't accept bool or float
            if isinstance(value, bool) or isinstance(value, float):
                return False, f"Value must be of type {self.type.__name__}, got {type(value).__name__}"
            if not isinstance(value, int):
                # Try to convert string to int
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    return False, f"Value must be of type {self.type.__name__}, got {type(value).__name__}"
        elif not isinstance(value, self.type):
            # For other types, try to convert
            try:
                value = self.type(value)
            except (ValueError, TypeError):
                return False, f"Value must be of type {self.type.__name__}, got {type(value).__name__}"
        
        # Check choices
        if self.choices is not None and value not in self.choices:
            return False, f"Value must be one of {self.choices}, got {value}"
        
        # Check range for numeric types
        if self.min_value is not None and value < self.min_value:
            return False, f"Value must be >= {self.min_value}, got {value}"
        
        if self.max_value is not None and value > self.max_value:
            return False, f"Value must be <= {self.max_value}, got {value}"
        
        return True, None


class ConfigSchema:
    """
    Complete configuration schema with validation.
    
    Manages all configuration options and provides validation methods.
    """
    
    def __init__(self):
        """Initialize schema with all configuration options."""
        self.options: dict[str, ConfigOption] = {}
        self._build_schema()
    
    def _build_schema(self) -> None:
        """Build the complete configuration schema."""
        # Capture settings
        self.add_option(ConfigOption(
            name='capture.fps',
            type=int,
            default=30,
            min_value=5,
            max_value=30,
            description='Frames per second for screen capture'
        ))
        
        self.add_option(ConfigOption(
            name='capture.quality',
            type=str,
            default='high',
            choices=['low', 'medium', 'high', 'ultra'],
            description='Capture quality setting'
        ))
        
        self.add_option(ConfigOption(
            name='capture.timeout_ms',
            type=int,
            default=5000,
            min_value=100,
            max_value=30000,
            description='Timeout for capture operations in milliseconds'
        ))
        
        self.add_option(ConfigOption(
            name='capture.method',
            type=str,
            default='auto',
            choices=['auto', 'directx', 'bettercam', 'screenshot', 'plugin'],
            description='Screen capture method to use'
        ))
        
        self.add_option(ConfigOption(
            name='capture.monitor_index',
            type=int,
            default=0,
            min_value=0,
            max_value=15,
            description='Index of the monitor to capture from'
        ))
        
        self.add_option(ConfigOption(
            name='capture.fallback_enabled',
            type=bool,
            default=True,
            description='Use fallback capture method when primary fails'
        ))
        self.add_option(ConfigOption(
            name='capture.enhance_small_text',
            type=bool,
            default=True,
            description='Enhance small text in captured regions'
        ))
        self.add_option(ConfigOption(
            name='capture.enhance_denoise',
            type=bool,
            default=True,
            description='Apply denoising to captured images'
        ))
        self.add_option(ConfigOption(
            name='capture.enhance_binarize',
            type=bool,
            default=False,
            description='Apply binarization to captured images'
        ))
        self.add_option(ConfigOption(
            name='capture.mode',
            type=str,
            default='directx',
            description='Capture mode (e.g. directx, full_screen)'
        ))
        self.add_option(ConfigOption(
            name='capture.region',
            type=str,
            default='custom',
            description='Capture region type (e.g. custom, full_screen)'
        ))
        self.add_option(ConfigOption(
            name='capture.regions',
            type=list,
            default=[],
            description='List of multi-capture regions'
        ))
        self.add_option(ConfigOption(
            name='capture.capture_mode',
            type=str,
            default='continuous',
            description='Capture mode: continuous or single'
        ))
        self.add_option(ConfigOption(
            name='capture.capture_interval',
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=60.0,
            description='Interval between captures in seconds'
        ))
        self.add_option(ConfigOption(
            name='capture.adaptive',
            type=bool,
            default=True,
            description='Use adaptive capture settings'
        ))
        self.add_option(ConfigOption(
            name='capture.monitor',
            type=str,
            default='primary',
            description='Monitor selection (e.g. primary, index)'
        ))
        self.add_option(ConfigOption(
            name='capture.multi_region_config',
            type=dict,
            default={},
            description='Configuration for multi-region capture'
        ))
        self.add_option(ConfigOption(
            name='capture.last_overlay_region',
            type=type(None),
            default=None,
            description='Last used overlay region (nullable)'
        ))
        self.add_option(ConfigOption(
            name='capture.selected_presets',
            type=list,
            default=[],
            description='Selected capture region presets'
        ))
        self.add_option(ConfigOption(
            name='capture.custom_region',
            type=dict,
            default={'x': 0, 'y': 0, 'width': 800, 'height': 600},
            description='Custom capture region {x, y, width, height}'
        ))
        self.add_option(ConfigOption(
            name='capture.active_region_ids',
            type=list,
            default=[],
            description='IDs of currently active capture regions'
        ))
        
        # OCR settings
        self.add_option(ConfigOption(
            name='ocr.engine',
            type=str,
            default='easyocr',
            description='OCR engine to use for text recognition'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.confidence_threshold',
            type=float,
            default=0.5,
            min_value=0.0,
            max_value=1.0,
            description='Minimum confidence threshold for OCR results'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.max_retries',
            type=int,
            default=3,
            min_value=0,
            max_value=10,
            description='Maximum number of OCR retry attempts'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.languages',
            type=list,
            default=['en'],
            description='List of languages for OCR recognition'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.preprocessing_enabled',
            type=bool,
            default=False,
            description='Enable image preprocessing before OCR (scaling, denoising, thresholding)'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.preprocessing_intelligent',
            type=bool,
            default=True,
            description='Use intelligent preprocessing that auto-detects when enhancement is needed'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.manga_bubble_detection',
            type=bool,
            default=False,
            description='Enable manga speech bubble detection'
        ))
        self.add_option(ConfigOption(
            name='ocr.source_language',
            type=str,
            default='en',
            description='Source language for OCR'
        ))
        self.add_option(ConfigOption(
            name='ocr.language',
            type=str,
            default='en',
            description='OCR language code'
        ))
        self.add_option(ConfigOption(
            name='ocr.default_engine',
            type=str,
            default='easyocr',
            description='Default OCR engine when using judge or fallback'
        ))
        self.add_option(ConfigOption(
            name='ocr.easyocr_config',
            type=dict,
            default={'gpu': True},
            description='EasyOCR engine configuration'
        ))
        self.add_option(ConfigOption(
            name='ocr.paddleocr_config',
            type=dict,
            default={'use_gpu': True},
            description='PaddleOCR engine configuration'
        ))
        
        # Judge OCR config
        self.add_option(ConfigOption(
            name='ocr.judge_ocr_config.engines',
            type=list,
            default=[],
            description='List of OCR engine names for Judge OCR to run and vote across'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.judge_ocr_config.voting_strategy',
            type=str,
            default='majority_vote',
            choices=['majority_vote', 'weighted_confidence', 'quorum', 'best_confidence'],
            description='Voting strategy used to pick the winning text from multiple engines'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.judge_ocr_config.quorum_count',
            type=int,
            default=2,
            min_value=1,
            max_value=10,
            description='Minimum number of engines that must agree for quorum voting'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.judge_ocr_config.engine_thresholds',
            type=dict,
            default={},
            description='Per-engine confidence thresholds (e.g. {"easyocr": 0.4, "paddleocr": 0.5})'
        ))
        
        self.add_option(ConfigOption(
            name='ocr.judge_ocr_config.parallel_execution',
            type=bool,
            default=True,
            description='Run sub-engines in parallel via ThreadPoolExecutor'
        ))
        
        # Translation settings
        self.add_option(ConfigOption(
            name='translation.engine',
            type=str,
            default='marianmt_gpu',
            description='Translation engine to use (valid engines discovered from plugins at runtime)'
        ))
        
        self.add_option(ConfigOption(
            name='translation.source_language',
            type=str,
            default='en',
            description='Source language code for translation'
        ))
        
        self.add_option(ConfigOption(
            name='translation.target_language',
            type=str,
            default='de',
            description='Target language code for translation'
        ))
        
        self.add_option(ConfigOption(
            name='translation.batch_size',
            type=int,
            default=10,
            min_value=1,
            max_value=100,
            description='Number of texts to translate in a single batch'
        ))

        self.add_option(ConfigOption(
            name='translation.quality_level',
            type=int,
            default=70,
            min_value=0,
            max_value=100,
            description='Quality vs speed tradeoff slider (0 = fastest, 100 = highest quality)'
        ))

        self.add_option(ConfigOption(
            name='translation.fallback_enabled',
            type=bool,
            default=True,
            description='When the primary translation engine fails, automatically try other available engines'
        ))

        self.add_option(ConfigOption(
            name='translation.preserve_formatting',
            type=bool,
            default=True,
            description='Preserve original text formatting (bold, italic, line breaks) in translations'
        ))

        self.add_option(ConfigOption(
            name='translation.context',
            type=str,
            default='',
            description='Optional context passed to the translation engine (e.g. "Manga dialogue", "Technical document") for LLM-based engines'
        ))
        
        self.add_option(ConfigOption(
            name='translation.multilingual_model_name',
            type=str,
            default='facebook/nllb-200-1.3B',
            description='HuggingFace model name for multilingual NLLB translation'
        ))
        self.add_option(ConfigOption(
            name='translation.batch_translation',
            type=bool,
            default=True,
            description='Enable batch translation for multiple segments'
        ))
        self.add_option(ConfigOption(
            name='translation.context_aware',
            type=bool,
            default=True,
            description='Use context-aware translation when available'
        ))
        
        self.add_option(ConfigOption(
            name='cache.translation_cache_size',
            type=int,
            default=10000,
            min_value=100,
            max_value=1000000,
            description='Maximum number of entries in the translation cache'
        ))

        self.add_option(ConfigOption(
            name='cache.translation_cache_ttl',
            type=int,
            default=3600,
            min_value=60,
            max_value=86400,
            description='Time-to-live for translation cache entries in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='cache.dictionary_cache_size',
            type=int,
            default=1000,
            min_value=100,
            max_value=100000,
            description='Maximum dictionary cache entries'
        ))
        self.add_option(ConfigOption(
            name='cache.frame_cache_size',
            type=int,
            default=100,
            min_value=0,
            max_value=1000,
            description='Frame cache size'
        ))
        self.add_option(ConfigOption(
            name='cache.frame_cache_memory_mb',
            type=float,
            default=50.0,
            min_value=0.0,
            max_value=1000.0,
            description='Frame cache memory limit in MB'
        ))
        self.add_option(ConfigOption(
            name='cache.ocr_cache_size',
            type=int,
            default=500,
            min_value=0,
            max_value=10000,
            description='OCR result cache size'
        ))
        self.add_option(ConfigOption(
            name='cache.ocr_cache_memory_mb',
            type=float,
            default=20.0,
            min_value=0.0,
            max_value=500.0,
            description='OCR cache memory limit in MB'
        ))
        self.add_option(ConfigOption(
            name='cache.translation_cache_memory_mb',
            type=float,
            default=10.0,
            min_value=0.0,
            max_value=500.0,
            description='Translation cache memory limit in MB'
        ))
        
        self.add_option(ConfigOption(
            name='translation.quality_filter_enabled',
            type=bool,
            default=True,
            description='Enable quality filter to prevent low-quality translations from being saved to the dictionary'
        ))
        
        self.add_option(ConfigOption(
            name='translation.quality_filter_mode',
            type=int,
            default=0,
            min_value=0,
            max_value=1,
            description='Quality filter strictness: 0 = balanced, 1 = strict'
        ))
        
        # Performance settings
        self.add_option(ConfigOption(
            name='performance.enable_gpu',
            type=bool,
            default=True,
            description='Enable GPU acceleration if available'
        ))
        
        self.add_option(ConfigOption(
            name='performance.enable_frame_skip',
            type=bool,
            default=True,
            description='Enable frame skipping to improve performance'
        ))
        
        self.add_option(ConfigOption(
            name='performance.enable_translation_cache',
            type=bool,
            default=True,
            description='Enable caching of translation results'
        ))
        
        self.add_option(ConfigOption(
            name='performance.enable_smart_dictionary',
            type=bool,
            default=True,
            description='Enable smart dictionary for improved translations'
        ))
        
        self.add_option(ConfigOption(
            name='performance.runtime_mode',
            type=str,
            default='gpu',
            choices=['auto', 'gpu', 'cpu'],
            description='Runtime mode: auto (detect), gpu, or cpu'
        ))
        self.add_option(ConfigOption(
            name='performance.worker_threads',
            type=int,
            default=4,
            min_value=1,
            max_value=64,
            description='Number of worker threads for pipeline stages'
        ))
        self.add_option(ConfigOption(
            name='performance.queue_size',
            type=int,
            default=16,
            min_value=2,
            max_value=256,
            description='Queue size for pipeline stage buffers'
        ))
        self.add_option(ConfigOption(
            name='performance.ocr_batch_size',
            type=int,
            default=8,
            min_value=1,
            max_value=64,
            description='Batch size for OCR processing'
        ))
        self.add_option(ConfigOption(
            name='performance.translation_batch_size',
            type=int,
            default=16,
            min_value=1,
            max_value=128,
            description='Batch size for translation processing'
        ))
        self.add_option(ConfigOption(
            name='performance.batch_wait_time_ms',
            type=float,
            default=20.0,
            min_value=0.0,
            max_value=1000.0,
            description='Max wait time in ms to fill a batch'
        ))
        self.add_option(ConfigOption(
            name='performance.enable_parallel_processing',
            type=bool,
            default=True,
            description='Enable parallel processing where supported'
        ))
        self.add_option(ConfigOption(
            name='performance.enable_gpu_acceleration',
            type=bool,
            default=True,
            description='Enable GPU acceleration for supported stages'
        ))
        
        # Pipeline execution settings
        self.add_option(ConfigOption(
            name='pipeline.queue_size',
            type=int,
            default=16,
            min_value=2,
            max_value=128,
            description='Per-stage input queue depth for the async pipeline strategy'
        ))
        
        self.add_option(ConfigOption(
            name='pipeline.max_workers',
            type=int,
            default=4,
            min_value=1,
            max_value=16,
            description='Maximum worker threads for async and custom pipeline strategies'
        ))
        
        self.add_option(ConfigOption(
            name='pipeline.execution_mode',
            type=str,
            default='sequential',
            choices=['sequential', 'async', 'custom', 'subprocess'],
            description='Pipeline execution strategy (subprocess runs OCR in an isolated process for crash resilience)'
        ))
        
        self.add_option(ConfigOption(
            name='pipeline.mode',
            type=str,
            default='text',
            choices=['text', 'vision', 'audio'],
            description='Active pipeline mode: text (OCR-based), vision (Qwen3-VL single-model), or audio (speech translation)'
        ))
        
        self.add_option(ConfigOption(
            name='pipeline.enable_optimizer_plugins',
            type=bool,
            default=False,
            description='Enable optional optimizer plugins for additional speed'
        ))

        # Benchmark settings
        self.add_option(ConfigOption(
            name='benchmark.last_mode_selection',
            type=list,
            default=['text', 'vision'],
            description='Last selected modes for the benchmark dialog (e.g. text, vision)'
        ))
        self.add_option(ConfigOption(
            name='benchmark.last_execution_selection',
            type=list,
            default=['sequential', 'async'],
            description='Last selected execution modes for the benchmark dialog'
        ))
        self.add_option(ConfigOption(
            name='benchmark.last_scope',
            type=str,
            default='fast',
            choices=['fast', 'full', 'custom'],
            description='Last selected benchmark scope preset'
        ))
        self.add_option(ConfigOption(
            name='benchmark.last_selected_ocr_engines',
            type=list,
            default=[],
            description='Last selected OCR engines for custom benchmark scope'
        ))
        self.add_option(ConfigOption(
            name='benchmark.last_selected_translation_engines',
            type=list,
            default=[],
            description='Last selected translation engines for custom benchmark scope'
        ))
        self.add_option(ConfigOption(
            name='benchmark.last_full_run_timestamp',
            type=str,
            default='',
            description='ISO timestamp of the last completed benchmark run'
        ))
        self.add_option(ConfigOption(
            name='benchmark.last_full_run_path',
            type=str,
            default='',
            description='Path to the JSON file of the last completed benchmark run'
        ))

        self.add_option(ConfigOption(
            name='plugins.context_manager.enabled',
            type=bool,
            default=True,
            description='Enable the Context Manager plugin for locked terms and context-aware translation'
        ))
        
        self.add_option(ConfigOption(
            name='plugins.context_manager.active_profile',
            type=str,
            default='',
            description='Name of the active context manager profile'
        ))
        
        # Vision settings (Qwen3-VL pipeline)
        self.add_option(ConfigOption(
            name='vision.model_name',
            type=str,
            default='Qwen/Qwen3-VL-4B-Instruct',
            description='HuggingFace model name for the Qwen3-VL vision-language model'
        ))
        
        self.add_option(ConfigOption(
            name='vision.max_tokens',
            type=int,
            default=512,
            min_value=64,
            max_value=4096,
            description='Maximum output tokens for vision model generation'
        ))
        
        self.add_option(ConfigOption(
            name='vision.temperature',
            type=float,
            default=0.3,
            min_value=0.0,
            max_value=2.0,
            description='Sampling temperature for vision model (lower = more deterministic)'
        ))
        
        self.add_option(ConfigOption(
            name='vision.quantization',
            type=str,
            default='none',
            choices=['none', '4bit', '8bit'],
            description='Quantization mode for the vision model (requires bitsandbytes for 4bit/8bit)'
        ))
        
        self.add_option(ConfigOption(
            name='vision.use_gpu',
            type=bool,
            default=True,
            description='Use GPU (CUDA) for the vision model when available; disable to force CPU'
        ))
        self.add_option(ConfigOption(
            name='vision.enabled',
            type=bool,
            default=True,
            description='Master toggle for vision pipeline mode availability'
        ))
        
        self.add_option(ConfigOption(
            name='vision.prompt_template',
            type=str,
            default='Extract all visible text from this image and translate it from {source_lang} to {target_lang}. For each text region, return the translated text and its approximate bounding box as JSON: [{{"text": "...", "bbox": [x, y, w, h]}}]. Only return the JSON array, no other text.',
            description='Prompt template for vision translation. Use {source_lang} and {target_lang} placeholders.'
        ))
        self.add_option(ConfigOption(
            name='vision.context',
            type=str,
            default='',
            description='Optional context prepended to the vision prompt (e.g. "This is manga dialogue").'
        ))
        self.add_option(ConfigOption(
            name='translation.qwen_prompt_template',
            type=str,
            default='You are a deterministic machine translation engine.\nTranslate the provided SOURCE_TEXT into {target_lang}.\nRules:\n1) Return ONLY the translation in {target_lang}.\n2) Do NOT explain, summarize, answer, or add notes.\n3) Preserve names, numbers, punctuation, and line breaks where possible.\n4) If text is already in {target_lang}, return it unchanged.',
            description='Prompt template for the Qwen3 text translation engine. Use {source_lang} and {target_lang} placeholders.'
        ))
        
        # API key settings (sensitive) — stored under translation.*
        # to match the keys the UI and translation engines actually use.
        self.add_option(ConfigOption(
            name='translation.google_api_key',
            type=str,
            default='',
            sensitive=True,
            description='Google Translate API key'
        ))
        
        self.add_option(ConfigOption(
            name='translation.deepl_api_key',
            type=str,
            default='',
            sensitive=True,
            description='DeepL API key'
        ))
        
        self.add_option(ConfigOption(
            name='translation.azure_api_key',
            type=str,
            default='',
            sensitive=True,
            description='Azure Translator API key'
        ))
        
        self.add_option(ConfigOption(
            name='translation.azure_region',
            type=str,
            default='global',
            description='Azure Translator service region'
        ))
        
        # Critical hardcoded values - URLs
        self.add_option(ConfigOption(
            name='urls.libretranslate_api',
            type=str,
            default='https://libretranslate.com',
            description='LibreTranslate API base URL'
        ))
        
        self.add_option(ConfigOption(
            name='urls.azure_translator_endpoint',
            type=str,
            default='https://api.cognitive.microsofttranslator.com',
            description='Azure Translator API endpoint'
        ))
        
        self.add_option(ConfigOption(
            name='urls.pytorch_cpu_index',
            type=str,
            default='https://download.pytorch.org/whl/cpu',
            description='PyTorch CPU package index URL'
        ))
        
        self.add_option(ConfigOption(
            name='urls.pytorch_cuda118_index',
            type=str,
            default='https://download.pytorch.org/whl/cu118',
            description='PyTorch CUDA 11.8 package index URL'
        ))
        
        self.add_option(ConfigOption(
            name='urls.pytorch_cuda121_index',
            type=str,
            default='https://download.pytorch.org/whl/cu121',
            description='PyTorch CUDA 12.1 package index URL'
        ))
        
        self.add_option(ConfigOption(
            name='urls.pytorch_cuda124_index',
            type=str,
            default='https://download.pytorch.org/whl/cu124',
            description='PyTorch CUDA 12.4 package index URL'
        ))
        
        self.add_option(ConfigOption(
            name='urls.tesseract_data',
            type=str,
            default='https://github.com/tesseract-ocr/tessdata',
            description='Tesseract language data repository URL'
        ))
        
        # Critical hardcoded values - Timeouts
        self.add_option(ConfigOption(
            name='timeouts.capture_stage_seconds',
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=10.0,
            description='Timeout for capture stage in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.preprocessing_stage_seconds',
            type=float,
            default=0.5,
            min_value=0.1,
            max_value=5.0,
            description='Timeout for preprocessing stage in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.ocr_stage_seconds',
            type=float,
            default=2.0,
            min_value=0.5,
            max_value=30.0,
            description='Timeout for OCR stage in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.validation_stage_seconds',
            type=float,
            default=0.5,
            min_value=0.1,
            max_value=5.0,
            description='Timeout for validation stage in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.translation_stage_seconds',
            type=float,
            default=3.0,
            min_value=0.5,
            max_value=60.0,
            description='Timeout for translation stage in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.overlay_stage_seconds',
            type=float,
            default=0.5,
            min_value=0.1,
            max_value=5.0,
            description='Timeout for overlay stage in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.pipeline_stop_seconds',
            type=float,
            default=5.0,
            min_value=1.0,
            max_value=30.0,
            description='Timeout for pipeline stop operation in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.thread_join_seconds',
            type=float,
            default=2.0,
            min_value=0.5,
            max_value=10.0,
            description='Timeout for thread join operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.subprocess_ready_seconds',
            type=float,
            default=10.0,
            min_value=5.0,
            max_value=60.0,
            description='Timeout for subprocess ready signal in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.subprocess_stop_seconds',
            type=float,
            default=5.0,
            min_value=1.0,
            max_value=30.0,
            description='Timeout for subprocess stop operation in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.subprocess_terminate_seconds',
            type=float,
            default=2.0,
            min_value=0.5,
            max_value=10.0,
            description='Timeout for subprocess terminate operation in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.translation_pool_seconds',
            type=float,
            default=15.0,
            min_value=5.0,
            max_value=120.0,
            description='Timeout for translation pool operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.health_monitor_seconds',
            type=float,
            default=5.0,
            min_value=1.0,
            max_value=30.0,
            description='Timeout for health monitor stop in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.nvidia_smi_seconds',
            type=float,
            default=5.0,
            min_value=1.0,
            max_value=30.0,
            description='Timeout for nvidia-smi command in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.pip_uninstall_seconds',
            type=float,
            default=120.0,
            min_value=30.0,
            max_value=600.0,
            description='Timeout for pip uninstall operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='timeouts.pip_install_seconds',
            type=float,
            default=600.0,
            min_value=60.0,
            max_value=3600.0,
            description='Timeout for pip install operations in seconds'
        ))
        
        # Critical hardcoded values - File paths
        self.add_option(ConfigOption(
            name='paths.user_data_dir',
            type=str,
            default='user_data',
            description='Directory for user data storage'
        ))
        
        self.add_option(ConfigOption(
            name='paths.models_dir',
            type=str,
            default='models',
            description='Directory for AI models storage'
        ))
        
        self.add_option(ConfigOption(
            name='paths.cache_dir',
            type=str,
            default='cache',
            description='Directory for cache storage'
        ))
        
        self.add_option(ConfigOption(
            name='paths.temp_dir',
            type=str,
            default='temp',
            description='Directory for temporary files'
        ))
        
        self.add_option(ConfigOption(
            name='paths.config_file',
            type=str,
            default='user_data/config/user_config.json',
            description='Path to user configuration file'
        ))
        
        self.add_option(ConfigOption(
            name='paths.image_processing_presets_dir',
            type=str,
            default='user_data/image_processing_presets',
            description='Directory for user-defined image processing preset files'
        ))
        
        # Overlay settings
        self.add_option(ConfigOption(
            name='overlay.disappear_timeout_seconds',
            type=float,
            default=2.0,
            min_value=0.1,
            max_value=30.0,
            description='Time before overlay disappears in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.save_interval',
            type=int,
            default=100,
            min_value=1,
            max_value=1000,
            description='Number of translations before auto-save'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.font_size',
            type=int,
            default=14,
            min_value=8,
            max_value=72,
            description='Font size for overlay text in points'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.opacity',
            type=float,
            default=0.8,
            min_value=0.0,
            max_value=1.0,
            description='Overlay opacity (0.0 = fully transparent, 1.0 = fully opaque)'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.collision_padding',
            type=int,
            default=5,
            min_value=0,
            max_value=50,
            description='Padding between overlay boxes to prevent overlap in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.screen_margin',
            type=int,
            default=10,
            min_value=0,
            max_value=100,
            description='Margin from screen edges for overlay placement in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.max_text_width',
            type=int,
            default=60,
            min_value=20,
            max_value=200,
            description='Maximum text width for overlay boxes in characters'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.animation_duration',
            type=int,
            default=300,
            min_value=100,
            max_value=2000,
            description='Duration of overlay show/hide animations in milliseconds'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.auto_hide_delay',
            type=int,
            default=0,
            min_value=0,
            max_value=30000,
            description='Delay before overlay auto-hides in milliseconds (0 = permanent)'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.positioning_mode',
            type=str,
            default='intelligent',
            choices=['simple', 'intelligent'],
            description='Overlay positioning strategy'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.grid_cell_size',
            type=int,
            default=50,
            min_value=10,
            max_value=200,
            description='Grid cell size in pixels for stable overlay ID tracking'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.animation_in',
            type=str,
            default='FADE',
            choices=['FADE', 'SLIDE', 'SCALE', 'NONE'],
            description='Animation type when overlay appears'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.animation_out',
            type=str,
            default='FADE',
            choices=['FADE', 'SLIDE', 'SCALE', 'NONE'],
            description='Animation type when overlay disappears'
        ))
        
        self.add_option(ConfigOption(
            name='overlay.font_family',
            type=str,
            default='Segoe UI',
            description='Font family for overlay text'
        ))
        self.add_option(ConfigOption(
            name='overlay.font_color',
            type=str,
            default='#ffffff',
            description='Overlay text color (hex)'
        ))
        self.add_option(ConfigOption(
            name='overlay.background_color',
            type=str,
            default='#000000',
            description='Overlay background color (hex)'
        ))
        self.add_option(ConfigOption(
            name='overlay.border_color',
            type=str,
            default='#646464',
            description='Overlay border color (hex)'
        ))
        self.add_option(ConfigOption(
            name='overlay.transparency',
            type=float,
            default=0.8,
            min_value=0.0,
            max_value=1.0,
            description='Overlay transparency (0=transparent, 1=opaque); prefer overlay.opacity as canonical'
        ))
        self.add_option(ConfigOption(
            name='overlay.animation_enabled',
            type=bool,
            default=True,
            description='Enable overlay show/hide animations'
        ))
        self.add_option(ConfigOption(
            name='overlay.auto_hide_on_disappear',
            type=bool,
            default=True,
            description='Auto-hide overlay when source text disappears'
        ))
        self.add_option(ConfigOption(
            name='overlay.interactive_on_hover',
            type=bool,
            default=False,
            description='Make overlay interactive on hover'
        ))
        self.add_option(ConfigOption(
            name='overlay.rounded_corners',
            type=bool,
            default=True,
            description='Use rounded corners for overlay boxes'
        ))
        self.add_option(ConfigOption(
            name='overlay.auto_font_size',
            type=bool,
            default=True,
            description='Automatically scale font size to fit overlay'
        ))
        self.add_option(ConfigOption(
            name='overlay.visible_in_screenshots',
            type=bool,
            default=False,
            description='Include overlay in screenshots'
        ))
        self.add_option(ConfigOption(
            name='overlay.region',
            type=dict,
            default={'x': 0, 'y': 0, 'width': 800, 'height': 600},
            description='Overlay placement region {x, y, width, height}'
        ))
        
        # High-priority hardcoded values - Thresholds
        self.add_option(ConfigOption(
            name='thresholds.queue_get_timeout_seconds',
            type=float,
            default=0.1,
            min_value=0.01,
            max_value=5.0,
            description='Timeout for queue get operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='thresholds.worker_scale_timeout_seconds',
            type=float,
            default=2.0,
            min_value=0.5,
            max_value=10.0,
            description='Timeout for worker scaling operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='thresholds.batch_coordinator_timeout_seconds',
            type=float,
            default=2.0,
            min_value=0.5,
            max_value=10.0,
            description='Timeout for batch coordinator thread join in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='thresholds.async_wait_timeout_seconds',
            type=float,
            default=0.1,
            min_value=0.01,
            max_value=5.0,
            description='Timeout for async wait operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='thresholds.resource_task_timeout_seconds',
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=10.0,
            description='Timeout for resource allocation task retrieval in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='thresholds.background_queue_timeout_seconds',
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=10.0,
            description='Timeout for background queue operations in seconds'
        ))
        
        self.add_option(ConfigOption(
            name='thresholds.subprocess_message_timeout_seconds',
            type=float,
            default=0.1,
            min_value=0.01,
            max_value=5.0,
            description='Timeout for subprocess message receive in seconds'
        ))
        
        # Logging settings
        self.add_option(ConfigOption(
            name='logging.log_level',
            type=str,
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            description='Application log level'
        ))
        
        # Advanced settings
        self.add_option(ConfigOption(
            name='advanced.debug_mode',
            type=bool,
            default=False,
            description='Enable debug mode with verbose diagnostics'
        ))
        
        self.add_option(ConfigOption(
            name='advanced.enable_monitoring',
            type=bool,
            default=False,
            description='Enable performance monitoring'
        ))
        
        self.add_option(ConfigOption(
            name='advanced.experimental_features',
            type=list,
            default=[],
            description='List of enabled experimental feature IDs'
        ))
        
        self.add_option(ConfigOption(
            name='advanced.quiet_console',
            type=bool,
            default=False,
            description='Reduce console output (quiet mode)'
        ))
        
        # ROI detection settings
        self.add_option(ConfigOption(
            name='roi_detection.min_region_width',
            type=int,
            default=50,
            min_value=10,
            max_value=500,
            description='Minimum width of detected text regions in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.min_region_height',
            type=int,
            default=20,
            min_value=10,
            max_value=500,
            description='Minimum height of detected text regions in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.max_region_width',
            type=int,
            default=2000,
            min_value=100,
            max_value=5000,
            description='Maximum width of detected text regions in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.max_region_height',
            type=int,
            default=1000,
            min_value=100,
            max_value=5000,
            description='Maximum height of detected text regions in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.padding',
            type=int,
            default=10,
            min_value=0,
            max_value=50,
            description='Extra padding around detected text regions in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.merge_distance',
            type=int,
            default=20,
            min_value=0,
            max_value=100,
            description='Distance threshold for merging nearby text regions in pixels'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.confidence_threshold',
            type=float,
            default=0.3,
            min_value=0.0,
            max_value=1.0,
            description='Minimum confidence for text region detection'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.adaptive_threshold',
            type=bool,
            default=True,
            description='Use adaptive thresholding for text detection'
        ))
        
        self.add_option(ConfigOption(
            name='roi_detection.use_morphology',
            type=bool,
            default=True,
            description='Use morphological operations to connect text regions'
        ))
        
        # Retry counts
        self.add_option(ConfigOption(
            name='retries.model_download_max',
            type=int,
            default=3,
            min_value=1,
            max_value=10,
            description='Maximum retry attempts for model downloads'
        ))
        
        self.add_option(ConfigOption(
            name='retries.translation_max',
            type=int,
            default=3,
            min_value=1,
            max_value=10,
            description='Maximum retry attempts for translation operations'
        ))
        
        self.add_option(ConfigOption(
            name='retries.api_request_max',
            type=int,
            default=3,
            min_value=1,
            max_value=10,
            description='Maximum retry attempts for API requests'
        ))
        
        # Image processing settings
        self.add_option(ConfigOption(
            name='image_processing.output_format',
            type=str,
            default='same',
            choices=['same', 'png', 'jpg', 'bmp'],
            description='Output image format (same keeps the original format)'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.jpg_quality',
            type=int,
            default=95,
            min_value=1,
            max_value=100,
            description='JPEG output quality (1-100)'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.naming_pattern',
            type=str,
            default='suffix',
            choices=['suffix', 'prefix', 'subfolder'],
            description='How to name output files relative to the originals'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.naming_suffix',
            type=str,
            default='_translated',
            description='Suffix or prefix string appended/prepended to output filenames'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.erase_original_text',
            type=bool,
            default=True,
            description='Erase the original text from the image before rendering translation'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.inpaint_method',
            type=str,
            default='solid_fill',
            choices=['solid_fill', 'inpaint'],
            description='Method used to erase original text (solid fill or OpenCV inpaint)'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.font_family',
            type=str,
            default='Segoe UI',
            description='Font family used to render translated text onto images'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.font_size',
            type=int,
            default=16,
            min_value=8,
            max_value=72,
            description='Font size in points for rendered translated text'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.auto_font_size',
            type=bool,
            default=True,
            description='Automatically scale font size to fit the detected bounding box'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.text_color',
            type=str,
            default='#FFFFFF',
            description='Hex color of the rendered translated text'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.background_color',
            type=str,
            default='#000000',
            description='Hex color of the background rectangle behind translated text'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.background_enabled',
            type=bool,
            default=True,
            description='Draw a background rectangle behind translated text'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.background_opacity',
            type=float,
            default=0.85,
            min_value=0.0,
            max_value=1.0,
            description='Opacity of the background rectangle (0.0 transparent, 1.0 opaque)'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.border_enabled',
            type=bool,
            default=False,
            description='Draw a border around the translated text background'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.padding',
            type=int,
            default=6,
            min_value=0,
            max_value=30,
            description='Padding in pixels between text and its background rectangle'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.use_main_ocr_settings',
            type=bool,
            default=True,
            description='Use the main application OCR settings instead of per-image overrides'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.use_main_translation_settings',
            type=bool,
            default=True,
            description='Use the main application translation settings instead of per-image overrides'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.last_input_folder',
            type=str,
            default='',
            description='Last used input folder path for the file picker'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.last_output_folder',
            type=str,
            default='',
            description='Last used output folder path for the file picker'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.active_preset',
            type=str,
            default='',
            description='Name of the currently active preset (empty = custom/manual)'
        ))
        
        self.add_option(ConfigOption(
            name='image_processing.last_used_preset_type',
            type=str,
            default='content',
            choices=['content', 'style', 'custom'],
            description='Category of the last applied preset'
        ))
        
        # UI settings
        self.add_option(ConfigOption(
            name='ui.language',
            type=str,
            default='en',
            description='UI language code (e.g. en, de)'
        ))
        self.add_option(ConfigOption(
            name='ui.dark_mode',
            type=bool,
            default=True,
            description='Use dark theme for the application'
        ))
        self.add_option(ConfigOption(
            name='ui.window_x',
            type=int,
            default=-1760,
            description='Main window X position'
        ))
        self.add_option(ConfigOption(
            name='ui.window_y',
            type=int,
            default=136,
            description='Main window Y position'
        ))
        self.add_option(ConfigOption(
            name='ui.window_width',
            type=int,
            default=1600,
            min_value=100,
            max_value=10000,
            description='Main window width'
        ))
        self.add_option(ConfigOption(
            name='ui.window_height',
            type=int,
            default=1168,
            min_value=100,
            max_value=10000,
            description='Main window height'
        ))
        
        # Startup settings
        self.add_option(ConfigOption(
            name='startup.minimize_to_tray',
            type=bool,
            default=False,
            description='Minimize to system tray instead of taskbar'
        ))
        self.add_option(ConfigOption(
            name='startup.show_setup_wizard',
            type=bool,
            default=False,
            description='Show setup wizard on next launch'
        ))
        self.add_option(ConfigOption(
            name='general.manga_mode',
            type=bool,
            default=False,
            description='Treat small changes (e.g. mouse in region) as unchanged to reduce false re-translation when reading manga'
        ))
        self.add_option(ConfigOption(
            name='general.pipeline_toggle_hotkey',
            type=str,
            default='Ctrl+T',
            description='Keyboard shortcut used to trigger the translation pipeline action'
        ))
        
        # Dictionary settings
        self.add_option(ConfigOption(
            name='dictionary.auto_learn',
            type=bool,
            default=True,
            description='Automatically learn new translations'
        ))
        self.add_option(ConfigOption(
            name='dictionary.learn_words',
            type=bool,
            default=True,
            description='Learn single words to the dictionary'
        ))
        self.add_option(ConfigOption(
            name='dictionary.learn_sentences',
            type=bool,
            default=True,
            description='Learn full sentences to the dictionary'
        ))
        self.add_option(ConfigOption(
            name='dictionary.extract_words_on_stop',
            type=bool,
            default=True,
            description='Extract words when stopping translation'
        ))
        self.add_option(ConfigOption(
            name='dictionary.min_confidence',
            type=float,
            default=0.7,
            min_value=0.0,
            max_value=1.0,
            description='Minimum confidence for dictionary entries'
        ))
        self.add_option(ConfigOption(
            name='dictionary.max_entries',
            type=int,
            default=999999,
            min_value=100,
            max_value=9999999,
            description='Maximum dictionary entries per language pair'
        ))
        
        # Storage settings
        self.add_option(ConfigOption(
            name='storage.cache_enabled',
            type=bool,
            default=True,
            description='Enable cache storage'
        ))
        self.add_option(ConfigOption(
            name='storage.cache_size_mb',
            type=float,
            default=500.0,
            min_value=0.0,
            max_value=10000.0,
            description='Maximum cache size in MB'
        ))
        self.add_option(ConfigOption(
            name='storage.retention_days',
            type=int,
            default=30,
            min_value=1,
            max_value=365,
            description='Days to retain cache data'
        ))
        self.add_option(ConfigOption(
            name='storage.periodic_cache_clear_enabled',
            type=bool,
            default=False,
            description='Enable periodic cache cleanup'
        ))
        
        # LLM settings
        self.add_option(ConfigOption(
            name='llm.enabled',
            type=bool,
            default=False,
            description='Enable LLM pipeline stage'
        ))
        self.add_option(ConfigOption(
            name='llm.engine',
            type=str,
            default='qwen3',
            choices=['qwen3'],
            description='LLM engine to use'
        ))
        self.add_option(ConfigOption(
            name='llm.mode',
            type=str,
            default='refine',
            description='LLM processing mode (e.g. refine, translate)'
        ))
        self.add_option(ConfigOption(
            name='llm.model_name',
            type=str,
            default='Qwen/Qwen3-1.7B',
            description='LLM model name or path'
        ))
        self.add_option(ConfigOption(
            name='llm.temperature',
            type=float,
            default=0.7,
            min_value=0.0,
            max_value=2.0,
            description='LLM sampling temperature'
        ))
        self.add_option(ConfigOption(
            name='llm.max_tokens',
            type=int,
            default=256,
            min_value=32,
            max_value=4096,
            description='Maximum output tokens for LLM'
        ))
        self.add_option(ConfigOption(
            name='llm.system_prompt',
            type=str,
            default='',
            description='Custom system prompt for LLM'
        ))
        
        # Consent (privacy / terms)
        self.add_option(ConfigOption(
            name='consent.consent_given',
            type=bool,
            default=False,
            description='User has accepted consent/terms'
        ))
        self.add_option(ConfigOption(
            name='consent.consent_date',
            type=str,
            default='',
            description='Date when consent was given (ISO)'
        ))
        self.add_option(ConfigOption(
            name='consent.version',
            type=str,
            default='pre-realese-1.0.0',
            description='Consent document version'
        ))
        
        # Installation (runtime / first-run)
        self.add_option(ConfigOption(
            name='installation.created',
            type=str,
            default='',
            description='Installation creation timestamp (ISO)'
        ))
        self.add_option(ConfigOption(
            name='installation.version',
            type=str,
            default='',
            description='Application version at installation'
        ))
        self.add_option(ConfigOption(
            name='installation.cuda',
            type=dict,
            default={'installed': False, 'path': ''},
            description='CUDA installation info'
        ))
        self.add_option(ConfigOption(
            name='installation.pytorch',
            type=dict,
            default={'version': '', 'cuda_available': False, 'device_name': ''},
            description='PyTorch/CUDA runtime info'
        ))
        
        # Presets (region presets, etc.)
        self.add_option(ConfigOption(
            name='presets.regions',
            type=dict,
            default={},
            description='Named region presets (capture + overlay regions)'
        ))
    
    def add_option(self, option: ConfigOption) -> None:
        """
        Add a configuration option to the schema.
        
        Args:
            option: The ConfigOption to add
        """
        self.options[option.name] = option
    
    def validate(self, key: str, value: Any) -> tuple[bool, str | None]:
        """
        Validate a configuration value against the schema.
        
        Args:
            key: Configuration key in dot notation
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if key not in self.options:
            logger.warning(f"Unknown configuration key: {key}")
            return True, None  # Allow unknown keys for backward compatibility
        
        option = self.options[key]
        return option.validate(value)
    
    def get_default(self, key: str) -> Any:
        """
        Get the default value for a configuration key.
        
        Args:
            key: Configuration key in dot notation
            
        Returns:
            Default value, or None if key not found
        """
        if key not in self.options:
            logger.warning(f"Unknown configuration key: {key}")
            return None
        
        return self.options[key].default
    
    def get_option(self, key: str) -> ConfigOption | None:
        """
        Get the ConfigOption for a key.
        
        Args:
            key: Configuration key in dot notation
            
        Returns:
            ConfigOption if found, None otherwise
        """
        return self.options.get(key)
    
    def get_all_options(self) -> dict[str, ConfigOption]:
        """
        Get all configuration options.
        
        Returns:
            Dictionary mapping keys to ConfigOptions
        """
        return self.options.copy()
    
    def get_sensitive_keys(self) -> list[str]:
        """
        Get list of all sensitive configuration keys.
        
        Returns:
            List of keys marked as sensitive
        """
        return [key for key, option in self.options.items() if option.sensitive]
    
    def validate_all(self, config: dict[str, Any]) -> list[str]:
        """
        Validate an entire configuration dictionary.
        
        Args:
            config: Configuration dictionary (may be nested)
            
        Returns:
            List of error messages (empty if all valid)
        """
        errors = []
        
        # Check required fields using nested lookup
        for key, option in self.options.items():
            if option.required:
                parts = key.split(".")
                obj = config
                found = True
                for p in parts:
                    if isinstance(obj, dict) and p in obj:
                        obj = obj[p]
                    else:
                        found = False
                        break
                if not found:
                    errors.append(f"Required configuration key missing: {key}")
        
        # Recursively validate leaf values against dotted schema keys
        self._validate_nested(config, "", errors)
        
        return errors

    def _validate_nested(self, obj: dict[str, Any], prefix: str,
                         errors: list[str]) -> None:
        """Walk a nested dict and validate each leaf against its schema entry."""
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._validate_nested(value, full_key, errors)
            elif full_key in self.options:
                is_valid, error_msg = self.options[full_key].validate(value)
                if not is_valid:
                    errors.append(f"{full_key}: {error_msg}")
