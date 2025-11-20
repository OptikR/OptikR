"""
Overlay Renderer - Unified interface for displaying translation overlays.
"""

import tkinter as tk
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from app.models import Translation, Rectangle
from app.utils.color_contrast import (
    detect_background_color_from_image,
    adjust_colors_for_contrast,
    hex_to_rgb
)

# Try to import intelligent positioning
try:
    from app.overlay.intelligent_positioning import (
        IntelligentPositioningEngine, PositioningContext, PositioningMode
    )
    INTELLIGENT_POSITIONING_AVAILABLE = True
except ImportError:
    INTELLIGENT_POSITIONING_AVAILABLE = False
    print("[INFO] Intelligent positioning not available, using basic positioning")


class SimpleOverlayWindow:
    """Simple overlay window for displaying translations."""
    
    def __init__(self, root: tk.Tk, config: Dict[str, Any] = None):
        """Initialize overlay window."""
        self.root = root
        self.window = None
        self.label = None
        self.config = config or {}
        self.position = None  # Store current position for collision detection
        
    def show(self, translation: Translation):
        """Show translation in overlay (must be called from main thread)."""
        def _show_on_main_thread():
            try:
                if self.window is None:
                    # Get config values
                    font_family = self.config.get('font_family', 'Segoe UI')
                    
                    # Determine font size based on auto_font_size setting
                    auto_font_size_enabled = self.config.get('auto_font_size', True)
                    base_font_size = self.config.get('font_size', 10)
                    
                    if auto_font_size_enabled and hasattr(translation, 'estimated_font_size') and translation.estimated_font_size:
                        # Use estimated font size from OCR, but ensure it's not too small
                        font_size = max(base_font_size, translation.estimated_font_size)
                    else:
                        # Use configured font size
                        font_size = base_font_size
                    
                    font_weight = self.config.get('font_weight', 'normal')
                    bg_color = self.config.get('bg_color', '#2D2D30')
                    fg_color = self.config.get('fg_color', '#FFFFFF')
                    border_color = self.config.get('border_color', '#007ACC')
                    opacity = self.config.get('opacity', 0.85)
                    
                    # Scale padding based on font size
                    base_padding_x = self.config.get('padding_x', 6)
                    base_padding_y = self.config.get('padding_y', 3)
                    padding_x = max(4, int(base_padding_x * (font_size / 10)))
                    padding_y = max(2, int(base_padding_y * (font_size / 10)))
                    
                    # Create overlay window
                    self.window = tk.Toplevel(self.root)
                    self.window.overrideredirect(True)  # Remove window decorations
                    self.window.attributes('-topmost', True)  # Always on top
                    self.window.attributes('-alpha', opacity)  # Transparency
                    
                    # Make window click-through (transparent to mouse events)
                    # Check if interactive mode is enabled
                    interactive_on_hover = self.config.get('interactive_on_hover', False)
                    
                    try:
                        # Windows-specific: Make window transparent to mouse clicks
                        import ctypes
                        hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id())
                        
                        # Store hwnd for later use
                        self.hwnd = hwnd
                        
                        # Set click-through by default
                        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                        style = style | 0x00000020  # WS_EX_TRANSPARENT
                        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
                        
                        # If interactive on hover is enabled, bind mouse events
                        if interactive_on_hover:
                            def on_enter(event):
                                # Remove click-through when mouse enters
                                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                                style = style & ~0x00000020  # Remove WS_EX_TRANSPARENT
                                ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
                            
                            def on_leave(event):
                                # Restore click-through when mouse leaves
                                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                                style = style | 0x00000020  # Add WS_EX_TRANSPARENT
                                ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
                            
                            self.window.bind('<Enter>', on_enter)
                            self.window.bind('<Leave>', on_leave)
                        
                    except Exception as e:
                        print(f"[DEBUG] Could not set click-through: {e}")
                    
                    # Build font tuple
                    if font_weight == 'bold':
                        font = (font_family, font_size, 'bold')
                    else:
                        font = (font_family, font_size)
                    
                    # Create label with configured settings
                    self.label = tk.Label(
                        self.window,
                        text="",
                        font=font,
                        bg=bg_color,
                        fg=fg_color,
                        padx=padding_x,
                        pady=padding_y,
                        relief="flat",
                        borderwidth=1,
                        highlightthickness=1,
                        highlightbackground=border_color
                    )
                    self.label.pack()
                
                # Update text - use word wrapping instead of truncation
                text = translation.translated_text
                max_line_length = self.config.get('max_text_width', 60)
                
                # Word wrap long text
                if len(text) > max_line_length:
                    words = text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words:
                        if len(current_line) + len(word) + 1 <= max_line_length:
                            current_line += (" " + word if current_line else word)
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    
                    if current_line:
                        lines.append(current_line)
                    
                    text = "\n".join(lines)
                
                self.label.config(text=text)
                
                # Position overlay - use coordinates from translation.position directly
                # The translation.position should already be in screen coordinates
                # (either from OCR or from positioning engine)
                x = translation.position.x
                y = translation.position.y
                
                # Try to get capture region offset from translation metadata
                if hasattr(translation, 'metadata') and translation.metadata:
                    region_x = translation.metadata.get('region_x', 0)
                    region_y = translation.metadata.get('region_y', 0)
                    x += region_x
                    y += region_y
                
                # Update window to get size
                self.window.update_idletasks()
                
                # Get window size
                window_width = self.window.winfo_width()
                window_height = self.window.winfo_height()
                
                # Only apply screen boundary checks (no repositioning logic)
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                screen_margin = self.config.get('screen_margin', 10)
                
                # Clamp to screen boundaries only if overlay would go off-screen
                if x + window_width > screen_width - screen_margin:
                    x = screen_width - window_width - screen_margin
                if x < screen_margin:
                    x = screen_margin
                
                if y + window_height > screen_height - screen_margin:
                    y = screen_height - window_height - screen_margin
                if y < screen_margin:
                    y = screen_margin
                
                # Store position for collision detection
                self.position = Rectangle(x=x, y=y, width=window_width, height=window_height)
                
                # Position window
                self.window.geometry(f"+{x}+{y}")
                self.window.deiconify()
                
            except Exception as e:
                print(f"[ERROR] Failed to show overlay: {e}")
                import traceback
                traceback.print_exc()
        
        # Schedule on main thread
        try:
            self.root.after(0, _show_on_main_thread)
        except Exception as e:
            print(f"[ERROR] Failed to schedule overlay: {e}")
    
    def hide(self):
        """Hide overlay window."""
        def _hide_on_main_thread():
            try:
                if self.window:
                    self.window.withdraw()
            except:
                pass
        
        try:
            self.root.after(0, _hide_on_main_thread)
        except:
            pass
    
    def destroy(self):
        """Destroy overlay window."""
        def _destroy_on_main_thread():
            try:
                if self.window:
                    self.window.destroy()
                    self.window = None
                    self.label = None
            except:
                pass
        
        try:
            self.root.after(0, _destroy_on_main_thread)
        except:
            pass


class OverlayRenderer:
    """
    Unified overlay renderer that manages translation display.
    Simple implementation using Tkinter overlays with intelligent positioning.
    """
    
    def __init__(self, config_manager=None):
        """Initialize the overlay renderer."""
        self.root = None
        self.overlays: List[SimpleOverlayWindow] = []
        self.initialized = False
        self.positioning_engine = None
        self.use_smart_positioning = True
        self.capture_region = None  # Store capture region for coordinate translation
        self.config_manager = config_manager  # Store config manager for reading settings
        
        # Load positioning mode from config
        self.positioning_mode = "intelligent"  # Default
        if self.config_manager:
            self.positioning_mode = self.config_manager.get_setting('overlay.positioning_mode', 'intelligent')
        
        # Default overlay settings (can be overridden)
        self.font_family = "Segoe UI"
        self.font_size = 10
        self.auto_font_size = True  # Auto-adjust font size based on detected text size
        self.font_weight = "normal"
        self.bg_color = "#2D2D30"
        self.fg_color = "#FFFFFF"
        self.border_color = "#007ACC"
        self.opacity = 0.85
        self.padding_x = 6
        self.padding_y = 3
        self.max_text_width = 60  # Maximum characters per line
        self.screen_margin = 10  # Minimum margin from screen edges
        self.collision_avoidance = True  # Enable collision avoidance
        
        # Load auto font size setting from config
        if self.config_manager:
            self.auto_font_size = self.config_manager.get_setting('overlay.auto_font_size', True)
        
        # Auto-contrast settings
        self.auto_contrast_enabled = False
        if self.config_manager:
            self.auto_contrast_enabled = self.config_manager.get_setting('overlay.auto_contrast_enabled', False)
        
    def initialize(self, root: tk.Tk = None):
        """
        Initialize the overlay system with a Tkinter root.
        
        Args:
            root: Optional Tkinter root window
        """
        try:
            if root is None:
                print("[WARNING] No root window provided for overlay renderer")
                return
            
            self.root = root
            
            # Initialize intelligent positioning if available
            if INTELLIGENT_POSITIONING_AVAILABLE and self.use_smart_positioning:
                try:
                    screen_width = root.winfo_screenwidth()
                    screen_height = root.winfo_screenheight()
                    context = PositioningContext(
                        screen_width=screen_width,
                        screen_height=screen_height
                    )
                    self.positioning_engine = IntelligentPositioningEngine(context)
                    print("[OK] Intelligent positioning enabled")
                except Exception as e:
                    print(f"[WARNING] Failed to initialize intelligent positioning: {e}")
                    self.positioning_engine = None
            
            self.initialized = True
            
            # Try to load overlay config from models
            self._load_overlay_config()
            
            print("[OK] Overlay renderer initialized")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize overlay renderer: {e}")
            import traceback
            traceback.print_exc()
            self.initialized = False
    
    def _load_overlay_config(self):
        """Load overlay configuration from models.OverlayConfig if available."""
        try:
            from app.models import OverlayConfig
            config = OverlayConfig()
            
            # Apply config settings
            self.font_family = config.font_family
            self.font_size = config.font_size
            self.bg_color = f"#{config.background_color[0]:02x}{config.background_color[1]:02x}{config.background_color[2]:02x}"
            self.fg_color = f"#{config.text_color[0]:02x}{config.text_color[1]:02x}{config.text_color[2]:02x}"
            self.opacity = config.opacity
            
            if config.border_enabled:
                self.border_color = f"#{config.border_color[0]:02x}{config.border_color[1]:02x}{config.border_color[2]:02x}"
            
            print(f"[CONFIG] Loaded overlay settings: {self.font_family} {self.font_size}pt, opacity={self.opacity}")
            
        except Exception as e:
            print(f"[DEBUG] Using default overlay settings: {e}")
    
    def set_config(self, config: Dict[str, Any]):
        """
        Update overlay configuration.
        
        Args:
            config: Dictionary with overlay settings
        """
        try:
            if 'font_family' in config:
                self.font_family = config['font_family']
            if 'font_size' in config:
                self.font_size = config['font_size']
            if 'bg_color' in config:
                self.bg_color = config['bg_color']
            if 'fg_color' in config:
                self.fg_color = config['fg_color']
            if 'opacity' in config:
                self.opacity = config['opacity']
            if 'border_color' in config:
                self.border_color = config['border_color']
            if 'interactive_on_hover' in config:
                self.interactive_on_hover = config['interactive_on_hover']
            if 'max_text_width' in config:
                self.max_text_width = config['max_text_width']
            if 'screen_margin' in config:
                self.screen_margin = config['screen_margin']
            if 'collision_avoidance' in config:
                self.collision_avoidance = config['collision_avoidance']
            if 'capture_region' in config:
                self.capture_region = config['capture_region']
            
            print(f"[CONFIG] Overlay settings updated")
            
        except Exception as e:
            print(f"[WARNING] Failed to update overlay config: {e}")
    
    def set_overlay_style(self, style: Dict[str, Any]):
        """
        Set overlay styling configuration (alias for set_config for interface compatibility).
        
        Args:
            style: Dictionary with overlay style settings
        """
        self.set_config(style)
    
    def set_positioning_mode(self, mode: str):
        """
        Set the positioning mode for overlays.
        
        Args:
            mode: Positioning mode - "simple" (use OCR coords exactly), 
                  "intelligent" (smart positioning with collision avoidance),
                  or "flow_based" (follow text flow direction)
        """
        valid_modes = ["simple", "intelligent", "flow_based"]
        if mode in valid_modes:
            self.positioning_mode = mode
            print(f"[CONFIG] Positioning mode set to: {mode}")
        else:
            print(f"[WARNING] Invalid positioning mode '{mode}'. Valid modes: {valid_modes}")
    
    def render(self, frame, translations: list):
        """
        Render multiple translations on screen with intelligent positioning and collision avoidance.
        
        Args:
            frame: Captured frame
            translations: List of Translation objects to display
        """
        if not self.initialized or not self.root:
            return
        
        try:
            # Hide old overlays
            self.hide_all_overlays()
            
            # Apply intelligent positioning if available and enabled
            if self.positioning_engine and translations and self.use_smart_positioning:
                try:
                    if INTELLIGENT_POSITIONING_AVAILABLE:
                        # Determine positioning mode
                        from app.overlay.intelligent_positioning import PositioningMode
                        
                        mode_map = {
                            "simple": PositioningMode.SIMPLE,
                            "intelligent": PositioningMode.INTELLIGENT,
                            "flow_based": PositioningMode.FLOW_BASED
                        }
                        
                        mode = mode_map.get(self.positioning_mode, PositioningMode.INTELLIGENT)
                        
                        # Use intelligent positioning engine
                        positioned_translations = self.positioning_engine.calculate_optimal_positions(
                            translations, 
                            frame,
                            mode
                        )
                        translations = positioned_translations
                        print(f"[DEBUG] Applied {self.positioning_mode} positioning to {len(translations)} translations")
                except Exception as e:
                    # Log error and fall back to original positions
                    print(f"[WARNING] Intelligent positioning failed: {e}, using basic positioning")
            
            # Show each translation with collision avoidance
            existing_positions = []
            for translation in translations:
                # Apply collision avoidance if enabled
                if self.collision_avoidance and existing_positions:
                    translation = self._apply_collision_avoidance(translation, existing_positions)
                
                # Show translation (pass frame for auto-contrast)
                frame_data = frame.data if hasattr(frame, 'data') else frame
                overlay_id = self.show_translation(translation, frame=frame_data)
                
                # Track position for collision detection
                if overlay_id is not None and overlay_id < len(self.overlays):
                    overlay = self.overlays[overlay_id]
                    if overlay.position:
                        existing_positions.append(overlay.position)
                
        except Exception as e:
            print(f"[ERROR] Failed to render translations: {e}")
            import traceback
            traceback.print_exc()
    
    def show_translation(self, translation: Translation, frame: Optional[np.ndarray] = None) -> Optional[int]:
        """
        Display a translation overlay.
        
        Args:
            translation: Translation object to display
            frame: Optional frame data for auto-contrast detection
            
        Returns:
            Overlay ID if successful, None otherwise
        """
        if not self.initialized or not self.root:
            return None
        
        try:
            # Determine colors (with auto-contrast if enabled)
            fg_color = self.fg_color
            bg_color = self.bg_color
            
            if self.auto_contrast_enabled and frame is not None and hasattr(translation, 'position'):
                try:
                    # Detect background color at translation position
                    pos_x = translation.position.x if hasattr(translation.position, 'x') else 0
                    pos_y = translation.position.y if hasattr(translation.position, 'y') else 0
                    
                    detected_bg = detect_background_color_from_image(
                        frame, 
                        (pos_x, pos_y),
                        sample_size=30
                    )
                    
                    # Adjust colors for optimal contrast
                    fg_color, bg_color = adjust_colors_for_contrast(
                        self.fg_color,
                        self.bg_color,
                        detected_bg
                    )
                    
                except Exception as e:
                    # Silently fall back to default colors if detection fails
                    print(f"[DEBUG] Auto-contrast failed, using default colors: {e}")
            
            # Create config dict for overlay window
            config = {
                'font_family': self.font_family,
                'font_size': self.font_size,
                'auto_font_size': self.auto_font_size,
                'font_weight': self.font_weight,
                'bg_color': bg_color,
                'fg_color': fg_color,
                'border_color': self.border_color,
                'opacity': self.opacity,
                'padding_x': self.padding_x,
                'padding_y': self.padding_y,
                'interactive_on_hover': getattr(self, 'interactive_on_hover', False),
                'max_text_width': self.max_text_width,
                'screen_margin': self.screen_margin
            }
            
            # Create new overlay window with config
            overlay = SimpleOverlayWindow(self.root, config)
            overlay.show(translation)
            self.overlays.append(overlay)
            
            return len(self.overlays) - 1
            
        except Exception as e:
            print(f"[ERROR] Failed to show translation overlay: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def hide(self):
        """Hide all overlays (alias for hide_all_overlays)."""
        self.hide_all_overlays()
    
    def hide_overlay(self, overlay_id: int):
        """
        Hide a specific overlay.
        
        Args:
            overlay_id: ID of the overlay to hide
        """
        try:
            if 0 <= overlay_id < len(self.overlays):
                self.overlays[overlay_id].hide()
                
        except Exception as e:
            print(f"[ERROR] Failed to hide overlay: {e}")
    
    def hide_all_overlays(self):
        """Hide all active overlays."""
        try:
            for overlay in self.overlays:
                overlay.hide()
            
        except Exception as e:
            print(f"[ERROR] Failed to hide all overlays: {e}")
    
    def toggle_overlay(self, visible: bool):
        """
        Toggle overlay visibility.
        
        Args:
            visible: True to show overlays, False to hide them
        """
        try:
            if visible:
                # Overlays will be shown when render() is called with translations
                pass
            else:
                # Hide all overlays
                self.hide_all_overlays()
        except Exception as e:
            print(f"[ERROR] Failed to toggle overlay: {e}")
    
    def _apply_collision_avoidance(self, translation: Translation, 
                                  existing_positions: List[Rectangle]) -> Translation:
        """
        Adjust translation position to avoid collisions with existing overlays.
        
        Args:
            translation: Translation to adjust
            existing_positions: List of existing overlay positions
            
        Returns:
            Translation with adjusted position
        """
        try:
            # Get original position
            original_pos = translation.position
            
            # Estimate overlay size
            text_width, text_height = self._estimate_text_size(translation.translated_text)
            
            # Try different positions to avoid collisions
            positions_to_try = [
                # Above
                Rectangle(original_pos.x, original_pos.y - text_height - 10, text_width, text_height),
                # Below
                Rectangle(original_pos.x, original_pos.y + original_pos.height + 10, text_width, text_height),
                # Left
                Rectangle(original_pos.x - text_width - 10, original_pos.y, text_width, text_height),
                # Right
                Rectangle(original_pos.x + original_pos.width + 10, original_pos.y, text_width, text_height),
                # Offset above-right
                Rectangle(original_pos.x + 20, original_pos.y - text_height - 10, text_width, text_height),
                # Offset below-right
                Rectangle(original_pos.x + 20, original_pos.y + original_pos.height + 10, text_width, text_height),
            ]
            
            # Find position with fewest collisions
            best_position = original_pos
            min_collisions = float('inf')
            
            for candidate_pos in positions_to_try:
                # Check if position is on screen
                if not self._is_position_on_screen(candidate_pos):
                    continue
                
                # Count collisions
                collision_count = self._count_collisions(candidate_pos, existing_positions)
                
                if collision_count < min_collisions:
                    min_collisions = collision_count
                    best_position = candidate_pos
                    
                    # If no collisions, use this position
                    if collision_count == 0:
                        break
            
            # Create new translation with adjusted position
            adjusted_translation = Translation(
                original_text=translation.original_text,
                translated_text=translation.translated_text,
                source_language=translation.source_language,
                target_language=translation.target_language,
                position=best_position,
                confidence=translation.confidence,
                engine_used=translation.engine_used
            )
            
            # Copy metadata if present
            if hasattr(translation, 'metadata'):
                adjusted_translation.metadata = translation.metadata
            
            return adjusted_translation
            
        except Exception as e:
            print(f"[WARNING] Collision avoidance failed: {e}")
            return translation
    
    def _estimate_text_size(self, text: str) -> Tuple[int, int]:
        """
        Estimate text size for collision detection.
        
        Args:
            text: Text to measure
            
        Returns:
            Tuple of (width, height) in pixels
        """
        # Character width estimation based on font
        char_width = self.font_size * 0.6
        line_height = self.font_size * 1.5
        
        # Handle multi-line text
        lines = text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else len(text)
        
        width = int(max_line_length * char_width) + self.padding_x * 2
        height = int(len(lines) * line_height) + self.padding_y * 2
        
        return width, height
    
    def _is_position_on_screen(self, rect: Rectangle) -> bool:
        """
        Check if a position is fully on screen.
        
        Args:
            rect: Rectangle to check
            
        Returns:
            True if position is on screen, False otherwise
        """
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            return (rect.x >= self.screen_margin and 
                    rect.y >= self.screen_margin and 
                    rect.x + rect.width <= screen_width - self.screen_margin and 
                    rect.y + rect.height <= screen_height - self.screen_margin)
        except:
            return True  # Assume valid if we can't check
    
    def _count_collisions(self, rect: Rectangle, existing_positions: List[Rectangle]) -> int:
        """
        Count how many existing overlays this position would collide with.
        
        Args:
            rect: Rectangle to check
            existing_positions: List of existing overlay positions
            
        Returns:
            Number of collisions
        """
        collision_count = 0
        padding = 5  # Minimum spacing between overlays
        
        for existing in existing_positions:
            # Check if rectangles overlap (with padding)
            if not (rect.x + rect.width + padding < existing.x or
                    existing.x + existing.width + padding < rect.x or
                    rect.y + rect.height + padding < existing.y or
                    existing.y + existing.height + padding < rect.y):
                collision_count += 1
        
        return collision_count
    
    def cleanup(self):
        """Clean up overlay resources."""
        try:
            # Destroy all overlays
            for overlay in self.overlays:
                overlay.destroy()
            
            self.overlays.clear()
            self.initialized = False
            print("[OK] Overlay renderer cleaned up")
            
        except Exception as e:
            print(f"[ERROR] Failed to cleanup overlay renderer: {e}")
