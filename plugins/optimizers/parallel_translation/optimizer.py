"""
Parallel Translation Optimizer Plugin
Translates multiple text blocks simultaneously using worker threads

Features:
- Warm start: Pre-loads translation models to avoid threading issues
- Automatic fallback: Falls back to sequential if parallel processing fails
- Thread-safe: Handles shutdown gracefully
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
import threading


class ParallelTranslationOptimizer:
    """Translates multiple text blocks in parallel using worker threads"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.worker_threads = config.get('worker_threads', 4)
        self.batch_size = config.get('batch_size', 16)
        self.timeout = config.get('timeout_seconds', 15.0)
        self.enable_warm_start = config.get('enable_warm_start', True)
        self.fallback_on_error = config.get('fallback_on_error', True)
        
        # Check global runtime mode from config_manager
        runtime_mode = config.get('runtime_mode', 'auto')
        plugin_use_gpu = config.get('use_gpu', True)
        
        # Force CPU if runtime mode is 'cpu'
        if runtime_mode == 'cpu':
            self.use_gpu = False
            print(f"[PARALLEL_TRANSLATION] Runtime mode is CPU - GPU disabled")
        else:
            self.use_gpu = plugin_use_gpu
        
        # Thread pool
        self.executor = ThreadPoolExecutor(
            max_workers=self.worker_threads,
            thread_name_prefix="translation_worker"
        )
        self.is_shutdown = False
        self.warm_started = False
        self.fallback_mode = False
        
        # Statistics
        self.total_texts = 0
        self.parallel_operations = 0
        self.total_time_saved = 0.0
        self.fallback_count = 0
        self.warm_start_attempts = 0
        self.lock = threading.Lock()
        
        print(f"[PARALLEL_TRANSLATION] Initialized with {self.worker_threads} workers "
              f"(Runtime: {runtime_mode}, GPU: {'enabled' if self.use_gpu else 'disabled'}, "
              f"warm_start: {'enabled' if self.enable_warm_start else 'disabled'}, "
              f"fallback: {'enabled' if self.fallback_on_error else 'disabled'})")
    
    def _translate_single_text(self, text_data: Dict[str, Any], translate_func) -> Dict[str, Any]:
        """Translate a single text block"""
        try:
            start_time = time.time()
            
            # Extract text info
            text_id = text_data.get('id', 0)
            source_text = text_data.get('text', '')
            source_lang = text_data.get('source_lang', 'auto')
            target_lang = text_data.get('target_lang', 'en')
            
            # Skip empty text
            if not source_text or not source_text.strip():
                return {
                    'text_id': text_id,
                    'source_text': source_text,
                    'translated_text': '',
                    'success': True,
                    'translation_time': 0.0,
                    'skipped': True
                }
            
            # Perform translation using provided translation function
            if translate_func:
                result = translate_func(source_text, source_lang, target_lang)
            else:
                result = {'translated_text': source_text, 'confidence': 0.0}
            
            elapsed = time.time() - start_time
            
            return {
                'text_id': text_id,
                'source_text': source_text,
                'translated_text': result.get('translated_text', source_text),
                'confidence': result.get('confidence', 1.0),
                'success': True,
                'translation_time': elapsed
            }
            
        except Exception as e:
            print(f"[PARALLEL_TRANSLATION] Error translating text {text_data.get('id')}: {e}")
            return {
                'text_id': text_data.get('id', 0),
                'source_text': text_data.get('text', ''),
                'translated_text': text_data.get('text', ''),  # Fallback to source
                'confidence': 0.0,
                'success': False,
                'error': str(e)
            }
    
    def warm_start(self, source_lang: str, target_lang: str, translate_func) -> bool:
        """
        Warm start: Pre-load translation models in worker threads.
        This helps avoid threading issues with model loading.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            translate_func: Translation function to warm up
            
        Returns:
            True if warm start successful, False otherwise
        """
        if not self.enable_warm_start or self.warm_started:
            return True
        
        with self.lock:
            self.warm_start_attempts += 1
        
        try:
            print(f"[PARALLEL_TRANSLATION] Warm starting {self.worker_threads} workers...")
            
            # Submit dummy translation to each worker to pre-load models
            dummy_text = "test"
            futures = []
            
            for i in range(self.worker_threads):
                try:
                    future = self.executor.submit(
                        self._warm_start_worker,
                        dummy_text,
                        source_lang,
                        target_lang,
                        translate_func,
                        i
                    )
                    futures.append(future)
                except Exception as e:
                    print(f"[PARALLEL_TRANSLATION] Failed to submit warm start task {i}: {e}")
                    return False
            
            # Wait for all workers to complete warm start
            success_count = 0
            # Get timeout from config
            model_timeout = 30.0
            if hasattr(self, 'config_manager') and self.config_manager:
                model_timeout = self.config_manager.get_setting('timeouts.model_loading', 30.0)
            
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=model_timeout)
                    if result:
                        success_count += 1
                except Exception as e:
                    print(f"[PARALLEL_TRANSLATION] Worker {i} warm start failed: {e}")
            
            if success_count == self.worker_threads:
                self.warm_started = True
                print(f"[PARALLEL_TRANSLATION] ✓ Warm start complete ({success_count}/{self.worker_threads} workers ready)")
                return True
            else:
                print(f"[PARALLEL_TRANSLATION] ⚠ Partial warm start ({success_count}/{self.worker_threads} workers ready)")
                # Still mark as warm started if at least one worker succeeded
                if success_count > 0:
                    self.warm_started = True
                    return True
                return False
                
        except Exception as e:
            print(f"[PARALLEL_TRANSLATION] Warm start failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _warm_start_worker(self, text: str, source_lang: str, target_lang: str, 
                          translate_func, worker_id: int) -> bool:
        """Warm start a single worker by performing a dummy translation."""
        try:
            print(f"[PARALLEL_TRANSLATION] Worker {worker_id} warming up...")
            result = translate_func(text, source_lang, target_lang)
            if result and result.get('translated_text'):
                print(f"[PARALLEL_TRANSLATION] Worker {worker_id} ready")
                return True
            return False
        except Exception as e:
            print(f"[PARALLEL_TRANSLATION] Worker {worker_id} warm start error: {e}")
            return False
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process: Translate multiple text blocks in parallel with fallback"""
        # Check if shutdown
        if self.is_shutdown:
            return data
        
        # Check if in fallback mode (skip parallel processing)
        if self.fallback_mode:
            return data
        
        texts = data.get('texts', [])
        translate_func = data.get('translation_function')
        
        # If only one text, no need for parallel processing
        if len(texts) <= 1:
            return data
        
        # Attempt warm start on first call (if not already done in background)
        if self.enable_warm_start and not self.warm_started:
            print(f"[PARALLEL_TRANSLATION] Warm start not complete yet, performing inline warm start...")
            source_lang = texts[0].get('source_lang', 'auto') if texts else 'auto'
            target_lang = texts[0].get('target_lang', 'en') if texts else 'en'
            
            warm_start_success = self.warm_start(source_lang, target_lang, translate_func)
            
            if not warm_start_success and self.fallback_on_error:
                print(f"[PARALLEL_TRANSLATION] Warm start failed, enabling fallback mode")
                self.fallback_mode = True
                with self.lock:
                    self.fallback_count += 1
                return data
        
        # Limit batch size
        texts_to_process = texts[:self.batch_size]
        
        start_time = time.time()
        
        try:
            # Submit all translation tasks
            futures = []
            for text_item in texts_to_process:
                try:
                    future = self.executor.submit(
                        self._translate_single_text,
                        text_item,
                        translate_func
                    )
                    futures.append(future)
                except RuntimeError as e:
                    # Executor is shutdown
                    print(f"[PARALLEL_TRANSLATION] Executor shutdown, enabling fallback mode")
                    self.is_shutdown = True
                    if self.fallback_on_error:
                        self.fallback_mode = True
                        with self.lock:
                            self.fallback_count += 1
                    return data
            
            # Collect results with improved timeout handling
            results = []
            completed_count = 0
            try:
                for future in as_completed(futures, timeout=self.timeout):
                    try:
                        result = future.result()
                        results.append(result)
                        completed_count += 1
                    except Exception as e:
                        print(f"[PARALLEL_TRANSLATION] Future failed: {e}")
            except TimeoutError as e:
                # Collect partial results from completed futures
                print(f"[PARALLEL_TRANSLATION] Timeout after {completed_count}/{len(futures)} completed")
                for future in futures:
                    if future.done() and not future.cancelled():
                        try:
                            result = future.result(timeout=0)
                            if result not in results:
                                results.append(result)
                        except:
                            pass
                
                # If we got some results, continue with partial success
                if results:
                    print(f"[PARALLEL_TRANSLATION] Continuing with {len(results)} partial results")
                elif self.fallback_on_error:
                    print(f"[PARALLEL_TRANSLATION] No results, enabling fallback mode")
                    self.fallback_mode = True
                    with self.lock:
                        self.fallback_count += 1
                    return data
            
            # Verify we got results
            if not results:
                print(f"[PARALLEL_TRANSLATION] No results obtained")
                if self.fallback_on_error:
                    print(f"[PARALLEL_TRANSLATION] Enabling fallback mode")
                    self.fallback_mode = True
                    with self.lock:
                        self.fallback_count += 1
                return data
            
            # Calculate time saved
            elapsed = time.time() - start_time
            sequential_time = sum(r.get('translation_time', 0) for r in results 
                                if not r.get('skipped', False))
            time_saved = max(0, sequential_time - elapsed)
            
            # Update statistics
            with self.lock:
                self.total_texts += len(texts_to_process)
                self.parallel_operations += 1
                self.total_time_saved += time_saved
            
            # Update data with results
            data['translation_results'] = results
            data['parallel_translation_time'] = elapsed
            data['time_saved'] = time_saved
            
            speedup = sequential_time / elapsed if elapsed > 0 else 1.0
            success_rate = f"{len(results)}/{len(texts_to_process)}"
            print(f"[PARALLEL_TRANSLATION] Successfully translated {success_rate} texts in {elapsed:.3f}s "
                  f"(saved {time_saved:.3f}s, speedup: {speedup:.1f}x)")
            
            return data
            
        except Exception as e:
            print(f"[PARALLEL_TRANSLATION] Error during parallel processing: {e}")
            import traceback
            traceback.print_exc()
            
            if self.fallback_on_error:
                print(f"[PARALLEL_TRANSLATION] Enabling fallback mode due to exception")
                self.fallback_mode = True
                with self.lock:
                    self.fallback_count += 1
            
            return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        with self.lock:
            avg_time_saved = (self.total_time_saved / self.parallel_operations 
                            if self.parallel_operations > 0 else 0)
            
            return {
                'total_texts': self.total_texts,
                'parallel_operations': self.parallel_operations,
                'total_time_saved': f"{self.total_time_saved:.2f}s",
                'avg_time_saved_per_operation': f"{avg_time_saved:.3f}s",
                'worker_threads': self.worker_threads,
                'gpu_enabled': self.use_gpu,
                'warm_started': self.warm_started,
                'warm_start_attempts': self.warm_start_attempts,
                'fallback_mode': self.fallback_mode,
                'fallback_count': self.fallback_count
            }
    
    def reset(self):
        """Reset optimizer state"""
        with self.lock:
            self.total_texts = 0
            self.parallel_operations = 0
            self.total_time_saved = 0.0
    
    def cleanup(self):
        """Cleanup resources"""
        if self.executor and not self.is_shutdown:
            self.is_shutdown = True
            self.executor.shutdown(wait=True)
            print("[PARALLEL_TRANSLATION] Thread pool shut down")


# Plugin interface
def initialize(config: Dict[str, Any]) -> ParallelTranslationOptimizer:
    """Initialize the optimizer plugin"""
    return ParallelTranslationOptimizer(config)


def shutdown(optimizer: ParallelTranslationOptimizer):
    """Shutdown the optimizer plugin"""
    if optimizer:
        optimizer.cleanup()
