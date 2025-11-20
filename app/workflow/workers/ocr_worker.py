"""
OCR Worker - Subprocess for text recognition.

Runs in separate process, performs OCR and sends results back.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workflow.base.base_worker import BaseWorker

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[OCR WORKER] Warning: easyocr not available", file=sys.stderr)


class OCRWorker(BaseWorker):
    """Worker for OCR using EasyOCR."""
    
    def initialize(self, config: dict) -> bool:
        """Initialize OCR engine."""
        try:
            if not EASYOCR_AVAILABLE:
                self.log("EasyOCR not available")
                return False
            
            language = config.get('language', 'en')
            self.log(f"Initializing EasyOCR for language: {language}")
            
            # Initialize EasyOCR reader
            self.reader = easyocr.Reader([language], gpu=True)
            
            self.log("EasyOCR initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize OCR: {e}")
            return False
    
    def process(self, data: dict) -> dict:
        """
        Perform OCR on frame.
        
        Args:
            data: {'frame': base64_encoded_frame, 'language': str}
            
        Returns:
            {'text_blocks': [{'text': str, 'bbox': [x,y,w,h], 'confidence': float}], 'count': int}
        """
        try:
            # Decode frame
            import base64
            import numpy as np
            
            frame_b64 = data.get('frame')
            if not frame_b64:
                return {'error': 'No frame provided'}
            
            # Decode base64 to numpy array
            frame_bytes = base64.b64decode(frame_b64)
            shape = data.get('shape', [600, 800, 3])
            dtype = data.get('dtype', 'uint8')
            
            self.log(f"Decoding frame: shape={shape}, dtype={dtype}, bytes={len(frame_bytes)}")
            
            frame = np.frombuffer(frame_bytes, dtype=dtype).reshape(shape)
            
            self.log(f"Frame decoded: {frame.shape}, min={frame.min()}, max={frame.max()}")
            
            # Convert BGR to RGB if needed (DXCam captures in BGR)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                import cv2
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.log("Converted BGR to RGB")
            
            # Perform OCR with detailed error handling
            self.log("Starting OCR...")
            try:
                results = self.reader.readtext(frame)
                self.log(f"OCR complete: {len(results)} results")
            except Exception as ocr_error:
                self.log(f"EasyOCR error: {type(ocr_error).__name__}: {ocr_error}")
                import traceback
                self.log(f"Traceback: {traceback.format_exc()}")
                # Return empty results instead of failing
                return {
                    'text_blocks': [],
                    'count': 0
                }
            
            # Convert results to text blocks
            text_blocks = []
            for bbox, text, confidence in results:
                # Convert bbox to x,y,w,h format
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x = int(min(x_coords))
                y = int(min(y_coords))
                w = int(max(x_coords) - x)
                h = int(max(y_coords) - y)
                
                text_blocks.append({
                    'text': text,
                    'bbox': [x, y, w, h],
                    'confidence': float(confidence)
                })
            
            return {
                'text_blocks': text_blocks,
                'count': len(text_blocks)
            }
            
        except Exception as e:
            return {'error': f'OCR failed: {e}'}
    
    def cleanup(self):
        """Clean up OCR resources."""
        if hasattr(self, 'reader'):
            del self.reader
        self.log("OCR worker shutdown")


if __name__ == '__main__':
    worker = OCRWorker(name="OCRWorker")
    worker.run()
