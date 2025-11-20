"""
Pipeline Worker Manager

Manages worker thread pools with dynamic scaling, health monitoring,
and graceful shutdown.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import queue


class WorkerState(Enum):
    """Worker thread states."""
    IDLE = "idle"
    WORKING = "working"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerStats:
    """Statistics for a worker."""
    worker_id: int
    state: WorkerState
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_work_time: float = 0.0
    average_task_time: float = 0.0
    last_activity: Optional[datetime] = None
    errors: int = 0


class Worker:
    """
    A managed worker thread.
    """
    
    def __init__(self,
                 worker_id: int,
                 task_queue: queue.Queue,
                 result_queue: Optional[queue.Queue] = None,
                 error_callback: Optional[Callable] = None):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique worker ID
            task_queue: Queue to get tasks from
            result_queue: Queue to put results in
            error_callback: Callback for errors
        """
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.error_callback = error_callback
        
        self.state = WorkerState.IDLE
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # Statistics
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_work_time = 0.0
        self.last_activity: Optional[datetime] = None
        self.errors = 0
        
        self.lock = threading.RLock()
        self.logger = logging.getLogger(f"{__name__}.Worker{worker_id}")
    
    def start(self):
        """Start the worker thread."""
        if self.thread and self.thread.is_alive():
            self.logger.warning(f"Worker {self.worker_id} already running")
            return
        
        self.stop_event.clear()
        self.pause_event.set()  # Not paused initially
        self.state = WorkerState.IDLE
        
        self.thread = threading.Thread(target=self._work_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"Worker {self.worker_id} started")
    
    def stop(self, timeout: float = 5.0):
        """
        Stop the worker thread.
        
        Args:
            timeout: Timeout for graceful shutdown
        """
        self.state = WorkerState.STOPPING
        self.stop_event.set()
        self.pause_event.set()  # Unpause if paused
        
        if self.thread:
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                self.logger.warning(f"Worker {self.worker_id} did not stop gracefully")
            else:
                self.logger.info(f"Worker {self.worker_id} stopped")
        
        self.state = WorkerState.STOPPED
    
    def pause(self):
        """Pause the worker."""
        self.state = WorkerState.PAUSED
        self.pause_event.clear()
        self.logger.debug(f"Worker {self.worker_id} paused")
    
    def resume(self):
        """Resume the worker."""
        self.state = WorkerState.IDLE
        self.pause_event.set()
        self.logger.debug(f"Worker {self.worker_id} resumed")
    
    def _work_loop(self):
        """Main work loop."""
        while not self.stop_event.is_set():
            # Wait if paused
            self.pause_event.wait()
            
            if self.stop_event.is_set():
                break
            
            try:
                # Get task with timeout
                task = self.task_queue.get(timeout=0.1)
                
                # Process task
                self.state = WorkerState.WORKING
                self.last_activity = datetime.now()
                
                start_time = time.time()
                result = self._process_task(task)
                work_time = time.time() - start_time
                
                with self.lock:
                    self.tasks_completed += 1
                    self.total_work_time += work_time
                
                # Put result if queue provided
                if self.result_queue and result is not None:
                    self.result_queue.put(result)
                
                self.state = WorkerState.IDLE
                
            except queue.Empty:
                # No task available, stay idle
                self.state = WorkerState.IDLE
                continue
                
            except Exception as e:
                with self.lock:
                    self.tasks_failed += 1
                    self.errors += 1
                
                self.logger.error(f"Worker {self.worker_id} error: {e}")
                
                if self.error_callback:
                    try:
                        self.error_callback(self.worker_id, e)
                    except Exception as callback_error:
                        self.logger.error(f"Error callback failed: {callback_error}")
                
                self.state = WorkerState.ERROR
                time.sleep(0.1)  # Brief pause after error
                self.state = WorkerState.IDLE
    
    def _process_task(self, task: Any) -> Any:
        """
        Process a task.
        
        Args:
            task: Task to process (callable or tuple of (func, args, kwargs))
            
        Returns:
            Task result
        """
        if callable(task):
            return task()
        elif isinstance(task, tuple):
            func, args, kwargs = task[0], task[1] if len(task) > 1 else (), task[2] if len(task) > 2 else {}
            return func(*args, **kwargs)
        else:
            raise ValueError(f"Invalid task type: {type(task)}")
    
    def get_stats(self) -> WorkerStats:
        """Get worker statistics."""
        with self.lock:
            avg_time = (
                self.total_work_time / self.tasks_completed
                if self.tasks_completed > 0 else 0.0
            )
            
            return WorkerStats(
                worker_id=self.worker_id,
                state=self.state,
                tasks_completed=self.tasks_completed,
                tasks_failed=self.tasks_failed,
                total_work_time=self.total_work_time,
                average_task_time=avg_time,
                last_activity=self.last_activity,
                errors=self.errors
            )


class PipelineWorkerManager:
    """
    Manages worker thread pools for the pipeline.
    
    Features:
    - Dynamic worker scaling
    - Worker health monitoring
    - Graceful shutdown
    - Load balancing
    - Statistics collection
    """
    
    def __init__(self, min_workers: int = 2, max_workers: int = 8):
        """
        Initialize worker manager.
        
        Args:
            min_workers: Minimum number of workers
            max_workers: Maximum number of workers
        """
        self.min_workers = min_workers
        self.max_workers = max_workers
        
        self.logger = logging.getLogger(__name__)
        
        # Worker pools
        self.pools: Dict[str, List[Worker]] = {}
        self.task_queues: Dict[str, queue.Queue] = {}
        self.result_queues: Dict[str, queue.Queue] = {}
        
        self.lock = threading.RLock()
        
        # Auto-scaling
        self.auto_scaling_enabled = True
        self.scale_up_threshold = 0.8  # 80% queue utilization
        self.scale_down_threshold = 0.2  # 20% queue utilization
        
        self.logger.info(f"Pipeline Worker Manager initialized (min={min_workers}, max={max_workers})")
    
    def create_pool(self,
                   pool_name: str,
                   num_workers: int = 4,
                   task_queue_size: int = 100,
                   result_queue_size: int = 100) -> bool:
        """
        Create a worker pool.
        
        Args:
            pool_name: Pool name
            num_workers: Initial number of workers
            task_queue_size: Task queue size
            result_queue_size: Result queue size
            
        Returns:
            bool: True if created successfully
        """
        with self.lock:
            if pool_name in self.pools:
                self.logger.warning(f"Pool {pool_name} already exists")
                return False
            
            # Clamp workers to min/max
            num_workers = max(self.min_workers, min(num_workers, self.max_workers))
            
            # Create queues
            task_queue = queue.Queue(maxsize=task_queue_size)
            result_queue = queue.Queue(maxsize=result_queue_size)
            
            self.task_queues[pool_name] = task_queue
            self.result_queues[pool_name] = result_queue
            
            # Create workers
            workers = []
            for i in range(num_workers):
                worker = Worker(
                    worker_id=i,
                    task_queue=task_queue,
                    result_queue=result_queue,
                    error_callback=lambda wid, err: self._on_worker_error(pool_name, wid, err)
                )
                worker.start()
                workers.append(worker)
            
            self.pools[pool_name] = workers
            self.logger.info(f"Created pool {pool_name} with {num_workers} workers")
            
            return True
    
    def submit_task(self, pool_name: str, task: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Submit a task to a pool.
        
        Args:
            pool_name: Pool name
            task: Task to submit (callable or tuple)
            block: Whether to block if queue full
            timeout: Timeout for blocking
            
        Returns:
            bool: True if submitted successfully
        """
        task_queue = self.task_queues.get(pool_name)
        if not task_queue:
            self.logger.error(f"Pool {pool_name} not found")
            return False
        
        try:
            task_queue.put(task, block=block, timeout=timeout)
            
            # Check if scaling needed
            if self.auto_scaling_enabled:
                self._check_scaling(pool_name)
            
            return True
        except queue.Full:
            self.logger.warning(f"Task queue for {pool_name} is full")
            return False
    
    def get_result(self, pool_name: str, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get a result from a pool.
        
        Args:
            pool_name: Pool name
            block: Whether to block if empty
            timeout: Timeout for blocking
            
        Returns:
            Result from pool
        """
        result_queue = self.result_queues.get(pool_name)
        if not result_queue:
            raise ValueError(f"Pool {pool_name} not found")
        
        return result_queue.get(block=block, timeout=timeout)
    
    def _check_scaling(self, pool_name: str):
        """Check if pool needs scaling."""
        with self.lock:
            workers = self.pools.get(pool_name, [])
            task_queue = self.task_queues.get(pool_name)
            
            if not task_queue:
                return
            
            queue_size = task_queue.qsize()
            queue_maxsize = task_queue.maxsize
            utilization = queue_size / queue_maxsize if queue_maxsize > 0 else 0
            
            # Scale up if high utilization
            if utilization >= self.scale_up_threshold and len(workers) < self.max_workers:
                self._scale_up(pool_name)
            
            # Scale down if low utilization
            elif utilization <= self.scale_down_threshold and len(workers) > self.min_workers:
                self._scale_down(pool_name)
    
    def _scale_up(self, pool_name: str):
        """Add a worker to the pool."""
        with self.lock:
            workers = self.pools.get(pool_name, [])
            if len(workers) >= self.max_workers:
                return
            
            worker_id = len(workers)
            worker = Worker(
                worker_id=worker_id,
                task_queue=self.task_queues[pool_name],
                result_queue=self.result_queues[pool_name],
                error_callback=lambda wid, err: self._on_worker_error(pool_name, wid, err)
            )
            worker.start()
            workers.append(worker)
            
            self.logger.info(f"Scaled up pool {pool_name}: {len(workers)-1} → {len(workers)} workers")
    
    def _scale_down(self, pool_name: str):
        """Remove a worker from the pool."""
        with self.lock:
            workers = self.pools.get(pool_name, [])
            if len(workers) <= self.min_workers:
                return
            
            # Stop last worker
            worker = workers.pop()
            worker.stop(timeout=2.0)
            
            self.logger.info(f"Scaled down pool {pool_name}: {len(workers)+1} → {len(workers)} workers")
    
    def _on_worker_error(self, pool_name: str, worker_id: int, error: Exception):
        """Handle worker error."""
        self.logger.error(f"Worker error in pool {pool_name}, worker {worker_id}: {error}")
    
    def pause_pool(self, pool_name: str):
        """Pause all workers in a pool."""
        with self.lock:
            workers = self.pools.get(pool_name, [])
            for worker in workers:
                worker.pause()
            self.logger.info(f"Paused pool {pool_name}")
    
    def resume_pool(self, pool_name: str):
        """Resume all workers in a pool."""
        with self.lock:
            workers = self.pools.get(pool_name, [])
            for worker in workers:
                worker.resume()
            self.logger.info(f"Resumed pool {pool_name}")
    
    def stop_pool(self, pool_name: str, timeout: float = 5.0):
        """
        Stop all workers in a pool.
        
        Args:
            pool_name: Pool name
            timeout: Timeout per worker
        """
        with self.lock:
            workers = self.pools.get(pool_name, [])
            for worker in workers:
                worker.stop(timeout=timeout)
            
            # Clear queues
            if pool_name in self.task_queues:
                self._clear_queue(self.task_queues[pool_name])
            if pool_name in self.result_queues:
                self._clear_queue(self.result_queues[pool_name])
            
            self.logger.info(f"Stopped pool {pool_name}")
    
    def stop_all(self, timeout: float = 5.0):
        """Stop all pools."""
        with self.lock:
            for pool_name in list(self.pools.keys()):
                self.stop_pool(pool_name, timeout)
            self.logger.info("Stopped all pools")
    
    @staticmethod
    def _clear_queue(q: queue.Queue):
        """Clear a queue."""
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break
    
    def get_pool_stats(self, pool_name: str) -> Dict[str, Any]:
        """Get statistics for a pool."""
        with self.lock:
            workers = self.pools.get(pool_name, [])
            if not workers:
                return {}
            
            worker_stats = [w.get_stats() for w in workers]
            
            total_completed = sum(s.tasks_completed for s in worker_stats)
            total_failed = sum(s.tasks_failed for s in worker_stats)
            total_errors = sum(s.errors for s in worker_stats)
            
            return {
                'pool_name': pool_name,
                'num_workers': len(workers),
                'total_tasks_completed': total_completed,
                'total_tasks_failed': total_failed,
                'total_errors': total_errors,
                'success_rate': (
                    total_completed / max(total_completed + total_failed, 1) * 100
                ),
                'task_queue_size': self.task_queues[pool_name].qsize() if pool_name in self.task_queues else 0,
                'result_queue_size': self.result_queues[pool_name].qsize() if pool_name in self.result_queues else 0,
                'workers': [vars(s) for s in worker_stats]
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools."""
        with self.lock:
            return {
                pool_name: self.get_pool_stats(pool_name)
                for pool_name in self.pools.keys()
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all pools."""
        all_stats = self.get_all_stats()
        
        total_workers = sum(s['num_workers'] for s in all_stats.values())
        total_completed = sum(s['total_tasks_completed'] for s in all_stats.values())
        total_failed = sum(s['total_tasks_failed'] for s in all_stats.values())
        
        return {
            'total_pools': len(self.pools),
            'total_workers': total_workers,
            'total_tasks_completed': total_completed,
            'total_tasks_failed': total_failed,
            'overall_success_rate': (
                total_completed / max(total_completed + total_failed, 1) * 100
            ),
            'auto_scaling_enabled': self.auto_scaling_enabled,
            'pools': all_stats
        }
