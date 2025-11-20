"""
PADDLEOCR Plugin - Auto-generated

This plugin provides OCR functionality using paddleocr library.
"""

import logging
from typing import List, Optional
from pathlib import Path

try:
    import paddleocr
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False

# Import OCR interfaces
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions, OCREngineType, OCREngineStatus
from app.models import Frame, TextBlock, Rectangle


class OCREngine(IOCREngine):
    """PADDLEOCR engine implementation."""
    
    def __init__(self, engine_name: str = "paddleocr", engine_type=None):
        """Initialize PADDLEOCR engine."""
        if engine_type is None:
            engine_type = OCREngineType.PADDLEOCR
        super().__init__(engine_name, engine_type)
        
        self.engine = None
        self.current_language = 'en'
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: dict) -> bool:
        """Initialize the OCR engine."""
        try:
            if not ENGINE_AVAILABLE:
                self.logger.error("paddleocr library not available")
                self.status = OCREngineStatus.ERROR
                return False
            
            from paddleocr import PaddleOCR
            import os
            
            self.status = OCREngineStatus.INITIALIZING
            self.current_language = config.get('language', 'en')
            use_gpu = config.get('gpu', True)
            
            # Suppress PaddleOCR verbose logging
            os.environ['GLOG_minloglevel'] = '3'
            os.environ['FLAGS_pir_apply_shape_optimization_pass'] = '0'
            
            # Map language codes
            lang_map = {
                'en': 'en',
                'ja': 'japan',
                'ko': 'korean',
                'zh': 'ch',
                'de': 'german',
                'fr': 'french',
                'es': 'spanish'
            }
            paddle_lang = lang_map.get(self.current_language, 'en')
            
            self.logger.info(f"Initializing PaddleOCR (lang={paddle_lang}, gpu={use_gpu})")
            
            # Initialize PaddleOCR
            try:
                # Try with show_log parameter (newer versions)
                self.engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=paddle_lang,
                    use_gpu=use_gpu,
                    show_log=False
                )
            except TypeError:
                # Fallback without show_log parameter (older versions)
                self.engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=paddle_lang,
                    use_gpu=use_gpu
                )
            
            self.status = OCREngineStatus.READY
            self.logger.info("PaddleOCR initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PaddleOCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False
    
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """Extract text from frame using PaddleOCR."""
        if not self.is_ready():
            return []
        
        try:
            import numpy as np
            
            # Convert frame to numpy array if needed
            if isinstance(frame.data, np.ndarray):
                image = frame.data
                # Convert BGR to RGB
                if len(image.shape) == 3 and image.shape[2] == 3:
                    image = image[:, :, ::-1]
            else:
                self.logger.error("Frame data is not a numpy array")
                return []
            
            # Perform OCR
            results = self.engine.ocr(image, cls=True)
            
            # Parse results into TextBlock objects
            text_blocks = []
            
            if results and results[0]:
                for line in results[0]:
                    # Each line: [bbox_points, (text, confidence)]
                    bbox_points, (text, confidence) = line
                    
                    # Convert bbox points to Rectangle
                    xs = [p[0] for p in bbox_points]
                    ys = [p[1] for p in bbox_points]
                    
                    x = int(min(xs))
                    y = int(min(ys))
                    w = int(max(xs) - x)
                    h = int(max(ys) - y)
                    
                    # Create TextBlock
                    position = Rectangle(x=x, y=y, width=w, height=h)
                    text_block = TextBlock(
                        text=text,
                        position=position,
                        confidence=float(confidence),
                        language=self.current_language
                    )
                    text_blocks.append(text_block)
            
            self.logger.info(f"PaddleOCR extracted {len(text_blocks)} text blocks")
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
        self.logger.info("paddleocr engine cleaned up")
