"""
Intelligent Text Processor

Combines text validation, OCR error correction, and smart merging
for parallel OCR/translation processing.

Handles common OCR errors like:
- | → I (pipe to capital I)
- l → I (lowercase L to capital I)
- 0 → O (zero to capital O)
- rn → m (two letters to one)

Author: OptikR Team
Date: 2025
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ProcessedText:
    """Processed text with corrections and confidence."""
    original: str
    corrected: str
    confidence: float
    corrections: List[str]  # List of corrections applied
    is_valid: bool
    validation_reason: str


class IntelligentTextProcessor:
    """
    Intelligent text processor that combines:
    - OCR error correction
    - Text validation
    - Smart dictionary lookup
    - Context-aware processing
    """
    
    def __init__(self, dict_engine=None, enable_corrections=True, enable_context=True):
        """
        Initialize intelligent text processor.
        
        Args:
            dict_engine: SmartDictionary instance for word validation
            enable_corrections: Enable OCR error corrections
            enable_context: Enable context-aware processing
        """
        self.dict_engine = dict_engine
        self.enable_corrections = enable_corrections
        self.enable_context = enable_context
        
        # Common OCR error patterns
        self.ocr_corrections = {
            # Pipe/vertical bar to I
            r'\|': 'I',
            # Standalone lowercase L to I
            r'\bl\b': 'I',
            # Zero in middle of words to O
            r'([a-zA-Z])0([a-zA-Z])': r'\1O\2',
            # rn to m (common OCR error)
            r'rn': 'm',
            # cl to d (common OCR error)
            r'cl': 'd',
            # vv to w (common OCR error)
            r'vv': 'w',
            # Fix encoding issues with apostrophes and smart quotes
            r'æ': "'",
            r'Ã¦': "'",
            r'â€™': "'",
            r'Ã¢â‚¬â„¢': "'",
            r'\u2018': "'",  # LEFT SINGLE QUOTATION MARK
            r'\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
            r''': "'",  # LEFT SINGLE QUOTATION MARK (literal)
            r''': "'",  # RIGHT SINGLE QUOTATION MARK (literal)
        }
        
        # Context patterns for better correction
        self.context_patterns = {
            # "When | was" → "When I was"
            r'\b(when|where|while|if)\s+\|': r'\1 I',
            # "| am" → "I am"
            r'^\|\s+(am|was|will|can|have)': r'I \1',
            # "at home" with pipe → "at home" with I
            r'\|\s+(am|was|at|in|on)': r'I \1',
        }
        
        # Common word patterns for validation (including short words and contractions)
        self.common_words = {
            # 1-letter words
            'i', 'a',
            # 2-letter words
            'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 'hi', 'ho', 
            'if', 'in', 'is', 'it', 'me', 'my', 'no', 'of', 'oh', 'on', 'or', 
            'so', 'to', 'uh', 'up', 'us', 'we', 'ye', 'yo',
            # 3-letter words
            'and', 'the', 'for', 'you', 'not', 'but', 'all', 'any', 'can', 'out',
            'get', 'him', 'her', 'who', 'man', 'new', 'now', 'one', 'two', 'she',
            'has', 'had', 'was', 'are', 'see', 'way', 'why', 'how', 'day', 'too',
            'big', 'bad', 'far', 'few', 'say', 'run', 'fun', 'let', 'old', 'own',
            # Longer common words
            'with', 'from', 'were', 'been', 'have', 'does', 'will', 'would', 
            'could', 'should', 'might', 'must', 'this', 'that', 'these', 'those',
            'they', 'your', 'his', 'its', 'our', 'their', 'them', 'what', 'when', 
            'where', 'each', 'every', 'both', 'more', 'most', 'other', 'some', 
            'such', 'only', 'same', 'than', 'very', 'first', 'good', 'high', 
            'great', 'small', 'home', 'did', 'may',
            # Common contractions (without apostrophe for matching)
            "dont", "doesnt", "didnt", "wont", "wouldnt", "couldnt", "shouldnt",
            "cant", "isnt", "arent", "wasnt", "werent", "havent", "hasnt", "hadnt",
            "im", "ive", "id", "ill", "youre", "youve", "youd", "youll",
            "hes", "shes", "its", "were", "theyre", "theyve", "theyd", "theyll"
        }
        
        # Statistics
        self.total_processed = 0
        self.total_corrected = 0
        self.total_validated = 0
        self.total_rejected = 0
    
    def process_text(self, text: str, context: Optional[str] = None, 
                    ocr_confidence: float = 1.0) -> ProcessedText:
        """
        Process text with intelligent corrections and validation.
        
        Args:
            text: Raw OCR text
            context: Optional context (previous/next text)
            ocr_confidence: OCR engine confidence score
            
        Returns:
            ProcessedText with corrections and validation
        """
        self.total_processed += 1
        
        original = text
        corrected = text
        corrections = []
        
        # Step 1: Apply context-aware corrections first (higher priority)
        if self.enable_context and context:
            for pattern, replacement in self.context_patterns.items():
                if re.search(pattern, corrected, re.IGNORECASE):
                    new_text = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
                    if new_text != corrected:
                        corrections.append(f"Context: '{pattern}' → '{replacement}'")
                        corrected = new_text
        
        # Step 2: Apply general OCR corrections
        if self.enable_corrections:
            for pattern, replacement in self.ocr_corrections.items():
                if re.search(pattern, corrected):
                    new_text = re.sub(pattern, replacement, corrected)
                    if new_text != corrected:
                        corrections.append(f"OCR: '{pattern}' → '{replacement}'")
                        corrected = new_text
        
        # Step 3: Validate corrected text
        is_valid, confidence, reason = self._validate_text(corrected, ocr_confidence)
        
        if is_valid:
            self.total_validated += 1
        else:
            self.total_rejected += 1
        
        if corrections:
            self.total_corrected += 1
        
        return ProcessedText(
            original=original,
            corrected=corrected,
            confidence=confidence,
            corrections=corrections,
            is_valid=is_valid,
            validation_reason=reason
        )
    
    def process_batch(self, texts: List[Dict[str, Any]], 
                     enable_merging: bool = True) -> List[ProcessedText]:
        """
        Process a batch of texts with context awareness.
        
        Args:
            texts: List of text dictionaries with 'text', 'bbox', 'confidence'
            enable_merging: Enable intelligent text merging
            
        Returns:
            List of ProcessedText objects
        """
        if not texts:
            return []
        
        # DO NOT SORT - Keep original OCR order (Tesseract provides correct reading order)
        # Sorting by bbox breaks the order for curved/manga text
        sorted_texts = texts
        
        processed = []
        
        for i, text_item in enumerate(sorted_texts):
            text = text_item.get('text', '')
            ocr_conf = text_item.get('confidence', 1.0)
            
            # Get context from adjacent texts
            context = None
            if i > 0:
                prev_text = sorted_texts[i-1].get('text', '')
                context = prev_text
            
            # Process with context
            result = self.process_text(text, context, ocr_conf)
            processed.append(result)
        
        return processed
    
    def _validate_text(self, text: str, ocr_confidence: float) -> Tuple[bool, float, str]:
        """
        Validate text quality.
        
        Args:
            text: Text to validate
            ocr_confidence: OCR confidence score
            
        Returns:
            (is_valid, confidence, reason)
        """
        if not text or not text.strip():
            return False, 0.0, "Empty text"
        
        text = text.strip()
        
        # Minimum length check (allow single-letter valid words like "I" and "A")
        if len(text) < 2 and text.upper() not in ['I', 'A']:
            return False, 0.0, "Too short"
        
        # Must contain letters
        if not re.search(r'[a-zA-Z]', text):
            return False, 0.0, "No letters"
        
        # Calculate confidence
        confidence = 0.0
        reasons = []
        
        # Check for common words (also check without apostrophes for contractions)
        words = text.lower().split()
        common_count = 0
        for w in words:
            w_clean = w.strip('.,!?;:')
            # Check as-is
            if w_clean in self.common_words:
                common_count += 1
            # Also check without apostrophes/special chars (for contractions with encoding issues)
            elif w_clean.replace("'", "").replace("æ", "").replace("â€™", "") in self.common_words:
                common_count += 1
        
        if words:
            common_ratio = common_count / len(words)
            confidence += common_ratio * 0.4
            if common_count > 0:
                reasons.append(f"{common_count} common words")
        
        # Check dictionary if available
        if self.dict_engine and words:
            dict_count = 0
            for word in words:
                word_clean = word.strip('.,!?;:')
                if self._is_in_dictionary(word_clean):
                    dict_count += 1
            
            if dict_count > 0:
                dict_ratio = dict_count / len(words)
                confidence += dict_ratio * 0.4
                reasons.append(f"{dict_count} known words")
        
        # Capitalization bonus
        if text[0].isupper() or text.isupper():
            confidence += 0.2
            reasons.append("proper capitalization")
        
        # Combine with OCR confidence
        combined_confidence = (confidence + ocr_confidence) / 2
        
        is_valid = combined_confidence >= 0.3
        reason = ", ".join(reasons) if reasons else "no indicators"
        
        return is_valid, combined_confidence, reason
    
    def _is_in_dictionary(self, word: str) -> bool:
        """Check if word exists in smart dictionary."""
        if not self.dict_engine or not word:
            return False
        
        try:
            word_lower = word.lower()
            
            # Check SmartDictionary
            if hasattr(self.dict_engine, '_dictionary'):
                dict_obj = self.dict_engine._dictionary
                if hasattr(dict_obj, '_dictionaries'):
                    for lang_pair, dictionary in dict_obj._dictionaries.items():
                        for dict_key in dictionary.keys():
                            # Extract source text from key
                            if ':' in dict_key:
                                parts = dict_key.split(':', 2)
                                dict_text = parts[2] if len(parts) > 2 else dict_key
                            else:
                                dict_text = dict_key
                            
                            dict_text_lower = dict_text.lower()
                            if word_lower == dict_text_lower or word_lower in dict_text_lower.split():
                                return True
        except Exception:
            pass
        
        return False
    
    def merge_processed_texts(self, processed: List[ProcessedText], 
                             texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge processed texts back into text dictionaries.
        
        Args:
            processed: List of ProcessedText objects
            texts: Original text dictionaries
            
        Returns:
            Updated text dictionaries with corrections
        """
        if len(processed) != len(texts):
            return texts
        
        merged = []
        
        for proc, text_dict in zip(processed, texts):
            if proc.is_valid:
                # Update with corrected text
                updated = text_dict.copy()
                updated['text'] = proc.corrected
                updated['original_text'] = proc.original
                updated['corrections'] = proc.corrections
                updated['validation_confidence'] = proc.confidence
                updated['validation_reason'] = proc.validation_reason
                merged.append(updated)
        
        return merged
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        correction_rate = (self.total_corrected / self.total_processed * 100) if self.total_processed > 0 else 0
        validation_rate = (self.total_validated / self.total_processed * 100) if self.total_processed > 0 else 0
        rejection_rate = (self.total_rejected / self.total_processed * 100) if self.total_processed > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'total_corrected': self.total_corrected,
            'total_validated': self.total_validated,
            'total_rejected': self.total_rejected,
            'correction_rate': f"{correction_rate:.1f}%",
            'validation_rate': f"{validation_rate:.1f}%",
            'rejection_rate': f"{rejection_rate:.1f}%"
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.total_processed = 0
        self.total_corrected = 0
        self.total_validated = 0
        self.total_rejected = 0


def create_intelligent_processor(dict_engine=None) -> IntelligentTextProcessor:
    """
    Create an intelligent text processor instance.
    
    Args:
        dict_engine: SmartDictionary instance
        
    Returns:
        IntelligentTextProcessor instance
    """
    return IntelligentTextProcessor(dict_engine=dict_engine)


# Example usage
if __name__ == "__main__":
    processor = IntelligentTextProcessor()
    
    test_cases = [
        "When | was at home",
        "When l was at home",
        "He is g0ing home",
        "The quick br0wn fox",
        "| am happy",
        "This is a test",
        "!!!###",
        "12345"
    ]
    
    print("Intelligent Text Processing Tests:")
    print("=" * 70)
    
    for text in test_cases:
        result = processor.process_text(text, ocr_confidence=0.9)
        
        status = "✓ VALID" if result.is_valid else "✗ INVALID"
        print(f"\n{status}: '{text}'")
        if result.corrected != result.original:
            print(f"  Corrected: '{result.corrected}'")
            print(f"  Corrections: {', '.join(result.corrections)}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reason: {result.validation_reason}")
    
    print("\n" + "=" * 70)
    print("Statistics:")
    stats = processor.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
