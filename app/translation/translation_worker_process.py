"""
Translation Worker Process

Runs MarianMT in a separate subprocess to avoid PyQt6/transformers conflicts.
The worker process stays alive and handles translation requests via stdin/stdout.
"""

import sys
import time
from typing import Optional


class TranslationWorkerProcess:
    """
    Manages a translation worker process.
    Provides simple interface for translation requests.
    """
    
    def __init__(self, src_lang: str, tgt_lang: str):
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.process: Optional[mp.Process] = None
        self.request_queue: Optional[mp.Queue] = None
        self.response_queue: Optional[mp.Queue] = None
        self.is_ready = False
        self.request_counter = 0
    
    def start(self, timeout: float = 30.0) -> bool:
        """
        Start the worker process and wait for it to be ready.
        Uses standalone script to avoid importing app modules.
        
        Args:
            timeout: Maximum time to wait for worker to be ready (seconds)
            
        Returns:
            True if worker started successfully
        """
        try:
            import subprocess
            from pathlib import Path
            
            # Get path to standalone worker script
            worker_script = Path(__file__).parent / "translation_worker_standalone.py"
            
            if not worker_script.exists():
                print(f"[TRANSLATION PROCESS] ✗ Worker script not found: {worker_script}")
                return False
            
            # Start worker as subprocess (not multiprocessing.Process)
            self.process = subprocess.Popen(
                [sys.executable, str(worker_script), self.src_lang, self.tgt_lang],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            print(f"[TRANSLATION PROCESS] Worker started (PID: {self.process.pid})")
            print(f"[TRANSLATION PROCESS] Loading model... (this takes 3-5 seconds)")
            
            # Wait for ready signal from stdout
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Read from stdout (non-blocking with timeout)
                    import select
                    
                    # Check if data available (Windows compatible)
                    line = self.process.stdout.readline()
                    if line:
                        try:
                            import json
                            response = json.loads(line.strip())
                            if response.get('type') == 'ready':
                                self.is_ready = True
                                print(f"[TRANSLATION PROCESS] ✓ Worker ready!")
                                return True
                            elif response.get('type') == 'error':
                                print(f"[TRANSLATION PROCESS] ✗ Worker error: {response.get('error')}")
                                return False
                        except json.JSONDecodeError:
                            # Not JSON, might be stderr output
                            pass
                    
                    # Check stderr for progress messages
                    if self.process.stderr:
                        import select
                        # Peek at stderr without blocking
                        try:
                            err_line = self.process.stderr.readline()
                            if err_line:
                                print(err_line.strip())
                        except:
                            pass
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"[TRANSLATION PROCESS] Error reading output: {e}")
                    time.sleep(0.1)
            
            print(f"[TRANSLATION PROCESS] ✗ Worker failed to start within {timeout}s")
            return False
            
        except Exception as e:
            print(f"[TRANSLATION PROCESS] ✗ Failed to start worker: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def translate(self, text: str, timeout: float = 10.0) -> Optional[str]:
        """
        Translate text using the worker process.
        
        Args:
            text: Text to translate
            timeout: Maximum time to wait for translation (seconds)
            
        Returns:
            Translated text or None if translation failed
        """
        if not self.is_ready or not self.process:
            print("[TRANSLATION PROCESS] Worker not ready")
            return None
        
        try:
            import json
            
            # Send request via stdin
            self.request_counter += 1
            request_id = self.request_counter
            
            request = json.dumps({
                'type': 'translate',
                'id': request_id,
                'text': text
            })
            
            self.process.stdin.write(request + '\n')
            self.process.stdin.flush()
            
            # Wait for response from stdout
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    line = self.process.stdout.readline()
                    if line:
                        response = json.loads(line.strip())
                        
                        if response.get('type') == 'result' and response.get('id') == request_id:
                            return response.get('translated_text')
                        elif response.get('type') == 'error':
                            print(f"[TRANSLATION PROCESS] Translation error: {response.get('error')}")
                            return None
                    
                    time.sleep(0.01)
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"[TRANSLATION PROCESS] Error reading response: {e}")
                    return None
            
            print(f"[TRANSLATION PROCESS] Translation timeout after {timeout}s")
            return None
            
        except Exception as e:
            print(f"[TRANSLATION PROCESS] Translation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def stop(self):
        """Stop the worker process."""
        if self.process and self.process.poll() is None:  # Process still running
            try:
                import json
                
                # Send stop signal via stdin
                stop_request = json.dumps({'type': 'stop'})
                self.process.stdin.write(stop_request + '\n')
                self.process.stdin.flush()
                
                # Wait for process to finish
                self.process.wait(timeout=2.0)
                
                print("[TRANSLATION PROCESS] Worker stopped")
                
            except Exception as e:
                # Force terminate if still alive
                try:
                    self.process.terminate()
                    self.process.wait(timeout=1.0)
                except:
                    self.process.kill()
                print(f"[TRANSLATION PROCESS] Worker terminated")
        
        self.is_ready = False
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


# Global worker instance (one per language pair)
_workers = {}


def get_translation_worker(src_lang: str, tgt_lang: str) -> TranslationWorkerProcess:
    """
    Get or create translation worker for language pair.
    
    Args:
        src_lang: Source language
        tgt_lang: Target language
        
    Returns:
        TranslationWorkerProcess instance
    """
    key = (src_lang, tgt_lang)
    
    if key not in _workers:
        worker = TranslationWorkerProcess(src_lang, tgt_lang)
        if worker.start():
            _workers[key] = worker
        else:
            return None
    
    return _workers.get(key)
