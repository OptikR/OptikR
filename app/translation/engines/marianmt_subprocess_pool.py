"""
MarianMT Subprocess Pool

Maintains a persistent subprocess for translations to avoid repeated model loading.
"""

import subprocess
import json
import sys
import threading
import queue
from pathlib import Path
from typing import Optional, Dict, Any


class MarianMTSubprocessPool:
    """
    Persistent subprocess pool for MarianMT translations.
    
    Keeps subprocess alive to avoid repeated model loading.
    """
    
    def __init__(self, src_lang: str, tgt_lang: str, max_workers: int = 1):
        """
        Initialize subprocess pool.
        
        Args:
            src_lang: Source language
            tgt_lang: Target language
            max_workers: Number of worker processes (default 1 for now)
        """
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.max_workers = max_workers
        
        self.process: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()
        self.is_running = False
        
    def start(self):
        """Start the persistent subprocess."""
        if self.is_running:
            return
        
        with self.lock:
            if self.is_running:
                return
            
            # Create worker script
            worker_script = f"""
import sys
import json
from transformers import MarianMTModel, MarianTokenizer

# Load model once at startup
model_name = "Helsinki-NLP/opus-mt-{self.src_lang}-{self.tgt_lang}"
print(f"[WORKER] Loading model: {{model_name}}", file=sys.stderr, flush=True)
tokenizer = MarianTokenizer.from_pretrained(model_name)
model = MarianMTModel.from_pretrained(model_name)
print("[WORKER] Model loaded, ready for translations", file=sys.stderr, flush=True)

# Process translations in loop
while True:
    try:
        # Read input line
        line = sys.stdin.readline()
        if not line:
            break
        
        # Parse request
        request = json.loads(line.strip())
        text = request['text']
        
        # Translate
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        translated = model.generate(**inputs)
        translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
        
        # Send response
        response = {{
            'translated_text': translated_text,
            'confidence': 0.9,
            'error': None
        }}
        print(json.dumps(response), flush=True)
        
    except Exception as e:
        response = {{
            'translated_text': None,
            'confidence': 0.0,
            'error': str(e)
        }}
        print(json.dumps(response), flush=True)
"""
            
            # Start subprocess
            self.process = subprocess.Popen(
                [sys.executable, '-c', worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr to stdout so we see errors
                text=True,
                bufsize=1  # Line buffered
            )
            
            self.is_running = True
            print(f"[SUBPROCESS POOL] Started worker process (PID: {self.process.pid})")
            print(f"[SUBPROCESS POOL] Loading model... (this may take 20-30 seconds on first run)")
            
            # Read initial output to confirm model loaded
            import threading
            def read_startup():
                try:
                    for i in range(10):  # Wait up to 10 lines of output
                        line = self.process.stdout.readline()
                        if line:
                            print(f"[WORKER] {line.strip()}")
                            if "ready for translations" in line.lower():
                                break
                except:
                    pass
            
            # Start reader thread
            reader = threading.Thread(target=read_startup, daemon=True)
            reader.start()
    
    def translate(self, text: str, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Translate text using the persistent subprocess.
        
        Args:
            text: Text to translate
            timeout: Timeout in seconds
            
        Returns:
            dict with 'translated_text', 'confidence', 'error' keys
        """
        if not self.is_running:
            self.start()
        
        try:
            with self.lock:
                # Send request
                request = {'text': text}
                self.process.stdin.write(json.dumps(request) + '\\n')
                self.process.stdin.flush()
                
                # Read response with timeout
                import select
                import time
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    # Check if data is available (non-blocking)
                    response_line = self.process.stdout.readline()
                    if response_line:
                        response = json.loads(response_line.strip())
                        return response
                    time.sleep(0.1)
                
                # Timeout
                raise Exception(f"Translation timed out after {timeout}s")
                
        except Exception as e:
            # Restart subprocess on error
            self.stop()
            return {
                'translated_text': None,
                'confidence': 0.0,
                'error': f"Subprocess error: {str(e)}"
            }
    
    def stop(self):
        """Stop the subprocess."""
        with self.lock:
            if self.process:
                try:
                    self.process.stdin.close()
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    self.process.kill()
                finally:
                    self.process = None
            
            self.is_running = False
            print("[SUBPROCESS POOL] Worker process stopped")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


# Global pool instance (one per language pair)
_pools: Dict[tuple, MarianMTSubprocessPool] = {}
_pools_lock = threading.Lock()


def get_subprocess_pool(src_lang: str, tgt_lang: str) -> MarianMTSubprocessPool:
    """
    Get or create subprocess pool for language pair.
    
    Args:
        src_lang: Source language
        tgt_lang: Target language
        
    Returns:
        MarianMTSubprocessPool instance
    """
    key = (src_lang, tgt_lang)
    
    with _pools_lock:
        if key not in _pools:
            _pools[key] = MarianMTSubprocessPool(src_lang, tgt_lang)
            _pools[key].start()
        
        return _pools[key]


def translate_with_pool(text: str, src_lang: str, tgt_lang: str, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Translate text using subprocess pool (reuses process).
    
    Args:
        text: Text to translate
        src_lang: Source language
        tgt_lang: Target language
        timeout: Timeout in seconds
        
    Returns:
        dict with 'translated_text', 'confidence', 'error' keys
    """
    pool = get_subprocess_pool(src_lang, tgt_lang)
    return pool.translate(text, timeout)
