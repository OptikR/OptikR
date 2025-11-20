"""
Overlay Tracker Module

Tracks active overlays and their source text regions to enable auto-hiding
when the source text disappears from the screen.
"""

import time
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class TrackedOverlay:
    """Information about a tracked overlay."""
    overlay_id: str
    text: str
    position: Tuple[int, int]
    source_region: Tuple[int, int, int, int]  # (x, y, width, height)
    last_seen: float  # timestamp
    confidence: float


class OverlayTracker:
    """
    Tracks active overlays and their source text regions.
    
    Enables auto-hiding overlays when source text disappears.
    """
    
    def __init__(self, disappear_threshold: float = 2.0):
        """
        Initialize overlay tracker.
        
        Args:
            disappear_threshold: Seconds without seeing text before considering it disappeared
        """
        self.tracked_overlays: Dict[str, TrackedOverlay] = {}
        self.disappear_threshold = disappear_threshold
        self.enabled = True
    
    def track_overlay(self, overlay_id: str, text: str, position: Tuple[int, int],
                     source_region: Tuple[int, int, int, int], confidence: float = 1.0):
        """
        Start tracking an overlay.
        
        Args:
            overlay_id: Unique overlay identifier
            text: Original text
            position: Overlay position (x, y)
            source_region: Source text region (x, y, width, height)
            confidence: Detection confidence
        """
        self.tracked_overlays[overlay_id] = TrackedOverlay(
            overlay_id=overlay_id,
            text=text,
            position=position,
            source_region=source_region,
            last_seen=time.time(),
            confidence=confidence
        )
    
    def update_overlay(self, overlay_id: str, still_visible: bool = True):
        """
        Update overlay tracking status.
        
        Args:
            overlay_id: Overlay to update
            still_visible: Whether the source text is still visible
        """
        if overlay_id in self.tracked_overlays:
            if still_visible:
                self.tracked_overlays[overlay_id].last_seen = time.time()
    
    def check_disappeared_overlays(self) -> List[str]:
        """
        Check for overlays whose source text has disappeared.
        
        Returns:
            List of overlay IDs that should be hidden
        """
        if not self.enabled:
            return []
        
        current_time = time.time()
        disappeared = []
        
        for overlay_id, tracked in list(self.tracked_overlays.items()):
            time_since_seen = current_time - tracked.last_seen
            
            if time_since_seen > self.disappear_threshold:
                disappeared.append(overlay_id)
        
        return disappeared
    
    def remove_overlay(self, overlay_id: str):
        """
        Stop tracking an overlay.
        
        Args:
            overlay_id: Overlay to stop tracking
        """
        if overlay_id in self.tracked_overlays:
            del self.tracked_overlays[overlay_id]
    
    def clear_all(self):
        """Clear all tracked overlays."""
        self.tracked_overlays.clear()
    
    def get_tracked_count(self) -> int:
        """Get number of tracked overlays."""
        return len(self.tracked_overlays)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable tracking."""
        self.enabled = enabled
        if not enabled:
            self.clear_all()
