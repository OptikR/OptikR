"""
Parallel Capture Optimizer Plugin
Captures multiple regions simultaneously using worker threads
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from queue import Queue, Empty
import threading


class ParallelCaptureOptimizer:
    """Captures multiple regions in parallel using worker threads"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.worker_threads = config.get('worker_threads', 4)
        self.queue_size = config.get('queue_size', 10)
        self.timeout = config.get('timeout_seconds', 5.0)
        
        # Thread pool
        self.executor = ThreadPoolExecutor(
            max_workers=self.worker_threads,
            thread_name_prefix="capture_worker"
        )
        
        # Statistics
        self.total_captures = 0
        self.parallel_captures = 0
        self.total_time_saved = 0.0
        self.lock = threading.Lock()
        
        print(f"[PARALLEL_CAPTURE] Initialized with {self.worker_threads} workers")
    
    def _capture_single_region(self, region_data: Dict[str, Any], capture_func) -> Dict[str, Any]:
        """Capture a single region"""
        try:
            start_time = time.time()
            
            # Extract region info
            region_id = region_data.get('id', 0)
            bbox = region_data.get('bbox', (0, 0, 100, 100))
            
            # Perform capture using provided capture function
            if capture_func:
                frame = capture_func(bbox)
            else:
                # Fallback: return None if no capture function provided
                frame = None
            
            elapsed = time.time() - start_time
            
            return {
                'region_id': region_id,
                'frame': frame,
                'bbox': bbox,
                'success': frame is not None,
                'capture_time': elapsed
            }
            
        except Exception as e:
            print(f"[PARALLEL_CAPTURE] Error capturing region {region_data.get('id')}: {e}")
            return {
                'region_id': region_data.get('id', 0),
                'frame': None,
                'bbox': region_data.get('bbox'),
                'success': False,
                'error': str(e)
            }
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process: Capture multiple regions in parallel"""
        regions = data.get('regions', [])
        capture_func = data.get('capture_function')
        
        # If only one region, no need for parallel processing
        if len(regions) <= 1:
            return data
        
        start_time = time.time()
        
        # Submit all capture tasks
        futures = []
        for region in regions:
            future = self.executor.submit(
                self._capture_single_region,
                region,
                capture_func
            )
            futures.append(future)
        
        # Collect results
        results = []
        for future in as_completed(futures, timeout=self.timeout):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[PARALLEL_CAPTURE] Future failed: {e}")
        
        # Calculate time saved
        elapsed = time.time() - start_time
        sequential_time = sum(r.get('capture_time', 0) for r in results)
        time_saved = sequential_time - elapsed
        
        # Update statistics
        with self.lock:
            self.total_captures += len(regions)
            self.parallel_captures += 1
            self.total_time_saved += time_saved
        
        # Update data with results
        data['capture_results'] = results
        data['parallel_capture_time'] = elapsed
        data['time_saved'] = time_saved
        
        print(f"[PARALLEL_CAPTURE] Captured {len(results)} regions in {elapsed:.3f}s "
              f"(saved {time_saved:.3f}s)")
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        with self.lock:
            avg_time_saved = (self.total_time_saved / self.parallel_captures 
                            if self.parallel_captures > 0 else 0)
            
            return {
                'total_captures': self.total_captures,
                'parallel_operations': self.parallel_captures,
                'total_time_saved': f"{self.total_time_saved:.2f}s",
                'avg_time_saved_per_operation': f"{avg_time_saved:.3f}s",
                'worker_threads': self.worker_threads
            }
    
    def reset(self):
        """Reset optimizer state"""
        with self.lock:
            self.total_captures = 0
            self.parallel_captures = 0
            self.total_time_saved = 0.0
    
    def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
            print("[PARALLEL_CAPTURE] Thread pool shut down")


# Plugin interface
def initialize(config: Dict[str, Any]) -> ParallelCaptureOptimizer:
    """Initialize the optimizer plugin"""
    return ParallelCaptureOptimizer(config)


def shutdown(optimizer: ParallelCaptureOptimizer):
    """Shutdown the optimizer plugin"""
    if optimizer:
        optimizer.cleanup()
