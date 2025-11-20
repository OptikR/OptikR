"""
Intelligent Spell Corrector Plugin

Advanced OCR error correction with:
- Common OCR character substitutions
- Capitalization normalization
- Spell checking with pyspellchecker
- Learning dictionary integration
- Context-aware corrections
"""

import re
import logging
from typing import List, Dict, Optional, Tuple


class IntelligentSpellCorrector:
    """Advanced spell corrector for OCR text."""
    
    def __init__(self, config: dict):
        """Initialize spell corrector with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Settings
        self.aggressive_mode = config.get('aggressive_mode', False)
        self.use_learning_dict = config.get('use_learning_dict', True)
        self.fix_capitalization = config.get('fix_capitalization', True)
        self.min_confidence = config.get('min_confidence', 0.5)
        self.language = config.get('language', 'en')
        
        # Initialize spell checker
        self.spell_checker = None
        try:
            from spellchecker import SpellChecker
            self.spell_checker = SpellChecker(language=self.language)
            self.logger.info(f"Spell checker initialized for language: {self.language}")
        except ImportError:
            self.logger.warning("pyspellchecker not installed. Install with: pip install pyspellchecker")
        
        # Dictionary engine reference (will be set by pipeline)
        self.dict_engine = None
        
        # Common OCR character substitutions (context-aware)
        self.char_substitutions = {
            # Numbers to letters
            '0': ['O', 'o'],
            '1': ['I', 'l', 'i'],
            '3': ['B'],
            '5': ['S', 's'],
            '6': ['G', 'b'],
            '8': ['B'],
            '9': ['g', 'q'],
            
            # Letter combinations
            'rn': ['m'],
            'vv': ['w'],
            'VV': ['W'],
            'cl': ['d'],
            'li': ['h'],
            'ii': ['u'],
        }
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'corrections_made': 0,
            'dict_assisted': 0,
            'spell_checked': 0
        }
    
    def set_dictionary_engine(self, dict_engine):
        """Set reference to dictionary engine for context (NEW SYSTEM)."""
        self.dict_engine = dict_engine
        if dict_engine:
            self.logger.info("Dictionary engine connected to spell corrector")
    
    def set_learning_dictionary(self, learning_dict):
        """DEPRECATED: Use set_dictionary_engine() instead."""
        self.logger.warning("set_learning_dictionary() is deprecated, use set_dictionary_engine()")
    
    def process(self, text_blocks: List) -> List:
        """
        Process text blocks and correct OCR errors.
        
        Args:
            text_blocks: List of text blocks from OCR
            
        Returns:
            List of corrected text blocks
        """
        corrected_blocks = []
        
        for block in text_blocks:
            original_text = block.text
            corrected_text = self.correct_text(original_text)
            
            # Update block with corrected text
            block.text = corrected_text
            corrected_blocks.append(block)
            
            # Track statistics
            self.stats['total_processed'] += 1
            if corrected_text != original_text:
                self.stats['corrections_made'] += 1
        
        return corrected_blocks
    
    def correct_text(self, text: str) -> str:
        """
        Correct OCR errors in text using multiple strategies.
        
        Args:
            text: Original OCR text
            
        Returns:
            Corrected text
        """
        if not text or not text.strip():
            return text
        
        corrected = text
        
        # Step 1: Check dictionary engine for known corrections (NEW SYSTEM)
        if self.use_learning_dict and self.dict_engine:
            dict_correction = self._check_learning_dict(corrected)
            if dict_correction:
                self.stats['dict_assisted'] += 1
                return dict_correction
        
        # Step 2: Fix common OCR character substitutions
        corrected = self._fix_char_substitutions(corrected)
        
        # Step 3: Fix capitalization issues
        if self.fix_capitalization:
            corrected = self._fix_capitalization(corrected)
        
        # Step 4: Spell check individual words
        if self.spell_checker:
            corrected = self._spell_check_words(corrected)
            if corrected != text:
                self.stats['spell_checked'] += 1
        
        return corrected
    
    def _check_learning_dict(self, text: str) -> Optional[str]:
        """Check if dictionary has a known correction (NEW SYSTEM)."""
        if not self.use_learning_dict or not self.dict_engine:
            return None
        
        try:
            # Check if this exact text has been translated before
            # If so, use the original text from the dictionary
            # This helps with consistent OCR errors
            
            # Get dictionary data from new engine - with safety checks
            if not hasattr(self.dict_engine, '_dictionary'):
                return None
            
            if not hasattr(self.dict_engine._dictionary, '_dictionaries'):
                return None
            
            # Check all loaded language pairs
            for lang_pair, dictionary in self.dict_engine._dictionary._dictionaries.items():
                # Look for similar entries (fuzzy match)
                for dict_key, entry_data in dictionary.items():
                    # Extract source text from key
                    if ':' in dict_key:
                        parts = dict_key.split(':', 2)
                        original = parts[2] if len(parts) > 2 else dict_key
                    else:
                        original = dict_key
                    
                    # Also check the 'original' field in entry data
                    if isinstance(entry_data, dict):
                        original = entry_data.get('original', original)
                    
                    # High similarity - use the dictionary version
                    if self._similarity(text.lower(), original.lower()) > 0.9:
                        return original
            
        except Exception as e:
            self.logger.debug(f"Dictionary check failed: {e}")
        
        return None
    
    def _fix_char_substitutions(self, text: str) -> str:
        """Fix common OCR character substitutions."""
        result = text
        
        # Only fix substitutions in word contexts
        for wrong, rights in self.char_substitutions.items():
            for right in rights:
                # Pattern: letter before and after
                pattern = f'(?<=[a-zA-Z]){re.escape(wrong)}(?=[a-zA-Z])'
                result = re.sub(pattern, right, result)
        
        return result
    
    def _fix_capitalization(self, text: str) -> str:
        """
        Fix random capitalization (common OCR error).
        
        Examples:
            "BRiNGiNe" -> "Bringing"
            "The Lieht" -> "The Lieht" (preserve if reasonable)
        """
        words = text.split()
        fixed_words = []
        
        for word in words:
            if len(word) <= 2:
                fixed_words.append(word)
                continue
            
            # Count uppercase and lowercase
            upper_count = sum(1 for c in word if c.isupper())
            lower_count = sum(1 for c in word if c.islower())
            
            # If no letters, skip
            if upper_count + lower_count == 0:
                fixed_words.append(word)
                continue
            
            # All caps - keep as is
            if lower_count == 0:
                fixed_words.append(word)
                continue
            
            # All lowercase - keep as is
            if upper_count == 0:
                fixed_words.append(word)
                continue
            
            # Title case (first letter caps) - keep as is
            if word[0].isupper() and word[1:].islower():
                fixed_words.append(word)
                continue
            
            # Mixed case - normalize
            # If more uppercase than lowercase, keep all caps
            if upper_count > lower_count:
                fixed_words.append(word.upper())
            else:
                # Make title case
                fixed_words.append(word.capitalize())
        
        return ' '.join(fixed_words)
    
    def _spell_check_words(self, text: str) -> str:
        """Spell check individual words."""
        if not self.spell_checker:
            return text
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Skip short words, numbers, and punctuation
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) <= 2 or any(c.isdigit() for c in clean_word):
                corrected_words.append(word)
                continue
            
            # Check if word is misspelled
            if clean_word.lower() not in self.spell_checker:
                # Get correction
                correction = self.spell_checker.correction(clean_word.lower())
                
                if correction and correction != clean_word.lower():
                    # Calculate confidence
                    confidence = self._similarity(clean_word.lower(), correction)
                    
                    if confidence >= self.min_confidence or self.aggressive_mode:
                        # Apply correction, preserving capitalization
                        if clean_word[0].isupper():
                            correction = correction.capitalize()
                        if clean_word.isupper():
                            correction = correction.upper()
                        
                        # Replace in original word (preserve punctuation)
                        corrected_word = word.replace(clean_word, correction)
                        corrected_words.append(corrected_word)
                    else:
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0.0 to 1.0)."""
        try:
            # Try using textdistance if available
            import textdistance
            return textdistance.levenshtein.normalized_similarity(s1, s2)
        except ImportError:
            # Fallback to simple ratio
            if s1 == s2:
                return 1.0
            
            # Simple character overlap ratio
            set1 = set(s1.lower())
            set2 = set(s2.lower())
            overlap = len(set1 & set2)
            total = len(set1 | set2)
            return overlap / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict:
        """Get correction statistics."""
        return self.stats.copy()


def initialize(config: dict) -> IntelligentSpellCorrector:
    """Initialize the spell corrector plugin."""
    return IntelligentSpellCorrector(config)
