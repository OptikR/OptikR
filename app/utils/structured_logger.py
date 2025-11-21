"""
Structured Logging System for OptikR

This module provides a comprehensive structured logging system with:
- Multiple verbosity levels
- Structured log format with operation tracking and performance data
- Log rotation and storage management
- Real-time log monitoring and filtering
- Performance metrics integration
"""

import json
import logging
import logging.handlers
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from queue import Queue, Empty
import traceback

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.interfaces import ILogger
from app.models import LogLevel, PerformanceMetrics

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path, ensure_app_directory


class LogCategory(Enum):
    """Categories for structured logging."""
    SYSTEM = "system"
    CAPTURE = "capture"
    OCR = "ocr"
    TRANSLATION = "translation"
    OVERLAY = "overlay"
    PERFORMANCE = "performance"
    ERROR = "error"
    USER_ACTION = "user_action"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"


class LogSeverity(Enum):
    """Log severity levels with numeric values for filtering."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEntry:
    """Structured log entry with comprehensive metadata."""
    timestamp: str
    level: str
    category: str
    operation: str
    message: str
    context: Dict[str, Any]
    performance_data: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None
    process_id: Optional[int] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


@dataclass
class LoggingConfiguration:
    """Configuration for structured logging system."""
    log_level: LogSeverity = LogSeverity.INFO
    log_to_file: bool = True
    log_to_console: bool = True
    log_directory: str = "logs"
    log_file_name: str = None  # Will be auto-generated with timestamp if None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 10
    enable_structured_format: bool = True
    enable_performance_logging: bool = True
    enable_operation_tracking: bool = True
    buffer_size: int = 1000
    flush_interval: float = 1.0  # seconds
    include_stack_trace_on_error: bool = True
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate timestamped log filename if not provided."""
        if self.log_file_name is None:
            # Generate filename with format: error-dd-mm-yyyy-hh-mm-ss.log
            now = datetime.now()
            self.log_file_name = now.strftime("error-%d-%m-%Y-%H-%M-%S.log")


class LogBuffer:
    """Thread-safe log buffer for batched writing."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: List[LogEntry] = []
        self.lock = threading.Lock()
        
    def add_entry(self, entry: LogEntry) -> None:
        """Add log entry to buffer."""
        with self.lock:
            self.buffer.append(entry)
            if len(self.buffer) >= self.max_size:
                self._flush_buffer()
    
    def _flush_buffer(self) -> List[LogEntry]:
        """Flush buffer and return entries."""
        entries = self.buffer.copy()
        self.buffer.clear()
        return entries
    
    def flush(self) -> List[LogEntry]:
        """Manually flush buffer."""
        with self.lock:
            return self._flush_buffer()
    
    def get_size(self) -> int:
        """Get current buffer size."""
        with self.lock:
            return len(self.buffer)


class PerformanceTracker:
    """Tracks performance metrics for operations."""
    
    def __init__(self):
        self.operations: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def start_operation(self, operation_id: str, operation_name: str, 
                       context: Optional[Dict[str, Any]] = None) -> None:
        """Start tracking an operation."""
        with self.lock:
            self.operations[operation_id] = {
                'name': operation_name,
                'start_time': time.time(),
                'context': context or {},
                'metrics': {}
            }
    
    def add_metric(self, operation_id: str, metric_name: str, value: Any) -> None:
        """Add a metric to an operation."""
        with self.lock:
            if operation_id in self.operations:
                self.operations[operation_id]['metrics'][metric_name] = value
    
    def end_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """End operation tracking and return performance data."""
        with self.lock:
            if operation_id in self.operations:
                operation = self.operations.pop(operation_id)
                operation['end_time'] = time.time()
                operation['duration'] = operation['end_time'] - operation['start_time']
                return operation
        return None


class LogRotationManager:
    """Manages log file rotation and cleanup."""
    
    def __init__(self, log_file_path: str, max_size: int, backup_count: int):
        self.log_file_path = Path(log_file_path)
        self.max_size = max_size
        self.backup_count = backup_count
        
        # Ensure log directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def should_rotate(self) -> bool:
        """Check if log file should be rotated."""
        if not self.log_file_path.exists():
            return False
        return self.log_file_path.stat().st_size >= self.max_size
    
    def rotate_logs(self) -> None:
        """Rotate log files."""
        if not self.log_file_path.exists():
            return
        
        # Move existing backup files
        for i in range(self.backup_count - 1, 0, -1):
            old_file = self.log_file_path.with_suffix(f'.log.{i}')
            new_file = self.log_file_path.with_suffix(f'.log.{i + 1}')
            
            if old_file.exists():
                if new_file.exists():
                    new_file.unlink()
                old_file.rename(new_file)
        
        # Move current log to .1
        backup_file = self.log_file_path.with_suffix('.log.1')
        if backup_file.exists():
            backup_file.unlink()
        self.log_file_path.rename(backup_file)
    
    def cleanup_old_logs(self) -> None:
        """Remove logs beyond backup count."""
        for i in range(self.backup_count + 1, self.backup_count + 10):
            old_file = self.log_file_path.with_suffix(f'.log.{i}')
            if old_file.exists():
                old_file.unlink()


class StructuredLogger(ILogger):
    """
    Comprehensive structured logging system with performance tracking,
    operation monitoring, and advanced log management capabilities.
    """
    
    def __init__(self, config: LoggingConfiguration):
        self.config = config
        self.session_id = config.session_id or self._generate_session_id()
        
        # Initialize components
        self.buffer = LogBuffer(config.buffer_size)
        self.performance_tracker = PerformanceTracker()
        self.rotation_manager = LogRotationManager(
            os.path.join(config.log_directory, config.log_file_name),
            config.max_file_size,
            config.backup_count
        )
        
        # Threading components
        self.flush_thread = None
        self.stop_event = threading.Event()
        self.log_handlers: List[Callable[[LogEntry], None]] = []
        
        # Initialize logging
        self._setup_logging()
        self._start_flush_thread()
        
        # Log system initialization
        self.log_info("SYSTEM", "logger_initialized", 
                     "Structured logging system initialized",
                     {"session_id": self.session_id, "config": asdict(config)})
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"session_{int(time.time())}_{os.getpid()}"
    
    def _setup_logging(self) -> None:
        """Setup logging infrastructure."""
        # Create log directory (EXE-compatible)
        # If log_directory is relative, make it app-relative
        if not Path(self.config.log_directory).is_absolute():
            log_dir = ensure_app_directory(self.config.log_directory)
            # Update config to use absolute path
            self.config.log_directory = str(log_dir)
        else:
            log_dir = Path(self.config.log_directory)
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup standard Python logger for fallback
        self.python_logger = logging.getLogger("StructuredLogger")
        self.python_logger.setLevel(self.config.log_level.value)
        
        # Console handler
        if self.config.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.config.log_level.value)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.python_logger.addHandler(console_handler)
    
    def _start_flush_thread(self) -> None:
        """Start background thread for flushing logs."""
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
    
    def _flush_worker(self) -> None:
        """Background worker for flushing log buffer."""
        while not self.stop_event.is_set():
            try:
                # Wait for flush interval or stop event
                if self.stop_event.wait(self.config.flush_interval):
                    break
                
                # Flush buffer
                entries = self.buffer.flush()
                if entries:
                    self._write_entries_to_file(entries)
                    
            except Exception as e:
                # Use Python logger for internal errors
                self.python_logger.error(f"Error in flush worker: {e}")
    
    def _write_entries_to_file(self, entries: List[LogEntry]) -> None:
        """Write log entries to file."""
        if not self.config.log_to_file or not entries:
            return
        
        try:
            # Check if rotation is needed
            if self.rotation_manager.should_rotate():
                self.rotation_manager.rotate_logs()
            
            # Write entries
            log_file_path = Path(self.config.log_directory) / self.config.log_file_name
            with open(log_file_path, 'a', encoding='utf-8') as f:
                for entry in entries:
                    if self.config.enable_structured_format:
                        f.write(entry.to_json() + '\n')
                    else:
                        f.write(f"{entry.timestamp} - {entry.level} - {entry.category} - {entry.message}\n")
                        
        except Exception as e:
            self.python_logger.error(f"Error writing to log file: {e}")
    
    def _create_log_entry(self, level: str, category: str, operation: str, 
                         message: str, context: Optional[Dict[str, Any]] = None,
                         performance_data: Optional[Dict[str, Any]] = None,
                         include_stack_trace: bool = False) -> LogEntry:
        """Create structured log entry."""
        
        # Generate correlation ID for request tracking
        correlation_id = f"{self.session_id}_{int(time.time() * 1000000)}"
        
        # Get stack trace if requested
        stack_trace = None
        if include_stack_trace:
            stack_trace = traceback.format_stack()
        
        return LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            category=category,
            operation=operation,
            message=message,
            context=context or {},
            performance_data=performance_data,
            thread_id=threading.current_thread().name,
            process_id=os.getpid(),
            session_id=self.session_id,
            correlation_id=correlation_id,
            stack_trace=stack_trace
        )
    
    # ILogger interface implementation
    
    def log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a message with specified level and optional context."""
        self.log_message(LogSeverity[level.upper()], "GENERAL", "log", message, context)
    
    def set_log_level(self, level: str) -> None:
        """Set minimum logging level."""
        try:
            self.config.log_level = LogSeverity[level.upper()]
            self.python_logger.setLevel(self.config.log_level.value)
            self.log_info("SYSTEM", "log_level_changed", 
                         f"Log level changed to {level}",
                         {"new_level": level})
        except KeyError:
            self.log_error("SYSTEM", "invalid_log_level", 
                          f"Invalid log level: {level}",
                          {"attempted_level": level})
    
    def add_handler(self, handler: Callable[[LogEntry], None]) -> None:
        """Add a log handler for real-time log processing."""
        self.log_handlers.append(handler)
        self.log_info("SYSTEM", "handler_added", 
                     "Log handler added",
                     {"handler_count": len(self.log_handlers)})
    
    def get_logs(self, level: Optional[str] = None, 
                limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve logged messages from file."""
        logs = []
        log_file_path = Path(self.config.log_directory) / self.config.log_file_name
        
        if not log_file_path.exists():
            return logs
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Filter by level if specified
            target_level = LogSeverity[level.upper()].value if level else 0
            
            for line in reversed(lines):  # Most recent first
                try:
                    if self.config.enable_structured_format:
                        log_data = json.loads(line.strip())
                        entry_level = LogSeverity[log_data.get('level', 'INFO')].value
                        
                        if entry_level >= target_level:
                            logs.append(log_data)
                    else:
                        # Parse simple format
                        parts = line.strip().split(' - ', 3)
                        if len(parts) >= 4:
                            timestamp, log_level, category, message = parts
                            entry_level = LogSeverity[log_level].value
                            
                            if entry_level >= target_level:
                                logs.append({
                                    'timestamp': timestamp,
                                    'level': log_level,
                                    'category': category,
                                    'message': message
                                })
                                
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
                
                if limit and len(logs) >= limit:
                    break
                    
        except Exception as e:
            self.python_logger.error(f"Error reading logs: {e}")
        
        return logs
    
    # Enhanced logging methods
    
    def log_message(self, level: LogSeverity, category: str, operation: str, 
                   message: str, context: Optional[Dict[str, Any]] = None,
                   performance_data: Optional[Dict[str, Any]] = None) -> None:
        """Log a message with full structured format."""
        
        # Check if message should be logged based on level
        if level.value < self.config.log_level.value:
            return
        
        # Include stack trace for errors if configured
        include_stack_trace = (
            self.config.include_stack_trace_on_error and 
            level.value >= LogSeverity.ERROR.value
        )
        
        # Create log entry
        entry = self._create_log_entry(
            level.name, category, operation, message, context,
            performance_data, include_stack_trace
        )
        
        # Add to buffer
        self.buffer.add_entry(entry)
        
        # Call real-time handlers
        for handler in self.log_handlers:
            try:
                handler(entry)
            except Exception as e:
                self.python_logger.error(f"Error in log handler: {e}")
        
        # Also log to Python logger for immediate console output
        if self.config.log_to_console:
            log_message = f"[{category}:{operation}] {message}"
            if context:
                log_message += f" | Context: {json.dumps(context, default=str)}"
            
            if level == LogSeverity.DEBUG:
                self.python_logger.debug(log_message)
            elif level == LogSeverity.INFO:
                self.python_logger.info(log_message)
            elif level == LogSeverity.WARNING:
                self.python_logger.warning(log_message)
            elif level == LogSeverity.ERROR:
                self.python_logger.error(log_message)
            elif level == LogSeverity.CRITICAL:
                self.python_logger.critical(log_message)
    
    # Convenience methods for different log levels
    
    def log_debug(self, category: str, operation: str, message: str, 
                  context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self.log_message(LogSeverity.DEBUG, category, operation, message, context)
    
    def log_info(self, category: str, operation: str, message: str, 
                 context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self.log_message(LogSeverity.INFO, category, operation, message, context)
    
    def log_warning(self, category: str, operation: str, message: str, 
                    context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self.log_message(LogSeverity.WARNING, category, operation, message, context)
    
    def log_error(self, category: str, operation: str, message: str, 
                  context: Optional[Dict[str, Any]] = None) -> None:
        """Log error message."""
        self.log_message(LogSeverity.ERROR, category, operation, message, context)
    
    def log_critical(self, category: str, operation: str, message: str, 
                     context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message."""
        self.log_message(LogSeverity.CRITICAL, category, operation, message, context)
    
    # Performance tracking methods
    
    def start_operation_tracking(self, operation_id: str, operation_name: str, 
                               category: str = "PERFORMANCE",
                               context: Optional[Dict[str, Any]] = None) -> None:
        """Start tracking an operation for performance logging."""
        if not self.config.enable_operation_tracking:
            return
        
        self.performance_tracker.start_operation(operation_id, operation_name, context)
        self.log_debug(category, "operation_started", 
                      f"Started tracking operation: {operation_name}",
                      {"operation_id": operation_id, "context": context})
    
    def add_operation_metric(self, operation_id: str, metric_name: str, 
                           value: Any) -> None:
        """Add a metric to a tracked operation."""
        if not self.config.enable_operation_tracking:
            return
        
        self.performance_tracker.add_metric(operation_id, metric_name, value)
    
    def end_operation_tracking(self, operation_id: str, 
                             category: str = "PERFORMANCE") -> None:
        """End operation tracking and log performance data."""
        if not self.config.enable_operation_tracking:
            return
        
        performance_data = self.performance_tracker.end_operation(operation_id)
        if performance_data:
            context = {"operation_id": operation_id}
            self.log_message(LogSeverity.INFO, category, "operation_completed",
                           f"Operation completed: {performance_data['name']}",
                           context, performance_data)
    
    def log_performance_metrics(self, metrics: PerformanceMetrics, 
                              category: str = "PERFORMANCE") -> None:
        """Log system performance metrics."""
        if not self.config.enable_performance_logging:
            return
        
        metrics_dict = {
            'fps': metrics.fps,
            'cpu_usage': metrics.cpu_usage,
            'gpu_usage': metrics.gpu_usage,
            'memory_usage': metrics.memory_usage,
            'latency_ms': metrics.latency_ms,
            'accuracy': metrics.accuracy
        }
        
        self.log_message(LogSeverity.INFO, category, "performance_metrics",
                        "System performance metrics", None, metrics_dict)
    
    # System management methods
    
    def flush_logs(self) -> None:
        """Manually flush all pending logs."""
        entries = self.buffer.flush()
        if entries:
            self._write_entries_to_file(entries)
    
    def rotate_logs_now(self) -> None:
        """Manually trigger log rotation."""
        self.flush_logs()
        self.rotation_manager.rotate_logs()
        self.log_info("SYSTEM", "log_rotation", "Log files rotated manually")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging system statistics."""
        log_file_path = Path(self.config.log_directory) / self.config.log_file_name
        
        stats = {
            'session_id': self.session_id,
            'buffer_size': self.buffer.get_size(),
            'log_file_exists': log_file_path.exists(),
            'log_file_size': log_file_path.stat().st_size if log_file_path.exists() else 0,
            'handler_count': len(self.log_handlers),
            'config': asdict(self.config)
        }
        
        return stats
    
    def cleanup(self) -> None:
        """Cleanup logging system resources."""
        self.log_info("SYSTEM", "logger_cleanup", "Shutting down structured logger")
        
        # Stop flush thread
        self.stop_event.set()
        if self.flush_thread and self.flush_thread.is_alive():
            self.flush_thread.join(timeout=5.0)
        
        # Final flush
        self.flush_logs()
        
        # Cleanup old logs
        self.rotation_manager.cleanup_old_logs()


def create_structured_logger(config: Optional[LoggingConfiguration] = None) -> StructuredLogger:
    """
    Factory function to create a structured logger with default configuration.
    
    Args:
        config: Optional logging configuration. If None, uses defaults.
        
    Returns:
        Configured StructuredLogger instance.
    """
    if config is None:
        config = LoggingConfiguration()
    
    return StructuredLogger(config)


def create_logger_from_system_config(system_config: Dict[str, Any]) -> StructuredLogger:
    """
    Create structured logger from system configuration.
    
    Args:
        system_config: System configuration dictionary containing logging settings.
        
    Returns:
        Configured StructuredLogger instance.
    """
    logging_config = system_config.get('logging', {})
    
    config = LoggingConfiguration(
        log_level=LogSeverity[logging_config.get('log_level', 'INFO').upper()],
        log_to_file=logging_config.get('log_to_file', True),
        log_to_console=logging_config.get('enable_console_output', True),
        log_directory=logging_config.get('log_directory', 'logs'),
        log_file_name=logging_config.get('log_file_name', None),  # None = auto-generate with timestamp
        max_file_size=logging_config.get('max_log_size', 10 * 1024 * 1024),
        backup_count=logging_config.get('backup_count', 10),
        enable_structured_format=logging_config.get('enable_structured_logging', True),
        enable_performance_logging=logging_config.get('enable_performance_logging', True),
        enable_operation_tracking=logging_config.get('enable_operation_tracking', True),
        session_id=logging_config.get('session_id')
    )
    
    return StructuredLogger(config)