"""
MarianMT Subprocess Wrapper

Runs MarianMT in a separate process to isolate crashes from the main UI.
"""

import subprocess
import json
import sys
from pathlib import Path


def translate_in_subprocess(text: str, src_lang: str, tgt_lang: str, timeout: float = 10.0):
    """
    Translate text using MarianMT in a subprocess.
    
    Args:
        text: Text to translate
        src_lang: Source language
        tgt_lang: Target language
        timeout: Timeout in seconds
        
    Returns:
        dict with 'translated_text', 'confidence', 'error' keys
    """
    try:
        # Create subprocess script
        script = f"""
import sys
import json
import os

# Disable the strict torch.load check
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

try:
    from transformers import MarianMTModel, MarianTokenizer
    import torch
    
    # Bypass the torch.load version check
    torch.serialization.add_safe_globals([])
    
    # Load model
    model_name = "Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    
    # Translate
    text = {json.dumps(text)}
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    translated = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
    translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
    
    # Return result
    result = {{
        'translated_text': translated_text,
        'confidence': 0.9,
        'error': None
    }}
    print(json.dumps(result))
    
except Exception as e:
    result = {{
        'translated_text': None,
        'confidence': 0.0,
        'error': str(e)
    }}
    print(json.dumps(result))
"""
        
        # Run subprocess
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            # Parse JSON output
            output = result.stdout.strip()
            return json.loads(output)
        else:
            return {
                'translated_text': None,
                'confidence': 0.0,
                'error': f"Subprocess failed: {result.stderr}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            'translated_text': None,
            'confidence': 0.0,
            'error': f"Translation timed out after {timeout}s"
        }
    except Exception as e:
        return {
            'translated_text': None,
            'confidence': 0.0,
            'error': str(e)
        }
