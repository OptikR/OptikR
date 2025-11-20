"""
Text Validator Optimizer Plugin
Filters garbage text and validates OCR quality
"""

from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "app"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from app.ocr.text_validator import TextValidator


class TextValidatorOptimizer:
    """Validates OCR text quality and filters garbage"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_confidence = config.get('min_confidence', 0.3)
        self.enable_smart_grammar = config.get('enable_smart_grammar', False)
        
        # Create text validator
        self.validator = TextValidator(
            enable_smart_grammar=self.enable_smart_grammar
        )
        
        # Statistics
        self.total_texts = 0
        self.filtered_texts = 0
        self.passed_texts = 0
        
        print(f"[TEXT_VALIDATOR] Initialized (min_confidence={self.min_confidence}, "
              f"smart_grammar={'enabled' if self.enable_smart_grammar else 'disabled'})")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process: Validate OCR text quality"""
        texts = data.get('texts', [])
        
        if not texts:
            return data
        
        validated_texts = []
        
        for text_item in texts:
            self.total_texts += 1
            
            text = text_item.get('text', '')
            
            # Validate text
            is_valid, confidence, reason = self.validator.is_valid_text(
                text, 
                self.min_confidence
            )
            
            if is_valid:
                # Keep text
                text_item['validated'] = True
                text_item['validation_confidence'] = confidence
                text_item['validation_reason'] = reason
                validated_texts.append(text_item)
                self.passed_texts += 1
            else:
                # Filter out
                self.filtered_texts += 1
                print(f"[TEXT_VALIDATOR] Filtered: '{text[:30]}...' "
                      f"(confidence={confidence:.2f}, reason={reason})")
        
        # Update data
        data['texts'] = validated_texts
        data['filtered_count'] = len(texts) - len(validated_texts)
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        filter_rate = (self.filtered_texts / self.total_texts * 100) if self.total_texts > 0 else 0
        
        return {
            'total_texts': self.total_texts,
            'passed_texts': self.passed_texts,
            'filtered_texts': self.filtered_texts,
            'filter_rate': f"{filter_rate:.1f}%",
            'min_confidence': self.min_confidence,
            'smart_grammar': self.enable_smart_grammar
        }
    
    def reset(self):
        """Reset optimizer state"""
        self.total_texts = 0
        self.filtered_texts = 0
        self.passed_texts = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> TextValidatorOptimizer:
    """Initialize the optimizer plugin"""
    return TextValidatorOptimizer(config)
