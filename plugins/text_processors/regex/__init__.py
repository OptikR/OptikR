"""
Regex Text Processor

Advanced regex-based text processing with:
- Pattern-based filtering
- Text replacement
- Format normalization
- Custom transformations
"""

import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class RegexTextProcessor:
    """Advanced regex-based text processor."""
    
    def __init__(self, config: dict):
        """Initialize regex processor with configuration."""
        self.config = config
        self.filter_mode = config.get('filter_mode', 'basic')
        
        # Predefined patterns for common use cases
        self.patterns = self._load_patterns()
        
        # Custom user patterns
        self.custom_patterns = config.get('custom_patterns', [])
        
        # Statistics
        self.total_processed = 0
        self.total_filtered = 0
        self.total_replaced = 0
        
        logger.info(f"Regex Text Processor initialized (mode: {self.filter_mode})")
    
    def _load_patterns(self) -> Dict[str, List[Tuple[str, str]]]:
        """Load predefined regex patterns."""
        return {
            'basic': [
                # Remove excessive whitespace
                (r'\s+', ' '),
                # Remove leading/trailing whitespace
                (r'^\s+|\s+$', ''),
            ],
            'aggressive': [
                # Remove excessive whitespace
                (r'\s+', ' '),
                # Remove leading/trailing whitespace
                (r'^\s+|\s+$', ''),
                # Remove special characters (keep alphanumeric and basic punctuation)
                (r'[^\w\s.,!?;:\-\'\"()]', ''),
                # Normalize multiple punctuation
                (r'([.,!?;:]){2,}', r'\1'),
            ],
            'normalize': [
                # Normalize quotes
                (r'["""]', '"'),
                (r'[''']', "'"),
                # Normalize dashes
                (r'[—–]', '-'),
                # Normalize ellipsis
                (r'\.{3,}', '...'),
                # Remove zero-width characters
                (r'[\u200b-\u200f\ufeff]', ''),
            ],
            'ocr_cleanup': [
                # Fix common OCR errors
                (r'\bl\b', 'I'),  # Standalone 'l' -> 'I'
                (r'\b0\b', 'O'),  # Standalone '0' -> 'O'
                # Remove random single characters
                (r'\s[a-z]\s', ' '),
                # Fix spacing around punctuation
                (r'\s+([.,!?;:])', r'\1'),
                (r'([.,!?;:])\s*([a-zA-Z])', r'\1 \2'),
            ],
            'japanese': [
                # Remove half-width spaces in Japanese text
                (r'(?<=[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF])\s+(?=[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF])', ''),
                # Normalize Japanese punctuation
                (r'[。、]', lambda m: m.group(0)),
            ],
            'url_email': [
                # Remove URLs
                (r'https?://\S+', ''),
                # Remove email addresses
                (r'\S+@\S+\.\S+', ''),
            ],
        }
    
    def process_text(self, text: str) -> str:
        """Process text using configured patterns."""
        if not text or not text.strip():
            return text
        
        self.total_processed += 1
        original_text = text
        
        # Apply mode-specific patterns
        if self.filter_mode in self.patterns:
            for pattern, replacement in self.patterns[self.filter_mode]:
                try:
                    text = re.sub(pattern, replacement, text)
                except Exception as e:
                    logger.warning(f"Pattern failed: {pattern} - {e}")
        
        # Apply custom patterns
        for pattern_config in self.custom_patterns:
            pattern = pattern_config.get('pattern')
            replacement = pattern_config.get('replacement', '')
            if pattern:
                try:
                    text = re.sub(pattern, replacement, text)
                    self.total_replaced += 1
                except Exception as e:
                    logger.warning(f"Custom pattern failed: {pattern} - {e}")
        
        # Track if text was filtered
        if text != original_text:
            self.total_filtered += 1
        
        return text
    
    def filter_text(self, text: str, min_length: int = 1, max_length: int = 10000) -> Optional[str]:
        """Filter text based on length and content."""
        if not text or not text.strip():
            return None
        
        # Length check
        if len(text) < min_length or len(text) > max_length:
            return None
        
        # Process text
        processed = self.process_text(text)
        
        # Check if still valid after processing
        if not processed or not processed.strip():
            return None
        
        return processed
    
    def extract_patterns(self, text: str, pattern: str) -> List[str]:
        """Extract all matches for a given pattern."""
        try:
            matches = re.findall(pattern, text)
            return matches
        except Exception as e:
            logger.warning(f"Pattern extraction failed: {pattern} - {e}")
            return []
    
    def replace_pattern(self, text: str, pattern: str, replacement: str) -> str:
        """Replace pattern in text."""
        try:
            return re.sub(pattern, replacement, text)
        except Exception as e:
            logger.warning(f"Pattern replacement failed: {pattern} - {e}")
            return text
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'total_processed': self.total_processed,
            'total_filtered': self.total_filtered,
            'total_replaced': self.total_replaced,
            'filter_rate': f"{(self.total_filtered / self.total_processed * 100):.1f}%" if self.total_processed > 0 else "0%"
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.total_processed = 0
        self.total_filtered = 0
        self.total_replaced = 0


# Global processor instance
_processor = None


def initialize(config: dict) -> bool:
    """Initialize text processor."""
    global _processor
    try:
        _processor = RegexTextProcessor(config)
        logger.info("Regex Text Processor initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Regex Text Processor: {e}")
        return False


def process_text(text: str) -> str:
    """Process/filter text."""
    if _processor:
        return _processor.process_text(text)
    return text


def filter_text(text: str, min_length: int = 1, max_length: int = 10000) -> Optional[str]:
    """Filter text based on criteria."""
    if _processor:
        return _processor.filter_text(text, min_length, max_length)
    return text


def extract_patterns(text: str, pattern: str) -> List[str]:
    """Extract pattern matches."""
    if _processor:
        return _processor.extract_patterns(text, pattern)
    return []


def replace_pattern(text: str, pattern: str, replacement: str) -> str:
    """Replace pattern in text."""
    if _processor:
        return _processor.replace_pattern(text, pattern, replacement)
    return text


def get_stats() -> Dict[str, int]:
    """Get processing statistics."""
    if _processor:
        return _processor.get_stats()
    return {}


def cleanup():
    """Clean up resources."""
    global _processor
    if _processor:
        logger.info(f"Regex Text Processor cleanup - Stats: {_processor.get_stats()}")
        _processor = None
