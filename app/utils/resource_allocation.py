"""
Intelligent Resource Allocation and Scheduling System

This module provides adaptive frame rate control, priority-based task scheduling,
resource usage prediction, dynamic quality adjustment, background task scheduling,
and system load balancing between capture, OCR, translation, and overlay components.
"""

import logging
import threading
import time
import queue
import psutil
from typing import Dict, Any, Optional, List, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from abc import ABC, abstractmethod
import statistics
from collections import deque, defaultdict

from ..models import PerformanceProfile, RuntimeMode, PerformanceMetrics


class TaskPriority(IntEnum):
    """Task priority levels for scheduling."""
    CRITICAL = 1    # System-critical tasks (error handling, shutdown)
    HIGH = 2        # Real-time tasks (capture, overlay updates)
    NORMAL = 3      # Standard processing (OCR, translation)
    LOW = 4         # Background tasks (caching, cleanup)
    IDLE = 5        # Maintenance tasks (garbage collection, logging)


class ResourceType(Enum):
    """Types of system resources."""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK = "network"


class ComponentType(Enum):
    """System component types for load balancing."""
    CAPTURE = "capture"
    PREPROCESSING = "preprocessing"
    OCR = "ocr"
    TRANSLATION = "translation"
    OVERLAY = "overlay"
    BACKGROUND = "background"


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    cpu_percent: float = 0.0
    gpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_io_percent: float = 0.0
    network_percent: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskInfo:
    """Information about a scheduled task."""
    task_id: str
    priority: TaskPriority
    component_type: ComponentType
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    estimated_duration: float = 0.1  # seconds
    resource_requirements: Dict[ResourceType, float] = field(default_factory=dict)
    created_time: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ComponentLoadInfo:
    """Load information for a system component."""
    component_type: ComponentType
    current_load: float = 0.0  # 0.0 to 1.0
    average_load: float = 0.0
    peak_load: float = 0.0
    task_queue_size: int = 0
    processing_time_ms: float = 0.0
    last_update: float = field(default_factory=time.time)


@dataclass
class QualitySettings:
    """Dynamic quality adjustment settings."""
    capture_fps: int = 30
    capture_resolution_scale: float = 1.0
    ocr_quality_level: str = "balanced"  # fast, balanced, high
    translation_batch_size: int = 3
    overlay_update_rate: int = 30
    preprocessing_enabled: bool = True
    frame_differencing_enabled: bool = True


class AdaptiveFrameRateController:
    """
    Adaptive frame rate controller that adjusts based on system load.
    Monitors system performance and dynamically adjusts capture frame rate
    to maintain optimal performance while preserving quality.
    """
    
    def __init__(self, target_fps: int = 30, min_fps: int = 10, max_fps: int = 60):
        self.logger = logging.getLogger(__name__)
        self.target_fps = target_fps
        self.min_fps = min_fps
        self.max_fps = max_fps
        self.current_fps = target_fps
        
        # Performance tracking
        self.frame_times = deque(maxlen=100)
        self.processing_times = deque(maxlen=50)
        self.system_load_history = deque(maxlen=30)
        
        # Adjustment parameters
        self.adjustment_threshold = 0.1  # 10% change threshold
        self.load_threshold_high = 80.0  # High system load threshold
        self.load_threshold_low = 40.0   # Low system load threshold
        
        # State tracking
        self.last_adjustment_time = time.time()
        self.adjustment_cooldown = 2.0  # seconds
        self.performance_trend = 0.0  # -1 to 1, negative means degrading
        
        self.lock = threading.Lock()
    
    def record_frame_time(self, frame_time: float):
        """Record frame processing time for analysis."""
        with self.lock:
            self.frame_times.append(frame_time)
    
    def record_processing_time(self, processing_time: float):
        """Record total processing time for a frame."""
        with self.lock:
            self.processing_times.append(processing_time)
    
    def record_system_load(self, cpu_percent: float, memory_percent: float, gpu_percent: float = 0.0):
        """Record current system load metrics."""
        with self.lock:
            combined_load = (cpu_percent + memory_percent + gpu_percent) / 3.0
            self.system_load_history.append(combined_load)
    
    def get_recommended_fps(self) -> int:
        """Get recommended FPS based on current system performance."""
        with self.lock:
            if not self._should_adjust():
                return self.current_fps
            
            # Calculate performance metrics
            avg_system_load = self._get_average_system_load()
            processing_efficiency = self._calculate_processing_efficiency()
            performance_trend = self._calculate_performance_trend()
            
            # Determine adjustment direction and magnitude
            adjustment_factor = self._calculate_adjustment_factor(
                avg_system_load, processing_efficiency, performance_trend
            )
            
            # Apply adjustment
            new_fps = max(self.min_fps, min(self.max_fps, 
                         int(self.current_fps * adjustment_factor)))
            
            if new_fps != self.current_fps:
                self.logger.info(
                    f"Adjusting FPS: {self.current_fps} -> {new_fps} "
                    f"(load: {avg_system_load:.1f}%, efficiency: {processing_efficiency:.2f})"
                )
                self.current_fps = new_fps
                self.last_adjustment_time = time.time()
            
            return self.current_fps
    
    def _should_adjust(self) -> bool:
        """Check if FPS adjustment should be considered."""
        # Cooldown period
        if time.time() - self.last_adjustment_time < self.adjustment_cooldown:
            return False
        
        # Need sufficient data
        return len(self.system_load_history) >= 5 and len(self.processing_times) >= 5
    
    def _get_average_system_load(self) -> float:
        """Calculate average system load over recent history."""
        if not self.system_load_history:
            return 0.0
        return statistics.mean(self.system_load_history)
    
    def _calculate_processing_efficiency(self) -> float:
        """Calculate processing efficiency (0.0 to 1.0)."""
        if not self.processing_times:
            return 1.0
        
        target_frame_time = 1.0 / self.current_fps
        avg_processing_time = statistics.mean(self.processing_times)
        
        # Efficiency is inverse of processing time relative to target
        efficiency = min(1.0, target_frame_time / max(avg_processing_time, 0.001))
        return efficiency
    
    def _calculate_performance_trend(self) -> float:
        """Calculate performance trend (-1 to 1, negative means degrading)."""
        if len(self.processing_times) < 10:
            return 0.0
        
        # Compare recent vs older processing times
        recent_times = list(self.processing_times)[-5:]
        older_times = list(self.processing_times)[-10:-5]
        
        recent_avg = statistics.mean(recent_times)
        older_avg = statistics.mean(older_times)
        
        # Negative trend means processing is getting slower (worse)
        if older_avg == 0:
            return 0.0
        
        trend = (older_avg - recent_avg) / older_avg
        return max(-1.0, min(1.0, trend))
    
    def _calculate_adjustment_factor(self, system_load: float, efficiency: float, trend: float) -> float:
        """Calculate FPS adjustment factor based on performance metrics."""
        base_factor = 1.0
        
        # System load based adjustment
        if system_load > self.load_threshold_high:
            # High load - reduce FPS
            load_factor = 0.8 - (system_load - self.load_threshold_high) * 0.01
            base_factor *= max(0.5, load_factor)
        elif system_load < self.load_threshold_low:
            # Low load - potentially increase FPS
            load_factor = 1.1 + (self.load_threshold_low - system_load) * 0.005
            base_factor *= min(1.3, load_factor)
        
        # Efficiency based adjustment
        if efficiency < 0.7:
            # Low efficiency - reduce FPS
            base_factor *= 0.85
        elif efficiency > 0.95:
            # High efficiency - potentially increase FPS
            base_factor *= 1.1
        
        # Trend based adjustment
        if trend < -0.3:
            # Degrading performance - reduce FPS
            base_factor *= 0.9
        elif trend > 0.3:
            # Improving performance - potentially increase FPS
            base_factor *= 1.05
        
        return base_factor
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get frame rate controller statistics."""
        with self.lock:
            return {
                'current_fps': self.current_fps,
                'target_fps': self.target_fps,
                'average_system_load': self._get_average_system_load(),
                'processing_efficiency': self._calculate_processing_efficiency(),
                'performance_trend': self._calculate_performance_trend(),
                'frame_count': len(self.frame_times),
                'last_adjustment': self.last_adjustment_time
            }


class PriorityTaskScheduler:
    """
    Priority-based task scheduler for time-critical operations.
    Manages task queues with different priority levels and ensures
    critical tasks are processed first while maintaining fairness.
    """
    
    def __init__(self, max_concurrent_tasks: int = 4):
        self.logger = logging.getLogger(__name__)
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Priority queues for different task priorities
        self.task_queues: Dict[TaskPriority, queue.PriorityQueue] = {
            priority: queue.PriorityQueue() for priority in TaskPriority
        }
        
        # Worker threads
        self.worker_threads: List[threading.Thread] = []
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Task tracking
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.completed_tasks: deque = deque(maxlen=1000)
        self.failed_tasks: deque = deque(maxlen=100)
        
        # Statistics
        self.task_stats = defaultdict(lambda: {'count': 0, 'total_time': 0.0, 'failures': 0})
        self.lock = threading.RLock()
    
    def start(self):
        """Start the task scheduler."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.shutdown_event.clear()
            
            # Start worker threads
            for i in range(self.max_concurrent_tasks):
                thread = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskScheduler-Worker-{i}",
                    daemon=True
                )
                thread.start()
                self.worker_threads.append(thread)
            
            self.logger.info(f"Task scheduler started with {self.max_concurrent_tasks} workers")
    
    def stop(self, timeout: float = 5.0):
        """Stop the task scheduler."""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            self.shutdown_event.set()
            
            # Wait for worker threads to finish
            for thread in self.worker_threads:
                thread.join(timeout=timeout)
            
            self.worker_threads.clear()
            self.logger.info("Task scheduler stopped")
    
    def schedule_task(self, task: TaskInfo) -> bool:
        """Schedule a task for execution."""
        try:
            if not self.running:
                self.logger.warning("Cannot schedule task - scheduler not running")
                return False
            
            # Add to appropriate priority queue
            priority_queue = self.task_queues[task.priority]
            
            # Use negative timestamp for FIFO within same priority
            priority_value = (task.priority.value, -task.created_time)
            priority_queue.put((priority_value, task))
            
            with self.lock:
                self.active_tasks[task.task_id] = task
            
            self.logger.debug(f"Scheduled task {task.task_id} with priority {task.priority.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule task {task.task_id}: {e}")
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self.lock:
            if task_id in self.active_tasks:
                # Mark task as cancelled (worker will check this)
                task = self.active_tasks[task_id]
                task.kwargs['_cancelled'] = True
                return True
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        with self.lock:
            queue_sizes = {}
            for priority, task_queue in self.task_queues.items():
                queue_sizes[priority.name] = task_queue.qsize()
            
            return {
                'running': self.running,
                'active_tasks': len(self.active_tasks),
                'queue_sizes': queue_sizes,
                'completed_tasks': len(self.completed_tasks),
                'failed_tasks': len(self.failed_tasks),
                'worker_threads': len(self.worker_threads),
                'task_statistics': dict(self.task_stats)
            }
    
    def _worker_loop(self):
        """Main worker loop for processing tasks."""
        self.logger.debug(f"Worker thread {threading.current_thread().name} started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                task = self._get_next_task(timeout=1.0)
                if task is None:
                    continue
                
                # Check if task was cancelled
                if task.kwargs.get('_cancelled', False):
                    self._complete_task(task, success=False, error="Task cancelled")
                    continue
                
                # Execute task
                self._execute_task(task)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
        
        self.logger.debug(f"Worker thread {threading.current_thread().name} stopped")
    
    def _get_next_task(self, timeout: float = 1.0) -> Optional[TaskInfo]:
        """Get the next task to execute based on priority."""
        # Check queues in priority order
        for priority in TaskPriority:
            task_queue = self.task_queues[priority]
            try:
                if not task_queue.empty():
                    _, task = task_queue.get_nowait()
                    return task
            except queue.Empty:
                continue
        
        return None
    
    def _execute_task(self, task: TaskInfo):
        """Execute a task and handle results."""
        start_time = time.time()
        
        try:
            # Check deadline
            if task.deadline and time.time() > task.deadline:
                self._complete_task(task, success=False, error="Task deadline exceeded")
                return
            
            # Execute the task function
            result = task.function(*task.args, **task.kwargs)
            
            execution_time = time.time() - start_time
            self._complete_task(task, success=True, execution_time=execution_time, result=result)
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Task {task.task_id} failed: {e}")
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                self.logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
                self.schedule_task(task)
            else:
                self._complete_task(task, success=False, execution_time=execution_time, error=str(e))
    
    def _complete_task(self, task: TaskInfo, success: bool, execution_time: float = 0.0, 
                      result: Any = None, error: str = None):
        """Mark task as completed and update statistics."""
        with self.lock:
            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            # Update statistics
            component_stats = self.task_stats[task.component_type.value]
            component_stats['count'] += 1
            component_stats['total_time'] += execution_time
            
            if success:
                self.completed_tasks.append({
                    'task_id': task.task_id,
                    'component_type': task.component_type.value,
                    'priority': task.priority.name,
                    'execution_time': execution_time,
                    'completed_at': time.time(),
                    'result': result
                })
            else:
                component_stats['failures'] += 1
                self.failed_tasks.append({
                    'task_id': task.task_id,
                    'component_type': task.component_type.value,
                    'priority': task.priority.name,
                    'error': error,
                    'failed_at': time.time(),
                    'retry_count': task.retry_count
                })


class ResourceUsagePredictor:
    """
    Resource usage prediction and preemptive optimization.
    Analyzes historical resource usage patterns to predict future needs
    and proactively adjust system configuration.
    """
    
    def __init__(self, history_size: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.history_size = history_size
        
        # Resource usage history
        self.usage_history: deque = deque(maxlen=history_size)
        self.component_usage: Dict[ComponentType, deque] = {
            component: deque(maxlen=100) for component in ComponentType
        }
        
        # Prediction models (simplified)
        self.prediction_window = 30  # seconds
        self.trend_analysis_window = 300  # 5 minutes
        
        # Thresholds for optimization triggers
        self.cpu_threshold_high = 85.0
        self.memory_threshold_high = 90.0
        self.gpu_threshold_high = 95.0
        
        self.lock = threading.Lock()
    
    def record_usage(self, usage: ResourceUsage, component_loads: Dict[ComponentType, float]):
        """Record current resource usage and component loads."""
        with self.lock:
            self.usage_history.append(usage)
            
            for component_type, load in component_loads.items():
                if component_type in self.component_usage:
                    self.component_usage[component_type].append({
                        'load': load,
                        'timestamp': usage.timestamp
                    })
    
    def predict_resource_usage(self, prediction_seconds: float = 30.0) -> ResourceUsage:
        """Predict resource usage for the next N seconds."""
        with self.lock:
            if len(self.usage_history) < 10:
                # Not enough data for prediction
                return ResourceUsage()
            
            # Simple trend-based prediction
            recent_usage = list(self.usage_history)[-10:]
            
            # Calculate trends
            cpu_trend = self._calculate_trend([u.cpu_percent for u in recent_usage])
            gpu_trend = self._calculate_trend([u.gpu_percent for u in recent_usage])
            memory_trend = self._calculate_trend([u.memory_percent for u in recent_usage])
            
            # Current values
            current = recent_usage[-1]
            
            # Predict future values
            predicted_cpu = max(0, min(100, current.cpu_percent + cpu_trend * prediction_seconds))
            predicted_gpu = max(0, min(100, current.gpu_percent + gpu_trend * prediction_seconds))
            predicted_memory = max(0, min(100, current.memory_percent + memory_trend * prediction_seconds))
            
            return ResourceUsage(
                cpu_percent=predicted_cpu,
                gpu_percent=predicted_gpu,
                memory_percent=predicted_memory,
                disk_io_percent=current.disk_io_percent,  # Assume stable
                network_percent=current.network_percent,  # Assume stable
                timestamp=time.time() + prediction_seconds
            )
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on usage patterns."""
        recommendations = []
        
        with self.lock:
            if len(self.usage_history) < 5:
                return recommendations
            
            # Analyze recent usage
            recent_usage = list(self.usage_history)[-5:]
            avg_cpu = statistics.mean([u.cpu_percent for u in recent_usage])
            avg_memory = statistics.mean([u.memory_percent for u in recent_usage])
            avg_gpu = statistics.mean([u.gpu_percent for u in recent_usage])
            
            # CPU optimization recommendations
            if avg_cpu > self.cpu_threshold_high:
                recommendations.append({
                    'type': 'cpu_optimization',
                    'priority': 'high',
                    'description': 'High CPU usage detected',
                    'actions': [
                        'Reduce capture frame rate',
                        'Disable non-essential preprocessing',
                        'Switch to faster OCR mode',
                        'Reduce translation batch size'
                    ],
                    'expected_improvement': '15-25% CPU reduction'
                })
            
            # Memory optimization recommendations
            if avg_memory > self.memory_threshold_high:
                recommendations.append({
                    'type': 'memory_optimization',
                    'priority': 'high',
                    'description': 'High memory usage detected',
                    'actions': [
                        'Clear translation cache',
                        'Reduce image resolution',
                        'Limit concurrent processing',
                        'Enable aggressive garbage collection'
                    ],
                    'expected_improvement': '10-20% memory reduction'
                })
            
            # GPU optimization recommendations
            if avg_gpu > self.gpu_threshold_high:
                recommendations.append({
                    'type': 'gpu_optimization',
                    'priority': 'medium',
                    'description': 'High GPU usage detected',
                    'actions': [
                        'Reduce GPU batch sizes',
                        'Switch some operations to CPU',
                        'Lower GPU precision if supported'
                    ],
                    'expected_improvement': '10-15% GPU reduction'
                })
            
            # Component-specific recommendations
            component_recommendations = self._analyze_component_usage()
            recommendations.extend(component_recommendations)
        
        return recommendations
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (change per second) from a list of values."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * values[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _analyze_component_usage(self) -> List[Dict[str, Any]]:
        """Analyze component-specific usage patterns."""
        recommendations = []
        
        for component_type, usage_data in self.component_usage.items():
            if len(usage_data) < 5:
                continue
            
            recent_loads = [data['load'] for data in list(usage_data)[-5:]]
            avg_load = statistics.mean(recent_loads)
            
            if avg_load > 0.8:  # 80% load threshold
                recommendations.append({
                    'type': 'component_optimization',
                    'component': component_type.value,
                    'priority': 'medium',
                    'description': f'High load detected in {component_type.value} component',
                    'current_load': avg_load,
                    'actions': self._get_component_optimization_actions(component_type),
                    'expected_improvement': f'Reduce {component_type.value} load by 20-30%'
                })
        
        return recommendations
    
    def _get_component_optimization_actions(self, component_type: ComponentType) -> List[str]:
        """Get optimization actions for specific component types."""
        actions_map = {
            ComponentType.CAPTURE: [
                'Reduce capture frame rate',
                'Lower capture resolution',
                'Enable frame differencing',
                'Optimize capture region'
            ],
            ComponentType.OCR: [
                'Switch to faster OCR engine',
                'Reduce OCR quality settings',
                'Enable OCR result caching',
                'Optimize text region detection'
            ],
            ComponentType.TRANSLATION: [
                'Increase translation batch size',
                'Enable translation caching',
                'Use faster translation model',
                'Reduce translation frequency'
            ],
            ComponentType.OVERLAY: [
                'Reduce overlay update rate',
                'Simplify overlay rendering',
                'Cache overlay elements',
                'Optimize text positioning'
            ],
            ComponentType.PREPROCESSING: [
                'Disable non-essential filters',
                'Reduce preprocessing quality',
                'Enable ROI-based processing',
                'Optimize image scaling'
            ]
        }
        
        return actions_map.get(component_type, ['Optimize component configuration'])


class DynamicQualityAdjuster:
    """
    Dynamic quality adjustment based on performance metrics.
    Automatically adjusts quality settings to maintain target performance
    while preserving user experience as much as possible.
    """
    
    def __init__(self, target_fps: int = 30, target_latency_ms: float = 100.0):
        self.logger = logging.getLogger(__name__)
        self.target_fps = target_fps
        self.target_latency_ms = target_latency_ms
        
        # Current quality settings
        self.current_settings = QualitySettings()
        self.baseline_settings = QualitySettings()
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=50)
        self.adjustment_history: deque = deque(maxlen=20)
        
        # Adjustment parameters
        self.adjustment_threshold = 0.15  # 15% performance deviation
        self.min_adjustment_interval = 5.0  # seconds
        self.last_adjustment_time = 0.0
        
        # Quality level mappings
        self.quality_levels = {
            'fast': {'ocr_accuracy': 0.7, 'processing_speed': 1.5},
            'balanced': {'ocr_accuracy': 0.85, 'processing_speed': 1.0},
            'high': {'ocr_accuracy': 0.95, 'processing_speed': 0.6}
        }
        
        self.lock = threading.Lock()
    
    def record_performance(self, metrics: PerformanceMetrics):
        """Record current performance metrics."""
        with self.lock:
            self.performance_history.append({
                'fps': metrics.fps,
                'latency_ms': metrics.latency_ms,
                'cpu_usage': metrics.cpu_usage,
                'memory_usage': metrics.memory_usage,
                'timestamp': time.time()
            })
    
    def get_adjusted_settings(self) -> QualitySettings:
        """Get quality settings adjusted for current performance."""
        with self.lock:
            if not self._should_adjust():
                return self.current_settings
            
            # Analyze performance
            performance_score = self._calculate_performance_score()
            adjustment_needed = self._determine_adjustment_needed(performance_score)
            
            if adjustment_needed != 0:
                self._apply_quality_adjustment(adjustment_needed)
                self.last_adjustment_time = time.time()
                
                self.adjustment_history.append({
                    'adjustment': adjustment_needed,
                    'performance_score': performance_score,
                    'timestamp': time.time(),
                    'settings': self._settings_to_dict(self.current_settings)
                })
            
            return self.current_settings
    
    def reset_to_baseline(self):
        """Reset quality settings to baseline."""
        with self.lock:
            self.current_settings = QualitySettings()
            self.baseline_settings = QualitySettings()
            self.logger.info("Quality settings reset to baseline")
    
    def _should_adjust(self) -> bool:
        """Check if quality adjustment should be considered."""
        # Need sufficient performance data
        if len(self.performance_history) < 5:
            return False
        
        # Respect minimum adjustment interval
        if time.time() - self.last_adjustment_time < self.min_adjustment_interval:
            return False
        
        return True
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0.0 to 1.0, higher is better)."""
        if not self.performance_history:
            return 1.0
        
        recent_metrics = list(self.performance_history)[-5:]
        
        # Calculate average metrics
        avg_fps = statistics.mean([m['fps'] for m in recent_metrics])
        avg_latency = statistics.mean([m['latency_ms'] for m in recent_metrics])
        avg_cpu = statistics.mean([m['cpu_usage'] for m in recent_metrics])
        
        # Calculate individual scores
        fps_score = min(1.0, avg_fps / self.target_fps)
        latency_score = max(0.0, 1.0 - (avg_latency - self.target_latency_ms) / self.target_latency_ms)
        cpu_score = max(0.0, 1.0 - avg_cpu / 100.0)
        
        # Weighted overall score
        overall_score = (fps_score * 0.4 + latency_score * 0.4 + cpu_score * 0.2)
        return max(0.0, min(1.0, overall_score))
    
    def _determine_adjustment_needed(self, performance_score: float) -> int:
        """Determine if quality adjustment is needed (-1: reduce, 0: no change, 1: increase)."""
        if performance_score < (1.0 - self.adjustment_threshold):
            # Performance is poor, reduce quality
            return -1
        elif performance_score > (1.0 + self.adjustment_threshold * 0.5):
            # Performance is excellent, potentially increase quality
            return 1
        else:
            # Performance is acceptable
            return 0
    
    def _apply_quality_adjustment(self, adjustment: int):
        """Apply quality adjustment to current settings."""
        if adjustment == -1:
            # Reduce quality for better performance
            self._reduce_quality()
        elif adjustment == 1:
            # Increase quality if performance allows
            self._increase_quality()
    
    def _reduce_quality(self):
        """Reduce quality settings to improve performance."""
        settings = self.current_settings
        
        # Reduce capture settings
        if settings.capture_fps > 15:
            settings.capture_fps = max(15, int(settings.capture_fps * 0.8))
            self.logger.info(f"Reduced capture FPS to {settings.capture_fps}")
        
        if settings.capture_resolution_scale > 0.5:
            settings.capture_resolution_scale = max(0.5, settings.capture_resolution_scale * 0.9)
            self.logger.info(f"Reduced capture resolution scale to {settings.capture_resolution_scale:.2f}")
        
        # Switch to faster OCR mode
        if settings.ocr_quality_level == "high":
            settings.ocr_quality_level = "balanced"
            self.logger.info("Switched OCR quality to balanced")
        elif settings.ocr_quality_level == "balanced":
            settings.ocr_quality_level = "fast"
            self.logger.info("Switched OCR quality to fast")
        
        # Reduce translation batch size
        if settings.translation_batch_size > 1:
            settings.translation_batch_size = max(1, settings.translation_batch_size - 1)
            self.logger.info(f"Reduced translation batch size to {settings.translation_batch_size}")
        
        # Disable expensive features
        if settings.preprocessing_enabled:
            settings.preprocessing_enabled = False
            self.logger.info("Disabled preprocessing")
        
        if settings.frame_differencing_enabled:
            settings.frame_differencing_enabled = False
            self.logger.info("Disabled frame differencing")
    
    def _increase_quality(self):
        """Increase quality settings when performance allows."""
        settings = self.current_settings
        baseline = self.baseline_settings
        
        # Increase capture settings (but don't exceed baseline)
        if settings.capture_fps < baseline.capture_fps:
            settings.capture_fps = min(baseline.capture_fps, settings.capture_fps + 5)
            self.logger.info(f"Increased capture FPS to {settings.capture_fps}")
        
        if settings.capture_resolution_scale < baseline.capture_resolution_scale:
            settings.capture_resolution_scale = min(baseline.capture_resolution_scale, 
                                                  settings.capture_resolution_scale + 0.1)
            self.logger.info(f"Increased capture resolution scale to {settings.capture_resolution_scale:.2f}")
        
        # Switch to higher quality OCR mode
        if settings.ocr_quality_level == "fast":
            settings.ocr_quality_level = "balanced"
            self.logger.info("Switched OCR quality to balanced")
        elif settings.ocr_quality_level == "balanced" and baseline.ocr_quality_level == "high":
            settings.ocr_quality_level = "high"
            self.logger.info("Switched OCR quality to high")
        
        # Enable features if they were disabled
        if not settings.preprocessing_enabled and baseline.preprocessing_enabled:
            settings.preprocessing_enabled = True
            self.logger.info("Enabled preprocessing")
        
        if not settings.frame_differencing_enabled and baseline.frame_differencing_enabled:
            settings.frame_differencing_enabled = True
            self.logger.info("Enabled frame differencing")
    
    def _settings_to_dict(self, settings: QualitySettings) -> Dict[str, Any]:
        """Convert quality settings to dictionary."""
        return {
            'capture_fps': settings.capture_fps,
            'capture_resolution_scale': settings.capture_resolution_scale,
            'ocr_quality_level': settings.ocr_quality_level,
            'translation_batch_size': settings.translation_batch_size,
            'overlay_update_rate': settings.overlay_update_rate,
            'preprocessing_enabled': settings.preprocessing_enabled,
            'frame_differencing_enabled': settings.frame_differencing_enabled
        }
    
    def get_adjustment_history(self) -> List[Dict[str, Any]]:
        """Get history of quality adjustments."""
        with self.lock:
            return list(self.adjustment_history)


class BackgroundTaskScheduler:
    """
    Background task scheduling for non-critical operations.
    Manages low-priority tasks that should run when system resources are available.
    """
    
    def __init__(self, max_background_threads: int = 2):
        self.logger = logging.getLogger(__name__)
        self.max_background_threads = max_background_threads
        
        # Task management
        self.background_queue: queue.Queue = queue.Queue()
        self.periodic_tasks: Dict[str, Dict[str, Any]] = {}
        self.worker_threads: List[threading.Thread] = []
        
        # Control
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Resource monitoring
        self.resource_threshold = 70.0  # Don't run background tasks if system load > 70%
        self.check_interval = 5.0  # Check system load every 5 seconds
        
        self.lock = threading.Lock()
    
    def start(self):
        """Start the background task scheduler."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.shutdown_event.clear()
            
            # Start worker threads
            for i in range(self.max_background_threads):
                thread = threading.Thread(
                    target=self._background_worker,
                    name=f"BackgroundScheduler-{i}",
                    daemon=True
                )
                thread.start()
                self.worker_threads.append(thread)
            
            # Start periodic task scheduler
            scheduler_thread = threading.Thread(
                target=self._periodic_scheduler,
                name="BackgroundScheduler-Periodic",
                daemon=True
            )
            scheduler_thread.start()
            self.worker_threads.append(scheduler_thread)
            
            self.logger.info(f"Background task scheduler started with {self.max_background_threads} workers")
    
    def stop(self, timeout: float = 5.0):
        """Stop the background task scheduler."""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            self.shutdown_event.set()
            
            # Wait for worker threads
            for thread in self.worker_threads:
                thread.join(timeout=timeout)
            
            self.worker_threads.clear()
            self.logger.info("Background task scheduler stopped")
    
    def schedule_background_task(self, task_function: Callable, *args, **kwargs):
        """Schedule a one-time background task."""
        if not self.running:
            self.logger.warning("Cannot schedule background task - scheduler not running")
            return
        
        task_info = {
            'type': 'one_time',
            'function': task_function,
            'args': args,
            'kwargs': kwargs,
            'scheduled_at': time.time()
        }
        
        self.background_queue.put(task_info)
        self.logger.debug(f"Scheduled background task: {task_function.__name__}")
    
    def schedule_periodic_task(self, task_id: str, task_function: Callable, 
                             interval_seconds: float, *args, **kwargs):
        """Schedule a periodic background task."""
        with self.lock:
            self.periodic_tasks[task_id] = {
                'function': task_function,
                'interval': interval_seconds,
                'args': args,
                'kwargs': kwargs,
                'last_run': 0.0,
                'next_run': time.time() + interval_seconds
            }
        
        self.logger.info(f"Scheduled periodic task {task_id} with {interval_seconds}s interval")
    
    def cancel_periodic_task(self, task_id: str) -> bool:
        """Cancel a periodic background task."""
        with self.lock:
            if task_id in self.periodic_tasks:
                del self.periodic_tasks[task_id]
                self.logger.info(f"Cancelled periodic task: {task_id}")
                return True
            return False
    
    def _background_worker(self):
        """Background task worker thread."""
        self.logger.debug(f"Background worker {threading.current_thread().name} started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Check system load before processing tasks
                if not self._should_run_background_tasks():
                    time.sleep(self.check_interval)
                    continue
                
                # Get next task
                try:
                    task_info = self.background_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Execute task
                self._execute_background_task(task_info)
                
            except Exception as e:
                self.logger.error(f"Error in background worker: {e}")
        
        self.logger.debug(f"Background worker {threading.current_thread().name} stopped")
    
    def _periodic_scheduler(self):
        """Periodic task scheduler thread."""
        self.logger.debug("Periodic task scheduler started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                with self.lock:
                    for task_id, task_info in self.periodic_tasks.items():
                        if current_time >= task_info['next_run']:
                            # Schedule the periodic task
                            self.schedule_background_task(
                                task_info['function'],
                                *task_info['args'],
                                **task_info['kwargs']
                            )
                            
                            # Update next run time
                            task_info['last_run'] = current_time
                            task_info['next_run'] = current_time + task_info['interval']
                
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in periodic scheduler: {e}")
        
        self.logger.debug("Periodic task scheduler stopped")
    
    def _should_run_background_tasks(self) -> bool:
        """Check if background tasks should run based on system load."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            
            # Don't run background tasks if system is under high load
            if cpu_percent > self.resource_threshold or memory_percent > self.resource_threshold:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check system load: {e}")
            return True  # Default to allowing background tasks
    
    def _execute_background_task(self, task_info: Dict[str, Any]):
        """Execute a background task."""
        try:
            function = task_info['function']
            args = task_info.get('args', ())
            kwargs = task_info.get('kwargs', {})
            
            start_time = time.time()
            result = function(*args, **kwargs)
            execution_time = time.time() - start_time
            
            self.logger.debug(f"Background task {function.__name__} completed in {execution_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Background task {function.__name__} failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get background scheduler status."""
        with self.lock:
            return {
                'running': self.running,
                'queue_size': self.background_queue.qsize(),
                'periodic_tasks': len(self.periodic_tasks),
                'worker_threads': len(self.worker_threads),
                'resource_threshold': self.resource_threshold,
                'periodic_task_list': list(self.periodic_tasks.keys())
            }


# Export all classes
__all__ = [
    'TaskPriority',
    'ResourceType', 
    'ComponentType',
    'ResourceUsage',
    'TaskInfo',
    'ComponentLoadInfo',
    'QualitySettings',
    'AdaptiveFrameRateController',
    'PriorityTaskScheduler',
    'ResourceUsagePredictor',
    'DynamicQualityAdjuster',
    'BackgroundTaskScheduler'
]