"""
LibreTranslate Translation Engine

Free and open-source translation API.
Supports self-hosted instances or public API.
"""

import requests
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class LibreTranslateConfig:
    """Configuration for LibreTranslate."""
    api_url: str = "https://libretranslate.com/translate"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


class LibreTranslateEngine:
    """LibreTranslate translation engine."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LibreTranslate engine."""
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.api_url = config.get('api_url', 'https://libretranslate.com/translate')
        self.api_key = config.get('api_key', None)
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        
        # Statistics
        self.total_requests = 0
        self.total_errors = 0
        self.total_chars_translated = 0
        
        self.logger.info(f"LibreTranslate initialized (URL: {self.api_url})")
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Translate text using LibreTranslate API.
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'en', 'ja', 'de')
            target_lang: Target language code
            
        Returns:
            Translated text or None on error
        """
        if not text or not text.strip():
            return text
        
        self.total_requests += 1
        
        # Prepare request
        payload = {
            'q': text,
            'source': source_lang,
            'target': target_lang,
            'format': 'text'
        }
        
        # Add API key if provided
        if self.api_key:
            payload['api_key'] = self.api_key
        
        # Try with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    translated_text = result.get('translatedText', '')
                    
                    if translated_text:
                        self.total_chars_translated += len(text)
                        return translated_text
                    else:
                        self.logger.warning("Empty translation received")
                        return None
                
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    self.logger.warning(f"Rate limit hit, attempt {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                
                elif response.status_code == 403:
                    self.logger.error("API key required or invalid")
                    self.total_errors += 1
                    return None
                
                else:
                    self.logger.error(f"API error: {response.status_code} - {response.text}")
                    self.total_errors += 1
                    return None
            
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    continue
                self.total_errors += 1
                return None
            
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed: {e}")
                self.total_errors += 1
                return None
            
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                self.total_errors += 1
                return None
        
        # All retries failed
        self.total_errors += 1
        return None
    
    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str) -> List[Optional[str]]:
        """
        Translate multiple texts.
        
        Note: LibreTranslate doesn't have native batch API,
        so we translate one by one.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of translated texts (None for failed translations)
        """
        results = []
        for text in texts:
            translated = self.translate(text, source_lang, target_lang)
            results.append(translated)
        return results
    
    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect language of text.
        
        Args:
            text: Text to detect language for
            
        Returns:
            Language code or None
        """
        if not text or not text.strip():
            return None
        
        # LibreTranslate detect endpoint
        detect_url = self.api_url.replace('/translate', '/detect')
        
        payload = {
            'q': text
        }
        
        if self.api_key:
            payload['api_key'] = self.api_key
        
        try:
            response = requests.post(
                detect_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('language')
            
            return None
        
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return None
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages.
        
        Returns:
            List of language dicts with 'code' and 'name'
        """
        languages_url = self.api_url.replace('/translate', '/languages')
        
        try:
            response = requests.get(languages_url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            
            return []
        
        except Exception as e:
            self.logger.error(f"Failed to get languages: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get translation statistics."""
        error_rate = (self.total_errors / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': f"{error_rate:.1f}%",
            'total_chars_translated': self.total_chars_translated,
            'api_url': self.api_url,
            'has_api_key': bool(self.api_key)
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.total_requests = 0
        self.total_errors = 0
        self.total_chars_translated = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> LibreTranslateEngine:
    """Initialize the translation engine."""
    return LibreTranslateEngine(config)


def translate(engine: LibreTranslateEngine, text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """Translate text."""
    return engine.translate(text, source_lang, target_lang)


def translate_batch(engine: LibreTranslateEngine, texts: List[str], source_lang: str, target_lang: str) -> List[Optional[str]]:
    """Translate multiple texts."""
    return engine.translate_batch(texts, source_lang, target_lang)


def detect_language(engine: LibreTranslateEngine, text: str) -> Optional[str]:
    """Detect language."""
    return engine.detect_language(text)


def get_supported_languages(engine: LibreTranslateEngine) -> List[Dict[str, str]]:
    """Get supported languages."""
    return engine.get_supported_languages()
