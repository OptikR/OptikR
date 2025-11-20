"""
Intelligent Local Dictionary Module

Advanced dictionary-based translation system with:
- Machine learning-based quality scoring
- Context-aware translation selection
- Automatic learning from AI translations
- Smart fuzzy matching with multiple algorithms
- Confidence decay over time
- Usage pattern analysis
- Multi-variant translation support
- Intelligent entry merging

Author: Niklas Verhasselt
Date: November 12, 2025
"""

import gzip
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock
from collections import defaultdict
import difflib

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path


@dataclass
class DictionaryEntry:
    """
    Advanced dictionary entry with machine learning features.
    
    Tracks multiple translation variants, context, quality metrics,
    and temporal decay of confidence.
    """
    source_text: str
    translation: str
    source_language: str
    target_language: str
    usage_count: int
    confidence: float
    last_used: str  # ISO format datetime string
    
    # Advanced features
    variants: List[str] = field(default_factory=list)  # Alternative translations
    context_tags: Set[str] = field(default_factory=set)  # Context keywords
    quality_score: float = 0.0  # ML-based quality (0-1)
    source_engine: str = "manual"  # Origin: manual, ai, learned
    creation_date: str = ""  # When first added
    success_rate: float = 1.0  # How often this translation was accepted
    avg_confidence: float = 0.0  # Average confidence over time
    decay_factor: float = 1.0  # Temporal decay (1.0 = fresh, 0.0 = stale)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.creation_date:
            self.creation_date = datetime.now().isoformat()
        if self.avg_confidence == 0.0:
            self.avg_confidence = self.confidence
        self._update_decay_factor()
    
    def _update_decay_factor(self):
        """Update confidence decay based on time since last use."""
        try:
            last_used_dt = datetime.fromisoformat(self.last_used)
            days_since_use = (datetime.now() - last_used_dt).days
            
            # Decay formula: confidence decreases 5% per month of non-use
            # After 6 months: ~75%, after 1 year: ~55%, after 2 years: ~30%
            self.decay_factor = max(0.3, 1.0 - (days_since_use / 30) * 0.05)
        except:
            self.decay_factor = 1.0
    
    def get_effective_confidence(self) -> float:
        """Get confidence adjusted for decay and success rate."""
        self._update_decay_factor()
        return self.confidence * self.decay_factor * self.success_rate
    
    def add_variant(self, variant: str):
        """Add alternative translation."""
        if variant not in self.variants and variant != self.translation:
            self.variants.append(variant)
    
    def add_context(self, context: str):
        """Add context tag."""
        # Extract keywords from context
        words = re.findall(r'\w+', context.lower())
        self.context_tags.update(words[:5])  # Keep top 5 keywords
    
    def update_usage(self, success: bool = True):
        """Update usage statistics."""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        
        # Update success rate (exponential moving average)
        alpha = 0.1  # Learning rate
        self.success_rate = (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        
        # Update decay factor
        self._update_decay_factor()
    
    def merge_with(self, other: 'DictionaryEntry'):
        """Intelligently merge with another entry."""
        # Keep higher confidence translation as primary
        if other.confidence > self.confidence:
            self.variants.append(self.translation)
            self.translation = other.translation
            self.confidence = other.confidence
        else:
            self.variants.append(other.translation)
        
        # Merge statistics
        self.usage_count += other.usage_count
        self.context_tags.update(other.context_tags)
        
        # Update quality score (weighted average)
        total_usage = self.usage_count + other.usage_count
        self.quality_score = (
            (self.quality_score * self.usage_count + other.quality_score * other.usage_count) / total_usage
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            'translation': self.translation,
            'usage_count': self.usage_count,
            'confidence': self.confidence,
            'last_used': self.last_used,
            'variants': list(self.variants) if self.variants else [],
            'context_tags': list(self.context_tags) if self.context_tags else [],
            'quality_score': self.quality_score,
            'source_engine': self.source_engine,
            'creation_date': self.creation_date,
            'success_rate': self.success_rate,
            'avg_confidence': self.avg_confidence
        }
    
    @classmethod
    def from_dict(cls, source_text: str, data: dict, source_lang: str, target_lang: str):
        """Create from dictionary format."""
        return cls(
            source_text=source_text,
            translation=data.get('translation', ''),
            source_language=source_lang,
            target_language=target_lang,
            usage_count=data.get('usage_count', 0),
            confidence=data.get('confidence', 0.0),
            last_used=data.get('last_used', datetime.now().isoformat()),
            variants=data.get('variants', []),
            context_tags=set(data.get('context_tags', [])),
            quality_score=data.get('quality_score', 0.0),
            source_engine=data.get('source_engine', 'manual'),
            creation_date=data.get('creation_date', datetime.now().isoformat()),
            success_rate=data.get('success_rate', 1.0),
            avg_confidence=data.get('avg_confidence', data.get('confidence', 0.0))
        )


@dataclass
class DictionaryStats:
    """Dictionary statistics."""
    total_entries: int = 0
    total_usage: int = 0
    average_usage: float = 0.0
    total_lookups: int = 0
    cache_hits: int = 0
    most_used: List[Dict] = None
    
    def __post_init__(self):
        if self.most_used is None:
            self.most_used = []


class DictionaryLookupCache:
    """Simple LRU cache for dictionary lookups."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize cache."""
        self.max_size = max_size
        self._cache: Dict[str, Optional[DictionaryEntry]] = {}
        self._access_order: List[str] = []
        self._lock = RLock()
    
    def get(self, key: str) -> Optional[DictionaryEntry]:
        """Get cached entry."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
        return None
    
    def put(self, key: str, entry: Optional[DictionaryEntry]):
        """Cache entry."""
        with self._lock:
            # Remove if already exists
            if key in self._cache:
                self._access_order.remove(key)
            
            # Add to cache
            self._cache[key] = entry
            self._access_order.append(key)
            
            # Evict oldest if over limit
            while len(self._cache) > self.max_size:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]
    
    def clear(self):
        """Clear cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()


class SmartDictionary:
    """
    Smart Dictionary - Intelligent ML-based translation dictionary.
    
    Features:
    - Machine learning quality scoring
    - Context-aware matching
    - Fuzzy search with 4 algorithms
    - Automatic learning from AI translations
    - Multi-variant support
    - Temporal decay
    
    This is the main dictionary system used by OptikR.
    
    Reads from compressed JSON dictionary files in the format:
    {
        "source_text": {
            "translation": "target_text",
            "usage_count": 15,
            "confidence": 0.95,
            "last_used": "2025-11-12T20:00:00"
        }
    }
    """
    
    def __init__(self, dictionary_path: Optional[str] = None, cache_size: int = None, config_manager=None):
        """
        Initialize local dictionary.
        
        Args:
            dictionary_path: Path to dictionary file (default: auto-detect)
            cache_size: Size of lookup cache
        """
        self.logger = logging.getLogger(__name__)
        
        # Get cache size from config if not provided
        if cache_size is None and config_manager:
            cache_size = config_manager.get_setting('cache.dictionary_cache_size', 1000)
        elif cache_size is None:
            cache_size = 1000
        
        self.cache = DictionaryLookupCache(cache_size)
        self._lock = RLock()
        
        # Statistics
        self.total_lookups = 0
        self.cache_hits = 0
        
        # Dictionary data
        self._dictionaries: Dict[Tuple[str, str], Dict[str, dict]] = {}
        
        # Track which file path is loaded for each language pair
        self._dictionary_paths: Dict[Tuple[str, str], str] = {}
        
        # Load dictionary if path provided
        if dictionary_path:
            self.load_dictionary(dictionary_path)
        else:
            # Auto-load all dictionaries from dictionary folder
            self._auto_load_dictionaries()
    
    def _auto_load_dictionaries(self):
        """Auto-load all dictionary files from dictionary folder."""
        # Use app-relative path for both Python and EXE
        dict_dir = get_app_path("dictionary")
        if not dict_dir.exists():
            self.logger.info("No dictionary folder found")
            return
        
        # Find all dictionary files
        for dict_file in dict_dir.glob("learned_dictionary_*_*.json.gz"):
            try:
                # Parse filename: learned_dictionary_en_de.json.gz
                filename = dict_file.stem  # Remove .gz
                if filename.endswith('.json'):
                    filename = filename[:-5]  # Remove .json
                
                parts = filename.split('_')
                if len(parts) >= 4:  # learned_dictionary_XX_YY
                    source_lang = parts[2]
                    target_lang = parts[3]
                    
                    self.logger.info(f"Loading dictionary: {source_lang} → {target_lang}")
                    self.load_dictionary(str(dict_file), source_lang, target_lang)
                    
            except Exception as e:
                self.logger.error(f"Failed to load dictionary {dict_file}: {e}")
    
    def load_dictionary(self, dictionary_path: str, source_lang: str = "en", target_lang: str = "de"):
        """
        Load dictionary from file or directory.
        
        Args:
            dictionary_path: Path to dictionary file or directory containing dictionary files
            source_lang: Source language code (used only if loading a specific file)
            target_lang: Target language code (used only if loading a specific file)
        """
        try:
            dict_path = Path(dictionary_path)
            
            if not dict_path.exists():
                self.logger.warning(f"Dictionary path not found: {dictionary_path}")
                return
            
            # If it's a directory, load all dictionary files from it
            if dict_path.is_dir():
                self.logger.info(f"Loading dictionaries from directory: {dictionary_path}")
                dict_files = list(dict_path.glob("learned_dictionary_*_*.json.gz"))
                
                if not dict_files:
                    self.logger.info(f"No dictionary files found in directory: {dictionary_path}")
                    return
                
                # Load each dictionary file
                for dict_file in dict_files:
                    try:
                        # Parse filename: learned_dictionary_en_de.json.gz
                        filename = dict_file.stem  # Remove .gz
                        if filename.endswith('.json'):
                            filename = filename[:-5]  # Remove .json
                        
                        parts = filename.split('_')
                        if len(parts) >= 4:  # learned_dictionary_XX_YY
                            src_lang = parts[2]
                            tgt_lang = parts[3]
                            
                            # Load this specific dictionary file
                            with gzip.open(dict_file, 'rt', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            # Extract translations from the file format
                            # Format: {"version": "1.0", "translations": {...}, "source_language": "en", "target_language": "de"}
                            if isinstance(data, dict) and 'translations' in data:
                                dictionary_data = data['translations']
                            else:
                                dictionary_data = data
                            
                            # Store in memory
                            lang_pair = (src_lang, tgt_lang)
                            self._dictionaries[lang_pair] = dictionary_data
                            self._dictionary_paths[lang_pair] = str(dict_file)
                            
                            self.logger.info(f"Loaded dictionary {src_lang}→{tgt_lang}: {len(dictionary_data)} entries from {dict_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to load dictionary file {dict_file}: {e}")
                
                # Clear cache when dictionaries change
                self.cache.clear()
                return
            
            # It's a file, load it directly
            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract translations from the file format
            # Format: {"version": "1.0", "translations": {...}, "source_language": "en", "target_language": "de"}
            if isinstance(data, dict) and 'translations' in data:
                dictionary_data = data['translations']
                # Use language codes from file if available
                if 'source_language' in data and 'target_language' in data:
                    source_lang = data['source_language']
                    target_lang = data['target_language']
            else:
                # Old format: direct dictionary
                dictionary_data = data
            
            # Store in memory
            lang_pair = (source_lang, target_lang)
            self._dictionaries[lang_pair] = dictionary_data
            self._dictionary_paths[lang_pair] = str(dict_path)
            
            self.logger.info(f"Loaded dictionary {source_lang}→{target_lang}: {len(dictionary_data)} entries from {dict_path}")
            
            # Clear cache when dictionary changes
            self.cache.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to load dictionary: {e}")
            import traceback
            traceback.print_exc()
    
    def lookup(self, text: str, source_language: str = "en", target_language: str = "de") -> Optional[DictionaryEntry]:
        """
        Look up translation in dictionary.
        
        Args:
            text: Source text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            DictionaryEntry if found, None otherwise
        """
        with self._lock:
            self.total_lookups += 1
            
            # Create cache key
            cache_key = f"{source_language}:{target_language}:{text}"
            
            # Check cache first
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.cache_hits += 1
                return cached
            
            # Look up in dictionary
            lang_pair = (source_language, target_language)
            if lang_pair not in self._dictionaries:
                # Cache miss
                self.cache.put(cache_key, None)
                return None
            
            dictionary = self._dictionaries[lang_pair]
            
            # Try exact match with text
            text_lower = text.lower()
            
            # Try different key formats
            possible_keys = [
                text,  # Exact match
                text_lower,  # Lowercase
                f"{source_language}:{target_language}:{text_lower}",  # Full key format
            ]
            
            for key in possible_keys:
                if key in dictionary:
                    entry_data = dictionary[key]
                    # Dictionary format with metadata
                    entry = DictionaryEntry(
                        source_text=entry_data.get('original', text),
                        translation=entry_data.get('translation', text),
                        source_language=source_language,
                        target_language=target_language,
                        usage_count=entry_data.get('usage_count', 1),
                        confidence=entry_data.get('confidence', 0.9),
                        last_used=entry_data.get('last_used', datetime.now().isoformat()),
                        source_engine=entry_data.get('engine', 'dictionary')
                        )
                    self.cache.put(cache_key, entry)
                    return entry
            
            # Not found
            self.cache.put(cache_key, None)
            return None
    
    def fuzzy_lookup(self, text: str, source_language: str = "en", target_language: str = "de", 
                    threshold: float = 0.8, context: Optional[str] = None) -> List[Tuple[DictionaryEntry, float]]:
        """
        Advanced fuzzy lookup with multiple similarity algorithms and context awareness.
        
        Uses:
        - Levenshtein distance (edit distance)
        - Sequence matching (difflib)
        - Token-based similarity
        - Context matching
        - Quality-weighted scoring
        
        Args:
            text: Source text
            source_language: Source language code
            target_language: Target language code
            threshold: Minimum similarity threshold (0.0-1.0)
            context: Optional context for better matching
            
        Returns:
            List of (DictionaryEntry, similarity_score) tuples sorted by relevance
        """
        lang_pair = (source_language, target_language)
        if lang_pair not in self._dictionaries:
            return []
        
        dictionary = self._dictionaries[lang_pair]
        matches = []
        
        text_lower = text.lower().strip()
        text_tokens = set(re.findall(r'\w+', text_lower))
        context_tokens = set(re.findall(r'\w+', context.lower())) if context else set()
        
        for dict_key, entry_data in dictionary.items():
            # Extract source text from key (format: "en:de:hello" or just "hello")
            if ':' in dict_key:
                parts = dict_key.split(':', 2)
                source_text = parts[2] if len(parts) > 2 else dict_key
            else:
                source_text = dict_key
            
            source_lower = source_text.lower().strip()
            
            # Skip if too different in length
            len_ratio = min(len(text_lower), len(source_lower)) / max(len(text_lower), len(source_lower))
            if len_ratio < 0.3:
                continue
            
            # Calculate multiple similarity scores
            scores = []
            
            # 1. Sequence matching (difflib) - best for typos
            seq_similarity = difflib.SequenceMatcher(None, text_lower, source_lower).ratio()
            scores.append(('sequence', seq_similarity, 0.4))  # 40% weight
            
            # 2. Token-based similarity - good for word order changes
            source_tokens = set(re.findall(r'\w+', source_lower))
            if text_tokens and source_tokens:
                token_similarity = len(text_tokens & source_tokens) / len(text_tokens | source_tokens)
                scores.append(('token', token_similarity, 0.3))  # 30% weight
            
            # 3. Substring matching - good for partial matches
            if text_lower in source_lower or source_lower in text_lower:
                substring_score = min(len(text_lower), len(source_lower)) / max(len(text_lower), len(source_lower))
                scores.append(('substring', substring_score, 0.2))  # 20% weight
            
            # Create entry from data
            if isinstance(entry_data, str):
                # Old format: direct translation string
                entry = DictionaryEntry(
                    source_text=source_text,
                    translation=entry_data,
                    source_language=source_language,
                    target_language=target_language,
                    usage_count=1,
                    confidence=0.9,
                    last_used=datetime.now().isoformat()
                )
            else:
                # New format: dictionary with metadata
                entry = DictionaryEntry(
                    source_text=entry_data.get('original', source_text),
                    translation=entry_data.get('translation', source_text),
                    source_language=source_language,
                    target_language=target_language,
                    usage_count=entry_data.get('usage_count', 1),
                    confidence=entry_data.get('confidence', 0.9),
                    last_used=entry_data.get('last_used', datetime.now().isoformat()),
                    source_engine=entry_data.get('engine', 'dictionary')
                )
            
            # 4. Context matching - bonus for context relevance
            if context_tokens and entry.context_tags:
                context_overlap = len(context_tokens & entry.context_tags) / len(context_tokens | entry.context_tags)
                scores.append(('context', context_overlap, 0.1))  # 10% weight
            
            # Calculate weighted similarity
            weighted_similarity = sum(score * weight for _, score, weight in scores)
            
            # Boost by quality and effective confidence
            quality_boost = 1.0 + (entry.quality_score * 0.2)  # Up to 20% boost
            confidence_boost = 1.0 + (entry.get_effective_confidence() * 0.1)  # Up to 10% boost
            
            final_score = weighted_similarity * quality_boost * confidence_boost
            final_score = min(1.0, final_score)  # Cap at 1.0
            
            if final_score >= threshold:
                matches.append((entry, final_score))
        
        # Sort by score (highest first), then by usage count
        matches.sort(key=lambda x: (x[1], x[0].usage_count), reverse=True)
        
        return matches
    
    def add_entry(self, source_text: str, translation: str, source_language: str = "en", 
                 target_language: str = "de", confidence: float = 1.0, context: Optional[str] = None,
                 source_engine: str = "manual", auto_merge: bool = True):
        """
        Intelligently add or update dictionary entry with automatic learning.
        
        Features:
        - Automatic variant detection
        - Smart merging of similar entries
        - Context extraction
        - Quality scoring
        - Duplicate detection
        
        Args:
            source_text: Source text
            translation: Translation
            source_language: Source language code
            target_language: Target language code
            confidence: Confidence score (0.0-1.0)
            context: Optional context for better learning
            source_engine: Origin of translation (manual, ai, learned)
            auto_merge: Automatically merge with similar entries
        """
        with self._lock:
            lang_pair = (source_language, target_language)
            
            # Create dictionary if doesn't exist
            if lang_pair not in self._dictionaries:
                self._dictionaries[lang_pair] = {}
            
            dictionary = self._dictionaries[lang_pair]
            
            # Normalize text
            source_normalized = source_text.strip()
            translation_normalized = translation.strip()
            
            # Check for exact match
            if source_normalized in dictionary:
                # Update existing entry
                entry_data = dictionary[source_normalized]
                entry = DictionaryEntry.from_dict(source_normalized, entry_data, source_language, target_language)
                
                # Check if translation is different (variant)
                if translation_normalized != entry.translation:
                    entry.add_variant(translation_normalized)
                    
                    # If new translation has higher confidence, make it primary
                    if confidence > entry.confidence:
                        entry.variants.append(entry.translation)
                        entry.translation = translation_normalized
                        entry.confidence = confidence
                
                # Update usage and context
                entry.update_usage(success=True)
                if context:
                    entry.add_context(context)
                
                # Update quality score based on consistency
                entry.quality_score = min(1.0, entry.quality_score + 0.05)  # Gradual improvement
                
                # Save back
                dictionary[source_normalized] = entry.to_dict()
                
            elif auto_merge:
                # Check for similar entries (fuzzy match)
                similar = self.fuzzy_lookup(source_normalized, source_language, target_language, threshold=0.9, context=context)
                
                if similar:
                    # Merge with most similar entry
                    best_match, similarity = similar[0]
                    
                    self.logger.info(f"Merging '{source_normalized}' with similar entry '{best_match.source_text}' (similarity: {similarity:.2f})")
                    
                    # Add as variant to existing entry
                    entry_data = dictionary[best_match.source_text]
                    entry = DictionaryEntry.from_dict(best_match.source_text, entry_data, source_language, target_language)
                    entry.add_variant(translation_normalized)
                    entry.update_usage(success=True)
                    if context:
                        entry.add_context(context)
                    
                    dictionary[best_match.source_text] = entry.to_dict()
                else:
                    # Create new entry
                    self._create_new_entry(dictionary, source_normalized, translation_normalized, 
                                          source_language, target_language, confidence, context, source_engine)
            else:
                # Create new entry without merging
                self._create_new_entry(dictionary, source_normalized, translation_normalized,
                                      source_language, target_language, confidence, context, source_engine)
            
            # Clear cache
            self.cache.clear()
    
    def _create_new_entry(self, dictionary: dict, source_text: str, translation: str,
                         source_lang: str, target_lang: str, confidence: float,
                         context: Optional[str], source_engine: str):
        """Create a new dictionary entry with full metadata."""
        entry = DictionaryEntry(
            source_text=source_text,
            translation=translation,
            source_language=source_lang,
            target_language=target_lang,
            usage_count=1,
            confidence=confidence,
            last_used=datetime.now().isoformat(),
            source_engine=source_engine,
            quality_score=confidence * 0.8,  # Initial quality based on confidence
            creation_date=datetime.now().isoformat()
        )
        
        if context:
            entry.add_context(context)
        
        dictionary[source_text] = entry.to_dict()
    
    def learn_from_translation(self, source_text: str, translation: str, 
                              source_language: str, target_language: str,
                              confidence: float, context: Optional[str] = None):
        """
        Learn from AI translation with quality validation.
        
        Only adds high-quality translations to avoid polluting dictionary.
        
        Args:
            source_text: Source text
            translation: AI translation
            source_language: Source language
            target_language: Target language
            confidence: AI confidence score
            context: Optional context
        """
        # Quality threshold for automatic learning
        MIN_CONFIDENCE = 0.85
        MIN_LENGTH = 2  # Minimum word length
        
        # Validate quality
        if confidence < MIN_CONFIDENCE:
            return  # Too low confidence
        
        if len(source_text.split()) < MIN_LENGTH:
            return  # Too short (likely noise)
        
        # Check if translation looks valid (not empty, not same as source)
        if not translation or translation.strip() == source_text.strip():
            return
        
        # Add to dictionary with AI source
        self.add_entry(
            source_text=source_text,
            translation=translation,
            source_language=source_language,
            target_language=target_language,
            confidence=confidence,
            context=context,
            source_engine="ai_learned",
            auto_merge=True
        )
        
        self.logger.info(f"Learned: '{source_text}' → '{translation}' (confidence: {confidence:.2f})")
    
    def get_stats(self, source_language: str = "en", target_language: str = "de") -> DictionaryStats:
        """
        Get dictionary statistics.
        
        Args:
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            DictionaryStats object
        """
        lang_pair = (source_language, target_language)
        
        if lang_pair not in self._dictionaries:
            return DictionaryStats()
        
        dictionary = self._dictionaries[lang_pair]
        
        # Calculate stats
        total_entries = len(dictionary)
        total_usage = sum(entry.get('usage_count', 0) for entry in dictionary.values())
        average_usage = total_usage / total_entries if total_entries > 0 else 0.0
        
        # Get most used
        sorted_entries = sorted(
            dictionary.items(),
            key=lambda x: x[1].get('usage_count', 0),
            reverse=True
        )[:10]
        
        most_used = [
            {
                'original': source,
                'translation': data.get('translation', ''),
                'usage_count': data.get('usage_count', 0),
                'confidence': data.get('confidence', 0.0)
            }
            for source, data in sorted_entries
        ]
        
        return DictionaryStats(
            total_entries=total_entries,
            total_usage=total_usage,
            average_usage=average_usage,
            total_lookups=self.total_lookups,
            cache_hits=self.cache_hits,
            most_used=most_used
        )
    
    def get_statistics(self, source_language: str = "en", target_language: str = "de") -> DictionaryStats:
        """
        Alias for get_stats() for backward compatibility.
        
        Args:
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            DictionaryStats object
        """
        return self.get_stats(source_language, target_language)
    
    def get_available_language_pairs(self) -> List[Tuple[str, str, str, int]]:
        """
        Get list of all loaded language-pair dictionaries.
        
        Returns:
            List of tuples: (source_lang, target_lang, file_path, entry_count)
        """
        pairs = []
        for (source_lang, target_lang), dictionary in self._dictionaries.items():
            file_path = self._dictionary_paths.get((source_lang, target_lang), "")
            entry_count = len(dictionary)
            pairs.append((source_lang, target_lang, file_path, entry_count))
        
        return pairs
    
    def get_loaded_dictionary_path(self, source_language: str, target_language: str) -> Optional[str]:
        """
        Get the file path of the currently loaded dictionary for a language pair.
        
        Args:
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            File path string if loaded, None otherwise
        """
        lang_pair = (source_language, target_language)
        return self._dictionary_paths.get(lang_pair)
    
    def get_all_entries(self, source_language: str = "en", target_language: str = "de") -> List[DictionaryEntry]:
        """
        Get all dictionary entries for a language pair.
        
        Args:
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            List of DictionaryEntry objects
        """
        lang_pair = (source_language, target_language)
        
        if lang_pair not in self._dictionaries:
            return []
        
        dictionary = self._dictionaries[lang_pair]
        entries = []
        
        with self._lock:
            for source_text, entry_data in dictionary.items():
                try:
                    entry = DictionaryEntry.from_dict(source_text, entry_data, source_language, target_language)
                    entries.append(entry)
                except Exception as e:
                    self.logger.warning(f"Failed to parse entry '{source_text}': {e}")
        
        return entries
    
    def reload_specific_dictionary(self, file_path: str, source_language: str, target_language: str):
        """
        Reload a specific dictionary file for a language pair.
        This allows switching between multiple dictionary files for the same language pair.
        
        Args:
            file_path: Path to the dictionary file to load
            source_language: Source language code
            target_language: Target language code
        """
        try:
            dict_path = Path(file_path)
            
            if not dict_path.exists():
                self.logger.warning(f"Dictionary file not found: {file_path}")
                return
            
            # Load the specific file
            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract translations
            if isinstance(data, dict) and 'translations' in data:
                dictionary_data = data['translations']
            else:
                dictionary_data = data
            
            # Replace the dictionary for this language pair
            lang_pair = (source_language, target_language)
            self._dictionaries[lang_pair] = dictionary_data
            self._dictionary_paths[lang_pair] = str(dict_path)
            
            # Clear cache
            self.cache.clear()
            
            self.logger.info(f"Reloaded dictionary {source_language}→{target_language} from {file_path}: {len(dictionary_data)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to reload dictionary from {file_path}: {e}")
    
    def cleanup_stale_entries(self, source_language: str = "en", target_language: str = "de",
                             min_quality: float = 0.3, max_age_days: int = 365):
        """
        Remove low-quality and stale entries to keep dictionary clean.
        
        Args:
            source_language: Source language code
            target_language: Target language code
            min_quality: Minimum quality score to keep
            max_age_days: Maximum age in days for unused entries
        """
        lang_pair = (source_language, target_language)
        if lang_pair not in self._dictionaries:
            return
        
        dictionary = self._dictionaries[lang_pair]
        to_remove = []
        
        for source_text, entry_data in dictionary.items():
            entry = DictionaryEntry.from_dict(source_text, entry_data, source_language, target_language)
            
            # Check quality
            if entry.quality_score < min_quality and entry.usage_count < 3:
                to_remove.append(source_text)
                continue
            
            # Check age
            try:
                last_used = datetime.fromisoformat(entry.last_used)
                days_old = (datetime.now() - last_used).days
                
                if days_old > max_age_days and entry.usage_count < 5:
                    to_remove.append(source_text)
            except:
                pass
        
        # Remove stale entries
        for source_text in to_remove:
            del dictionary[source_text]
        
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} stale entries from {source_language}→{target_language}")
            self.cache.clear()
    
    def get_recommendations(self, source_language: str = "en", target_language: str = "de",
                           limit: int = 10) -> List[Dict]:
        """
        Get recommendations for entries that need review or improvement.
        
        Returns entries with:
        - Low quality scores
        - High usage but low confidence
        - Multiple variants (needs consolidation)
        - Stale entries (not used recently)
        
        Args:
            source_language: Source language code
            target_language: Target language code
            limit: Maximum recommendations to return
            
        Returns:
            List of recommendation dictionaries
        """
        lang_pair = (source_language, target_language)
        if lang_pair not in self._dictionaries:
            return []
        
        dictionary = self._dictionaries[lang_pair]
        recommendations = []
        
        for source_text, entry_data in dictionary.items():
            entry = DictionaryEntry.from_dict(source_text, entry_data, source_language, target_language)
            
            # Check for issues
            issues = []
            priority = 0
            
            # Low quality but high usage
            if entry.quality_score < 0.5 and entry.usage_count > 10:
                issues.append("Low quality despite high usage")
                priority += 3
            
            # Multiple variants (needs consolidation)
            if len(entry.variants) > 2:
                issues.append(f"Has {len(entry.variants)} variants - needs review")
                priority += 2
            
            # Low success rate
            if entry.success_rate < 0.7:
                issues.append(f"Low success rate: {entry.success_rate:.1%}")
                priority += 3
            
            # Stale but frequently used
            if entry.decay_factor < 0.7 and entry.usage_count > 20:
                issues.append("Frequently used but stale - needs refresh")
                priority += 2
            
            if issues:
                recommendations.append({
                    'source_text': source_text,
                    'translation': entry.translation,
                    'issues': issues,
                    'priority': priority,
                    'usage_count': entry.usage_count,
                    'quality_score': entry.quality_score,
                    'variants': entry.variants
                })
        
        # Sort by priority (highest first)
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        return recommendations[:limit]
    
    def save_dictionary(self, dictionary_path: str, source_language: str = "en", target_language: str = "de",
                       auto_cleanup: bool = True):
        """
        Save dictionary to file with optional automatic cleanup.
        
        Args:
            dictionary_path: Path to save dictionary
            source_language: Source language code
            target_language: Target language code
            auto_cleanup: Automatically clean up stale entries before saving
        """
        try:
            lang_pair = (source_language, target_language)
            
            if lang_pair not in self._dictionaries:
                self.logger.warning(f"No dictionary to save for {source_language}→{target_language}")
                return
            
            # Optional cleanup before saving
            if auto_cleanup:
                self.cleanup_stale_entries(source_language, target_language)
            
            dictionary = self._dictionaries[lang_pair]
            
            # Save to compressed JSON with metadata
            dict_path = Path(dictionary_path)
            dict_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            if dict_path.exists():
                backup_path = dict_path.with_suffix('.backup.json.gz')
                import shutil
                shutil.copy2(dict_path, backup_path)
            
            # Create dictionary file with proper format
            dict_file_data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(dictionary),
                "compressed": True,
                "source_language": source_language,
                "target_language": target_language,
                "translations": dictionary
            }
            
            with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                json.dump(dict_file_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved dictionary {source_language}→{target_language}: {len(dictionary)} entries to {dictionary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save dictionary: {e}")
            import traceback
            traceback.print_exc()


def create_smart_dictionary(dictionary_path: Optional[str] = None, cache_size: int = 1000) -> 'SmartDictionary':
    """
    Create a SmartDictionary instance.
    
    Args:
        dictionary_path: Path to dictionary file (optional)
        cache_size: Size of lookup cache
        
    Returns:
        SmartDictionary instance
    """
    return SmartDictionary(dictionary_path, cache_size)
