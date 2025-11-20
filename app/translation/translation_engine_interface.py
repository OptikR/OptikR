"""
Translation Engine Interface and Base Classes

This module provides the abstract translation engine interface and base implementations
for translation functionality including batch processing, caching, and language detection.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
import time
import hashlib
import threading
from collections import defaultdict, OrderedDict
import logging

try:
    from ..interfaces import TranslationEngine
    from ..models import Translation, TextBlock
except ImportError:
    try:
        from interfaces import TranslationEngine
        from models import Translation, TextBlock
    except ImportError:
        from app.interfaces import TranslationEngine
        from app.models import Translation, TextBlock


class TranslationQuality(Enum):
    """Translation quality levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BEST = "best"


class LanguageDetectionConfidence(Enum):
    """Language detection confidence levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class TranslationOptions:
    """Options for translation requests."""
    quality: TranslationQuality = TranslationQuality.MEDIUM
    preserve_formatting: bool = True
    use_cache: bool = True
    timeout_seconds: float = 5.0
    context: Optional[str] = None
    domain: Optional[str] = None  # e.g., "technical", "medical", "general"
    
    
@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language_code: str
    confidence: float
    confidence_level: LanguageDetectionConfidence
    alternative_languages: List[Tuple[str, float]] = field(default_factory=list)
    

@dataclass
class TranslationResult:
    """Result of translation operation."""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    engine_used: str
    processing_time_ms: float
    from_cache: bool = False
    alternatives: List[str] = field(default_factory=list)


@dataclass
class BatchTranslationResult:
    """Result of batch translation operation."""
    results: List[TranslationResult]
    total_processing_time_ms: float
    cache_hit_rate: float
    failed_translations: List[Tuple[int, str]] = field(default_factory=list)  # (index, error)


class TranslationCache:
    """High-performance translation cache with LRU eviction."""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        Initialize translation cache.
        
        Args:
            max_size: Maximum number of cached translations
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _generate_cache_key(self, text: str, src_lang: str, tgt_lang: str, 
                          engine: str, options: Optional[TranslationOptions] = None) -> str:
        """Generate cache key for translation request."""
        key_data = f"{text}|{src_lang}|{tgt_lang}|{engine}"
        if options:
            key_data += f"|{options.quality.value}|{options.domain or ''}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, text: str, src_lang: str, tgt_lang: str, engine: str,
            options: Optional[TranslationOptions] = None) -> Optional[str]:
        """Get cached translation if available and not expired."""
        cache_key = self._generate_cache_key(text, src_lang, tgt_lang, engine, options)
        
        with self._lock:
            if cache_key in self._cache:
                translation, timestamp = self._cache[cache_key]
                
                # Check if entry has expired
                if time.time() - timestamp > self.ttl_seconds:
                    del self._cache[cache_key]
                    self._stats['misses'] += 1
                    self._stats['size'] = len(self._cache)
                    return None
                
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                self._stats['hits'] += 1
                return translation
            
            self._stats['misses'] += 1
            return None
    
    def put(self, text: str, src_lang: str, tgt_lang: str, engine: str,
            translation: str, options: Optional[TranslationOptions] = None) -> None:
        """Cache translation result."""
        cache_key = self._generate_cache_key(text, src_lang, tgt_lang, engine, options)
        
        with self._lock:
            # Remove oldest entries if cache is full
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
            
            self._cache[cache_key] = (translation, time.time())
            self._stats['size'] = len(self._cache)
    
    def clear(self) -> None:
        """Clear all cached translations."""
        with self._lock:
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'size': 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': self._stats['size'],
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class LanguageDetector:
    """Language detection and validation system."""
    
    def __init__(self):
        """Initialize language detector."""
        self._supported_languages = {
            'en': 'English',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'th': 'Thai',
            'vi': 'Vietnamese',
            'nl': 'Dutch'
        }
        self._logger = logging.getLogger(__name__)
    
    def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect language of input text.
        
        Args:
            text: Text to analyze
            
        Returns:
            LanguageDetectionResult with detected language and confidence
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                language_code='unknown',
                confidence=0.0,
                confidence_level=LanguageDetectionConfidence.VERY_LOW
            )
        
        # Simple heuristic-based detection (placeholder implementation)
        # In a real implementation, this would use a proper language detection library
        text_lower = text.lower().strip()
        
        # Basic character-based detection
        if any(ord(char) >= 0x4e00 and ord(char) <= 0x9fff for char in text):
            confidence = 0.9
            return LanguageDetectionResult(
                language_code='zh',
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                alternative_languages=[('ja', 0.1)]
            )
        
        if any(ord(char) >= 0x3040 and ord(char) <= 0x309f for char in text):
            confidence = 0.95
            return LanguageDetectionResult(
                language_code='ja',
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence)
            )
        
        if any(ord(char) >= 0xac00 and ord(char) <= 0xd7af for char in text):
            confidence = 0.95
            return LanguageDetectionResult(
                language_code='ko',
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence)
            )
        
        # Default to English for Latin script
        confidence = 0.7
        return LanguageDetectionResult(
            language_code='en',
            confidence=confidence,
            confidence_level=self._get_confidence_level(confidence),
            alternative_languages=[('es', 0.15), ('fr', 0.1), ('de', 0.05)]
        )
    
    def _get_confidence_level(self, confidence: float) -> LanguageDetectionConfidence:
        """Convert numeric confidence to confidence level enum."""
        if confidence >= 0.9:
            return LanguageDetectionConfidence.VERY_HIGH
        elif confidence >= 0.7:
            return LanguageDetectionConfidence.HIGH
        elif confidence >= 0.5:
            return LanguageDetectionConfidence.MEDIUM
        elif confidence >= 0.3:
            return LanguageDetectionConfidence.LOW
        else:
            return LanguageDetectionConfidence.VERY_LOW
    
    def validate_language_code(self, language_code: str) -> bool:
        """Validate if language code is supported."""
        return language_code in self._supported_languages
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported language codes and names."""
        return self._supported_languages.copy()
    
    def get_language_name(self, language_code: str) -> Optional[str]:
        """Get human-readable name for language code."""
        return self._supported_languages.get(language_code)


class AbstractTranslationEngine(ABC):
    """Abstract base class for translation engines."""
    
    def __init__(self, engine_name: str):
        """
        Initialize translation engine.
        
        Args:
            engine_name: Name identifier for this engine
        """
        self.engine_name = engine_name
        self._logger = logging.getLogger(f"{__name__}.{engine_name}")
        self._is_initialized = False
        self._supported_languages: Set[str] = set()
        self._performance_stats = defaultdict(list)
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the translation engine with configuration.
        
        Args:
            config: Engine-specific configuration
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[TranslationOptions] = None) -> TranslationResult:
        """
        Translate single text.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            TranslationResult with translation and metadata
        """
        pass
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str,
                       options: Optional[TranslationOptions] = None) -> BatchTranslationResult:
        """
        Translate multiple texts in batch.
        
        Default implementation translates individually. Engines should override
        for true batch processing optimization.
        
        Args:
            texts: List of texts to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            BatchTranslationResult with all translations and metadata
        """
        start_time = time.time()
        results = []
        failed_translations = []
        
        for i, text in enumerate(texts):
            try:
                result = self.translate_text(text, src_lang, tgt_lang, options)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Failed to translate text at index {i}: {e}")
                failed_translations.append((i, str(e)))
        
        total_time_ms = (time.time() - start_time) * 1000
        cache_hits = sum(1 for r in results if r.from_cache)
        cache_hit_rate = cache_hits / len(results) if results else 0.0
        
        return BatchTranslationResult(
            results=results,
            total_processing_time_ms=total_time_ms,
            cache_hit_rate=cache_hit_rate,
            failed_translations=failed_translations
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return list(self._supported_languages)
    
    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        """Check if engine supports specific language pair."""
        return src_lang in self._supported_languages and tgt_lang in self._supported_languages
    
    def is_available(self) -> bool:
        """Check if engine is available and initialized."""
        return self._is_initialized
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information and capabilities."""
        return {
            'name': self.engine_name,
            'initialized': self._is_initialized,
            'supported_languages': list(self._supported_languages),
            'supports_batch': True,
            'supports_quality_levels': True,
            'supports_domains': False
        }
    
    def record_performance(self, operation: str, duration_ms: float) -> None:
        """Record performance metrics for monitoring."""
        self._performance_stats[operation].append(duration_ms)
        
        # Keep only last 100 measurements per operation
        if len(self._performance_stats[operation]) > 100:
            self._performance_stats[operation] = self._performance_stats[operation][-100:]
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        for operation, times in self._performance_stats.items():
            if times:
                stats[operation] = {
                    'avg_ms': sum(times) / len(times),
                    'min_ms': min(times),
                    'max_ms': max(times),
                    'count': len(times)
                }
        return stats
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up engine resources."""
        pass


class TranslationEngineRegistry:
    """Registry for managing translation engines."""
    
    def __init__(self):
        """Initialize engine registry."""
        self._engines: Dict[str, AbstractTranslationEngine] = {}
        self._logger = logging.getLogger(__name__)
    
    def register_engine(self, engine: AbstractTranslationEngine) -> bool:
        """
        Register a translation engine.
        
        Args:
            engine: Translation engine instance
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            if engine.engine_name in self._engines:
                self._logger.warning(f"Engine {engine.engine_name} already registered, replacing")
            
            self._engines[engine.engine_name] = engine
            self._logger.info(f"Registered translation engine: {engine.engine_name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register engine {engine.engine_name}: {e}")
            return False
    
    def unregister_engine(self, engine_name: str) -> bool:
        """
        Unregister a translation engine.
        
        Args:
            engine_name: Name of engine to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if engine_name in self._engines:
                engine = self._engines[engine_name]
                engine.cleanup()
                del self._engines[engine_name]
                self._logger.info(f"Unregistered translation engine: {engine_name}")
                return True
            else:
                self._logger.warning(f"Engine {engine_name} not found for unregistration")
                return False
                
        except Exception as e:
            self._logger.error(f"Failed to unregister engine {engine_name}: {e}")
            return False
    
    def get_engine(self, engine_name: str) -> Optional[AbstractTranslationEngine]:
        """Get engine by name."""
        return self._engines.get(engine_name)
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engine names."""
        return [name for name, engine in self._engines.items() if engine.is_available()]
    
    def get_engines_for_language_pair(self, src_lang: str, tgt_lang: str) -> List[str]:
        """Get engines that support specific language pair."""
        compatible_engines = []
        for name, engine in self._engines.items():
            if engine.is_available() and engine.supports_language_pair(src_lang, tgt_lang):
                compatible_engines.append(name)
        return compatible_engines
    
    def cleanup_all(self) -> None:
        """Clean up all registered engines."""
        for engine in self._engines.values():
            try:
                engine.cleanup()
            except Exception as e:
                self._logger.error(f"Error cleaning up engine {engine.engine_name}: {e}")
        self._engines.clear()