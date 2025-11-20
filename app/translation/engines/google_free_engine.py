"""
Google Translate Free Engine

Uses the googletrans library (unofficial Google Translate API) for free translation
without requiring an API key.
"""

import logging
import time
from typing import List, Optional

try:
    import googletrans
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False
    Translator = None

from ..translation_engine_interface import (
    AbstractTranslationEngine, TranslationOptions, TranslationResult,
    BatchTranslationResult, TranslationQuality
)


class GoogleFreeTranslationEngine(AbstractTranslationEngine):
    """
    Google Translate Free engine using googletrans library.
    
    This engine provides free translation without requiring an API key.
    It uses the unofficial Google Translate API.
    """
    
    def __init__(self):
        """Initialize Google Free translation engine."""
        super().__init__("google_free")
        self._logger = logging.getLogger(__name__)
        self._translator = None
        self._is_initialized = False
        
        if GOOGLETRANS_AVAILABLE:
            try:
                self._translator = Translator()
                self._is_initialized = True
                self._logger.info("Google Free translation engine initialized")
            except Exception as e:
                self._logger.error(f"Failed to initialize Google Free translator: {e}")
                self._is_initialized = False
        else:
            self._logger.warning("googletrans library not available. Install with: pip install googletrans==4.0.0-rc1")
    
    def initialize(self, config: dict) -> bool:
        """Initialize engine with configuration."""
        if not GOOGLETRANS_AVAILABLE:
            return False
        try:
            self._translator = Translator()
            self._is_initialized = True
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized and self._translator is not None
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using Google Translate Free.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            TranslationResult with translated text
        """
        if not self.is_available():
            raise RuntimeError("Google Free translation engine is not available")
        
        start_time = time.time()
        
        try:
            # Convert language codes if needed (googletrans uses ISO 639-1)
            src_lang = self._normalize_language_code(src_lang)
            tgt_lang = self._normalize_language_code(tgt_lang)
            
            # Perform translation
            result = self._translator.translate(text, src=src_lang, dest=tgt_lang)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=result.text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.85,  # googletrans doesn't provide confidence scores
                engine_used=self.engine_name,
                processing_time_ms=processing_time,
                from_cache=False
            )
            
        except Exception as e:
            self._logger.error(f"Google Free translation failed: {e}")
            raise RuntimeError(f"Translation failed: {e}")
    
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
            BatchTranslationResult with all translations
        """
        if not self.is_available():
            raise RuntimeError("Google Free translation engine is not available")
        
        start_time = time.time()
        results = []
        failed = []
        
        # Convert language codes
        src_lang = self._normalize_language_code(src_lang)
        tgt_lang = self._normalize_language_code(tgt_lang)
        
        for i, text in enumerate(texts):
            try:
                result = self.translate_text(text, src_lang, tgt_lang, options)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Failed to translate text {i}: {e}")
                failed.append((i, str(e)))
                # Add placeholder result
                results.append(TranslationResult(
                    original_text=text,
                    translated_text=text,  # Return original on failure
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
        if not GOOGLETRANS_AVAILABLE:
            return []
        
        # googletrans supports many languages
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh-cn', 'zh-tw',
            'ar', 'hi', 'th', 'vi', 'nl', 'pl', 'tr', 'sv', 'no', 'da', 'fi',
            'cs', 'el', 'he', 'id', 'ms', 'ro', 'uk', 'bg', 'hr', 'sr', 'sk',
            'sl', 'et', 'lv', 'lt', 'fa', 'ur', 'bn', 'ta', 'te', 'mr', 'gu',
            'kn', 'ml', 'pa', 'si', 'ne', 'my', 'km', 'lo', 'ka', 'hy', 'az',
            'eu', 'be', 'ca', 'gl', 'is', 'mk', 'mn', 'sq', 'sw', 'tl', 'cy',
            'yi', 'af', 'zu', 'xh', 'st', 'tn', 'sn', 'yo', 'ig', 'ha', 'so',
            'am', 'ti', 'om', 'rw', 'lg', 'ny', 'mg', 'eo', 'la', 'jw', 'su',
            'ceb', 'haw', 'sm', 'ht', 'hmn', 'ku', 'ky', 'tg', 'tk', 'uz', 'ps'
        ]
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """Check if engine supports specific language pair."""
        supported = self.get_supported_languages()
        src_normalized = self._normalize_language_code(src_lang)
        tgt_normalized = self._normalize_language_code(tgt_lang)
        return src_normalized in supported and tgt_normalized in supported
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """Normalize language code to googletrans format."""
        # Convert common variations
        lang_map = {
            'zh-CN': 'zh-cn',
            'zh-TW': 'zh-tw',
            'zh': 'zh-cn'
        }
        return lang_map.get(lang_code, lang_code.lower())
    
    def cleanup(self) -> None:
        """Clean up engine resources."""
        self._translator = None
        self._is_initialized = False
        self._logger.info("Google Free translation engine cleaned up")
