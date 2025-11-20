"""
Priority Queue Manager - Enhanced queue system with task priorities
"""

import queue
import threading
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import IntEnum


class TaskPriority(IntEnum):
    """Task priority levels (lower number = higher priority)."""
    CRITICAL = 0   # User-facing overlays, UI updates
    HIGH = 1       # OCR processing for visible regions
    NORMAL = 2     # Translation, caching
    LOW = 3        # Background tasks, prefetching
    IDLE = 4       # Cleanup, optimization


@dataclass(order=True)
class PriorityTask:
    """Task with priority."""
    priority: int
    task: Any = field(compare=False)
    timestamp: float = field(compare=False)


class PriorityManagedQueue:
    """
    Priority-based queue for task scheduling.
    
    Benefits:
    - User-facing tasks processed first
    - Better responsiveness
    - Adaptive load balancing
    """
    
    def __init__(self, name: str, maxsize: int = 100):
        self.name = name
        self.maxsize = maxsize
        self.queue = queue.PriorityQueue(maxsize=maxsize)
        self.lock = threading.RLock()
        
        # Stats
        self.tasks_by_priority = {p: 0 for p in TaskPriority}
    
    def put(self, task: Any, priority: TaskPriority = TaskPriority.NORMAL, 
            block: bool = True, timeout: Optional[float] = None) -> bool:
        """Add task with priority."""
        import time
        
        priority_task = PriorityTask(
            priority=priority.value,
            task=task,
            timestamp=time.time()
        )
        
        try:
            self.queue.put(priority_task, block=block, timeout=timeout)
            with self.lock:
                self.tasks_by_priority[priority] += 1
            return True
        except queue.Full:
            return False
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """Get highest priority task."""
        priority_task = self.queue.get(block=block, timeout=timeout)
        return priority_task.task
    
    def size(self) -> int:
        return self.queue.qsize()
    
    def get_priority_distribution(self):
        """Get distribution of tasks by priority."""
        with self.lock:
            return dict(self.tasks_by_priority)


# Usage example:
"""
# In pipeline:
priority_queue = PriorityManagedQueue("ocr_tasks", maxsize=100)

# Critical: User clicked on text
priority_queue.put(ocr_task, priority=TaskPriority.CRITICAL)

# Normal: Background region scanning
priority_queue.put(ocr_task, priority=TaskPriority.NORMAL)

# Low: Prefetch next frame
priority_queue.put(ocr_task, priority=TaskPriority.LOW)
"""
