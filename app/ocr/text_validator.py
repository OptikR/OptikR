"""
Intelligent Text Validation

Validates OCR text to filter out nonsense before translation.
Checks if text is readable, makes sense, and is worth translating.
"""

import re
from typing import Tuple, Optional


class TextValidator:
    """
    Validates OCR text quality and readability.
    Filters out garbage text before it gets translated.
    """
    
    def __init__(self, dict_engine=None, enable_smart_grammar=False):
        """
        Initialize text validator.
        
        Args:
            dict_engine: Optional dictionary engine for word validation (SmartDictionary)
            enable_smart_grammar: Enable lightweight grammar checking (default: False)
        """
        self.dict_engine = dict_engine
        self.enable_smart_grammar = enable_smart_grammar
        
        # Common English words for basic validation
        self.common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'can', 'may', 'might', 'must', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your',
            'his', 'her', 'its', 'our', 'their', 'me', 'him', 'us', 'them',
            'what', 'when', 'where', 'who', 'why', 'how', 'all', 'each', 'every',
            'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 'one', 'two',
            'first', 'new', 'good', 'high', 'old', 'great', 'big', 'small'
        }
        
        # Smart Grammar Mode: Lightweight grammar patterns (English)
        self.grammar_patterns = {
            # Subject-Verb patterns
            'subject_verb': [
                r'\b(i|you|we|they)\s+(am|are|have|do|will|can)\b',
                r'\b(he|she|it)\s+(is|has|does|will|can)\b',
            ],
            # Article-Noun patterns
            'article_noun': [
                r'\b(the|a|an)\s+\w+',
                r'\b(this|that|these|those)\s+\w+',
            ],
            # Verb-Object patterns
            'verb_object': [
                r'\b(is|are|was|were)\s+(a|an|the)?\s*\w+',
                r'\b(have|has|had)\s+(a|an|the)?\s*\w+',
            ],
            # Preposition-Noun patterns
            'prep_noun': [
                r'\b(in|on|at|to|for|with|by|from)\s+(the|a|an)?\s*\w+',
            ],
            # Question patterns
            'question': [
                r'\b(what|when|where|who|why|how)\s+',
                r'\b(do|does|did|will|can|could|would|should)\s+\w+',
            ],
        }
        
        # Word order anomalies (scrambled text detection)
        self.scrambled_indicators = [
            r'\b(the|a|an)\s+(is|are|was|were)\b',  # Article before verb (wrong)
            r'\b(is|are|was|were)\s+(the|a|an)\s+(is|are|was|were)\b',  # Double verb
        ]
        
        # Patterns that indicate valid text
        self.valid_patterns = [
            r'\b(the|a|an)\s+\w+',  # Article + word
            r'\w+\s+(is|are|was|were)\s+\w+',  # Verb patterns
            r'\w+,\s*\w+',  # Comma-separated words
        ]
        
        # Patterns that indicate garbage
        self.garbage_patterns = [
            r'^[^a-zA-Z0-9\s]{3,}$',  # Only special characters
            r'^[0-9\s\-_\.]{5,}$',  # Only numbers and punctuation
            r'(.)\1{4,}',  # Same character repeated 5+ times
            # Removed all-caps check - manga uses all caps normally
        ]
    
    def is_valid_text(self, text: str, min_confidence: float = 0.3) -> Tuple[bool, float, str]:
        """
        Check if text is valid and worth translating.
        
        Args:
            text: Text to validate
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            (is_valid, confidence, reason)
        """
        if not text or not text.strip():
            return False, 0.0, "Empty text"
        
        text = text.strip()
        
        # Check 1: Minimum length (but allow short text if it looks like a word fragment)
        if len(text) < 2:
            return False, 0.0, "Too short (< 2 chars)"
        
        # Special case: Short text with letters and punctuation (likely continuation)
        if len(text) <= 8 and re.search(r'[a-zA-Z]{3,}', text):
            # Has at least 3 consecutive letters - likely a word fragment
            pass  # Continue validation
        
        # Check 2: Check for garbage patterns
        for pattern in self.garbage_patterns:
            if re.search(pattern, text):
                return False, 0.0, f"Garbage pattern detected"
        
        # Check 3: Must contain at least some letters
        if not re.search(r'[a-zA-Z]', text):
            return False, 0.0, "No letters found"
        
        # Check 4: Calculate confidence score
        confidence = 0.0
        reasons = []
        
        # Has common words?
        words = text.lower().split()
        common_word_count = sum(1 for word in words if word in self.common_words)
        
        # Check dictionary for known words
        dict_word_count = 0
        if self.dict_engine and words:
            for word in words:
                # Check if word or its variations exist in dictionary
                word_clean = word.strip('.,!?;:')
                if self._is_in_dictionary(word_clean):
                    dict_word_count += 1
        
        if words:
            # Common words score
            common_ratio = common_word_count / len(words)
            confidence += common_ratio * 0.3
            if common_word_count > 0:
                reasons.append(f"{common_word_count} common words")
            
            # Dictionary words score (higher weight)
            if dict_word_count > 0:
                dict_ratio = dict_word_count / len(words)
                confidence += dict_ratio * 0.4
                reasons.append(f"{dict_word_count} known words")
            
            # Even without common/dict words, if it has multiple words it's likely valid
            if common_word_count == 0 and dict_word_count == 0 and len(words) >= 2:
                confidence += 0.2
                reasons.append(f"{len(words)} words")
        
        # Has valid patterns?
        pattern_matches = 0
        for pattern in self.valid_patterns:
            if re.search(pattern, text.lower()):
                pattern_matches += 1
        if pattern_matches > 0:
            confidence += min(0.3, pattern_matches * 0.15)
            reasons.append(f"{pattern_matches} valid patterns")
        
        # Smart Grammar Mode (optional, lightweight)
        if self.enable_smart_grammar and len(words) >= 2:
            grammar_score = self._check_grammar_patterns(text.lower())
            if grammar_score > 0:
                confidence += grammar_score
                reasons.append(f"grammar patterns (+{grammar_score:.2f})")
        
        # Has proper capitalization?
        # Special case: ALL CAPS is valid (manga style)
        if text.isupper():
            # All caps is valid for manga, even single words
            if len(words) >= 2:
                confidence += 0.15
                reasons.append("manga-style caps")
            else:
                # Single word in all caps - still valid for manga
                confidence += 0.35  # Higher bonus for single caps words (ensures >= 0.3)
                reasons.append("single caps word")
        elif text[0].isupper() or text.istitle():
            confidence += 0.1
            reasons.append("proper capitalization")
        
        # Check for hyphenated word (split across lines)
        if text.endswith('-') or text.endswith('—'):
            confidence += 0.15
            reasons.append("hyphenated (continues)")
        
        # Has punctuation (indicates complete sentence)?
        if any(p in text for p in '.!?,;:'):
            confidence += 0.1
            reasons.append("has punctuation")
        
        # Word length distribution (real text has varied word lengths)
        if words and len(words) > 1:
            word_lengths = [len(w) for w in words]
            avg_length = sum(word_lengths) / len(word_lengths)
            if 3 <= avg_length <= 8:  # Reasonable average
                confidence += 0.1
                reasons.append("reasonable word lengths")
        
        # Final decision
        is_valid = confidence >= min_confidence
        reason = ", ".join(reasons) if reasons else "no valid indicators"
        
        return is_valid, confidence, reason
    
    def _is_in_dictionary(self, word: str) -> bool:
        """
        Check if word exists in SmartDictionary.
        
        Args:
            word: Word to check
            
        Returns:
            True if word is in dictionary
        """
        if self.dict_engine and word:
            try:
                word_lower = word.lower()
                
                # Check SmartDictionary
                if hasattr(self.dict_engine, '_dictionary') and hasattr(self.dict_engine._dictionary, '_dictionaries'):
                    for lang_pair, dictionary in self.dict_engine._dictionary._dictionaries.items():
                        for dict_key in dictionary.keys():
                            # Extract source text from key
                            if ':' in dict_key:
                                parts = dict_key.split(':', 2)
                                dict_text = parts[2] if len(parts) > 2 else dict_key
                            else:
                                dict_text = dict_key
                            
                            dict_text_lower = dict_text.lower()
                            # Check if word matches or is part of the dictionary text
                            if word_lower == dict_text_lower or word_lower in dict_text_lower.split():
                                return True
            except Exception:
                pass
        
        return False
    
    def set_dictionary_engine(self, dict_engine):
        """Set the dictionary engine reference (SmartDictionary)."""
        self.dict_engine = dict_engine
        """DEPRECATED: Set the learning dictionary reference. Use set_dictionary_engine() instead."""
        self.learning_dict = learning_dict
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text with intelligent OCR error correction.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Fix common OCR errors
        # Pipe/vertical bar to I
        text = re.sub(r'\|', 'I', text)
        
        # l -> I in certain contexts
        text = re.sub(r'\bl\b', 'I', text)  # Standalone 'l' -> 'I'
        text = re.sub(r'\b(when|where|while|if)\s+l\b', r'\1 I', text, flags=re.IGNORECASE)
        
        # 0 -> O in words
        text = re.sub(r'([a-zA-Z])0([a-zA-Z])', r'\1O\2', text)
        
        # rn -> m (common OCR error)
        text = re.sub(r'\brn\b', 'm', text)
        
        # cl -> d (common OCR error in some fonts)
        text = re.sub(r'\bcl\b', 'd', text)
        
        # Remove weird Unicode characters
        text = ''.join(char for char in text if ord(char) < 65536)
        
        return text
    
    def should_translate(self, text: str, ocr_confidence: float = 1.0) -> Tuple[bool, str]:
        """
        Determine if text should be sent to translation.
        
        Args:
            text: Text to check
            ocr_confidence: OCR confidence score
            
        Returns:
            (should_translate, reason)
        """
        # Clean text first
        cleaned = self.clean_text(text)
        
        # Validate
        is_valid, text_confidence, reason = self.is_valid_text(cleaned)
        
        # Combine OCR confidence with text validation confidence
        combined_confidence = (ocr_confidence + text_confidence) / 2
        
        # Decision thresholds
        if not is_valid:
            return False, f"Invalid text: {reason}"
        
        if combined_confidence < 0.3:  # Lower threshold - be more permissive
            return False, f"Low confidence ({combined_confidence:.2f}): {reason}"
        
        if len(cleaned) < 2:
            return False, "Too short after cleaning"
        
        # Additional check: If OCR confidence is high, trust it more
        if ocr_confidence > 0.85:
            return True, f"High OCR confidence ({ocr_confidence:.2f})"
        
        return True, f"Valid ({combined_confidence:.2f}): {reason}"
    
    def _check_grammar_patterns(self, text: str) -> float:
        """
        Check for basic grammar patterns (Smart Grammar Mode).
        Fast, lightweight, no external dependencies.
        
        Args:
            text: Lowercase text to check
            
        Returns:
            float: Grammar score (0.0-0.2)
        """
        score = 0.0
        matches = 0
        
        # Check for scrambled text (negative indicator)
        for pattern in self.scrambled_indicators:
            if re.search(pattern, text):
                return -0.1  # Penalty for scrambled text
        
        # Check grammar patterns (positive indicators)
        for category, patterns in self.grammar_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    matches += 1
                    break  # One match per category
        
        # Score based on matches (max 0.2)
        if matches >= 3:
            score = 0.2  # Excellent grammar
        elif matches == 2:
            score = 0.15  # Good grammar
        elif matches == 1:
            score = 0.1  # Basic grammar
        
        return score


def create_text_validator(dict_engine=None) -> TextValidator:
    """
    Create a text validator instance.
    
    Args:
        dict_engine: Optional dictionary engine for word validation (SmartDictionary)
    """
    return TextValidator(dict_engine=dict_engine)


# Example usage
if __name__ == "__main__":
    validator = TextValidator()
    
    test_cases = [
        ("An Axe, a spear, a sword,", 0.9),
        ("AN AXE, A SPEAR, A SWORD,", 0.9),  # Manga style
        ("A HAMMER, A FLAIL, A BOW,", 0.9),  # Manga style
        ("AN INSTRU-", 0.9),  # Hyphenated (continues)
        ("MENT...", 0.9),  # Continuation
        ("sup reme", 0.8),
        ("!!!###$$$", 0.9),
        ("12345678", 0.9),
        ("aaaaaaaaaa", 0.9),
        ("The quick brown fox", 0.95),
        ("Hello World", 0.9),
        ("x", 0.9),
    ]
    
    print("Text Validation Tests:")
    print("=" * 70)
    
    for text, ocr_conf in test_cases:
        should_trans, reason = validator.should_translate(text, ocr_conf)
        status = "✓ TRANSLATE" if should_trans else "✗ SKIP"
        print(f"{status}: '{text}'")
        print(f"  Reason: {reason}")
        print()
