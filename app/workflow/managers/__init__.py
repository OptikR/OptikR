"""
Pipeline Managers Package

Modular managers for the translation pipeline to improve maintainability,
robustness, and testability.
"""

# Phase 1: Foundation
from .pipeline_core_manager import PipelineCoreManager, PipelineState, PipelineConfig
from .pipeline_error_handler import PipelineErrorHandler, CircuitBreaker, ErrorSeverity
from .pipeline_metrics_manager import PipelineMetricsManager, PipelineMetrics

# Phase 2: Performance
from .pipeline_queue_manager import PipelineQueueManager, ManagedQueue, QueueStats
from .pipeline_worker_manager import PipelineWorkerManager, WorkerState, WorkerStats
from .pipeline_cache_manager import PipelineCacheManager

# Phase 3: Advanced
from .pipeline_stage_manager import PipelineStageManager, PipelineStage, StageConfig, StageState
from .pipeline_health_monitor import PipelineHealthMonitor, HealthCheck, HealthStatus

__all__ = [
    # Phase 1
    "PipelineCoreManager",
    "PipelineState",
    "PipelineConfig",
    "PipelineErrorHandler",
    "CircuitBreaker",
    "ErrorSeverity",
    "PipelineMetricsManager",
    "PipelineMetrics",
    # Phase 2
    "PipelineQueueManager",
    "ManagedQueue",
    "QueueStats",
    "PipelineWorkerManager",
    "WorkerState",
    "WorkerStats",
    "PipelineCacheManager",
    # Phase 3
    "PipelineStageManager",
    "PipelineStage",
    "StageConfig",
    "StageState",
    "PipelineHealthMonitor",
    "HealthCheck",
    "HealthStatus",
]
