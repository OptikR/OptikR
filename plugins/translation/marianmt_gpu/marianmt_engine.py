"""
MarianMT Translation Engine Plugin

Neural machine translation using MarianMT (Helsinki-NLP models).
This is the plugin wrapper that implements the AbstractTranslationEngine interface.

Author: OptikR Team
Date: November 2025
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

# Import base classes
try:
    from app.translation.translation_engine_interface import (
        AbstractTranslationEngine, TranslationOptions, TranslationResult,
        BatchTranslationResult
    )
except ImportError:
    # Fallback for different import paths
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from app.translation.translation_engine_interface import (
        AbstractTranslationEngine, TranslationOptions, TranslationResult,
        BatchTranslationResult
    )


class TranslationEngine(AbstractTranslationEngine):
    """
    MarianMT translation engine plugin.
    
    This is the main class that the plugin manager will instantiate.
    Must be named 'TranslationEngine' for plugin discovery.
    """
    
    def __init__(self):
        """Initialize MarianMT engine."""
        super().__init__("marianmt")
        self._logger = logging.getLogger(__name__)
        self._is_initialized = TRANSFORMERS_AVAILABLE
        self._loaded_models = {}  # Cache: {(src, tgt): (model, tokenizer)}
        self._device = None  # Will be set during initialization
        
        if not TRANSFORMERS_AVAILABLE:
            self._logger.warning("transformers library not available")
        else:
            self._logger.info("MarianMT engine plugin initialized")
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize engine with configuration.
        
        Args:
            config: Configuration dictionary with optional keys:
                   - source_language: Source language code
                   - target_language: Target language code
                   - gpu: Use GPU acceleration if available
                   - runtime_mode: 'auto', 'gpu', or 'cpu'
                   
        Returns:
            True if initialization successful
        """
        if not TRANSFORMERS_AVAILABLE:
            self._logger.error("transformers library not available")
            return False
        
        try:
            import torch
            
            # Store config for later use
            self._config = config
            
            # Determine device based on config
            use_gpu = config.get('gpu', True)
            runtime_mode = config.get('runtime_mode', 'auto')
            
            if runtime_mode == 'cpu':
                use_gpu = False
            elif runtime_mode == 'gpu':
                use_gpu = True
            # 'auto' mode uses the gpu config value
            
            if use_gpu and torch.cuda.is_available():
                self._device = torch.device('cuda')
                self._logger.info("MarianMT using GPU acceleration (CUDA)")
            else:
                self._device = torch.device('cpu')
                if use_gpu and not torch.cuda.is_available():
                    self._logger.warning("GPU requested but CUDA not available, using CPU")
                else:
                    self._logger.info("MarianMT using CPU")
            
            self._is_initialized = True
            self._logger.info(f"MarianMT engine initialized successfully on device: {self._device}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized and TRANSFORMERS_AVAILABLE
    
    def _get_model_name(self, src_lang: str, tgt_lang: str) -> str:
        """Get HuggingFace model name for language pair."""
        src = src_lang.lower()[:2]
        tgt = tgt_lang.lower()[:2]
        return f"Helsinki-NLP/opus-mt-{src}-{tgt}"
    
    def _load_model(self, src_lang: str, tgt_lang: str) -> Optional[tuple]:
        """
        Load MarianMT model for language pair.
        
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
            self._logger.info(f"Loading MarianMT model: {model_name} on device: {self._device}")
            
            # Load model and tokenizer
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            
            # Move model to configured device (GPU or CPU)
            model = model.to(self._device)
            
            # Cache the loaded model
            self._loaded_models[lang_pair] = (model, tokenizer)
            
            self._logger.info(f"Model loaded successfully: {model_name} on {self._device}")
            return model, tokenizer
            
        except Exception as e:
            self._logger.error(f"Failed to load model for {src_lang}->{tgt_lang}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using MarianMT.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options (optional)
            
        Returns:
            TranslationResult with translated text
        """
        if not self.is_available():
            self._logger.warning("Engine not available, returning original text")
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
            # Load model for language pair
            model_tuple = self._load_model(src_lang, tgt_lang)
            
            if model_tuple is None:
                self._logger.warning(f"Model loading failed, returning original text")
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
            
            # Tokenize input and move to device
            inputs = tokenizer(text, return_tensors="pt", padding=True, 
                             truncation=True, max_length=512)
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Generate translation
            translated = model.generate(
                **inputs,
                max_length=512,  # Allow longer translations
                num_beams=4,     # Better quality translations
                early_stopping=True
            )
            
            # Decode output
            translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.90,
                engine_used=self.engine_name,
                processing_time_ms=processing_time,
                from_cache=False
            )
            
        except Exception as e:
            self._logger.error(f"Translation failed: {e}")
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
            options: Translation options (optional)
            
        Returns:
            BatchTranslationResult with all translations
        """
        start_time = time.time()
        results = []
        failed = []
        
        try:
            # Load model
            model_tuple = self._load_model(src_lang, tgt_lang)
            
            if model_tuple is None:
                # Return original texts
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
            else:
                model, tokenizer = model_tuple
                
                # Batch tokenization and move to device
                inputs = tokenizer(texts, return_tensors="pt", padding=True,
                                 truncation=True, max_length=512)
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
                
                # Batch translation
                translated = model.generate(
                    **inputs,
                    max_length=512,  # Allow longer translations
                    num_beams=4,     # Better quality translations
                    early_stopping=True
                )
                
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
                            processing_time_ms=0.0,
                            from_cache=False
                        ))
                    except Exception as e:
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
            self._logger.error(f"Batch translation failed: {e}")
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
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
            'ar', 'nl', 'pl', 'tr', 'sv', 'no', 'da', 'fi', 'cs', 'el'
        ]
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """Check if engine supports specific language pair."""
        supported = self.get_supported_languages()
        src_normalized = src_lang.lower()[:2]
        tgt_normalized = tgt_lang.lower()[:2]
        return src_normalized in supported and tgt_normalized in supported
    
    def cleanup(self) -> None:
        """Clean up engine resources."""
        self._loaded_models.clear()
        self._is_initialized = False
        self._logger.info("MarianMT engine cleaned up")
