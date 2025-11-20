"""
Async Pipeline Optimizer Plugin
Enables overlapping execution of pipeline stages
"""

import threading
import time
from typing import Dict, Any, Callable, List
from queue import Queue, Empty, Full
from concurrent.futures import ThreadPoolExecutor, Future


class AsyncPipelineOptimizer:
    """Enables async/overlapping execution of pipeline stages"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_concurrent = config.get('max_concurrent_stages', 4)
        self.queue_size = config.get('queue_size', 16)
        self.enable_prefetch = config.get('enable_prefetch', True)
        self.thread_pool_size = config.get('thread_pool_size', 4)
        
        # Thread pool for async execution
        self.executor = ThreadPoolExecutor(max_workers=self.thread_pool_size)
        
        # Stage queues
        self.stage_queues: Dict[str, Queue] = {}
        self.stage_threads: Dict[str, threading.Thread] = {}
        self.running = False
        
        # Statistics
        self.total_processed = 0
        self.stage_times: Dict[str, List[float]] = {}
        self.concurrent_stages = 0
    
    def _create_stage_queue(self, stage_name: str) -> Queue:
        """Create queue for a pipeline stage"""
        return Queue(maxsize=self.queue_size)
    
    def _stage_worker(self, stage_name: str, stage_func: Callable, output_queue: Queue):
        """Worker thread for a pipeline stage"""
        input_queue = self.stage_queues.get(stage_name)
        
        while self.running:
            try:
                # Get input from queue
                data = input_queue.get(timeout=0.1)
                
                if data is None:  # Poison pill
                    break
                
                # Process stage
                start_time = time.time()
                result = stage_func(data)
                elapsed = time.time() - start_time
                
                # Track timing
                if stage_name not in self.stage_times:
                    self.stage_times[stage_name] = []
                self.stage_times[stage_name].append(elapsed)
                
                # Put result in output queue
                if output_queue is not None:
                    output_queue.put(result)
                
                self.total_processed += 1
                
            except Empty:
                continue
            except Exception as e:
                print(f"Error in stage {stage_name}: {e}")
    
    def register_stage(self, stage_name: str, stage_func: Callable, next_stage: str = None):
        """Register a pipeline stage for async execution"""
        # Create input queue for this stage
        self.stage_queues[stage_name] = self._create_stage_queue(stage_name)
        
        # Get output queue (next stage's input queue)
        output_queue = self.stage_queues.get(next_stage) if next_stage else None
        
        # Create worker thread
        thread = threading.Thread(
            target=self._stage_worker,
            args=(stage_name, stage_func, output_queue),
            daemon=True
        )
        self.stage_threads[stage_name] = thread
    
    def start(self):
        """Start all stage workers"""
        self.running = True
        for thread in self.stage_threads.values():
            thread.start()
    
    def stop(self):
        """Stop all stage workers"""
        self.running = False
        
        # Send poison pills
        for queue in self.stage_queues.values():
            try:
                queue.put(None, timeout=1.0)
            except Full:
                pass
        
        # Wait for threads
        for thread in self.stage_threads.values():
            thread.join(timeout=2.0)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
    
    def submit(self, stage_name: str, data: Dict[str, Any]) -> bool:
        """Submit data to a stage queue"""
        queue = self.stage_queues.get(stage_name)
        if queue is None:
            return False
        
        try:
            queue.put(data, timeout=0.1)
            return True
        except Full:
            return False
    
    def submit_async(self, func: Callable, *args, **kwargs) -> Future:
        """Submit function for async execution"""
        return self.executor.submit(func, *args, **kwargs)
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data through async pipeline"""
        # Mark as async processing
        data['async_processing'] = True
        data['async_enabled'] = self.running
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get async pipeline statistics"""
        avg_times = {}
        for stage, times in self.stage_times.items():
            if times:
                avg_times[stage] = f"{sum(times) / len(times) * 1000:.1f}ms"
        
        return {
            'total_processed': self.total_processed,
            'active_stages': len(self.stage_threads),
            'avg_stage_times': avg_times,
            'queue_sizes': {
                name: queue.qsize() 
                for name, queue in self.stage_queues.items()
            }
        }
    
    def reset(self):
        """Reset optimizer state"""
        self.stop()
        self.stage_queues.clear()
        self.stage_threads.clear()
        self.stage_times.clear()
        self.total_processed = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> AsyncPipelineOptimizer:
    """Initialize the optimizer plugin"""
    return AsyncPipelineOptimizer(config)
