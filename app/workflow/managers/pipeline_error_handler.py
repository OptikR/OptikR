"""
Pipeline Error Handler

Centralized error handling with circuit breaker pattern, retry logic,
and automatic recovery strategies.
"""

import time
import logging
import threading
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, blocking calls
    HALF_OPEN = "half_open"  # Testing if system recovered


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"           # Minor issues, can continue
    MEDIUM = "medium"     # Significant issues, may need attention
    HIGH = "high"         # Critical issues, immediate action needed
    CRITICAL = "critical"  # System failure, stop pipeline


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    timestamp: datetime
    component: str
    error_type: str
    message: str
    severity: ErrorSeverity
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if system recovered
    """
    
    def __init__(self,
                 name: str,
                 failure_threshold: int = 5,
                 timeout: float = 60.0,
                 success_threshold: int = 2):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            timeout: Seconds to wait before trying again
            success_threshold: Successes needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.lock = threading.RLock()
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.logger.info(f"Circuit {self.name}: Attempting reset (HALF_OPEN)")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(f"Circuit {self.name} is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.logger.info(f"Circuit {self.name}: Closing (recovered)")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                self.logger.warning(f"Circuit {self.name}: Opening (test failed)")
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.logger.error(f"Circuit {self.name}: Opening (threshold reached)")
                self.state = CircuitState.OPEN
    
    def reset(self):
        """Manually reset circuit breaker."""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.logger.info(f"Circuit {self.name}: Manually reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        with self.lock:
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure': self.last_failure_time.isoformat() if self.last_failure_time else None
            }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class PipelineErrorHandler:
    """
    Centralized error handling for the pipeline.
    
    Features:
    - Circuit breakers for each component
    - Retry logic with exponential backoff
    - Error tracking and reporting
    - Automatic recovery strategies
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.logger = logging.getLogger(__name__)
        
        # Circuit breakers for each component
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Error tracking
        self.error_history: List[ErrorRecord] = []
        self.error_counts: Dict[str, int] = {}
        self.lock = threading.RLock()
        
        # Recovery strategies
        self.recovery_strategies: Dict[str, Callable] = {}
        
        self.logger.info("Pipeline Error Handler initialized")
    
    def register_circuit_breaker(self,
                                 component: str,
                                 failure_threshold: int = 5,
                                 timeout: float = 60.0) -> CircuitBreaker:
        """
        Register a circuit breaker for a component.
        
        Args:
            component: Component name
            failure_threshold: Failures before opening
            timeout: Seconds before retry
            
        Returns:
            CircuitBreaker instance
        """
        breaker = CircuitBreaker(
            name=component,
            failure_threshold=failure_threshold,
            timeout=timeout
        )
        self.circuit_breakers[component] = breaker
        self.logger.info(f"Registered circuit breaker for: {component}")
        return breaker
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """
        Register a recovery strategy for an error type.
        
        Args:
            error_type: Type of error (e.g., 'OCRError', 'TranslationError')
            strategy: Recovery function
        """
        self.recovery_strategies[error_type] = strategy
        self.logger.debug(f"Registered recovery strategy for: {error_type}")
    
    def handle_error(self,
                    component: str,
                    error: Exception,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle an error with appropriate strategy.
        
        Args:
            component: Component where error occurred
            error: The exception
            severity: Error severity
            context: Additional context
            
        Returns:
            bool: True if recovered, False otherwise
        """
        error_type = type(error).__name__
        
        # Record error
        record = ErrorRecord(
            timestamp=datetime.now(),
            component=component,
            error_type=error_type,
            message=str(error),
            severity=severity,
            stack_trace=self._get_stack_trace(error)
        )
        
        with self.lock:
            self.error_history.append(record)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log error
        log_func = {
            ErrorSeverity.LOW: self.logger.debug,
            ErrorSeverity.MEDIUM: self.logger.warning,
            ErrorSeverity.HIGH: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical
        }.get(severity, self.logger.error)
        
        log_func(f"Error in {component}: {error_type} - {str(error)}")
        
        # Attempt recovery
        if error_type in self.recovery_strategies:
            try:
                record.recovery_attempted = True
                self.recovery_strategies[error_type](error, context)
                record.recovery_successful = True
                self.logger.info(f"Successfully recovered from {error_type}")
                return True
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed: {recovery_error}")
        
        return False
    
    def retry_with_backoff(self,
                          func: Callable,
                          max_attempts: int = 3,
                          initial_delay: float = 1.0,
                          backoff_factor: float = 2.0,
                          max_delay: float = 60.0) -> Any:
        """
        Retry function with exponential backoff.
        
        Args:
            func: Function to retry
            max_attempts: Maximum retry attempts
            initial_delay: Initial delay in seconds
            backoff_factor: Backoff multiplier
            max_delay: Maximum delay between retries
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                last_exception = e
                
                if attempt < max_attempts - 1:
                    # Add jitter to prevent thundering herd
                    import random
                    jitter = random.uniform(0, delay * 0.1)
                    sleep_time = min(delay + jitter, max_delay)
                    
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor
        
        raise last_exception
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get error summary statistics.
        
        Returns:
            dict: Error statistics
        """
        with self.lock:
            recent_errors = [
                e for e in self.error_history
                if (datetime.now() - e.timestamp) < timedelta(minutes=5)
            ]
            
            return {
                'total_errors': len(self.error_history),
                'recent_errors': len(recent_errors),
                'error_counts': dict(self.error_counts),
                'circuit_breakers': {
                    name: breaker.get_status()
                    for name, breaker in self.circuit_breakers.items()
                }
            }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            list: Recent error records
        """
        with self.lock:
            recent = sorted(
                self.error_history,
                key=lambda e: e.timestamp,
                reverse=True
            )[:limit]
            
            return [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'component': e.component,
                    'error_type': e.error_type,
                    'message': e.message,
                    'severity': e.severity.value,
                    'recovered': e.recovery_successful
                }
                for e in recent
            ]
    
    def clear_history(self, older_than: Optional[timedelta] = None):
        """
        Clear error history.
        
        Args:
            older_than: Only clear errors older than this duration
        """
        with self.lock:
            if older_than:
                cutoff = datetime.now() - older_than
                self.error_history = [
                    e for e in self.error_history
                    if e.timestamp > cutoff
                ]
            else:
                self.error_history.clear()
                self.error_counts.clear()
        
        self.logger.info("Error history cleared")
    
    def reset_all_circuits(self):
        """Reset all circuit breakers."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        self.logger.info("All circuit breakers reset")
    
    @staticmethod
    def _get_stack_trace(error: Exception) -> str:
        """Get stack trace from exception."""
        import traceback
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
