"""
Crash Reporter
OptikR Translation Overlay System

This module provides comprehensive crash reporting and error handling for production deployment:
- Automatic crash detection and reporting
- Error log collection and analysis
- System state capture at crash time
- Recovery suggestions and automatic recovery attempts
- Crash report generation and submission

Author: Niklas Verhasselt
Date: November 2025
"""

import sys
import os
import traceback
import threading
import time
import json
import platform
import psutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import zipfile
import tempfile

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path

from ..interfaces import ILogger
from ..models import SystemStatus, PerformanceMetrics


@dataclass
class CrashInfo:
    """Crash information data structure"""
    timestamp: str
    exception_type: str
    exception_message: str
    traceback: str
    system_info: Dict[str, Any]
    performance_metrics: Optional[Dict[str, Any]] = None
    system_status: Optional[str] = None
    recent_logs: List[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class SystemSnapshot:
    """System state snapshot at crash time"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_usage: Dict[str, Any]
    network_connections: int
    running_processes: int
    system_uptime: float
    python_version: str
    platform_info: Dict[str, str]


class CrashReporter:
    """
    Comprehensive crash reporter for production troubleshooting.
    
    Features:
    - Automatic crash detection and handling
    - System state capture at crash time
    - Error log collection and analysis
    - Crash report generation with detailed diagnostics
    - Recovery attempt mechanisms
    - Crash report persistence and submission
    """
    
    def __init__(self, logger: Optional[ILogger] = None, 
                 crash_dir: Optional[str] = None):
        """Initialize crash reporter."""
        self.logger = logger
        self.crash_dir = Path(crash_dir) if crash_dir else Path("crash_reports")
        self.crash_dir.mkdir(exist_ok=True)
        
        # State tracking
        self.crash_count = 0
        self.last_crash_time: Optional[datetime] = None
        self.recovery_callbacks: List[Callable[[], bool]] = []
        self.crash_callbacks: List[Callable[[CrashInfo], None]] = []
        
        # System monitoring
        self.system_monitor_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.system_snapshots: List[SystemSnapshot] = []
        self.max_snapshots = 10
        
        # Install exception handler
        self.original_excepthook = sys.excepthook
        sys.excepthook = self._handle_exception
        
        # Install thread exception handler (Python 3.8+)
        if hasattr(threading, 'excepthook'):
            self.original_thread_excepthook = threading.excepthook
            threading.excepthook = self._handle_thread_exception
    
    def add_recovery_callback(self, callback: Callable[[], bool]) -> None:
        """Add recovery callback that returns True if recovery successful."""
        self.recovery_callbacks.append(callback)
    
    def add_crash_callback(self, callback: Callable[[CrashInfo], None]) -> None:
        """Add crash notification callback."""
        self.crash_callbacks.append(callback)
    
    def start_system_monitoring(self) -> None:
        """Start system monitoring for crash context."""
        if self.system_monitor_active:
            return
        
        self.system_monitor_active = True
        self.monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        if self.logger:
            self.logger.log_info("System monitoring started for crash reporting")
    
    def stop_system_monitoring(self) -> None:
        """Stop system monitoring."""
        self.system_monitor_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        if self.logger:
            self.logger.log_info("System monitoring stopped")
    
    def _system_monitor_loop(self) -> None:
        """System monitoring loop (runs in separate thread)."""
        while self.system_monitor_active:
            try:
                snapshot = self._capture_system_snapshot()
                self.system_snapshots.append(snapshot)
                
                # Keep only recent snapshots
                if len(self.system_snapshots) > self.max_snapshots:
                    self.system_snapshots.pop(0)
                
                time.sleep(30)  # Capture every 30 seconds
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in system monitoring: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _capture_system_snapshot(self) -> SystemSnapshot:
        """Capture current system state snapshot."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network and process info
            network_connections = len(psutil.net_connections())
            running_processes = len(psutil.pids())
            
            # Get system uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            
            # Get platform info
            platform_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor()
            }
            
            return SystemSnapshot(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage={
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                network_connections=network_connections,
                running_processes=running_processes,
                system_uptime=uptime,
                python_version=sys.version,
                platform_info=platform_info
            )
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error capturing system snapshot: {e}")
            
            # Return minimal snapshot on error
            return SystemSnapshot(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage={},
                network_connections=0,
                running_processes=0,
                system_uptime=0.0,
                python_version=sys.version,
                platform_info={}
            )
    
    def _handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Handle uncaught exceptions."""
        if exc_type is KeyboardInterrupt:
            # Don't report keyboard interrupts as crashes
            self.original_excepthook(exc_type, exc_value, exc_traceback)
            return
        
        # Create crash info
        crash_info = self._create_crash_info(exc_type, exc_value, exc_traceback)
        
        # Handle the crash
        self._handle_crash(crash_info)
        
        # Call original handler
        self.original_excepthook(exc_type, exc_value, exc_traceback)
    
    def _handle_thread_exception(self, args) -> None:
        """Handle uncaught thread exceptions."""
        exc_type = args.exc_type
        exc_value = args.exc_value
        exc_traceback = args.exc_traceback
        thread = args.thread
        
        if exc_type is KeyboardInterrupt:
            return
        
        # Create crash info with thread information
        crash_info = self._create_crash_info(exc_type, exc_value, exc_traceback)
        crash_info.system_info['thread_name'] = thread.name if thread else 'Unknown'
        crash_info.system_info['thread_id'] = thread.ident if thread else 'Unknown'
        
        # Handle the crash
        self._handle_crash(crash_info)
        
        # Call original handler if available
        if hasattr(self, 'original_thread_excepthook'):
            self.original_thread_excepthook(args)
    
    def _create_crash_info(self, exc_type, exc_value, exc_traceback) -> CrashInfo:
        """Create crash information from exception."""
        # Get traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_string = ''.join(tb_lines)
        
        # Get system info
        system_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture(),
            'processor': platform.processor(),
            'hostname': platform.node(),
            'working_directory': os.getcwd(),
            'command_line': sys.argv,
            'environment_variables': dict(os.environ),
            'loaded_modules': list(sys.modules.keys())
        }
        
        # Get recent logs if logger available
        recent_logs = []
        if self.logger and hasattr(self.logger, 'get_recent_logs'):
            try:
                recent_logs = self.logger.get_recent_logs(100)  # Last 100 log entries
            except:
                pass
        
        return CrashInfo(
            timestamp=datetime.now().isoformat(),
            exception_type=exc_type.__name__ if exc_type else 'Unknown',
            exception_message=str(exc_value) if exc_value else 'Unknown',
            traceback=tb_string,
            system_info=system_info,
            recent_logs=recent_logs
        )
    
    def _handle_crash(self, crash_info: CrashInfo) -> None:
        """Handle crash with reporting and recovery attempts."""
        self.crash_count += 1
        self.last_crash_time = datetime.now()
        
        if self.logger:
            self.logger.log_error(f"Application crash detected: {crash_info.exception_type}: {crash_info.exception_message}")
        
        # Add system snapshots to crash info
        if self.system_snapshots:
            crash_info.system_info['system_snapshots'] = [
                asdict(snapshot) for snapshot in self.system_snapshots
            ]
        
        # Attempt recovery
        recovery_successful = self._attempt_recovery(crash_info)
        crash_info.recovery_attempted = True
        crash_info.recovery_successful = recovery_successful
        
        # Save crash report
        self._save_crash_report(crash_info)
        
        # Notify callbacks
        for callback in self.crash_callbacks:
            try:
                callback(crash_info)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in crash callback: {e}")
    
    def _attempt_recovery(self, crash_info: CrashInfo) -> bool:
        """Attempt automatic recovery from crash."""
        if self.logger:
            self.logger.log_info("Attempting automatic recovery from crash")
        
        recovery_successful = False
        
        for i, callback in enumerate(self.recovery_callbacks):
            try:
                if self.logger:
                    self.logger.log_info(f"Attempting recovery method {i+1}")
                
                success = callback()
                if success:
                    recovery_successful = True
                    if self.logger:
                        self.logger.log_info(f"Recovery method {i+1} successful")
                    break
                else:
                    if self.logger:
                        self.logger.log_warning(f"Recovery method {i+1} failed")
                        
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Recovery method {i+1} raised exception: {e}")
        
        if recovery_successful:
            if self.logger:
                self.logger.log_info("Automatic recovery successful")
        else:
            if self.logger:
                self.logger.log_error("All recovery methods failed")
        
        return recovery_successful
    
    def _save_crash_report(self, crash_info: CrashInfo) -> str:
        """Save crash report to file and return file path."""
        try:
            # Create crash report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            crash_file = self.crash_dir / f"crash_report_{timestamp}.json"
            
            # Save crash info as JSON
            with open(crash_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(crash_info), f, indent=2, default=str)
            
            if self.logger:
                self.logger.log_info(f"Crash report saved to {crash_file}")
            
            # Create crash report package
            package_file = self._create_crash_package(crash_info, crash_file)
            
            return str(package_file)
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to save crash report: {e}")
            return ""
    
    def _create_crash_package(self, crash_info: CrashInfo, crash_file: Path) -> Path:
        """Create comprehensive crash report package."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_file = self.crash_dir / f"crash_package_{timestamp}.zip"
            
            with zipfile.ZipFile(package_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add crash report
                zf.write(crash_file, crash_file.name)
                
                # Add recent log files (EXE-compatible)
                logs_dir = get_app_path("logs")
                if logs_dir.exists():
                    for log_file in logs_dir.glob("*.log"):
                        try:
                            # Only include recent log files (last 7 days)
                            if time.time() - log_file.stat().st_mtime < 7 * 24 * 3600:
                                zf.write(log_file, f"logs/{log_file.name}")
                        except:
                            pass
                
                # Add configuration files (EXE-compatible)
                config_dir = get_app_path("config")
                if config_dir.exists():
                    for config_file in config_dir.glob("*.json"):
                        try:
                            zf.write(config_file, f"config/{config_file.name}")
                        except:
                            pass
                
                # Add system information
                system_info_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False
                )
                try:
                    system_info_file.write("System Information\n")
                    system_info_file.write("==================\n\n")
                    
                    for key, value in crash_info.system_info.items():
                        if key != 'environment_variables':  # Skip env vars for privacy
                            system_info_file.write(f"{key}: {value}\n")
                    
                    system_info_file.close()
                    zf.write(system_info_file.name, "system_info.txt")
                    
                finally:
                    os.unlink(system_info_file.name)
            
            if self.logger:
                self.logger.log_info(f"Crash package created: {package_file}")
            
            return package_file
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to create crash package: {e}")
            return crash_file
    
    def get_crash_statistics(self) -> Dict[str, Any]:
        """Get crash statistics."""
        return {
            'total_crashes': self.crash_count,
            'last_crash_time': self.last_crash_time.isoformat() if self.last_crash_time else None,
            'crash_reports_available': len(list(self.crash_dir.glob("crash_report_*.json"))),
            'crash_packages_available': len(list(self.crash_dir.glob("crash_package_*.zip")))
        }
    
    def cleanup_old_reports(self, max_age_days: int = 30) -> int:
        """Clean up old crash reports and return number of files removed."""
        removed_count = 0
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        try:
            for pattern in ["crash_report_*.json", "crash_package_*.zip"]:
                for file_path in self.crash_dir.glob(pattern):
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            removed_count += 1
                    except:
                        pass
            
            if self.logger and removed_count > 0:
                self.logger.log_info(f"Cleaned up {removed_count} old crash reports")
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error cleaning up crash reports: {e}")
        
        return removed_count
    
    def restore_exception_handlers(self) -> None:
        """Restore original exception handlers."""
        sys.excepthook = self.original_excepthook
        
        if hasattr(self, 'original_thread_excepthook'):
            threading.excepthook = self.original_thread_excepthook
    
    def shutdown(self) -> None:
        """Shutdown crash reporter."""
        self.stop_system_monitoring()
        self.restore_exception_handlers()
        
        if self.logger:
            self.logger.log_info("Crash reporter shutdown complete")


def create_crash_reporter(logger: Optional[ILogger] = None,
                         crash_dir: Optional[str] = None) -> CrashReporter:
    """
    Create crash reporter instance.
    
    Args:
        logger: Optional logger for error reporting
        crash_dir: Optional directory for crash reports
        
    Returns:
        CrashReporter: Configured crash reporter
    """
    return CrashReporter(logger, crash_dir)