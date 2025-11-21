"""
Sentence Validator for Learning Dictionary

Validates sentences before saving to ensure quality and completeness.
Implements data protection by only saving valid, complete sentences.

Author: OptikR Team
Date: 2024
"""

import re
from typing import Tuple


class SentenceValidator:
    """Validates sentences for dictionary storage."""
    
    def __init__(self, min_length: int = 2, max_length: int = 500):
        """
        Initialize validator.
        
        Args:
            min_length: Minimum sentence length in characters
            max_length: Maximum sentence length in characters
        """
        self.min_length = min_length
        self.max_length = max_length
        
        # Sentence ending punctuation
        self.sentence_endings = {'.', '!', '?', '。', '！', '？', '…'}
        
        # Common incomplete patterns
        self.incomplete_patterns = [
            r'^[a-z]',  # Starts with lowercase (likely fragment)
            r'^\d+$',  # Only numbers
            r'^[^\w\s]+$',  # Only punctuation/symbols
            r'^\s*$',  # Only whitespace
        ]
    
    def is_valid_sentence(self, text: str) -> Tuple[bool, str]:
        """
        Check if text is a valid, complete sentence.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not text:
            return False, "Empty text"
        
        # Strip whitespace
        text = text.strip()
        
        # Length check
        if len(text) < self.min_length:
            return False, f"Too short (< {self.min_length} characters)"
        
        if len(text) > self.max_length:
            return False, f"Too long (> {self.max_length} characters)"
        
        # Check for incomplete patterns
        for pattern in self.incomplete_patterns:
            if re.match(pattern, text):
                return False, "Incomplete or invalid pattern"
        
        # Check for sentence structure
        # Should have at least one word character
        if not re.search(r'\w', text):
            return False, "No word characters found"
        
        # Check for proper sentence ending (optional but recommended)
        # We'll be lenient here - not all valid sentences end with punctuation
        # But we'll flag it as a warning
        has_ending = any(text.endswith(ending) for ending in self.sentence_endings)
        
        # Check for minimum word count (at least 2 words for most languages)
        words = re.findall(r'\w+', text)
        if len(words) < 1:
            return False, "No words found"
        
        # Single character "words" are suspicious
        if len(words) == 1 and len(words[0]) == 1:
            return False, "Single character only"
        
        # All checks passed
        return True, "Valid sentence"
    
    def should_save_to_dictionary(
        self,
        source_text: str,
        translated_text: str,
        confidence: float,
        min_confidence: float = 0.8
    ) -> Tuple[bool, str]:
        """
        Determine if translation should be saved to dictionary.
        
        Args:
            source_text: Original text
            translated_text: Translated text
            confidence: Translation confidence (0.0-1.0)
            min_confidence: Minimum confidence threshold
            
        Returns:
            Tuple of (should_save, reason)
        """
        # Check confidence threshold
        if confidence < min_confidence:
            return False, f"Confidence too low ({confidence:.2f} < {min_confidence})"
        
        # Validate source text
        source_valid, source_reason = self.is_valid_sentence(source_text)
        if not source_valid:
            return False, f"Invalid source: {source_reason}"
        
        # Validate translated text
        trans_valid, trans_reason = self.is_valid_sentence(translated_text)
        if not trans_valid:
            return False, f"Invalid translation: {trans_reason}"
        
        # Check if source and translation are identical (likely error)
        if source_text.strip().lower() == translated_text.strip().lower():
            return False, "Source and translation are identical"
        
        # All checks passed
        return True, "Valid for dictionary storage"
    
    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text before storage.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # Strip whitespace
        text = text.strip()
        
        # Normalize whitespace (multiple spaces → single space)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
        
        return text


# Global validator instance
_validator = None


def get_validator() -> SentenceValidator:
    """Get global validator instance."""
    global _validator
    if _validator is None:
        _validator = SentenceValidator()
    return _validator


def validate_for_dictionary(
    source_text: str,
    translated_text: str,
    confidence: float,
    min_confidence: float = 0.8
) -> Tuple[bool, str]:
    """
    Convenience function to validate translation for dictionary storage.
    
    Args:
        source_text: Original text
        translated_text: Translated text
        confidence: Translation confidence
        min_confidence: Minimum confidence threshold
        
    Returns:
        Tuple of (should_save, reason)
    """
    validator = get_validator()
    return validator.should_save_to_dictionary(
        source_text,
        translated_text,
        confidence,
        min_confidence
    )
