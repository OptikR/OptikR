"""
Smart Translation Caching - Experimental Feature
Intelligent cache management with context-aware matching.
"""

import hashlib
import json
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from pathlib import Path


class SmartCache:
    """
    Smart translation cache with context-aware matching.
    
    Features:
    - Context-aware cache keys (considers surrounding text)
    - Fuzzy matching for similar translations
    - Confidence-based cache entries
    - Automatic cache optimization
    """
    
    def __init__(self, cache_dir: str = "cache", max_entries: int = 10000):
        """Initialize smart cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "smart_translation_cache.json"
        self.max_entries = max_entries
        
        # Cache structure: {cache_key: {translation, context, confidence, timestamp, hit_count}}
        self.cache: Dict[str, Dict] = {}
        self.load_cache()
    
    def _generate_cache_key(self, text: str, context: Optional[List[str]] = None) -> str:
        """
        Generate context-aware cache key.
        
        Args:
            text: Text to translate
            context: Surrounding text for context
            
        Returns:
            Cache key string
        """
        # Base key from text
        key_parts = [text.lower().strip()]
        
        # Add context if available
        if context:
            # Use first and last context items for key
            context_str = " ".join([c.lower().strip() for c in context[:2]])
            key_parts.append(context_str)
        
        # Generate hash
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, text: str, context: Optional[List[str]] = None, 
            min_confidence: float = 0.7) -> Optional[str]:
        """
        Get translation from cache with context awareness.
        
        Args:
            text: Text to translate
            context: Surrounding text for context
            min_confidence: Minimum confidence threshold
            
        Returns:
            Cached translation or None
        """
        # Try exact match first
        cache_key = self._generate_cache_key(text, context)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check confidence threshold
            if entry.get('confidence', 1.0) >= min_confidence:
                # Update hit count
                entry['hit_count'] = entry.get('hit_count', 0) + 1
                entry['last_accessed'] = datetime.now().isoformat()
                return entry['translation']
        
        # Try fuzzy match (without context)
        if context:
            simple_key = self._generate_cache_key(text, None)
            if simple_key in self.cache:
                entry = self.cache[simple_key]
                if entry.get('confidence', 1.0) >= min_confidence:
                    entry['hit_count'] = entry.get('hit_count', 0) + 1
                    entry['last_accessed'] = datetime.now().isoformat()
                    return entry['translation']
        
        return None
    
    def put(self, text: str, translation: str, context: Optional[List[str]] = None,
            confidence: float = 1.0):
        """
        Store translation in cache with context.
        
        Args:
            text: Original text
            translation: Translated text
            context: Surrounding text for context
            confidence: Translation confidence score
        """
        cache_key = self._generate_cache_key(text, context)
        
        self.cache[cache_key] = {
            'text': text,
            'translation': translation,
            'context': context or [],
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'hit_count': 0
        }
        
        # Optimize cache if too large
        if len(self.cache) > self.max_entries:
            self._optimize_cache()
    
    def _optimize_cache(self):
        """Optimize cache by removing least useful entries."""
        # Sort by usefulness score (hit_count / age)
        entries = []
        now = datetime.now()
        
        for key, entry in self.cache.items():
            timestamp = datetime.fromisoformat(entry['timestamp'])
            age_days = (now - timestamp).days + 1
            hit_count = entry.get('hit_count', 0)
            confidence = entry.get('confidence', 1.0)
            
            # Usefulness score: (hits * confidence) / age
            usefulness = (hit_count * confidence) / age_days
            entries.append((key, usefulness))
        
        # Sort by usefulness (descending)
        entries.sort(key=lambda x: x[1], reverse=True)
        
        # Keep top entries
        keep_count = int(self.max_entries * 0.8)  # Keep 80%
        keys_to_keep = {key for key, _ in entries[:keep_count]}
        
        # Remove least useful entries
        self.cache = {k: v for k, v in self.cache.items() if k in keys_to_keep}
        
        print(f"[INFO] Smart cache optimized: {len(self.cache)} entries remaining")
    
    def load_cache(self):
        """Load cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"[INFO] Smart cache loaded: {len(self.cache)} entries")
        except Exception as e:
            print(f"[WARNING] Failed to load smart cache: {e}")
            self.cache = {}
    
    def save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Smart cache saved: {len(self.cache)} entries")
        except Exception as e:
            print(f"[ERROR] Failed to save smart cache: {e}")
    
    def clear(self):
        """Clear all cache entries."""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        print("[INFO] Smart cache cleared")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_hits = sum(entry.get('hit_count', 0) for entry in self.cache.values())
        avg_confidence = sum(entry.get('confidence', 1.0) for entry in self.cache.values()) / max(len(self.cache), 1)
        
        return {
            'total_entries': len(self.cache),
            'total_hits': total_hits,
            'avg_confidence': avg_confidence,
            'cache_file': str(self.cache_file)
        }
