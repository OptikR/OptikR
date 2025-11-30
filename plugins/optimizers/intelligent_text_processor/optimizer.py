"""
Intelligent Text Processor Optimizer Plugin

Combines OCR error correction, text validation, and smart dictionary lookup
for parallel OCR/translation processing.

Handles:
- OCR error correction (| → I, 0 → O, rn → m, etc.)
- Context-aware corrections
- Text validation
- Smart dictionary integration
- Parallel processing safety
"""

from typing import Dict, Any, List
import sys
from pathlib import Path

# Add app to path for imports
app_path = Path(__file__).parent.parent.parent.parent / "app"
if str(app_path) not in sys.path:
    sys.path.insert(0, str(app_path))

from app.ocr.intelligent_text_processor import IntelligentTextProcessor


class IntelligentTextProcessorOptimizer:
    """
    Intelligent text processor optimizer for parallel processing.
    
    Features:
    - OCR error correction
    - Context-aware processing
    - Text validation
    - Smart dictionary integration
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enable_corrections = config.get('enable_corrections', True)
        self.enable_context = config.get('enable_context', True)
        self.enable_validation = config.get('enable_validation', True)
        self.min_confidence = config.get('min_confidence', 0.2)
        self.min_word_length = config.get('min_word_length', 1)  # Default to 1 for CJK support
        self.auto_learn = config.get('auto_learn', True)
        
        # Store in config dict for later access
        self.config['min_word_length'] = self.min_word_length
        
        # Create processor (dict_engine will be set later)
        self.processor = IntelligentTextProcessor(
            dict_engine=None,
            enable_corrections=self.enable_corrections,
            enable_context=self.enable_context
        )
        
        # Statistics
        self.total_processed = 0
        self.total_corrected = 0
        self.total_validated = 0
        self.total_rejected = 0
        
        print(f"[INTELLIGENT_PROCESSOR] Initialized")
        print(f"  Corrections: {'enabled' if self.enable_corrections else 'disabled'}")
        print(f"  Context: {'enabled' if self.enable_context else 'disabled'}")
        print(f"  Validation: {'enabled' if self.enable_validation else 'disabled'}")
        print(f"  Min confidence: {self.min_confidence}")
        print(f"  Min word length: {self.min_word_length}")
    
    def set_dict_engine(self, dict_engine):
        """Set smart dictionary engine reference."""
        self.processor.dict_engine = dict_engine
        print(f"[INTELLIGENT_PROCESSOR] Smart dictionary connected")
    
    def configure(self, config: Dict[str, Any]):
        """Update configuration dynamically."""
        if 'min_confidence' in config:
            self.min_confidence = config['min_confidence']
            self.config['min_confidence'] = config['min_confidence']
        if 'min_word_length' in config:
            self.min_word_length = config['min_word_length']
            self.config['min_word_length'] = config['min_word_length']
        if 'enable_corrections' in config:
            self.enable_corrections = config['enable_corrections']
            self.processor.enable_corrections = config['enable_corrections']
        if 'enable_context' in config:
            self.enable_context = config['enable_context']
            self.processor.enable_context = config['enable_context']
        if 'enable_validation' in config:
            self.enable_validation = config['enable_validation']
        
        print(f"[INTELLIGENT_PROCESSOR] Configuration updated: min_conf={self.min_confidence}, min_word_len={self.min_word_length}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process: Apply intelligent text processing.
        
        Args:
            data: Pipeline data with 'texts' list
            
        Returns:
            Updated data with processed texts
        """
        texts = data.get('texts', [])
        
        if not texts:
            return data
        
        # Process batch with context awareness
        processed = self.processor.process_batch(texts, enable_merging=False)
        
        # Filter and update texts
        validated_texts = []
        corrections_applied = []
        
        for proc, text_dict in zip(processed, texts):
            self.total_processed += 1
            
            # Check if corrections were applied
            if proc.corrections:
                self.total_corrected += 1
                corrections_applied.append({
                    'original': proc.original,
                    'corrected': proc.corrected,
                    'corrections': proc.corrections
                })
            
            # Validate if enabled
            if self.enable_validation:
                # Check minimum word length (filter out short garbage like "3 Z", "Py")
                min_word_length = self.config.get('min_word_length', 2)
                text_length = len(proc.corrected.strip())
                
                # Check if text contains CJK characters (Japanese, Chinese, Korean)
                import re
                has_cjk = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]', proc.corrected))
                
                # Allow single-letter words if they're valid English words (I, A) OR if they're CJK characters
                is_valid_single_letter = text_length == 1 and (proc.corrected.strip().upper() in ['I', 'A'] or has_cjk)
                
                # If corrections were applied, be more lenient with confidence threshold AND validation
                min_conf_threshold = self.min_confidence
                is_valid_check = proc.is_valid
                
                if proc.corrections:
                    # Corrected text gets lower threshold (0.3 instead of 0.55)
                    min_conf_threshold = 0.3
                    # Also override is_valid if confidence is above the lower threshold
                    if proc.confidence >= 0.3:
                        is_valid_check = True
                
                if is_valid_check and proc.confidence >= min_conf_threshold and (text_length >= min_word_length or is_valid_single_letter):
                    # Keep text
                    updated = text_dict.copy()
                    updated['text'] = proc.corrected
                    updated['original_text'] = proc.original
                    updated['corrections'] = proc.corrections
                    updated['validation_confidence'] = proc.confidence
                    updated['validation_reason'] = proc.validation_reason
                    validated_texts.append(updated)
                    self.total_validated += 1
                else:
                    # Reject text
                    self.total_rejected += 1
                    reason = proc.validation_reason
                    if text_length < min_word_length:
                        reason = f"Too short ({text_length} < {min_word_length})"
                    print(f"[INTELLIGENT_PROCESSOR] Rejected: '{proc.original[:30]}...' "
                          f"(confidence={proc.confidence:.2f}, reason={reason})")
            else:
                # No validation, keep all texts with corrections
                updated = text_dict.copy()
                updated['text'] = proc.corrected
                updated['original_text'] = proc.original
                updated['corrections'] = proc.corrections
                validated_texts.append(updated)
                self.total_validated += 1
        
        # Update data
        data['texts'] = validated_texts
        data['corrections_applied'] = corrections_applied
        data['filtered_count'] = len(texts) - len(validated_texts)
        
        if corrections_applied:
            print(f"[INTELLIGENT_PROCESSOR] Applied {len(corrections_applied)} corrections")
        
        if self.enable_validation:
            print(f"[INTELLIGENT_PROCESSOR] Validated {len(validated_texts)}/{len(texts)} texts")
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
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
            'rejection_rate': f"{rejection_rate:.1f}%",
            'enable_corrections': self.enable_corrections,
            'enable_context': self.enable_context,
            'enable_validation': self.enable_validation
        }
    
    def reset(self):
        """Reset optimizer state."""
        self.total_processed = 0
        self.total_corrected = 0
        self.total_validated = 0
        self.total_rejected = 0
        self.processor.reset_stats()


# Plugin interface
def initialize(config: Dict[str, Any]) -> IntelligentTextProcessorOptimizer:
    """Initialize the optimizer plugin."""
    return IntelligentTextProcessorOptimizer(config)
