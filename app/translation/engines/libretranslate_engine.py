"""
LibreTranslate Engine

Uses LibreTranslate API for free, open-source AI translation.
Can use the public instance or a self-hosted instance.
"""

import logging
import time
import requests
from typing import List, Optional

from ..translation_engine_interface import (
    AbstractTranslationEngine, TranslationOptions, TranslationResult,
    BatchTranslationResult, TranslationQuality
)


class LibreTranslateEngine(AbstractTranslationEngine):
    """
    LibreTranslate engine for free AI translation.
    
    Uses the LibreTranslate API (https://libretranslate.com) which is free
    and open-source. Can use public instance or self-hosted.
    """
    
    def __init__(self, api_url: str = "https://libretranslate.com", api_key: Optional[str] = None):
        """
        Initialize LibreTranslate engine.
        
        Args:
            api_url: LibreTranslate API URL (default: public instance)
            api_key: Optional API key for rate limiting (free to get)
        """
        super().__init__("libretranslate")
        self._logger = logging.getLogger(__name__)
        self._api_url = api_url.rstrip('/')
        self._api_key = api_key
        self._is_initialized = False
        self._supported_languages = []
        
        # Test connection and get supported languages
        try:
            self._test_connection()
            self._fetch_supported_languages()
            self._is_initialized = True
            self._logger.info(f"LibreTranslate engine initialized (URL: {self._api_url})")
        except Exception as e:
            self._logger.error(f"Failed to initialize LibreTranslate: {e}")
            self._is_initialized = False
    
    def initialize(self, config: dict) -> bool:
        """Initialize engine with configuration."""
        try:
            self._api_url = config.get('api_url', 'https://libretranslate.com').rstrip('/')
            self._api_key = config.get('api_key')
            self._test_connection()
            self._fetch_supported_languages()
            self._is_initialized = True
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    def _test_connection(self) -> None:
        """Test connection to LibreTranslate API."""
        try:
            response = requests.get(f"{self._api_url}/languages", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Cannot connect to LibreTranslate API: {e}")
    
    def _fetch_supported_languages(self) -> None:
        """Fetch list of supported languages from API."""
        try:
            response = requests.get(f"{self._api_url}/languages", timeout=5)
            response.raise_for_status()
            languages = response.json()
            self._supported_languages = [lang['code'] for lang in languages]
            self._logger.info(f"LibreTranslate supports {len(self._supported_languages)} languages")
        except Exception as e:
            self._logger.error(f"Failed to fetch supported languages: {e}")
            # Fallback to common languages
            self._supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar']
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using LibreTranslate.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            TranslationResult with translated text
        """
        if not self.is_available():
            raise RuntimeError("LibreTranslate engine is not available")
        
        start_time = time.time()
        
        try:
            # Normalize language codes
            src_lang = self._normalize_language_code(src_lang)
            tgt_lang = self._normalize_language_code(tgt_lang)
            
            # Prepare request
            payload = {
                'q': text,
                'source': src_lang,
                'target': tgt_lang,
                'format': 'text'
            }
            
            if self._api_key:
                payload['api_key'] = self._api_key
            
            # Make request
            response = requests.post(
                f"{self._api_url}/translate",
                json=payload,
                timeout=10
            )
            
            # Check for API key requirement
            if response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', '')
                if 'API key' in error_msg or 'api key' in error_msg.lower():
                    raise RuntimeError(
                        "LibreTranslate requires an API key. "
                        "Visit https://portal.libretranslate.com to get a free API key, "
                        "then add it to your configuration under 'translation.libretranslate_api_key'"
                    )
            
            response.raise_for_status()
            
            result_data = response.json()
            translated_text = result_data.get('translatedText', text)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.80,  # LibreTranslate doesn't provide confidence scores
                engine_used=self.engine_name,
                processing_time_ms=processing_time,
                from_cache=False
            )
            
        except requests.exceptions.RequestException as e:
            self._logger.error(f"LibreTranslate API request failed: {e}")
            raise RuntimeError(f"Translation failed: {e}")
        except Exception as e:
            self._logger.error(f"LibreTranslate translation failed: {e}")
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
            raise RuntimeError("LibreTranslate engine is not available")
        
        start_time = time.time()
        results = []
        failed = []
        
        # Normalize language codes
        src_lang = self._normalize_language_code(src_lang)
        tgt_lang = self._normalize_language_code(tgt_lang)
        
        # LibreTranslate doesn't have native batch support, so translate one by one
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
        return self._supported_languages.copy()
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """Check if engine supports specific language pair."""
        src_normalized = self._normalize_language_code(src_lang)
        tgt_normalized = self._normalize_language_code(tgt_lang)
        return src_normalized in self._supported_languages and tgt_normalized in self._supported_languages
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """Normalize language code to LibreTranslate format."""
        # LibreTranslate uses ISO 639-1 codes
        lang_map = {
            'zh-CN': 'zh',
            'zh-TW': 'zh',
            'zh-cn': 'zh',
            'zh-tw': 'zh'
        }
        return lang_map.get(lang_code, lang_code.lower()[:2])
    
    def set_api_key(self, api_key: str) -> None:
        """Set API key for LibreTranslate."""
        self._api_key = api_key
        self._logger.info("LibreTranslate API key updated")
    
    def set_api_url(self, api_url: str) -> None:
        """Set custom LibreTranslate API URL (for self-hosted instances)."""
        self._api_url = api_url.rstrip('/')
        self._logger.info(f"LibreTranslate API URL updated: {self._api_url}")
        # Re-test connection and fetch languages
        try:
            self._test_connection()
            self._fetch_supported_languages()
            self._is_initialized = True
        except Exception as e:
            self._logger.error(f"Failed to connect to new API URL: {e}")
            self._is_initialized = False
    
    def cleanup(self) -> None:
        """Clean up engine resources."""
        self._is_initialized = False
        self._logger.info("LibreTranslate engine cleaned up")
