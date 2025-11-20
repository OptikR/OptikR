"""
OCR Subprocess - Wrapper for OCR worker.

Handles:
- Frame encoding for OCR
- Language configuration
- Text block parsing
"""

import base64
import numpy as np
from typing import Any, Dict, Optional, List
from ..base.base_subprocess import BaseSubprocess


class OCRSubprocess(BaseSubprocess):
    """Subprocess wrapper for OCR stage."""
    
    def __init__(self, worker_script: str = "src/workflow/workers/ocr_worker.py"):
        """
        Initialize OCR subprocess.
        
        Args:
            worker_script: Path to OCR worker script
        """
        super().__init__(name="OCR", worker_script=worker_script)
    
    def _prepare_message(self, data: Any) -> Dict:
        """
        Prepare OCR request message.
        
        Args:
            data: Dictionary with 'frame' (base64 string or numpy array) and optional 'language'
            
        Returns:
            Message dictionary for worker
        """
        frame = data.get('frame')
        if frame is None:
            raise ValueError("OCR data must include 'frame'")
        
        # Frame is already base64 encoded from capture subprocess
        message = {
            'frame': frame,
            'shape': data.get('shape'),
            'dtype': data.get('dtype', 'uint8'),
            'language': data.get('language', 'en')
        }
        
        return message
    
    def _parse_result(self, result: Dict) -> Any:
        """
        Parse OCR results from worker.
        
        Args:
            result: Result message from worker {'type': 'result', 'data': {...}}
            
        Returns:
            Dictionary with 'text_blocks' list
        """
        # Extract data from result message
        data = result.get('data', {})
        
        # Check for error in data
        if 'error' in data:
            print(f"[{self.name}] OCR error: {data['error']}")
            return {'text_blocks': [], 'count': 0}
        
        try:
            # Parse text blocks
            text_blocks_data = data.get('text_blocks', [])
            text_blocks = []
            
            for block_data in text_blocks_data:
                # Create text block object
                text_block = type('TextBlock', (), {
                    'text': block_data.get('text', ''),
                    'bbox': block_data.get('bbox', [0, 0, 0, 0]),
                    'confidence': block_data.get('confidence', 0.0)
                })()
                
                text_blocks.append(text_block)
            
            return {
                'text_blocks': text_blocks,
                'count': len(text_blocks)
            }
            
        except Exception as e:
            print(f"[{self.name}] Error parsing OCR results: {e}")
            import traceback
            traceback.print_exc()
            return {'text_blocks': [], 'count': 0}
