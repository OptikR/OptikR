"""
OptikR Performance Monitoring System

Comprehensive performance monitoring system that collects real-time metrics
including FPS, CPU usage, GPU usage, memory usage, and latency measurements.
Provides historical data tracking, alert management, and optimization suggestions.
"""

import threading
import time
import psutil
import queue
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Tuple
from collections import deque
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from models import PerformanceMetrics, RuntimeMode, PerformanceProfile
    from interfaces import IPerformanceMonitor
except ImportError:
    # Handle case when running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app.models import PerformanceMetrics, RuntimeMode, PerformanceProfile
    from app.interfaces import IPerformanceMonitor

# Try to import GPU monitoring libraries
try:
    import GPUtil
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False

try:
    import nvidia_ml_py3 as nvml
    NVIDIA_ML_AVAILABLE = True
except ImportError:
    NVIDIA_ML_AVAILABLE = False


@dataclass
class PerformanceAlert:
    """Represents a performance alert with metadata and auto-fix capability."""
    alert_type: str
    severity: str  # critical, warning, info
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    threshold_value: float = 0.0
    current_value: float = 0.0
    auto_fix: Optional[Callable] = None
    dismissed: bool = False
    id: str = field(default="")
    
    def __post_init__(self):
        """Generate unique ID for alert."""
        if not self.id:
            self.id = f"{self.alert_type}_{int(self.timestamp.timestamp())}"


@dataclass
class OptimizationSuggestion:
    """Represents an optimization suggestion with impact assessment."""
    title: str
    description: str
    impact: str  # high, medium, low
    estimated_improvement: str
    action: Optional[Callable] = None
    category: str = "general"
    priority: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SystemResourceInfo:
    """Detailed system resource information."""
    cpu_count: int
    cpu_freq_current: float
    cpu_freq_max: float
    memory_total: float  # GB
    memory_available: float  # GB
    gpu_count: int
    gpu_memory_total: float  # GB
    gpu_memory_free: float  # GB
    disk_usage: float  # Percentage
    network_sent: float  # MB/s
    network_recv: float  # MB/s


class MetricsCollector:
    """Collects system performance metrics from various sources."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger(__name__)
        self.gpu_available = self._initialize_gpu_monitoring()
        self.baseline_metrics = self._collect_baseline_metrics()
        
        # Performance tracking
        self.frame_times = deque(maxlen=60)  # Last 60 frame times for FPS calculation
        self.processing_times = deque(maxlen=100)  # Processing latency tracking
        self.translation_count = 0
        self.error_count = 0
        self.last_reset_time = time.time()
        
        # Network monitoring
        self.network_io_start = psutil.net_io_counters()
        self.network_last_check = time.time()
    
    def _initialize_gpu_monitoring(self) -> bool:
        """Initialize GPU monitoring capabilities."""
        if NVIDIA_ML_AVAILABLE:
            try:
                nvml.nvmlInit()
                return True
            except Exception as e:
                self.logger.warning(f"Failed to initialize NVIDIA ML: {e}")
        
        if GPU_MONITORING_AVAILABLE:
            try:
                GPUtil.getGPUs()
                return True
            except Exception as e:
                self.logger.warning(f"Failed to initialize GPUtil: {e}")
        
        return False
    
    def _collect_baseline_metrics(self) -> Dict[str, float]:
        """Collect baseline system metrics for comparison."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            baseline = {
                'cpu_idle': 100 - cpu_percent,
                'memory_available': memory.available / (1024**3),  # GB
                'disk_io_read': psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
                'disk_io_write': psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0,
            }
            
            if self.gpu_available:
                gpu_info = self._get_gpu_metrics()
                baseline['gpu_memory_free'] = gpu_info.get('memory_free', 0)
            
            return baseline
        except Exception as e:
            self.logger.error(f"Failed to collect baseline metrics: {e}")
            return {}
    
    def collect_current_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_usage_mb = (memory.total - memory.available) / (1024**2)
            
            # GPU metrics
            gpu_usage = 0.0
            if self.gpu_available:
                gpu_metrics = self._get_gpu_metrics()
                gpu_usage = gpu_metrics.get('utilization', 0.0)
            
            # FPS calculation
            fps = self._calculate_fps()
            
            # Latency calculation
            latency_ms = self._calculate_average_latency()
            
            # Accuracy (placeholder - would be calculated from actual translation results)
            accuracy = self._calculate_accuracy()
            
            return PerformanceMetrics(
                fps=fps,
                cpu_usage=cpu_usage,
                gpu_usage=gpu_usage,
                memory_usage=memory_usage_mb,
                latency_ms=latency_ms,
                accuracy=accuracy,
                timestamp=time.time()
            )
        
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            # Return default metrics on error
            return PerformanceMetrics(
                fps=0.0,
                cpu_usage=0.0,
                gpu_usage=0.0,
                memory_usage=0.0,
                latency_ms=0.0,
                accuracy=0.0,
                timestamp=time.time()
            )
    
    def _get_gpu_metrics(self) -> Dict[str, float]:
        """Get GPU utilization and memory metrics."""
        gpu_metrics = {
            'utilization': 0.0,
            'memory_used': 0.0,
            'memory_total': 0.0,
            'memory_free': 0.0,
            'temperature': 0.0
        }
        
        try:
            if NVIDIA_ML_AVAILABLE:
                device_count = nvml.nvmlDeviceGetCount()
                if device_count > 0:
                    handle = nvml.nvmlDeviceGetHandleByIndex(0)  # Use first GPU
                    
                    # Utilization
                    util = nvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_metrics['utilization'] = util.gpu
                    
                    # Memory
                    mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu_metrics['memory_used'] = mem_info.used / (1024**2)  # MB
                    gpu_metrics['memory_total'] = mem_info.total / (1024**2)  # MB
                    gpu_metrics['memory_free'] = mem_info.free / (1024**2)  # MB
                    
                    # Temperature
                    temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
                    gpu_metrics['temperature'] = temp
            
            elif GPU_MONITORING_AVAILABLE:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]  # Use first GPU
                    gpu_metrics['utilization'] = gpu.load * 100
                    gpu_metrics['memory_used'] = gpu.memoryUsed
                    gpu_metrics['memory_total'] = gpu.memoryTotal
                    gpu_metrics['memory_free'] = gpu.memoryFree
                    gpu_metrics['temperature'] = gpu.temperature
        
        except Exception as e:
            self.logger.warning(f"Failed to get GPU metrics: {e}")
        
        return gpu_metrics
    
    def _calculate_fps(self) -> float:
        """Calculate current FPS based on recent frame times."""
        if len(self.frame_times) < 2:
            return 0.0
        
        # Calculate average time between frames
        total_time = sum(self.frame_times)
        if total_time == 0:
            return 0.0
        
        avg_frame_time = total_time / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def _calculate_average_latency(self) -> float:
        """Calculate average processing latency."""
        if not self.processing_times:
            return 0.0
        
        return sum(self.processing_times) / len(self.processing_times)
    
    def _calculate_accuracy(self) -> float:
        """Calculate translation accuracy percentage."""
        if self.translation_count == 0:
            return 100.0  # Default to 100% when no translations yet
        
        # Simple accuracy calculation based on error rate
        error_rate = self.error_count / self.translation_count
        return max(0.0, (1.0 - error_rate) * 100.0)
    
    def record_frame_time(self, frame_time: float):
        """Record frame processing time for FPS calculation."""
        self.frame_times.append(frame_time)
    
    def record_processing_time(self, processing_time: float):
        """Record processing latency."""
        self.processing_times.append(processing_time)
    
    def record_translation(self, success: bool = True):
        """Record translation attempt."""
        self.translation_count += 1
        if not success:
            self.error_count += 1
    
    def reset_counters(self):
        """Reset performance counters."""
        self.translation_count = 0
        self.error_count = 0
        self.last_reset_time = time.time()
    
    def get_system_resource_info(self) -> SystemResourceInfo:
        """Get detailed system resource information."""
        try:
            # CPU info
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            cpu_freq_current = cpu_freq.current if cpu_freq else 0.0
            cpu_freq_max = cpu_freq.max if cpu_freq else 0.0
            
            # Memory info
            memory = psutil.virtual_memory()
            memory_total = memory.total / (1024**3)  # GB
            memory_available = memory.available / (1024**3)  # GB
            
            # GPU info
            gpu_count = 0
            gpu_memory_total = 0.0
            gpu_memory_free = 0.0
            
            if self.gpu_available:
                gpu_metrics = self._get_gpu_metrics()
                gpu_count = 1  # Simplified - assume 1 GPU
                gpu_memory_total = gpu_metrics.get('memory_total', 0.0) / 1024  # GB
                gpu_memory_free = gpu_metrics.get('memory_free', 0.0) / 1024  # GB
            
            # Disk usage
            disk_usage = psutil.disk_usage('/').percent
            
            # Network I/O
            network_io = psutil.net_io_counters()
            current_time = time.time()
            time_delta = current_time - self.network_last_check
            
            if time_delta > 0:
                bytes_sent_delta = network_io.bytes_sent - self.network_io_start.bytes_sent
                bytes_recv_delta = network_io.bytes_recv - self.network_io_start.bytes_recv
                
                network_sent = (bytes_sent_delta / time_delta) / (1024**2)  # MB/s
                network_recv = (bytes_recv_delta / time_delta) / (1024**2)  # MB/s
            else:
                network_sent = network_recv = 0.0
            
            # Update network baseline
            self.network_io_start = network_io
            self.network_last_check = current_time
            
            return SystemResourceInfo(
                cpu_count=cpu_count,
                cpu_freq_current=cpu_freq_current,
                cpu_freq_max=cpu_freq_max,
                memory_total=memory_total,
                memory_available=memory_available,
                gpu_count=gpu_count,
                gpu_memory_total=gpu_memory_total,
                gpu_memory_free=gpu_memory_free,
                disk_usage=disk_usage,
                network_sent=network_sent,
                network_recv=network_recv
            )
        
        except Exception as e:
            self.logger.error(f"Failed to get system resource info: {e}")
            return SystemResourceInfo(
                cpu_count=0, cpu_freq_current=0.0, cpu_freq_max=0.0,
                memory_total=0.0, memory_available=0.0,
                gpu_count=0, gpu_memory_total=0.0, gpu_memory_free=0.0,
                disk_usage=0.0, network_sent=0.0, network_recv=0.0
            )


class AlertManager:
    """Manages performance alerts and notifications."""
    
    def __init__(self, alert_callback: Optional[Callable] = None):
        """Initialize alert manager.
        
        Args:
            alert_callback: Optional callback for alert notifications
        """
        self.logger = logging.getLogger(__name__)
        self.alert_callback = alert_callback
        self.alerts: List[PerformanceAlert] = []
        self.alert_thresholds: Dict[str, Dict[str, float]] = self._get_default_thresholds()
        self.alert_history: List[PerformanceAlert] = []
        self.max_history_size = 1000
        
        # Alert suppression to prevent spam
        self.alert_suppression: Dict[str, float] = {}
        self.suppression_duration = 60.0  # seconds
    
    def _get_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get default alert thresholds."""
        return {
            'cpu_usage': {'warning': 75.0, 'critical': 90.0},
            'gpu_usage': {'warning': 80.0, 'critical': 95.0},
            'memory_usage': {'warning': 12000.0, 'critical': 15000.0},  # MB
            'latency_ms': {'warning': 100.0, 'critical': 200.0},
            'fps': {'warning': 30.0, 'critical': 15.0},  # Lower is worse for FPS
            'accuracy': {'warning': 90.0, 'critical': 80.0},  # Lower is worse for accuracy
            'temperature': {'warning': 75.0, 'critical': 85.0}
        }
    
    def set_alert_thresholds(self, thresholds: Dict[str, float]):
        """Set custom alert thresholds."""
        for metric, threshold in thresholds.items():
            if metric in self.alert_thresholds:
                # Assume single threshold maps to warning level
                self.alert_thresholds[metric]['warning'] = threshold
    
    def check_metrics_for_alerts(self, metrics: PerformanceMetrics) -> List[PerformanceAlert]:
        """Check metrics against thresholds and generate alerts."""
        new_alerts = []
        current_time = time.time()
        
        # Check each metric against thresholds
        metric_checks = [
            ('cpu_usage', metrics.cpu_usage, False),
            ('gpu_usage', metrics.gpu_usage, False),
            ('memory_usage', metrics.memory_usage, False),
            ('latency_ms', metrics.latency_ms, False),
            ('fps', metrics.fps, True),  # Lower is worse
            ('accuracy', metrics.accuracy, True)  # Lower is worse
        ]
        
        for metric_name, value, lower_is_worse in metric_checks:
            thresholds = self.alert_thresholds.get(metric_name, {})
            
            # Check if alert should be suppressed
            suppression_key = f"{metric_name}_alert"
            if suppression_key in self.alert_suppression:
                if current_time - self.alert_suppression[suppression_key] < self.suppression_duration:
                    continue
            
            # Determine alert level
            alert_level = None
            threshold_value = 0.0
            
            if lower_is_worse:
                # For metrics where lower values are worse (FPS, accuracy)
                if 'critical' in thresholds and value <= thresholds['critical']:
                    alert_level = 'critical'
                    threshold_value = thresholds['critical']
                elif 'warning' in thresholds and value <= thresholds['warning']:
                    alert_level = 'warning'
                    threshold_value = thresholds['warning']
            else:
                # For metrics where higher values are worse (CPU, GPU, memory, latency)
                if 'critical' in thresholds and value >= thresholds['critical']:
                    alert_level = 'critical'
                    threshold_value = thresholds['critical']
                elif 'warning' in thresholds and value >= thresholds['warning']:
                    alert_level = 'warning'
                    threshold_value = thresholds['warning']
            
            # Create alert if threshold exceeded
            if alert_level:
                alert = PerformanceAlert(
                    alert_type=metric_name,
                    severity=alert_level,
                    message=self._generate_alert_message(metric_name, value, threshold_value, alert_level),
                    threshold_value=threshold_value,
                    current_value=value,
                    auto_fix=self._get_auto_fix_function(metric_name)
                )
                
                new_alerts.append(alert)
                self.alerts.append(alert)
                
                # Add to history
                self.alert_history.append(alert)
                if len(self.alert_history) > self.max_history_size:
                    self.alert_history.pop(0)
                
                # Set suppression
                self.alert_suppression[suppression_key] = current_time
                
                # Call notification callback
                if self.alert_callback:
                    try:
                        self.alert_callback(alert)
                    except Exception as e:
                        self.logger.error(f"Alert callback failed: {e}")
        
        return new_alerts
    
    def _generate_alert_message(self, metric_name: str, value: float, 
                              threshold: float, severity: str) -> str:
        """Generate human-readable alert message."""
        metric_display_names = {
            'cpu_usage': 'CPU Usage',
            'gpu_usage': 'GPU Usage',
            'memory_usage': 'Memory Usage',
            'latency_ms': 'Processing Latency',
            'fps': 'Frame Rate',
            'accuracy': 'Translation Accuracy',
            'temperature': 'GPU Temperature'
        }
        
        units = {
            'cpu_usage': '%',
            'gpu_usage': '%',
            'memory_usage': 'MB',
            'latency_ms': 'ms',
            'fps': 'FPS',
            'accuracy': '%',
            'temperature': '°C'
        }
        
        display_name = metric_display_names.get(metric_name, metric_name)
        unit = units.get(metric_name, '')
        
        if metric_name in ['fps', 'accuracy']:
            # Lower is worse
            return f"{display_name} below threshold: {value:.1f}{unit} (threshold: {threshold:.1f}{unit})"
        else:
            # Higher is worse
            return f"{display_name} above threshold: {value:.1f}{unit} (threshold: {threshold:.1f}{unit})"
    
    def _get_auto_fix_function(self, metric_name: str) -> Optional[Callable]:
        """Get auto-fix function for specific metric alert."""
        auto_fix_functions = {
            'cpu_usage': self._auto_fix_cpu_usage,
            'gpu_usage': self._auto_fix_gpu_usage,
            'memory_usage': self._auto_fix_memory_usage,
            'latency_ms': self._auto_fix_latency,
        }
        
        return auto_fix_functions.get(metric_name)
    
    def _auto_fix_cpu_usage(self):
        """Auto-fix for high CPU usage."""
        self.logger.info("Applying CPU usage optimization")
        # Implementation would reduce processing load
        pass
    
    def _auto_fix_gpu_usage(self):
        """Auto-fix for high GPU usage."""
        self.logger.info("Applying GPU usage optimization")
        # Implementation would optimize GPU workload
        pass
    
    def _auto_fix_memory_usage(self):
        """Auto-fix for high memory usage."""
        self.logger.info("Applying memory usage optimization")
        # Implementation would clear caches, optimize memory
        pass
    
    def _auto_fix_latency(self):
        """Auto-fix for high latency."""
        self.logger.info("Applying latency optimization")
        # Implementation would optimize processing pipeline
        pass
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get list of active (non-dismissed) alerts."""
        return [alert for alert in self.alerts if not alert.dismissed]
    
    def dismiss_alert(self, alert_id: str):
        """Dismiss an alert by ID."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.dismissed = True
                break
    
    def clear_all_alerts(self):
        """Clear all active alerts."""
        self.alerts.clear()
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        active_alerts = self.get_active_alerts()
        
        return {
            'total_alerts': len(self.alert_history),
            'active_alerts': len(active_alerts),
            'critical_alerts': len([a for a in active_alerts if a.severity == 'critical']),
            'warning_alerts': len([a for a in active_alerts if a.severity == 'warning']),
            'most_common_alert': self._get_most_common_alert_type(),
            'alert_frequency': len(self.alert_history) / max(1, (time.time() - self.alert_history[0].timestamp.timestamp()) / 3600) if self.alert_history else 0
        }
    
    def _get_most_common_alert_type(self) -> str:
        """Get the most common alert type from history."""
        if not self.alert_history:
            return "none"
        
        alert_counts = {}
        for alert in self.alert_history:
            alert_counts[alert.alert_type] = alert_counts.get(alert.alert_type, 0) + 1
        
        return max(alert_counts, key=alert_counts.get)


class OptimizationEngine:
    """Generates optimization suggestions based on performance analysis."""
    
    def __init__(self):
        """Initialize optimization engine."""
        self.logger = logging.getLogger(__name__)
        self.suggestions: List[OptimizationSuggestion] = []
        self.metrics_history: List[PerformanceMetrics] = []
        self.analysis_window = 300  # 5 minutes of data for analysis
    
    def analyze_performance(self, metrics_history: List[PerformanceMetrics]) -> List[OptimizationSuggestion]:
        """Analyze performance metrics and generate optimization suggestions."""
        self.metrics_history = metrics_history[-self.analysis_window:]  # Keep recent data
        suggestions = []
        
        if len(self.metrics_history) < 10:  # Need minimum data for analysis
            return suggestions
        
        # Analyze different performance aspects
        suggestions.extend(self._analyze_cpu_performance())
        suggestions.extend(self._analyze_gpu_performance())
        suggestions.extend(self._analyze_memory_performance())
        suggestions.extend(self._analyze_latency_performance())
        suggestions.extend(self._analyze_fps_performance())
        
        # Sort by priority and impact
        suggestions.sort(key=lambda s: (s.priority, s.impact == 'high', s.impact == 'medium'), reverse=True)
        
        self.suggestions = suggestions
        return suggestions
    
    def _analyze_cpu_performance(self) -> List[OptimizationSuggestion]:
        """Analyze CPU performance and generate suggestions."""
        suggestions = []
        
        avg_cpu = sum(m.cpu_usage for m in self.metrics_history) / len(self.metrics_history)
        max_cpu = max(m.cpu_usage for m in self.metrics_history)
        
        if avg_cpu > 70:
            suggestions.append(OptimizationSuggestion(
                title="Reduce CPU Load",
                description=f"Average CPU usage is {avg_cpu:.1f}%. Consider reducing processing quality or enabling GPU acceleration.",
                impact="high" if avg_cpu > 85 else "medium",
                estimated_improvement="10-20% CPU reduction",
                category="cpu",
                priority=90 if avg_cpu > 85 else 70
            ))
        
        if max_cpu > 95:
            suggestions.append(OptimizationSuggestion(
                title="CPU Throttling Detected",
                description="CPU usage peaked at 95%+. System may be throttling performance.",
                impact="critical",
                estimated_improvement="Prevent system instability",
                category="cpu",
                priority=100
            ))
        
        return suggestions
    
    def _analyze_gpu_performance(self) -> List[OptimizationSuggestion]:
        """Analyze GPU performance and generate suggestions."""
        suggestions = []
        
        avg_gpu = sum(m.gpu_usage for m in self.metrics_history) / len(self.metrics_history)
        
        if avg_gpu < 30:
            suggestions.append(OptimizationSuggestion(
                title="Enable GPU Acceleration",
                description=f"GPU usage is only {avg_gpu:.1f}%. Enable GPU acceleration for better performance.",
                impact="high",
                estimated_improvement="30-50% performance increase",
                category="gpu",
                priority=85
            ))
        elif avg_gpu > 90:
            suggestions.append(OptimizationSuggestion(
                title="GPU Overload",
                description=f"GPU usage is {avg_gpu:.1f}%. Consider reducing GPU workload or quality settings.",
                impact="medium",
                estimated_improvement="Prevent GPU throttling",
                category="gpu",
                priority=75
            ))
        
        return suggestions
    
    def _analyze_memory_performance(self) -> List[OptimizationSuggestion]:
        """Analyze memory performance and generate suggestions."""
        suggestions = []
        
        avg_memory = sum(m.memory_usage for m in self.metrics_history) / len(self.metrics_history)
        memory_trend = self._calculate_trend([m.memory_usage for m in self.metrics_history])
        
        if avg_memory > 12000:  # 12GB
            suggestions.append(OptimizationSuggestion(
                title="High Memory Usage",
                description=f"Memory usage is {avg_memory/1024:.1f}GB. Consider clearing caches or reducing model sizes.",
                impact="medium",
                estimated_improvement="Prevent memory swapping",
                category="memory",
                priority=70
            ))
        
        if memory_trend > 0.1:  # Memory increasing
            suggestions.append(OptimizationSuggestion(
                title="Memory Leak Detected",
                description="Memory usage is steadily increasing. Possible memory leak detected.",
                impact="high",
                estimated_improvement="Prevent system crash",
                category="memory",
                priority=95
            ))
        
        return suggestions
    
    def _analyze_latency_performance(self) -> List[OptimizationSuggestion]:
        """Analyze latency performance and generate suggestions."""
        suggestions = []
        
        avg_latency = sum(m.latency_ms for m in self.metrics_history) / len(self.metrics_history)
        latency_variance = self._calculate_variance([m.latency_ms for m in self.metrics_history])
        
        if avg_latency > 100:
            suggestions.append(OptimizationSuggestion(
                title="High Processing Latency",
                description=f"Average latency is {avg_latency:.1f}ms. Target is <100ms for real-time performance.",
                impact="high",
                estimated_improvement="Improve real-time responsiveness",
                category="latency",
                priority=80
            ))
        
        if latency_variance > 500:  # High variance
            suggestions.append(OptimizationSuggestion(
                title="Inconsistent Performance",
                description="Latency varies significantly. Consider optimizing processing pipeline.",
                impact="medium",
                estimated_improvement="More consistent performance",
                category="latency",
                priority=60
            ))
        
        return suggestions
    
    def _analyze_fps_performance(self) -> List[OptimizationSuggestion]:
        """Analyze FPS performance and generate suggestions."""
        suggestions = []
        
        avg_fps = sum(m.fps for m in self.metrics_history) / len(self.metrics_history)
        min_fps = min(m.fps for m in self.metrics_history)
        
        if avg_fps < 30:
            suggestions.append(OptimizationSuggestion(
                title="Low Frame Rate",
                description=f"Average FPS is {avg_fps:.1f}. Target is 30+ FPS for smooth operation.",
                impact="high",
                estimated_improvement="Smoother user experience",
                category="fps",
                priority=85
            ))
        
        if min_fps < 15:
            suggestions.append(OptimizationSuggestion(
                title="Frame Drops Detected",
                description=f"Minimum FPS dropped to {min_fps:.1f}. Investigate performance bottlenecks.",
                impact="medium",
                estimated_improvement="Eliminate stuttering",
                category="fps",
                priority=70
            ))
        
        return suggestions
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) of values over time."""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        # Linear regression slope
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        return slope
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance
    
    def get_suggestions_by_category(self, category: str) -> List[OptimizationSuggestion]:
        """Get optimization suggestions for specific category."""
        return [s for s in self.suggestions if s.category == category]
    
    def get_high_impact_suggestions(self) -> List[OptimizationSuggestion]:
        """Get high-impact optimization suggestions."""
        return [s for s in self.suggestions if s.impact == "high"]


class PerformanceMonitor(IPerformanceMonitor):
    """Main performance monitoring system implementation."""
    
    def __init__(self, update_interval: float = 1.0, history_size: int = 3600):
        """Initialize performance monitor.
        
        Args:
            update_interval: Metrics collection interval in seconds
            history_size: Maximum number of metrics to store in history
        """
        self.logger = logging.getLogger(__name__)
        self.update_interval = update_interval
        self.history_size = history_size
        
        # Components
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.optimization_engine = OptimizationEngine()
        
        # Data storage
        self.metrics_history: deque = deque(maxlen=history_size)
        self.is_monitoring = False
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.metrics_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        # Performance tracking
        self.monitoring_start_time = 0.0
        self.total_metrics_collected = 0
        
        self.logger.info("Performance monitor initialized")
    
    def start_monitoring(self):
        """Start performance monitoring."""
        if self.is_monitoring:
            self.logger.warning("Performance monitoring already running")
            return
        
        self.is_monitoring = True
        self.stop_event.clear()
        self.monitoring_start_time = time.time()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop running in separate thread."""
        self.logger.info("Performance monitoring loop started")
        
        while not self.stop_event.is_set():
            try:
                # Collect current metrics
                metrics = self.metrics_collector.collect_current_metrics()
                
                # Add to history
                self.metrics_history.append(metrics)
                self.total_metrics_collected += 1
                
                # Check for alerts
                new_alerts = self.alert_manager.check_metrics_for_alerts(metrics)
                
                # Notify callbacks
                for callback in self.metrics_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        self.logger.error(f"Metrics callback failed: {e}")
                
                for alert in new_alerts:
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            self.logger.error(f"Alert callback failed: {e}")
                
                # Generate optimization suggestions periodically
                if self.total_metrics_collected % 60 == 0:  # Every minute
                    self.optimization_engine.analyze_performance(list(self.metrics_history))
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            # Wait for next update
            self.stop_event.wait(self.update_interval)
        
        self.logger.info("Performance monitoring loop ended")
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics_collector.collect_current_metrics()
    
    def get_metrics_history(self, duration_seconds: int) -> List[PerformanceMetrics]:
        """Get performance metrics history for specified duration."""
        if not self.metrics_history:
            return []
        
        cutoff_time = time.time() - duration_seconds
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def set_alert_thresholds(self, thresholds: Dict[str, float]):
        """Set performance alert thresholds."""
        self.alert_manager.set_alert_thresholds(thresholds)
    
    def add_metrics_callback(self, callback: Callable[[PerformanceMetrics], None]):
        """Add callback for metrics updates."""
        self.metrics_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add callback for alert notifications."""
        self.alert_callbacks.append(callback)
    
    def record_frame_time(self, frame_time: float):
        """Record frame processing time for FPS calculation."""
        self.metrics_collector.record_frame_time(frame_time)
    
    def record_processing_time(self, processing_time: float):
        """Record processing latency."""
        self.metrics_collector.record_processing_time(processing_time)
    
    def record_translation(self, success: bool = True):
        """Record translation attempt."""
        self.metrics_collector.record_translation(success)
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get list of active performance alerts."""
        return self.alert_manager.get_active_alerts()
    
    def dismiss_alert(self, alert_id: str):
        """Dismiss a performance alert."""
        self.alert_manager.dismiss_alert(alert_id)
    
    def get_optimization_suggestions(self) -> List[OptimizationSuggestion]:
        """Get current optimization suggestions."""
        return self.optimization_engine.suggestions
    
    def get_system_resource_info(self) -> SystemResourceInfo:
        """Get detailed system resource information."""
        return self.metrics_collector.get_system_resource_info()
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get performance monitoring statistics."""
        uptime = time.time() - self.monitoring_start_time if self.monitoring_start_time > 0 else 0
        
        return {
            'is_monitoring': self.is_monitoring,
            'uptime_seconds': uptime,
            'total_metrics_collected': self.total_metrics_collected,
            'metrics_history_size': len(self.metrics_history),
            'collection_rate': self.total_metrics_collected / max(1, uptime / 60),  # per minute
            'alert_statistics': self.alert_manager.get_alert_statistics(),
            'optimization_suggestions_count': len(self.optimization_engine.suggestions)
        }
    
    def export_metrics_data(self, file_path: str, duration_hours: int = 24):
        """Export metrics data to file."""
        try:
            metrics_data = self.get_metrics_history(duration_hours * 3600)
            
            if file_path.endswith('.json'):
                # Export as JSON
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'duration_hours': duration_hours,
                    'metrics_count': len(metrics_data),
                    'metrics': [
                        {
                            'timestamp': m.timestamp,
                            'fps': m.fps,
                            'cpu_usage': m.cpu_usage,
                            'gpu_usage': m.gpu_usage,
                            'memory_usage': m.memory_usage,
                            'latency_ms': m.latency_ms,
                            'accuracy': m.accuracy
                        }
                        for m in metrics_data
                    ]
                }
                
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
            
            else:
                # Export as CSV
                import csv
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Timestamp', 'FPS', 'CPU%', 'GPU%', 'Memory_MB', 'Latency_ms', 'Accuracy%'])
                    
                    for metric in metrics_data:
                        writer.writerow([
                            datetime.fromtimestamp(metric.timestamp).isoformat(),
                            metric.fps, metric.cpu_usage, metric.gpu_usage,
                            metric.memory_usage, metric.latency_ms, metric.accuracy
                        ])
            
            self.logger.info(f"Exported {len(metrics_data)} metrics to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics data: {e}")
            raise


def create_performance_monitor(update_interval: float = 1.0, 
                             history_size: int = 3600) -> PerformanceMonitor:
    """Factory function to create performance monitor instance.
    
    Args:
        update_interval: Metrics collection interval in seconds
        history_size: Maximum number of metrics to store in history
        
    Returns:
        Configured PerformanceMonitor instance
    """
    return PerformanceMonitor(update_interval=update_interval, history_size=history_size)


if __name__ == "__main__":
    # Test the performance monitor
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    monitor = create_performance_monitor(update_interval=0.5)
    
    try:
        monitor.start_monitoring()
        
        # Simulate some activity
        for i in range(10):
            time.sleep(1)
            
            # Simulate frame processing
            monitor.record_frame_time(0.016)  # ~60 FPS
            monitor.record_processing_time(45.0)  # 45ms processing
            monitor.record_translation(success=True)
            
            # Get current metrics
            metrics = monitor.get_current_metrics()
            print(f"Metrics: FPS={metrics.fps:.1f}, CPU={metrics.cpu_usage:.1f}%, "
                  f"GPU={metrics.gpu_usage:.1f}%, Memory={metrics.memory_usage:.0f}MB, "
                  f"Latency={metrics.latency_ms:.1f}ms")
        
        # Get statistics
        stats = monitor.get_monitoring_statistics()
        print(f"Monitoring stats: {stats}")
        
        # Get alerts
        alerts = monitor.get_active_alerts()
        print(f"Active alerts: {len(alerts)}")
        
        # Get suggestions
        suggestions = monitor.get_optimization_suggestions()
        print(f"Optimization suggestions: {len(suggestions)}")
        
    finally:
        monitor.stop_monitoring()