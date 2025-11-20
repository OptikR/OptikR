"""
Overlay System Factory

Creates the appropriate overlay system based on configuration.
Allows switching between thread-based and process-based implementations.
"""

from typing import Any


def create_overlay_system(config_manager=None) -> Any:
    """
    Create overlay system based on configuration.
    
    Checks config setting 'overlay.use_background_process':
    - True: Use process-based overlay system (isolated, guaranteed cleanup)
    - False: Use thread-based overlay system (lower latency, traditional)
    
    Args:
        config_manager: Configuration manager
        
    Returns:
        Overlay system instance (either ProcessBasedOverlaySystem or PyQt6OverlayAdapter)
    """
    use_process = False
    
    if config_manager:
        use_process = config_manager.get_setting('overlay.use_background_process', False)
    
    if use_process:
        print("[OVERLAY FACTORY] Creating PROCESS-BASED overlay system")
        from ui.overlay_process import create_process_overlay_system
        return create_process_overlay_system(config_manager)
    else:
        print("[OVERLAY FACTORY] Creating THREAD-BASED overlay system")
        from ui.overlay_integration import PyQt6OverlayAdapter
        return PyQt6OverlayAdapter(config_manager)


def create_thread_safe_overlay_system(config_manager=None) -> Any:
    """
    Create thread-safe overlay system based on configuration.
    
    Wraps the chosen overlay system in ThreadSafeOverlaySystem for thread safety.
    
    Args:
        config_manager: Configuration manager
        
    Returns:
        ThreadSafeOverlaySystem wrapping the chosen implementation
    """
    use_process = False
    
    if config_manager:
        use_process = config_manager.get_setting('overlay.use_background_process', False)
    
    if use_process:
        print("[OVERLAY FACTORY] Creating PROCESS-BASED thread-safe overlay system")
        from ui.overlay_process import create_process_overlay_system
        overlay_system = create_process_overlay_system(config_manager)
        
        # Process-based system is already thread-safe (uses queues)
        # But wrap it anyway for consistent interface
        from ui.thread_safe_overlay import ThreadSafeOverlaySystem
        return ThreadSafeOverlaySystem(overlay_system)
    else:
        print("[OVERLAY FACTORY] Creating THREAD-BASED thread-safe overlay system")
        from ui.overlay_integration import PyQt6OverlayAdapter
        from ui.thread_safe_overlay import ThreadSafeOverlaySystem
        
        overlay_adapter = PyQt6OverlayAdapter(config_manager)
        return ThreadSafeOverlaySystem(overlay_adapter)
