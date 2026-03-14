"""
Overlay Settings Tab - PyQt6 Implementation
Overlay styling, positioning, animation, and interaction configuration.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton, QSlider,
    QColorDialog, QFontComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class OverlaySettingsTab(TranslatableMixin, QWidget):
    """Overlay settings including font, colors, transparency, positioning, and animation."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the Overlay settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Font widgets
        self.font_family_combo = None
        self.font_size_spinbox = None
        
        # Color widgets
        self.text_color_btn = None
        self.bg_color_btn = None
        self.border_color_btn = None
        self.text_color = QColor("#FFFFFF")
        self.bg_color = QColor("#000000")
        self.border_color = QColor("#646464")  # Gray default
        
        # Transparency widgets
        self.transparency_slider = None
        self.transparency_spinbox = None
        
        # Positioning widgets
        self.positioning_combo = None
        
        # Animation widgets
        self.animation_enabled_check = None
        self.animation_type_combo = None
        self.fade_duration_spinbox = None
        
        # Display timeout widget
        self.timeout_spinbox = None
        
        # Auto-hide widget
        self.auto_hide_on_disappear_check = None
        
        # Interactive overlay widget
        self.interactive_on_hover_check = None
        
        # Preview widget
        self.preview_label = None
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area (custom - only scrolls when mouse is over it)
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Create sections
        self._create_font_section(content_layout)
        self._create_colors_section(content_layout)
        self._create_transparency_section(content_layout)
        self._create_positioning_section(content_layout)
        self._create_animation_section(content_layout)
        self._create_display_section(content_layout)
        self._create_interaction_section(content_layout)
        self._create_preview_section(content_layout)
        
        # Add stretch at the end
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label
    
    def _create_restart_indicator(self, restart_type: str = "instant") -> QLabel:
        """
        Create a visual restart indicator.
        
        Args:
            restart_type: "instant", "pipeline", or "app"
        """
        if restart_type == "instant":
            text_key = "overlay_takes_effect_immediately"
            color = "#4CAF50"  # Green
            bg_color = "rgba(76, 175, 80, 0.1)"
        elif restart_type == "pipeline":
            text_key = "overlay_requires_pipeline_restart"
            color = "#FF9800"  # Orange
            bg_color = "rgba(255, 152, 0, 0.1)"
        else:  # app
            text_key = "overlay_requires_app_restart"
            color = "#F44336"  # Red
            bg_color = "rgba(244, 67, 54, 0.1)"
        
        label = QLabel()
        self.set_translatable_text(label, text_key)
        label.setWordWrap(True)
        label.setStyleSheet(
            f"color: {color}; "
            f"font-size: 8pt; "
            f"margin-top: 5px; "
            f"padding: 6px 10px; "
            f"background-color: {bg_color}; "
            f"border-radius: 4px; "
            f"border-left: 3px solid {color};"
        )
        return label
    
    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        if self.font_family_combo:
            state['font_family'] = self.font_family_combo.currentText()
        if self.font_size_spinbox:
            state['font_size'] = self.font_size_spinbox.value()
        if hasattr(self, 'auto_font_size_check') and self.auto_font_size_check:
            state['auto_font_size'] = self.auto_font_size_check.isChecked()
        if hasattr(self, 'text_color'):
            state['font_color'] = self.text_color.name()
        if hasattr(self, 'bg_color'):
            state['background_color'] = self.bg_color.name()
        if hasattr(self, 'border_color'):
            state['border_color'] = self.border_color.name()
        if hasattr(self, 'transparency_slider') and self.transparency_slider:
            state['transparency'] = self.transparency_slider.value()
        if hasattr(self, 'positioning_combo') and self.positioning_combo:
            state['positioning_mode'] = self.positioning_combo.currentIndex()
        if hasattr(self, 'collision_padding_spinbox') and self.collision_padding_spinbox:
            state['collision_padding'] = self.collision_padding_spinbox.value()
        if hasattr(self, 'screen_margin_spinbox') and self.screen_margin_spinbox:
            state['screen_margin'] = self.screen_margin_spinbox.value()
        if hasattr(self, 'max_text_width_spinbox') and self.max_text_width_spinbox:
            state['max_text_width'] = self.max_text_width_spinbox.value()
        if hasattr(self, 'animation_enabled_check') and self.animation_enabled_check:
            state['animation_enabled'] = self.animation_enabled_check.isChecked()
        if hasattr(self, 'animation_type_combo') and self.animation_type_combo:
            state['animation_type'] = self.animation_type_combo.currentIndex()
        if hasattr(self, 'fade_duration_spinbox') and self.fade_duration_spinbox:
            state['animation_duration'] = self.fade_duration_spinbox.value()
        if hasattr(self, 'timeout_spinbox') and self.timeout_spinbox:
            state['auto_hide_delay'] = self.timeout_spinbox.value()
        if hasattr(self, 'auto_hide_on_disappear_check') and self.auto_hide_on_disappear_check:
            state['auto_hide_on_disappear'] = self.auto_hide_on_disappear_check.isChecked()
        if hasattr(self, 'disappear_timeout_spinbox') and self.disappear_timeout_spinbox:
            state['disappear_timeout'] = self.disappear_timeout_spinbox.value()
        if hasattr(self, 'interactive_on_hover_check') and self.interactive_on_hover_check:
            state['interactive_on_hover'] = self.interactive_on_hover_check.isChecked()
        if hasattr(self, 'rounded_corners_check') and self.rounded_corners_check:
            state['rounded_corners'] = self.rounded_corners_check.isChecked()
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        self.settingChanged.emit()
        # Update preview when settings change
        self.update_preview()
    
    def _create_font_section(self, parent_layout):
        """Create font configuration section."""
        font_group = QGroupBox()
        self.set_translatable_text(font_group, "overlay_font_section")
        layout = QGridLayout(font_group)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setColumnStretch(2, 1)  # Stretch last column to push everything left
        
        # Font family
        font_family_label = self._create_label("", bold=True)
        self.set_translatable_text(font_family_label, "overlay_font_family_label")
        layout.addWidget(font_family_label, 0, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(QFont("Segoe UI"))
        self.font_family_combo.currentFontChanged.connect(self.on_change)
        layout.addWidget(self.font_family_combo, 0, 1, 1, 2)
        
        # Font size
        font_size_label = self._create_label("", bold=True)
        self.set_translatable_text(font_size_label, "overlay_font_size_label")
        layout.addWidget(font_size_label, 1, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.font_size_spinbox = CustomSpinBox()
        self.font_size_spinbox.setRange(8, 72)
        self.font_size_spinbox.setValue(14)
        self.font_size_spinbox.setSuffix(" pt")
        self.font_size_spinbox.setMinimumWidth(100)
        self.font_size_spinbox.valueChanged.connect(self.on_change)
        layout.addWidget(self.font_size_spinbox, 1, 1)
        
        # Font size description
        font_desc = QLabel()
        self.set_translatable_text(font_desc, "overlay_font_desc")
        font_desc.setWordWrap(True)
        font_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(font_desc, 2, 0, 1, 3)
        
        # Restart indicator
        restart_note = self._create_restart_indicator("instant")
        self.set_translatable_text(restart_note, "overlay_font_restart_note")
        layout.addWidget(restart_note, 3, 0, 1, 3)
        
        parent_layout.addWidget(font_group)
    
    def _create_colors_section(self, parent_layout):
        """Create color configuration section."""
        colors_group = QGroupBox()
        self.set_translatable_text(colors_group, "overlay_colors_section")
        layout = QGridLayout(colors_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Text color
        text_color_label = self._create_label("", bold=True)
        self.set_translatable_text(text_color_label, "overlay_text_color_label")
        layout.addWidget(text_color_label, 0, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.text_color_btn = QPushButton()
        self.text_color_btn.setProperty("class", "action")
        self.text_color_btn.setMinimumWidth(120)
        self.text_color_btn.setMinimumHeight(32)
        self.text_color_btn.clicked.connect(self._select_text_color)
        self._update_color_button(self.text_color_btn, self.text_color)
        layout.addWidget(self.text_color_btn, 0, 1)
        
        text_color_desc = QLabel()
        self.set_translatable_text(text_color_desc, "overlay_text_color_desc")
        text_color_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(text_color_desc, 0, 2)
        
        # Background color
        bg_color_label = self._create_label("", bold=True)
        self.set_translatable_text(bg_color_label, "overlay_bg_color_label")
        layout.addWidget(bg_color_label, 1, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setProperty("class", "action")
        self.bg_color_btn.setMinimumWidth(120)
        self.bg_color_btn.setMinimumHeight(32)
        self.bg_color_btn.clicked.connect(self._select_bg_color)
        self._update_color_button(self.bg_color_btn, self.bg_color)
        layout.addWidget(self.bg_color_btn, 1, 1)
        
        bg_color_desc = QLabel()
        self.set_translatable_text(bg_color_desc, "overlay_bg_color_desc")
        bg_color_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(bg_color_desc, 1, 2)
        
        # Border color (NEW - was hardcoded before!)
        border_color_label = self._create_label("", bold=True)
        self.set_translatable_text(border_color_label, "overlay_border_color_label")
        layout.addWidget(border_color_label, 2, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.border_color_btn = QPushButton()
        self.border_color_btn.setProperty("class", "action")
        self.border_color_btn.setMinimumWidth(120)
        self.border_color_btn.setMinimumHeight(32)
        self.border_color_btn.clicked.connect(self._select_border_color)
        self._update_color_button(self.border_color_btn, self.border_color)
        layout.addWidget(self.border_color_btn, 2, 1)
        
        border_color_desc = QLabel()
        self.set_translatable_text(border_color_desc, "overlay_border_color_desc")
        border_color_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(border_color_desc, 2, 2)
        
        # Color contrast note — feature moved to Color Contrast Optimizer plugin
        color_contrast_note = QLabel()
        self.set_translatable_text(color_contrast_note, "overlay_color_contrast_note")
        color_contrast_note.setWordWrap(True)
        color_contrast_note.setStyleSheet("color: #888; font-size: 8pt; margin-left: 5px; margin-top: 5px;")
        layout.addWidget(color_contrast_note, 3, 0, 1, 3)
        
        # Color tips
        color_tip = QLabel()
        self.set_translatable_text(color_tip, "overlay_color_tip")
        color_tip.setWordWrap(True)
        color_tip.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(color_tip, 5, 0, 1, 3)
        
        parent_layout.addWidget(colors_group)
    
    def _create_transparency_section(self, parent_layout):
        """Create transparency configuration section."""
        transparency_group = QGroupBox()
        self.set_translatable_text(transparency_group, "overlay_transparency_section")
        layout = QGridLayout(transparency_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Transparency label
        transparency_label = self._create_label("", bold=True)
        self.set_translatable_text(transparency_label, "overlay_bg_opacity_label")
        layout.addWidget(transparency_label, 0, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Transparency slider
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100)
        self.transparency_slider.setValue(80)
        self.transparency_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.transparency_slider.setTickInterval(10)
        self.transparency_slider.valueChanged.connect(self._on_transparency_changed)
        layout.addWidget(self.transparency_slider, 0, 1)
        
        # Transparency value spinbox (compact: editable + synced with slider)
        self.transparency_spinbox = CustomSpinBox()
        self.transparency_spinbox.setRange(0, 100)
        self.transparency_spinbox.setValue(80)
        self.transparency_spinbox.setSuffix("%")
        self.transparency_spinbox.setMinimumWidth(80)
        self.transparency_spinbox.setMaximumWidth(100)
        self.transparency_spinbox.valueChanged.connect(self._on_transparency_spinbox_changed)
        layout.addWidget(self.transparency_spinbox, 0, 2)
        
        # Transparency description
        transparency_desc = QLabel()
        self.set_translatable_text(transparency_desc, "overlay_transparency_desc")
        transparency_desc.setWordWrap(True)
        transparency_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(transparency_desc, 1, 0, 1, 3)
        
        # Rounded corners option
        self.rounded_corners_check = QCheckBox()
        self.set_translatable_text(self.rounded_corners_check, "overlay_rounded_corners_check")
        self.rounded_corners_check.setChecked(True)
        self.rounded_corners_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.rounded_corners_check, 2, 0, 1, 3)
        
        rounded_desc = QLabel()
        self.set_translatable_text(rounded_desc, "overlay_rounded_desc")
        rounded_desc.setWordWrap(True)
        rounded_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(rounded_desc, 3, 0, 1, 3)
        
        parent_layout.addWidget(transparency_group)
    
    def _create_positioning_section(self, parent_layout):
        """Create positioning strategy section."""
        positioning_group = QGroupBox()
        self.set_translatable_text(positioning_group, "overlay_positioning_section")
        layout = QVBoxLayout(positioning_group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Positioning label
        positioning_label = self._create_label("", bold=True)
        self.set_translatable_text(positioning_label, "overlay_position_label")
        layout.addWidget(positioning_label)
        
        # Positioning combo box
        self.positioning_combo = QComboBox()
        # Items will be populated after translation system is ready
        self.positioning_combo.setCurrentIndex(0)
        self.positioning_combo.currentTextChanged.connect(self.on_change)
        layout.addWidget(self.positioning_combo)
        
        # Create description label that updates based on selection
        self.positioning_desc_label = QLabel()
        self.positioning_desc_label.setWordWrap(True)
        self.positioning_desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(self.positioning_desc_label)
        
        # Populate combo box with translated items
        self._populate_positioning_combo()
        
        # Add separator
        separator = QLabel("─" * 80)
        separator.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(separator)
        
        # Fine-tuning settings
        fine_tune_label = self._create_label("", bold=True)
        self.set_translatable_text(fine_tune_label, "overlay_fine_tuning_label")
        fine_tune_label.setStyleSheet("font-size: 10pt; font-weight: 600; margin-top: 5px;")
        layout.addWidget(fine_tune_label)
        
        # Create grid layout for fine-tuning spinboxes (matching ROI Detection Settings style)
        fine_tune_grid = QGridLayout()
        fine_tune_grid.setHorizontalSpacing(8)
        fine_tune_grid.setVerticalSpacing(8)
        fine_tune_grid.setContentsMargins(0, 5, 0, 5)
        fine_tune_grid.setColumnStretch(2, 1)  # Stretch last column to push everything left
        
        # Collision padding
        self.collision_padding_spinbox = CustomSpinBox()
        self.collision_padding_spinbox.setRange(0, 50)
        self.collision_padding_spinbox.setValue(5)
        self.collision_padding_spinbox.setSuffix(" px")
        self.collision_padding_spinbox.setMinimumWidth(120)
        self.collision_padding_spinbox.valueChanged.connect(self.on_change)
        
        # Screen margin
        self.screen_margin_spinbox = CustomSpinBox()
        self.screen_margin_spinbox.setRange(0, 100)
        self.screen_margin_spinbox.setValue(10)
        self.screen_margin_spinbox.setSuffix(" px")
        self.screen_margin_spinbox.setMinimumWidth(120)
        self.screen_margin_spinbox.valueChanged.connect(self.on_change)
        
        # Max text width
        self.max_text_width_spinbox = CustomSpinBox()
        self.max_text_width_spinbox.setRange(20, 200)
        self.max_text_width_spinbox.setValue(60)
        self.max_text_width_spinbox.setSuffix(" chars")
        self.max_text_width_spinbox.setMinimumWidth(120)
        self.max_text_width_spinbox.valueChanged.connect(self.on_change)
        
        # Add to grid: Columns: 0=Label, 1=Spinbox
        collision_padding_label = QLabel()
        self.set_translatable_text(collision_padding_label, "overlay_collision_padding_label")
        fine_tune_grid.addWidget(collision_padding_label, 0, 0)
        fine_tune_grid.addWidget(self.collision_padding_spinbox, 0, 1)
        
        screen_margin_label = QLabel()
        self.set_translatable_text(screen_margin_label, "overlay_screen_margin_label")
        fine_tune_grid.addWidget(screen_margin_label, 1, 0)
        fine_tune_grid.addWidget(self.screen_margin_spinbox, 1, 1)
        
        max_text_width_label = QLabel()
        self.set_translatable_text(max_text_width_label, "overlay_max_text_width_label")
        fine_tune_grid.addWidget(max_text_width_label, 2, 0)
        fine_tune_grid.addWidget(self.max_text_width_spinbox, 2, 1)
        
        layout.addLayout(fine_tune_grid)
        
        # Description text
        desc_label = QLabel()
        self.set_translatable_text(desc_label, "overlay_fine_tuning_desc")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 10px; margin-top: 5px;")
        layout.addWidget(desc_label)
        
        # Add separator before auto font size
        separator2 = QLabel("─" * 80)
        separator2.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(separator2)
        
        # Auto font sizing checkbox
        self.auto_font_size_check = QCheckBox()
        self.set_translatable_text(self.auto_font_size_check, "overlay_auto_font_size_check")
        self.auto_font_size_check.setChecked(True)
        self.set_translatable_text(self.auto_font_size_check, "overlay_auto_font_size_tooltip", method="setToolTip")
        self.auto_font_size_check.stateChanged.connect(self._on_auto_font_size_changed)
        layout.addWidget(self.auto_font_size_check)
        
        # Auto font size description
        auto_font_desc = QLabel()
        self.set_translatable_text(auto_font_desc, "overlay_auto_font_size_desc")
        auto_font_desc.setWordWrap(True)
        auto_font_desc.setStyleSheet("color: #888888; font-size: 8pt; margin-left: 20px; margin-top: 3px;")
        layout.addWidget(auto_font_desc)
        
        parent_layout.addWidget(positioning_group)
    
    def _populate_positioning_combo(self):
        """Populate positioning combo box with translated items."""
        from app.localization import tr
        
        # Get translated items with fallback
        items = []
        keys = ["overlay_position_simple", "overlay_position_intelligent"]
        fallbacks = ["Simple (OCR Coordinates)", "Smart (Recommended)"]
        
        for key, fallback in zip(keys, fallbacks):
            translated = tr(key)
            # If translation returns the key itself, use fallback
            if translated == key:
                items.append(fallback)
            else:
                items.append(translated)
        
        self.positioning_combo.clear()
        self.positioning_combo.addItems(items)
        
        # Set initial description
        self._update_positioning_description(0)
        
        # Connect to update description (disconnect first to avoid duplicates)
        try:
            self.positioning_combo.currentIndexChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.positioning_combo.currentIndexChanged.connect(self._update_positioning_description)
    
    def _update_positioning_description(self, index):
        """Update positioning description based on selection."""
        from app.localization import tr
        
        desc_keys = [
            "overlay_positioning_desc_simple",
            "overlay_positioning_desc_intelligent",
        ]
        
        fallback_descs = [
            "Uses OCR coordinates exactly. Overlays appear precisely where text was detected.",
            "Smart positioning with collision avoidance. Recommended for most use cases.",
        ]
        
        if 0 <= index < len(desc_keys):
            desc = tr(desc_keys[index])
            # If translation returns the key itself, use fallback
            if desc == desc_keys[index]:
                desc = fallback_descs[index]
            self.positioning_desc_label.setText(desc)
    
    def _create_animation_section(self, parent_layout):
        """Create animation settings section."""
        animation_group = QGroupBox()
        self.set_translatable_text(animation_group, "overlay_animation_section")
        layout = QVBoxLayout(animation_group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Enable animation checkbox
        self.animation_enabled_check = QCheckBox()
        self.set_translatable_text(self.animation_enabled_check, "overlay_animation_enabled_check")
        self.animation_enabled_check.setChecked(True)
        self.animation_enabled_check.stateChanged.connect(self._on_animation_enabled_changed)
        layout.addWidget(self.animation_enabled_check)
        
        # Animation type
        animation_type_layout = QHBoxLayout()
        animation_type_layout.setSpacing(10)
        
        animation_type_label = self._create_label("", bold=True)
        self.set_translatable_text(animation_type_label, "overlay_animation_type_label")
        animation_type_layout.addWidget(animation_type_label)
        
        self.animation_type_combo = QComboBox()
        # Items will be populated after translation system is ready
        self.animation_type_combo.currentTextChanged.connect(self.on_change)
        animation_type_layout.addWidget(self.animation_type_combo)
        
        animation_type_layout.addStretch()
        layout.addLayout(animation_type_layout)
        
        # Animation duration - using grid layout
        duration_grid = QGridLayout()
        duration_grid.setHorizontalSpacing(8)
        duration_grid.setVerticalSpacing(8)
        duration_grid.setContentsMargins(0, 5, 0, 5)
        duration_grid.setColumnStretch(2, 1)
        
        duration_label = self._create_label("", bold=True)
        self.set_translatable_text(duration_label, "overlay_animation_duration_label")
        
        self.fade_duration_spinbox = CustomSpinBox()
        self.fade_duration_spinbox.setRange(100, 2000)
        self.fade_duration_spinbox.setValue(300)
        self.fade_duration_spinbox.setSuffix("ms")
        self.fade_duration_spinbox.setSingleStep(50)
        self.fade_duration_spinbox.setMinimumWidth(100)
        self.fade_duration_spinbox.valueChanged.connect(self.on_change)
        
        duration_grid.addWidget(duration_label, 0, 0)
        duration_grid.addWidget(self.fade_duration_spinbox, 0, 1)
        layout.addLayout(duration_grid)
        
        # Populate animation combo
        self._populate_animation_combo()
        
        # Animation description
        animation_desc = QLabel()
        self.set_translatable_text(animation_desc, "overlay_animation_desc")
        animation_desc.setWordWrap(True)
        animation_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(animation_desc)
        
        parent_layout.addWidget(animation_group)
    
    def _populate_animation_combo(self):
        """Populate animation combo box with translated items."""
        from app.localization import tr
        items = [
            tr("overlay_animation_fade"),
            tr("overlay_animation_slide"),
            tr("overlay_animation_scale"),
            tr("overlay_animation_none")
        ]
        self.animation_type_combo.clear()
        self.animation_type_combo.addItems(items)
        self.animation_type_combo.setCurrentIndex(0)  # Default to Fade In
    
    def _create_display_section(self, parent_layout):
        """Create display timeout section."""
        display_group = QGroupBox()
        self.set_translatable_text(display_group, "overlay_display_section")
        layout = QVBoxLayout(display_group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Display timeout - using grid layout
        timeout_grid = QGridLayout()
        timeout_grid.setHorizontalSpacing(8)
        timeout_grid.setVerticalSpacing(8)
        timeout_grid.setContentsMargins(0, 5, 0, 5)
        timeout_grid.setColumnStretch(2, 1)
        
        timeout_label = self._create_label("", bold=True)
        self.set_translatable_text(timeout_label, "overlay_display_timeout_label")
        
        self.timeout_spinbox = CustomSpinBox()
        self.timeout_spinbox.setRange(0, 30000)  # Allow 0 for permanent display
        self.timeout_spinbox.setValue(5000)
        self.timeout_spinbox.setSuffix("ms")
        self.timeout_spinbox.setSingleStep(1000)
        self.timeout_spinbox.setMinimumWidth(120)
        self.timeout_spinbox.setSpecialValueText(tr("overlay_permanent"))  # Show "Permanent" when value is 0
        self.timeout_spinbox.valueChanged.connect(self.on_change)
        
        timeout_grid.addWidget(timeout_label, 0, 0)
        timeout_grid.addWidget(self.timeout_spinbox, 0, 1)
        layout.addLayout(timeout_grid)
        
        # Timeout description
        timeout_desc = QLabel()
        self.set_translatable_text(timeout_desc, "overlay_timeout_desc")
        timeout_desc.setWordWrap(True)
        timeout_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(timeout_desc)
        
        # Separator
        separator = QLabel("─" * 80)
        separator.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(separator)
        
        # Auto-hide when text disappears
        self.auto_hide_on_disappear_check = QCheckBox()
        self.set_translatable_text(self.auto_hide_on_disappear_check, "overlay_auto_hide_check")
        self.auto_hide_on_disappear_check.setChecked(True)  # Enabled by default
        self.auto_hide_on_disappear_check.stateChanged.connect(self.on_change)
        self.auto_hide_on_disappear_check.stateChanged.connect(self._on_auto_hide_changed)
        layout.addWidget(self.auto_hide_on_disappear_check)
        
        # Auto-hide description
        auto_hide_desc = QLabel()
        self.set_translatable_text(auto_hide_desc, "overlay_auto_hide_desc")
        auto_hide_desc.setWordWrap(True)
        auto_hide_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(auto_hide_desc)
        
        # Disappear timeout (how long to wait before hiding overlay when text disappears) - using grid layout
        disappear_grid = QGridLayout()
        disappear_grid.setHorizontalSpacing(8)
        disappear_grid.setVerticalSpacing(8)
        disappear_grid.setContentsMargins(0, 5, 0, 5)
        disappear_grid.setColumnStretch(2, 1)
        
        timeout_label = QLabel()
        self.set_translatable_text(timeout_label, "overlay_disappear_delay_label")
        self.set_translatable_text(timeout_label, "overlay_disappear_delay_tooltip", method="setToolTip")
        
        self.disappear_timeout_spinbox = CustomDoubleSpinBox()
        self.disappear_timeout_spinbox.setRange(0.1, 5.0)
        self.disappear_timeout_spinbox.setSingleStep(0.1)
        self.disappear_timeout_spinbox.setValue(2.0)  # Default 2 seconds
        self.disappear_timeout_spinbox.setSuffix(" sec")
        self.set_translatable_text(self.disappear_timeout_spinbox, "overlay_disappear_spinbox_tooltip", method="setToolTip")
        self.disappear_timeout_spinbox.valueChanged.connect(self.on_change)
        
        disappear_grid.addWidget(timeout_label, 0, 0)
        disappear_grid.addWidget(self.disappear_timeout_spinbox, 0, 1)
        layout.addLayout(disappear_grid)
        
        # Timeout hint
        timeout_hint = QLabel()
        self.set_translatable_text(timeout_hint, "overlay_disappear_hint")
        timeout_hint.setStyleSheet("color: #0066CC; font-size: 8pt; font-style: italic; margin-top: 5px;")
        timeout_hint.setWordWrap(True)
        layout.addWidget(timeout_hint)
        
        parent_layout.addWidget(display_group)
    
    def _create_interaction_section(self, parent_layout):
        """Create overlay interaction section."""
        interaction_group = QGroupBox()
        self.set_translatable_text(interaction_group, "overlay_interaction_section")
        layout = QVBoxLayout(interaction_group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Interactive on hover checkbox
        self.interactive_on_hover_check = QCheckBox()
        self.set_translatable_text(self.interactive_on_hover_check, "overlay_interactive_check")
        self.interactive_on_hover_check.setChecked(False)  # Disabled by default
        self.interactive_on_hover_check.stateChanged.connect(self.on_change)
        self.interactive_on_hover_check.stateChanged.connect(self._on_interactive_changed)
        layout.addWidget(self.interactive_on_hover_check)
        
        # Interactive description
        interactive_desc = QLabel()
        self.set_translatable_text(interactive_desc, "overlay_interactive_desc")
        interactive_desc.setWordWrap(True)
        interactive_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(interactive_desc)
        
        parent_layout.addWidget(interaction_group)
    
    def _create_preview_section(self, parent_layout):
        """Create live preview section."""
        preview_group = QGroupBox()
        self.set_translatable_text(preview_group, "overlay_preview_section")
        layout = QVBoxLayout(preview_group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Preview frame
        preview_frame = QFrame()
        preview_frame.setProperty("class", "card")
        preview_frame.setMinimumHeight(100)
        preview_frame.setStyleSheet("QFrame { background-color: #2C2C2C; border-radius: 4px; }")
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        
        # Preview label
        self.preview_label = QLabel()
        self.set_translatable_text(self.preview_label, "overlay_preview_text")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_frame)
        
        # Preview description
        preview_desc = QLabel()
        self.set_translatable_text(preview_desc, "overlay_preview_desc")
        preview_desc.setWordWrap(True)
        preview_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(preview_desc)
        
        parent_layout.addWidget(preview_group)
        
        # Initial preview update
        self.update_preview()
    
    def _update_color_button(self, button: QPushButton, color: QColor):
        """Update color button appearance to show the selected color."""
        # Create color swatch with border
        button.setText(f"  {color.name().upper()}  ")
        button.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {color.name()}; "
            f"color: {'#FFFFFF' if color.lightness() < 128 else '#000000'}; "
            f"border: 2px solid #D0D0D0; "
            f"border-radius: 3px; "
            f"padding: 6px 12px; "
            f"font-weight: 500; "
            f"}} "
            f"QPushButton:hover {{ "
            f"border: 2px solid #2196F3; "
            f"}}"
        )
    
    def _select_text_color(self):
        """Open color dialog to select text color."""
        color = QColorDialog.getColor(self.text_color, self, tr("overlay_select_text_color"))
        if color.isValid():
            self.text_color = color
            self._update_color_button(self.text_color_btn, self.text_color)
            self.on_change()
    
    def _select_bg_color(self):
        """Open color dialog to select background color."""
        color = QColorDialog.getColor(self.bg_color, self, tr("overlay_select_bg_color"))
        if color.isValid():
            self.bg_color = color
            self._update_color_button(self.bg_color_btn, self.bg_color)
            self.on_change()
    
    def _select_border_color(self):
        """Open color dialog to select border color."""
        color = QColorDialog.getColor(self.border_color, self, tr("overlay_select_border_color"))
        if color.isValid():
            self.border_color = color
            self._update_color_button(self.border_color_btn, self.border_color)
            self.on_change()
    
    def _on_transparency_changed(self, value):
        """Handle transparency slider value change."""
        if self.transparency_spinbox:
            self.transparency_spinbox.blockSignals(True)
            self.transparency_spinbox.setValue(value)
            self.transparency_spinbox.blockSignals(False)
        self.on_change()
    
    def _on_transparency_spinbox_changed(self, value):
        """Handle transparency spinbox value change — sync slider."""
        if self.transparency_slider:
            self.transparency_slider.blockSignals(True)
            self.transparency_slider.setValue(value)
            self.transparency_slider.blockSignals(False)
        self.on_change()
    
    def _on_animation_enabled_changed(self, state):
        """Handle animation enabled checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        self.animation_type_combo.setEnabled(enabled)
        self.fade_duration_spinbox.setEnabled(enabled)
        self.on_change()
    
    def _on_auto_font_size_changed(self, state):
        """Handle auto font size checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        
        # When auto-sizing is enabled, the manual font size becomes a fallback/minimum
        # No need to disable the spinbox - it's still useful as a fallback
        
        self.on_change()
    
    def _on_auto_hide_changed(self, state):
        """Handle auto-hide checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        
        # Enable/disable the timeout spinbox
        if hasattr(self, 'disappear_timeout_spinbox'):
            self.disappear_timeout_spinbox.setEnabled(enabled)
        
        self.on_change()
    
    def _on_interactive_changed(self, state):
        """Handle interactive on hover checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        
        try:
            main_window = self.window()
            pipeline = getattr(main_window, 'pipeline', None)
            if pipeline and hasattr(pipeline, 'overlay_system') and pipeline.overlay_system:
                if hasattr(pipeline.overlay_system, 'set_interactive_mode'):
                    pipeline.overlay_system.set_interactive_mode(enabled)
                    logger.debug("Interactive mode %s", 'enabled' if enabled else 'disabled')
        except Exception as e:
            logger.warning("Failed to apply interactive mode: %s", e)
        
        self.on_change()
    
    def update_preview(self):
        """Update the live preview with current settings."""
        if not self.preview_label:
            return
        
        try:
            # Get current settings
            font_family = self.font_family_combo.currentFont().family()
            font_size = self.font_size_spinbox.value()
            text_color = self.text_color.name()
            bg_color = self.bg_color.name()
            border_color = self.border_color.name()
            opacity = self.transparency_slider.value() / 100.0
            rounded = self.rounded_corners_check.isChecked()
            
            # Calculate background color with opacity
            bg_rgba = f"rgba({self.bg_color.red()}, {self.bg_color.green()}, {self.bg_color.blue()}, {opacity})"
            
            # Border radius
            border_radius = "8px" if rounded else "0px"
            
            # Apply styling to preview label
            self.preview_label.setStyleSheet(
                f"QLabel {{ "
                f"font-family: '{font_family}'; "
                f"font-size: {font_size}pt; "
                f"color: {text_color}; "
                f"background-color: {bg_rgba}; "
                f"border: 2px solid {border_color}; "
                f"border-radius: {border_radius}; "
                f"padding: 10px 20px; "
                f"}}"
            )
            
        except Exception as e:
            logger.warning("Failed to update preview: %s", e)
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Block signals during loading
            self.blockSignals(True)
            
            # Load font settings
            font_family = self.config_manager.get_setting('overlay.font_family', 'Segoe UI')
            font_size = self.config_manager.get_setting('overlay.font_size', 14)
            auto_font_size = self.config_manager.get_setting('overlay.auto_font_size', True)
            
            self.font_family_combo.setCurrentFont(QFont(font_family))
            self.font_size_spinbox.setValue(font_size)
            self.auto_font_size_check.setChecked(auto_font_size)
            
            # Load color settings
            text_color = self.config_manager.get_setting('overlay.font_color', '#FFFFFF')
            bg_color = self.config_manager.get_setting('overlay.background_color', '#000000')
            border_color = self.config_manager.get_setting('overlay.border_color', '#646464')  # NEW!
            
            # Handle color values that might be lists (RGB) or strings (hex)
            if isinstance(text_color, list):
                self.text_color = QColor(*text_color) if len(text_color) >= 3 else QColor('#FFFFFF')
            else:
                self.text_color = QColor(text_color)
            
            if isinstance(bg_color, list):
                self.bg_color = QColor(*bg_color) if len(bg_color) >= 3 else QColor('#000000')
            else:
                self.bg_color = QColor(bg_color)
            
            if isinstance(border_color, list):
                self.border_color = QColor(*border_color) if len(border_color) >= 3 else QColor('#646464')
            else:
                self.border_color = QColor(border_color)
            
            self._update_color_button(self.text_color_btn, self.text_color)
            self._update_color_button(self.bg_color_btn, self.bg_color)
            self._update_color_button(self.border_color_btn, self.border_color)  # NEW!
            
            # Load opacity (canonical key; fallback to legacy overlay.transparency for old configs)
            opacity = self.config_manager.get_setting('overlay.opacity', None)
            if opacity is None:
                opacity = self.config_manager.get_setting('overlay.transparency', 0.8)
            transparency_percent = int(opacity * 100)
            self.transparency_slider.setValue(transparency_percent)
            if self.transparency_spinbox:
                self.transparency_spinbox.setValue(transparency_percent)
            
            # Repopulate positioning combo with translations (now that translations are loaded)
            self._populate_positioning_combo()
            
            # Load positioning mode
            positioning = self.config_manager.get_setting('overlay.positioning_mode', 'intelligent')
            positioning_map = {
                'simple': 0,
                'intelligent': 1,
            }
            index = positioning_map.get(positioning, 1)  # Default to intelligent (Smart)
            self.positioning_combo.setCurrentIndex(index)
            
            # Load fine-tuning settings
            collision_padding = self.config_manager.get_setting('overlay.collision_padding', 5)
            self.collision_padding_spinbox.setValue(collision_padding)
            
            screen_margin = self.config_manager.get_setting('overlay.screen_margin', 10)
            self.screen_margin_spinbox.setValue(screen_margin)
            
            max_text_width = self.config_manager.get_setting('overlay.max_text_width', 60)
            self.max_text_width_spinbox.setValue(max_text_width)
            
            # Load animation settings
            animation_enabled = self.config_manager.get_setting('overlay.animation_enabled', True)
            self.animation_enabled_check.setChecked(animation_enabled)
            
            # Use index-based mapping (locale-safe) and read runtime-compatible keys
            animation_in = self.config_manager.get_setting('overlay.animation_in', 'FADE').lower()
            animation_index_map = {
                'fade': 0,
                'slide': 1,
                'scale': 2,
                'none': 3,
            }
            anim_index = animation_index_map.get(animation_in, 0)
            if 0 <= anim_index < self.animation_type_combo.count():
                self.animation_type_combo.setCurrentIndex(anim_index)
            
            animation_duration = self.config_manager.get_setting('overlay.animation_duration', 300)
            self.fade_duration_spinbox.setValue(animation_duration)
            
            # Load display timeout (adapter reads overlay.auto_hide_delay)
            timeout = self.config_manager.get_setting('overlay.auto_hide_delay', 5000)
            self.timeout_spinbox.setValue(timeout)
            
            # Load auto-hide on disappear setting
            auto_hide_on_disappear = self.config_manager.get_setting('overlay.auto_hide_on_disappear', True)
            self.auto_hide_on_disappear_check.setChecked(auto_hide_on_disappear)
            
            # Load disappear timeout setting (schema key: disappear_timeout_seconds)
            disappear_timeout = self.config_manager.get_setting('overlay.disappear_timeout_seconds', 2.0)
            self.disappear_timeout_spinbox.setValue(disappear_timeout)
            self.disappear_timeout_spinbox.setEnabled(auto_hide_on_disappear)
            
            # Load interactive on hover setting
            interactive_on_hover = self.config_manager.get_setting('overlay.interactive_on_hover', False)
            self.interactive_on_hover_check.setChecked(interactive_on_hover)
            
            # Load rounded corners setting
            rounded_corners = self.config_manager.get_setting('overlay.rounded_corners', True)
            self.rounded_corners_check.setChecked(rounded_corners)
            
            # Update animation controls enabled state
            self.animation_type_combo.setEnabled(animation_enabled)
            self.fade_duration_spinbox.setEnabled(animation_enabled)
            
            # Unblock signals
            self.blockSignals(False)
            
            # Update preview
            self.update_preview()
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            logger.debug("Overlay tab configuration loaded")
            
        except Exception as e:
            self.blockSignals(False)
            logger.warning("Failed to load overlay tab config: %s", e, exc_info=True)
    
    def save_config(self):
        """
        Save configuration to config manager.
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"
        
        try:
            # Save font settings
            self.config_manager.set_setting('overlay.font_family', self.font_family_combo.currentFont().family())
            self.config_manager.set_setting('overlay.font_size', self.font_size_spinbox.value())
            self.config_manager.set_setting('overlay.auto_font_size', self.auto_font_size_check.isChecked())
            
            # Save color settings
            self.config_manager.set_setting('overlay.font_color', self.text_color.name())
            self.config_manager.set_setting('overlay.background_color', self.bg_color.name())
            self.config_manager.set_setting('overlay.border_color', self.border_color.name())  # NEW!
            
            # Save opacity (single canonical key; adapter reads overlay.opacity)
            opacity = self.transparency_slider.value() / 100.0
            self.config_manager.set_setting('overlay.opacity', opacity)
            
            # Save positioning mode
            positioning_index = self.positioning_combo.currentIndex()
            positioning_modes = ['simple', 'intelligent']
            positioning_mode = positioning_modes[positioning_index] if 0 <= positioning_index < len(positioning_modes) else 'intelligent'
            self.config_manager.set_setting('overlay.positioning_mode', positioning_mode)
            
            # Save fine-tuning settings
            self.config_manager.set_setting('overlay.collision_padding', self.collision_padding_spinbox.value())
            self.config_manager.set_setting('overlay.screen_margin', self.screen_margin_spinbox.value())
            self.config_manager.set_setting('overlay.max_text_width', self.max_text_width_spinbox.value())
            
            # Save animation settings
            animation_enabled = self.animation_enabled_check.isChecked()
            self.config_manager.set_setting('overlay.animation_enabled', animation_enabled)
            
            # Use index-based mapping (locale-safe) and write runtime-compatible keys
            animation_type_index = self.animation_type_combo.currentIndex()
            animation_values = ['FADE', 'SLIDE_DOWN', 'SCALE', 'NONE']
            if animation_enabled:
                animation_value = animation_values[animation_type_index] if 0 <= animation_type_index < len(animation_values) else 'FADE'
            else:
                animation_value = 'NONE'
            # Write keys that overlay_integration.py actually reads
            self.config_manager.set_setting('overlay.animation_in', animation_value)
            self.config_manager.set_setting('overlay.animation_out', animation_value)
            
            self.config_manager.set_setting('overlay.animation_duration', self.fade_duration_spinbox.value())
            
            # Save display timeout (adapter reads overlay.auto_hide_delay)
            self.config_manager.set_setting('overlay.auto_hide_delay', self.timeout_spinbox.value())
            
            # Save auto-hide on disappear setting
            self.config_manager.set_setting('overlay.auto_hide_on_disappear', self.auto_hide_on_disappear_check.isChecked())
            
            # Save disappear timeout setting (schema key: disappear_timeout_seconds)
            self.config_manager.set_setting('overlay.disappear_timeout_seconds', self.disappear_timeout_spinbox.value())
            
            # Save interactive on hover setting
            self.config_manager.set_setting('overlay.interactive_on_hover', self.interactive_on_hover_check.isChecked())
            
            # Save rounded corners setting
            self.config_manager.set_setting('overlay.rounded_corners', self.rounded_corners_check.isChecked())
            
            # Save the configuration file
            success, error_msg = self.config_manager.save_config()
            
            if not success:
                return False, error_msg
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            logger.info("Overlay tab configuration saved")
            return True, ""
            
        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def validate(self) -> bool:
        """
        Validate settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        # All settings are from dropdowns/sliders/spinboxes with valid ranges
        # No specific validation needed
        return True
