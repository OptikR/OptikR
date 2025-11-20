"""
Pipeline Queue Manager

Manages queues between pipeline stages with monitoring, backpressure handling,
and memory control.
"""

import queue
import threading
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from collections import deque


@dataclass
class QueueStats:
    """Statistics for a queue."""
    name: str
    size: int
    max_size: int
    total_items_added: int = 0
    total_items_removed: int = 0
    total_items_dropped: int = 0
    average_wait_time_ms: float = 0.0
    peak_size: int = 0
    utilization_percent: float = 0.0


class ManagedQueue:
    """
    A managed queue with monitoring and backpressure handling.
    """
    
    def __init__(self, name: str, maxsize: int = 10, drop_policy: str = "oldest"):
        """
        Initialize managed queue.
        
        Args:
            name: Queue name
            maxsize: Maximum queue size
            drop_policy: What to drop when full ("oldest", "newest", "block")
        """
        self.name = name
        self.maxsize = maxsize
        self.drop_policy = drop_policy
        
        self.queue = queue.Queue(maxsize=maxsize)
        self.lock = threading.RLock()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Statistics
        self.total_added = 0
        self.total_removed = 0
        self.total_dropped = 0
        self.peak_size = 0
        self.wait_times = deque(maxlen=100)
        
        # Callbacks
        self.on_full_callback: Optional[Callable] = None
        self.on_empty_callback: Optional[Callable] = None
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Put item in queue with backpressure handling.
        
        Args:
            item: Item to add
            block: Whether to block if full
            timeout: Timeout for blocking
            
        Returns:
            bool: True if added, False if dropped
        """
        start_time = datetime.now()
        
        try:
            with self.lock:
                current_size = self.queue.qsize()
                
                # Check if full
                if current_size >= self.maxsize:
                    if self.drop_policy == "block":
                        # Block until space available
                        pass  # Let queue.put handle blocking
                    elif self.drop_policy == "oldest":
                        # Drop oldest item
                        try:
                            self.queue.get_nowait()
                            self.total_dropped += 1
                            self.logger.debug(f"Dropped oldest item from {self.name}")
                        except queue.Empty:
                            pass
                    elif self.drop_policy == "newest":
                        # Drop new item
                        self.total_dropped += 1
                        self.logger.debug(f"Dropped newest item from {self.name}")
                        return False
                    
                    # Trigger callback
                    if self.on_full_callback:
                        try:
                            self.on_full_callback(self.name, current_size)
                        except Exception as e:
                            self.logger.error(f"Full callback error: {e}")
            
            # Add to queue
            self.queue.put(item, block=block, timeout=timeout)
            
            with self.lock:
                self.total_added += 1
                current_size = self.queue.qsize()
                self.peak_size = max(self.peak_size, current_size)
                
                # Record wait time
                wait_time = (datetime.now() - start_time).total_seconds()
                self.wait_times.append(wait_time)
            
            return True
            
        except queue.Full:
            with self.lock:
                self.total_dropped += 1
            self.logger.warning(f"Queue {self.name} full, item dropped")
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get item from queue.
        
        Args:
            block: Whether to block if empty
            timeout: Timeout for blocking
            
        Returns:
            Item from queue
            
        Raises:
            queue.Empty: If queue is empty and not blocking
        """
        item = self.queue.get(block=block, timeout=timeout)
        
        with self.lock:
            self.total_removed += 1
            
            # Trigger callback if empty
            if self.queue.empty() and self.on_empty_callback:
                try:
                    self.on_empty_callback(self.name)
                except Exception as e:
                    self.logger.error(f"Empty callback error: {e}")
        
        return item
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
    
    def is_full(self) -> bool:
        """Check if queue is full."""
        return self.queue.qsize() >= self.maxsize
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()
    
    def clear(self):
        """Clear all items from queue."""
        with self.lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break
            self.logger.info(f"Cleared queue {self.name}")
    
    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        with self.lock:
            current_size = self.queue.qsize()
            utilization = (current_size / self.maxsize * 100) if self.maxsize > 0 else 0
            avg_wait = sum(self.wait_times) / len(self.wait_times) * 1000 if self.wait_times else 0
            
            return QueueStats(
                name=self.name,
                size=current_size,
                max_size=self.maxsize,
                total_items_added=self.total_added,
                total_items_removed=self.total_removed,
                total_items_dropped=self.total_dropped,
                average_wait_time_ms=avg_wait,
                peak_size=self.peak_size,
                utilization_percent=utilization
            )


class PipelineQueueManager:
    """
    Manages all queues in the pipeline.
    
    Features:
    - Queue creation and management
    - Backpressure handling
    - Queue monitoring
    - Memory control
    - Statistics collection
    """
    
    def __init__(self):
        """Initialize queue manager."""
        self.logger = logging.getLogger(__name__)
        
        # Managed queues
        self.queues: Dict[str, ManagedQueue] = {}
        self.lock = threading.RLock()
        
        # Global settings
        self.backpressure_enabled = True
        self.backpressure_threshold = 0.8  # 80% full triggers backpressure
        
        # Callbacks
        self.backpressure_callbacks: list = []
        
        self.logger.info("Pipeline Queue Manager initialized")
    
    def create_queue(self,
                    name: str,
                    maxsize: int = 10,
                    drop_policy: str = "oldest") -> ManagedQueue:
        """
        Create a managed queue.
        
        Args:
            name: Queue name
            maxsize: Maximum size
            drop_policy: Drop policy ("oldest", "newest", "block")
            
        Returns:
            ManagedQueue instance
        """
        with self.lock:
            if name in self.queues:
                self.logger.warning(f"Queue {name} already exists")
                return self.queues[name]
            
            managed_queue = ManagedQueue(name, maxsize, drop_policy)
            
            # Set callbacks
            managed_queue.on_full_callback = self._on_queue_full
            managed_queue.on_empty_callback = self._on_queue_empty
            
            self.queues[name] = managed_queue
            self.logger.info(f"Created queue: {name} (maxsize={maxsize}, policy={drop_policy})")
            
            return managed_queue
    
    def get_queue(self, name: str) -> Optional[ManagedQueue]:
        """
        Get a queue by name.
        
        Args:
            name: Queue name
            
        Returns:
            ManagedQueue or None
        """
        return self.queues.get(name)
    
    def put(self, queue_name: str, item: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Put item in named queue.
        
        Args:
            queue_name: Queue name
            item: Item to add
            block: Whether to block
            timeout: Timeout
            
        Returns:
            bool: True if added
        """
        queue_obj = self.queues.get(queue_name)
        if not queue_obj:
            self.logger.error(f"Queue {queue_name} not found")
            return False
        
        return queue_obj.put(item, block, timeout)
    
    def get(self, queue_name: str, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get item from named queue.
        
        Args:
            queue_name: Queue name
            block: Whether to block
            timeout: Timeout
            
        Returns:
            Item from queue
        """
        queue_obj = self.queues.get(queue_name)
        if not queue_obj:
            raise ValueError(f"Queue {queue_name} not found")
        
        return queue_obj.get(block, timeout)
    
    def _on_queue_full(self, queue_name: str, size: int):
        """Handle queue full event."""
        self.logger.warning(f"Queue {queue_name} is full (size={size})")
        
        # Check if backpressure should be applied
        if self.backpressure_enabled:
            utilization = size / self.queues[queue_name].maxsize
            if utilization >= self.backpressure_threshold:
                self._apply_backpressure(queue_name)
    
    def _on_queue_empty(self, queue_name: str):
        """Handle queue empty event."""
        self.logger.debug(f"Queue {queue_name} is empty")
    
    def _apply_backpressure(self, queue_name: str):
        """Apply backpressure for a queue."""
        self.logger.info(f"Applying backpressure for queue: {queue_name}")
        
        for callback in self.backpressure_callbacks:
            try:
                callback(queue_name)
            except Exception as e:
                self.logger.error(f"Backpressure callback error: {e}")
    
    def register_backpressure_callback(self, callback: Callable):
        """
        Register callback for backpressure events.
        
        Args:
            callback: Function to call (receives queue_name)
        """
        self.backpressure_callbacks.append(callback)
        self.logger.debug("Registered backpressure callback")
    
    def get_all_stats(self) -> Dict[str, QueueStats]:
        """
        Get statistics for all queues.
        
        Returns:
            dict: Queue name -> QueueStats
        """
        with self.lock:
            return {
                name: queue_obj.get_stats()
                for name, queue_obj in self.queues.items()
            }
    
    def get_total_memory_estimate(self) -> float:
        """
        Estimate total memory used by queues (rough estimate).
        
        Returns:
            float: Estimated memory in MB
        """
        import sys
        
        total_items = sum(q.size() for q in self.queues.values())
        # Rough estimate: 1KB per item
        return total_items * 1024 / (1024 * 1024)
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check health of all queues.
        
        Returns:
            dict: Health status
        """
        with self.lock:
            issues = []
            
            for name, queue_obj in self.queues.items():
                stats = queue_obj.get_stats()
                
                # Check for high utilization
                if stats.utilization_percent > 90:
                    issues.append(f"{name}: High utilization ({stats.utilization_percent:.1f}%)")
                
                # Check for high drop rate
                if stats.total_items_added > 0:
                    drop_rate = stats.total_items_dropped / stats.total_items_added * 100
                    if drop_rate > 10:
                        issues.append(f"{name}: High drop rate ({drop_rate:.1f}%)")
            
            return {
                'healthy': len(issues) == 0,
                'issues': issues,
                'total_queues': len(self.queues),
                'total_items': sum(q.size() for q in self.queues.values()),
                'estimated_memory_mb': self.get_total_memory_estimate()
            }
    
    def clear_all(self):
        """Clear all queues."""
        with self.lock:
            for queue_obj in self.queues.values():
                queue_obj.clear()
            self.logger.info("Cleared all queues")
    
    def resize_queue(self, queue_name: str, new_maxsize: int):
        """
        Resize a queue (creates new queue with same items).
        
        Args:
            queue_name: Queue to resize
            new_maxsize: New maximum size
        """
        with self.lock:
            old_queue = self.queues.get(queue_name)
            if not old_queue:
                self.logger.error(f"Queue {queue_name} not found")
                return
            
            # Create new queue
            new_queue = ManagedQueue(queue_name, new_maxsize, old_queue.drop_policy)
            
            # Transfer items
            items = []
            while not old_queue.is_empty():
                try:
                    items.append(old_queue.get(block=False))
                except queue.Empty:
                    break
            
            for item in items:
                new_queue.put(item, block=False)
            
            # Replace
            self.queues[queue_name] = new_queue
            self.logger.info(f"Resized queue {queue_name}: {old_queue.maxsize} → {new_maxsize}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all queues.
        
        Returns:
            dict: Summary information
        """
        stats = self.get_all_stats()
        health = self.check_health()
        
        return {
            'total_queues': len(self.queues),
            'total_items': sum(s.size for s in stats.values()),
            'total_capacity': sum(s.max_size for s in stats.values()),
            'average_utilization': sum(s.utilization_percent for s in stats.values()) / len(stats) if stats else 0,
            'total_dropped': sum(s.total_items_dropped for s in stats.values()),
            'health': health,
            'queues': {name: vars(stat) for name, stat in stats.items()}
        }
