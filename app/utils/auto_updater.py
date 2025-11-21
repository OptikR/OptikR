"""
Auto Updater
OptikR Translation Overlay System

This module provides automatic update and self-repair mechanisms for production deployment:
- Automatic update checking and downloading
- Version management and rollback capabilities
- Self-repair mechanisms for corrupted files
- Update scheduling and user notification
- Secure update verification and installation

Author: Niklas Verhasselt
Date: November 2025
"""

import os
import sys
import json
import hashlib
import shutil
import tempfile
import threading
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import zipfile
import subprocess

from ..interfaces import ILogger


class UpdateStatus(Enum):
    """Update status enumeration"""
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    UP_TO_DATE = "up_to_date"
    DISABLED = "disabled"


class UpdateType(Enum):
    """Update type enumeration"""
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"
    HOTFIX = "hotfix"


@dataclass
class VersionInfo:
    """Version information"""
    major: int
    minor: int
    patch: int
    build: Optional[str] = None
    
    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version_str += f"-{self.build}"
        return version_str
    
    def __lt__(self, other: 'VersionInfo') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __eq__(self, other: 'VersionInfo') -> bool:
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)


@dataclass
class UpdateInfo:
    """Update information"""
    version: VersionInfo
    update_type: UpdateType
    download_url: str
    checksum: str
    size_bytes: int
    release_notes: str
    required: bool = False
    min_version: Optional[VersionInfo] = None


@dataclass
class UpdateProgress:
    """Update progress information"""
    status: UpdateStatus
    progress: float  # 0.0 to 1.0
    message: str
    error: Optional[str] = None
    bytes_downloaded: int = 0
    total_bytes: int = 0


class AutoUpdater:
    """
    Automatic updater with self-repair capabilities.
    
    Features:
    - Automatic update checking and downloading
    - Version management and comparison
    - Secure update verification with checksums
    - Rollback capabilities for failed updates
    - Self-repair mechanisms for corrupted files
    - Update scheduling and user notification
    - Background update processing
    """
    
    def __init__(self, logger: Optional[ILogger] = None,
                 update_server_url: Optional[str] = None,
                 current_version: Optional[VersionInfo] = None):
        """Initialize auto updater."""
        self.logger = logger
        self.update_server_url = update_server_url or "https://updates.example.com/api"
        self.current_version = current_version or VersionInfo(1, 0, 0)
        
        # Paths
        self.app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
        self.update_dir = self.app_dir / "updates"
        self.backup_dir = self.app_dir / "backups"
        self.config_file = self.app_dir / "update_config.json"
        
        # Create directories
        self.update_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # State
        self.update_status = UpdateStatus.UP_TO_DATE
        self.available_update: Optional[UpdateInfo] = None
        self.update_progress = UpdateProgress(
            status=UpdateStatus.UP_TO_DATE,
            progress=0.0,
            message="No updates available"
        )
        
        # Configuration
        self.config = self._load_config()
        
        # Callbacks
        self.progress_callbacks: List[Callable[[UpdateProgress], None]] = []
        self.update_available_callbacks: List[Callable[[UpdateInfo], None]] = []
        self.update_completed_callbacks: List[Callable[[bool], None]] = []
        
        # Threading
        self.check_thread: Optional[threading.Thread] = None
        self.download_thread: Optional[threading.Thread] = None
        self.install_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Auto-check timer
        self.auto_check_timer: Optional[threading.Timer] = None
        
        if self.logger:
            self.logger.log_info(f"Auto updater initialized, current version: {self.current_version}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load updater configuration."""
        default_config = {
            "auto_check_enabled": True,
            "auto_check_interval_hours": 24,
            "auto_download_enabled": False,
            "auto_install_enabled": False,
            "check_for_prereleases": False,
            "last_check_time": None,
            "update_channel": "stable",
            "backup_count": 3
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    default_config.update(config)
            
            return default_config
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to load update config: {e}")
            return default_config
    
    def _save_config(self) -> None:
        """Save updater configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to save update config: {e}")
    
    def add_progress_callback(self, callback: Callable[[UpdateProgress], None]) -> None:
        """Add progress update callback."""
        self.progress_callbacks.append(callback)
    
    def add_update_available_callback(self, callback: Callable[[UpdateInfo], None]) -> None:
        """Add update available callback."""
        self.update_available_callbacks.append(callback)
    
    def add_update_completed_callback(self, callback: Callable[[bool], None]) -> None:
        """Add update completed callback."""
        self.update_completed_callbacks.append(callback)
    
    def _update_progress(self, status: UpdateStatus, progress: float, 
                        message: str, error: Optional[str] = None,
                        bytes_downloaded: int = 0, total_bytes: int = 0) -> None:
        """Update progress and notify callbacks."""
        self.update_status = status
        self.update_progress = UpdateProgress(
            status=status,
            progress=progress,
            message=message,
            error=error,
            bytes_downloaded=bytes_downloaded,
            total_bytes=total_bytes
        )
        
        # Notify callbacks
        for callback in self.progress_callbacks:
            try:
                callback(self.update_progress)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in progress callback: {e}")
    
    def _notify_update_available(self, update_info: UpdateInfo) -> None:
        """Notify update available callbacks."""
        for callback in self.update_available_callbacks:
            try:
                callback(update_info)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in update available callback: {e}")
    
    def _notify_update_completed(self, success: bool) -> None:
        """Notify update completed callbacks."""
        for callback in self.update_completed_callbacks:
            try:
                callback(success)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in update completed callback: {e}")
    
    def start_auto_check(self) -> None:
        """Start automatic update checking."""
        if not self.config.get("auto_check_enabled", True):
            if self.logger:
                self.logger.log_info("Auto-check disabled in configuration")
            return
        
        interval_hours = self.config.get("auto_check_interval_hours", 24)
        interval_seconds = interval_hours * 3600
        
        def schedule_next_check():
            if not self.shutdown_event.is_set():
                self.auto_check_timer = threading.Timer(
                    interval_seconds,
                    self._auto_check_worker
                )
                self.auto_check_timer.daemon = True
                self.auto_check_timer.start()
        
        # Check if we should check now
        last_check = self.config.get("last_check_time")
        if last_check:
            try:
                last_check_time = datetime.fromisoformat(last_check)
                next_check_time = last_check_time + timedelta(hours=interval_hours)
                
                if datetime.now() >= next_check_time:
                    # Check now
                    self._auto_check_worker()
                else:
                    # Schedule next check
                    schedule_next_check()
            except:
                # Invalid last check time, check now
                self._auto_check_worker()
        else:
            # No previous check, check now
            self._auto_check_worker()
        
        if self.logger:
            self.logger.log_info(f"Auto-check started with {interval_hours}h interval")
    
    def stop_auto_check(self) -> None:
        """Stop automatic update checking."""
        if self.auto_check_timer:
            self.auto_check_timer.cancel()
            self.auto_check_timer = None
        
        if self.logger:
            self.logger.log_info("Auto-check stopped")
    
    def _auto_check_worker(self) -> None:
        """Auto-check worker (runs in timer thread)."""
        try:
            self.check_for_updates()
            
            # Schedule next check
            if not self.shutdown_event.is_set():
                interval_hours = self.config.get("auto_check_interval_hours", 24)
                interval_seconds = interval_hours * 3600
                
                self.auto_check_timer = threading.Timer(
                    interval_seconds,
                    self._auto_check_worker
                )
                self.auto_check_timer.daemon = True
                self.auto_check_timer.start()
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error in auto-check worker: {e}")
    
    def check_for_updates(self) -> bool:
        """
        Check for available updates.
        
        Returns:
            bool: True if update is available, False otherwise
        """
        if self.update_status == UpdateStatus.CHECKING:
            return False
        
        self.check_thread = threading.Thread(
            target=self._check_for_updates_worker,
            daemon=True
        )
        self.check_thread.start()
        
        return True
    
    def _check_for_updates_worker(self) -> None:
        """Check for updates worker (runs in separate thread)."""
        try:
            self._update_progress(
                UpdateStatus.CHECKING, 0.0,
                "Checking for updates..."
            )
            
            # Update last check time
            self.config["last_check_time"] = datetime.now().isoformat()
            self._save_config()
            
            # Get update information from server
            update_info = self._fetch_update_info()
            
            if update_info and update_info.version > self.current_version:
                self.available_update = update_info
                self._update_progress(
                    UpdateStatus.AVAILABLE, 1.0,
                    f"Update available: {update_info.version}"
                )
                
                # Notify callbacks
                self._notify_update_available(update_info)
                
                # Auto-download if enabled
                if self.config.get("auto_download_enabled", False):
                    self.download_update()
                
            else:
                self.available_update = None
                self._update_progress(
                    UpdateStatus.UP_TO_DATE, 1.0,
                    "Application is up to date"
                )
            
        except Exception as e:
            error_msg = f"Failed to check for updates: {e}"
            if self.logger:
                self.logger.log_error(error_msg)
            
            self._update_progress(
                UpdateStatus.FAILED, 0.0,
                "Update check failed",
                error_msg
            )
    
    def _fetch_update_info(self) -> Optional[UpdateInfo]:
        """Fetch update information from server."""
        try:
            # Prepare request parameters
            params = {
                'current_version': str(self.current_version),
                'channel': self.config.get('update_channel', 'stable'),
                'platform': sys.platform,
                'arch': 'x64' if sys.maxsize > 2**32 else 'x86'
            }
            
            if self.config.get('check_for_prereleases', False):
                params['include_prereleases'] = 'true'
            
            # Make request to update server
            response = requests.get(
                f"{self.update_server_url}/check",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('update_available', False):
                    version_data = data['version']
                    version = VersionInfo(
                        major=version_data['major'],
                        minor=version_data['minor'],
                        patch=version_data['patch'],
                        build=version_data.get('build')
                    )
                    
                    update_type = UpdateType(data.get('update_type', 'patch'))
                    
                    min_version = None
                    if data.get('min_version'):
                        min_ver_data = data['min_version']
                        min_version = VersionInfo(
                            major=min_ver_data['major'],
                            minor=min_ver_data['minor'],
                            patch=min_ver_data['patch']
                        )
                    
                    return UpdateInfo(
                        version=version,
                        update_type=update_type,
                        download_url=data['download_url'],
                        checksum=data['checksum'],
                        size_bytes=data['size_bytes'],
                        release_notes=data.get('release_notes', ''),
                        required=data.get('required', False),
                        min_version=min_version
                    )
            
            elif response.status_code == 204:
                # No update available
                return None
            
            else:
                raise Exception(f"Server returned status {response.status_code}")
            
        except requests.RequestException as e:
            raise Exception(f"Network error: {e}")
        except Exception as e:
            raise Exception(f"Update check error: {e}")
        
        return None
    
    def download_update(self) -> bool:
        """
        Download available update.
        
        Returns:
            bool: True if download started, False otherwise
        """
        if not self.available_update:
            return False
        
        if self.update_status in [UpdateStatus.DOWNLOADING, UpdateStatus.INSTALLING]:
            return False
        
        self.download_thread = threading.Thread(
            target=self._download_update_worker,
            daemon=True
        )
        self.download_thread.start()
        
        return True
    
    def _download_update_worker(self) -> None:
        """Download update worker (runs in separate thread)."""
        try:
            if not self.available_update:
                return
            
            self._update_progress(
                UpdateStatus.DOWNLOADING, 0.0,
                "Downloading update..."
            )
            
            # Download update file
            update_file = self.update_dir / f"update_{self.available_update.version}.zip"
            
            response = requests.get(
                self.available_update.download_url,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.shutdown_event.is_set():
                        return
                    
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        progress = downloaded_size / total_size if total_size > 0 else 0.0
                        self._update_progress(
                            UpdateStatus.DOWNLOADING, progress,
                            f"Downloading update... ({downloaded_size}/{total_size} bytes)",
                            bytes_downloaded=downloaded_size,
                            total_bytes=total_size
                        )
            
            # Verify checksum
            if not self._verify_file_checksum(update_file, self.available_update.checksum):
                raise Exception("Update file checksum verification failed")
            
            self._update_progress(
                UpdateStatus.DOWNLOADING, 1.0,
                "Download completed"
            )
            
            # Auto-install if enabled
            if self.config.get("auto_install_enabled", False):
                self.install_update()
            
        except Exception as e:
            error_msg = f"Failed to download update: {e}"
            if self.logger:
                self.logger.log_error(error_msg)
            
            self._update_progress(
                UpdateStatus.FAILED, 0.0,
                "Download failed",
                error_msg
            )
    
    def install_update(self) -> bool:
        """
        Install downloaded update.
        
        Returns:
            bool: True if installation started, False otherwise
        """
        if not self.available_update:
            return False
        
        update_file = self.update_dir / f"update_{self.available_update.version}.zip"
        if not update_file.exists():
            return False
        
        if self.update_status == UpdateStatus.INSTALLING:
            return False
        
        self.install_thread = threading.Thread(
            target=self._install_update_worker,
            args=(update_file,),
            daemon=True
        )
        self.install_thread.start()
        
        return True
    
    def _install_update_worker(self, update_file: Path) -> None:
        """Install update worker (runs in separate thread)."""
        try:
            self._update_progress(
                UpdateStatus.INSTALLING, 0.0,
                "Installing update..."
            )
            
            # Create backup
            backup_success = self._create_backup()
            if not backup_success:
                raise Exception("Failed to create backup")
            
            self._update_progress(
                UpdateStatus.INSTALLING, 0.2,
                "Backup created, extracting update..."
            )
            
            # Extract update
            temp_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(update_file, 'r') as zf:
                    zf.extractall(temp_dir)
                
                self._update_progress(
                    UpdateStatus.INSTALLING, 0.5,
                    "Update extracted, applying changes..."
                )
                
                # Apply update
                self._apply_update(Path(temp_dir))
                
                self._update_progress(
                    UpdateStatus.INSTALLING, 0.9,
                    "Update applied, cleaning up..."
                )
                
                # Update version info
                self.current_version = self.available_update.version
                self.available_update = None
                
                # Clean up
                update_file.unlink()
                
                self._update_progress(
                    UpdateStatus.COMPLETED, 1.0,
                    f"Update completed successfully to version {self.current_version}"
                )
                
                # Notify completion
                self._notify_update_completed(True)
                
                if self.logger:
                    self.logger.log_info(f"Update completed successfully to version {self.current_version}")
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            error_msg = f"Failed to install update: {e}"
            if self.logger:
                self.logger.log_error(error_msg)
            
            # Attempt rollback
            try:
                self._rollback_update()
                error_msg += " (rollback successful)"
            except Exception as rollback_error:
                error_msg += f" (rollback failed: {rollback_error})"
            
            self._update_progress(
                UpdateStatus.FAILED, 0.0,
                "Installation failed",
                error_msg
            )
            
            # Notify completion with failure
            self._notify_update_completed(False)
    
    def _verify_file_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum."""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Checksum verification error: {e}")
            return False
    
    def _create_backup(self) -> bool:
        """Create backup of current application."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            # Copy current application files
            shutil.copytree(self.app_dir, backup_path, 
                          ignore=shutil.ignore_patterns('updates', 'backups', 'logs', '*.log'))
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            if self.logger:
                self.logger.log_info(f"Backup created: {backup_path}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Backup creation failed: {e}")
            return False
    
    def _apply_update(self, update_dir: Path) -> None:
        """Apply update from extracted directory."""
        # Copy new files
        for item in update_dir.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(update_dir)
                target_path = self.app_dir / relative_path
                
                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(item, target_path)
    
    def _rollback_update(self) -> None:
        """Rollback to previous version."""
        # Find most recent backup
        backups = sorted(self.backup_dir.glob("backup_*"), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not backups:
            raise Exception("No backup available for rollback")
        
        latest_backup = backups[0]
        
        # Remove current files (except critical directories)
        for item in self.app_dir.iterdir():
            if item.name not in ['updates', 'backups', 'logs', 'config']:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        
        # Restore from backup
        for item in latest_backup.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(latest_backup)
                target_path = self.app_dir / relative_path
                
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_path)
        
        if self.logger:
            self.logger.log_info(f"Rollback completed from backup: {latest_backup}")
    
    def _cleanup_old_backups(self) -> None:
        """Clean up old backups."""
        max_backups = self.config.get("backup_count", 3)
        
        backups = sorted(self.backup_dir.glob("backup_*"), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        
        for backup in backups[max_backups:]:
            try:
                shutil.rmtree(backup)
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Failed to remove old backup {backup}: {e}")
    
    def get_update_status(self) -> UpdateProgress:
        """Get current update status."""
        return self.update_progress
    
    def get_available_update(self) -> Optional[UpdateInfo]:
        """Get available update information."""
        return self.available_update
    
    def cancel_update(self) -> bool:
        """Cancel ongoing update operation."""
        if self.update_status in [UpdateStatus.DOWNLOADING, UpdateStatus.INSTALLING]:
            self.shutdown_event.set()
            
            # Wait for threads to finish
            if self.download_thread and self.download_thread.is_alive():
                self.download_thread.join(timeout=5.0)
            
            if self.install_thread and self.install_thread.is_alive():
                self.install_thread.join(timeout=5.0)
            
            self.shutdown_event.clear()
            
            self._update_progress(
                UpdateStatus.UP_TO_DATE, 0.0,
                "Update cancelled"
            )
            
            return True
        
        return False
    
    def shutdown(self) -> None:
        """Shutdown auto updater."""
        self.shutdown_event.set()
        self.stop_auto_check()
        
        # Wait for threads to finish
        for thread in [self.check_thread, self.download_thread, self.install_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=5.0)
        
        if self.logger:
            self.logger.log_info("Auto updater shutdown complete")


def create_auto_updater(logger: Optional[ILogger] = None,
                       update_server_url: Optional[str] = None,
                       current_version: Optional[VersionInfo] = None) -> AutoUpdater:
    """
    Create auto updater instance.
    
    Args:
        logger: Optional logger for error reporting
        update_server_url: Optional update server URL
        current_version: Optional current version info
        
    Returns:
        AutoUpdater: Configured auto updater
    """
    return AutoUpdater(logger, update_server_url, current_version)