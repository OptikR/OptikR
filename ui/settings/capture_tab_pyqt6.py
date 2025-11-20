"""
Capture Settings Tab - PyQt6 Implementation
Capture method, region, performance, and multi-monitor configuration.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QRadioButton, QCheckBox, QPushButton, QSpinBox, QSlider,
    QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.translations import TranslatableMixin


class CaptureSettingsTab(TranslatableMixin, QWidget):
    """Capture settings including method, region, performance, and multi-monitor."""
    
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
        self.method_screenshot_radio = None
        self.method_auto_radio = None
        self.method_button_group = None
        
        # Capture region widgets
        self.region_full_radio = None
        self.region_window_radio = None
        self.region_custom_radio = None
        self.region_button_group = None
        
        # Performance widgets
        self.fps_slider = None
        self.fps_spinbox = None
        self.quality_combo = None
        
        # Multi-monitor widgets
        self.monitor_combo = None
        self.detect_monitors_btn = None
        
        # Additional options
        self.adaptive_check = None
        self.fallback_check = None
        self.small_text_enhancement_check = None
        self.denoise_check = None
        self.binarize_check = None
        
        # Initialize UI
        self._init_ui()
    
    def _detect_available_capture_methods(self):
        """
        Detect which capture methods are available on this system.
        
        Returns:
            dict: Dictionary with method availability and details
        """
        methods = {
            'directx': {'available': False, 'name': 'DirectX Desktop Duplication', 'reason': '', 'performance': ''},
            'screenshot': {'available': False, 'name': 'Screenshot API', 'reason': '', 'performance': ''},
            'auto': {'available': True, 'name': 'Auto-detect', 'reason': '', 'performance': ''}  # Always available
        }
        
        # Check DirectX availability using dxcam (the actual library we use)
        try:
            import dxcam
            # Try to create a test camera
            test_camera = dxcam.create(device_idx=0, output_idx=0)
            if test_camera is not None:
                methods['directx']['available'] = True
                methods['directx']['reason'] = 'dxcam library available (GPU-accelerated)'
                methods['directx']['performance'] = '~7-8ms per frame (~140 FPS) - Best for full-screen'
                del test_camera  # Clean up test camera
                print("[INFO] DirectX capture: Available via dxcam")
            else:
                methods['directx']['available'] = False
                methods['directx']['reason'] = 'dxcam failed to create camera'
                print("[INFO] DirectX capture: dxcam camera creation failed")
        except ImportError:
            methods['directx']['available'] = False
            methods['directx']['reason'] = 'dxcam library not installed (pip install dxcam)'
            print("[INFO] DirectX capture: dxcam not installed")
        except Exception as e:
            methods['directx']['available'] = False
            methods['directx']['reason'] = f'DirectX initialization failed: {str(e)}'
            print(f"[INFO] DirectX capture: Not available ({e})")
        
        # Check Screenshot methods availability
        screenshot_methods = []
        
        # Check Win32 GDI (fastest screenshot method)
        try:
            import win32gui
            import win32ui
            import win32con
            screenshot_methods.append('Win32 GDI (fastest)')
        except:
            pass
        
        # Check MSS
        try:
            import mss
            screenshot_methods.append('MSS')
        except:
            pass
        
        # Check PIL ImageGrab
        try:
            from PIL import ImageGrab
            ImageGrab.grab(bbox=(0, 0, 10, 10))
            screenshot_methods.append('PIL ImageGrab')
        except:
            pass
        
        if screenshot_methods:
            methods['screenshot']['available'] = True
            methods['screenshot']['reason'] = f"Available: {', '.join(screenshot_methods)}"
            methods['screenshot']['performance'] = '~11-12ms per frame (~85 FPS) - Best for small regions'
            print(f"[INFO] Screenshot capture: Available ({', '.join(screenshot_methods)})")
        else:
            methods['screenshot']['available'] = False
            methods['screenshot']['reason'] = 'No screenshot libraries available'
            print("[WARNING] Screenshot capture: Not available")
        
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
        # Capture Region section removed as requested
        # self._create_capture_region_section(content_layout)
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
        
        # Method label with Available count
        method_header_layout = QHBoxLayout()
        method_label = self._create_label("Select capture method:", bold=True)
        method_header_layout.addWidget(method_label)
        
        # Count available methods
        available_count = sum(1 for m in self.available_methods.values() if m['available'])
        available_label = QLabel(f"({available_count} Available)")
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
            directx_desc = QLabel(
                f"<b>Performance:</b> {self.available_methods['directx']['performance']}<br>"
                f"<b>Best for:</b> Full-screen or large region captures (>50% of screen)<br>"
                f"<b>Technology:</b> Uses DirectX Desktop Duplication API via dxcam library<br>"
                f"<b>GPU Usage:</b> Low (hardware-accelerated)<br>"
                f"<b>CPU Usage:</b> Very Low"
            )
            directx_desc.setWordWrap(True)
            directx_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
            layout.addWidget(directx_desc)
            
            if first_available is None:
                first_available = self.method_directx_radio
            button_id += 1
        else:
            # Show as unavailable
            unavailable_label = QLabel("🚀 DirectX Desktop Duplication (Not Available)")
            unavailable_label.setStyleSheet("color: #999999; font-size: 9pt;")
            layout.addWidget(unavailable_label)
            
            reason_label = QLabel(f"   ⚠️ {self.available_methods['directx']['reason']}")
            reason_label.setWordWrap(True)
            reason_label.setStyleSheet("color: #999999; font-size: 8pt; margin-left: 25px; margin-bottom: 8px;")
            layout.addWidget(reason_label)
            
            # Add install instructions if dxcam is missing
            if 'not installed' in self.available_methods['directx']['reason']:
                install_label = QLabel("   💡 To enable: Open terminal and run: <b>pip install dxcam</b>")
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
            screenshot_desc = QLabel(
                f"<b>Performance:</b> {self.available_methods['screenshot']['performance']}<br>"
                f"<b>Best for:</b> Small region captures (<50% of screen), single frames<br>"
                f"<b>Technology:</b> {self.available_methods['screenshot']['reason']}<br>"
                f"<b>GPU Usage:</b> None<br>"
                f"<b>CPU Usage:</b> Moderate"
            )
            screenshot_desc.setWordWrap(True)
            screenshot_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
            layout.addWidget(screenshot_desc)
            
            if first_available is None:
                first_available = self.method_screenshot_radio
            button_id += 1
        else:
            # Show as unavailable
            unavailable_label = QLabel("📸 Screenshot API (Not Available)")
            unavailable_label.setStyleSheet("color: #999999; font-size: 9pt;")
            layout.addWidget(unavailable_label)
            
            reason_label = QLabel(f"   ⚠️ {self.available_methods['screenshot']['reason']}")
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
            available_list.append("DirectX (primary)")
        if self.available_methods['screenshot']['available']:
            available_list.append("Screenshot (fallback)")
        
        auto_desc = QLabel(
            f"<b>Intelligent Selection:</b> Automatically chooses the best capture method<br>"
            f"<b>Available methods:</b> {', '.join(available_list) if available_list else 'None'}<br>"
            f"<b>Behavior:</b> Tries DirectX first, falls back to Screenshot if needed<br>"
            f"<b>Adaptive:</b> Switches methods based on performance and reliability"
        )
        auto_desc.setWordWrap(True)
        auto_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 10px;")
        layout.addWidget(auto_desc)
        
        # Add a note about the recommendation
        if self.available_methods['directx']['available']:
            recommendation = QLabel(
                "💡 <b>Recommendation:</b> Use Auto-Select for best results. "
                "DirectX will be used for full-screen captures, Screenshot for small regions."
            )
        else:
            recommendation = QLabel(
                "💡 <b>Note:</b> DirectX not available. Install dxcam for better performance: <b>pip install dxcam</b>"
            )
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
        
        test_info = QLabel("Test the selected capture method to verify it works correctly")
        test_info.setStyleSheet("color: #666666; font-size: 9pt;")
        test_layout.addWidget(test_info)
        test_layout.addStretch()
        
        layout.addLayout(test_layout)
        
        parent_layout.addWidget(group)
    
    def _create_capture_region_section(self, parent_layout):
        """Create capture region selection section."""
        group = QGroupBox()
        self.set_translatable_text(group, "capture_region_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Region label
        region_label = self._create_label("Select capture region:", bold=True)
        layout.addWidget(region_label)
        
        # Create button group for radio buttons
        self.region_button_group = QButtonGroup()
        
        # Full screen mode
        self.region_full_radio = QRadioButton()
        self.set_translatable_text(self.region_full_radio, "region_full_label")
        self.region_full_radio.setChecked(True)
        self.region_full_radio.toggled.connect(self.on_change)
        self.region_button_group.addButton(self.region_full_radio, 0)
        layout.addWidget(self.region_full_radio)
        
        # Full screen description
        full_desc = QLabel("Capture the entire screen. Best for full-screen applications.")
        full_desc.setWordWrap(True)
        full_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(full_desc)
        
        # Window mode
        self.region_window_radio = QRadioButton()
        self.set_translatable_text(self.region_window_radio, "region_window_label")
        self.region_window_radio.toggled.connect(self.on_change)
        self.region_button_group.addButton(self.region_window_radio, 1)
        layout.addWidget(self.region_window_radio)
        
        # Window description
        window_desc = QLabel("Capture only the active window. Useful for windowed applications.")
        window_desc.setWordWrap(True)
        window_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(window_desc)
        
        # Custom region mode
        self.region_custom_radio = QRadioButton()
        self.set_translatable_text(self.region_custom_radio, "region_custom_label")
        self.region_custom_radio.toggled.connect(self.on_change)
        self.region_button_group.addButton(self.region_custom_radio, 2)
        layout.addWidget(self.region_custom_radio)
        
        # Custom description
        custom_desc = QLabel("Define a custom rectangular region. Click 'Select Region' to choose area.")
        custom_desc.setWordWrap(True)
        custom_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(custom_desc)
        
        # Select region button (only enabled when custom is selected)
        select_region_btn = QPushButton()
        self.set_translatable_text(select_region_btn, "select_region_button")
        select_region_btn.setProperty("class", "action")
        select_region_btn.setEnabled(False)
        select_region_btn.clicked.connect(self._select_custom_region)
        
        # Enable/disable button based on custom radio selection
        self.region_custom_radio.toggled.connect(select_region_btn.setEnabled)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(select_region_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
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
        fps_label = self._create_label("Frame Rate (FPS):", bold=True)
        layout.addWidget(fps_label, 0, 0, Qt.AlignmentFlag.AlignLeft)
        
        # FPS slider (limited to 60 FPS for better control)
        self.fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.fps_slider.setRange(5, 60)
        self.fps_slider.setValue(30)
        self.fps_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.fps_slider.setTickInterval(5)
        self.fps_slider.setPageStep(5)
        self.fps_slider.setSingleStep(1)
        self.fps_slider.setMinimumWidth(200)
        self.fps_slider.valueChanged.connect(self._on_fps_slider_changed)
        layout.addWidget(self.fps_slider, 0, 1)
        
        # FPS spinbox (allows up to 120 FPS with manual input)
        self.fps_spinbox = CustomSpinBox()
        self.fps_spinbox.setRange(5, 120)
        self.fps_spinbox.setValue(30)
        self.fps_spinbox.setSuffix(" FPS")
        self.fps_spinbox.setMinimumWidth(100)
        self.fps_spinbox.valueChanged.connect(self._on_fps_spinbox_changed)
        layout.addWidget(self.fps_spinbox, 0, 2)
        
        # FPS description
        fps_desc = QLabel("Higher FPS = smoother capture but more CPU usage. Recommended: 30 FPS")
        fps_desc.setWordWrap(True)
        fps_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(fps_desc, 1, 0, 1, 3)
        
        # FPS warning label (shown when > 60 FPS)
        self.fps_warning_label = QLabel("⚠️ Warning: FPS above 60 significantly increases system resource usage!")
        self.fps_warning_label.setWordWrap(True)
        self.fps_warning_label.setStyleSheet("color: #FF9800; font-size: 9pt; font-weight: bold; margin-top: 5px;")
        self.fps_warning_label.setVisible(False)  # Hidden by default
        layout.addWidget(self.fps_warning_label, 2, 0, 1, 3)
        
        # Quality setting
        quality_label = self._create_label("Capture Quality:", bold=True)
        layout.addWidget(quality_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low", "Medium", "High", "Ultra"])
        self.quality_combo.setCurrentText("High")
        self.quality_combo.currentTextChanged.connect(self.on_change)
        layout.addWidget(self.quality_combo, 3, 1, 1, 2)
        
        # Quality description
        quality_desc = QLabel("Higher quality = better OCR accuracy but larger memory usage")
        quality_desc.setWordWrap(True)
        quality_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(quality_desc, 4, 0, 1, 3)
        
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
        
        monitor_label = self._create_label("Target Monitor:", bold=True)
        monitor_layout.addWidget(monitor_label)
        
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems(["Primary Monitor", "Monitor 1", "Monitor 2", "All Monitors"])
        self.monitor_combo.currentTextChanged.connect(self.on_change)
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
        monitor_info = QLabel(
            "💡 Tip: Use 'Detect Monitors' to refresh the list of available displays. "
            "Select 'All Monitors' to capture from multiple screens simultaneously."
        )
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
        
        # Adaptive capture
        self.adaptive_check = QCheckBox()
        self.set_translatable_text(self.adaptive_check, "adaptive_capture_label")
        self.adaptive_check.setChecked(True)
        self.adaptive_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.adaptive_check)
        
        adaptive_desc = QLabel(
            "Automatically adjusts capture rate based on screen activity. "
            "Reduces CPU usage when screen is static."
        )
        adaptive_desc.setWordWrap(True)
        adaptive_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(adaptive_desc)
        
        # Fallback mode
        self.fallback_check = QCheckBox()
        self.set_translatable_text(self.fallback_check, "fallback_mode_label")
        self.fallback_check.setChecked(True)
        self.fallback_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.fallback_check)
        
        fallback_desc = QLabel(
            "Automatically switch to alternative capture method if primary method fails. "
            "Ensures continuous operation."
        )
        fallback_desc.setWordWrap(True)
        fallback_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px; margin-bottom: 8px;")
        layout.addWidget(fallback_desc)
        
        # Small text enhancement
        self.small_text_enhancement_check = QCheckBox()
        self.set_translatable_text(self.small_text_enhancement_check, "small_text_enhancement_label")
        self.small_text_enhancement_check.setChecked(False)  # Disabled by default
        self.small_text_enhancement_check.stateChanged.connect(self._on_small_text_enhancement_changed)
        layout.addWidget(self.small_text_enhancement_check)
        
        small_text_desc = QLabel(
            "Upscale and enhance captured images to improve OCR accuracy for small text. "
            "Uses 2x upscaling, sharpening, and contrast enhancement. "
            "May increase processing time slightly."
        )
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
        
        denoise_desc = QLabel("Reduces image noise before enhancement. Recommended for low-quality captures.")
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
        
        binarize_desc = QLabel("Converts to pure black/white for very small text. Best for clean backgrounds.")
        binarize_desc.setWordWrap(True)
        binarize_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        sub_options_layout.addWidget(binarize_desc)
        
        layout.addLayout(sub_options_layout)
        
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
        # Update slider to match spinbox (without triggering its signal)
        # Only update slider if value is within slider range (5-60)
        self.fps_slider.blockSignals(True)
        if value <= 60:
            self.fps_slider.setValue(value)
        else:
            self.fps_slider.setValue(60)  # Max out slider at 60
        self.fps_slider.blockSignals(False)
        
        # Show/hide warning for high FPS values
        if hasattr(self, 'fps_warning_label'):
            self.fps_warning_label.setVisible(value > 60)
        
        # Emit change signal
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
    
    def _select_custom_region(self):
        """Handle custom region selection."""
        # Placeholder for region selection functionality
        QMessageBox.information(
            self,
            "Select Region",
            "Region selection tool will be implemented here.\n\n"
            "This will allow you to click and drag to define a custom capture area."
        )
    
    def _test_capture_method(self):
        """Test the selected capture method."""
        try:
            import time
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import Qt
            
            # Determine which method to test
            if self.method_directx_radio and self.method_directx_radio.isChecked():
                method_name = "DirectX (DXCam)"
                plugin_name = "dxcam_capture_gpu"
            elif self.method_screenshot_radio and self.method_screenshot_radio.isChecked():
                method_name = "Screenshot (CPU)"
                plugin_name = "screenshot_capture_cpu"
            else:
                method_name = "Auto-Select"
                plugin_name = "dxcam_capture_gpu"  # Default to DXCam
            
            # Create progress dialog
            progress = QProgressDialog(f"Testing {method_name} capture method...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Testing Capture")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            # Test the capture method
            try:
                progress.setLabelText(f"Initializing {method_name} capture...")
                progress.setValue(20)
                
                # Import plugin-based capture layer
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                
                from app.capture.plugin_capture_layer import PluginCaptureLayer
                from app.models import CaptureRegion, Rectangle
                from app.interfaces import CaptureSource
                
                progress.setLabelText(f"Creating plugin capture layer...")
                progress.setValue(30)
                
                # Create plugin-based capture layer
                capture_layer = PluginCaptureLayer(config_manager=self.config_manager)
                
                progress.setLabelText(f"Loading {method_name} plugin...")
                progress.setValue(40)
                
                # Set the active plugin
                if not capture_layer.plugin_manager.set_active_plugin(plugin_name):
                    raise Exception(f"Failed to load plugin: {plugin_name}")
                
                progress.setLabelText(f"Capturing test frame...")
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
                    "Capture Test Successful",
                    f"<b>{method_name} Capture Test Results:</b><br><br>"
                    f"<b>Status:</b> ✅ Working<br>"
                    f"<b>Plugin:</b> {actual_method}<br>"
                    f"<b>Frame Size:</b> {frame.data.shape[1]}x{frame.data.shape[0]}<br>"
                    f"<b>Average Time:</b> {avg_time*1000:.2f}ms<br>"
                    f"<b>Min Time:</b> {min_time*1000:.2f}ms<br>"
                    f"<b>Max Time:</b> {max_time*1000:.2f}ms<br>"
                    f"<b>Theoretical FPS:</b> {fps:.1f}<br><br>"
                    f"The capture method is working correctly!"
                )
                
                # Cleanup
                capture_layer.plugin_manager.unload_plugin(plugin_name)
                
            except Exception as e:
                progress.close()
                import traceback
                error_details = traceback.format_exc()
                print(f"[ERROR] Capture test failed: {error_details}")
                QMessageBox.critical(
                    self,
                    "Capture Test Failed",
                    f"<b>{method_name} capture test failed:</b><br><br>"
                    f"<b>Error:</b> {str(e)}<br><br>"
                    f"<b>Possible solutions:</b><br>"
                    f"• Try a different capture method<br>"
                    f"• Check if required libraries are installed<br>"
                    f"• Restart the application<br>"
                    f"• Check the console for detailed error messages"
                )
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Test Error",
                f"Failed to run capture test:\n\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _detect_monitors(self):
        """Detect and update available monitors."""
        try:
            # Try to detect monitors using PyQt6
            from PyQt6.QtWidgets import QApplication
            screens = QApplication.screens()
            
            # Clear existing items
            self.monitor_combo.clear()
            
            # Add primary monitor
            self.monitor_combo.addItem("Primary Monitor")
            
            # Add detected monitors
            for i, screen in enumerate(screens):
                geometry = screen.geometry()
                name = screen.name() if hasattr(screen, 'name') else f"Monitor {i + 1}"
                self.monitor_combo.addItem(
                    f"{name} ({geometry.width()}x{geometry.height()})"
                )
            
            # Add "All Monitors" option
            self.monitor_combo.addItem("All Monitors")
            
            # Show success message
            QMessageBox.information(
                self,
                "Monitors Detected",
                f"Successfully detected {len(screens)} monitor(s).\n\n"
                f"Select your preferred monitor from the dropdown."
            )
            
            print(f"[INFO] Detected {len(screens)} monitor(s)")
            
        except Exception as e:
            print(f"[ERROR] Failed to detect monitors: {e}")
            QMessageBox.warning(
                self,
                "Detection Failed",
                f"Failed to detect monitors:\n\n{str(e)}\n\n"
                f"Using default monitor list."
            )
    
    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        
        # Capture method
        if self.method_directx_radio and self.method_directx_radio.isChecked():
            state['capture_mode'] = 'directx'
        elif self.method_screenshot_radio and self.method_screenshot_radio.isChecked():
            state['capture_mode'] = 'screenshot'
        else:
            state['capture_mode'] = 'auto'
        
        # Capture region
        if self.region_full_radio and self.region_full_radio.isChecked():
            state['capture_region'] = 'full_screen'
        elif self.region_window_radio and self.region_window_radio.isChecked():
            state['capture_region'] = 'window'
        elif self.region_custom_radio and self.region_custom_radio.isChecked():
            state['capture_region'] = 'custom'
        else:
            state['capture_region'] = 'full_screen'
        
        # FPS
        if self.fps_spinbox:
            state['fps'] = self.fps_spinbox.value()
        
        # Quality
        if self.quality_combo:
            state['quality'] = self.quality_combo.currentText()
        
        return state
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Block signals during loading to prevent triggering change events
            self.blockSignals(True)
            
            # Load capture method
            capture_mode = self.config_manager.get_setting('capture.mode', 'auto')
            
            # Check if requested mode is available, otherwise use auto
            if capture_mode == 'directx' and not self.available_methods['directx']['available']:
                print(f"[WARNING] DirectX not available, switching to auto mode")
                capture_mode = 'auto'
            elif capture_mode == 'screenshot' and not self.available_methods['screenshot']['available']:
                print(f"[WARNING] Screenshot not available, switching to auto mode")
                capture_mode = 'auto'
            
            # Set the appropriate radio button
            if capture_mode == 'directx' and self.method_directx_radio:
                self.method_directx_radio.setChecked(True)
            elif capture_mode == 'screenshot' and self.method_screenshot_radio:
                self.method_screenshot_radio.setChecked(True)
            elif self.method_auto_radio:
                self.method_auto_radio.setChecked(True)
            
            # Load capture region
            capture_region = self.config_manager.get_setting('capture.region', 'full_screen')
            
            # Handle both string and dict formats
            if isinstance(capture_region, dict):
                # If it's a dict, default to full_screen
                region_type = 'full_screen'
            else:
                region_type = capture_region
            
            region_map = {'full_screen': 0, 'window': 1, 'custom': 2}
            region_id = region_map.get(region_type.lower() if isinstance(region_type, str) else 'full_screen', 0)
            
            # Only set if widgets are initialized
            if self.region_full_radio and self.region_window_radio and self.region_custom_radio:
                if region_id == 0:
                    self.region_full_radio.setChecked(True)
                elif region_id == 1:
                    self.region_window_radio.setChecked(True)
                elif region_id == 2:
                    self.region_custom_radio.setChecked(True)
            
            # Load FPS
            if self.fps_slider and self.fps_spinbox:
                fps = self.config_manager.get_setting('capture.fps', 30)
                self.fps_slider.setValue(fps)
                self.fps_spinbox.setValue(fps)
            
            # Load quality
            if self.quality_combo:
                quality = self.config_manager.get_setting('capture.quality', 'high')
                quality_index = self.quality_combo.findText(quality.capitalize())
                if quality_index >= 0:
                    self.quality_combo.setCurrentIndex(quality_index)
            
            # Load monitor
            if self.monitor_combo:
                monitor = self.config_manager.get_setting('capture.monitor', 'primary')
                # Convert to string if it's an integer (monitor ID)
                monitor_str = str(monitor).lower() if isinstance(monitor, int) else monitor.lower()
                # Try to find matching monitor in combo box
                for i in range(self.monitor_combo.count()):
                    if monitor_str in self.monitor_combo.itemText(i).lower():
                        self.monitor_combo.setCurrentIndex(i)
                        break
            
            # Load additional options
            if self.adaptive_check:
                adaptive = self.config_manager.get_setting('capture.adaptive', True)
                self.adaptive_check.setChecked(adaptive)
            
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
            
            # Unblock signals
            self.blockSignals(False)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            print("[DEBUG] Capture tab configuration loaded")
            
        except Exception as e:
            self.blockSignals(False)
            print(f"[WARNING] Failed to load capture tab config: {e}")
            import traceback
            traceback.print_exc()
    
    def save_config(self):
        """Save configuration to config manager."""
        if not self.config_manager:
            return
        
        try:
            # Save capture method
            if self.method_directx_radio and self.method_directx_radio.isChecked():
                capture_mode = 'directx'
            elif self.method_screenshot_radio and self.method_screenshot_radio.isChecked():
                capture_mode = 'screenshot'
            else:
                capture_mode = 'auto'
            
            self.config_manager.set_setting('capture.mode', capture_mode)
            
            # Save capture region
            if self.region_full_radio and self.region_full_radio.isChecked():
                capture_region = 'full_screen'
            elif self.region_window_radio and self.region_window_radio.isChecked():
                capture_region = 'window'
            else:
                capture_region = 'custom'
            
            self.config_manager.set_setting('capture.region', capture_region)
            
            # Save FPS
            self.config_manager.set_setting('capture.fps', self.fps_spinbox.value())
            
            # Save quality
            self.config_manager.set_setting('capture.quality', self.quality_combo.currentText().lower())
            
            # Save monitor
            monitor_text = self.monitor_combo.currentText()
            if "Primary" in monitor_text:
                monitor = 'primary'
            elif "All" in monitor_text:
                monitor = 'all'
            else:
                monitor = monitor_text.split()[0].lower()  # Extract monitor number
            
            self.config_manager.set_setting('capture.monitor', monitor)
            
            # Save additional options
            self.config_manager.set_setting('capture.adaptive', self.adaptive_check.isChecked())
            self.config_manager.set_setting('capture.fallback_enabled', self.fallback_check.isChecked())
            self.config_manager.set_setting('capture.enhance_small_text', self.small_text_enhancement_check.isChecked())
            
            # Save sub-options for small text enhancement
            if self.denoise_check:
                self.config_manager.set_setting('capture.enhance_denoise', self.denoise_check.isChecked())
            if self.binarize_check:
                self.config_manager.set_setting('capture.enhance_binarize', self.binarize_check.isChecked())
            
            # Save the configuration file
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            print("[INFO] Capture tab configuration saved")
            
        except Exception as e:
            print(f"[ERROR] Failed to save capture tab config: {e}")
            import traceback
            traceback.print_exc()
    
    def validate(self) -> bool:
        """
        Validate settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        # Validate FPS range
        fps = self.fps_spinbox.value()
        if fps < 5 or fps > 120:
            QMessageBox.warning(
                self,
                "Invalid FPS",
                f"FPS must be between 5 and 120.\n\nCurrent value: {fps}"
            )
            return False
        
        # All other settings are from dropdowns/radio buttons, so they're always valid
        return True
