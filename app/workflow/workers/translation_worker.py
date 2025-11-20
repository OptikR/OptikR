"""
Translation Worker - Subprocess for text translation.

Runs in separate process, translates text and sends results back.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workflow.base.base_worker import BaseWorker

try:
    from transformers import MarianMTModel, MarianTokenizer
    MARIANMT_AVAILABLE = True
except ImportError:
    MARIANMT_AVAILABLE = False
    print("[TRANSLATION WORKER] Warning: transformers not available", file=sys.stderr)


class TranslationWorker(BaseWorker):
    """Worker for translation using MarianMT."""
    
    def initialize(self, config: dict) -> bool:
        """Initialize translation model."""
        try:
            if not MARIANMT_AVAILABLE:
                self.log("MarianMT not available")
                return False
            
            source_lang = config.get('source_language', 'en')
            target_lang = config.get('target_language', 'de')
            
            self.log(f"Initializing MarianMT: {source_lang} -> {target_lang}")
            
            # Determine model name
            model_name = f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}"
            
            # Load model and tokenizer
            self.log(f"Loading model: {model_name}")
            self.tokenizer = MarianTokenizer.from_pretrained(model_name)
            self.model = MarianMTModel.from_pretrained(model_name)
            
            self.log("MarianMT initialized successfully")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize translation: {e}")
            return False
    
    def process(self, data: dict) -> dict:
        """
        Translate text blocks.
        
        Args:
            data: {
                'text_blocks': [{'text': str, 'bbox': [...], 'confidence': float}],
                'source_language': str,
                'target_language': str
            }
            
        Returns:
            {
                'translations': [{'original_text': str, 'translated_text': str, 'bbox': [...]}],
                'count': int
            }
        """
        try:
            text_blocks = data.get('text_blocks', [])
            if not text_blocks:
                return {'translations': [], 'count': 0}
            
            # Extract texts
            texts = [block['text'] for block in text_blocks]
            
            # Translate in batch
            inputs = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
            translated = self.model.generate(**inputs)
            translated_texts = [self.tokenizer.decode(t, skip_special_tokens=True) for t in translated]
            
            # Create translation results
            translations = []
            for block, translated_text in zip(text_blocks, translated_texts):
                translations.append({
                    'original_text': block['text'],
                    'translated_text': translated_text,
                    'bbox': block['bbox'],
                    'confidence': block.get('confidence', 1.0)
                })
            
            return {
                'translations': translations,
                'count': len(translations)
            }
            
        except Exception as e:
            return {'error': f'Translation failed: {e}'}
    
    def cleanup(self):
        """Clean up translation resources."""
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'tokenizer'):
            del self.tokenizer
        self.log("Translation worker shutdown")


if __name__ == '__main__':
    worker = TranslationWorker(name="TranslationWorker")
    worker.run()
