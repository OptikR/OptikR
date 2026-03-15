"""
EasyOCR Plugin - Main Entry Point

This plugin provides OCR functionality using EasyOCR library.
"""

import logging
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
            
            self.logger.info(f"Initializing EasyOCR (language={self.current_language}, gpu={use_gpu})")
            
            # Initialize EasyOCR reader
            self.reader = easyocr.Reader([self.current_language], gpu=use_gpu)
            
            self.capabilities.has_text_detection = True
            self.status = OCREngineStatus.READY
            self.logger.info("EasyOCR initialized successfully")
            return True
            
        except Exception as e:
            from app.ocr.ocr_engine_interface import OCREngineStatus
            self.logger.error(f"Failed to initialize EasyOCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False
    
    # Max pixel dimension before downscaling (keeps OCR under ~1 s on GPU)
    _MAX_DIMENSION = 1280

    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> list[TextBlock]:
        """Extract text from frame (required by IOCREngine)."""
        if not self.is_ready():
            return []
        
        try:
            import cv2
            import numpy as np

            image = frame.data
            h, w = image.shape[:2]
            scale = 1.0

            # Downscale large frames to stay within _MAX_DIMENSION
            if max(h, w) > self._MAX_DIMENSION:
                scale = self._MAX_DIMENSION / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

            results = self.reader.readtext(image, paragraph=True)
            
            # Convert to TextBlock objects
            text_blocks = []
            min_confidence = options.confidence_threshold if options else 0.5
            inv_scale = 1.0 / scale

            for entry in results:
                # paragraph=True can return (bbox, text) without confidence
                if len(entry) == 3:
                    bbox, text, confidence = entry
                elif len(entry) == 2:
                    bbox, text = entry
                    confidence = 1.0
                else:
                    continue

                if confidence < min_confidence:
                    continue

                if not text or not text.strip():
                    continue

                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]

                # Map coordinates back to original resolution
                x = int(min(x_coords) * inv_scale)
                y = int(min(y_coords) * inv_scale)
                width = int((max(x_coords) - min(x_coords)) * inv_scale)
                height = int((max(y_coords) - min(y_coords)) * inv_scale)

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
    
    def extract_text_batch(self, frames: list[Frame], options: OCRProcessingOptions) -> list[list[TextBlock]]:
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
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages (required by IOCREngine)."""
        # EasyOCR supports 80+ languages
        return ['en', 'ja', 'ko', 'zh_sim', 'zh_tra', 'de', 'fr', 'es', 'ru', 'ar', 'hi', 'th', 'vi']
    
    def cleanup(self) -> None:
        """Clean up resources and release GPU memory."""
        from app.ocr.ocr_engine_interface import OCREngineStatus
        self.reader = None
        self.status = OCREngineStatus.UNINITIALIZED

        from app.utils.pytorch_manager import release_gpu_memory
        release_gpu_memory()

        self.logger.info("EasyOCR engine cleaned up")
