"""
Capture Subprocess - Wrapper for screen capture worker.

Handles:
- Frame encoding/decoding (base64 + numpy)
- Region configuration
- Monitor selection
"""

import base64
import numpy as np
from typing import Any, Dict, Optional
from ..base.base_subprocess import BaseSubprocess


class CaptureSubprocess(BaseSubprocess):
    """Subprocess wrapper for capture stage."""
    
    def __init__(self, worker_script: str = "src/workflow/workers/capture_worker.py"):
        """
        Initialize capture subprocess.
        
        Args:
            worker_script: Path to capture worker script
        """
        super().__init__(name="Capture", worker_script=worker_script)
    
    def _prepare_message(self, data: Any) -> Dict:
        """
        Prepare capture request message.
        
        Args:
            data: Dictionary with 'region' key containing CaptureRegion
            
        Returns:
            Message dictionary for worker
        """
        region = data.get('region')
        
        if not region:
            raise ValueError("Capture data must include 'region'")
        
        # Extract region data
        if hasattr(region, 'rectangle'):
            # CaptureRegion object
            rect = region.rectangle
            message = {
                'region': {
                    'x': rect.x,
                    'y': rect.y,
                    'width': rect.width,
                    'height': rect.height,
                    'monitor_id': region.monitor_id if hasattr(region, 'monitor_id') else 0
                }
            }
            print(f"[{self.name}] Prepared region message: {message}")
        elif isinstance(region, dict):
            # Already a dictionary
            message = {'region': region}
            print(f"[{self.name}] Using dict region: {message}")
        else:
            raise ValueError(f"Invalid region type: {type(region)}")
        
        return message
    
    def _parse_result(self, result: Dict) -> Any:
        """
        Parse captured frame from worker.
        
        Args:
            result: Result message from worker {'type': 'result', 'data': {...}}
            
        Returns:
            Dictionary with 'frame' (base64 encoded) and 'shape'
        """
        # Extract data from result message
        data = result.get('data', {})
        
        # Check for error in data
        if 'error' in data:
            print(f"[{self.name}] Capture error: {data['error']}")
            return None
        
        # Check if frame exists
        if not data.get('frame'):
            print(f"[{self.name}] No frame in result data: {data}")
            return None
        
        # Return the frame data as-is (base64 encoded)
        # The OCR subprocess will decode it
        return {
            'frame': data.get('frame'),
            'shape': data.get('shape'),
            'dtype': data.get('dtype', 'uint8')
        }
