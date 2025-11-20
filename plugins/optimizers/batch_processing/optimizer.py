"""
Batch Processing Optimizer Plugin
Batches multiple frames for processing together
"""

import time
import threading
from typing import Dict, Any, List
from queue import Queue, Empty


class BatchProcessingOptimizer:
    """Batches frames for more efficient processing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_batch_size = config.get('max_batch_size', 8)
        self.max_wait_time = config.get('max_wait_time_ms', 10.0) / 1000.0
        self.min_batch_size = config.get('min_batch_size', 2)
        self.adaptive = config.get('adaptive', True)
        
        # Batch queue
        self.batch_queue: Queue = Queue()
        self.current_batch: List[Dict[str, Any]] = []
        self.batch_start_time = None
        self.lock = threading.Lock()
        
        # Statistics
        self.total_items = 0
        self.total_batches = 0
        self.avg_batch_size = 0.0
    
    def _should_flush_batch(self) -> bool:
        """Check if batch should be flushed"""
        with self.lock:
            # Flush if batch is full
            if len(self.current_batch) >= self.max_batch_size:
                return True
            
            # Flush if wait time exceeded
            if self.batch_start_time is not None:
                elapsed = time.time() - self.batch_start_time
                if elapsed >= self.max_wait_time:
                    return True
            
            return False
    
    def _flush_batch(self) -> List[Dict[str, Any]]:
        """Flush current batch and return it"""
        with self.lock:
            if not self.current_batch:
                return []
            
            batch = self.current_batch.copy()
            self.current_batch = []
            self.batch_start_time = None
            
            # Update statistics
            self.total_batches += 1
            self.total_items += len(batch)
            self.avg_batch_size = self.total_items / self.total_batches
            
            return batch
    
    def add_to_batch(self, data: Dict[str, Any]) -> bool:
        """Add item to batch. Returns True if batch is ready."""
        with self.lock:
            # Start timer on first item
            if not self.current_batch:
                self.batch_start_time = time.time()
            
            self.current_batch.append(data)
            
            return self._should_flush_batch()
    
    def get_batch(self, timeout: float = None) -> List[Dict[str, Any]]:
        """Get a batch when ready"""
        # Wait for batch to be ready
        start_time = time.time()
        
        while True:
            if self._should_flush_batch():
                return self._flush_batch()
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    # Flush partial batch if minimum size met
                    with self.lock:
                        if len(self.current_batch) >= self.min_batch_size:
                            return self._flush_batch()
                    return []
            
            # Small sleep to avoid busy waiting
            time.sleep(0.001)
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-process: Add to batch"""
        # Add to batch
        batch_ready = self.add_to_batch(data)
        
        # Mark as batched
        data['batched'] = True
        data['batch_ready'] = batch_ready
        
        if batch_ready:
            # Get the batch
            batch = self._flush_batch()
            data['batch'] = batch
            data['batch_size'] = len(batch)
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch statistics"""
        return {
            'total_items': self.total_items,
            'total_batches': self.total_batches,
            'avg_batch_size': f"{self.avg_batch_size:.1f}",
            'current_batch_size': len(self.current_batch)
        }
    
    def reset(self):
        """Reset optimizer state"""
        with self.lock:
            self.current_batch = []
            self.batch_start_time = None
            self.total_items = 0
            self.total_batches = 0
            self.avg_batch_size = 0.0


# Plugin interface
def initialize(config: Dict[str, Any]) -> BatchProcessingOptimizer:
    """Initialize the optimizer plugin"""
    return BatchProcessingOptimizer(config)
