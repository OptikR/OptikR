"""
Google Translate API Engine

Premium translation engine using Google Cloud Translation API.
Requires API key from Google Cloud Console.
"""

import logging
from typing import List, Optional

try:
    from google.cloud import translate_v2 as translate
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    translate = None

from ..translation_engine_interface import (
    AbstractTranslationEngine, TranslationOptions, TranslationResult,
    BatchTranslationResult
)


class GoogleAPITranslationEngine(AbstractTranslationEngine):
    """Google Translate API engine (premium)."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Google Translate API engine.
        
        Args:
            api_key: Google Cloud API key
        """
        super().__init__("google")
        self._logger = logging.getLogger(__name__)
        self._api_key = api_key
        self._client = None
        self._is_initialized = False
        
        if not GOOGLE_API_AVAILABLE:
            self._logger.warning("google-cloud-translate library not available")
            self._logger.info("Install with: pip install google-cloud-translate")
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize engine with configuration.
        
        Args:
            config: Configuration dictionary with 'api_key'
            
        Returns:
            True if initialization successful
        """
        if not GOOGLE_API_AVAILABLE:
            self._logger.error("google-cloud-translate library not available")
            return False
        
        try:
            # Get API key from config
            self._api_key = config.get('api_key', self._api_key)
            
            if not self._api_key:
                self._logger.error("No API key provided")
                return False
            
            # Initialize client
            import os
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self._api_key
            self._client = translate.Client()
            
            self._is_initialized = True
            self._logger.info("Google Translate API engine initialized")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized and GOOGLE_API_AVAILABLE and self._api_key is not None
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using Google Translate API.
        
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
            # Translate
            result = self._client.translate(
                text,
                source_language=src_lang,
                target_language=tgt_lang
            )
            
            translated_text = result['translatedText']
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.95,  # Google API is high quality
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
        # Google Translate supports 100+ languages
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
            'ar', 'nl', 'pl', 'tr', 'sv', 'no', 'da', 'fi', 'cs', 'el',
            'he', 'hi', 'id', 'ms', 'th', 'vi', 'uk', 'ro', 'hu', 'bg'
        ]
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """Check if engine supports specific language pair."""
        supported = self.get_supported_languages()
        return src_lang in supported and tgt_lang in supported
    
    def cleanup(self) -> None:
        """Clean up engine resources."""
        self._client = None
        self._is_initialized = False
        self._logger.info("Google Translate API engine cleaned up")
