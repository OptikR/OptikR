"""
Subprocess Manager - Orchestrates all pipeline stage subprocesses.

Manages:
- Starting/stopping all subprocesses
- Health monitoring
- Automatic restart on crash
- Metrics aggregation
"""

import time
from typing import Dict, Optional
from .subprocesses import CaptureSubprocess, OCRSubprocess, TranslationSubprocess


class SubprocessManager:
    """Manages all pipeline stage subprocesses."""
    
    def __init__(self):
        """Initialize subprocess manager."""
        self.capture_subprocess: Optional[CaptureSubprocess] = None
        self.ocr_subprocess: Optional[OCRSubprocess] = None
        self.translation_subprocess: Optional[TranslationSubprocess] = None
        
        self.all_started = False
        self.start_time = None
    
    def start_all(self, config: Dict) -> bool:
        """
        Start all subprocesses.
        
        Args:
            config: Configuration dictionary with keys:
                - capture: Config for capture subprocess
                - ocr: Config for OCR subprocess
                - translation: Config for translation subprocess
                
        Returns:
            True if all subprocesses started successfully
        """
        print("[SubprocessManager] Starting all subprocesses...")
        self.start_time = time.time()
        
        # Start capture subprocess
        print("[SubprocessManager] Starting capture subprocess...")
        self.capture_subprocess = CaptureSubprocess()
        if not self.capture_subprocess.start(config.get('capture', {})):
            print("[SubprocessManager] Failed to start capture subprocess")
            return False
        
        # Start OCR subprocess
        print("[SubprocessManager] Starting OCR subprocess...")
        self.ocr_subprocess = OCRSubprocess()
        if not self.ocr_subprocess.start(config.get('ocr', {})):
            print("[SubprocessManager] Failed to start OCR subprocess")
            self.stop_all()
            return False
        
        # Start translation subprocess
        print("[SubprocessManager] Starting translation subprocess...")
        self.translation_subprocess = TranslationSubprocess()
        if not self.translation_subprocess.start(config.get('translation', {})):
            print("[SubprocessManager] Failed to start translation subprocess")
            self.stop_all()
            return False
        
        self.all_started = True
        print("[SubprocessManager] All subprocesses started successfully")
        return True
    
    def stop_all(self):
        """Stop all subprocesses gracefully."""
        print("[SubprocessManager] Stopping all subprocesses...")
        
        if self.capture_subprocess:
            self.capture_subprocess.stop()
            self.capture_subprocess = None
        
        if self.ocr_subprocess:
            self.ocr_subprocess.stop()
            self.ocr_subprocess = None
        
        if self.translation_subprocess:
            self.translation_subprocess.stop()
            self.translation_subprocess = None
        
        self.all_started = False
        print("[SubprocessManager] All subprocesses stopped")
    
    def check_health(self) -> Dict[str, bool]:
        """
        Check health of all subprocesses.
        
        Returns:
            Dictionary with health status for each subprocess
        """
        return {
            'capture': self.capture_subprocess.is_alive() if self.capture_subprocess else False,
            'ocr': self.ocr_subprocess.is_alive() if self.ocr_subprocess else False,
            'translation': self.translation_subprocess.is_alive() if self.translation_subprocess else False
        }
    
    def restart_crashed(self) -> Dict[str, bool]:
        """
        Restart any crashed subprocesses.
        
        Returns:
            Dictionary with restart success for each subprocess
        """
        results = {}
        
        # Check and restart capture
        if self.capture_subprocess and self.capture_subprocess.crashed:
            print("[SubprocessManager] Restarting crashed capture subprocess...")
            results['capture'] = self.capture_subprocess.restart()
        
        # Check and restart OCR
        if self.ocr_subprocess and self.ocr_subprocess.crashed:
            print("[SubprocessManager] Restarting crashed OCR subprocess...")
            results['ocr'] = self.ocr_subprocess.restart()
        
        # Check and restart translation
        if self.translation_subprocess and self.translation_subprocess.crashed:
            print("[SubprocessManager] Restarting crashed translation subprocess...")
            results['translation'] = self.translation_subprocess.restart()
        
        return results
    
    def get_all_metrics(self) -> Dict:
        """
        Get metrics from all subprocesses.
        
        Returns:
            Dictionary with metrics for each subprocess
        """
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'manager': {
                'all_started': self.all_started,
                'uptime_seconds': uptime
            },
            'capture': self.capture_subprocess.get_metrics() if self.capture_subprocess else {},
            'ocr': self.ocr_subprocess.get_metrics() if self.ocr_subprocess else {},
            'translation': self.translation_subprocess.get_metrics() if self.translation_subprocess else {}
        }
    
    def are_all_running(self) -> bool:
        """Check if all subprocesses are running."""
        if not self.all_started:
            return False
        
        health = self.check_health()
        return all(health.values())
