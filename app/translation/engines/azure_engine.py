"""
Azure Translator Engine

Premium translation engine using Microsoft Azure Cognitive Services.
Requires API key and region from Azure Portal.
"""

import logging
from typing import List, Optional
import requests

from ..translation_engine_interface import (
    AbstractTranslationEngine, TranslationOptions, TranslationResult,
    BatchTranslationResult
)


class AzureTranslatorEngine(AbstractTranslationEngine):
    """Azure Translator engine (premium)."""
    
    def __init__(self, api_key: str = None, region: str = "global"):
        """
        Initialize Azure Translator engine.
        
        Args:
            api_key: Azure Translator API key
            region: Azure region (default: global)
        """
        super().__init__("azure")
        self._logger = logging.getLogger(__name__)
        self._api_key = api_key
        self._region = region
        self._endpoint = "https://api.cognitive.microsofttranslator.com"
        self._is_initialized = False
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize engine with configuration.
        
        Args:
            config: Configuration dictionary with 'api_key' and optional 'region'
            
        Returns:
            True if initialization successful
        """
        try:
            # Get API key from config
            self._api_key = config.get('api_key', self._api_key)
            self._region = config.get('region', self._region)
            
            if not self._api_key:
                self._logger.error("No API key provided")
                return False
            
            self._is_initialized = True
            self._logger.info(f"Azure Translator engine initialized (region: {self._region})")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self._is_initialized and self._api_key is not None
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate text using Azure Translator.
        
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
            # Prepare request
            path = '/translate'
            constructed_url = self._endpoint + path
            
            params = {
                'api-version': '3.0',
                'from': src_lang,
                'to': tgt_lang
            }
            
            headers = {
                'Ocp-Apim-Subscription-Key': self._api_key,
                'Ocp-Apim-Subscription-Region': self._region,
                'Content-type': 'application/json'
            }
            
            body = [{'text': text}]
            
            # Make request
            response = requests.post(
                constructed_url,
                params=params,
                headers=headers,
                json=body,
                timeout=10
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            translated_text = result[0]['translations'][0]['text']
            
            processing_time = (time.time() - start_time) * 1000
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.95,  # Azure is high quality
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
        
        try:
            # Azure supports batch translation
            path = '/translate'
            constructed_url = self._endpoint + path
            
            params = {
                'api-version': '3.0',
                'from': src_lang,
                'to': tgt_lang
            }
            
            headers = {
                'Ocp-Apim-Subscription-Key': self._api_key,
                'Ocp-Apim-Subscription-Region': self._region,
                'Content-type': 'application/json'
            }
            
            body = [{'text': text} for text in texts]
            
            # Make request
            response = requests.post(
                constructed_url,
                params=params,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response
            translations = response.json()
            
            for i, (original, translation) in enumerate(zip(texts, translations)):
                try:
                    translated_text = translation['translations'][0]['text']
                    results.append(TranslationResult(
                        original_text=original,
                        translated_text=translated_text,
                        source_language=src_lang,
                        target_language=tgt_lang,
                        confidence=0.95,
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
        # Azure supports 100+ languages
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
        self._is_initialized = False
        self._logger.info("Azure Translator engine cleaned up")
