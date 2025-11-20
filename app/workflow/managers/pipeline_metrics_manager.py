"""
Pipeline Metrics Manager

Collects, aggregates, and reports pipeline performance metrics.
Provides real-time monitoring and bottleneck identification.
"""

import time
import threading
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque


@dataclass
class PipelineMetrics:
    """Comprehensive pipeline metrics."""
    # Frame metrics
    frames_captured: int = 0
    frames_processed: int = 0
    frames_skipped: int = 0
    
    # OCR metrics
    text_blocks_detected: int = 0
    text_blocks_validated: int = 0
    text_blocks_rejected: int = 0
    ocr_confidence_avg: float = 0.0
    
    # Translation metrics
    translations_completed: int = 0
    translations_failed: int = 0
    translation_confidence_avg: float = 0.0
    dictionary_hits: int = 0
    cache_hits: int = 0
    
    # Performance metrics
    average_fps: float = 0.0
    current_fps: float = 0.0
    average_latency_ms: float = 0.0
    total_processing_time: float = 0.0
    
    # Component timing (ms)
    capture_time_ms: float = 0.0
    preprocessing_time_ms: float = 0.0
    ocr_time_ms: float = 0.0
    translation_time_ms: float = 0.0
    overlay_time_ms: float = 0.0
    
    # Resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    gpu_usage_percent: float = 0.0
    
    # Queue metrics
    capture_queue_size: int = 0
    ocr_queue_size: int = 0
    translation_queue_size: int = 0
    overlay_queue_size: int = 0
    
    # Error metrics
    total_errors: int = 0
    errors_last_minute: int = 0


class MetricsCollector:
    """Collects metrics for a specific component."""
    
    def __init__(self, name: str, window_size: int = 100):
        """
        Initialize metrics collector.
        
        Args:
            name: Component name
            window_size: Number of samples to keep for averaging
        """
        self.name = name
        self.window_size = window_size
        
        # Timing data
        self.timings = deque(maxlen=window_size)
        self.total_time = 0.0
        self.count = 0
        
        # Success/failure tracking
        self.successes = 0
        self.failures = 0
        
        self.lock = threading.Lock()
    
    def record_timing(self, duration: float):
        """Record a timing measurement."""
        with self.lock:
            self.timings.append(duration)
            self.total_time += duration
            self.count += 1
    
    def record_success(self):
        """Record a successful operation."""
        with self.lock:
            self.successes += 1
    
    def record_failure(self):
        """Record a failed operation."""
        with self.lock:
            self.failures += 1
    
    def get_average(self) -> float:
        """Get average timing."""
        with self.lock:
            if not self.timings:
                return 0.0
            return sum(self.timings) / len(self.timings)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get component statistics."""
        with self.lock:
            return {
                'name': self.name,
                'count': self.count,
                'successes': self.successes,
                'failures': self.failures,
                'average_time_ms': self.get_average() * 1000,
                'total_time_s': self.total_time,
                'success_rate': self.successes / max(self.count, 1) * 100
            }


class PipelineMetricsManager:
    """
    Manages pipeline metrics collection and reporting.
    
    Features:
    - Real-time metrics collection
    - Component-level timing
    - Performance tracking
    - Bottleneck identification
    - Statistics export
    """
    
    def __init__(self):
        """Initialize metrics manager."""
        self.logger = logging.getLogger(__name__)
        
        # Main metrics
        self.metrics = PipelineMetrics()
        self.lock = threading.RLock()
        
        # Component collectors
        self.collectors: Dict[str, MetricsCollector] = {
            'capture': MetricsCollector('capture'),
            'preprocessing': MetricsCollector('preprocessing'),
            'ocr': MetricsCollector('ocr'),
            'translation': MetricsCollector('translation'),
            'overlay': MetricsCollector('overlay')
        }
        
        # FPS calculation
        self.frame_timestamps = deque(maxlen=100)
        self.last_fps_update = time.time()
        
        # Latency tracking
        self.latencies = deque(maxlen=100)
        
        # Start time
        self.start_time: Optional[datetime] = None
        
        self.logger.info("Pipeline Metrics Manager initialized")
    
    def start(self):
        """Start metrics collection."""
        self.start_time = datetime.now()
        self.logger.info("Metrics collection started")
    
    def stop(self):
        """Stop metrics collection."""
        self.start_time = None
        self.logger.info("Metrics collection stopped")
    
    def record_frame_captured(self):
        """Record a frame capture."""
        with self.lock:
            self.metrics.frames_captured += 1
            self.frame_timestamps.append(time.time())
            self._update_fps()
    
    def record_frame_processed(self):
        """Record a frame processed."""
        with self.lock:
            self.metrics.frames_processed += 1
    
    def record_frame_skipped(self):
        """Record a frame skipped."""
        with self.lock:
            self.metrics.frames_skipped += 1
    
    def record_text_detected(self, count: int, confidence: float = 0.0):
        """Record text blocks detected."""
        with self.lock:
            self.metrics.text_blocks_detected += count
            if confidence > 0:
                # Update running average
                total = self.metrics.text_blocks_detected
                current_avg = self.metrics.ocr_confidence_avg
                self.metrics.ocr_confidence_avg = (
                    (current_avg * (total - count) + confidence * count) / total
                )
    
    def record_text_validated(self, count: int):
        """Record text blocks validated."""
        with self.lock:
            self.metrics.text_blocks_validated += count
    
    def record_text_rejected(self, count: int):
        """Record text blocks rejected."""
        with self.lock:
            self.metrics.text_blocks_rejected += count
    
    def record_translation(self, success: bool = True, confidence: float = 0.0):
        """Record a translation."""
        with self.lock:
            if success:
                self.metrics.translations_completed += 1
                if confidence > 0:
                    total = self.metrics.translations_completed
                    current_avg = self.metrics.translation_confidence_avg
                    self.metrics.translation_confidence_avg = (
                        (current_avg * (total - 1) + confidence) / total
                    )
            else:
                self.metrics.translations_failed += 1
    
    def record_dictionary_hit(self):
        """Record a dictionary cache hit."""
        with self.lock:
            self.metrics.dictionary_hits += 1
    
    def record_cache_hit(self):
        """Record a translation cache hit."""
        with self.lock:
            self.metrics.cache_hits += 1
    
    def record_component_timing(self, component: str, duration: float):
        """
        Record timing for a component.
        
        Args:
            component: Component name
            duration: Duration in seconds
        """
        if component in self.collectors:
            self.collectors[component].record_timing(duration)
            
            # Update metrics
            with self.lock:
                avg_ms = self.collectors[component].get_average() * 1000
                if component == 'capture':
                    self.metrics.capture_time_ms = avg_ms
                elif component == 'preprocessing':
                    self.metrics.preprocessing_time_ms = avg_ms
                elif component == 'ocr':
                    self.metrics.ocr_time_ms = avg_ms
                elif component == 'translation':
                    self.metrics.translation_time_ms = avg_ms
                elif component == 'overlay':
                    self.metrics.overlay_time_ms = avg_ms
    
    def record_latency(self, latency: float):
        """
        Record end-to-end latency.
        
        Args:
            latency: Latency in seconds
        """
        with self.lock:
            self.latencies.append(latency)
            if self.latencies:
                self.metrics.average_latency_ms = (
                    sum(self.latencies) / len(self.latencies) * 1000
                )
    
    def record_error(self):
        """Record an error."""
        with self.lock:
            self.metrics.total_errors += 1
    
    def update_queue_sizes(self, **sizes):
        """
        Update queue sizes.
        
        Args:
            **sizes: Queue sizes (e.g., capture=5, ocr=3)
        """
        with self.lock:
            if 'capture' in sizes:
                self.metrics.capture_queue_size = sizes['capture']
            if 'ocr' in sizes:
                self.metrics.ocr_queue_size = sizes['ocr']
            if 'translation' in sizes:
                self.metrics.translation_queue_size = sizes['translation']
            if 'overlay' in sizes:
                self.metrics.overlay_queue_size = sizes['overlay']
    
    def update_resource_usage(self, memory_mb: float = 0.0, cpu_percent: float = 0.0, gpu_percent: float = 0.0):
        """
        Update resource usage metrics.
        
        Args:
            memory_mb: Memory usage in MB
            cpu_percent: CPU usage percentage
            gpu_percent: GPU usage percentage
        """
        with self.lock:
            if memory_mb > 0:
                self.metrics.memory_usage_mb = memory_mb
            if cpu_percent > 0:
                self.metrics.cpu_usage_percent = cpu_percent
            if gpu_percent > 0:
                self.metrics.gpu_usage_percent = gpu_percent
    
    def _update_fps(self):
        """Update FPS calculation."""
        now = time.time()
        if now - self.last_fps_update >= 1.0:  # Update every second
            if len(self.frame_timestamps) >= 2:
                time_span = self.frame_timestamps[-1] - self.frame_timestamps[0]
                if time_span > 0:
                    self.metrics.current_fps = (len(self.frame_timestamps) - 1) / time_span
                    
                    # Update average FPS
                    total_frames = self.metrics.frames_captured
                    if self.start_time and total_frames > 0:
                        elapsed = (datetime.now() - self.start_time).total_seconds()
                        if elapsed > 0:
                            self.metrics.average_fps = total_frames / elapsed
            
            self.last_fps_update = now
    
    def get_metrics(self) -> PipelineMetrics:
        """Get current metrics snapshot."""
        with self.lock:
            return PipelineMetrics(**vars(self.metrics))
    
    def get_component_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all components."""
        return {
            name: collector.get_stats()
            for name, collector in self.collectors.items()
        }
    
    def identify_bottleneck(self) -> Optional[str]:
        """
        Identify the slowest component (bottleneck).
        
        Returns:
            str: Name of bottleneck component, or None
        """
        stats = self.get_component_stats()
        if not stats:
            return None
        
        slowest = max(stats.items(), key=lambda x: x[1]['average_time_ms'])
        return slowest[0] if slowest[1]['average_time_ms'] > 0 else None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary.
        
        Returns:
            dict: Performance summary
        """
        with self.lock:
            bottleneck = self.identify_bottleneck()
            
            return {
                'fps': {
                    'current': round(self.metrics.current_fps, 2),
                    'average': round(self.metrics.average_fps, 2)
                },
                'latency_ms': round(self.metrics.average_latency_ms, 2),
                'frames': {
                    'captured': self.metrics.frames_captured,
                    'processed': self.metrics.frames_processed,
                    'skipped': self.metrics.frames_skipped
                },
                'translations': {
                    'completed': self.metrics.translations_completed,
                    'failed': self.metrics.translations_failed,
                    'success_rate': (
                        self.metrics.translations_completed /
                        max(self.metrics.translations_completed + self.metrics.translations_failed, 1) * 100
                    )
                },
                'cache': {
                    'dictionary_hits': self.metrics.dictionary_hits,
                    'cache_hits': self.metrics.cache_hits
                },
                'bottleneck': bottleneck,
                'errors': self.metrics.total_errors
            }
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics for external monitoring.
        
        Returns:
            dict: Complete metrics export
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': vars(self.get_metrics()),
            'component_stats': self.get_component_stats(),
            'performance_summary': self.get_performance_summary()
        }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.metrics = PipelineMetrics()
            self.frame_timestamps.clear()
            self.latencies.clear()
            
            for collector in self.collectors.values():
                collector.timings.clear()
                collector.total_time = 0.0
                collector.count = 0
                collector.successes = 0
                collector.failures = 0
            
            self.start_time = None
            self.logger.info("Metrics reset")
