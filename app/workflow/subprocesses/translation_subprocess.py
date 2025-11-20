"""
Translation Subprocess - Wrapper for translation worker.

Handles:
- Text encoding
- Language pair configuration
- Translation result parsing
"""

from typing import Any, Dict, Optional, List
from ..base.base_subprocess import BaseSubprocess


class TranslationSubprocess(BaseSubprocess):
    """Subprocess wrapper for translation stage."""
    
    def __init__(self, worker_script: str = "src/workflow/workers/translation_worker.py"):
        """
        Initialize translation subprocess.
        
        Args:
            worker_script: Path to translation worker script
        """
        super().__init__(name="Translation", worker_script=worker_script)
    
    def _prepare_message(self, data: Any) -> Dict:
        """
        Prepare translation request message.
        
        Args:
            data: Dictionary with 'text_blocks', 'source_language', 'target_language'
            
        Returns:
            Message dictionary for worker
        """
        text_blocks = data.get('text_blocks', [])
        if not text_blocks:
            raise ValueError("Translation data must include 'text_blocks'")
        
        # Convert text blocks to simple dicts for JSON serialization
        blocks_data = []
        for block in text_blocks:
            block_dict = {
                'text': block.text if hasattr(block, 'text') else str(block),
                'bbox': block.bbox if hasattr(block, 'bbox') else [0, 0, 100, 50],
                'confidence': block.confidence if hasattr(block, 'confidence') else 1.0
            }
            blocks_data.append(block_dict)
        
        message = {
            'text_blocks': blocks_data,
            'source_language': data.get('source_language', 'en'),
            'target_language': data.get('target_language', 'de')
        }
        
        return message
    
    def _parse_result(self, result: Dict) -> Any:
        """
        Parse translation results from worker.
        
        Args:
            result: Result message from worker {'type': 'result', 'data': {...}}
            
        Returns:
            Dictionary with 'translations' list
        """
        # Extract data from result message
        data = result.get('data', {})
        
        # Check for error in data
        if 'error' in data:
            print(f"[{self.name}] Translation error: {data['error']}")
            return {'translations': [], 'count': 0}
        
        try:
            # Parse translations
            translations_data = data.get('translations', [])
            translations = []
            
            for trans_data in translations_data:
                # Create translation object
                translation = type('Translation', (), {
                    'original_text': trans_data.get('original_text', ''),
                    'translated_text': trans_data.get('translated_text', ''),
                    'bbox': trans_data.get('bbox', [0, 0, 100, 50]),
                    'confidence': trans_data.get('confidence', 0.0)
                })()
                
                translations.append(translation)
            
            return {
                'translations': translations,
                'count': len(translations)
            }
            
        except Exception as e:
            print(f"[{self.name}] Error parsing translation results: {e}")
            import traceback
            traceback.print_exc()
            return {'translations': [], 'count': 0}
