"""
Background Process Overlay System

Runs overlays in a separate process for complete isolation and guaranteed cleanup.
One process manages ALL overlays (not one process per overlay).
"""

import multiprocessing
import sys
import time
from typing import Tuple, Optional, Dict, Any
from queue import Empty


def overlay_process_main(command_queue: multiprocessing.Queue, 
                        response_queue: multiprocessing.Queue,
                        config_dict: Dict[str, Any]):
    """
    Main function for overlay process.
    Runs in separate process, manages ALL overlays.
    
    Args:
        command_queue: Queue for receiving commands from main process
        response_queue: Queue for sending responses back
        config_dict: Configuration dictionary
    """
    try:
        # Import Qt in this process
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        
        # Create Qt application in this process
        app = QApplication(sys.argv)
        
        # Create overlay manager
        from ui.overlay_pyqt6 import OverlayManager, OverlayConfig, OverlayStyle
        
        # Load config from config_dict
        config = OverlayConfig()
        
        # Apply settings from config_dict if provided
        if config_dict:
            # Display timeout (convert from ms to ms, already in correct unit)
            if 'display_timeout' in config_dict:
                config.auto_hide_delay = config_dict['display_timeout']
                print(f"[OVERLAY PROCESS] Display timeout set to: {config.auto_hide_delay}ms")
            
            # Animation duration
            if 'animation_duration' in config_dict:
                config.animation_duration = config_dict['animation_duration']
            
            # Click-through
            if 'click_through' in config_dict:
                config.click_through = config_dict['click_through']
            
            # Style settings
            if any(k in config_dict for k in ['font_family', 'font_size', 'text_color', 'bg_color', 'opacity']):
                style = OverlayStyle()
                if 'font_family' in config_dict:
                    style.font_family = config_dict['font_family']
                if 'font_size' in config_dict:
                    style.font_size = config_dict['font_size']
                if 'text_color' in config_dict:
                    style.text_color = config_dict['text_color']
                if 'bg_color' in config_dict:
                    style.bg_color = config_dict['bg_color']
                if 'opacity' in config_dict:
                    style.opacity = config_dict['opacity']
                config.style = style
        
        manager = OverlayManager(config=config)
        
        print("[OVERLAY PROCESS] Started successfully")
        response_queue.put({'status': 'ready'})
        
        # Command processor
        def process_commands():
            """Process commands from main process."""
            try:
                while not command_queue.empty():
                    try:
                        cmd = command_queue.get_nowait()
                        
                        if cmd['action'] == 'show':
                            manager.show_overlay(
                                cmd['id'],
                                cmd['text'],
                                cmd['position']
                            )
                            response_queue.put({'status': 'shown', 'id': cmd['id']})
                        
                        elif cmd['action'] == 'hide':
                            manager.hide_overlay(cmd['id'])
                            response_queue.put({'status': 'hidden', 'id': cmd['id']})
                        
                        elif cmd['action'] == 'hide_all':
                            immediate = cmd.get('immediate', True)
                            manager.hide_all(immediate=immediate)
                            response_queue.put({'status': 'all_hidden'})
                        
                        elif cmd['action'] == 'update':
                            manager.update_overlay(
                                cmd['id'],
                                cmd.get('text'),
                                cmd.get('position')
                            )
                            response_queue.put({'status': 'updated', 'id': cmd['id']})
                        
                        elif cmd['action'] == 'get_count':
                            count = len(manager.active_overlays)
                            response_queue.put({'status': 'count', 'count': count})
                        
                        elif cmd['action'] == 'stop':
                            print("[OVERLAY PROCESS] Received stop command")
                            # Hide all overlays before stopping
                            manager.hide_all(immediate=True)
                            response_queue.put({'status': 'stopped'})
                            # Force immediate exit
                            app.quit()
                            import sys
                            sys.exit(0)  # Force exit immediately
                            return
                    
                    except Empty:
                        break
                    except Exception as e:
                        print(f"[OVERLAY PROCESS] Error processing command: {e}")
                        print(f"[OVERLAY PROCESS] Command was: {cmd if 'cmd' in locals() else 'unknown'}")
                        import traceback
                        traceback.print_exc()
                        response_queue.put({'status': 'error', 'error': str(e)})
            
            except Exception as e:
                print(f"[OVERLAY PROCESS] Fatal error in command processor: {e}")
        
        # Timer to check for commands (every 5ms for faster response)
        timer = QTimer()
        timer.timeout.connect(process_commands)
        timer.start(5)  # Check every 5ms instead of 10ms
        
        # Run Qt event loop
        print("[OVERLAY PROCESS] Starting event loop")
        app.exec()
        print("[OVERLAY PROCESS] Event loop ended")
    
    except Exception as e:
        print(f"[OVERLAY PROCESS] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        response_queue.put({'status': 'error', 'error': str(e)})


class ProcessBasedOverlaySystem:
    """
    Overlay system using background process.
    
    One process manages ALL overlays (not one per overlay).
    Provides complete isolation and guaranteed cleanup.
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize process-based overlay system.
        
        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        
        # Create queues for IPC
        self.command_queue = multiprocessing.Queue()
        self.response_queue = multiprocessing.Queue()
        
        # Prepare config dict
        config_dict = self._load_config_dict()
        
        # Start overlay process
        print("[PROCESS OVERLAY] Starting background process...")
        self.process = multiprocessing.Process(
            target=overlay_process_main,
            args=(self.command_queue, self.response_queue, config_dict),
            daemon=True,
            name="OverlayProcess"
        )
        self.process.start()
        
        # Wait for process to be ready (with timeout)
        ready = False
        for _ in range(50):  # 5 second timeout
            try:
                response = self.response_queue.get(timeout=0.1)
                if response.get('status') == 'ready':
                    ready = True
                    break
            except:
                pass
        
        if ready:
            print(f"[PROCESS OVERLAY] Background process started (PID: {self.process.pid})")
        else:
            print("[PROCESS OVERLAY] WARNING: Process may not have started properly")
        
        self.next_overlay_id = 0
    
    def _load_config_dict(self) -> Dict[str, Any]:
        """Load configuration as dictionary."""
        if not self.config_manager:
            return {}
        
        # Helper to parse color strings to tuples
        def parse_color(color_str: str, default: tuple) -> tuple:
            """Parse color string '255,255,255,255' to tuple (255, 255, 255, 255)."""
            try:
                if isinstance(color_str, str):
                    parts = [int(x.strip()) for x in color_str.split(',')]
                    if len(parts) == 4:
                        return tuple(parts)
                elif isinstance(color_str, (list, tuple)) and len(color_str) == 4:
                    return tuple(color_str)
            except:
                pass
            return default
        
        bg_color = self.config_manager.get_setting('overlay.background_color', '30,30,30,230')
        text_color = self.config_manager.get_setting('overlay.text_color', '255,255,255,255')
        
        return {
            'bg_color': parse_color(bg_color, (30, 30, 30, 230)),
            'text_color': parse_color(text_color, (255, 255, 255, 255)),
            'font_family': self.config_manager.get_setting('overlay.font_family', 'Arial'),
            'font_size': self.config_manager.get_setting('overlay.font_size', 14),
            'display_timeout': self.config_manager.get_setting('overlay.display_timeout', 5000),  # milliseconds, 0 = permanent
        }
    
    def show_translation(self, text: str, position: Tuple[int, int], 
                        translation_id: Optional[str] = None,
                        monitor_id: Optional[int] = None) -> str:
        """
        Show a translation overlay (sends command to process).
        
        Args:
            text: Translation text to display
            position: (x, y) screen position
            translation_id: Optional ID (auto-generated if not provided)
            monitor_id: Optional monitor ID (not used in process version)
            
        Returns:
            Overlay ID
        """
        if translation_id is None:
            translation_id = f"translation_{self.next_overlay_id}"
            self.next_overlay_id += 1
        
        self.command_queue.put({
            'action': 'show',
            'id': translation_id,
            'text': text,
            'position': position
        })
        
        return translation_id
    
    def hide_translation(self, translation_id: str):
        """Hide a specific translation overlay (sends command to process)."""
        self.command_queue.put({
            'action': 'hide',
            'id': translation_id
        })
    
    def hide_all_translations(self, immediate: bool = True):
        """
        Hide all translation overlays (sends command to process).
        
        Args:
            immediate: If True, hide immediately without animation
        """
        print(f"[PROCESS OVERLAY] Sending hide_all command (immediate={immediate})")
        self.command_queue.put({
            'action': 'hide_all',
            'immediate': immediate
        })
        
        # Wait for confirmation (with timeout)
        try:
            response = self.response_queue.get(timeout=1.0)
            if response.get('status') == 'all_hidden':
                print("[PROCESS OVERLAY] All overlays hidden")
        except:
            print("[PROCESS OVERLAY] WARNING: No response from process")
    
    def update_translation(self, translation_id: str, text: Optional[str] = None,
                          position: Optional[Tuple[int, int]] = None):
        """Update an existing translation overlay (sends command to process)."""
        self.command_queue.put({
            'action': 'update',
            'id': translation_id,
            'text': text,
            'position': position
        })
    
    def is_visible(self, translation_id: str) -> bool:
        """Check if translation is visible (not implemented for process version)."""
        # Would require synchronous query to process
        return False
    
    def get_active_count(self) -> int:
        """Get number of active overlays (queries process)."""
        self.command_queue.put({'action': 'get_count'})
        
        try:
            response = self.response_queue.get(timeout=0.5)
            if response.get('status') == 'count':
                return response.get('count', 0)
        except:
            pass
        
        return 0
    
    def get_performance_stats(self):
        """Get performance statistics (not implemented for process version)."""
        return {
            'total_created': 0,
            'total_reused': 0,
            'avg_render_time': 0.0
        }
    
    def stop(self):
        """Stop overlay process."""
        print("[PROCESS OVERLAY] Stopping background process...")
        
        # Send stop command
        self.command_queue.put({'action': 'stop'})
        
        # Wait for process to stop (shorter timeout - 0.5 seconds)
        self.process.join(timeout=0.5)
        
        if self.process.is_alive():
            print("[PROCESS OVERLAY] Process did not stop gracefully, terminating...")
            self.process.terminate()
            self.process.join(timeout=0.3)
            
            if self.process.is_alive():
                print("[PROCESS OVERLAY] Process did not terminate, killing...")
                self.process.kill()
                self.process.join(timeout=0.2)  # Final wait after kill
        
        print("[PROCESS OVERLAY] Background process stopped")
    
    def reload_config(self):
        """Reload configuration (not implemented for process version)."""
        # Process-based system would need to restart to reload config
        # For now, just log that it's not supported
        print("[PROCESS OVERLAY] Config reload not supported (requires process restart)")
    
    def cleanup(self):
        """Cleanup method for compatibility with other overlay systems."""
        self.stop()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            if hasattr(self, 'process') and self.process.is_alive():
                self.stop()
        except:
            pass


def create_process_overlay_system(config_manager=None) -> ProcessBasedOverlaySystem:
    """
    Create process-based overlay system.
    
    Args:
        config_manager: Configuration manager
        
    Returns:
        ProcessBasedOverlaySystem instance
    """
    return ProcessBasedOverlaySystem(config_manager)
