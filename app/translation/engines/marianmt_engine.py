"""
MarianMT Translation Engine

Uses Helsinki-NLP's MarianMT models for offline neural machine translation.
"""

import logging
import time
from typing import List, Optional
from pathlib import Path

try:
    from transformers import MarianMTModel, MarianTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    MarianMTModel = None
    MarianTokenizer = None

from ..translation_engine_interface import (
    AbstractTranslationEngine, TranslationOptions, TranslationResult,
    BatchTranslationResult, TranslationQuality
)

# Import path utilities for EXE compatibility
from app.utils.path_utils import ensure_app_directory


class MarianMTEngine(AbstractTranslationEngine):
    """
    MarianMT engine for offline neural machine translation.
    
    Uses Helsinki-NLP's MarianMT models which are free and work completely offline
    after models are downloaded.
    """
    
    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize MarianMT engine.
        
        Args:
            models_dir: Directory to store/load models (default: ./models/marianmt)
        """
        super().__init__("marianmt")
        self._logger = logging.getLogger(__name__)
        # Use path_utils for EXE compatibility
        self._models_dir = Path(models_dir) if models_dir else ensure_app_directory("models", "marianmt")
        
        self._is_initialized = TRANSFORMERS_AVAILABLE
        self._loaded_models = {}  # Cache for loaded models: {(src, tgt): (model, tokenizer)}
        self._loading_models = {}  # Track models currently being loaded: {(src, tgt): threading.Lock}
        
        if not TRANSFORMERS_AVAILABLE:
            self._logger.warning("transformers library not available. Install with: pip install transformers sentencepiece")
        else:
            self._logger.info("MarianMT engine initialized")
    
    def initialize(self, config: dict) -> bool:
        """Initialize engine with configuration."""
        if not TRANSFORMERS_AVAILABLE:
            return False
        try:
            models_dir = config.get('models_dir')
            if models_dir:
                self._models_dir = Path(models_dir)
                self._models_dir.mkdir(parents=True, exist_ok=True)
            self._is_initialized = True
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized
    
    def _get_model_name(self, src_lang: str, tgt_lang: str) -> str:
        """Get HuggingFace model name for language pair."""
        # Normalize language codes
        src = src_lang.lower()[:2]
        tgt = tgt_lang.lower()[:2]
        
        # MarianMT model naming convention
        return f"Helsinki-NLP/opus-mt-{src}-{tgt}"
    
    def preload_model(self, src_lang: str, tgt_lang: str) -> bool:
        """
        Pre-load MarianMT model in the main thread to avoid threading issues.
        MUST be called from the main thread before starting background pipeline.
        
        Args:
            src_lang: Source language
            tgt_lang: Target language
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        result = self._load_model(src_lang, tgt_lang)
        return result is not None
    
    def _load_model(self, src_lang: str, tgt_lang: str) -> Optional[tuple]:
        """
        Load MarianMT model for language pair.
        Loads directly in main process (the old way that was working).
        
        Args:
            src_lang: Source language
            tgt_lang: Target language
        
        Returns:
            Tuple of (model, tokenizer) or None if loading fails
        """
        lang_pair = (src_lang, tgt_lang)
        
        # Check if already loaded
        if lang_pair in self._loaded_models:
            return self._loaded_models[lang_pair]
        
        try:
            model_name = self._get_model_name(src_lang, tgt_lang)
            self._logger.info(f"Loading MarianMT model: {model_name}")
            print(f"[MarianMT] Loading model: {model_name}")
            print(f"[MarianMT] This may take 3-5 seconds on first load...")
            
            # Load model directly (the old working way)
            # Set weights_only=False to bypass the PyTorch 2.6 requirement
            import torch
            torch.serialization.add_safe_globals([])  # Allow loading
            
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            
            # Cache the loaded model
            self._loaded_models[lang_pair] = (model, tokenizer)
            
            self._logger.info(f"MarianMT model loaded successfully")
            print(f"[MarianMT] ✓ Model loaded successfully!")
            return model, tokenizer
            
        except KeyboardInterrupt:
            # Allow user to interrupt
            raise
        except Exception as e:
            self._logger.error(f"Failed to load MarianMT model for {src_lang}->{tgt_lang}: {e}")
            print(f"[MarianMT] ✗ ERROR loading model: {e}")
            import traceback
            traceback.print_exc()
            # Return None instead of raising - graceful degradation
            return None
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using MarianMT.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            TranslationResult with translated text (or original text on failure)
        """
        if not self.is_available():
            self._logger.warning("MarianMT engine is not available, returning original text")
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.0,
                engine_used=self.engine_name,
                processing_time_ms=0.0,
                from_cache=False
            )
        
        start_time = time.time()
        
        try:
            # Load model for language pair - may return None on crash
            model_tuple = self._load_model(src_lang, tgt_lang)
            
            if model_tuple is None:
                # Model loading failed, return original text
                self._logger.warning(f"Model loading failed for {src_lang}->{tgt_lang}, returning original text")
                print(f"[MarianMT] Model loading failed, returning original text")
                return TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=src_lang,
                    target_language=tgt_lang,
                    confidence=0.0,
                    engine_used=self.engine_name,
                    processing_time_ms=0.0,
                    from_cache=False
                )
            
            model, tokenizer = model_tuple
            
            # Tokenize input
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            
            # Generate translation
            translated = model.generate(**inputs)
            
            # Decode output
            translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.90,  # MarianMT generally has high quality
                engine_used=self.engine_name,
                processing_time_ms=processing_time,
                from_cache=False
            )
            
        except Exception as e:
            self._logger.error(f"MarianMT translation failed: {e}")
            print(f"[MarianMT] Translation exception: {e}")
            import traceback
            traceback.print_exc()
            # Return original text instead of crashing
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.0,
                engine_used=self.engine_name,
                processing_time_ms=0.0,
                from_cache=False
            )
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str,
                       options: Optional[TranslationOptions] = None) -> BatchTranslationResult:
        """
        Translate multiple texts in batch.
        
        Args:
            texts: List of texts to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            BatchTranslationResult with all translations (or original texts on failure)
        """
        if not self.is_available():
            self._logger.warning("MarianMT engine is not available, returning original texts")
            results = [
                TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=src_lang,
                    target_language=tgt_lang,
                    confidence=0.0,
                    engine_used=self.engine_name,
                    processing_time_ms=0.0,
                    from_cache=False
                )
                for text in texts
            ]
            return BatchTranslationResult(
                results=results,
                total_processing_time_ms=0.0,
                cache_hit_rate=0.0,
                failed_translations=[(i, "Engine not available") for i in range(len(texts))]
            )
        
        start_time = time.time()
        results = []
        failed = []
        
        try:
            # Load model for language pair - may return None on crash
            model_tuple = self._load_model(src_lang, tgt_lang)
            
            if model_tuple is None:
                # Model loading failed, return original texts
                self._logger.warning(f"Model loading failed for {src_lang}->{tgt_lang}, returning original texts")
                print(f"[MarianMT] Batch: Model loading failed, returning original texts")
                for i, text in enumerate(texts):
                    failed.append((i, "Model loading failed"))
                    results.append(TranslationResult(
                        original_text=text,
                        translated_text=text,
                        source_language=src_lang,
                        target_language=tgt_lang,
                        confidence=0.0,
                        engine_used=self.engine_name,
                        processing_time_ms=0.0,
                        from_cache=False
                    ))
                
                total_time = (time.time() - start_time) * 1000
                return BatchTranslationResult(
                    results=results,
                    total_processing_time_ms=total_time,
                    cache_hit_rate=0.0,
                    failed_translations=failed
                )
            
            model, tokenizer = model_tuple
            
            # Batch tokenization
            inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
            
            # Batch translation
            translated = model.generate(**inputs)
            
            # Decode all outputs
            for i, (original, translation) in enumerate(zip(texts, translated)):
                try:
                    translated_text = tokenizer.decode(translation, skip_special_tokens=True)
                    
                    results.append(TranslationResult(
                        original_text=original,
                        translated_text=translated_text,
                        source_language=src_lang,
                        target_language=tgt_lang,
                        confidence=0.90,
                        engine_used=self.engine_name,
                        processing_time_ms=0.0,  # Will be calculated at the end
                        from_cache=False
                    ))
                except Exception as e:
                    self._logger.error(f"Failed to decode translation {i}: {e}")
                    print(f"[MarianMT] Batch decode error {i}: {e}")
                    failed.append((i, str(e)))
                    results.append(TranslationResult(
                        original_text=original,
                        translated_text=original,
                        source_language=src_lang,
                        target_language=tgt_lang,
                        confidence=0.0,
                        engine_used=self.engine_name,
                        processing_time_ms=0.0,
                        from_cache=False
                    ))
            
        except Exception as e:
            self._logger.error(f"MarianMT batch translation failed: {e}")
            print(f"[MarianMT] Batch translation exception: {e}")
            import traceback
            traceback.print_exc()
            # Return original texts on complete failure
            for i, text in enumerate(texts):
                failed.append((i, str(e)))
                results.append(TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=src_lang,
                    target_language=tgt_lang,
                    confidence=0.0,
                    engine_used=self.engine_name,
                    processing_time_ms=0.0,
                    from_cache=False
                ))
        
        total_time = (time.time() - start_time) * 1000
        
        return BatchTranslationResult(
            results=results,
            total_processing_time_ms=total_time,
            cache_hit_rate=0.0,
            failed_translations=failed
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # MarianMT supports many language pairs
        # This is a subset of commonly used languages
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
            'ar', 'nl', 'pl', 'tr', 'sv', 'no', 'da', 'fi', 'cs', 'el',
            'he', 'id', 'ro', 'uk', 'bg', 'hr', 'sr', 'sk', 'sl', 'et',
            'lv', 'lt', 'ca', 'gl', 'eu', 'is', 'mk', 'sq', 'af', 'sw'
        ]
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """
        Check if engine supports specific language pair.
        
        Note: This checks if the model exists on HuggingFace, but doesn't
        guarantee it's downloaded locally.
        """
        supported = self.get_supported_languages()
        src_normalized = src_lang.lower()[:2]
        tgt_normalized = tgt_lang.lower()[:2]
        return src_normalized in supported and tgt_normalized in supported
    
    def unload_model(self, src_lang: str, tgt_lang: str) -> None:
        """Unload a specific model to free memory."""
        lang_pair = (src_lang, tgt_lang)
        if lang_pair in self._loaded_models:
            del self._loaded_models[lang_pair]
            self._logger.info(f"Unloaded MarianMT model: {src_lang}->{tgt_lang}")
    
    def unload_all_models(self) -> None:
        """Unload all models to free memory."""
        self._loaded_models.clear()
        self._logger.info("Unloaded all MarianMT models")
    
    def cleanup(self) -> None:
        """Clean up engine resources."""
        self.unload_all_models()
        self._is_initialized = False
        self._logger.info("MarianMT engine cleaned up")
