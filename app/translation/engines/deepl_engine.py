"""
DeepL Translation Engine

Premium translation engine using DeepL API.
Requires API key from DeepL.
"""

import logging
from typing import List, Optional

try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False
    deepl = None

from ..translation_engine_interface import (
    AbstractTranslationEngine, TranslationOptions, TranslationResult,
    BatchTranslationResult
)


class DeepLTranslationEngine(AbstractTranslationEngine):
    """DeepL translation engine (premium)."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize DeepL engine.
        
        Args:
            api_key: DeepL API key
        """
        super().__init__("deepl")
        self._logger = logging.getLogger(__name__)
        self._api_key = api_key
        self._translator = None
        self._is_initialized = False
        
        if not DEEPL_AVAILABLE:
            self._logger.warning("deepl library not available")
            self._logger.info("Install with: pip install deepl")
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize engine with configuration.
        
        Args:
            config: Configuration dictionary with 'api_key'
            
        Returns:
            True if initialization successful
        """
        if not DEEPL_AVAILABLE:
            self._logger.error("deepl library not available")
            return False
        
        try:
            # Get API key from config
            self._api_key = config.get('api_key', self._api_key)
            
            if not self._api_key:
                self._logger.error("No API key provided")
                return False
            
            # Initialize translator
            self._translator = deepl.Translator(self._api_key)
            
            self._is_initialized = True
            self._logger.info("DeepL engine initialized")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized and DEEPL_AVAILABLE and self._api_key is not None
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using DeepL.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options (optional)
            
        Returns:
            TranslationResult with translated text
        """
        import time
        start_time = time.time()
        
        if not self.is_available():
            self._logger.warning("Engine not available")
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
        
        try:
            # DeepL uses uppercase language codes
            src_upper = src_lang.upper()
            tgt_upper = tgt_lang.upper()
            
            # Translate
            result = self._translator.translate_text(
                text,
                source_lang=src_upper,
                target_lang=tgt_upper
            )
            
            translated_text = result.text
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.98,  # DeepL is very high quality
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
        """Translate multiple texts in batch."""
        import time
        start_time = time.time()
        results = []
        failed = []
        
        for i, text in enumerate(texts):
            result = self.translate_text(text, src_lang, tgt_lang, options)
            results.append(result)
            if result.confidence == 0.0:
                failed.append((i, "Translation failed"))
        
        total_time = (time.time() - start_time) * 1000
        
        return BatchTranslationResult(
            results=results,
            total_processing_time_ms=total_time,
            cache_hit_rate=0.0,
            failed_translations=failed
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # DeepL supports European languages primarily
        return [
            'en', 'de', 'fr', 'es', 'it', 'nl', 'pl', 'pt', 'ru',
            'ja', 'zh', 'bg', 'cs', 'da', 'el', 'et', 'fi', 'hu',
            'id', 'lv', 'lt', 'ro', 'sk', 'sl', 'sv', 'tr', 'uk'
        ]
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """Check if engine supports specific language pair."""
        supported = self.get_supported_languages()
        return src_lang.lower() in supported and tgt_lang.lower() in supported
    
    def cleanup(self) -> None:
        """Clean up engine resources."""
        self._translator = None
        self._is_initialized = False
        self._logger.info("DeepL engine cleaned up")
