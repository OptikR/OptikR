"""
Tesseract - OCR engine using tesseract library

OCR plugin worker script.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workflow.base.base_worker import BaseWorker


class OCRWorker(BaseWorker):
    """Worker for Tesseract."""
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize OCR engine.
        
        Args:
            config: Configuration dictionary with 'language' key
            
        Returns:
            True if successful
        """
        try:
            import pytesseract
            
            self.language = config.get('language', 'eng')
            
            # Map common language codes to Tesseract format
            lang_map = {
                'en': 'eng',
                'ja': 'jpn',
                'ko': 'kor',
                'zh': 'chi_sim',
                'de': 'deu',
                'fr': 'fra',
                'es': 'spa'
            }
            self.tesseract_lang = lang_map.get(self.language, self.language)
            
            # Test if Tesseract is installed
            try:
                pytesseract.get_tesseract_version()
                self.log(f"Tesseract initialized for language: {self.tesseract_lang}")
                return True
            except Exception as e:
                self.log(f"Tesseract not found. Please install Tesseract OCR: {e}")
                return False
            
        except Exception as e:
            self.log(f"Failed to initialize: {e}")
            return False
    
    def process(self, data: dict) -> dict:
        """
        Perform OCR on frame.
        
        Args:
            data: {
                'frame': base64_string,
                'shape': [h, w, c],
                'dtype': 'uint8',
                'language': str
            }
            
        Returns:
            {
                'text_blocks': [
                    {'text': str, 'bbox': [x, y, w, h], 'confidence': float}
                ],
                'count': int
            }
        """
        try:
            import base64
            import numpy as np
            import pytesseract
            from PIL import Image
            
            # Decode frame
            frame_b64 = data.get('frame')
            if not frame_b64:
                self.log("ERROR: No frame provided")
                return {'error': 'No frame provided'}
            
            self.log(f"Decoding frame...")
            frame_bytes = base64.b64decode(frame_b64)
            shape = data.get('shape', [600, 800, 3])
            dtype = data.get('dtype', 'uint8')
            
            self.log(f"Frame: shape={shape}, dtype={dtype}, bytes={len(frame_bytes)}")
            
            frame = np.frombuffer(frame_bytes, dtype=dtype).reshape(shape)
            self.log(f"Frame decoded: {frame.shape}, min={frame.min()}, max={frame.max()}")
            
            # Convert to PIL Image
            if len(shape) == 3 and shape[2] == 3:
                # BGR to RGB
                frame_rgb = frame[:, :, ::-1]
                image = Image.fromarray(frame_rgb)
                self.log("Converted BGR to RGB")
            else:
                image = Image.fromarray(frame)
                self.log("Using grayscale image")
            
            # Perform OCR with detailed data
            self.log(f"Starting Tesseract OCR (lang={self.tesseract_lang})...")
            try:
                ocr_data = pytesseract.image_to_data(
                    image,
                    lang=self.tesseract_lang,
                    output_type=pytesseract.Output.DICT
                )
                self.log(f"Tesseract OCR complete: {len(ocr_data['text'])} boxes detected")
            except Exception as ocr_error:
                self.log(f"Tesseract error: {type(ocr_error).__name__}: {ocr_error}")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}")
                # Return empty results instead of failing
                return {
                    'text_blocks': [],
                    'count': 0
                }
            
            # Parse results into text blocks
            text_blocks = []
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                # Skip empty text or low confidence
                if not text or conf < 0:
                    continue
                
                # Get bounding box
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                text_blocks.append({
                    'text': text,
                    'bbox': [x, y, w, h],
                    'confidence': conf / 100.0  # Convert to 0-1 range
                })
            
            self.log(f"Parsed {len(text_blocks)} valid text blocks")
            
            return {
                'text_blocks': text_blocks,
                'count': len(text_blocks)
            }
            
        except Exception as e:
            import traceback
            error_msg = f'OCR failed: {e}\n{traceback.format_exc()}'
            self.log(error_msg)
            return {'error': error_msg}
    
    def cleanup(self):
        """Clean up resources."""
        self.log("Tesseract cleanup complete")


if __name__ == '__main__':
    worker = OCRWorker(name="tesseract")
    worker.run()
