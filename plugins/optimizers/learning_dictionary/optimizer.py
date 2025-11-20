"""
Smart Dictionary Optimizer Plugin
Persistent learned translations for instant lookup using SmartDictionary
"""

from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "app"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import sentence validator
try:
    from app.utils.sentence_validator import validate_for_dictionary
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    print("[LEARNING_DICT] Warning: Sentence validator not available")


class SmartDictionaryOptimizer:
    """Provides instant lookup for learned translations using SmartDictionary (dict_engine)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.auto_save = config.get('auto_save', True)
        self.min_confidence = config.get('min_confidence', 0.8)
        self.validate_sentences = config.get('validate_sentences', True)
        
        # Statistics
        self.total_lookups = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.saved_translations = 0
        self.rejected_translations = 0  # Rejected by validation
        
        print(f"[LEARNING_DICT] Initialized (auto_save={'on' if self.auto_save else 'off'}, "
              f"min_confidence={self.min_confidence}, validate_sentences={self.validate_sentences})")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-process: Check dictionary for existing translations"""
        texts = data.get('texts', [])
        dict_engine = data.get('dictionary_engine')
        
        if not texts or not dict_engine:
            return data
        
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'de')
        
        # Check each text in dictionary
        for text_item in texts:
            self.total_lookups += 1
            
            source_text = text_item.get('text', '')
            
            # Try dictionary lookup
            try:
                translation = dict_engine.translate(source_text, source_lang, target_lang)
                
                if translation and translation != source_text:
                    # Found in dictionary!
                    text_item['translated_text'] = translation
                    text_item['from_dictionary'] = True
                    text_item['skip_translation'] = True  # Skip main translation
                    self.cache_hits += 1
                else:
                    self.cache_misses += 1
            except Exception as e:
                self.cache_misses += 1
        
        return data
    
    def post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process: Save new translations to dictionary (including from cache)"""
        if not self.auto_save:
            return data
        
        texts = data.get('texts', [])
        dict_engine = data.get('dictionary_engine')
        
        if not texts or not dict_engine:
            return data
        
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'de')
        
        # Save new translations
        for text_item in texts:
            # Skip if already from dictionary (already saved)
            if text_item.get('from_dictionary'):
                continue
            
            source_text = text_item.get('text', '')
            translated_text = text_item.get('translated_text', '')
            confidence = text_item.get('confidence', 0.9)  # Default confidence for cache hits
            
            # Get confidence from text_item if available
            if 'confidence' in text_item:
                confidence = text_item['confidence']
            
            # Validate translation before saving (data protection)
            if self.validate_sentences and VALIDATOR_AVAILABLE:
                is_valid, reason = validate_for_dictionary(
                    source_text,
                    translated_text,
                    confidence,
                    self.min_confidence
                )
                
                if not is_valid:
                    self.rejected_translations += 1
                    print(f"[LEARNING_DICT] Rejected: '{source_text[:30]}...' - {reason}")
                    continue
            else:
                # Fallback validation without validator
                if not translated_text or confidence < self.min_confidence:
                    self.rejected_translations += 1
                    continue
            
            # Save validated translation
            try:
                # Add to dictionary
                if hasattr(dict_engine, 'add_entry'):
                    dict_engine.add_entry(
                        source_text,
                        translated_text,
                        source_lang,
                        target_lang,
                        confidence=confidence
                    )
                    self.saved_translations += 1
                    print(f"[LEARNING_DICT] ✓ Saved: '{source_text[:30]}...' → '{translated_text[:30]}...' (conf: {confidence:.2f})")
            except Exception as e:
                print(f"[LEARNING_DICT] Error saving translation: {e}")
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        hit_rate = (self.cache_hits / self.total_lookups * 100) if self.total_lookups > 0 else 0
        save_rate = (self.saved_translations / (self.saved_translations + self.rejected_translations) * 100) if (self.saved_translations + self.rejected_translations) > 0 else 0
        
        return {
            'total_lookups': self.total_lookups,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'saved_translations': self.saved_translations,
            'rejected_translations': self.rejected_translations,
            'save_rate': f"{save_rate:.1f}%",
            'auto_save': self.auto_save,
            'validation_enabled': self.validate_sentences
        }
    
    def reset(self):
        """Reset optimizer state"""
        self.total_lookups = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.saved_translations = 0
        self.rejected_translations = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> SmartDictionaryOptimizer:
    """Initialize the optimizer plugin"""
    return SmartDictionaryOptimizer(config)
