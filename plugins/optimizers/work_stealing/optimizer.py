"""
Work-Stealing Pool Optimizer Plugin
Load balancing across worker threads
"""

import threading
import random
from typing import Dict, Any, List, Callable
from queue import Queue, Empty
from collections import deque


class WorkStealingPoolOptimizer:
    """Work-stealing thread pool for load balancing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.num_workers = config.get('num_workers', 4)
        self.steal_threshold = config.get('steal_threshold', 2)
        self.enable_affinity = config.get('enable_affinity', False)
        
        # Per-worker queues (deques for efficient stealing)
        self.worker_queues: List[deque] = [deque() for _ in range(self.num_workers)]
        self.worker_locks: List[threading.Lock] = [threading.Lock() for _ in range(self.num_workers)]
        
        # Worker threads
        self.workers: List[threading.Thread] = []
        self.running = False
        
        # Statistics
        self.total_processed = 0
        self.total_stolen = 0
        self.worker_stats = [{'processed': 0, 'stolen': 0} for _ in range(self.num_workers)]
    
    def _worker_thread(self, worker_id: int, process_func: Callable):
        """Worker thread that processes tasks and steals work"""
        my_queue = self.worker_queues[worker_id]
        my_lock = self.worker_locks[worker_id]
        
        while self.running:
            task = None
            
            # Try to get task from own queue
            with my_lock:
                if my_queue:
                    task = my_queue.popleft()
            
            # If no task, try to steal from others
            if task is None:
                task = self._steal_work(worker_id)
                if task is not None:
                    self.total_stolen += 1
                    self.worker_stats[worker_id]['stolen'] += 1
            
            # Process task if found
            if task is not None:
                try:
                    process_func(task)
                    self.total_processed += 1
                    self.worker_stats[worker_id]['processed'] += 1
                except Exception as e:
                    print(f"Worker {worker_id} error: {e}")
            else:
                # No work available, sleep briefly
                threading.Event().wait(0.001)
    
    def _steal_work(self, thief_id: int) -> Any:
        """Attempt to steal work from another worker"""
        # Randomly select victims to steal from
        victims = list(range(self.num_workers))
        victims.remove(thief_id)
        random.shuffle(victims)
        
        for victim_id in victims:
            victim_queue = self.worker_queues[victim_id]
            victim_lock = self.worker_locks[victim_id]
            
            # Only steal if victim has enough work
            with victim_lock:
                if len(victim_queue) > self.steal_threshold:
                    # Steal from the end (LIFO for better cache locality)
                    return victim_queue.pop()
        
        return None
    
    def submit(self, task: Dict[str, Any], worker_id: int = None):
        """Submit task to a worker queue"""
        # Round-robin assignment if no worker specified
        if worker_id is None:
            worker_id = self.total_processed % self.num_workers
        
        # Add to worker's queue
        with self.worker_locks[worker_id]:
            self.worker_queues[worker_id].append(task)
    
    def start(self, process_func: Callable):
        """Start worker threads"""
        self.running = True
        
        for i in range(self.num_workers):
            thread = threading.Thread(
                target=self._worker_thread,
                args=(i, process_func),
                daemon=True
            )
            self.workers.append(thread)
            thread.start()
    
    def stop(self):
        """Stop worker threads"""
        self.running = False
        
        for thread in self.workers:
            thread.join(timeout=2.0)
        
        self.workers.clear()
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with work-stealing pool"""
        data['work_stealing_enabled'] = self.running
        data['num_workers'] = self.num_workers
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get work-stealing statistics"""
        steal_rate = (self.total_stolen / self.total_processed * 100) if self.total_processed > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'total_stolen': self.total_stolen,
            'steal_rate': f"{steal_rate:.1f}%",
            'num_workers': self.num_workers,
            'worker_stats': self.worker_stats
        }
    
    def reset(self):
        """Reset optimizer state"""
        self.stop()
        for queue in self.worker_queues:
            queue.clear()
        self.total_processed = 0
        self.total_stolen = 0
        self.worker_stats = [{'processed': 0, 'stolen': 0} for _ in range(self.num_workers)]


# Plugin interface
def initialize(config: Dict[str, Any]) -> WorkStealingPoolOptimizer:
    """Initialize the optimizer plugin"""
    return WorkStealingPoolOptimizer(config)
