"""
Enhanced Auto Language Detection - Experimental Feature
Improved language detection using multiple algorithms.
"""

import re
from typing import Dict, List, Tuple, Optional
from collections import Counter


class EnhancedLanguageDetector:
    """
    Enhanced language detector using multiple detection methods.
    
    Features:
    - Character set analysis
    - Script detection (Latin, CJK, Cyrillic, etc.)
    - Common word patterns
    - Statistical analysis
    - Confidence scoring
    """
    
    # Character ranges for different scripts
    SCRIPT_RANGES = {
        'latin': [(0x0041, 0x007A), (0x00C0, 0x00FF)],
        'cyrillic': [(0x0400, 0x04FF)],
        'greek': [(0x0370, 0x03FF)],
        'arabic': [(0x0600, 0x06FF), (0x0750, 0x077F)],
        'hebrew': [(0x0590, 0x05FF)],
        'devanagari': [(0x0900, 0x097F)],
        'chinese': [(0x4E00, 0x9FFF)],
        'japanese_hiragana': [(0x3040, 0x309F)],
        'japanese_katakana': [(0x30A0, 0x30FF)],
        'korean': [(0xAC00, 0xD7AF)],
        'thai': [(0x0E00, 0x0E7F)],
    }
    
    # Common words for language identification
    COMMON_WORDS = {
        'en': ['the', 'is', 'and', 'to', 'of', 'a', 'in', 'that', 'it', 'for'],
        'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'],
        'es': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se'],
        'fr': ['le', 'de', 'un', 'être', 'et', 'à', 'il', 'avoir', 'ne', 'je'],
        'it': ['il', 'di', 'e', 'la', 'che', 'per', 'un', 'in', 'è', 'a'],
        'pt': ['o', 'de', 'e', 'a', 'que', 'do', 'em', 'um', 'para', 'é'],
        'ru': ['и', 'в', 'не', 'на', 'я', 'что', 'с', 'он', 'а', 'как'],
        'ja': ['の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し'],
        'zh': ['的', '一', '是', '不', '了', '在', '人', '有', '我', '他'],
        'ko': ['이', '그', '저', '것', '수', '있', '하', '등', '들', '및'],
    }
    
    # Language to script mapping
    LANGUAGE_SCRIPTS = {
        'en': 'latin', 'de': 'latin', 'es': 'latin', 'fr': 'latin',
        'it': 'latin', 'pt': 'latin', 'nl': 'latin', 'sv': 'latin',
        'ru': 'cyrillic', 'uk': 'cyrillic', 'bg': 'cyrillic',
        'el': 'greek',
        'ar': 'arabic',
        'he': 'hebrew',
        'hi': 'devanagari',
        'zh': 'chinese',
        'ja': 'japanese',
        'ko': 'korean',
        'th': 'thai',
    }
    
    def __init__(self):
        """Initialize enhanced language detector."""
        self.detection_history = []
        self.max_history = 20
    
    def detect_script(self, text: str) -> Dict[str, float]:
        """
        Detect script(s) used in text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary mapping script names to confidence scores
        """
        if not text:
            return {}
        
        script_counts = Counter()
        total_chars = 0
        
        for char in text:
            code_point = ord(char)
            
            # Skip whitespace and punctuation
            if char.isspace() or not char.isalnum():
                continue
            
            total_chars += 1
            
            # Check which script this character belongs to
            for script, ranges in self.SCRIPT_RANGES.items():
                for start, end in ranges:
                    if start <= code_point <= end:
                        script_counts[script] += 1
                        break
        
        if total_chars == 0:
            return {}
        
        # Convert counts to percentages
        script_percentages = {
            script: count / total_chars
            for script, count in script_counts.items()
        }
        
        return script_percentages
    
    def detect_by_common_words(self, text: str) -> Dict[str, float]:
        """
        Detect language by matching common words.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary mapping language codes to confidence scores
        """
        if not text:
            return {}
        
        # Normalize text
        text_lower = text.lower()
        words = re.findall(r'\w+', text_lower)
        
        if not words:
            return {}
        
        language_scores = {}
        
        for lang_code, common_words in self.COMMON_WORDS.items():
            # Count how many common words appear
            matches = sum(1 for word in words if word in common_words)
            
            # Calculate confidence (matches / total words)
            confidence = matches / len(words)
            
            if confidence > 0:
                language_scores[lang_code] = confidence
        
        return language_scores
    
    def detect_by_character_frequency(self, text: str) -> Dict[str, float]:
        """
        Detect language by character frequency analysis.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary mapping language codes to confidence scores
        """
        # Character frequency patterns for different languages
        # This is a simplified version - real implementation would use n-grams
        
        char_freq = Counter(text.lower())
        total_chars = sum(char_freq.values())
        
        if total_chars == 0:
            return {}
        
        scores = {}
        
        # English: high frequency of 'e', 't', 'a', 'o'
        en_chars = char_freq.get('e', 0) + char_freq.get('t', 0) + char_freq.get('a', 0) + char_freq.get('o', 0)
        scores['en'] = en_chars / total_chars
        
        # German: high frequency of 'e', 'n', 'i', 's'
        de_chars = char_freq.get('e', 0) + char_freq.get('n', 0) + char_freq.get('i', 0) + char_freq.get('s', 0)
        scores['de'] = de_chars / total_chars
        
        # Spanish: high frequency of 'e', 'a', 'o', 's'
        es_chars = char_freq.get('e', 0) + char_freq.get('a', 0) + char_freq.get('o', 0) + char_freq.get('s', 0)
        scores['es'] = es_chars / total_chars
        
        # French: high frequency of 'e', 'a', 's', 'i'
        fr_chars = char_freq.get('e', 0) + char_freq.get('a', 0) + char_freq.get('s', 0) + char_freq.get('i', 0)
        scores['fr'] = fr_chars / total_chars
        
        return scores
    
    def detect_language(self, text: str, context: Optional[List[str]] = None) -> Tuple[str, float]:
        """
        Detect language using multiple methods.
        
        Args:
            text: Input text
            context: Previous text for context
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not text or not text.strip():
            return ('unknown', 0.0)
        
        # Method 1: Script detection
        scripts = self.detect_script(text)
        
        # Method 2: Common words
        word_scores = self.detect_by_common_words(text)
        
        # Method 3: Character frequency
        freq_scores = self.detect_by_character_frequency(text)
        
        # Combine scores
        combined_scores = {}
        
        # Add script-based scores
        for script, script_conf in scripts.items():
            for lang_code, lang_script in self.LANGUAGE_SCRIPTS.items():
                if lang_script == script:
                    combined_scores[lang_code] = combined_scores.get(lang_code, 0) + script_conf * 0.4
        
        # Add word-based scores
        for lang_code, word_conf in word_scores.items():
            combined_scores[lang_code] = combined_scores.get(lang_code, 0) + word_conf * 0.4
        
        # Add frequency-based scores
        for lang_code, freq_conf in freq_scores.items():
            combined_scores[lang_code] = combined_scores.get(lang_code, 0) + freq_conf * 0.2
        
        # Use context if available
        if context and self.detection_history:
            # Boost languages that appeared recently
            recent_langs = [lang for lang, _ in self.detection_history[-3:]]
            for lang in recent_langs:
                if lang in combined_scores:
                    combined_scores[lang] *= 1.2
        
        # Find best match
        if not combined_scores:
            return ('unknown', 0.0)
        
        best_lang = max(combined_scores.items(), key=lambda x: x[1])
        
        # Update history
        self.detection_history.append(best_lang)
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
        
        return best_lang
    
    def get_language_confidence(self, text: str, expected_language: str) -> float:
        """
        Get confidence that text is in expected language.
        
        Args:
            text: Input text
            expected_language: Expected language code
            
        Returns:
            Confidence score (0-1)
        """
        detected_lang, confidence = self.detect_language(text)
        
        if detected_lang == expected_language:
            return confidence
        else:
            return 1.0 - confidence
    
    def get_detection_stats(self) -> Dict:
        """Get detection statistics."""
        if not self.detection_history:
            return {'total_detections': 0}
        
        lang_counts = Counter(lang for lang, _ in self.detection_history)
        avg_confidence = sum(conf for _, conf in self.detection_history) / len(self.detection_history)
        
        return {
            'total_detections': len(self.detection_history),
            'language_distribution': dict(lang_counts),
            'avg_confidence': avg_confidence,
            'most_common': lang_counts.most_common(1)[0] if lang_counts else None
        }
