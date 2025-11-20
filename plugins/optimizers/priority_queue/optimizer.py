"""
Priority Queue Optimizer Plugin
Prioritizes user-triggered tasks over automatic captures
"""

import time
import heapq
import threading
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field


@dataclass(order=True)
class PriorityItem:
    """Item in priority queue"""
    priority: int
    timestamp: float = field(compare=False)
    data: Dict[str, Any] = field(compare=False)
    age_boost: int = field(default=0, compare=False)


class PriorityQueueOptimizer:
    """Priority-based task scheduling"""
    
    # Priority levels
    PRIORITY_CRITICAL = 0
    PRIORITY_HIGH = 10
    PRIORITY_NORMAL = 50
    PRIORITY_LOW = 100
    PRIORITY_BACKGROUND = 200
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enable_priorities = config.get('enable_priorities', True)
        self.high_priority_boost = config.get('high_priority_boost', 10)
        self.max_queue_size = config.get('max_queue_size', 100)
        self.starvation_prevention = config.get('starvation_prevention', True)
        
        # Priority queue (min-heap)
        self.queue: List[PriorityItem] = []
        self.lock = threading.Lock()
        
        # Statistics
        self.total_enqueued = 0
        self.total_dequeued = 0
        self.priority_counts = {
            'critical': 0,
            'high': 0,
            'normal': 0,
            'low': 0,
            'background': 0
        }
    
    def _get_priority_level(self, priority: int) -> str:
        """Get priority level name"""
        if priority <= self.PRIORITY_CRITICAL:
            return 'critical'
        elif priority <= self.PRIORITY_HIGH:
            return 'high'
        elif priority <= self.PRIORITY_NORMAL:
            return 'normal'
        elif priority <= self.PRIORITY_LOW:
            return 'low'
        else:
            return 'background'
    
    def _apply_age_boost(self, item: PriorityItem) -> int:
        """Apply age-based priority boost to prevent starvation"""
        if not self.starvation_prevention:
            return item.priority
        
        # Calculate age in seconds
        age = time.time() - item.timestamp
        
        # Boost priority based on age (1 point per second)
        age_boost = int(age)
        
        # Apply boost (lower number = higher priority)
        boosted_priority = max(0, item.priority - age_boost)
        
        return boosted_priority
    
    def enqueue(self, data: Dict[str, Any], priority: int = None) -> bool:
        """Add item to priority queue"""
        if not self.enable_priorities:
            priority = self.PRIORITY_NORMAL
        
        # Determine priority from data if not specified
        if priority is None:
            if data.get('user_triggered', False):
                priority = self.PRIORITY_HIGH
            elif data.get('background_task', False):
                priority = self.PRIORITY_BACKGROUND
            else:
                priority = self.PRIORITY_NORMAL
        
        with self.lock:
            # Check queue size
            if len(self.queue) >= self.max_queue_size:
                return False
            
            # Create priority item
            item = PriorityItem(
                priority=priority,
                timestamp=time.time(),
                data=data
            )
            
            # Add to heap
            heapq.heappush(self.queue, item)
            
            # Update statistics
            self.total_enqueued += 1
            level = self._get_priority_level(priority)
            self.priority_counts[level] += 1
            
            return True
    
    def dequeue(self, timeout: float = None) -> Dict[str, Any]:
        """Get highest priority item from queue"""
        start_time = time.time()
        
        while True:
            with self.lock:
                if self.queue:
                    # Get item with highest priority (lowest number)
                    item = heapq.heappop(self.queue)
                    
                    # Apply age boost if enabled
                    if self.starvation_prevention:
                        boosted_priority = self._apply_age_boost(item)
                        if boosted_priority < item.priority:
                            # Re-insert with boosted priority
                            item.priority = boosted_priority
                            heapq.heappush(self.queue, item)
                            continue
                    
                    # Update statistics
                    self.total_dequeued += 1
                    
                    # Add priority info to data
                    item.data['queue_priority'] = item.priority
                    item.data['queue_wait_time'] = time.time() - item.timestamp
                    
                    return item.data
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None
            
            # Small sleep to avoid busy waiting
            time.sleep(0.001)
    
    def peek(self) -> Dict[str, Any]:
        """Peek at highest priority item without removing"""
        with self.lock:
            if self.queue:
                return self.queue[0].data
            return None
    
    def size(self) -> int:
        """Get queue size"""
        with self.lock:
            return len(self.queue)
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with priority"""
        # Determine priority
        priority = data.get('priority', self.PRIORITY_NORMAL)
        
        # Add to queue
        enqueued = self.enqueue(data, priority)
        
        data['priority_queued'] = enqueued
        data['priority_level'] = self._get_priority_level(priority)
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get priority queue statistics"""
        with self.lock:
            queue_size = len(self.queue)
            
            # Calculate average wait time
            if self.queue:
                current_time = time.time()
                wait_times = [current_time - item.timestamp for item in self.queue]
                avg_wait = sum(wait_times) / len(wait_times)
            else:
                avg_wait = 0.0
        
        return {
            'total_enqueued': self.total_enqueued,
            'total_dequeued': self.total_dequeued,
            'current_size': queue_size,
            'avg_wait_time': f"{avg_wait * 1000:.1f}ms",
            'priority_counts': self.priority_counts.copy()
        }
    
    def clear(self):
        """Clear queue"""
        with self.lock:
            self.queue.clear()
            self.total_enqueued = 0
            self.total_dequeued = 0
            self.priority_counts = {k: 0 for k in self.priority_counts}


# Plugin interface
def initialize(config: Dict[str, Any]) -> PriorityQueueOptimizer:
    """Initialize the optimizer plugin"""
    return PriorityQueueOptimizer(config)
