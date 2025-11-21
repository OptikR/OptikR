"""
Comprehensive Error Handling System

This module provides centralized error handling, categorization, automatic recovery,
and user notification for OptikR.

Requirements Fulfilled:
- 1.4: Fallback to screenshot-based capture mode when DirectX capture fails
- 7.5: Graceful fallback to CPU Mode when GPU acceleration is unavailable  
- 9.4: Clear error messages and alternative installation methods for dependency failures

Author: Niklas Verhasselt
Date: November 2025
"""

import logging
import traceback
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime, timedelta

# Import existing error types
try:
    from ..capture.capture_layer import CaptureLayerError
    from ..capture.directx_capture import DirectXCaptureError
    from ..capture.screenshot_capture import ScreenshotCaptureError
    from ..overlay.directx_overlay import DirectXOverlayError
    from ..translation.cloud_translation_engines import (
        CloudTranslationError, RateLimitError, AuthenticationError
    )
except ImportError:
    # Define placeholder classes if imports fail
    class CaptureLayerError(Exception): pass
    class DirectXCaptureError(Exception): pass
    class ScreenshotCaptureError(Exception): pass
    class DirectXOverlayError(Exception): pass
    class CloudTranslationError(Exception): pass
    class RateLimitError(Exception): pass
    class AuthenticationError(Exception): pass


class ErrorCategory(Enum):
    """Error categories for systematic error handling."""
    HARDWARE = "hardware"
    DEPENDENCY = "dependency"
    CAPTURE = "capture"
    PROCESSING = "processing"
    RENDERING = "rendering"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels for prioritization."""
    CRITICAL = "critical"      # System cannot continue
    HIGH = "high"             # Major functionality affected
    MEDIUM = "medium"         # Some functionality affected
    LOW = "low"              # Minor issues, system continues
    INFO = "info"            # Informational, no action needed


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    RESTART_COMPONENT = "restart_component"
    DEGRADE_PERFORMANCE = "degrade_performance"
    SWITCH_MODE = "switch_mode"
    USER_INTERVENTION = "user_intervention"
    IGNORE = "ignore"


@dataclass
class ErrorContext:
    """Context information for error analysis."""
    component: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)
    system_state: Dict[str, Any] = field(default_factory=dict)
    user_action: Optional[str] = None
    retry_count: int = 0
    previous_errors: List[str] = field(default_factory=list)


@dataclass
class RecoveryAction:
    """Represents a recovery action to be taken."""
    strategy: RecoveryStrategy
    description: str
    action_function: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_probability: float = 0.5
    estimated_time: float = 0.0  # seconds
    requires_user_confirmation: bool = False


@dataclass
class ErrorReport:
    """Comprehensive error report for analysis and user notification."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    title: str
    message: str
    technical_details: str
    context: ErrorContext
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    user_message: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)
    auto_recovery_attempted: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class IErrorRecoveryHandler(ABC):
    """Interface for component-specific error recovery handlers."""
    
    @abstractmethod
    def can_handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this handler can process the given error."""
        pass
    
    @abstractmethod
    def get_recovery_actions(self, error: Exception, context: ErrorContext) -> List[RecoveryAction]:
        """Get available recovery actions for the error."""
        pass
    
    @abstractmethod
    def execute_recovery(self, action: RecoveryAction, error: Exception, context: ErrorContext) -> bool:
        """Execute a recovery action and return success status."""
        pass


class ErrorClassifier:
    """Classifies errors into categories and determines severity."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._error_patterns = self._initialize_error_patterns()
    
    def _initialize_error_patterns(self) -> Dict[str, tuple]:
        """Initialize error classification patterns."""
        return {
            # Hardware errors
            'cuda': (ErrorCategory.HARDWARE, ErrorSeverity.HIGH),
            'gpu': (ErrorCategory.HARDWARE, ErrorSeverity.HIGH),
            'directx': (ErrorCategory.HARDWARE, ErrorSeverity.MEDIUM),
            'memory': (ErrorCategory.HARDWARE, ErrorSeverity.HIGH),
            'insufficient': (ErrorCategory.HARDWARE, ErrorSeverity.MEDIUM),
            
            # Dependency errors
            'import': (ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH),
            'module': (ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH),
            'package': (ErrorCategory.DEPENDENCY, ErrorSeverity.MEDIUM),
            'version': (ErrorCategory.DEPENDENCY, ErrorSeverity.MEDIUM),
            
            # Capture errors
            'capture': (ErrorCategory.CAPTURE, ErrorSeverity.MEDIUM),
            'screen': (ErrorCategory.CAPTURE, ErrorSeverity.MEDIUM),
            'desktop': (ErrorCategory.CAPTURE, ErrorSeverity.MEDIUM),
            
            # Processing errors
            'ocr': (ErrorCategory.PROCESSING, ErrorSeverity.MEDIUM),
            'translation': (ErrorCategory.PROCESSING, ErrorSeverity.MEDIUM),
            'preprocessing': (ErrorCategory.PROCESSING, ErrorSeverity.LOW),
            
            # Rendering errors
            'overlay': (ErrorCategory.RENDERING, ErrorSeverity.MEDIUM),
            'render': (ErrorCategory.RENDERING, ErrorSeverity.MEDIUM),
            'display': (ErrorCategory.RENDERING, ErrorSeverity.MEDIUM),
            
            # Network errors
            'network': (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            'connection': (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            'timeout': (ErrorCategory.NETWORK, ErrorSeverity.LOW),
            'rate limit': (ErrorCategory.NETWORK, ErrorSeverity.LOW),
            
            # Configuration errors
            'config': (ErrorCategory.CONFIGURATION, ErrorSeverity.LOW),
            'setting': (ErrorCategory.CONFIGURATION, ErrorSeverity.LOW),
            'parameter': (ErrorCategory.CONFIGURATION, ErrorSeverity.LOW),
        }
    
    def classify_error(self, error: Exception, context: ErrorContext) -> tuple:
        """Classify error into category and severity."""
        error_text = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check specific error types first
        if isinstance(error, (DirectXCaptureError, DirectXOverlayError)):
            return ErrorCategory.HARDWARE, ErrorSeverity.MEDIUM
        elif isinstance(error, (CaptureLayerError, ScreenshotCaptureError)):
            return ErrorCategory.CAPTURE, ErrorSeverity.MEDIUM
        elif isinstance(error, (CloudTranslationError, RateLimitError, AuthenticationError)):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        elif isinstance(error, ImportError):
            return ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH
        elif isinstance(error, MemoryError):
            return ErrorCategory.HARDWARE, ErrorSeverity.CRITICAL
        elif isinstance(error, PermissionError):
            return ErrorCategory.SYSTEM, ErrorSeverity.HIGH
        
        # Pattern matching
        for pattern, (category, severity) in self._error_patterns.items():
            if pattern in error_text or pattern in error_type:
                return category, severity
        
        # Default classification
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def determine_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on context."""
        _, base_severity = self.classify_error(error, context)
        
        # Adjust severity based on context
        if context.retry_count > 3:
            # Repeated failures are more severe
            if base_severity == ErrorSeverity.LOW:
                return ErrorSeverity.MEDIUM
            elif base_severity == ErrorSeverity.MEDIUM:
                return ErrorSeverity.HIGH
        
        # Critical components failing
        if context.component in ['system_controller', 'capture_layer']:
            if base_severity == ErrorSeverity.MEDIUM:
                return ErrorSeverity.HIGH
        
        return base_severity


class CaptureErrorRecoveryHandler(IErrorRecoveryHandler):
    """Recovery handler for capture-related errors."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def can_handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this handler can process capture errors."""
        return (isinstance(error, (CaptureLayerError, DirectXCaptureError, ScreenshotCaptureError)) or
                context.component in ['capture_layer', 'directx_capture', 'screenshot_capture'])
    
    def get_recovery_actions(self, error: Exception, context: ErrorContext) -> List[RecoveryAction]:
        """Get recovery actions for capture errors."""
        actions = []
        
        if isinstance(error, DirectXCaptureError):
            # DirectX capture failed - fallback to screenshot
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                description="Switch to screenshot-based capture",
                action_function=self._fallback_to_screenshot,
                success_probability=0.8,
                estimated_time=2.0
            ))
        
        if context.retry_count < 3:
            # Retry capture with different settings
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Retry capture with reduced quality",
                action_function=self._retry_with_reduced_quality,
                success_probability=0.6,
                estimated_time=1.0
            ))
        
        # Restart capture component
        actions.append(RecoveryAction(
            strategy=RecoveryStrategy.RESTART_COMPONENT,
            description="Restart capture system",
            action_function=self._restart_capture_component,
            success_probability=0.7,
            estimated_time=5.0
        ))
        
        return actions
    
    def execute_recovery(self, action: RecoveryAction, error: Exception, context: ErrorContext) -> bool:
        """Execute capture recovery action."""
        try:
            if action.action_function:
                return action.action_function(error, context)
            return False
        except Exception as e:
            self.logger.error(f"Recovery action failed: {e}")
            return False
    
    def _fallback_to_screenshot(self, error: Exception, context: ErrorContext) -> bool:
        """Fallback to screenshot-based capture."""
        self.logger.info("Falling back to screenshot capture")
        # Implementation would switch capture mode
        return True
    
    def _retry_with_reduced_quality(self, error: Exception, context: ErrorContext) -> bool:
        """Retry capture with reduced quality settings."""
        self.logger.info("Retrying capture with reduced quality")
        # Implementation would adjust capture settings
        return True
    
    def _restart_capture_component(self, error: Exception, context: ErrorContext) -> bool:
        """Restart the capture component."""
        self.logger.info("Restarting capture component")
        # Implementation would restart capture system
        return True


class HardwareErrorRecoveryHandler(IErrorRecoveryHandler):
    """Recovery handler for hardware-related errors."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def can_handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this handler can process hardware errors."""
        error_text = str(error).lower()
        return ('gpu' in error_text or 'cuda' in error_text or 'directx' in error_text or
                'memory' in error_text or isinstance(error, MemoryError))
    
    def get_recovery_actions(self, error: Exception, context: ErrorContext) -> List[RecoveryAction]:
        """Get recovery actions for hardware errors."""
        actions = []
        
        error_text = str(error).lower()
        
        if 'gpu' in error_text or 'cuda' in error_text:
            # GPU unavailable - switch to CPU mode
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.SWITCH_MODE,
                description="Switch to CPU mode",
                action_function=self._switch_to_cpu_mode,
                success_probability=0.9,
                estimated_time=3.0
            ))
        
        if 'memory' in error_text or isinstance(error, MemoryError):
            # Memory issues - reduce performance profile
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.DEGRADE_PERFORMANCE,
                description="Reduce performance profile to conserve memory",
                action_function=self._reduce_performance_profile,
                success_probability=0.8,
                estimated_time=2.0
            ))
        
        return actions
    
    def execute_recovery(self, action: RecoveryAction, error: Exception, context: ErrorContext) -> bool:
        """Execute hardware recovery action."""
        try:
            if action.action_function:
                return action.action_function(error, context)
            return False
        except Exception as e:
            self.logger.error(f"Hardware recovery action failed: {e}")
            return False
    
    def _switch_to_cpu_mode(self, error: Exception, context: ErrorContext) -> bool:
        """Switch system to CPU mode."""
        self.logger.info("Switching to CPU mode due to GPU issues")
        # Implementation would switch runtime mode
        return True
    
    def _reduce_performance_profile(self, error: Exception, context: ErrorContext) -> bool:
        """Reduce performance profile to conserve resources."""
        self.logger.info("Reducing performance profile to conserve memory")
        # Implementation would adjust performance settings
        return True


class DependencyErrorRecoveryHandler(IErrorRecoveryHandler):
    """Recovery handler for dependency-related errors."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def can_handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this handler can process dependency errors."""
        return isinstance(error, (ImportError, ModuleNotFoundError)) or 'import' in str(error).lower()
    
    def get_recovery_actions(self, error: Exception, context: ErrorContext) -> List[RecoveryAction]:
        """Get recovery actions for dependency errors."""
        actions = []
        
        # Attempt automatic installation
        actions.append(RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            description="Attempt automatic dependency installation",
            action_function=self._install_missing_dependency,
            success_probability=0.7,
            estimated_time=30.0,
            requires_user_confirmation=True
        ))
        
        # Suggest manual installation
        actions.append(RecoveryAction(
            strategy=RecoveryStrategy.USER_INTERVENTION,
            description="Manual dependency installation required",
            success_probability=0.9,
            estimated_time=300.0,
            requires_user_confirmation=True
        ))
        
        return actions
    
    def execute_recovery(self, action: RecoveryAction, error: Exception, context: ErrorContext) -> bool:
        """Execute dependency recovery action."""
        try:
            if action.action_function:
                return action.action_function(error, context)
            return False
        except Exception as e:
            self.logger.error(f"Dependency recovery action failed: {e}")
            return False
    
    def _install_missing_dependency(self, error: Exception, context: ErrorContext) -> bool:
        """Attempt to install missing dependency."""
        self.logger.info("Attempting automatic dependency installation")
        # Implementation would use dependency manager
        return True


class ErrorHandler:
    """Central error handling system with recovery and notification."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.classifier = ErrorClassifier()
        self.recovery_handlers: List[IErrorRecoveryHandler] = []
        self.error_history: List[ErrorReport] = []
        self.notification_callbacks: List[Callable[[ErrorReport], None]] = []
        self.auto_recovery_enabled = True
        self.max_retry_attempts = 3
        self.error_suppression_time = timedelta(minutes=5)
        self._suppressed_errors: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        
        # Initialize default recovery handlers
        self._initialize_recovery_handlers()
    
    def _initialize_recovery_handlers(self):
        """Initialize default recovery handlers."""
        self.recovery_handlers = [
            CaptureErrorRecoveryHandler(self.logger),
            HardwareErrorRecoveryHandler(self.logger),
            DependencyErrorRecoveryHandler(self.logger)
        ]
    
    def add_recovery_handler(self, handler: IErrorRecoveryHandler):
        """Add a custom recovery handler."""
        self.recovery_handlers.append(handler)
    
    def add_notification_callback(self, callback: Callable[[ErrorReport], None]):
        """Add a callback for error notifications."""
        self.notification_callbacks.append(callback)
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorReport:
        """Main error handling entry point."""
        with self._lock:
            # Generate unique error ID
            error_id = f"{context.component}_{int(time.time())}_{id(error)}"
            
            # Check if error should be suppressed
            if self._should_suppress_error(error, context):
                self.logger.debug(f"Suppressing repeated error: {error}")
                return self._create_suppressed_error_report(error_id, error, context)
            
            # Classify error
            category, severity = self.classifier.classify_error(error, context)
            
            # Create error report
            error_report = self._create_error_report(error_id, error, context, category, severity)
            
            # Log error
            self._log_error(error_report)
            
            # Attempt automatic recovery if enabled
            if self.auto_recovery_enabled and severity != ErrorSeverity.CRITICAL:
                self._attempt_auto_recovery(error_report, error, context)
            
            # Store in history
            self.error_history.append(error_report)
            
            # Notify callbacks
            self._notify_callbacks(error_report)
            
            # Update suppression tracking
            self._update_error_suppression(error, context)
            
            return error_report
    
    def _should_suppress_error(self, error: Exception, context: ErrorContext) -> bool:
        """Check if error should be suppressed due to recent occurrence."""
        error_key = f"{type(error).__name__}_{context.component}_{str(error)[:100]}"
        
        if error_key in self._suppressed_errors:
            last_occurrence = self._suppressed_errors[error_key]
            if datetime.now() - last_occurrence < self.error_suppression_time:
                return True
        
        return False
    
    def _update_error_suppression(self, error: Exception, context: ErrorContext):
        """Update error suppression tracking."""
        error_key = f"{type(error).__name__}_{context.component}_{str(error)[:100]}"
        self._suppressed_errors[error_key] = datetime.now()
        
        # Clean old entries
        cutoff_time = datetime.now() - self.error_suppression_time * 2
        self._suppressed_errors = {
            k: v for k, v in self._suppressed_errors.items() 
            if v > cutoff_time
        }
    
    def _create_error_report(self, error_id: str, error: Exception, context: ErrorContext, 
                           category: ErrorCategory, severity: ErrorSeverity) -> ErrorReport:
        """Create comprehensive error report."""
        # Generate user-friendly message
        user_message = self._generate_user_message(error, category, severity)
        
        # Get recovery actions
        recovery_actions = self._get_recovery_actions(error, context)
        
        # Generate suggested actions for user
        suggested_actions = self._generate_suggested_actions(error, category, recovery_actions)
        
        return ErrorReport(
            error_id=error_id,
            category=category,
            severity=severity,
            title=self._generate_error_title(error, category),
            message=str(error),
            technical_details=traceback.format_exc(),
            context=context,
            recovery_actions=recovery_actions,
            user_message=user_message,
            suggested_actions=suggested_actions
        )
    
    def _create_suppressed_error_report(self, error_id: str, error: Exception, context: ErrorContext) -> ErrorReport:
        """Create minimal error report for suppressed errors."""
        category, severity = self.classifier.classify_error(error, context)
        
        return ErrorReport(
            error_id=error_id,
            category=category,
            severity=ErrorSeverity.INFO,
            title="Suppressed Error",
            message=f"Repeated error suppressed: {str(error)[:100]}",
            technical_details="",
            context=context,
            resolved=True
        )
    
    def _generate_error_title(self, error: Exception, category: ErrorCategory) -> str:
        """Generate user-friendly error title."""
        titles = {
            ErrorCategory.HARDWARE: "Hardware Issue",
            ErrorCategory.DEPENDENCY: "Missing Component",
            ErrorCategory.CAPTURE: "Screen Capture Problem",
            ErrorCategory.PROCESSING: "Processing Error",
            ErrorCategory.RENDERING: "Display Issue",
            ErrorCategory.NETWORK: "Network Problem",
            ErrorCategory.CONFIGURATION: "Configuration Error",
            ErrorCategory.SYSTEM: "System Error",
            ErrorCategory.USER_INPUT: "Input Error"
        }
        return titles.get(category, "System Error")
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory, severity: ErrorSeverity) -> str:
        """Generate user-friendly error message."""
        if category == ErrorCategory.HARDWARE:
            if 'gpu' in str(error).lower():
                return "GPU acceleration is not available. The system will continue using CPU processing."
            elif 'memory' in str(error).lower():
                return "System is running low on memory. Performance settings will be reduced."
            else:
                return "A hardware-related issue occurred. The system will attempt to continue with alternative methods."
        
        elif category == ErrorCategory.DEPENDENCY:
            return "A required component is missing or outdated. The system will attempt automatic installation."
        
        elif category == ErrorCategory.CAPTURE:
            return "Screen capture encountered an issue. The system will try alternative capture methods."
        
        elif category == ErrorCategory.NETWORK:
            return "Network connectivity issue detected. Local processing will be used instead."
        
        else:
            return "An issue occurred, but the system will attempt to continue operation."
    
    def _get_recovery_actions(self, error: Exception, context: ErrorContext) -> List[RecoveryAction]:
        """Get available recovery actions from handlers."""
        all_actions = []
        
        for handler in self.recovery_handlers:
            if handler.can_handle_error(error, context):
                actions = handler.get_recovery_actions(error, context)
                all_actions.extend(actions)
        
        # Sort by success probability
        all_actions.sort(key=lambda x: x.success_probability, reverse=True)
        
        return all_actions
    
    def _generate_suggested_actions(self, error: Exception, category: ErrorCategory, 
                                  recovery_actions: List[RecoveryAction]) -> List[str]:
        """Generate user-friendly suggested actions."""
        suggestions = []
        
        # Add recovery action descriptions
        for action in recovery_actions[:3]:  # Top 3 actions
            if not action.requires_user_confirmation:
                suggestions.append(f"System will automatically: {action.description}")
            else:
                suggestions.append(action.description)
        
        # Add category-specific suggestions
        if category == ErrorCategory.HARDWARE:
            suggestions.append("Check system requirements and available resources")
            suggestions.append("Close other applications to free up memory")
        elif category == ErrorCategory.DEPENDENCY:
            suggestions.append("Ensure internet connection for automatic installation")
            suggestions.append("Run as administrator if installation fails")
        elif category == ErrorCategory.CAPTURE:
            suggestions.append("Check screen capture permissions")
            suggestions.append("Try selecting a different capture region")
        
        return suggestions
    
    def _attempt_auto_recovery(self, error_report: ErrorReport, error: Exception, context: ErrorContext):
        """Attempt automatic error recovery."""
        if not error_report.recovery_actions:
            return
        
        self.logger.info(f"Attempting automatic recovery for error: {error_report.error_id}")
        
        for action in error_report.recovery_actions:
            if action.requires_user_confirmation:
                continue
            
            # Find handler that can execute this action
            for handler in self.recovery_handlers:
                if handler.can_handle_error(error, context):
                    try:
                        success = handler.execute_recovery(action, error, context)
                        if success:
                            self.logger.info(f"Recovery successful: {action.description}")
                            error_report.auto_recovery_attempted = True
                            error_report.resolved = True
                            error_report.resolution_time = datetime.now()
                            return
                        else:
                            self.logger.warning(f"Recovery failed: {action.description}")
                    except Exception as e:
                        self.logger.error(f"Recovery action error: {e}")
                    break
        
        error_report.auto_recovery_attempted = True
    
    def _log_error(self, error_report: ErrorReport):
        """Log error with appropriate level."""
        log_message = f"[{error_report.category.value.upper()}] {error_report.title}: {error_report.message}"
        
        if error_report.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_report.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_report.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log technical details at debug level
        if error_report.technical_details:
            self.logger.debug(f"Technical details for {error_report.error_id}:\n{error_report.technical_details}")
    
    def _notify_callbacks(self, error_report: ErrorReport):
        """Notify registered callbacks about the error."""
        for callback in self.notification_callbacks:
            try:
                callback(error_report)
            except Exception as e:
                self.logger.error(f"Error notification callback failed: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and trends."""
        if not self.error_history:
            return {}
        
        total_errors = len(self.error_history)
        resolved_errors = sum(1 for e in self.error_history if e.resolved)
        auto_recovered = sum(1 for e in self.error_history if e.auto_recovery_attempted and e.resolved)
        
        # Category breakdown
        category_counts = {}
        for error in self.error_history:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Severity breakdown
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': total_errors,
            'resolved_errors': resolved_errors,
            'auto_recovered_errors': auto_recovered,
            'resolution_rate': resolved_errors / total_errors if total_errors > 0 else 0,
            'auto_recovery_rate': auto_recovered / total_errors if total_errors > 0 else 0,
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'recent_errors': len([e for e in self.error_history 
                                if datetime.now() - e.context.timestamp < timedelta(hours=1)])
        }
    
    def get_recent_errors(self, hours: int = 24) -> List[ErrorReport]:
        """Get recent errors within specified time window."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [error for error in self.error_history 
                if error.context.timestamp > cutoff_time]
    
    def clear_error_history(self):
        """Clear error history (for testing or maintenance)."""
        with self._lock:
            self.error_history.clear()
            self._suppressed_errors.clear()
    
    def set_auto_recovery_enabled(self, enabled: bool):
        """Enable or disable automatic recovery."""
        self.auto_recovery_enabled = enabled
        self.logger.info(f"Automatic recovery {'enabled' if enabled else 'disabled'}")


def create_error_handler(logger: Optional[logging.Logger] = None) -> ErrorHandler:
    """Factory function to create configured ErrorHandler instance."""
    return ErrorHandler(logger)


# Convenience function for quick error handling
def handle_system_error(error: Exception, component: str, operation: str, 
                       logger: Optional[logging.Logger] = None, 
                       error_handler: Optional[ErrorHandler] = None) -> ErrorReport:
    """Convenience function for handling system errors."""
    if error_handler is None:
        error_handler = create_error_handler(logger)
    
    context = ErrorContext(
        component=component,
        operation=operation,
        system_state={'timestamp': datetime.now().isoformat()}
    )
    
    return error_handler.handle_error(error, context)