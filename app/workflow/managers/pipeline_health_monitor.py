"""
Pipeline Health Monitor

Monitors pipeline health with automatic recovery and self-healing capabilities.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """A health check configuration."""
    name: str
    check_func: Callable[[], bool]
    interval: float = 5.0
    timeout: float = 2.0
    failure_threshold: int = 3
    recovery_threshold: int = 2
    recovery_action: Optional[Callable] = None


@dataclass
class HealthReport:
    """Health check report."""
    check_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None


class PipelineHealthMonitor:
    """
    Monitors pipeline health and triggers automatic recovery.
    
    Features:
    - Continuous health monitoring
    - Automatic recovery triggers
    - Performance degradation detection
    - Self-healing capabilities
    - Health status reporting
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self.logger = logging.getLogger(__name__)
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_reports: Dict[str, HealthReport] = {}
        
        # Monitoring control
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Recovery control
        self.recovery_enabled = True
        self.recovery_cooldown = 60.0  # Seconds between recovery attempts
        self.last_recovery: Dict[str, datetime] = {}
        
        # Global health
        self.overall_status = HealthStatus.HEALTHY
        
        self.lock = threading.RLock()
        
        self.logger.info("Pipeline Health Monitor initialized")
    
    def register_health_check(self, health_check: HealthCheck):
        """
        Register a health check.
        
        Args:
            health_check: Health check configuration
        """
        with self.lock:
            self.health_checks[health_check.name] = health_check
            self.health_reports[health_check.name] = HealthReport(
                check_name=health_check.name,
                status=HealthStatus.HEALTHY,
                message="Not yet checked",
                timestamp=datetime.now()
            )
            self.logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_health_check(self, check_name: str):
        """
        Unregister a health check.
        
        Args:
            check_name: Name of check to remove
        """
        with self.lock:
            if check_name in self.health_checks:
                del self.health_checks[check_name]
                del self.health_reports[check_name]
                self.logger.info(f"Unregistered health check: {check_name}")
    
    def start_monitoring(self):
        """Start health monitoring."""
        if self.monitoring:
            self.logger.warning("Health monitoring already running")
            return
        
        self.monitoring = True
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("Health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        check_timers: Dict[str, float] = {}
        
        while not self.stop_event.is_set():
            current_time = time.time()
            
            with self.lock:
                checks_to_run = []
                
                for check_name, health_check in self.health_checks.items():
                    last_check = check_timers.get(check_name, 0)
                    
                    if current_time - last_check >= health_check.interval:
                        checks_to_run.append((check_name, health_check))
                        check_timers[check_name] = current_time
            
            # Run checks (outside lock to avoid blocking)
            for check_name, health_check in checks_to_run:
                self._run_health_check(check_name, health_check)
            
            # Update overall status
            self._update_overall_status()
            
            # Sleep briefly
            time.sleep(0.5)
    
    def _run_health_check(self, check_name: str, health_check: HealthCheck):
        """Run a single health check."""
        try:
            # Run check with timeout
            start_time = time.time()
            result = self._run_with_timeout(
                health_check.check_func,
                timeout=health_check.timeout
            )
            check_time = time.time() - start_time
            
            with self.lock:
                report = self.health_reports[check_name]
                
                if result:
                    # Success
                    report.consecutive_successes += 1
                    report.consecutive_failures = 0
                    report.last_success = datetime.now()
                    
                    # Check if recovered
                    if report.status != HealthStatus.HEALTHY:
                        if report.consecutive_successes >= health_check.recovery_threshold:
                            report.status = HealthStatus.HEALTHY
                            report.message = f"Recovered (check time: {check_time:.2f}s)"
                            self.logger.info(f"Health check {check_name} recovered")
                    else:
                        report.message = f"Healthy (check time: {check_time:.2f}s)"
                else:
                    # Failure
                    report.consecutive_failures += 1
                    report.consecutive_successes = 0
                    report.last_failure = datetime.now()
                    
                    # Determine status based on failures
                    if report.consecutive_failures >= health_check.failure_threshold:
                        if report.consecutive_failures >= health_check.failure_threshold * 2:
                            report.status = HealthStatus.CRITICAL
                        else:
                            report.status = HealthStatus.UNHEALTHY
                        
                        report.message = f"Failed {report.consecutive_failures} times"
                        
                        # Trigger recovery
                        if self.recovery_enabled:
                            self._trigger_recovery(check_name, health_check)
                    else:
                        report.status = HealthStatus.DEGRADED
                        report.message = f"Degraded ({report.consecutive_failures} failures)"
                
                report.timestamp = datetime.now()
                
        except Exception as e:
            self.logger.error(f"Health check {check_name} error: {e}")
            
            with self.lock:
                report = self.health_reports[check_name]
                report.consecutive_failures += 1
                report.status = HealthStatus.UNHEALTHY
                report.message = f"Check error: {str(e)}"
                report.timestamp = datetime.now()
    
    def _run_with_timeout(self, func: Callable, timeout: float) -> bool:
        """Run function with timeout."""
        result = [False]
        exception = [None]
        
        def wrapper():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # Timeout
            return False
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def _trigger_recovery(self, check_name: str, health_check: HealthCheck):
        """Trigger recovery action for a failed check."""
        # Check cooldown
        last_recovery = self.last_recovery.get(check_name)
        if last_recovery:
            elapsed = (datetime.now() - last_recovery).total_seconds()
            if elapsed < self.recovery_cooldown:
                return
        
        if not health_check.recovery_action:
            return
        
        self.logger.warning(f"Triggering recovery for {check_name}")
        
        try:
            health_check.recovery_action()
            self.last_recovery[check_name] = datetime.now()
            self.logger.info(f"Recovery action completed for {check_name}")
        except Exception as e:
            self.logger.error(f"Recovery action failed for {check_name}: {e}")
    
    def _update_overall_status(self):
        """Update overall health status."""
        with self.lock:
            if not self.health_reports:
                self.overall_status = HealthStatus.HEALTHY
                return
            
            # Count statuses
            critical_count = sum(
                1 for r in self.health_reports.values()
                if r.status == HealthStatus.CRITICAL
            )
            unhealthy_count = sum(
                1 for r in self.health_reports.values()
                if r.status == HealthStatus.UNHEALTHY
            )
            degraded_count = sum(
                1 for r in self.health_reports.values()
                if r.status == HealthStatus.DEGRADED
            )
            
            # Determine overall status
            if critical_count > 0:
                self.overall_status = HealthStatus.CRITICAL
            elif unhealthy_count > 0:
                self.overall_status = HealthStatus.UNHEALTHY
            elif degraded_count > 0:
                self.overall_status = HealthStatus.DEGRADED
            else:
                self.overall_status = HealthStatus.HEALTHY
    
    def get_health_report(self, check_name: str) -> Optional[HealthReport]:
        """Get health report for a specific check."""
        with self.lock:
            return self.health_reports.get(check_name)
    
    def get_all_reports(self) -> Dict[str, HealthReport]:
        """Get all health reports."""
        with self.lock:
            return dict(self.health_reports)
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall health status."""
        with self.lock:
            return self.overall_status
    
    def is_healthy(self) -> bool:
        """Check if pipeline is healthy."""
        return self.overall_status == HealthStatus.HEALTHY
    
    def get_unhealthy_checks(self) -> List[str]:
        """Get list of unhealthy checks."""
        with self.lock:
            return [
                name for name, report in self.health_reports.items()
                if report.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
            ]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health summary."""
        with self.lock:
            reports = self.get_all_reports()
            
            status_counts = {
                'healthy': 0,
                'degraded': 0,
                'unhealthy': 0,
                'critical': 0
            }
            
            for report in reports.values():
                status_counts[report.status.value] += 1
            
            return {
                'overall_status': self.overall_status.value,
                'is_healthy': self.is_healthy(),
                'monitoring': self.monitoring,
                'total_checks': len(self.health_checks),
                'status_counts': status_counts,
                'unhealthy_checks': self.get_unhealthy_checks(),
                'recovery_enabled': self.recovery_enabled,
                'checks': {
                    name: {
                        'status': report.status.value,
                        'message': report.message,
                        'consecutive_failures': report.consecutive_failures,
                        'consecutive_successes': report.consecutive_successes,
                        'last_check': report.timestamp.isoformat()
                    }
                    for name, report in reports.items()
                }
            }
    
    def force_check(self, check_name: str) -> bool:
        """
        Force immediate execution of a health check.
        
        Args:
            check_name: Name of check to run
            
        Returns:
            bool: Check result
        """
        health_check = self.health_checks.get(check_name)
        if not health_check:
            self.logger.error(f"Health check {check_name} not found")
            return False
        
        self._run_health_check(check_name, health_check)
        
        report = self.health_reports.get(check_name)
        return report.status == HealthStatus.HEALTHY if report else False
    
    def reset_check(self, check_name: str):
        """Reset a health check to initial state."""
        with self.lock:
            if check_name in self.health_reports:
                self.health_reports[check_name] = HealthReport(
                    check_name=check_name,
                    status=HealthStatus.HEALTHY,
                    message="Reset",
                    timestamp=datetime.now()
                )
                self.logger.info(f"Reset health check: {check_name}")
    
    def enable_recovery(self):
        """Enable automatic recovery."""
        self.recovery_enabled = True
        self.logger.info("Automatic recovery enabled")
    
    def disable_recovery(self):
        """Disable automatic recovery."""
        self.recovery_enabled = False
        self.logger.info("Automatic recovery disabled")
