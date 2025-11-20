"""
Intelligent Positioning Engine - Stub Implementation

This module provides stub classes for the automatic positioning system.
The actual positioning logic is implemented in automatic_positioning.py.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import time


class PositioningMode(Enum):
    """Positioning modes for intelligent engine."""
    INTELLIGENT = "intelligent"
    SIMPLE = "simple"
    FLOW_BASED = "flow_based"


class TextFlow(Enum):
    """Text flow directions."""
    LEFT_TO_RIGHT = "ltr"
    RIGHT_TO_LEFT = "rtl"
    TOP_TO_BOTTOM = "ttb"
    BOTTOM_TO_TOP = "btt"


@dataclass
class PositioningContext:
    """Context for positioning decisions."""
    screen_width: int = 1920
    screen_height: int = 1080
    text_flow: TextFlow = TextFlow.LEFT_TO_RIGHT
    content_type: str = "general"
    ui_elements: List = field(default_factory=list)
    exclusion_zones: List = field(default_factory=list)


@dataclass
class MovementTracker:
    """Tracks movement of text elements."""
    velocity: Tuple[float, float] = (0.0, 0.0)
    is_moving: bool = False
    movement_threshold: float = 5.0
    last_update: float = field(default_factory=time.time)


class IntelligentPositioningEngine:
    """
    Intelligent positioning engine that applies smart positioning strategies.
    
    This can work standalone or delegate to AutomaticPositioningSystem for advanced features.
    """
    
    def __init__(self, context: Optional[PositioningContext] = None):
        self.context = context or PositioningContext()
        self._automatic_system = None  # Lazy-loaded if needed
    
    def calculate_optimal_positions(self, translations, frame=None, mode=PositioningMode.INTELLIGENT):
        """
        Calculate optimal positions for translations.
        
        Args:
            translations: List of translations to position
            frame: Optional frame for context
            mode: Positioning mode to use
            
        Returns:
            List of translations with optimized positions
        """
        if mode == PositioningMode.SIMPLE:
            # Simple mode: return translations with their OCR coordinates unchanged
            return translations
        
        elif mode == PositioningMode.INTELLIGENT:
            # Intelligent mode: apply smart positioning with collision avoidance
            return self._apply_intelligent_positioning(translations, frame)
        
        elif mode == PositioningMode.FLOW_BASED:
            # Flow-based mode: position based on text flow direction
            return self._apply_flow_based_positioning(translations, frame)
        
        else:
            # Default: return unchanged
            return translations
    
    def _apply_intelligent_positioning(self, translations, frame):
        """
        Apply intelligent positioning with collision avoidance.
        
        This is a lightweight implementation. For advanced features,
        use AutomaticPositioningSystem directly.
        """
        positioned = []
        existing_rects = []
        
        for translation in translations:
            # Start with OCR position
            original_rect = translation.position
            
            # Try to find non-colliding position
            best_rect = self._find_best_position(
                original_rect, 
                existing_rects,
                translation
            )
            
            # Create new translation with adjusted position
            from app.models import Translation
            positioned_translation = Translation(
                original_text=translation.original_text,
                translated_text=translation.translated_text,
                source_language=translation.source_language,
                target_language=translation.target_language,
                position=best_rect,
                confidence=translation.confidence,
                engine_used=translation.engine_used
            )
            
            # Copy metadata if present
            if hasattr(translation, 'metadata'):
                positioned_translation.metadata = translation.metadata
            if hasattr(translation, 'estimated_font_size'):
                positioned_translation.estimated_font_size = translation.estimated_font_size
            
            positioned.append(positioned_translation)
            existing_rects.append(best_rect)
        
        return positioned
    
    def _find_best_position(self, original_rect, existing_rects, translation):
        """
        Find best position avoiding collisions.
        
        Args:
            original_rect: Original OCR rectangle
            existing_rects: List of existing overlay rectangles
            translation: Translation object
            
        Returns:
            Best rectangle position
        """
        from app.models import Rectangle
        
        # If no collisions, use original position
        if not self._has_collision(original_rect, existing_rects):
            return original_rect
        
        # Try positions in order of preference:
        # 1. Above original
        # 2. Below original  
        # 3. Left of original
        # 4. Right of original
        # 5. Offset diagonally
        
        candidates = [
            # Above
            Rectangle(
                original_rect.x,
                original_rect.y - original_rect.height - 10,
                original_rect.width,
                original_rect.height
            ),
            # Below
            Rectangle(
                original_rect.x,
                original_rect.y + original_rect.height + 10,
                original_rect.width,
                original_rect.height
            ),
            # Left
            Rectangle(
                original_rect.x - original_rect.width - 10,
                original_rect.y,
                original_rect.width,
                original_rect.height
            ),
            # Right
            Rectangle(
                original_rect.x + original_rect.width + 10,
                original_rect.y,
                original_rect.width,
                original_rect.height
            ),
            # Diagonal offsets
            Rectangle(
                original_rect.x + 20,
                original_rect.y - original_rect.height - 10,
                original_rect.width,
                original_rect.height
            ),
            Rectangle(
                original_rect.x - 20,
                original_rect.y + original_rect.height + 10,
                original_rect.width,
                original_rect.height
            ),
        ]
        
        # Find first non-colliding position
        for candidate in candidates:
            if self._is_on_screen(candidate) and not self._has_collision(candidate, existing_rects):
                return candidate
        
        # If all positions collide, use original (better than nothing)
        return original_rect
    
    def _has_collision(self, rect, existing_rects, padding=5):
        """Check if rectangle collides with any existing rectangles."""
        for existing in existing_rects:
            if not (rect.x + rect.width + padding < existing.x or
                    existing.x + existing.width + padding < rect.x or
                    rect.y + rect.height + padding < existing.y or
                    existing.y + existing.height + padding < rect.y):
                return True
        return False
    
    def _is_on_screen(self, rect):
        """Check if rectangle is within screen bounds."""
        return (rect.x >= 0 and 
                rect.y >= 0 and 
                rect.x + rect.width <= self.context.screen_width and 
                rect.y + rect.height <= self.context.screen_height)
    
    def _apply_flow_based_positioning(self, translations, frame):
        """Apply flow-based positioning (follows text reading direction)."""
        # For now, just use intelligent positioning
        # Can be enhanced later to follow text flow patterns
        return self._apply_intelligent_positioning(translations, frame)
    
    def update_context(self, context: PositioningContext):
        """Update positioning context."""
        self.context = context
