"""
EasyOCR Plugin - Main Entry Point

This plugin provides OCR functionality using EasyOCR library.
"""

import logging
from typing import List, Optional
from pathlib import Path

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Import OCR interfaces
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions
from app.models import Frame, TextBlock, Rectangle


class OCREngine(IOCREngine):
    """EasyOCR engine implementation."""
    
    def __init__(self, engine_name: str = "easyocr_gpu", engine_type=None):
        """Initialize EasyOCR engine."""
        from app.ocr.ocr_engine_interface import OCREngineType, OCREngineStatus
        
        # Call parent constructor
        if engine_type is None:
            engine_type = OCREngineType.EASYOCR
        super().__init__(engine_name, engine_type)
        
        self.reader = None
        self.current_language = 'en'
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: dict) -> bool:
        """Initialize the OCR engine."""
        try:
            from app.ocr.ocr_engine_interface import OCREngineStatus
            
            if not EASYOCR_AVAILABLE:
                self.logger.error("EasyOCR library not available")
                self.status = OCREngineStatus.ERROR
                return False
            
            self.status = OCREngineStatus.INITIALIZING
            
            self.current_language = config.get('language', 'en')
            use_gpu = config.get('gpu', True)
            
            # Get all languages from config (for multi-language support)
            languages = config.get('languages', [self.current_language])
            if isinstance(languages, str):
                languages = [languages]
            
            # Map language codes to EasyOCR format
            lang_mapping = {
                'zh-CN': 'zh_sim',  # Simplified Chinese
                'zh-TW': 'zh_tra',  # Traditional Chinese
                'zh': 'zh_sim'      # Default Chinese to simplified
            }
            languages = [lang_mapping.get(lang, lang) for lang in languages]
            
            # For Japanese, always include English too (manga often has mixed text)
            if 'ja' in languages and 'en' not in languages:
                languages.append('en')
            
            # Remove duplicates
            languages = list(dict.fromkeys(languages))
            
            # EasyOCR restriction: Japanese only works with English
            if 'ja' in languages:
                languages = ['ja', 'en']
                self.logger.info("Japanese detected - limiting to ja+en (EasyOCR requirement)")
            else:
                # Limit to 3 languages for performance
                languages = languages[:3]
            
            self.logger.info(f"Initializing EasyOCR (languages={languages}, gpu={use_gpu})")
            
            # Initialize EasyOCR reader with all languages
            self.reader = easyocr.Reader(languages, gpu=use_gpu)
            
            self.status = OCREngineStatus.READY
            self.logger.info("EasyOCR initialized successfully")
            return True
            
        except Exception as e:
            from app.ocr.ocr_engine_interface import OCREngineStatus
            self.logger.error(f"Failed to initialize EasyOCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False
    
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """Extract text from frame (required by IOCREngine)."""
        if not self.is_ready():
            return []
        
        try:
            # Perform OCR
            results = self.reader.readtext(frame.data)
            
            # Convert to TextBlock objects
            text_blocks = []
            for bbox, text, confidence in results:
                # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                
                x = int(min(x_coords))
                y = int(min(y_coords))
                width = int(max(x_coords) - min(x_coords))
                height = int(max(y_coords) - min(y_coords))
                
                # Apply confidence threshold
                min_confidence = options.confidence_threshold if options else 0.5
                
                if confidence >= min_confidence:
                    text_block = TextBlock(
                        text=text,
                        position=Rectangle(x, y, width, height),
                        confidence=confidence,
                        language=options.language if options else self.current_language
                    )
                    text_blocks.append(text_block)
            
            return text_blocks
            
        except Exception as e:
            self.logger.error(f"OCR processing failed: {e}")
            return []
    
    def extract_text_batch(self, frames: List[Frame], options: OCRProcessingOptions) -> List[List[TextBlock]]:
        """Extract text from multiple frames (required by IOCREngine)."""
        results = []
        for frame in frames:
            results.append(self.extract_text(frame, options))
        return results
    
    def set_language(self, language: str) -> bool:
        """Set the OCR language (required by IOCREngine)."""
        try:
            if language != self.current_language:
                self.logger.info(f"Changing language from {self.current_language} to {language}")
                # Reinitialize reader with new language
                use_gpu = self.reader.gpu if hasattr(self.reader, 'gpu') else True
                self.reader = easyocr.Reader([language], gpu=use_gpu)
                self.current_language = language
            return True
        except Exception as e:
            self.logger.error(f"Failed to set language: {e}")
            return False
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages (required by IOCREngine)."""
        # EasyOCR supports 80+ languages
        return ['en', 'ja', 'ko', 'zh_sim', 'zh_tra', 'de', 'fr', 'es', 'ru', 'ar', 'hi', 'th', 'vi']
    
    def cleanup(self) -> None:
        """Clean up resources."""
        from app.ocr.ocr_engine_interface import OCREngineStatus
        self.reader = None
        self.status = OCREngineStatus.UNINITIALIZED
        self.logger.info("EasyOCR engine cleaned up")
