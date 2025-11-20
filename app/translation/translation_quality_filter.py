"""
Translation Quality Filter

Prevents low-quality translations from being saved to the dictionary.
Filters out scuffy, garbage, or unreliable translations.
"""

import re
from typing import Optional, Tuple


class TranslationQualityFilter:
    """
    Filters translations before saving to dictionary.
    
    Prevents:
    - Very low confidence translations
    - Translations that are identical to source
    - Translations with too many special characters
    - Translations that are too short or too long
    - Translations with suspicious patterns
    """
    
    def __init__(self, config: dict = None):
        """Initialize quality filter with configuration."""
        self.config = config or {}
        
        # Thresholds
        self.min_confidence = self.config.get('min_confidence', 0.7)  # 70% minimum
        self.min_length = self.config.get('min_length', 2)  # At least 2 characters
        self.max_special_char_ratio = self.config.get('max_special_char_ratio', 0.5)  # 50% max
        self.min_word_count = self.config.get('min_word_count', 1)  # At least 1 word
        
        # Patterns that indicate bad translations
        self.bad_patterns = [
            r'^[^a-zA-Z0-9\s]{3,}$',  # Only special characters
            r'^[\d\s\-_\.]{5,}$',  # Only numbers and punctuation
            r'^[A-Z\s]{10,}$',  # All caps (likely OCR error)
            r'(.)\1{4,}',  # Repeated character 5+ times (aaaaa)
        ]
    
    def should_save(self, original: str, translation: str, confidence: float, 
                   source_lang: str, target_lang: str) -> Tuple[bool, Optional[str]]:
        """
        Check if translation should be saved to dictionary.
        
        Args:
            original: Original text
            translation: Translated text
            confidence: Translation confidence (0-1)
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Tuple of (should_save: bool, reason: str)
        """
        # Check 1: Confidence too low
        if confidence < self.min_confidence:
            return False, f"Confidence too low ({confidence:.2f} < {self.min_confidence})"
        
        # Check 2: Translation is empty
        if not translation or not translation.strip():
            return False, "Translation is empty"
        
        # Check 3: Translation is identical to original (no translation happened)
        if translation.strip().lower() == original.strip().lower():
            return False, "Translation identical to original"
        
        # Check 4: Translation too short
        if len(translation.strip()) < self.min_length:
            return False, f"Translation too short ({len(translation)} < {self.min_length})"
        
        # Check 5: Too many special characters
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', translation))
        total_chars = len(translation)
        if total_chars > 0:
            special_ratio = special_chars / total_chars
            if special_ratio > self.max_special_char_ratio:
                return False, f"Too many special characters ({special_ratio:.1%} > {self.max_special_char_ratio:.1%})"
        
        # Check 6: Not enough words
        words = translation.split()
        if len(words) < self.min_word_count:
            return False, f"Not enough words ({len(words)} < {self.min_word_count})"
        
        # Check 7: Bad patterns
        for pattern in self.bad_patterns:
            if re.search(pattern, translation):
                return False, f"Matches bad pattern: {pattern}"
        
        # Check 8: Translation is just whitespace variations
        if translation.replace(' ', '').replace('\t', '').replace('\n', '') == '':
            return False, "Translation is only whitespace"
        
        # Check 9: Translation has suspicious character repetition
        # Example: "aaaaaaa" or "111111"
        if len(set(translation.replace(' ', ''))) < 3 and len(translation) > 5:
            return False, "Translation has too few unique characters"
        
        # All checks passed!
        return True, None
    
    def get_quality_score(self, original: str, translation: str, confidence: float) -> float:
        """
        Calculate a quality score for the translation (0-1).
        
        Args:
            original: Original text
            translation: Translated text
            confidence: Translation confidence
            
        Returns:
            Quality score (0-1, higher is better)
        """
        score = confidence  # Start with confidence
        
        # Bonus for reasonable length
        if 5 <= len(translation) <= 100:
            score += 0.05
        
        # Bonus for having multiple words
        words = translation.split()
        if len(words) >= 2:
            score += 0.05
        
        # Bonus for low special character ratio
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', translation))
        total_chars = len(translation)
        if total_chars > 0:
            special_ratio = special_chars / total_chars
            if special_ratio < 0.2:  # Less than 20% special chars
                score += 0.05
        
        # Penalty for all caps
        if translation.isupper() and len(translation) > 5:
            score -= 0.1
        
        # Penalty for very similar to original
        if translation.lower() == original.lower():
            score -= 0.3
        
        # Cap at 1.0
        return min(1.0, max(0.0, score))
    
    def suggest_improvements(self, original: str, translation: str) -> list:
        """
        Suggest improvements for a translation.
        
        Args:
            original: Original text
            translation: Translated text
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for all caps
        if translation.isupper() and len(translation) > 5:
            suggestions.append("Consider using proper capitalization instead of ALL CAPS")
        
        # Check for excessive special characters
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', translation))
        if special_chars > len(translation) * 0.3:
            suggestions.append("Translation has many special characters - verify accuracy")
        
        # Check for very short translation
        if len(translation) < 3:
            suggestions.append("Translation is very short - verify completeness")
        
        # Check for identical translation
        if translation.strip().lower() == original.strip().lower():
            suggestions.append("Translation is identical to original - may not be translated")
        
        return suggestions


# Default instance with standard settings
default_quality_filter = TranslationQualityFilter({
    'min_confidence': 0.7,  # 70% minimum confidence
    'min_length': 2,
    'max_special_char_ratio': 0.5,
    'min_word_count': 1
})


# Strict instance for high-quality only
strict_quality_filter = TranslationQualityFilter({
    'min_confidence': 0.85,  # 85% minimum confidence
    'min_length': 3,
    'max_special_char_ratio': 0.3,
    'min_word_count': 1
})
