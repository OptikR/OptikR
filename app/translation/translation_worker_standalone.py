"""
Standalone Translation Worker

Minimal worker script that only loads transformers.
Run as a separate process to avoid PyQt6 conflicts.
"""

import sys
import os
import json

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

import warnings
warnings.filterwarnings('ignore')


def main():
    """Main worker loop."""
    try:
        # Get language pair from command line
        if len(sys.argv) < 3:
            print(json.dumps({'type': 'error', 'error': 'Missing language arguments'}), flush=True)
            return
        
        src_lang = sys.argv[1]
        tgt_lang = sys.argv[2]
        
        # Import transformers
        from transformers import MarianMTModel, MarianTokenizer
        
        # Load model with safetensors to avoid torch.load vulnerability
        model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        sys.stderr.write(f"[WORKER] Loading model: {model_name}\n")
        sys.stderr.flush()
        
        # Try to use safetensors if available
        try:
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(
                model_name,
                use_safetensors=True  # Use safetensors format (safer)
            )
        except Exception as e:
            # Fallback to regular loading if safetensors not available
            sys.stderr.write(f"[WORKER] Safetensors not available, using regular loading\n")
            sys.stderr.flush()
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
        
        sys.stderr.write(f"[WORKER] Model loaded!\n")
        sys.stderr.flush()
        
        # Signal ready
        print(json.dumps({'type': 'ready'}), flush=True)
        
        # Process requests from stdin
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line.strip())
                
                if request.get('type') == 'stop':
                    break
                
                if request.get('type') == 'translate':
                    text = request.get('text', '')
                    request_id = request.get('id', 0)
                    
                    if not text:
                        print(json.dumps({
                            'type': 'result',
                            'id': request_id,
                            'translated_text': '',
                            'confidence': 0.0
                        }), flush=True)
                        continue
                    
                    # Translate
                    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
                    translated = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
                    translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
                    
                    # Send response
                    print(json.dumps({
                        'type': 'result',
                        'id': request_id,
                        'translated_text': translated_text,
                        'confidence': 0.9
                    }), flush=True)
                    
            except Exception as e:
                print(json.dumps({
                    'type': 'error',
                    'error': str(e)
                }), flush=True)
        
    except Exception as e:
        error_msg = str(e)
        
        # Check for PyTorch version issue
        if 'torch.load' in error_msg or 'CVE-2025-32434' in error_msg or 'v2.6' in error_msg:
            error_msg = (
                "PyTorch upgrade required! Your PyTorch version has a security vulnerability.\n"
                "Please upgrade: pip install --upgrade torch torchvision torchaudio\n"
                "See PYTORCH_UPGRADE_REQUIRED.md for details."
            )
        
        print(json.dumps({
            'type': 'error',
            'error': f"Worker initialization failed: {error_msg}"
        }), flush=True)


if __name__ == '__main__':
    main()
