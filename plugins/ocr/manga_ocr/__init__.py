"""
MANGA_OCR Plugin

This plugin provides OCR functionality for Japanese manga using manga_ocr library.
"""

import logging
from typing import List, Optional
from pathlib import Path

try:
    from manga_ocr import MangaOcr
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False

# Import OCR interfaces
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions, OCREngineType, OCREngineStatus
from app.models import Frame, TextBlock, Rectangle


class OCREngine(IOCREngine):
    """MANGA_OCR engine implementation (Japanese only)."""
    
    def __init__(self, engine_name: str = "manga_ocr", engine_type=None):
        """Initialize MANGA_OCR engine."""
        if engine_type is None:
            engine_type = OCREngineType.MANGA_OCR
        super().__init__(engine_name, engine_type)
        
        self.mocr = None
        self.current_language = 'ja'  # Manga OCR is Japanese only
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: dict) -> bool:
        """Initialize the OCR engine."""
        try:
            if not ENGINE_AVAILABLE:
                self.logger.error("manga_ocr library not available")
                self.status = OCREngineStatus.ERROR
                return False
            
            self.status = OCREngineStatus.INITIALIZING
            
            self.logger.info("Initializing Manga OCR (Japanese only)")
            self.mocr = MangaOcr()
            
            self.status = OCREngineStatus.READY
            self.logger.info("Manga OCR initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Manga OCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False
    
    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> List[TextBlock]:
        """Extract text from frame using Manga OCR.
        
        Note: Manga OCR processes the entire image as one text block.
        It doesn't provide bounding boxes - designed for single text bubbles.
        """
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
            
            # Manga OCR processes entire image as one text block
            text = self.mocr(image)
            
            # Create single text block covering entire image
            text_blocks = []
            if text and text.strip():
                h, w = frame.data.shape[:2]
                position = Rectangle(x=0, y=0, width=w, height=h)
                text_block = TextBlock(
                    text=text.strip(),
                    position=position,
                    confidence=0.95,  # Manga OCR doesn't provide confidence
                    language='ja'
                )
                text_blocks.append(text_block)
            
            self.logger.info(f"Manga OCR extracted: '{text[:50]}...'")
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
        """Set the OCR language (Manga OCR only supports Japanese)."""
        if language != 'ja':
            self.logger.warning(f"Manga OCR only supports Japanese, ignoring language: {language}")
        return True
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ['ja']  # Japanese only
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.mocr = None
        self.status = OCREngineStatus.UNINITIALIZED
        self.logger.info("Manga OCR engine cleaned up")
