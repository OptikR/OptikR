"""
Manga Ocr - OCR engine using manga_ocr library

OCR plugin worker script.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workflow.base.base_worker import BaseWorker


class OCRWorker(BaseWorker):
    """Worker for Manga Ocr."""
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize OCR engine.
        
        Args:
            config: Configuration dictionary with 'language' key
            
        Returns:
            True if successful
        """
        try:
            from manga_ocr import MangaOcr
            
            # Manga OCR is Japanese-only
            self.log("Initializing Manga OCR (Japanese only)...")
            self.mocr = MangaOcr()
            self.log("Manga OCR initialized successfully")
            return True
            
        except Exception as e:
            import traceback
            self.log(f"Failed to initialize Manga OCR: {e}\n{traceback.format_exc()}")
            return False
    
    def process(self, data: dict) -> dict:
        """
        Perform OCR on frame.
        
        Note: Manga OCR processes the entire image as one text block.
        It doesn't provide bounding boxes - designed for single text bubbles.
        
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
            from PIL import Image
            
            # Decode frame
            frame_b64 = data.get('frame')
            if not frame_b64:
                return {'error': 'No frame provided'}
            
            frame_bytes = base64.b64decode(frame_b64)
            shape = data.get('shape', [600, 800, 3])
            dtype = data.get('dtype', 'uint8')
            frame = np.frombuffer(frame_bytes, dtype=dtype).reshape(shape)
            
            # Convert to PIL Image (RGB)
            if len(shape) == 3 and shape[2] == 3:
                # BGR to RGB
                frame_rgb = frame[:, :, ::-1]
                image = Image.fromarray(frame_rgb)
            else:
                image = Image.fromarray(frame)
            
            # Manga OCR processes entire image as one text block
            text = self.mocr(image)
            
            # Create single text block covering entire image
            # Manga OCR doesn't provide bounding boxes
            text_blocks = []
            if text and text.strip():
                text_blocks.append({
                    'text': text.strip(),
                    'bbox': [0, 0, shape[1], shape[0]],  # Full image
                    'confidence': 0.95  # Manga OCR doesn't provide confidence
                })
            
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
        self.mocr = None
        self.log("Manga OCR cleanup complete")


if __name__ == '__main__':
    worker = OCRWorker(name="manga_ocr")
    worker.run()
