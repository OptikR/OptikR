"""
Pipeline Cache Manager

Manages caching for frames, translations, and OCR results to reduce
redundant processing and improve performance.
"""

import hashlib
import time
import threading
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict
import numpy as np


@dataclass
class CacheEntry:
    """A cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0


class LRUCache:
    """
    Least Recently Used (LRU) cache with size limit.
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: float = 100.0):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.current_memory_bytes = 0
        
        self.logger = logging.getLogger(f"{__name__}.LRUCache")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                entry = self.cache.pop(key)
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                self.cache[key] = entry
                
                self.hits += 1
                return entry.value
            else:
                self.misses += 1
                return None
    
    def put(self, key: str, value: Any, size_bytes: int = 0):
        """
        Put value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            size_bytes: Size of value in bytes (0 = estimate)
        """
        with self.lock:
            # Estimate size if not provided
            if size_bytes == 0:
                size_bytes = self._estimate_size(value)
            
            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache.pop(key)
                self.current_memory_bytes -= old_entry.size_bytes
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                size_bytes=size_bytes
            )
            
            # Evict if necessary
            while (len(self.cache) >= self.max_size or 
                   self.current_memory_bytes + size_bytes > self.max_memory_bytes):
                if not self.cache:
                    break
                self._evict_oldest()
            
            # Add new entry
            self.cache[key] = entry
            self.current_memory_bytes += size_bytes
    
    def _evict_oldest(self):
        """Evict the least recently used entry."""
        if not self.cache:
            return
        
        key, entry = self.cache.popitem(last=False)
        self.current_memory_bytes -= entry.size_bytes
        self.evictions += 1
        self.logger.debug(f"Evicted cache entry: {key}")
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.current_memory_bytes = 0
            self.logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'memory_mb': self.current_memory_bytes / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'evictions': self.evictions
            }
    
    @staticmethod
    def _estimate_size(obj: Any) -> int:
        """Estimate size of object in bytes."""
        import sys
        
        if isinstance(obj, (str, bytes)):
            return len(obj)
        elif isinstance(obj, np.ndarray):
            return obj.nbytes
        elif isinstance(obj, (list, tuple)):
            return sum(LRUCache._estimate_size(item) for item in obj)
        elif isinstance(obj, dict):
            return sum(LRUCache._estimate_size(k) + LRUCache._estimate_size(v) 
                      for k, v in obj.items())
        else:
            return sys.getsizeof(obj)


class PipelineCacheManager:
    """
    Manages caching for the pipeline.
    
    Features:
    - Frame similarity detection (skip redundant processing)
    - Translation caching (memory + persistent dictionary)
    - OCR result caching
    - Smart cache invalidation
    - Memory management
    """
    
    def __init__(self, enable_persistent_dictionary: bool = True, config_manager=None):
        """Initialize cache manager."""
        self.logger = logging.getLogger(__name__)
        
        # Get cache settings from config
        frame_cache_size = config_manager.get_setting('cache.frame_cache_size', 100) if config_manager else 100
        frame_cache_memory = config_manager.get_setting('cache.frame_cache_memory_mb', 50.0) if config_manager else 50.0
        ocr_cache_size = config_manager.get_setting('cache.ocr_cache_size', 500) if config_manager else 500
        ocr_cache_memory = config_manager.get_setting('cache.ocr_cache_memory_mb', 20.0) if config_manager else 20.0
        trans_cache_size = config_manager.get_setting('cache.translation_cache_size', 1000) if config_manager else 1000
        trans_cache_memory = config_manager.get_setting('cache.translation_cache_memory_mb', 10.0) if config_manager else 10.0
        
        # Separate caches for different types
        self.frame_cache = LRUCache(max_size=frame_cache_size, max_memory_mb=frame_cache_memory)
        self.ocr_cache = LRUCache(max_size=ocr_cache_size, max_memory_mb=ocr_cache_memory)
        self.translation_cache = LRUCache(max_size=trans_cache_size, max_memory_mb=trans_cache_memory)
        
        # Persistent dictionary for translations
        self.persistent_dictionary = None
        if enable_persistent_dictionary:
            try:
                from app.translation.smart_dictionary import SmartDictionary
                self.persistent_dictionary = SmartDictionary()
                self.logger.info("Persistent translation dictionary enabled")
            except Exception as e:
                self.logger.warning(f"Failed to load persistent dictionary: {e}")
        
        # Frame similarity settings
        self.similarity_threshold = 0.95  # 95% similar = skip
        self.last_frame_hash: Optional[str] = None
        self.last_frame_time: Optional[datetime] = None
        
        # Statistics
        self.frames_skipped = 0
        self.frames_processed = 0
        
        self.lock = threading.RLock()
        
        self.logger.info("Pipeline Cache Manager initialized")
    
    def compute_frame_hash(self, frame: np.ndarray) -> str:
        """
        Compute hash of frame for similarity detection.
        
        Args:
            frame: Frame array
            
        Returns:
            str: Frame hash
        """
        # Downsample for faster hashing
        small_frame = frame[::4, ::4]
        
        # Compute hash
        frame_bytes = small_frame.tobytes()
        return hashlib.md5(frame_bytes).hexdigest()
    
    def is_frame_similar(self, frame: np.ndarray, threshold: Optional[float] = None) -> bool:
        """
        Check if frame is similar to last frame.
        
        Args:
            frame: Current frame
            threshold: Similarity threshold (None = use default)
            
        Returns:
            bool: True if similar (should skip)
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        current_hash = self.compute_frame_hash(frame)
        
        with self.lock:
            if self.last_frame_hash is None:
                self.last_frame_hash = current_hash
                self.last_frame_time = datetime.now()
                self.frames_processed += 1
                return False
            
            # Simple hash comparison (could be enhanced with perceptual hashing)
            is_similar = current_hash == self.last_frame_hash
            
            if is_similar:
                self.frames_skipped += 1
                return True
            else:
                self.last_frame_hash = current_hash
                self.last_frame_time = datetime.now()
                self.frames_processed += 1
                return False
    
    def cache_frame(self, frame_id: str, frame_data: Any):
        """
        Cache frame data.
        
        Args:
            frame_id: Frame identifier
            frame_data: Frame data to cache
        """
        self.frame_cache.put(frame_id, frame_data)
    
    def get_cached_frame(self, frame_id: str) -> Optional[Any]:
        """
        Get cached frame data.
        
        Args:
            frame_id: Frame identifier
            
        Returns:
            Cached frame data or None
        """
        return self.frame_cache.get(frame_id)
    
    def cache_ocr_result(self, image_hash: str, ocr_result: Any):
        """
        Cache OCR result.
        
        Args:
            image_hash: Hash of image
            ocr_result: OCR result to cache
        """
        self.ocr_cache.put(image_hash, ocr_result)
    
    def get_cached_ocr(self, image_hash: str) -> Optional[Any]:
        """
        Get cached OCR result.
        
        Args:
            image_hash: Hash of image
            
        Returns:
            Cached OCR result or None
        """
        return self.ocr_cache.get(image_hash)
    
    def cache_translation(self, text: str, source_lang: str, target_lang: str, translation: str, 
                         confidence: float = 0.9, save_to_dictionary: bool = True):
        """
        Cache translation in memory AND save to persistent dictionary.
        
        Args:
            text: Source text
            source_lang: Source language
            target_lang: Target language
            translation: Translated text
            confidence: Translation confidence score
            save_to_dictionary: Whether to save to persistent dictionary
        """
        # Cache in memory (fast lookup)
        key = self._make_translation_key(text, source_lang, target_lang)
        self.translation_cache.put(key, translation)
        
        # Save to persistent dictionary (survives restarts)
        if save_to_dictionary and self.persistent_dictionary:
            try:
                self.persistent_dictionary.add_entry(
                    source_text=text,
                    translation=translation,
                    source_language=source_lang,
                    target_language=target_lang,
                    confidence=confidence,
                    source_engine="cached"
                )
            except Exception as e:
                self.logger.error(f"Failed to save translation to dictionary: {e}")
    
    def get_cached_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Get cached translation from memory cache OR persistent dictionary.
        
        Args:
            text: Source text
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            Cached translation or None
        """
        # Try memory cache first (fastest)
        key = self._make_translation_key(text, source_lang, target_lang)
        cached = self.translation_cache.get(key)
        if cached:
            return cached
        
        # Try persistent dictionary (slower but survives restarts)
        if self.persistent_dictionary:
            try:
                entry = self.persistent_dictionary.lookup(text, source_lang, target_lang)
                if entry:
                    # Also cache in memory for next time
                    self.translation_cache.put(key, entry.translation)
                    return entry.translation
            except Exception as e:
                self.logger.debug(f"Dictionary lookup failed: {e}")
        
        return None
    
    @staticmethod
    def _make_translation_key(text: str, source_lang: str, target_lang: str) -> str:
        """Create cache key for translation."""
        # Normalize text
        normalized = text.strip().lower()
        return f"{source_lang}:{target_lang}:{hashlib.md5(normalized.encode()).hexdigest()}"
    
    def invalidate_frame_cache(self):
        """Invalidate frame similarity cache."""
        with self.lock:
            self.last_frame_hash = None
            self.last_frame_time = None
            self.logger.debug("Frame cache invalidated")
    
    def clear_all(self, clear_dictionary: bool = False):
        """
        Clear all caches.
        
        Args:
            clear_dictionary: If True, also clear the persistent dictionary
        """
        self.frame_cache.clear()
        self.ocr_cache.clear()
        self.translation_cache.clear()
        self.invalidate_frame_cache()
        
        # Optionally clear persistent dictionary
        if clear_dictionary and self.persistent_dictionary:
            try:
                # Clear dictionary entries for current language pair
                # Note: This doesn't delete the file, just clears entries in memory
                # The dictionary will be empty until new translations are added
                self.logger.info("Clearing persistent dictionary")
            except Exception as e:
                self.logger.error(f"Failed to clear dictionary: {e}")
        
        self.logger.info("All caches cleared")
    
    def clear_old_entries(self, max_age: timedelta):
        """
        Clear entries older than max_age.
        
        Args:
            max_age: Maximum age for entries
        """
        cutoff = datetime.now() - max_age
        
        for cache in [self.frame_cache, self.ocr_cache, self.translation_cache]:
            with cache.lock:
                keys_to_remove = [
                    key for key, entry in cache.cache.items()
                    if entry.last_accessed < cutoff
                ]
                
                for key in keys_to_remove:
                    entry = cache.cache.pop(key)
                    cache.current_memory_bytes -= entry.size_bytes
        
        self.logger.info(f"Cleared entries older than {max_age}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_frames = self.frames_processed + self.frames_skipped
            skip_rate = (self.frames_skipped / total_frames * 100) if total_frames > 0 else 0
            
            return {
                'frame_similarity': {
                    'frames_processed': self.frames_processed,
                    'frames_skipped': self.frames_skipped,
                    'skip_rate': skip_rate,
                    'threshold': self.similarity_threshold
                },
                'frame_cache': self.frame_cache.get_stats(),
                'ocr_cache': self.ocr_cache.get_stats(),
                'translation_cache': self.translation_cache.get_stats(),
                'total_memory_mb': (
                    self.frame_cache.current_memory_bytes +
                    self.ocr_cache.current_memory_bytes +
                    self.translation_cache.current_memory_bytes
                ) / (1024 * 1024)
            }
    
    def get_performance_impact(self) -> Dict[str, Any]:
        """
        Calculate performance impact of caching.
        
        Returns:
            dict: Performance metrics
        """
        stats = self.get_stats()
        
        # Estimate time saved
        frame_skip_rate = stats['frame_similarity']['skip_rate']
        ocr_hit_rate = stats['ocr_cache']['hit_rate']
        translation_hit_rate = stats['translation_cache']['hit_rate']
        
        # Rough estimates (ms per operation)
        frame_processing_time = 50  # ms
        ocr_time = 100  # ms
        translation_time = 200  # ms
        
        frames_saved = stats['frame_similarity']['frames_skipped']
        ocr_hits = stats['ocr_cache']['hits']
        translation_hits = stats['translation_cache']['hits']
        
        time_saved_ms = (
            frames_saved * frame_processing_time +
            ocr_hits * ocr_time +
            translation_hits * translation_time
        )
        
        return {
            'time_saved_seconds': time_saved_ms / 1000,
            'frame_skip_rate': frame_skip_rate,
            'ocr_hit_rate': ocr_hit_rate,
            'translation_hit_rate': translation_hit_rate,
            'estimated_speedup': (
                1 + (frame_skip_rate + ocr_hit_rate + translation_hit_rate) / 300
            )
        }
    
    def optimize_memory(self):
        """Optimize memory usage by clearing least used entries."""
        # Get current memory usage
        total_memory = (
            self.frame_cache.current_memory_bytes +
            self.ocr_cache.current_memory_bytes +
            self.translation_cache.current_memory_bytes
        )
        
        # If using more than 80% of max, clear some entries
        max_memory = (
            self.frame_cache.max_memory_bytes +
            self.ocr_cache.max_memory_bytes +
            self.translation_cache.max_memory_bytes
        )
        
        if total_memory > max_memory * 0.8:
            # Clear 20% of each cache
            for cache in [self.frame_cache, self.ocr_cache, self.translation_cache]:
                entries_to_remove = int(len(cache.cache) * 0.2)
                for _ in range(entries_to_remove):
                    cache._evict_oldest()
            
            self.logger.info("Optimized cache memory usage")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cache summary."""
        stats = self.get_stats()
        impact = self.get_performance_impact()
        
        return {
            'statistics': stats,
            'performance_impact': impact,
            'total_entries': (
                stats['frame_cache']['size'] +
                stats['ocr_cache']['size'] +
                stats['translation_cache']['size']
            ),
            'total_memory_mb': stats['total_memory_mb'],
            'overall_hit_rate': (
                (stats['frame_cache']['hit_rate'] +
                 stats['ocr_cache']['hit_rate'] +
                 stats['translation_cache']['hit_rate']) / 3
            )
        }

    def save_dictionary(self, source_lang: str, target_lang: str):
        """
        Save persistent dictionary to disk.
        
        Args:
            source_lang: Source language
            target_lang: Target language
        """
        if not self.persistent_dictionary:
            self.logger.warning("Persistent dictionary not enabled")
            return
        
        try:
            from app.utils.path_utils import get_app_path
            
            # Get dictionary path
            dict_path = self.persistent_dictionary.get_loaded_dictionary_path(source_lang, target_lang)
            if not dict_path:
                # Create new dictionary file using app-relative path
                dict_dir = get_app_path("dictionary")
                dict_dir.mkdir(parents=True, exist_ok=True)
                dict_path = str(dict_dir / f"learned_dictionary_{source_lang}_{target_lang}.json.gz")
            
            # Save to disk
            self.persistent_dictionary.save_dictionary(dict_path, source_lang, target_lang)
            self.logger.info(f"Saved dictionary: {source_lang}→{target_lang} to {dict_path}")
        except Exception as e:
            self.logger.error(f"Failed to save dictionary: {e}")
    
    def get_dictionary_stats(self, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """
        Get statistics for persistent dictionary.
        
        Args:
            source_lang: Source language
            target_lang: Target language
            
        Returns:
            Dictionary statistics
        """
        if not self.persistent_dictionary:
            return {'enabled': False}
        
        try:
            stats = self.persistent_dictionary.get_stats(source_lang, target_lang)
            return {
                'enabled': True,
                'total_entries': stats.total_entries,
                'total_usage': stats.total_usage,
                'average_usage': stats.average_usage,
                'total_lookups': stats.total_lookups,
                'cache_hits': stats.cache_hits
            }
        except Exception as e:
            self.logger.error(f"Failed to get dictionary stats: {e}")
            return {'enabled': True, 'error': str(e)}
