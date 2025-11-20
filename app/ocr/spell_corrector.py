"""
OCR Spell Corrector

Corrects common OCR errors before translation.
Uses simple heuristics and optional spell checking library.
"""

import re
from typing import Optional


class OCRSpellCorrector:
    """Corrects common OCR errors in text."""
    
    def __init__(self, language: str = 'en'):
        """
        Initialize spell corrector.
        
        Args:
            language: Language code for spell checking
        """
        self.language = language
        self.spell_checker = None
        
        # Try to load spell checker library
        try:
            from spellchecker import SpellChecker
            self.spell_checker = SpellChecker(language=language)
        except ImportError:
            # Spell checker not available, use basic corrections only
            pass
        
        # Common OCR character substitutions
        self.ocr_fixes = {
            '0': 'O',  # Zero to O
            '1': 'I',  # One to I
            '5': 'S',  # Five to S
            '8': 'B',  # Eight to B
            'rn': 'm',  # rn to m
            'vv': 'w',  # vv to w
            'VV': 'W',  # VV to W
        }
    
    def correct_text(self, text: str, aggressive: bool = False) -> str:
        """
        Correct OCR errors in text.
        
        Args:
            text: Text to correct
            aggressive: If True, applies more aggressive corrections
            
        Returns:
            Corrected text
        """
        if not text or not text.strip():
            return text
        
        corrected = text
        
        # Step 1: Fix common OCR character substitutions
        corrected = self._fix_common_substitutions(corrected)
        
        # Step 2: Fix capitalization issues
        corrected = self._fix_capitalization(corrected)
        
        # Step 3: Use spell checker if available
        if self.spell_checker and aggressive:
            corrected = self._spell_check(corrected)
        
        return corrected
    
    def _fix_common_substitutions(self, text: str) -> str:
        """Fix common OCR character substitutions."""
        # Only fix if the character is in the middle of a word
        result = text
        
        # Fix common patterns
        for wrong, right in self.ocr_fixes.items():
            # Only replace in word contexts
            result = re.sub(f'(?<=[a-zA-Z]){re.escape(wrong)}(?=[a-zA-Z])', right, result)
        
        return result
    
    def _fix_capitalization(self, text: str) -> str:
        """Fix random capitalization (common OCR error)."""
        # If text has random caps like "BRiNGiNe", try to fix it
        
        # Count uppercase and lowercase
        upper_count = sum(1 for c in text if c.isupper())
        lower_count = sum(1 for c in text if c.islower())
        
        # If mixed case with no clear pattern, normalize
        if upper_count > 0 and lower_count > 0:
            # Check if it's title case (first letter caps)
            if text[0].isupper() and text[1:].islower():
                return text  # Already proper title case
            
            # Check if it's all caps
            if upper_count > lower_count * 2:
                return text  # Keep all caps
            
            # Mixed case - try to fix
            # If starts with capital, make title case
            if text[0].isupper():
                return text.capitalize()
            else:
                return text.lower()
        
        return text
    
    def _spell_check(self, text: str) -> str:
        """Use spell checker to correct words."""
        if not self.spell_checker:
            return text
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Skip short words and words with numbers
            if len(word) <= 2 or any(c.isdigit() for c in word):
                corrected_words.append(word)
                continue
            
            # Check if word is misspelled
            if word.lower() not in self.spell_checker:
                # Get correction
                correction = self.spell_checker.correction(word.lower())
                if correction:
                    # Preserve original capitalization
                    if word[0].isupper():
                        correction = correction.capitalize()
                    corrected_words.append(correction)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)


# Global instance
_corrector = None


def get_corrector(language: str = 'en') -> OCRSpellCorrector:
    """Get or create spell corrector instance."""
    global _corrector
    if _corrector is None:
        _corrector = OCRSpellCorrector(language)
    return _corrector
