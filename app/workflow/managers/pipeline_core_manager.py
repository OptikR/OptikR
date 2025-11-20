"""
Pipeline Core Manager

Manages pipeline lifecycle, state transitions, and component coordination.
Provides a clean interface for starting, stopping, pausing, and resuming the pipeline.
"""

import threading
import logging
from enum import Enum
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class PipelineState(Enum):
    """Pipeline execution states with clear transitions."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class PipelineConfig:
    """Configuration for the translation pipeline."""
    # Capture settings
    capture_fps: int = 30
    capture_region: Optional[Any] = None
    
    # OCR settings
    ocr_confidence_threshold: float = 0.7
    ocr_language: str = "en"
    ocr_engine: str = "paddleocr"
    
    # Translation settings
    source_language: str = "en"
    target_language: str = "de"
    translation_confidence_threshold: float = 0.75
    enable_dictionary: bool = True
    enable_caching: bool = True
    translation_engine: str = "marianmt"
    
    # Overlay settings
    enable_overlay: bool = True
    auto_size_text: bool = True
    auto_position_overlay: bool = True
    
    # Performance settings
    enable_multithreading: bool = True
    max_worker_threads: int = 4
    enable_frame_skip: bool = True
    frame_skip_threshold: float = 0.95
    
    # Optimization settings
    enable_roi_detection: bool = True
    enable_parallel_ocr: bool = True
    batch_translation: bool = True
    
    # Experimental features
    experimental_features: list = field(default_factory=list)


class PipelineCoreManager:
    """
    Manages pipeline lifecycle and state transitions.
    
    Responsibilities:
    - State management (IDLE → STARTING → RUNNING → STOPPING → IDLE)
    - Lifecycle control (start, stop, pause, resume)
    - Configuration management
    - Component coordination
    - Thread-safe state transitions
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline core manager.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger(__name__)
        
        # State management
        self._state = PipelineState.IDLE
        self._state_lock = threading.RLock()
        self._state_callbacks: Dict[PipelineState, list] = {state: [] for state in PipelineState}
        
        # Lifecycle management
        self._is_running = False
        self._is_paused = False
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Timing
        self._start_time: Optional[datetime] = None
        self._pause_time: Optional[datetime] = None
        self._total_paused_time: float = 0.0
        
        # Component references (set by pipeline)
        self.components: Dict[str, Any] = {}
        
        self.logger.info("Pipeline Core Manager initialized")
    
    @property
    def state(self) -> PipelineState:
        """Get current pipeline state (thread-safe)."""
        with self._state_lock:
            return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._is_running
    
    @property
    def is_paused(self) -> bool:
        """Check if pipeline is paused."""
        return self._is_paused
    
    @property
    def uptime(self) -> float:
        """Get pipeline uptime in seconds (excluding paused time)."""
        if not self._start_time:
            return 0.0
        
        elapsed = (datetime.now() - self._start_time).total_seconds()
        return elapsed - self._total_paused_time
    
    def register_component(self, name: str, component: Any):
        """
        Register a pipeline component.
        
        Args:
            name: Component name (e.g., 'capture', 'ocr', 'translation')
            component: Component instance
        """
        self.components[name] = component
        self.logger.debug(f"Registered component: {name}")
    
    def register_state_callback(self, state: PipelineState, callback: Callable):
        """
        Register a callback for state transitions.
        
        Args:
            state: State to monitor
            callback: Function to call when entering this state
        """
        self._state_callbacks[state].append(callback)
        self.logger.debug(f"Registered callback for state: {state.value}")
    
    def _transition_state(self, new_state: PipelineState):
        """
        Transition to a new state (thread-safe).
        
        Args:
            new_state: Target state
        """
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            
            self.logger.info(f"State transition: {old_state.value} → {new_state.value}")
            
            # Execute callbacks
            for callback in self._state_callbacks[new_state]:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"State callback error: {e}")
    
    def start(self) -> bool:
        """
        Start the pipeline.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        with self._state_lock:
            if self._state not in [PipelineState.IDLE, PipelineState.ERROR]:
                self.logger.warning(f"Cannot start pipeline from state: {self._state.value}")
                return False
            
            self._transition_state(PipelineState.STARTING)
        
        try:
            # Reset events
            self._stop_event.clear()
            self._pause_event.clear()
            
            # Initialize timing
            self._start_time = datetime.now()
            self._total_paused_time = 0.0
            
            # Set flags
            self._is_running = True
            self._is_paused = False
            
            self._transition_state(PipelineState.RUNNING)
            self.logger.info("Pipeline started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start pipeline: {e}")
            self._transition_state(PipelineState.ERROR)
            return False
    
    def stop(self) -> bool:
        """
        Stop the pipeline.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        with self._state_lock:
            if self._state not in [PipelineState.RUNNING, PipelineState.PAUSED, PipelineState.ERROR]:
                self.logger.warning(f"Cannot stop pipeline from state: {self._state.value}")
                return False
            
            self._transition_state(PipelineState.STOPPING)
        
        try:
            # Signal stop
            self._stop_event.set()
            
            # Resume if paused (to allow clean shutdown)
            if self._is_paused:
                self._pause_event.set()
            
            # Set flags
            self._is_running = False
            self._is_paused = False
            
            self._transition_state(PipelineState.IDLE)
            self.logger.info("Pipeline stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop pipeline: {e}")
            self._transition_state(PipelineState.ERROR)
            return False
    
    def pause(self) -> bool:
        """
        Pause the pipeline.
        
        Returns:
            bool: True if paused successfully, False otherwise
        """
        with self._state_lock:
            if self._state != PipelineState.RUNNING:
                self.logger.warning(f"Cannot pause pipeline from state: {self._state.value}")
                return False
            
            self._transition_state(PipelineState.PAUSED)
        
        try:
            self._pause_time = datetime.now()
            self._is_paused = True
            self._pause_event.clear()
            
            self.logger.info("Pipeline paused")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause pipeline: {e}")
            return False
    
    def resume(self) -> bool:
        """
        Resume the pipeline from paused state.
        
        Returns:
            bool: True if resumed successfully, False otherwise
        """
        with self._state_lock:
            if self._state != PipelineState.PAUSED:
                self.logger.warning(f"Cannot resume pipeline from state: {self._state.value}")
                return False
            
            self._transition_state(PipelineState.RUNNING)
        
        try:
            # Calculate paused duration
            if self._pause_time:
                paused_duration = (datetime.now() - self._pause_time).total_seconds()
                self._total_paused_time += paused_duration
                self._pause_time = None
            
            self._is_paused = False
            self._pause_event.set()
            
            self.logger.info("Pipeline resumed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resume pipeline: {e}")
            return False
    
    def should_stop(self) -> bool:
        """Check if pipeline should stop."""
        return self._stop_event.is_set()
    
    def should_pause(self) -> bool:
        """Check if pipeline should pause."""
        return self._is_paused
    
    def wait_if_paused(self, timeout: Optional[float] = None):
        """
        Wait if pipeline is paused.
        
        Args:
            timeout: Maximum time to wait (None = wait indefinitely)
        """
        if self._is_paused:
            self._pause_event.wait(timeout)
    
    def update_config(self, **kwargs):
        """
        Update pipeline configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self.logger.debug(f"Updated config: {key} = {value}")
            else:
                self.logger.warning(f"Unknown config parameter: {key}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status.
        
        Returns:
            dict: Status information
        """
        return {
            'state': self._state.value,
            'is_running': self._is_running,
            'is_paused': self._is_paused,
            'uptime': self.uptime,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'components': list(self.components.keys())
        }
    
    def reset(self):
        """Reset pipeline to initial state."""
        with self._state_lock:
            if self._state in [PipelineState.RUNNING, PipelineState.PAUSED]:
                self.logger.warning("Cannot reset while pipeline is running")
                return
            
            self._state = PipelineState.IDLE
            self._is_running = False
            self._is_paused = False
            self._stop_event.clear()
            self._pause_event.clear()
            self._start_time = None
            self._pause_time = None
            self._total_paused_time = 0.0
            
            self.logger.info("Pipeline reset to initial state")
