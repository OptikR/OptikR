"""
Work-Stealing Thread Pool - Advanced load balancing
"""

import threading
import queue
import time
from typing import List, Any, Optional
from collections import deque


class WorkStealingWorker:
    """
    Worker that can steal tasks from other workers.
    
    Benefits:
    - Better CPU utilization
    - Reduced idle time
    - Automatic load balancing
    """
    
    def __init__(self, worker_id: int, local_queue: deque, 
                 shared_queues: List[deque], stop_event: threading.Event):
        self.worker_id = worker_id
        self.local_queue = local_queue  # Own queue (LIFO for cache locality)
        self.shared_queues = shared_queues  # Other workers' queues
        self.stop_event = stop_event
        
        self.lock = threading.Lock()
        self.tasks_completed = 0
        self.tasks_stolen = 0
        
        self.thread = threading.Thread(target=self._work_loop, daemon=True)
        self.thread.start()
    
    def _work_loop(self):
        """Main work loop with work stealing."""
        while not self.stop_event.is_set():
            task = self._get_task()
            
            if task is None:
                time.sleep(0.001)  # Brief sleep if no work
                continue
            
            try:
                # Process task
                if callable(task):
                    task()
                elif isinstance(task, tuple):
                    func, args, kwargs = task[0], task[1] if len(task) > 1 else (), task[2] if len(task) > 2 else {}
                    func(*args, **kwargs)
                
                with self.lock:
                    self.tasks_completed += 1
            except Exception as e:
                print(f"Worker {self.worker_id} error: {e}")
    
    def _get_task(self) -> Optional[Any]:
        """Get task from local queue or steal from others."""
        # Try local queue first (LIFO for cache locality)
        with self.lock:
            if self.local_queue:
                return self.local_queue.pop()
        
        # Try stealing from other workers (FIFO - steal oldest tasks)
        for other_queue in self.shared_queues:
            if other_queue is self.local_queue:
                continue
            
            try:
                # Steal from front (oldest task)
                if other_queue:
                    task = other_queue.popleft()
                    with self.lock:
                        self.tasks_stolen += 1
                    return task
            except (IndexError, AttributeError):
                continue
        
        return None
    
    def submit(self, task: Any):
        """Submit task to local queue."""
        with self.lock:
            self.local_queue.append(task)
    
    def get_stats(self):
        """Get worker statistics."""
        with self.lock:
            return {
                'worker_id': self.worker_id,
                'tasks_completed': self.tasks_completed,
                'tasks_stolen': self.tasks_stolen,
                'queue_size': len(self.local_queue)
            }


class WorkStealingPool:
    """
    Thread pool with work-stealing for optimal load balancing.
    
    Usage:
        pool = WorkStealingPool(num_workers=4)
        pool.submit(lambda: process_frame(frame))
        pool.shutdown()
    """
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.stop_event = threading.Event()
        
        # Create per-worker queues
        self.queues = [deque() for _ in range(num_workers)]
        
        # Create workers
        self.workers = [
            WorkStealingWorker(i, self.queues[i], self.queues, self.stop_event)
            for i in range(num_workers)
        ]
        
        self.next_worker = 0
        self.lock = threading.Lock()
    
    def submit(self, task: Any):
        """Submit task to pool (round-robin distribution)."""
        with self.lock:
            worker = self.workers[self.next_worker]
            self.next_worker = (self.next_worker + 1) % self.num_workers
        
        worker.submit(task)
    
    def get_stats(self):
        """Get pool statistics."""
        return {
            'num_workers': self.num_workers,
            'workers': [w.get_stats() for w in self.workers]
        }
    
    def shutdown(self, timeout: float = 5.0):
        """Shutdown pool."""
        self.stop_event.set()
        for worker in self.workers:
            worker.thread.join(timeout=timeout)


# Performance comparison:
"""
Standard ThreadPool:
- Worker 1: 100 tasks (busy)
- Worker 2: 100 tasks (busy)
- Worker 3: 0 tasks (idle)
- Worker 4: 0 tasks (idle)
→ 50% CPU utilization

Work-Stealing Pool:
- Worker 1: 50 tasks (steals from 1)
- Worker 2: 50 tasks (steals from 2)
- Worker 3: 50 tasks (steals from 1)
- Worker 4: 50 tasks (steals from 2)
→ 100% CPU utilization
"""
