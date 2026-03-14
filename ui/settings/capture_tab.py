"""
Capture Settings Tab - PyQt6 Implementation
Capture method, performance, and multi-monitor configuration.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QRadioButton, QCheckBox, QPushButton, QSpinBox, QSlider,
    QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.common.widgets.custom_spinbox import CustomSpinBox

# Import custom scroll area
from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.localization import TranslatableMixin, tr

# Import hardware capability gate
from app.utils.hardware_capability_gate import get_hardware_gate, GatedFeature


logger = logging.getLogger(__name__)


class CaptureSettingsTab(TranslatableMixin, QWidget):
    """Capture settings including method, performance, and multi-monitor."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the Capture settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Detect available capture methods
        self.available_methods = self._detect_available_capture_methods()
        
        # Capture method widgets
        self.method_directx_radio = None
        self.method_bettercam_radio = None
        self.method_screenshot_radio = None
        self.method_auto_radio = None
        self.method_button_group = None
        
        # Performance widgets
        self.fps_slider = None
        self.fps_spinbox = None
        self.quality_combo = None
        
        # Multi-monitor widgets
        self.monitor_combo = None
        self.detect_monitors_btn = None
        
        # Additional options
        self.fallback_check = None
        self.small_text_enhancement_check = None
        self.denoise_check = None
        self.binarize_check = None
        self.overlay_screenshot_check = None
        
        # Initialize UI
        self._init_ui()
    
    def _detect_available_capture_methods(self):
        """
        Detect which capture methods are available on this system.
        Filters GPU-only methods when running in CPU mode.
        
        Returns:
            dict: Dictionary with method availability and details
        """
        methods = {
            'directx': {'available': False, 'name': 'DirectX Desktop Duplication', 'reason': '', 'performance': ''},
            'bettercam': {'available': False, 'name': 'BetterCam (AMD/NVIDIA)', 'reason': '', 'performance': ''},
            'screenshot': {'available': False, 'name': 'Screenshot API', 'reason': '', 'performance': ''},
            'auto': {'available': True, 'name': 'Auto-detect', 'reason': '', 'performance': ''}  # Always available
        }
        
        # Check if running in CPU mode
        runtime_mode = self.config_manager.get_runtime_mode() if self.config_manager else 'auto'
        
        # Check DirectX availability using hardware capability gate
        directx_gated = False
        try:
            gate = get_hardware_gate(self.config_manager)
            directx_gated = not gate.is_available(GatedFeature.DIRECTX_CAPTURE)
        except Exception:
            # If gate unavailable, fall back to runtime mode check
            directx_gated = (runtime_mode == 'cpu')
        
        # Check DirectX / BetterCam availability (single probe — both use bettercam)
        bettercam_ok = False
        if directx_gated:
            methods['directx']['available'] = False
            methods['directx']['reason'] = 'Requires GPU mode'
            methods['bettercam']['available'] = False
            methods['bettercam']['reason'] = 'Requires GPU mode'
            logger.info("DirectX/BetterCam capture: Disabled by hardware capability gate")
        else:
            try:
                import bettercam
                test_camera = bettercam.create()
                if test_camera is not None:
                    bettercam_ok = True
                    test_camera.release()
                    logger.info("BetterCam probe: Available")
                else:
                    logger.info("BetterCam probe: camera creation failed")
            except ImportError:
                logger.info("BetterCam probe: not installed")
            except Exception as e:
                logger.info("BetterCam probe: Not available (%s)", e)

            if bettercam_ok:
                methods['directx']['available'] = True
                methods['directx']['reason'] = 'bettercam library available (GPU-accelerated)'
                methods['directx']['performance'] = '~4-8ms per frame (~240 FPS) - Best for full-screen'
                methods['bettercam']['available'] = True
                methods['bettercam']['reason'] = 'bettercam library available (GPU-accelerated, AMD/NVIDIA)'
                methods['bettercam']['performance'] = '~4-8ms per frame (~240 FPS) - AMD & NVIDIA compatible'
            else:
                methods['directx']['available'] = False
                methods['directx']['reason'] = 'bettercam library not available'
                methods['bettercam']['available'] = False
                methods['bettercam']['reason'] = 'bettercam library not available'
        
        # Check Screenshot methods availability
        screenshot_methods = []
        
        # Check Win32 GDI (fastest screenshot method)
        try:
            import win32gui
            import win32ui
            import win32con
            screenshot_methods.append('Win32 GDI (fastest)')
        except Exception:
            pass
        
        # Check MSS
        try:
            import mss
            screenshot_methods.append('MSS')
        except Exception:
            pass
        
        # Check PIL ImageGrab
        try:
            from PIL import ImageGrab
            ImageGrab.grab(bbox=(0, 0, 10, 10))
            screenshot_methods.append('PIL ImageGrab')
        except Exception:
            pass
        
        if screenshot_methods:
            methods['screenshot']['available'] = True
            methods['screenshot']['reason'] = f"Available: {', '.join(screenshot_methods)}"
            methods['screenshot']['performance'] = '~11-12ms per frame (~85 FPS) - Best for small regions'
            logger.info("Screenshot capture: Available (%s)", ', '.join(screenshot_methods))
        else:
            methods['screenshot']['available'] = False
            methods['screenshot']['reason'] = 'No screenshot libraries available'
            logger.warning("Screenshot capture: Not available")
        
        return methods
    
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
        self._create_capture_method_section(content_layout)
        self._create_performance_section(content_layout)
        self._create_monitor_section(content_layout)
        self._create_additional_options_section(content_layout)
        
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
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        # Always emit the signal - let the main window decide if there are actual changes
        # The main window will check _get_current_state() vs _original_state
        self.settingChanged.emit()
    
    def _create_capture_method_section(self, parent_layout):
        """Create capture method selection section."""
        group = QGroupBox()
        self.set_translatable_text(group, "capture_method_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # CPU Mode Warning (if applicable)
        runtime_mode = self.config_manager.get_runtime_mode() if self.config_manager else 'auto'
        if runtime_mode == 'cpu':
            cpu_warning = QLabel()
            cpu_warning.setWordWrap(True)
            cpu_warning.setStyleSheet(
                "background-color: #FFF3CD; color: #856404; padding: 10px; "
                "border-radius: 4px; border: 1px solid #FFE69C; font-size: 9pt;"
            )
            self.set_translatable_text(cpu_warning, "capture_cpu_mode_warning")
            layout.addWidget(cpu_warning)
        
        # Method label with Available count
        method_header_layout = QHBoxLayout()
        method_label = self._create_label("", bold=True)
        self.set_translatable_text(method_label, "capture_select_method_label")
        method_header_layout.addWidget(method_label)
        
        # Count available methods
        available_count = sum(1 for m in self.available_methods.values() if m['available'])
        available_label = QLabel(tr("capture_available_count").format(count=available_count))
        available_label.setStyleSheet("color: #4A9EFF; font-size: 9pt; font-weight: normal;")
        method_header_layout.addWidget(available_label)
        method_header_layout.addStretch()
        
        layout.addLayout(method_header_layout)
        
        # Create button group for radio buttons
        self.method_button_group = QButtonGroup()
        button_id = 0
        first_available = None
        
        # DirectX mode (only if available)
        if self.available_methods['directx']['available']:
            self.method_directx_radio = QRadioButton()
            self.set_translatable_text(self.method_directx_radio, "method_directx_label")
            self.method_directx_radio.toggled.connect(self.on_change)
            self.method_button_group.addButton(self.method_directx_radio, button_id)
            layout.addWidget(self.method_directx_radio)
            
            # DirectX description
            directx_desc = QLabel(tr("capture_directx_desc").format(
                performance=self.available_methods['directx']['performance']
            ))
            directx_desc.setWordWrap(True)
            directx_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
            layout.addWidget(directx_desc)
            
            if first_available is None:
                first_available = self.method_directx_radio
            button_id += 1
        else:
            # Show as unavailable
            unavailable_label = QLabel()
            self.set_translatable_text(unavailable_label, "capture_directx_unavailable")
            unavailable_label.setStyleSheet("color: #999999; font-size: 9pt;")
            layout.addWidget(unavailable_label)
            
            reason_label = QLabel(f"   \u26a0\ufe0f {self.available_methods['directx']['reason']}")
            reason_label.setWordWrap(True)
            reason_label.setStyleSheet("color: #999999; font-size: 8pt; margin-left: 25px; margin-bottom: 8px;")
            layout.addWidget(reason_label)
            
            # Add install instructions if bettercam is missing
            if 'not installed' in self.available_methods['directx']['reason']:
                install_label = QLabel()
                self.set_translatable_text(install_label, "capture_directx_install")
                install_label.setWordWrap(True)
                install_label.setStyleSheet("color: #0066cc; font-size: 8pt; margin-left: 25px; margin-bottom: 10px;")
                layout.addWidget(install_label)
        
        # BetterCam mode (AMD/NVIDIA compatible - only if available)
        if self.available_methods['bettercam']['available']:
            self.method_bettercam_radio = QRadioButton()
            self.set_translatable_text(self.method_bettercam_radio, "method_bettercam_label")
            self.method_bettercam_radio.toggled.connect(self.on_change)
            self.method_button_group.addButton(self.method_bettercam_radio, button_id)
            layout.addWidget(self.method_bettercam_radio)

            bettercam_desc = QLabel(tr("capture_bettercam_desc").format(
                performance=self.available_methods['bettercam']['performance']
            ))
            bettercam_desc.setWordWrap(True)
            bettercam_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
            layout.addWidget(bettercam_desc)

            if first_available is None:
                first_available = self.method_bettercam_radio
            button_id += 1
        else:
            unavailable_label = QLabel()
            self.set_translatable_text(unavailable_label, "capture_bettercam_unavailable")
            unavailable_label.setStyleSheet("color: #999999; font-size: 9pt;")
            layout.addWidget(unavailable_label)

            reason_label = QLabel(f"   \u26a0\ufe0f {self.available_methods['bettercam']['reason']}")
            reason_label.setWordWrap(True)
            reason_label.setStyleSheet("color: #999999; font-size: 8pt; margin-left: 25px; margin-bottom: 8px;")
            layout.addWidget(reason_label)

            if 'not installed' in self.available_methods['bettercam']['reason']:
                install_label = QLabel()
                self.set_translatable_text(install_label, "capture_bettercam_install")
                install_label.setWordWrap(True)
                install_label.setStyleSheet("color: #0066cc; font-size: 8pt; margin-left: 25px; margin-bottom: 10px;")
                layout.addWidget(install_label)

        # Screenshot API mode (only if available)
        if self.available_methods['screenshot']['available']:
            self.method_screenshot_radio = QRadioButton()
            self.set_translatable_text(self.method_screenshot_radio, "method_screenshot_label")
            self.method_screenshot_radio.toggled.connect(self.on_change)
            self.method_button_group.addButton(self.method_screenshot_radio, button_id)
            layout.addWidget(self.method_screenshot_radio)
            
            # Screenshot description
            screenshot_desc = QLabel(tr("capture_screenshot_desc").format(
                performance=self.available_methods['screenshot']['performance'],
                technology=self.available_methods['screenshot']['reason']
            ))
            screenshot_desc.setWordWrap(True)
            screenshot_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
            layout.addWidget(screenshot_desc)
            
            if first_available is None:
                first_available = self.method_screenshot_radio
            button_id += 1
        else:
            # Show as unavailable
            unavailable_label = QLabel()
            self.set_translatable_text(unavailable_label, "capture_screenshot_unavailable")
            unavailable_label.setStyleSheet("color: #999999; font-size: 9pt;")
            layout.addWidget(unavailable_label)
            
            reason_label = QLabel(f"   \u26a0\ufe0f {self.available_methods['screenshot']['reason']}")
            reason_label.setWordWrap(True)
            reason_label.setStyleSheet("color: #999999; font-size: 8pt; margin-left: 25px; margin-bottom: 8px;")
            layout.addWidget(reason_label)
        
        # Auto-detect mode (always available)
        self.method_auto_radio = QRadioButton()
        self.set_translatable_text(self.method_auto_radio, "method_auto_label")
        self.method_auto_radio.toggled.connect(self.on_change)
        self.method_button_group.addButton(self.method_auto_radio, button_id)
        layout.addWidget(self.method_auto_radio)
        
        # Auto description - show what's available
        available_list = []
        if self.available_methods['directx']['available']:
            available_list.append(tr("capture_auto_directx_primary"))
        if self.available_methods['bettercam']['available']:
            available_list.append(tr("capture_auto_bettercam_option"))
        if self.available_methods['screenshot']['available']:
            available_list.append(tr("capture_auto_screenshot_fallback"))
        
        auto_desc = QLabel(tr("capture_auto_desc").format(
            methods=', '.join(available_list) if available_list else tr("capture_auto_no_methods")
        ))
        auto_desc.setWordWrap(True)
        auto_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
        layout.addWidget(auto_desc)
        
        # Add a note about the recommendation
        if self.available_methods['directx']['available'] or self.available_methods['bettercam']['available']:
            recommendation = QLabel()
            self.set_translatable_text(recommendation, "capture_recommendation_gpu")
        else:
            recommendation = QLabel()
            self.set_translatable_text(recommendation, "capture_recommendation_no_gpu")
        recommendation.setWordWrap(True)
        recommendation.setStyleSheet("color: #4A9EFF; font-size: 9pt; margin-left: 25px; padding: 8px; background-color: #1E3A4F; border-radius: 4px; border: 1px solid #2A5A7F;")
        layout.addWidget(recommendation)
        
        # Set default selection (prefer Auto, then DirectX, then Screenshot)
        if self.method_auto_radio:
            self.method_auto_radio.setChecked(True)
        elif first_available:
            first_available.setChecked(True)
        
        # Add test button
        test_layout = QHBoxLayout()
        test_layout.setSpacing(10)
        
        test_btn = QPushButton()
        self.set_translatable_text(test_btn, "test_capture_button")
        test_btn.setProperty("class", "action")
        test_btn.clicked.connect(self._test_capture_method)
        test_layout.addWidget(test_btn)
        
        test_info = QLabel()
        self.set_translatable_text(test_info, "capture_test_info")
        test_info.setStyleSheet("color: #666666; font-size: 9pt;")
        test_layout.addWidget(test_info)
        test_layout.addStretch()
        
        layout.addLayout(test_layout)
        
        parent_layout.addWidget(group)
    
    
    def _create_performance_section(self, parent_layout):
        """Create performance settings section."""
        group = QGroupBox()
        self.set_translatable_text(group, "performance_section_title")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setColumnStretch(3, 1)  # Stretch last column to push everything left
        
        # FPS setting with slider and spinbox
        fps_label = self._create_label("", bold=True)
        self.set_translatable_text(fps_label, "capture_fps_label")
        layout.addWidget(fps_label, 0, 0, Qt.AlignmentFlag.AlignLeft)
        
        # FPS slider
        self.fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.fps_slider.setRange(5, 30)
        self.fps_slider.setValue(30)
        self.fps_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.fps_slider.setTickInterval(5)
        self.fps_slider.setPageStep(5)
        self.fps_slider.setSingleStep(1)
        self.fps_slider.setMinimumWidth(200)
        self.fps_slider.valueChanged.connect(self._on_fps_slider_changed)
        layout.addWidget(self.fps_slider, 0, 1)
        
        self.fps_spinbox = CustomSpinBox()
        self.fps_spinbox.setRange(5, 30)
        self.fps_spinbox.setValue(30)
        self.fps_spinbox.setSuffix(" FPS")
        self.fps_spinbox.setMinimumWidth(100)
        self.fps_spinbox.valueChanged.connect(self._on_fps_spinbox_changed)
        layout.addWidget(self.fps_spinbox, 0, 2)
        
        # FPS description
        fps_desc = QLabel()
        self.set_translatable_text(fps_desc, "capture_fps_desc")
        fps_desc.setWordWrap(True)
        fps_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(fps_desc, 1, 0, 1, 3)
        
        # Quality setting
        quality_label = self._create_label("", bold=True)
        self.set_translatable_text(quality_label, "capture_quality_label")
        layout.addWidget(quality_label, 2, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            tr("capture_quality_low"),
            tr("capture_quality_medium"),
            tr("capture_quality_high"),
            tr("capture_quality_ultra")
        ])
        self.quality_combo.setCurrentIndex(2)  # High
        self.quality_combo.currentIndexChanged.connect(self.on_change)
        layout.addWidget(self.quality_combo, 2, 1, 1, 2)
        
        # Quality description
        quality_desc = QLabel()
        self.set_translatable_text(quality_desc, "capture_quality_desc")
        quality_desc.setWordWrap(True)
        quality_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(quality_desc, 3, 0, 1, 3)
        
        parent_layout.addWidget(group)
    
    def _create_monitor_section(self, parent_layout):
        """Create multi-monitor configuration section."""
        group = QGroupBox()
        self.set_translatable_text(group, "monitor_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Monitor selection
        monitor_layout = QHBoxLayout()
        monitor_layout.setSpacing(10)
        
        monitor_label = self._create_label("", bold=True)
        self.set_translatable_text(monitor_label, "capture_target_monitor_label")
        monitor_layout.addWidget(monitor_label)
        
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItem(tr("capture_primary_monitor"), 0)
        self.monitor_combo.addItem(tr("capture_monitor_n").format(n=1), 1)
        self.monitor_combo.addItem(tr("capture_monitor_n").format(n=2), 2)
        self.monitor_combo.addItem(tr("capture_all_monitors"), -1)
        self.monitor_combo.currentIndexChanged.connect(self.on_change)
        self.monitor_combo.setMinimumWidth(200)
        monitor_layout.addWidget(self.monitor_combo)
        
        # Detect monitors button
        self.detect_monitors_btn = QPushButton()
        self.set_translatable_text(self.detect_monitors_btn, "detect_monitors_button")
        self.detect_monitors_btn.setProperty("class", "action")
        self.detect_monitors_btn.clicked.connect(self._detect_monitors)
        monitor_layout.addWidget(self.detect_monitors_btn)
        
        monitor_layout.addStretch()
        layout.addLayout(monitor_layout)
        
        # Monitor info
        monitor_info = QLabel()
        self.set_translatable_text(monitor_info, "capture_monitor_info")
        monitor_info.setWordWrap(True)
        monitor_info.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(monitor_info)
        
        parent_layout.addWidget(group)
    
    def _create_additional_options_section(self, parent_layout):
        """Create additional capture options section."""
        group = QGroupBox()
        self.set_translatable_text(group, "additional_options_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Fallback mode
        self.fallback_check = QCheckBox()
        self.set_translatable_text(self.fallback_check, "fallback_mode_label")
        self.fallback_check.setChecked(True)
        self.fallback_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.fallback_check)
        
        fallback_desc = QLabel()
        self.set_translatable_text(fallback_desc, "capture_fallback_desc")
        fallback_desc.setWordWrap(True)
        fallback_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(fallback_desc)
        
        # Small text enhancement
        self.small_text_enhancement_check = QCheckBox()
        self.set_translatable_text(self.small_text_enhancement_check, "small_text_enhancement_label")
        self.small_text_enhancement_check.setChecked(False)  # Disabled by default
        self.small_text_enhancement_check.stateChanged.connect(self._on_small_text_enhancement_changed)
        layout.addWidget(self.small_text_enhancement_check)
        
        small_text_desc = QLabel()
        self.set_translatable_text(small_text_desc, "capture_small_text_desc")
        small_text_desc.setWordWrap(True)
        small_text_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(small_text_desc)
        
        # Sub-options for small text enhancement (indented)
        sub_options_layout = QVBoxLayout()
        sub_options_layout.setContentsMargins(40, 5, 0, 5)
        sub_options_layout.setSpacing(5)
        
        # Denoise option
        self.denoise_check = QCheckBox()
        self.set_translatable_text(self.denoise_check, "denoise_label")
        self.denoise_check.setChecked(False)
        self.denoise_check.setEnabled(False)  # Disabled until main option is checked
        self.denoise_check.stateChanged.connect(self.on_change)
        sub_options_layout.addWidget(self.denoise_check)
        
        denoise_desc = QLabel()
        self.set_translatable_text(denoise_desc, "capture_denoise_desc")
        denoise_desc.setWordWrap(True)
        denoise_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        sub_options_layout.addWidget(denoise_desc)
        
        # Binarization option
        self.binarize_check = QCheckBox()
        self.set_translatable_text(self.binarize_check, "binarize_label")
        self.binarize_check.setChecked(False)
        self.binarize_check.setEnabled(False)  # Disabled until main option is checked
        self.binarize_check.stateChanged.connect(self.on_change)
        sub_options_layout.addWidget(self.binarize_check)
        
        binarize_desc = QLabel()
        self.set_translatable_text(binarize_desc, "capture_binarize_desc")
        binarize_desc.setWordWrap(True)
        binarize_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        sub_options_layout.addWidget(binarize_desc)
        
        layout.addLayout(sub_options_layout)
        
        # Overlay visible in screenshots
        self.overlay_screenshot_check = QCheckBox()
        self.set_translatable_text(self.overlay_screenshot_check, "overlay_visible_screenshots_label")
        self.overlay_screenshot_check.setChecked(False)
        self.overlay_screenshot_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.overlay_screenshot_check)
        
        overlay_screenshot_desc = QLabel()
        self.set_translatable_text(overlay_screenshot_desc, "overlay_visible_screenshots_desc")
        overlay_screenshot_desc.setWordWrap(True)
        overlay_screenshot_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(overlay_screenshot_desc)
        
        parent_layout.addWidget(group)
    
    def _on_fps_slider_changed(self, value):
        """Handle FPS slider value change."""
        # Update spinbox to match slider (without triggering its signal)
        self.fps_spinbox.blockSignals(True)
        self.fps_spinbox.setValue(value)
        self.fps_spinbox.blockSignals(False)
        
        # Emit change signal
        self.on_change()
    
    def _on_fps_spinbox_changed(self, value):
        """Handle FPS spinbox value change."""
        self.fps_slider.blockSignals(True)
        self.fps_slider.setValue(value)
        self.fps_slider.blockSignals(False)
        
        self.on_change()
    
    def _on_small_text_enhancement_changed(self, state):
        """Handle small text enhancement checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        
        # Enable/disable sub-options based on main checkbox
        if self.denoise_check:
            self.denoise_check.setEnabled(enabled)
            if not enabled:
                self.denoise_check.setChecked(False)
        
        if self.binarize_check:
            self.binarize_check.setEnabled(enabled)
            if not enabled:
                self.binarize_check.setChecked(False)
        
        # Emit change signal
        self.on_change()
    
    
    def _test_capture_method(self):
        """Test the selected capture method."""
        try:
            import time
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import Qt
            
            # Determine which method to test
            if self.method_directx_radio and self.method_directx_radio.isChecked():
                method_name = "DirectX (BetterCam)"
                plugin_name = "bettercam_capture_gpu"
            elif self.method_bettercam_radio and self.method_bettercam_radio.isChecked():
                method_name = "BetterCam (AMD/NVIDIA)"
                plugin_name = "bettercam_capture_gpu"
            elif self.method_screenshot_radio and self.method_screenshot_radio.isChecked():
                method_name = "Screenshot (CPU)"
                plugin_name = "screenshot_capture_cpu"
            else:
                method_name = "Auto-Select"
                plugin_name = "bettercam_capture_gpu"
            
            # Create progress dialog
            progress = QProgressDialog(
                tr("capture_test_progress_msg").format(method=method_name),
                tr("capture_cancel"),
                0, 100, self
            )
            progress.setWindowTitle(tr("capture_test_progress_title"))
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            # Test the capture method
            try:
                progress.setLabelText(tr("capture_test_initializing").format(method=method_name))
                progress.setValue(20)
                
                from app.capture.plugin_capture_layer import PluginCaptureLayer
                from app.models import CaptureRegion, Rectangle
                from app.interfaces import CaptureSource
                
                progress.setLabelText(tr("capture_test_creating_layer"))
                progress.setValue(30)
                
                # Create plugin-based capture layer
                capture_layer = PluginCaptureLayer(config_manager=self.config_manager)
                
                progress.setLabelText(tr("capture_test_loading_plugin").format(method=method_name))
                progress.setValue(40)
                
                # Set the active plugin
                if not capture_layer.plugin_manager.set_active_plugin(plugin_name):
                    raise Exception(f"Failed to load plugin: {plugin_name}")
                
                progress.setLabelText(tr("capture_test_capturing"))
                progress.setValue(60)
                
                # Create test region (small region in center of screen)
                test_region = CaptureRegion(
                    rectangle=Rectangle(x=100, y=100, width=400, height=300),
                    monitor_id=0
                )
                
                # Capture 3 frames and measure performance
                times = []
                for i in range(3):
                    start = time.time()
                    frame = capture_layer.capture_frame(CaptureSource.CUSTOM_REGION, test_region)
                    elapsed = time.time() - start
                    times.append(elapsed)
                    
                    if frame is None:
                        raise Exception("Capture returned None")
                    
                    progress.setValue(60 + (i + 1) * 10)
                
                progress.setValue(100)
                
                # Calculate statistics
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                fps = 1.0 / avg_time if avg_time > 0 else 0
                
                # Get actual method used
                actual_method = plugin_name
                
                # Show results
                QMessageBox.information(
                    self,
                    tr("capture_test_success_title"),
                    tr("capture_test_success_msg").format(
                        method=method_name,
                        plugin=actual_method,
                        width=frame.data.shape[1],
                        height=frame.data.shape[0],
                        avg=avg_time*1000,
                        min=min_time*1000,
                        max=max_time*1000,
                        fps=fps
                    )
                )
                
                # Cleanup
                capture_layer.plugin_manager.unload_plugin(plugin_name)
                
            except Exception as e:
                progress.close()
                import traceback
                error_details = traceback.format_exc()
                logger.error("Capture test failed: %s", error_details)
                QMessageBox.critical(
                    self,
                    tr("capture_test_failed_title"),
                    tr("capture_test_failed_msg").format(
                        method=method_name,
                        error=str(e)
                    )
                )
            
        except Exception as e:
            logger.error("Capture test error: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("capture_test_error_title"),
                tr("capture_test_error_msg").format(error=str(e))
            )
    
    def _detect_monitors(self):
        """Detect and update available monitors."""
        try:
            # Try to detect monitors using PyQt6
            from PyQt6.QtWidgets import QApplication
            screens = QApplication.screens()
            
            # Clear existing items
            self.monitor_combo.clear()
            
            # Add primary monitor
            self.monitor_combo.addItem(tr("capture_primary_monitor"), 0)
            
            # Add detected monitors
            for i, screen in enumerate(screens):
                geometry = screen.geometry()
                name = screen.name()
                self.monitor_combo.addItem(
                    f"{name} ({geometry.width()}x{geometry.height()})",
                    i,
                )
            
            # Add "All Monitors" option
            self.monitor_combo.addItem(tr("capture_all_monitors"), -1)
            
            # Show success message
            QMessageBox.information(
                self,
                tr("capture_monitors_detected_title"),
                tr("capture_monitors_detected_msg").format(count=len(screens))
            )
            
            logger.info("Detected %d monitor(s)", len(screens))
            
        except Exception as e:
            logger.error("Failed to detect monitors: %s", e)
            QMessageBox.warning(
                self,
                tr("capture_detection_failed_title"),
                tr("capture_detection_failed_msg").format(error=str(e))
            )
    
    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        
        # Capture method
        if self.method_directx_radio and self.method_directx_radio.isChecked():
            state['capture_mode'] = 'directx'
        elif hasattr(self, 'method_bettercam_radio') and self.method_bettercam_radio and self.method_bettercam_radio.isChecked():
            state['capture_mode'] = 'bettercam'
        elif self.method_screenshot_radio and self.method_screenshot_radio.isChecked():
            state['capture_mode'] = 'screenshot'
        else:
            state['capture_mode'] = 'auto'
        
        # FPS
        if self.fps_spinbox:
            state['fps'] = self.fps_spinbox.value()
        
        # Quality (index-based to avoid translated text issues)
        if self.quality_combo:
            state['quality'] = self.quality_combo.currentIndex()
        
        # Monitor (device ID from item data)
        if hasattr(self, 'monitor_combo') and self.monitor_combo:
            monitor_id = self.monitor_combo.currentData()
            state['monitor_index'] = monitor_id if monitor_id is not None else 0
        
        # Additional options
        if hasattr(self, 'fallback_check') and self.fallback_check:
            state['fallback_enabled'] = self.fallback_check.isChecked()
        if hasattr(self, 'small_text_enhancement_check') and self.small_text_enhancement_check:
            state['enhance_small_text'] = self.small_text_enhancement_check.isChecked()
        if hasattr(self, 'denoise_check') and self.denoise_check:
            state['enhance_denoise'] = self.denoise_check.isChecked()
        if hasattr(self, 'binarize_check') and self.binarize_check:
            state['enhance_binarize'] = self.binarize_check.isChecked()
        if hasattr(self, 'overlay_screenshot_check') and self.overlay_screenshot_check:
            state['overlay_visible_screenshots'] = self.overlay_screenshot_check.isChecked()
        
        return state
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Block signals during loading to prevent triggering change events
            self.blockSignals(True)
            
            # Load capture method
            capture_mode = self.config_manager.get_setting('capture.method', 'auto')
            
            # Check if requested mode is available, otherwise use auto
            if capture_mode == 'directx' and not self.available_methods['directx']['available']:
                logger.warning("DirectX not available, switching to auto mode")
                capture_mode = 'auto'
            elif capture_mode == 'bettercam' and not self.available_methods['bettercam']['available']:
                logger.warning("BetterCam not available, switching to auto mode")
                capture_mode = 'auto'
            elif capture_mode == 'screenshot' and not self.available_methods['screenshot']['available']:
                logger.warning("Screenshot not available, switching to auto mode")
                capture_mode = 'auto'
            
            # Set the appropriate radio button
            if capture_mode == 'directx' and self.method_directx_radio:
                self.method_directx_radio.setChecked(True)
            elif capture_mode == 'bettercam' and self.method_bettercam_radio:
                self.method_bettercam_radio.setChecked(True)
            elif capture_mode == 'screenshot' and self.method_screenshot_radio:
                self.method_screenshot_radio.setChecked(True)
            elif self.method_auto_radio:
                self.method_auto_radio.setChecked(True)
            
            # Apply hardware gating to DirectX radio button
            try:
                gate = get_hardware_gate(self.config_manager)
                directx_available = gate.is_available(GatedFeature.DIRECTX_CAPTURE)
                if self.method_directx_radio:
                    self.method_directx_radio.setEnabled(directx_available)
                    if not directx_available:
                        self.set_translatable_text(
                            self.method_directx_radio, "capture_requires_gpu_tooltip",
                            method="setToolTip"
                        )
                    else:
                        self.method_directx_radio.setToolTip("")
            except Exception as e:
                logger.warning("Failed to apply hardware gating in capture tab: %s", e)
            
            # Load FPS
            if self.fps_slider and self.fps_spinbox:
                fps = self.config_manager.get_setting('capture.fps', 30)
                self.fps_slider.setValue(fps)
                self.fps_spinbox.setValue(fps)
            
            # Load quality (index-based)
            if self.quality_combo:
                quality = self.config_manager.get_setting('capture.quality', 'high')
                quality_map = {'low': 0, 'medium': 1, 'high': 2, 'ultra': 3}
                quality_idx = quality_map.get(quality, 2)
                self.quality_combo.setCurrentIndex(quality_idx)
            
            # Load monitor (find item by device ID stored as item data)
            if self.monitor_combo:
                monitor_id = self.config_manager.get_setting('capture.monitor_index', 0)
                idx = self.monitor_combo.findData(monitor_id)
                if idx >= 0:
                    self.monitor_combo.setCurrentIndex(idx)
                else:
                    self.monitor_combo.setCurrentIndex(0)
            
            # Load additional options
            if self.fallback_check:
                fallback = self.config_manager.get_setting('capture.fallback_enabled', True)
                self.fallback_check.setChecked(fallback)
            
            if self.small_text_enhancement_check:
                small_text_enhancement = self.config_manager.get_setting('capture.enhance_small_text', False)
                self.small_text_enhancement_check.setChecked(small_text_enhancement)
                
                # Load sub-options
                if self.denoise_check:
                    denoise = self.config_manager.get_setting('capture.enhance_denoise', False)
                    self.denoise_check.setChecked(denoise)
                    self.denoise_check.setEnabled(small_text_enhancement)
                
                if self.binarize_check:
                    binarize = self.config_manager.get_setting('capture.enhance_binarize', False)
                    self.binarize_check.setChecked(binarize)
                    self.binarize_check.setEnabled(small_text_enhancement)
            
            if self.overlay_screenshot_check:
                overlay_visible = self.config_manager.get_setting('overlay.visible_in_screenshots', False)
                self.overlay_screenshot_check.setChecked(overlay_visible)
            
            # Unblock signals
            self.blockSignals(False)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            logger.debug("Capture tab configuration loaded")
            
        except Exception as e:
            self.blockSignals(False)
            logger.warning("Failed to load capture tab config: %s", e, exc_info=True)
    
    def save_config(self):
        """
        Save configuration to config manager.
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"
        
        try:
            # Save capture method
            if self.method_directx_radio and self.method_directx_radio.isChecked():
                capture_mode = 'directx'
            elif self.method_bettercam_radio and self.method_bettercam_radio.isChecked():
                capture_mode = 'bettercam'
            elif self.method_screenshot_radio and self.method_screenshot_radio.isChecked():
                capture_mode = 'screenshot'
            else:
                capture_mode = 'auto'
            
            self.config_manager.set_setting('capture.method', capture_mode)
            
            # Save FPS
            self.config_manager.set_setting('capture.fps', self.fps_spinbox.value())
            
            # Save quality (index-based)
            quality_values = ['low', 'medium', 'high', 'ultra']
            self.config_manager.set_setting(
                'capture.quality',
                quality_values[self.quality_combo.currentIndex()]
            )
            
            # Save monitor index (device ID stored as item data)
            monitor_id = self.monitor_combo.currentData()
            if monitor_id is None:
                monitor_id = 0
            self.config_manager.set_setting('capture.monitor_index', monitor_id)
            
            # Save additional options
            self.config_manager.set_setting('capture.fallback_enabled', self.fallback_check.isChecked())
            self.config_manager.set_setting('capture.enhance_small_text', self.small_text_enhancement_check.isChecked())
            
            # Save sub-options for small text enhancement
            if self.denoise_check:
                self.config_manager.set_setting('capture.enhance_denoise', self.denoise_check.isChecked())
            if self.binarize_check:
                self.config_manager.set_setting('capture.enhance_binarize', self.binarize_check.isChecked())
            
            # Save overlay screenshot visibility
            if self.overlay_screenshot_check:
                self.config_manager.set_setting('overlay.visible_in_screenshots', self.overlay_screenshot_check.isChecked())
            
            # Save the configuration file
            success, error_msg = self.config_manager.save_config()
            
            if not success:
                return False, error_msg
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            logger.info("Capture tab configuration saved")
            return True, ""
            
        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error("%s", error_msg, exc_info=True)
            return False, error_msg
    
    def validate(self) -> bool:
        """
        Validate settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        # Validate FPS range
        fps = self.fps_spinbox.value()
        if fps < 5 or fps > 30:
            QMessageBox.warning(
                self,
                tr("capture_invalid_fps_title"),
                tr("capture_invalid_fps_msg").format(fps=fps)
            )
            return False
        
        # All other settings are from dropdowns/radio buttons, so they're always valid
        return True
