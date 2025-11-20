"""
Translation Cache Optimizer Plugin
Caches translations for instant lookup of repeated text
"""

import time
import hashlib
from collections import OrderedDict
from typing import Dict, Any, Optional


class TranslationCacheOptimizer:
    """Caches translations to avoid repeated API calls"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_size = config.get('max_cache_size', 10000)
        self.ttl = config.get('ttl_seconds', 3600)
        self.fuzzy_match = config.get('enable_fuzzy_match', False)
        
        # LRU cache with timestamps
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _make_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Create cache key from text and language pair"""
        key_str = f"{source_lang}:{target_lang}:{text}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        age = time.time() - self.timestamps[key]
        return age > self.ttl
    
    def _evict_old_entries(self):
        """Remove expired entries"""
        current_time = time.time()
        keys_to_remove = []
        
        for key, timestamp in self.timestamps.items():
            if current_time - timestamp > self.ttl:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.cache:
                del self.cache[key]
            del self.timestamps[key]
            self.evictions += 1
    
    def _evict_lru(self):
        """Remove least recently used entry"""
        if self.cache:
            key, _ = self.cache.popitem(last=False)
            if key in self.timestamps:
                del self.timestamps[key]
            self.evictions += 1
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation if available"""
        key = self._make_key(text, source_lang, target_lang)
        
        # Check if expired
        if self._is_expired(key):
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
            self.misses += 1
            return None
        
        # Check cache
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        
        self.misses += 1
        return None
    
    def put(self, text: str, source_lang: str, target_lang: str, translation: str):
        """Store translation in cache"""
        key = self._make_key(text, source_lang, target_lang)
        
        # Evict old entries periodically
        if len(self.cache) % 100 == 0:
            self._evict_old_entries()
        
        # Evict LRU if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Store in cache
        self.cache[key] = translation
        self.timestamps[key] = time.time()
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-process: Check cache before translation"""
        text = data.get('text', '')
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'en')
        
        # Try cache lookup
        cached = self.get(text, source_lang, target_lang)
        
        if cached is not None:
            # Cache hit - return immediately
            data['translated_text'] = cached
            data['cache_hit'] = True
            data['skip_translation'] = True
        else:
            # Cache miss - will translate normally
            data['cache_hit'] = False
            data['skip_translation'] = False
        
        return data
    
    def post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process: Store translation in cache AND pass to learning dictionary"""
        if not data.get('cache_hit', False) and 'translated_text' in data:
            text = data.get('text', '')
            source_lang = data.get('source_lang', 'auto')
            target_lang = data.get('target_lang', 'en')
            translation = data['translated_text']
            
            self.put(text, source_lang, target_lang, translation)
            
            # Mark that this should be saved to learning dictionary
            # Don't mark as cache_hit so learning dictionary can save it
            data['should_save_to_dictionary'] = True
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_size': len(self.cache),
            'evictions': self.evictions
        }
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.timestamps.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> TranslationCacheOptimizer:
    """Initialize the optimizer plugin"""
    return TranslationCacheOptimizer(config)
