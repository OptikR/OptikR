"""
TESSERACT Plugin - Auto-generated

This plugin provides OCR functionality using tesseract library.
"""

import logging
from typing import List, Optional
from pathlib import Path

try:
    import pytesseract
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False

# Import OCR interfaces
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions, OCREngineType, OCREngineStatus
from app.models import Frame, TextBlock, Rectangle


class OCREngine(IOCREngine):
    """TESSERACT engine implementation."""
    
    def __init__(self, engine_name: str = "tesseract", engine_type=None):
        """Initialize TESSERACT engine."""
        if engine_type is None:
            engine_type = OCREngineType.TESSERACT
        super().__init__(engine_name, engine_type)
        
        self.engine = None
        self.current_language = 'en'
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: dict) -> bool:
        """Initialize the OCR engine."""
        try:
            if not ENGINE_AVAILABLE:
                self.logger.error("tesseract library not available")
                self.status = OCREngineStatus.ERROR
                return False
            
            self.status = OCREngineStatus.INITIALIZING
            self.current_language = config.get('language', 'en')
            
            self.logger.info(f"Initializing tesseract (language={self.current_language})")
            
            self.status = OCREngineStatus.READY
            self.logger.info("tesseract initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize tesseract: {e}")
            self.status = OCREngineStatus.ERROR
            return False
    
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """Extract text from frame using Tesseract."""
        if not self.is_ready():
            return []
        
        try:
            from PIL import Image
            import numpy as np
            
            # Convert frame to PIL Image
            if isinstance(frame.data, np.ndarray):
                # Convert BGR to RGB if needed
                if len(frame.data.shape) == 3 and frame.data.shape[2] == 3:
                    image_rgb = frame.data[:, :, ::-1]
                    image = Image.fromarray(image_rgb)
                else:
                    image = Image.fromarray(frame.data)
            else:
                self.logger.error("Frame data is not a numpy array")
                return []
            
            # Map language codes
            lang_map = {
                'en': 'eng',
                'ja': 'jpn',
                'ko': 'kor',
                'zh': 'chi_sim',
                'de': 'deu',
                'fr': 'fra',
                'es': 'spa'
            }
            tesseract_lang = lang_map.get(self.current_language, self.current_language)
            
            # Perform OCR with configuration for better text grouping
            # PSM 6 = Assume a single uniform block of text (good for manga bubbles)
            # PSM 11 = Sparse text. Find as much text as possible in no particular order
            custom_config = r'--psm 6 --oem 3'  # PSM 6 for block text, OEM 3 for best accuracy
            
            ocr_data = pytesseract.image_to_data(
                image,
                lang=tesseract_lang,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Parse results and group by lines
            # Tesseract provides line-level grouping via 'line_num'
            lines = {}
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                # Skip empty text or low confidence
                if not text or conf < 0:
                    continue
                
                # Group by line number
                line_num = ocr_data['line_num'][i]
                if line_num not in lines:
                    lines[line_num] = []
                
                lines[line_num].append({
                    'text': text,
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'conf': conf
                })
            
            # Merge words in each line into text blocks
            text_blocks = []
            for line_num, words in lines.items():
                if not words:
                    continue
                
                # Combine all words in the line
                combined_text = ' '.join(w['text'] for w in words)
                
                # Calculate bounding box for entire line
                min_x = min(w['left'] for w in words)
                min_y = min(w['top'] for w in words)
                max_x = max(w['left'] + w['width'] for w in words)
                max_y = max(w['top'] + w['height'] for w in words)
                
                # Average confidence
                avg_conf = sum(w['conf'] for w in words) / len(words)
                
                # Create TextBlock for the line
                position = Rectangle(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)
                text_block = TextBlock(
                    text=combined_text,
                    position=position,
                    confidence=avg_conf / 100.0,  # Convert to 0-1 range
                    language=self.current_language
                )
                text_blocks.append(text_block)
            
            self.logger.info(f"Tesseract extracted {len(text_blocks)} text blocks")
            return text_blocks
            
        except Exception as e:
            self.logger.error(f"OCR processing failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def extract_text_batch(self, frames: List[Frame], options: OCRProcessingOptions) -> List[List[TextBlock]]:
        """Extract text from multiple frames."""
        results = []
        for frame in frames:
            results.append(self.extract_text(frame, options))
        return results
    
    def set_language(self, language: str) -> bool:
        """Set the OCR language."""
        try:
            self.current_language = language
            return True
        except Exception as e:
            self.logger.error(f"Failed to set language: {e}")
            return False
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ['en', 'ja', 'ko', 'zh', 'de', 'fr', 'es']
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.engine = None
        self.status = OCREngineStatus.UNINITIALIZED
        self.logger.info("tesseract engine cleaned up")
