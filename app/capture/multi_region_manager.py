"""
Multi-Region Capture Manager

Manages capturing from multiple regions across multiple monitors simultaneously.
Supports parallel processing and independent frame rates per region.
"""

import threading
import time
import queue
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import logging

try:
    from models import Frame, CaptureRegion, MultiRegionConfig, Rectangle
    from interfaces import ICaptureLayer
except ImportError:
    from app.models import Frame, CaptureRegion, MultiRegionConfig, Rectangle
    from app.interfaces import ICaptureLayer


@dataclass
class RegionCaptureResult:
    """Result of capturing a single region."""
    region_id: str
    frame: Optional[Frame]
    success: bool
    error: Optional[str] = None
    capture_time_ms: float = 0.0


class MultiRegionCaptureManager:
    """
    Manages capturing from multiple regions simultaneously.
    
    Features:
    - Parallel capture from multiple regions
    - Independent FPS per region
    - Per-region error handling
    - Efficient resource management
    """
    
    def __init__(self, capture_layer: ICaptureLayer, config: Optional[MultiRegionConfig] = None):
        """
        Initialize multi-region capture manager.
        
        Args:
            capture_layer: Capture layer implementation
            config: Multi-region configuration
        """
        self.capture_layer = capture_layer
        self.config = config or MultiRegionConfig()
        self.logger = logging.getLogger(__name__)
        
        # Threading
        self.is_running = False
        self.capture_threads: Dict[str, threading.Thread] = {}
        self.result_queues: Dict[str, queue.Queue] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        
        # Callbacks
        self.on_frame_captured: Optional[Callable[[str, Frame], None]] = None
        self.on_capture_error: Optional[Callable[[str, str], None]] = None
        
        # Statistics
        self.capture_stats: Dict[str, Dict] = {}
    
    def start(self) -> bool:
        """
        Start capturing from all enabled regions.
        
        Returns:
            True if started successfully
        """
        if self.is_running:
            self.logger.warning("Multi-region capture already running")
            return False
        
        enabled_regions = self.config.get_enabled_regions()
        if not enabled_regions:
            self.logger.error("No enabled regions to capture")
            return False
        
        self.is_running = True
        
        # Start capture thread for each enabled region
        for region in enabled_regions:
            self._start_region_capture(region)
        
        self.logger.info(f"Started capturing from {len(enabled_regions)} regions")
        return True
    
    def stop(self):
        """Stop capturing from all regions."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Signal all threads to stop
        for region_id, stop_event in self.stop_events.items():
            stop_event.set()
        
        # Wait for threads to finish
        for region_id, thread in self.capture_threads.items():
            if thread.is_alive():
                thread.join(timeout=2.0)
        
        # Clear data structures
        self.capture_threads.clear()
        self.result_queues.clear()
        self.stop_events.clear()
        
        self.logger.info("Stopped multi-region capture")
    
    def _start_region_capture(self, region: CaptureRegion):
        """Start capture thread for a specific region."""
        region_id = region.region_id
        
        # Create queue and stop event
        self.result_queues[region_id] = queue.Queue(maxsize=10)
        self.stop_events[region_id] = threading.Event()
        
        # Initialize stats
        self.capture_stats[region_id] = {
            'frames_captured': 0,
            'frames_failed': 0,
            'average_capture_time_ms': 0.0,
            'last_capture_time': 0.0
        }
        
        # Start capture thread
        thread = threading.Thread(
            target=self._capture_loop,
            args=(region,),
            name=f"CaptureThread-{region_id}",
            daemon=True
        )
        thread.start()
        self.capture_threads[region_id] = thread
        
        self.logger.info(f"Started capture thread for region: {region.name}")
    
    def _capture_loop(self, region: CaptureRegion):
        """Capture loop for a single region."""
        region_id = region.region_id
        stop_event = self.stop_events[region_id]
        result_queue = self.result_queues[region_id]
        
        # FPS control (default 15 FPS)
        frame_interval = 1.0 / 15.0
        last_capture_time = 0.0
        
        while not stop_event.is_set() and self.is_running:
            try:
                # FPS limiting
                current_time = time.time()
                time_since_last = current_time - last_capture_time
                if time_since_last < frame_interval:
                    time.sleep(frame_interval - time_since_last)
                    continue
                
                last_capture_time = current_time
                capture_start = time.time()
                
                # Capture frame from this region
                try:
                    from app.interfaces import CaptureSource
                    frame = self.capture_layer.capture_frame(
                        CaptureSource.CUSTOM_REGION,
                        region
                    )
                    
                    capture_time_ms = (time.time() - capture_start) * 1000
                    
                    if frame:
                        # Update stats
                        stats = self.capture_stats[region_id]
                        stats['frames_captured'] += 1
                        stats['last_capture_time'] = current_time
                        
                        # Update average capture time
                        count = stats['frames_captured']
                        avg = stats['average_capture_time_ms']
                        stats['average_capture_time_ms'] = (avg * (count - 1) + capture_time_ms) / count
                        
                        # Put result in queue (non-blocking)
                        try:
                            result_queue.put_nowait(RegionCaptureResult(
                                region_id=region_id,
                                frame=frame,
                                success=True,
                                capture_time_ms=capture_time_ms
                            ))
                        except queue.Full:
                            # Queue full, skip this frame
                            pass
                        
                        # Call callback if set
                        if self.on_frame_captured:
                            self.on_frame_captured(region_id, frame)
                    else:
                        # Capture failed
                        self.capture_stats[region_id]['frames_failed'] += 1
                        
                except Exception as e:
                    error_msg = f"Capture error for region {region.name}: {e}"
                    self.logger.error(error_msg)
                    self.capture_stats[region_id]['frames_failed'] += 1
                    
                    if self.on_capture_error:
                        self.on_capture_error(region_id, str(e))
                
            except Exception as e:
                self.logger.error(f"Error in capture loop for {region_id}: {e}")
                time.sleep(0.1)  # Prevent tight error loop
        
        self.logger.info(f"Capture loop stopped for region: {region.name}")
    
    def get_latest_frames(self, timeout: float = 0.1) -> List[RegionCaptureResult]:
        """
        Get latest frames from all regions.
        
        Args:
            timeout: Maximum time to wait for frames
            
        Returns:
            List of capture results (one per region)
        """
        results = []
        
        for region_id, result_queue in self.result_queues.items():
            try:
                result = result_queue.get(timeout=timeout)
                results.append(result)
            except queue.Empty:
                # No frame available for this region
                pass
        
        return results
    
    def get_region_stats(self, region_id: str) -> Optional[Dict]:
        """Get capture statistics for a specific region."""
        return self.capture_stats.get(region_id)
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get capture statistics for all regions."""
        return self.capture_stats.copy()
    
    def add_region(self, region: CaptureRegion):
        """
        Add a new region to capture from.
        
        Args:
            region: Region to add
        """
        self.config.add_region(region)
        
        # If already running and region is enabled, start capturing
        if self.is_running and region.enabled:
            self._start_region_capture(region)
    
    def remove_region(self, region_id: str):
        """
        Remove a region from capture.
        
        Args:
            region_id: ID of region to remove
        """
        # Stop capture thread if running
        if region_id in self.stop_events:
            self.stop_events[region_id].set()
            
            if region_id in self.capture_threads:
                thread = self.capture_threads[region_id]
                if thread.is_alive():
                    thread.join(timeout=1.0)
                del self.capture_threads[region_id]
            
            del self.stop_events[region_id]
            del self.result_queues[region_id]
            del self.capture_stats[region_id]
        
        # Remove from config
        self.config.remove_region(region_id)
    
    def enable_region(self, region_id: str):
        """Enable a region and start capturing if manager is running."""
        self.config.enable_region(region_id)
        
        if self.is_running:
            region = self.config.get_region(region_id)
            if region:
                self._start_region_capture(region)
    
    def disable_region(self, region_id: str):
        """Disable a region and stop capturing."""
        self.config.disable_region(region_id)
        
        # Stop capture thread
        if region_id in self.stop_events:
            self.stop_events[region_id].set()
    
    def update_config(self, config: MultiRegionConfig):
        """
        Update the multi-region configuration.
        
        Args:
            config: New configuration
        """
        was_running = self.is_running
        
        # Stop if running
        if was_running:
            self.stop()
        
        # Update config
        self.config = config
        
        # Restart if was running
        if was_running:
            self.start()


def create_multi_region_manager(capture_layer: ICaptureLayer, 
                                config: Optional[MultiRegionConfig] = None) -> MultiRegionCaptureManager:
    """
    Factory function to create multi-region capture manager.
    
    Args:
        capture_layer: Capture layer implementation
        config: Multi-region configuration
        
    Returns:
        MultiRegionCaptureManager instance
    """
    return MultiRegionCaptureManager(capture_layer, config)
