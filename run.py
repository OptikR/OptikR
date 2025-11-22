"""
Test window to verify PyQt6 styling system.
Displays various widgets with the base.qss stylesheet applied.
"""

import sys
import json
import os
import warnings
from pathlib import Path

# ============================================================================
# EXE FIX: Redirect stdout/stderr for windowed applications
# ============================================================================
# When running as a windowed EXE (console=False), sys.stdout and sys.stderr
# are None, which causes crashes when code tries to use print() or flush().
# This fix redirects them to devnull with UTF-8 encoding to handle Unicode.
if getattr(sys, 'frozen', False):
    # Running as EXE
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
# ============================================================================

# Suppress common warnings for cleaner console output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='paddle')
warnings.filterwarnings('ignore', category=UserWarning, module='transformers')
warnings.filterwarnings('ignore', message='.*resume_download.*')
warnings.filterwarnings('ignore', message='.*torch.load.*')
warnings.filterwarnings('ignore', message='.*_pytree.*')

# Suppress paddle verbose output
os.environ['GLOG_minloglevel'] = '3'  # Suppress all glog messages except FATAL
os.environ['FLAGS_pir_apply_shape_optimization_pass'] = '0'  # Reduce paddle warnings
os.environ['PPOCR_SHOW_LOG'] = '0'  # Suppress PaddleOCR verbose logging
os.environ['PADDLEOCR_VERBOSE'] = '0'  # Additional PaddleOCR suppression

# Suppress stdout/stderr from libraries
import io
import contextlib
import logging

# Configure logging to suppress verbose library output
logging.getLogger('manga_ocr').setLevel(logging.CRITICAL)
logging.getLogger('manga_ocr.ocr').setLevel(logging.CRITICAL)
logging.getLogger('transformers').setLevel(logging.CRITICAL)
logging.getLogger('huggingface_hub').setLevel(logging.CRITICAL)
logging.getLogger('paddleocr').setLevel(logging.CRITICAL)

# Suppress root logger warnings
logging.getLogger().setLevel(logging.ERROR)

# Add root directory to Python path for imports
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))


# ============================================================================
# PYTORCH AUTO-INSTALLATION: Install PyTorch on first run if not present
# ============================================================================
def check_and_install_pytorch():
    """
    Check if PyTorch is installed. If not, auto-install CPU version.
    This ensures the app works on all systems without manual PyTorch installation.
    
    Returns:
        tuple: (success: bool, is_gpu: bool, message: str)
    """
    try:
        import torch
        is_gpu = torch.cuda.is_available()
        version = torch.__version__
        
        if is_gpu:
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[INFO] PyTorch {version} detected with GPU: {gpu_name}")
        else:
            print(f"[INFO] PyTorch {version} detected (CPU mode)")
        
        return True, is_gpu, f"PyTorch {version} ready"
        
    except ImportError:
        print("\n" + "="*70)
        print("[FIRST RUN] PyTorch not found - Installing CPU version...")
        print("This is a one-time setup and will take 2-3 minutes.")
        print("="*70 + "\n")
        
        try:
            import subprocess
            
            # Install CPU version (works on all systems, ~200MB download)
            cmd = [
                sys.executable, '-m', 'pip', 'install',
                'torch', 'torchvision', 'torchaudio',
                '--index-url', 'https://download.pytorch.org/whl/cpu'
            ]
            
            print("[INFO] Running: pip install torch torchvision torchaudio (CPU version)")
            print("[INFO] Please wait...")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                print("\n[SUCCESS] PyTorch CPU installed successfully!")
                print("[INFO] Restarting application to load PyTorch...\n")
                
                # Restart the application to load the newly installed PyTorch
                os.execv(sys.executable, [sys.executable] + sys.argv)
                
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                print(f"\n[ERROR] PyTorch installation failed: {error_msg}")
                return False, False, f"Installation failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            print("\n[ERROR] PyTorch installation timed out (network issue?)")
            return False, False, "Installation timed out"
        except Exception as e:
            print(f"\n[ERROR] PyTorch installation error: {e}")
            return False, False, f"Installation error: {e}"
    
    except Exception as e:
        print(f"[ERROR] PyTorch check failed: {e}")
        return False, False, f"Check failed: {e}"


# Check and install PyTorch before any imports that depend on it
_pytorch_success, _pytorch_gpu, _pytorch_msg = check_and_install_pytorch()

if not _pytorch_success:
    print("\n" + "="*70)
    print("[CRITICAL] PyTorch installation failed!")
    print("="*70)
    print("\nPlease install PyTorch manually:")
    print("\nFor CPU-only systems:")
    print("  pip install -r requirements-cpu.txt")
    print("\nFor GPU systems (NVIDIA CUDA required):")
    print("  pip install -r requirements-gpu.txt")
    print("\n" + "="*70 + "\n")
    
    # Show error dialog if GUI is available
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "PyTorch Installation Required",
            "PyTorch could not be installed automatically.\n\n"
            "Please install it manually:\n\n"
            "CPU-only: pip install -r requirements-cpu.txt\n"
            "GPU: pip install -r requirements-gpu.txt\n\n"
            f"Error: {_pytorch_msg}"
        )
    except:
        pass
    
    sys.exit(1)

# ============================================================================

# Import structured logger
from app.utils.structured_logger import create_structured_logger, LoggingConfiguration

# Import PyQt6 overlay system (thread-safe version)
from ui.thread_safe_overlay import create_thread_safe_overlay_system

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QCheckBox, QRadioButton, QSlider, QProgressBar, QGroupBox,
    QTabWidget, QListWidget, QScrollArea, QFrame, QDialog, QSizePolicy,
    QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QTimer

# Import translation system
from app.translations import tr, set_language


def create_installation_info():
    """
    Automatically detect and create installation info.
    
    Returns:
        dict: Installation information with hardware detection
    """
    import torch
    from datetime import datetime
    
    install_info = {
        'created': datetime.now().isoformat(),
        'version': '0.1.1',
        'cuda': {
            'installed': torch.cuda.is_available(),
            'path': os.environ.get('CUDA_HOME', os.environ.get('CUDA_PATH', '')),
        },
        'pytorch': {
            'version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
            'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
        }
    }
    
    return install_info


def save_installation_info(install_info, config_manager):
    """
    Save installation info to consolidated config.
    
    Args:
        install_info: Installation information dictionary
        config_manager: Config manager instance (required)
    """
    # Save to consolidated config
    config_manager.set_installation_info(install_info)
    config_manager.save_config()
    print("[INFO] Installation info saved to consolidated config")


def load_installation_info(config_manager):
    """
    Load or create installation information including CUDA path.
    
    Args:
        config_manager: Config manager instance (required)
        
    Returns:
        dict: Installation information or None if failed
    """
    # Load from consolidated config
    install_info = config_manager.get_installation_info()
    if install_info and install_info.get('created'):
        print("[INFO] Loaded installation info from consolidated config")
    
    # Create new installation info if none exists
    if not install_info or not install_info.get('created'):
        print("[INFO] Creating installation info automatically...")
        install_info = create_installation_info()
        save_installation_info(install_info, config_manager)
        
        # Log detected hardware
        if install_info['pytorch']['cuda_available']:
            print(f"[INFO] GPU detected: {install_info['pytorch']['device_name']}")
        else:
            print("[INFO] No GPU detected - running in CPU mode")
    
    # Set CUDA environment variables if CUDA is installed
    if install_info:
        cuda_info = install_info.get('cuda', {})
        if cuda_info.get('installed') and cuda_info.get('path'):
            cuda_path = cuda_info['path']
            os.environ['CUDA_HOME'] = cuda_path
            os.environ['CUDA_PATH'] = cuda_path
            print(f"[INFO] CUDA path loaded: {cuda_path}")
            
            # Add CUDA bin to PATH if not already there
            cuda_bin = str(Path(cuda_path) / 'bin')
            if cuda_bin not in os.environ.get('PATH', ''):
                os.environ['PATH'] = cuda_bin + os.pathsep + os.environ.get('PATH', '')
                print(f"[INFO] Added CUDA bin to PATH: {cuda_bin}")
        
        # Log GPU availability
        pytorch_info = install_info.get('pytorch', {})
        if pytorch_info.get('cuda_available'):
            gpu_name = pytorch_info.get('device_name', 'Unknown GPU')
            print(f"[INFO] GPU acceleration available: {gpu_name}")
        else:
            print("[INFO] Running in CPU mode")
        
        # Log installed engines
        ocr_engine = install_info.get('ocr_engine', {}).get('name')
        if ocr_engine:
            print(f"[INFO] OCR engine: {ocr_engine}")
        
        translation_engine = install_info.get('translation_engine', {}).get('name')
        if translation_engine:
            print(f"[INFO] Translation engine: {translation_engine}")
    
    return install_info


def ensure_app_directories():
    """
    Ensure all required application directories exist.
    Creates directories if they don't exist, works for both Python and EXE.
    """
    from app.utils.path_utils import ensure_app_directory
    
    required_dirs = [
        'user_data',
        'user_data/config',
        'user_data/learned',
        'user_data/learned/translations',
        'user_data/exports',
        'user_data/exports/translations',
        'user_data/exports/screenshots',
        'user_data/exports/logs',
        'user_data/custom_plugins',
        'user_data/backups',
        'system_data',
        'system_data/ai_models',
        'system_data/ai_models/ocr',
        'system_data/ai_models/translation',
        'system_data/cache',
        'system_data/logs',
        'system_data/temp',
        'system_data/temp/processing',
        'system_data/temp/downloads',
        'plugins'
    ]
    
    for dir_name in required_dirs:
        ensure_app_directory(dir_name)
    
    print("[INFO] All application directories verified")


# Ensure all directories exist
ensure_app_directories()

# Import core modules (need this before loading installation info)
from app.core.config_manager import SimpleConfigManager

# Create config manager early so we can use consolidated config
_early_config_manager = SimpleConfigManager()

# Load installation info and set CUDA path before anything else
INSTALLATION_INFO = load_installation_info(_early_config_manager)

# Import dialogs
from ui.dialogs.consent_dialog import (
    check_user_consent,
    save_user_consent,
    show_consent_dialog
)
from ui.dialogs.help_dialog import show_help_dialog
from ui.dialogs.quick_ocr_switch_dialog import show_quick_ocr_switch_dialog

# Import UI components
from ui.sidebar.sidebar_widget import SidebarWidget
from ui.toolbar.main_toolbar import MainToolbar
from ui.loading_overlay import LoadingOverlay

# Import settings tabs
from ui.settings.general_tab_pyqt6 import GeneralSettingsTab
from ui.settings.capture_tab_pyqt6 import CaptureSettingsTab
from ui.settings.ocr_tab_pyqt6 import OCRSettingsTab
from ui.settings.translation_tab_pyqt6 import TranslationSettingsTab
from ui.settings.overlay_tab_pyqt6 import OverlaySettingsTab
from ui.settings.smart_dictionary_tab_pyqt6 import SmartDictionaryTab  # NEW!
from ui.settings.pipeline_management_tab_pyqt6 import PipelineManagementTab
from ui.settings.storage_tab_pyqt6 import StorageSettingsTab
from ui.settings.advanced_tab_pyqt6 import AdvancedSettingsTab

# Import additional widgets
from PyQt6.QtWidgets import QMessageBox
from datetime import datetime


# SimpleConfigManager and UserConsentDialog have been moved to separate modules
# See: core/config_manager.py and components/dialogs/consent_dialog.py


class StyleTestWindow(QMainWindow):
    """Test window showcasing PyQt6 styling matching reference UI."""
    
    def __init__(self):
        super().__init__()
        self.config_manager = SimpleConfigManager()
        self.has_unsaved_changes = False
        self.save_btn = None  # Will be set when toolbar is created
        self.start_btn = None  # Will be set when toolbar is created
        
        # Load UI language using LanguageManager (triggers signals for dynamic updates)
        ui_language = self.config_manager.get_setting('ui.language', 'en')
        from app.translations import get_language_manager
        self.language_manager = get_language_manager()
        self.language_manager.set_language(ui_language)
        print(f"[INFO] UI Language: {ui_language}")
        
        # Initialize structured logger
        from app.utils.structured_logger import LogSeverity
        log_level_str = self.config_manager.get_setting('logging.log_level', 'INFO').upper()
        log_level = LogSeverity[log_level_str] if log_level_str in LogSeverity.__members__ else LogSeverity.INFO
        
        log_config = LoggingConfiguration(
            log_level=log_level,
            log_to_file=self.config_manager.get_setting('logging.log_to_file', True),
            log_to_console=self.config_manager.get_setting('logging.enable_console_output', True),
            log_directory=self.config_manager.get_setting('logging.log_directory', 'system_data/logs'),
            enable_performance_logging=self.config_manager.get_setting('logging.enable_performance_logging', True)
        )
        self.logger = create_structured_logger(log_config)
        self.logger.log_info("SYSTEM", "app_init", "Application initializing")
        
        # Initialize PyQt6 overlay system (thread-safe)
        # Uses factory to choose between thread-based or process-based implementation
        from ui.overlay_factory import create_thread_safe_overlay_system
        self.overlay_system = create_thread_safe_overlay_system(self.config_manager)
        self.logger.log_info("SYSTEM", "overlay_init", "Thread-safe PyQt6 overlay system initialized")
        
        # Pipeline integration
        self.pipeline = None
        self.pipeline_running = False
        self.capture_region = None  # Will be set by region selector
        
        # Lazy loading: Track which tabs have been loaded
        self.loaded_tabs = {}  # Maps tab index to loaded tab widget
        self.tab_widget = None  # Will be set in create_content_area
        
        # Loading overlay
        self.loading_overlay = None
        
        # System tray manager
        self.tray_manager = None
        
        # Initialize UI immediately (instant window)
        self.init_ui_shell()
        
        # Show window immediately
        self.show()
        
        # Process events to ensure window is drawn
        QApplication.processEvents()
        
        # Load rest of UI asynchronously
        QTimer.singleShot(0, self._init_ui_async)
    
    def _update_tab_names(self):
        """Update tab names when language changes."""
        print("[DEBUG] _update_tab_names called")
        if not self.tab_widget:
            print("[DEBUG] tab_widget not available yet")
            return
        
        tab_names = [
            tr("general"),
            tr("capture"),
            tr("ocr_engines"),
            tr("translation"),
            tr("overlay"),
            tr("smart_dictionary"),
            tr("pipeline"),
            tr("storage"),
            tr("advanced")
        ]
        
        for i, tab_name in enumerate(tab_names):
            self.tab_widget.setTabText(i, tab_name)
            print(f"[DEBUG] Updated tab {i}: {tab_name}")
        
        # Also update window title
        self.setWindowTitle(tr("app_title"))
        print("[DEBUG] Tab names updated successfully")
    
    def init_ui_shell(self):
        """Initialize minimal UI shell for instant window display."""
        # Get window settings from config
        window_x = self.config_manager.get_setting('ui.window_x', 100)
        window_y = self.config_manager.get_setting('ui.window_y', 50)
        window_width = self.config_manager.get_setting('ui.window_width', 1600)
        window_height = self.config_manager.get_setting('ui.window_height', 1050)
        min_width = self.config_manager.get_setting('ui.window_min_width', 1300)
        min_height = self.config_manager.get_setting('ui.window_min_height', 850)
        
        self.setWindowTitle(tr("app_title"))
        self.setGeometry(window_x, window_y, window_width, window_height)
        self.setMinimumSize(min_width, min_height)
        
        print("\n[INFO] Application window created")
        print("[INFO] Loading user interface...")
        
        # Create minimal central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create loading overlay
        self.loading_overlay = LoadingOverlay(central_widget)
        self.loading_overlay.set_status("Initializing application...", 10)
        self.loading_overlay.show()
    
    def _init_ui_async(self):
        """Load the rest of the UI asynchronously after window is shown."""
        # Update loading status
        self.loading_overlay.set_status("Loading user interface...", 20)
        QApplication.processEvents()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the full UI (called after window is shown)."""
        # Update loading status
        self.loading_overlay.set_status("Creating sidebar...", 30)
        QApplication.processEvents()
        
        # Create central widget
        central_widget = QWidget()
        
        # Main horizontal layout (sidebar + content)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Update loading status
        self.loading_overlay.set_status("Creating settings tabs...", 50)
        QApplication.processEvents()
        
        # Create vertical layout for content + toolbar
        content_container = QWidget()
        content_container_layout = QVBoxLayout(content_container)
        content_container_layout.setContentsMargins(0, 0, 0, 0)
        content_container_layout.setSpacing(0)
        
        # Create content area
        content_area = self.create_content_area()
        content_container_layout.addWidget(content_area, 1)
        
        # Update loading status
        self.loading_overlay.set_status("Creating toolbar...", 70)
        QApplication.processEvents()
        
        # Create toolbar at bottom
        toolbar = self.create_toolbar()
        content_container_layout.addWidget(toolbar)
        
        main_layout.addWidget(content_container, 1)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Recreate loading overlay on new central widget
        self.loading_overlay = LoadingOverlay(central_widget)
        self.loading_overlay.set_status("Finalizing...", 80)
        self.loading_overlay.show()
        QApplication.processEvents()
        
        # Status bar
        status_bar = self.statusBar()
        status_bar.showMessage("● System Ready")
        status_bar.setStyleSheet("QStatusBar { font-size: 8pt; }")
        
        # Add pipeline stages label to status bar (left side)
        from PyQt6.QtWidgets import QLabel
        self.pipeline_stages_label = QLabel("")
        self.pipeline_stages_label.setStyleSheet("QLabel { font-size: 7pt; color: #666666; padding-left: 10px; }")
        status_bar.addWidget(self.pipeline_stages_label)
        
        # Add version label to status bar (right side)
        version_label = QLabel(tr("version"))
        version_label.setStyleSheet("QLabel { font-size: 8pt; color: #95A5A6; padding-right: 10px; }")
        status_bar.addPermanentWidget(version_label)
        
        # Validate essential plugins before loading
        self.loading_overlay.set_status("Validating system plugins...", 80)
        QApplication.processEvents()
        print("[INFO] Validating essential plugins...")
        
        try:
            from app.utils.plugin_validator import validate_system_plugins
            from pathlib import Path
            
            app_root = Path(__file__).parent
            success, errors = validate_system_plugins(app_root)
            
            if not success:
                print("[ERROR] Essential plugin validation failed:")
                for error in errors:
                    print(f"  - {error}")
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "Essential Plugins Missing",
                    "System validation failed:\n\n" + "\n".join(errors) + "\n\n"
                    "The application cannot start without essential plugins.\n"
                    "Please ensure at least one OCR engine is installed."
                )
                # Don't exit - let user see the error and try to fix it
            else:
                print("[INFO] ✓ All essential plugins validated")
        except Exception as e:
            print(f"[WARNING] Plugin validation failed: {e}")
            # Continue anyway - validation is not critical for startup
        
        # Set default region and initialize pipeline
        self.loading_overlay.set_status("Setting up capture region...", 85)
        QApplication.processEvents()
        self._set_default_primary_monitor_region()
        
        # Initialize pipeline
        # Load StartupPipeline at startup (initializes OCR/Translation/Capture components)
        # RuntimePipeline will be created when user clicks "Start Translation"
        print("[INFO] Loading StartupPipeline (initializing components)...")
        self.loading_overlay.set_status("[1/6] Discovering plugins...", 85)
        QApplication.processEvents()
        self.init_pipeline()
        
        # Initialize system tray
        self.loading_overlay.set_status("Setting up system tray...", 95)
        QApplication.processEvents()
        self._init_system_tray()
        
        # Sync Windows startup with config
        self._sync_windows_startup()
        
        # Start metrics update timer for sidebar
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._update_sidebar_metrics)
        self.metrics_timer.start(1000)  # Update every 1 second
        
        # Hide loading overlay after a short delay
        QTimer.singleShot(500, lambda: self._finish_loading())
    
    def _init_system_tray(self):
        """Initialize system tray icon."""
        try:
            from ui.system_tray import SystemTrayManager
            
            self.tray_manager = SystemTrayManager(self, self.config_manager)
            
            # Connect signals
            self.tray_manager.showRequested.connect(self._on_tray_show_requested)
            self.tray_manager.quitRequested.connect(self.quit_application)
            
            self.logger.log_info("SYSTEM", "tray_init", "System tray initialized")
            
        except Exception as e:
            self.logger.log_error("SYSTEM", "tray_init_failed", f"Failed to initialize system tray: {e}")
            print(f"[WARNING] System tray initialization failed: {e}")
    
    def _sync_windows_startup(self):
        """Synchronize Windows startup registry with configuration."""
        try:
            from app.utils.windows_startup import sync_startup_with_config
            
            if sync_startup_with_config(self.config_manager):
                self.logger.log_info("SYSTEM", "startup_sync", "Windows startup synchronized with config")
            
        except Exception as e:
            self.logger.log_warning("SYSTEM", "startup_sync_failed", f"Failed to sync Windows startup: {e}")
            print(f"[WARNING] Windows startup sync failed: {e}")
    
    def _on_tray_show_requested(self):
        """Handle show window request from system tray."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.logger.log_info("USER_ACTION", "window_restored", "Window restored from system tray")
    
    def _finish_loading(self):
        """Finish loading and hide the overlay."""
        if self.loading_overlay:
            self.loading_overlay.set_status("Ready!", 100)
            QApplication.processEvents()
            QTimer.singleShot(300, lambda: self.loading_overlay.hide())
    
    def _update_sidebar_metrics(self):
        """Update sidebar metrics with real-time system data."""
        try:
            import psutil
            
            # Get CPU usage
            cpu = psutil.cpu_percent(interval=0.1)
            
            # Get memory info
            memory_info = psutil.virtual_memory()
            memory_gb = memory_info.used / (1024 ** 3)  # Convert to GB
            
            # Try to get GPU usage (if available)
            gpu = 0.0
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0].load * 100  # Convert to percentage
            except:
                # GPU monitoring not available
                pass
            
            # FPS - would come from actual capture system if running
            fps = 0.0
            if self.pipeline_running and self.pipeline:
                # Try to get FPS from pipeline metrics if available
                try:
                    if hasattr(self.pipeline, 'get_metrics'):
                        metrics = self.pipeline.get_metrics()
                        if hasattr(metrics, 'average_fps'):
                            fps = metrics.average_fps
                except:
                    pass
            
            # Update sidebar
            if hasattr(self, 'sidebar'):
                self.sidebar.update_metrics(fps=fps, cpu=cpu, gpu=gpu, memory_gb=memory_gb)
                
        except Exception as e:
            # Silently fail - not critical
            pass
    
    def create_sidebar(self):
        """Create left sidebar with system status."""
        # Create sidebar widget
        self.sidebar = SidebarWidget(self.config_manager, self)
        
        # Connect signals
        self.sidebar.logsClicked.connect(self.show_log_viewer)
        self.sidebar.quickOcrSwitchClicked.connect(self.show_quick_ocr_switch)
        self.sidebar.fullTestClicked.connect(self.show_full_test_dialog)
        self.sidebar.languagePackClicked.connect(self.show_language_pack_manager)  # NEW
        self.sidebar.sourceLanguageChanged.connect(self._on_sidebar_source_changed)
        self.sidebar.targetLanguageChanged.connect(self._on_sidebar_target_changed)
        self.sidebar.presetLoaded.connect(self._on_preset_loaded)  # NEW: Preset system
        
        return self.sidebar
    
    def show_log_viewer(self):
        """Show the enhanced log viewer dialog."""
        from ui.log_viewer_pyqt6 import LogViewerDialog
        
        # Create and show log viewer (modeless - allows interaction with main window)
        # Keep reference to prevent garbage collection
        if not hasattr(self, 'log_viewer_window') or not self.log_viewer_window:
            self.log_viewer_window = LogViewerDialog(logs_dir="logs", parent=self)
        
        self.log_viewer_window.show()
        self.log_viewer_window.raise_()
        self.log_viewer_window.activateWindow()
    
    def show_full_test_dialog(self):
        """Show the comprehensive full test dialog."""
        from ui.dialogs.full_pipeline_test_dialog import show_full_pipeline_test
        
        # Show test dialog
        show_full_pipeline_test(
            parent=self,
            pipeline=self.pipeline,
            config_manager=self.config_manager
        )
    
    def create_content_area(self):
        """Create main content area with settings tabs (lazy loaded)."""
        content = QWidget()
        content.setObjectName("contentArea")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create tab widget for settings
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setUsesScrollButtons(True)
        
        # Enable expanding to fill available space
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Add placeholder tabs (empty widgets) - tabs will load on demand
        # Tab order: General, Capture, OCR Engines, Translation, Overlay, Smart Dictionary, Pipeline, Storage, Advanced
        tab_names = [
            tr("general"),
            tr("capture"),
            tr("ocr_engines"),
            tr("translation"),
            tr("overlay"),
            tr("smart_dictionary"),  # NEW TAB!
            tr("pipeline"),
            tr("storage"),
            tr("advanced")
        ]
        
        for tab_name in tab_names:
            placeholder = QWidget()
            placeholder_layout = QVBoxLayout(placeholder)
            placeholder_layout.setContentsMargins(0, 0, 0, 0)
            self.tab_widget.addTab(placeholder, tab_name)
        
        # Load first tab (General) immediately so user sees content
        self._load_tab_on_demand(0)
        
        # Connect signal to load tabs when user switches to them
        self.tab_widget.currentChanged.connect(self._load_tab_on_demand)
        
        # Connect to language change signal to update tab names
        self.language_manager.language_changed.connect(self._update_tab_names)
        
        layout.addWidget(self.tab_widget, 1)  # Stretch factor of 1 to expand
        
        return content
    
    def _load_tab_on_demand(self, index):
        """
        Load a tab's content on demand when user switches to it.
        
        Args:
            index: Tab index (0-7)
        """
        # Check if tab is already loaded
        if index in self.loaded_tabs:
            return
        
        # Create the actual tab content based on index
        tab_widget = None
        
        if index == 0:  # General
            tab_widget = self.create_general_tab()
        elif index == 1:  # Capture
            tab_widget = self.create_capture_tab()
        elif index == 2:  # OCR Engines
            tab_widget = self.create_ocr_tab()
        elif index == 3:  # Translation
            tab_widget = self.create_translation_tab()
        elif index == 4:  # Overlay
            tab_widget = self.create_overlay_tab()
        elif index == 5:  # Smart Dictionary (NEW!)
            tab_widget = self.create_smart_dictionary_tab()
        elif index == 6:  # Pipeline
            tab_widget = self.create_pipeline_tab()
        elif index == 7:  # Storage
            tab_widget = self.create_storage_tab()
        elif index == 8:  # Advanced
            tab_widget = self.create_advanced_tab()
        
        if tab_widget:
            # Replace placeholder with actual tab content
            placeholder = self.tab_widget.widget(index)
            placeholder_layout = placeholder.layout()
            placeholder_layout.addWidget(tab_widget)
            
            # Mark as loaded
            self.loaded_tabs[index] = tab_widget
        else:
            self.logger.log_warning("UI", "tab_loading", f"Failed to load tab at index {index}", {"tab_index": index})
    
    def create_general_tab(self):
        """Create General settings tab using the modular PyQt6 implementation."""
        # Create the modular general settings tab
        self.general_tab = GeneralSettingsTab(config_manager=self.config_manager, parent=self)
        
        # Load configuration
        self.general_tab.load_config()
        
        # Connect change signal
        self.general_tab.settingChanged.connect(self.on_settings_changed)
        
        # Also connect language changes to sync sidebar
        self.general_tab.source_lang_combo.currentTextChanged.connect(self._sync_sidebar_languages)
        self.general_tab.target_lang_combo.currentTextChanged.connect(self._sync_sidebar_languages)
        
        # Initial sync of sidebar with loaded config
        self._sync_sidebar_languages()
        
        return self.general_tab
    
    def on_settings_changed(self):
        """Called when any setting changes - checks if there are actual changes."""
        # Check if any loaded tab has actual changes
        has_changes = False
        
        # Check each loaded tab for actual changes
        if hasattr(self, 'capture_tab') and self.capture_tab:
            if hasattr(self.capture_tab, '_get_current_state') and hasattr(self.capture_tab, '_original_state'):
                current = self.capture_tab._get_current_state()
                original = self.capture_tab._original_state
                if current != original:
                    has_changes = True
                    print(f"[DEBUG] Capture tab has changes: {current} != {original}")
                else:
                    print(f"[DEBUG] Capture tab NO changes: {current} == {original}")
        
        if hasattr(self, 'general_tab') and self.general_tab:
            if hasattr(self.general_tab, '_get_current_state') and hasattr(self.general_tab, '_original_state'):
                if self.general_tab._get_current_state() != self.general_tab._original_state:
                    has_changes = True
        
        if hasattr(self, 'ocr_tab') and self.ocr_tab:
            if hasattr(self.ocr_tab, '_get_current_state') and hasattr(self.ocr_tab, '_original_state'):
                if self.ocr_tab._get_current_state() != self.ocr_tab._original_state:
                    has_changes = True
        
        if hasattr(self, 'translation_tab') and self.translation_tab:
            if hasattr(self.translation_tab, '_get_current_state') and hasattr(self.translation_tab, '_original_state'):
                if self.translation_tab._get_current_state() != self.translation_tab._original_state:
                    has_changes = True
        
        if hasattr(self, 'overlay_tab') and self.overlay_tab:
            if hasattr(self.overlay_tab, '_get_current_state') and hasattr(self.overlay_tab, '_original_state'):
                if self.overlay_tab._get_current_state() != self.overlay_tab._original_state:
                    has_changes = True
        
        if hasattr(self, 'smart_dictionary_tab') and self.smart_dictionary_tab:
            if hasattr(self.smart_dictionary_tab, '_get_current_state') and hasattr(self.smart_dictionary_tab, '_original_state'):
                if self.smart_dictionary_tab._get_current_state() != self.smart_dictionary_tab._original_state:
                    has_changes = True
        
        if hasattr(self, 'advanced_tab') and self.advanced_tab:
            if hasattr(self.advanced_tab, '_get_current_state') and hasattr(self.advanced_tab, '_original_state'):
                if self.advanced_tab._get_current_state() != self.advanced_tab._original_state:
                    has_changes = True
        
        if hasattr(self, 'storage_tab') and self.storage_tab:
            if hasattr(self.storage_tab, '_get_current_state') and hasattr(self.storage_tab, '_original_state'):
                if self.storage_tab._get_current_state() != self.storage_tab._original_state:
                    has_changes = True
        
        # Update state
        if has_changes and not self.has_unsaved_changes:
            # Only log the first time changes are detected
            self.logger.log_info("USER_ACTION", "settings_changed", "Settings changed - Save button enabled")
        
        self.has_unsaved_changes = has_changes
        
        if self.save_btn:
            self.save_btn.setEnabled(has_changes)
            if has_changes:
                self.save_btn.setToolTip("Save all settings")
            else:
                self.save_btn.setToolTip("No unsaved changes")
    
    def _on_sidebar_source_changed(self, language_name):
        """Handle sidebar source language change."""
        # Update the General tab's source language combo (if loaded)
        if hasattr(self, 'general_tab') and self.general_tab:
            index = self.general_tab.source_lang_combo.findText(language_name)
            if index >= 0:
                self.general_tab.source_lang_combo.setCurrentIndex(index)
                self.logger.log_info("CONFIGURATION", "language_change", "OCR source language changed", {"language": language_name})
    
    def _on_sidebar_target_changed(self, language_name):
        """Handle sidebar target language change."""
        # Update the General tab's target language combo (if loaded)
        if hasattr(self, 'general_tab') and self.general_tab:
            index = self.general_tab.target_lang_combo.findText(language_name)
            if index >= 0:
                self.general_tab.target_lang_combo.setCurrentIndex(index)
                self.logger.log_info("CONFIGURATION", "language_change", "Translation target language changed", {"language": language_name})
    
    def _sync_sidebar_languages(self):
        """Sync sidebar language dropdowns with General tab settings."""
        if hasattr(self, 'general_tab') and self.general_tab and hasattr(self, 'sidebar'):
            # Sync source language
            source_lang = self.general_tab.source_lang_combo.currentText()
            self.sidebar.set_source_language(source_lang)
            
            # Sync target language
            target_lang = self.general_tab.target_lang_combo.currentText()
            self.sidebar.set_target_language(target_lang)
    
    def _on_preset_loaded(self, preset_name):
        """Handle preset loaded signal from sidebar."""
        self.logger.log_info("CONFIGURATION", "preset_loaded", f"Preset '{preset_name}' loaded")
        # Reload all settings will be called by sidebar after user confirmation
    
    def reload_all_settings(self):
        """Reload all settings from config into UI (used after preset load)."""
        try:
            # Reload all LOADED tabs
            if hasattr(self, 'general_tab') and self.general_tab:
                self.general_tab.load_config()
            
            if hasattr(self, 'capture_tab') and self.capture_tab:
                self.capture_tab.load_config()
            
            if hasattr(self, 'ocr_tab') and self.ocr_tab:
                self.ocr_tab.load_config()
            
            if hasattr(self, 'translation_tab') and self.translation_tab:
                self.translation_tab.load_config()
            
            if hasattr(self, 'overlay_tab') and self.overlay_tab:
                self.overlay_tab.load_config()
                # Reload overlay configuration
                if hasattr(self, 'overlay_system') and self.overlay_system:
                    self.overlay_system.reload_config()
            
            if hasattr(self, 'smart_dictionary_tab') and self.smart_dictionary_tab:
                self.smart_dictionary_tab.load_config()
            
            if hasattr(self, 'pipeline_tab') and self.pipeline_tab:
                self.pipeline_tab.load_config()
            
            if hasattr(self, 'storage_tab') and self.storage_tab:
                self.storage_tab.load_config()
            
            if hasattr(self, 'advanced_tab') and self.advanced_tab:
                self.advanced_tab.load_config()
            
            # Update sidebar displays
            if hasattr(self, 'sidebar'):
                self._sync_sidebar_languages()
                self.update_sidebar_ocr_display()
            
            # Reinitialize pipeline with new settings if needed
            if self.pipeline:
                # Update multi-region config
                regions_data = self.config_manager.get_setting('capture.regions', [])
                active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
                
                if regions_data and active_ids:
                    from app.models import MultiRegionConfig
                    config = MultiRegionConfig.from_dict({
                        'regions': regions_data,
                        'active_region_ids': active_ids
                    })
                    self.pipeline.set_multi_region_config(config)
            
            # Clear unsaved changes flag
            self.has_unsaved_changes = False
            if self.save_btn:
                self.save_btn.setEnabled(False)
            
            self.logger.log_info("CONFIGURATION", "settings_reloaded", "All settings reloaded from preset")
            
        except Exception as e:
            self.logger.log_error("CONFIGURATION", "reload_failed", "Failed to reload settings", {"error": str(e)})
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Reload Failed",
                f"Failed to reload settings:\n\n{str(e)}"
            )
    
    def save_all_settings(self):
        """Save all settings from all tabs (only loaded tabs)."""
        try:
            # Validate all LOADED tabs before saving (skip pipeline tab - it's read-only)
            # Note: Only loaded tabs need validation since unloaded tabs have no changes
            if hasattr(self, 'general_tab') and self.general_tab and not self.general_tab.validate():
                return  # Validation failed, don't save
            
            if hasattr(self, 'capture_tab') and self.capture_tab and not self.capture_tab.validate():
                return  # Validation failed, don't save
            
            if hasattr(self, 'ocr_tab') and self.ocr_tab and not self.ocr_tab.validate():
                return  # Validation failed, don't save
            
            if hasattr(self, 'translation_tab') and self.translation_tab and not self.translation_tab.validate():
                return  # Validation failed, don't save
            
            if hasattr(self, 'overlay_tab') and self.overlay_tab and not self.overlay_tab.validate():
                return  # Validation failed, don't save
            
            if hasattr(self, 'storage_tab') and self.storage_tab and not self.storage_tab.validate():
                return  # Validation failed, don't save
            
            if hasattr(self, 'advanced_tab') and self.advanced_tab and not self.advanced_tab.validate():
                return  # Validation failed, don't save
            
            # All validations passed, proceed with saving
            # Save general tab settings (if loaded)
            if hasattr(self, 'general_tab') and self.general_tab:
                self.general_tab.save_config()
            
            # Save capture tab settings (if loaded)
            if hasattr(self, 'capture_tab') and self.capture_tab:
                self.capture_tab.save_config()
            
            # Save OCR tab settings (if loaded)
            if hasattr(self, 'ocr_tab') and self.ocr_tab:
                self.ocr_tab.save_config()
            
            # Save translation tab settings (if loaded)
            if hasattr(self, 'translation_tab') and self.translation_tab:
                self.translation_tab.save_config()
            
            # Save overlay tab settings (if loaded)
            if hasattr(self, 'overlay_tab') and self.overlay_tab:
                self.overlay_tab.save_config()
                # Reload overlay configuration to apply changes
                if hasattr(self, 'overlay_system') and self.overlay_system:
                    self.overlay_system.reload_config()
            
            # Save smart dictionary tab settings (if loaded)
            if hasattr(self, 'smart_dictionary_tab') and self.smart_dictionary_tab:
                self.smart_dictionary_tab.save_config()
            
            # Note: Pipeline tab is read-only dashboard - no save needed
            
            # Save storage tab settings (if loaded)
            if hasattr(self, 'storage_tab') and self.storage_tab:
                self.storage_tab.save_config()
            
            # Save advanced tab settings (if loaded)
            if hasattr(self, 'advanced_tab') and self.advanced_tab:
                self.advanced_tab.save_config()
            
            # Mark as saved
            self.has_unsaved_changes = False
            if self.save_btn:
                self.save_btn.setEnabled(False)
                self.save_btn.setToolTip("No unsaved changes")
            
            self.logger.log_info("CONFIGURATION", "settings_saved", "All settings saved successfully")
            
            # Show success message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Settings Saved",
                "All settings have been saved successfully!"
            )
        except Exception as e:
            self.logger.log_error("CONFIGURATION", "settings_save_failed", "Failed to save settings", {"error": str(e)})
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save settings:\n\n{str(e)}"
            )
    
    def export_settings(self):
        """Export settings to a JSON file."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            import json
            from datetime import datetime
            
            # Get file path from user
            default_name = f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Settings",
                default_name,
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Get current configuration
            config_data = self.config_manager.config
            
            # Add metadata
            version = self.config_manager.get_setting('ui.version', '0.1.1')
            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'version': version,
                    'application': 'OptikR'
                },
                'settings': config_data
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.log_info("CONFIGURATION", "settings_exported", "Settings exported", {"file_path": file_path})
            QMessageBox.information(
                self,
                "Export Successful",
                f"Settings have been exported to:\n\n{file_path}"
            )
            
        except Exception as e:
            self.logger.log_error("CONFIGURATION", "export_failed", "Failed to export settings", {"error": str(e)})
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export settings:\n\n{str(e)}"
            )
    
    def import_settings(self):
        """Import settings from a JSON file."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            import json
            
            # Show warning
            reply = QMessageBox.warning(
                self,
                "Import Settings",
                "Importing settings will overwrite your current configuration.\n\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Get file path from user
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Settings",
                "",
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Extract settings
            settings = import_data['settings']
            metadata = import_data.get('metadata', {})
            self.logger.log_info("CONFIGURATION", "settings_importing", "Importing settings", {"export_date": metadata.get('export_date', 'unknown date')})
            
            # Update config manager
            for key, value in settings.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        self.config_manager.set_setting(f"{key}.{subkey}", subvalue)
                else:
                    self.config_manager.set_setting(key, value)
            
            # Save configuration
            self.config_manager.save_config()
            
            # Reload all LOADED tabs (lazy loading: only reload what's been loaded)
            if hasattr(self, 'general_tab') and self.general_tab:
                self.general_tab.load_config()
            if hasattr(self, 'capture_tab') and self.capture_tab:
                self.capture_tab.load_config()
            if hasattr(self, 'ocr_tab') and self.ocr_tab:
                self.ocr_tab.load_config()
            if hasattr(self, 'translation_tab') and self.translation_tab:
                self.translation_tab.load_config()
            if hasattr(self, 'overlay_tab') and self.overlay_tab:
                self.overlay_tab.load_config()
            if hasattr(self, 'smart_dictionary_tab') and self.smart_dictionary_tab:
                self.smart_dictionary_tab.load_config()
            if hasattr(self, 'pipeline_tab') and self.pipeline_tab:
                self.pipeline_tab.load_config()  # Refresh dashboard display
            if hasattr(self, 'storage_tab') and self.storage_tab:
                self.storage_tab.load_config()
            if hasattr(self, 'advanced_tab') and self.advanced_tab:
                self.advanced_tab.load_config()
            
            self.logger.log_info("CONFIGURATION", "settings_imported", "Settings imported successfully", {"file_path": file_path})
            QMessageBox.information(
                self,
                "Import Successful",
                f"Settings have been imported from:\n\n{file_path}\n\n"
                "The application will now reload with the new settings."
            )
            
        except Exception as e:
            self.logger.log_error("CONFIGURATION", "import_failed", "Failed to import settings", {"error": str(e)})
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import settings:\n\n{str(e)}"
            )
    
    def create_capture_tab(self):
        """Create Capture settings tab using the modular PyQt6 implementation."""
        # Create the modular capture settings tab
        self.capture_tab = CaptureSettingsTab(config_manager=self.config_manager, parent=self)
        
        # Load configuration
        self.capture_tab.load_config()
        
        # Connect change signal
        self.capture_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.capture_tab
    
    def create_ocr_tab(self):
        """Create OCR Engines settings tab using the modular PyQt6 implementation."""
        # Create the modular OCR settings tab
        self.ocr_tab = OCRSettingsTab(config_manager=self.config_manager, parent=self)
        
        # Set pipeline reference for dynamic engine discovery
        self.ocr_tab.pipeline = self.pipeline
        
        # Load configuration
        self.ocr_tab.load_config()
        
        # Connect change signal
        self.ocr_tab.settingChanged.connect(self.on_settings_changed)
        
        # Connect engine change to update sidebar
        self.ocr_tab.settingChanged.connect(self.update_sidebar_ocr_display)
        
        # Update engine statuses if pipeline is ready
        if self.pipeline:
            self.ocr_tab._update_engine_statuses()
            # Refresh engine list to show discovered engines
            self.ocr_tab.refresh_engine_list()
        
        return self.ocr_tab
    
    def create_translation_tab(self):
        """Create Translation settings tab using the modular PyQt6 implementation."""
        # Create the modular translation settings tab
        self.translation_tab = TranslationSettingsTab(
            config_manager=self.config_manager,
            pipeline=self.pipeline,  # Pass pipeline for dictionary management
            parent=self
        )
        
        # Load configuration
        self.translation_tab.load_config()
        
        # Connect change signal
        self.translation_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.translation_tab
    
    def create_overlay_tab(self):
        """Create Overlay settings tab using the modular PyQt6 implementation."""
        # Create the modular overlay settings tab
        self.overlay_tab = OverlaySettingsTab(config_manager=self.config_manager, parent=self)
        
        # Load configuration
        self.overlay_tab.load_config()
        
        # Connect change signal
        self.overlay_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.overlay_tab
    
    def create_smart_dictionary_tab(self):
        """Create Smart Dictionary settings tab using the modular PyQt6 implementation."""
        # Create the modular smart dictionary settings tab
        self.smart_dictionary_tab = SmartDictionaryTab(
            config_manager=self.config_manager,
            pipeline=self.pipeline if hasattr(self, 'pipeline') else None,
            parent=self
        )
        
        # Load configuration
        self.smart_dictionary_tab.load_config()
        
        # Connect change signal
        self.smart_dictionary_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.smart_dictionary_tab
    
    def show_performance_monitor(self):
        """Show the Performance Monitor window."""
        from ui.performance_monitor_pyqt6 import PerformanceMonitorWindow
        
        # Create and show performance monitor window
        if not hasattr(self, 'perf_monitor_window') or not self.perf_monitor_window:
            self.perf_monitor_window = PerformanceMonitorWindow(parent=self, config_manager=self.config_manager)
        
        self.perf_monitor_window.show()
        self.perf_monitor_window.raise_()
        self.perf_monitor_window.activateWindow()
    
    def show_region_overlay(self):
        """Show visual overlay of both capture and translation regions on screen."""
        from ui.region_visualizer_pyqt6 import RegionVisualizer
        
        # Create visualizer (keep reference to prevent garbage collection)
        if not hasattr(self, 'region_visualizer'):
            self.region_visualizer = RegionVisualizer(self.config_manager)
        
        # Hide any existing overlays first
        self.region_visualizer.hide_all()
        
        # Show all regions (red for OCR capture, blue for translation display, green for boundaries)
        capture_overlays, translation_overlays = self.region_visualizer.show_both_regions()
        
        if capture_overlays or translation_overlays:
            self.logger.log_info("UI", "region_visualizer", "Showing region visualizations", 
                               {"capture_count": len(capture_overlays), 
                                "translation_count": len(translation_overlays)})
    
    def show_help(self):
        """Show the Help dialog."""
        show_help_dialog(self.config_manager, self)
    
    def show_language_pack_manager(self):
        """Show the Language Pack Manager dialog."""
        from ui.dialogs.language_pack_manager import show_language_pack_manager
        show_language_pack_manager(self)
    
    def _set_default_primary_monitor_region(self):
        """Load saved capture region or set default to primary monitor full screen."""
        try:
            from PyQt6.QtWidgets import QApplication
            from app.models import MultiRegionConfig
            
            # First, try to load saved multi-region config
            regions_data = self.config_manager.get_setting('capture.regions', [])
            active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
            
            if regions_data and active_ids:
                # Load saved multi-region config
                config = MultiRegionConfig.from_dict({
                    'regions': regions_data,
                    'active_region_ids': active_ids
                })
                
                # Use first enabled region
                enabled_regions = config.get_enabled_regions()
                if enabled_regions:
                    first_region = enabled_regions[0]
                    self.capture_region = {
                        'x': first_region.rectangle.x,
                        'y': first_region.rectangle.y,
                        'width': first_region.rectangle.width,
                        'height': first_region.rectangle.height,
                        'monitor_id': first_region.monitor_id
                    }
                    
                    self.logger.log_info("CAPTURE", "saved_region_loaded", "Loaded saved capture region", 
                                        {"region": self.capture_region})
                    return  # Successfully loaded saved region
            
            # No saved region, set default to full primary monitor
            app = QApplication.instance()
            primary_screen = app.primaryScreen()
            
            if primary_screen:
                geometry = primary_screen.geometry()
                
                # Set capture region to full primary monitor
                self.capture_region = {
                    'x': geometry.x(),
                    'y': geometry.y(),
                    'width': geometry.width(),
                    'height': geometry.height(),
                    'monitor_id': 0  # Primary monitor
                }
                
                self.logger.log_info("CAPTURE", "default_region_set", "Default capture region set to primary monitor", 
                                    {"width": geometry.width(), "height": geometry.height(), "x": geometry.x(), "y": geometry.y()})
            else:
                self.logger.log_warning("CAPTURE", "monitor_detection", "Could not detect primary monitor, using fallback defaults")
                # Fallback to common resolution
                self.capture_region = {
                    'x': 0,
                    'y': 0,
                    'width': 1920,
                    'height': 1080,
                    'monitor_id': 0
                }
        except Exception as e:
            self.logger.log_error("CAPTURE", "region_setup_failed", "Failed to set default primary monitor region", {"error": str(e)})
            # Fallback to common resolution
            self.capture_region = {
                'x': 0,
                'y': 0,
                'width': 1920,
                'height': 1080,
                'monitor_id': 0
            }
    
    def _is_fullscreen_capture(self):
        """
        Check if the current capture region is fullscreen or near-fullscreen.
        
        Returns:
            bool: True if capturing fullscreen, False otherwise
        """
        if not self.capture_region:
            return False
        
        try:
            from PyQt6.QtWidgets import QApplication
            
            # Get the screen that contains the capture region
            app = QApplication.instance()
            screens = app.screens()
            
            capture_width = self.capture_region.get('width', 0)
            capture_height = self.capture_region.get('height', 0)
            
            # Check against all screens
            for screen in screens:
                geometry = screen.geometry()
                screen_width = geometry.width()
                screen_height = geometry.height()
                
                # Consider it fullscreen if capture area is >= 90% of screen area
                capture_area = capture_width * capture_height
                screen_area = screen_width * screen_height
                
                if capture_area >= (screen_area * 0.9):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.log_warning("CAPTURE", "fullscreen_check_failed", f"Failed to check fullscreen: {e}")
            return False
    
    def show_capture_region_selector(self):
        """Show the Capture Region Selector dialog."""
        # ALWAYS use multi-region dialog (new UI)
        # The old single-region dialog is deprecated and causes issues
        self._show_multi_region_selector()
    

    def _show_multi_region_selector(self):
        """Show multi-region selector dialog."""
        from ui.multi_region_selector_dialog import MultiRegionSelectorDialog
        from app.models import MultiRegionConfig
        
        # Load existing multi-region config
        try:
            regions_data = self.config_manager.get_setting('capture.regions', [])
            active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
            
            config = MultiRegionConfig.from_dict({
                'regions': regions_data,
                'active_region_ids': active_ids
            })
        except Exception as e:
            self.logger.log_warning("CAPTURE", "config_load_failed", "Failed to load multi-region config", {"error": str(e)})
            config = MultiRegionConfig()
        
        # Create and show dialog (non-modal)
        if not hasattr(self, 'multi_region_dialog') or not self.multi_region_dialog:
            self.multi_region_dialog = MultiRegionSelectorDialog(config, parent=self, config_manager=self.config_manager)
            # Connect to handle configuration changes
            self.multi_region_dialog.configurationChanged.connect(self._on_multi_region_config_changed)
        
        self.multi_region_dialog.show()
        self.multi_region_dialog.raise_()
        self.multi_region_dialog.activateWindow()
    
    def _on_multi_region_config_changed(self, result):
        """Handle multi-region configuration changes."""
        if result:
            # Save configuration
            config_dict = result.to_dict()
            self.config_manager.set_setting('capture.regions', config_dict['regions'])
            self.config_manager.set_setting('capture.active_region_ids', config_dict['active_region_ids'])
            
            # Update pipeline if it exists
            if self.pipeline:
                self.pipeline.set_multi_region_config(result)
            
            # Update self.capture_region with the first enabled region
            # This ensures the pipeline uses the correct coordinates when starting
            enabled_regions = result.get_enabled_regions()
            if enabled_regions:
                first_region = enabled_regions[0]
                self.capture_region = {
                    'x': first_region.rectangle.x,
                    'y': first_region.rectangle.y,
                    'width': first_region.rectangle.width,
                    'height': first_region.rectangle.height,
                    'monitor_id': first_region.monitor_id
                }
                
                self.logger.log_info("CAPTURE", "primary_region_updated", 
                                   f"Primary capture region updated from multi-region config",
                                   {"region": self.capture_region})
            
            enabled_count = len(result.get_enabled_regions())
            self.logger.log_info("CAPTURE", "multi_region_configured", 
                               f"Multi-region configuration saved: {enabled_count} active regions",
                               {"total": len(result.regions), "enabled": enabled_count})
            
            # Mark as changed
            self.on_settings_changed()
    
    def create_pipeline_tab(self):
        """Create Pipeline Management tab with advanced monitoring and control."""
        # Create the new modular pipeline management tab
        self.pipeline_tab = PipelineManagementTab(
            config_manager=self.config_manager,
            pipeline=self.pipeline,  # May be None if pipeline still loading
            parent=self
        )
        
        # If pipeline is already loaded, set it now
        if self.pipeline:
            self.pipeline_tab.set_pipeline(self.pipeline)
        
        # Load configuration
        self.pipeline_tab.load_config()
        
        # Connect settings changed signal
        self.pipeline_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.pipeline_tab
    
    def create_storage_tab(self):
        """Create Storage settings tab using the modular PyQt6 implementation."""
        # Create the modular storage settings tab
        self.storage_tab = StorageSettingsTab(
            config_manager=self.config_manager,
            pipeline=self.pipeline,  # Pass pipeline for dictionary management
            parent=self
        )
        
        # Load configuration
        self.storage_tab.load_config()
        
        # Connect change signal
        self.storage_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.storage_tab
    
    def create_advanced_tab(self):
        """Create Advanced settings tab using the modular PyQt6 implementation."""
        # Create the modular advanced settings tab
        self.advanced_tab = AdvancedSettingsTab(config_manager=self.config_manager, parent=self)
        
        # Load configuration
        self.advanced_tab.load_config()
        
        # Connect change signal
        self.advanced_tab.settingChanged.connect(self.on_settings_changed)
        
        return self.advanced_tab
    
    def create_toolbar(self):
        """Create bottom toolbar with colored buttons."""
        # Create toolbar widget
        self.toolbar = MainToolbar(self)
        
        # Connect signals
        self.toolbar.startClicked.connect(self.toggle_translation)
        self.toolbar.captureRegionClicked.connect(self.show_capture_region_selector)
        self.toolbar.monitorClicked.connect(self.show_performance_monitor)
        self.toolbar.helpClicked.connect(self.show_help)
        self.toolbar.regionOverlayClicked.connect(self.show_region_overlay)
        self.toolbar.saveClicked.connect(self.save_all_settings)
        self.toolbar.importClicked.connect(self.import_settings)
        self.toolbar.exportClicked.connect(self.export_settings)
        self.toolbar.themeToggled.connect(self.toggle_theme)
        
        # Get references to buttons for later use
        self.save_btn = self.toolbar.get_save_button()
        self.start_btn = self.toolbar.get_start_button()
        
        # Load saved theme preference
        is_dark = self.config_manager.get_setting('ui.dark_mode', True)
        self.toolbar.set_theme(is_dark)
        
        return self.toolbar
    
    def init_pipeline(self):
        """Initialize the translation pipeline asynchronously."""
        # Update status to show loading
        self.update_system_status("Loading OCR engines...", "loading")
        
        print("[INFO] Starting pipeline initialization in MAIN thread...")
        print("[INFO] This process may take 20-30 seconds on first run")
        print("[INFO] Please wait and do not close the application...\n")
        
        # CRITICAL FIX: Load in MAIN thread to avoid Qt/OpenCV conflicts
        # Background thread causes crashes with screenshot capture and OCR loading
        print("[INFO] Loading in main thread to avoid Qt conflicts...")
        
        from PyQt6.QtCore import QObject, pyqtSignal
        
        class PipelineLoader(QObject):
            """Background thread for loading pipeline using standard Python threading."""
            finished = pyqtSignal(object)  # Emits pipeline object or None
            error = pyqtSignal(str)  # Emits error message
            progress = pyqtSignal(str)  # Emits progress messages
            
            def __init__(self, config_manager):
                super().__init__()
                self.config_manager = config_manager
                self._thread = None
                self._is_running = False
            
            def start(self):
                """Start the loading thread."""
                self._is_running = True
                self._thread = threading.Thread(target=self.run, daemon=True)
                self._thread.start()
            
            def isRunning(self):
                """Check if the loader thread is still running."""
                return self._is_running and self._thread and self._thread.is_alive()
            
            def terminate(self):
                """Terminate is not supported for Python threads - just mark as not running."""
                self._is_running = False
            
            def wait(self, timeout_ms=None):
                """Wait for thread to finish (compatibility with QThread)."""
                if self._thread and self._thread.is_alive():
                    timeout_sec = timeout_ms / 1000.0 if timeout_ms else None
                    self._thread.join(timeout=timeout_sec)
            
            def run(self):
                """Load pipeline in background."""
                try:
                    print("\n" + "="*60)
                    print("PIPELINE INITIALIZATION")
                    print("="*60)
                    
                    # Stage 1: Verify directory structure and import pipeline module
                    self.progress.emit("[1/6] Discovering OCR plugins...")
                    print("[1/6] Discovering OCR plugins...")
                    
                    # Verify critical directories exist
                    from pathlib import Path
                    script_dir = Path(__file__).parent
                    critical_dirs = [
                        script_dir / "app",
                        script_dir / "app" / "ocr",
                        script_dir / "app" / "workflow",
                        script_dir / "plugins",  # New plugin system
                    ]
                    
                    print("      → Verifying directory structure...")
                    missing_dirs = []
                    for dir_path in critical_dirs:
                        if not dir_path.exists():
                            missing_dirs.append(str(dir_path.relative_to(script_dir)))
                            print(f"      ✗ Missing: {dir_path.relative_to(script_dir)}")
                        else:
                            print(f"      ✓ Found: {dir_path.relative_to(script_dir)}")
                    
                    if missing_dirs:
                        raise RuntimeError(f"Missing critical directories: {', '.join(missing_dirs)}")
                    
                    print("      → Importing pipeline module...")
                    try:
                        from app.workflow.pipeline_integration import create_pipeline_integration
                        print("      ✓ Pipeline module loaded")
                    except ImportError as e:
                        print(f"      ✗ Failed to import pipeline module: {e}")
                        print("      → Check if all __init__.py files exist")
                        print("      → Verify src/workflow/pipeline_integration.py exists")
                        import traceback
                        traceback.print_exc()
                        raise
                    
                    # Stage 2: Load OCR plugins (new plugin system)
                    self.progress.emit("[2/6] Loading OCR plugins (this may take 20-30 seconds)...")
                    print("[2/6] Loading OCR plugins (this may take 20-30 seconds)...")
                    print("      → Scanning for available OCR plugins...")
                    
                    # Add diagnostic information
                    import sys
                    from pathlib import Path
                    print(f"      → Python: {sys.executable}")
                    print(f"      → Working dir: {Path.cwd()}")
                    print(f"      → Script dir: {Path(__file__).parent}")
                    
                    # Check for OCR plugin directories (NEW PLUGIN SYSTEM)
                    plugins_dir = Path(__file__).parent / "plugins" / "ocr"
                    if plugins_dir.exists():
                        plugin_dirs = [d.name for d in plugins_dir.iterdir() if d.is_dir() and not d.name.startswith('__')]
                        print(f"      → Found OCR plugins: {', '.join(plugin_dirs) if plugin_dirs else 'none'}")
                        
                        # Check for plugin.json files
                        for plugin_dir in plugin_dirs:
                            plugin_json = plugins_dir / plugin_dir / "plugin.json"
                            if plugin_json.exists():
                                print(f"      ✓ {plugin_dir}/plugin.json exists")
                            else:
                                print(f"      ✗ {plugin_dir}/plugin.json missing")
                    else:
                        print(f"      ✗ OCR plugins directory not found: {plugins_dir}")
                    
                    try:
                        # Try to import OCR components first to catch import errors early
                        print("      → Importing OCR layer...")
                        try:
                            from app.ocr.ocr_layer import OCRLayer
                            print("      ✓ OCR layer module imported")
                        except ImportError as e:
                            print(f"      ✗ Failed to import OCR layer: {e}")
                            raise ImportError(f"OCR layer import failed: {e}")
                        
                        print("      → Importing OCR plugin manager...")
                        try:
                            from app.ocr.ocr_plugin_manager import OCRPluginManager
                            print("      ✓ OCR plugin manager imported")
                        except ImportError as e:
                            print(f"      ✗ Failed to import plugin manager: {e}")
                            raise ImportError(f"Plugin manager import failed: {e}")
                        
                        print("      → Creating pipeline integration...")
                        print("      → Initializing PipelineIntegration class...")
                        
                        try:
                            # Import STARTUP pipeline (initializes components)
                            from app.workflow.startup_pipeline import StartupPipeline
                            print("      ✓ StartupPipeline class imported")
                            
                            print("      → Creating startup pipeline instance...")
                            integration = StartupPipeline(config_manager=self.config_manager)
                            print("      ✓ Integration instance created")
                            
                            print("      → Initializing pipeline components...")
                            print("         (This may take 20-30 seconds...)")
                            print("         → Step 1/5: Capture layer...")
                            import sys
                            sys.stdout.flush()  # Force output
                            
                            # Call initialize with progress tracking
                            original_logger_info = integration.logger.info
                            def tracked_info(msg):
                                # Print logger messages to console for visibility
                                if "capture" in msg.lower():
                                    print(f"         ✓ Capture layer ready")
                                    sys.stdout.flush()
                                    print(f"         → Step 2/5: Preprocessing layer...")
                                    sys.stdout.flush()
                                elif "preprocessing" in msg.lower():
                                    print(f"         ✓ Preprocessing layer ready")
                                    sys.stdout.flush()
                                    print(f"         → Step 3/5: OCR layer (slow step)...")
                                    sys.stdout.flush()
                                elif "ocr" in msg.lower() and "initializing" in msg.lower():
                                    print(f"         → OCR initialization starting...")
                                    sys.stdout.flush()
                                elif "ocr" in msg.lower() and "initialized" in msg.lower():
                                    print(f"         ✓ OCR layer ready")
                                    sys.stdout.flush()
                                    print(f"         → Step 4/5: Translation layer...")
                                    sys.stdout.flush()
                                elif "translation" in msg.lower():
                                    print(f"         ✓ Translation layer ready")
                                    sys.stdout.flush()
                                    print(f"         → Step 5/5: Overlay renderer...")
                                    sys.stdout.flush()
                                elif "overlay" in msg.lower():
                                    print(f"         ✓ Overlay renderer ready")
                                    sys.stdout.flush()
                                original_logger_info(msg)
                            
                            integration.logger.info = tracked_info
                            
                            print("         → Calling initialize_components()...")
                            sys.stdout.flush()
                            
                            try:
                                result = integration.initialize_components()
                                if not result:
                                    print("      ✗ initialize_components() returned False")
                                    raise RuntimeError("initialize_components() returned False - check component creation")
                            except Exception as init_error:
                                print(f"      ✗ Exception during component initialization: {type(init_error).__name__}")
                                print(f"      ✗ Error: {init_error}")
                                import traceback
                                print("\n      Component initialization traceback:")
                                traceback.print_exc()
                                raise
                            finally:
                                integration.logger.info = original_logger_info
                            
                            print("      ✓ Components initialized")
                            
                            pipeline = integration
                            
                        except ImportError as e:
                            print(f"      ✗ Import failed: {e}")
                            import traceback
                            traceback.print_exc()
                            raise
                        except AttributeError as e:
                            print(f"      ✗ Attribute error: {e}")
                            print("      → This usually means a required module or class is missing")
                            import traceback
                            traceback.print_exc()
                            raise
                        except Exception as e:
                            print(f"      ✗ Pipeline creation failed: {type(e).__name__}: {e}")
                            import traceback
                            print("\n      Detailed traceback:")
                            traceback.print_exc()
                            raise RuntimeError(f"Pipeline creation failed: {e}") from e
                        
                        if not pipeline:
                            raise RuntimeError("Pipeline creation returned None - check logs for details")
                        
                        print("      ✓ Pipeline created successfully")
                        
                        # Verify OCR layer exists
                        if not hasattr(pipeline, 'ocr_layer') or pipeline.ocr_layer is None:
                            print("      ⚠ Warning: Pipeline has no OCR layer")
                        else:
                            print("      ✓ OCR layer attached to pipeline")
                        
                        print("      ✓ OCR engines initialized")
                        
                    except ImportError as e:
                        print(f"      ✗ Missing OCR dependencies: {e}")
                        print("      → Possible causes:")
                        print("         • Missing __init__.py files")
                        print("         • Incorrect Python path")
                        print("         • Missing OCR engine packages")
                        print("      → Try: pip install easyocr pytesseract paddleocr")
                        import traceback
                        print("\n      Full traceback:")
                        traceback.print_exc()
                        raise
                    except RuntimeError as e:
                        print(f"      ✗ OCR initialization failed: {e}")
                        print("      → Check if OCR engine directories exist")
                        print("      → Verify plugin.json files are present")
                        import traceback
                        print("\n      Full traceback:")
                        traceback.print_exc()
                        raise
                    except MemoryError:
                        print("      ✗ Out of memory loading OCR models")
                        print("      → Try closing other applications")
                        print("      → Consider using a lighter OCR engine (tesseract)")
                        raise
                    except AttributeError as e:
                        print(f"      ✗ Attribute error: {e}")
                        print("      → This usually means a module is missing or incomplete")
                        import traceback
                        print("\n      Full traceback:")
                        traceback.print_exc()
                        raise
                    except Exception as e:
                        print(f"      ✗ Unexpected error loading OCR: {type(e).__name__}: {e}")
                        print("      → This is an unexpected error type")
                        import traceback
                        print("\n      Full traceback:")
                        traceback.print_exc()
                        raise
                    
                    # Stage 3: Verify OCR engines
                    self.progress.emit("[3/6] Verifying OCR engines...")
                    print("[3/6] Verifying OCR engines...")
                    try:
                        if hasattr(pipeline, 'ocr_layer') and pipeline.ocr_layer:
                            available = pipeline.get_available_ocr_engines()
                            if available:
                                print(f"      ✓ Found {len(available)} OCR engine(s): {', '.join(available)}")
                            else:
                                print("      ⚠ Warning: No OCR engines available")
                        else:
                            print("      ⚠ Warning: OCR layer not initialized")
                    except Exception as e:
                        print(f"      ⚠ Could not verify OCR engines: {e}")
                    
                    # Stage 4: Initialize translation layer (skip pre-loading for now)
                    self.progress.emit("[4/6] Initializing translation layer...")
                    print("[4/6] Initializing translation layer...")
                    try:
                        if hasattr(pipeline, 'translation_layer') and pipeline.translation_layer:
                            print("      ✓ Translation layer created")
                            
                            # SKIP pre-loading MarianMT model here - it crashes in Qt thread
                            # The model will load on first translation in the pipeline thread
                            # This is safer and the crash protection in the pipeline will handle it
                            print("      → MarianMT will load on first translation (lazy loading)")
                            print("      → First translation may take 3-5 seconds")
                        else:
                            print("      ⚠ Translation layer not available")
                    except Exception as e:
                        print(f"      ⚠ Translation layer check failed: {e}")
                    
                    # Stage 5: Verify overlay system
                    self.progress.emit("[5/6] Verifying overlay system...")
                    print("[5/6] Verifying overlay system...")
                    print("      ✓ Overlay system ready")
                    
                    # Stage 6: Final checks
                    self.progress.emit("[6/6] Finalizing pipeline...")
                    print("[6/6] Finalizing pipeline...")
                    print("      ✓ All components initialized")
                    print("="*60)
                    print("✓ OptikR is ready to use")
                    print("="*60 + "\n")
                    
                    self.progress.emit("Pipeline ready")
                    self.finished.emit(pipeline)
                    
                except KeyboardInterrupt:
                    print("\n[INFO] Pipeline initialization cancelled by user")
                    self.error.emit("Cancelled by user")
                except SystemExit:
                    print("\n[INFO] System exit called during initialization")
                    self.error.emit("System exit")
                except Exception as e:
                    # Note: Can't use self.logger here as this is in a separate thread
                    print("\n" + "="*60)
                    print("✗ PIPELINE INITIALIZATION FAILED")
                    print("="*60)
                    print(f"Error Type: {type(e).__name__}")
                    print(f"Error Message: {e}")
                    print("\nFull Traceback:")
                    print("-"*60)
                    
                    import traceback
                    import sys
                    traceback.print_exc(file=sys.stdout)
                    sys.stdout.flush()
                    
                    print("-"*60)
                    print("\nTroubleshooting:")
                    print("1. Check if all dependencies are installed:")
                    print("   pip install opencv-python numpy easyocr pytesseract paddleocr")
                    print("2. Check logs folder for detailed error messages")
                    print("3. Ensure you have enough RAM (4GB+ recommended)")
                    print("4. Try running from the original dev folder to compare")
                    print("="*60 + "\n")
                    
                    self.error.emit(f"{type(e).__name__}: {str(e)}")
                
                finally:
                    # Mark as not running when done (success or failure)
                    self._is_running = False
        
        # CRITICAL FIX: Run synchronously in main thread
        # Background thread causes Qt/OpenCV conflicts
        self.pipeline_loader = PipelineLoader(self.config_manager)
        self.pipeline_loader.finished.connect(self._on_pipeline_loaded)
        self.pipeline_loader.error.connect(self._on_pipeline_error_loading)
        self.pipeline_loader.progress.connect(self._on_pipeline_progress)
        
        # Run directly instead of in thread
        print("[INFO] Running pipeline initialization synchronously...")
        
        # Since we're running synchronously, we need to handle the result directly
        # The signals won't work properly in synchronous mode
        try:
            # Temporarily store the pipeline result
            pipeline_result = [None]  # Use list to allow modification in nested function
            error_result = [None]
            
            def capture_finished(pipeline):
                pipeline_result[0] = pipeline
            
            def capture_error(error):
                error_result[0] = error
            
            # Connect temporary handlers
            self.pipeline_loader.finished.connect(capture_finished)
            self.pipeline_loader.error.connect(capture_error)
            
            # Run the loader
            self.pipeline_loader.run()
            
            # Disconnect temporary handlers
            self.pipeline_loader.finished.disconnect(capture_finished)
            self.pipeline_loader.error.disconnect(capture_error)
            
            # Handle the result directly (no timeout needed - it's synchronous!)
            if error_result[0]:
                print(f"[ERROR] Pipeline initialization failed: {error_result[0]}")
                self._on_pipeline_error_loading(error_result[0])
            elif pipeline_result[0]:
                print("[INFO] Pipeline initialization completed successfully")
                self._on_pipeline_loaded(pipeline_result[0])
                
                # Warm up components for faster first translation
                if self.pipeline:
                    self.loading_overlay.set_status("[6/6] Warming up components...", 98)
                    QApplication.processEvents()
                    self.pipeline.warm_up_components()
            else:
                print("[WARNING] Pipeline initialization completed but no result")
                self._on_pipeline_error_loading("No pipeline returned")
                
        except Exception as e:
            print(f"[ERROR] Exception during pipeline initialization: {e}")
            import traceback
            traceback.print_exc()
            self._on_pipeline_error_loading(str(e))
    
    def _on_pipeline_progress(self, message):
        """Called when pipeline loading progress updates."""
        self.update_system_status(message, "loading")
        
        # Update loading overlay with detailed progress
        if self.loading_overlay and self.loading_overlay.isVisible():
            # Map progress messages to percentages
            progress_map = {
                "[1/6]": 85,
                "[2/6]": 90,
                "[3/6]": 92,
                "[4/6]": 94,
                "[5/6]": 96,
                "[6/6]": 98
            }
            
            for key, percentage in progress_map.items():
                if key in message:
                    self.loading_overlay.set_status(message, percentage)
                    QApplication.processEvents()
                    break
    
    def _on_pipeline_timeout(self):
        """Called when pipeline loading times out."""
        self.logger.log_error("SYSTEM", "pipeline_timeout", "Pipeline initialization timed out after 120 seconds")
        
        print("\n" + "="*60)
        print("⚠ PIPELINE INITIALIZATION TIMEOUT")
        print("="*60)
        print("The pipeline is taking longer than expected to load.")
        print("This usually means:")
        print("1. OCR models are being downloaded (first time only)")
        print("2. System is low on memory")
        print("3. An OCR engine is stuck loading")
        print("\nThe application will continue, but OCR may not work.")
        print("="*60 + "\n")
        
        # Try to terminate the loader thread
        if hasattr(self, 'pipeline_loader') and self.pipeline_loader.isRunning():
            self.pipeline_loader.terminate()
            self.pipeline_loader.wait(2000)  # Wait up to 2 seconds
        
        self.update_system_status("Pipeline initialization timed out", "error")
        
        # Show warning dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self,
            "Pipeline Timeout",
            "Pipeline initialization is taking longer than expected.\n\n"
            "Possible causes:\n"
            "• First-time model downloads (can take several minutes)\n"
            "• Low system memory\n"
            "• Slow internet connection\n\n"
            "The application will continue, but OCR functionality may be limited.\n"
            "You can try restarting the application."
        )
        
        # Hide loading overlay
        if self.loading_overlay:
            self.loading_overlay.hide()
    
    def _on_pipeline_loaded(self, pipeline):
        """Called when pipeline loading completes."""
        # Cancel timeout timer
        if hasattr(self, 'pipeline_timeout_timer'):
            self.pipeline_timeout_timer.stop()
        
        self.pipeline = pipeline
        
        if self.pipeline:
            # Set callbacks
            self.pipeline.on_translation_callback = self.on_translation_received
            self.pipeline.on_error_callback = self.on_pipeline_error
            self.pipeline.on_metrics_callback = self.on_metrics_updated
            self.logger.log_info("SYSTEM", "pipeline_initialized", "Translation pipeline initialized successfully")
            
            # Update sidebar OCR display
            self.update_sidebar_ocr_display()
            
            # Update OCR tab with available engines
            self._update_ocr_tab_availability()
            
            # Update Pipeline Management tab with pipeline reference
            if hasattr(self, 'pipeline_tab') and self.pipeline_tab:
                self.pipeline_tab.set_pipeline(self.pipeline)
            
            # Update status to ready
            self.update_system_status("Ready", "ready")
            
            # Hide loading overlay now that everything is ready
            if self.loading_overlay:
                self.loading_overlay.set_status("Ready!", 100)
                QApplication.processEvents()
                QTimer.singleShot(300, lambda: self.loading_overlay.hide())
        else:
            self.logger.log_warning("SYSTEM", "pipeline_init_failed", "Failed to initialize translation pipeline")
            self.update_system_status("Pipeline initialization failed", "error")
            
            # Hide loading overlay even on error
            if self.loading_overlay:
                self.loading_overlay.set_status("Initialization failed", 100)
                QApplication.processEvents()
                QTimer.singleShot(1000, lambda: self.loading_overlay.hide())
    
    def _update_ocr_tab_availability(self):
        """Update OCR tab with available engines after pipeline loads (if tab is loaded)."""
        try:
            if self.pipeline and hasattr(self.pipeline, 'ocr_layer'):
                engines = self.pipeline.ocr_layer.plugin_manager.get_available_engines()
                
                # Handle both dict and list return types
                if isinstance(engines, dict):
                    available_engines = list(engines.keys())
                else:
                    available_engines = engines if isinstance(engines, list) else []
                
                self.logger.log_info("OCR", "engines_discovered", "Available OCR engines", {"engines": available_engines})
                
                # Update OCR tab status indicators and refresh engine list if tab is loaded
                if hasattr(self, 'ocr_tab') and self.ocr_tab:
                    self.ocr_tab.pipeline = self.pipeline  # Update pipeline reference
                    self.ocr_tab._update_engine_statuses()
                    self.ocr_tab.refresh_engine_list()  # Refresh to show discovered engines
        except Exception as e:
            # Silently fail - not critical
            pass
    
    def _on_pipeline_error_loading(self, error_msg):
        """Called when pipeline loading fails with helpful error messages."""
        self.logger.log_error("SYSTEM", "pipeline_loading_error", "Pipeline loading error", {"error": error_msg})
        self.update_system_status("Pipeline initialization failed", "error")
        
        # Hide loading overlay
        if self.loading_overlay:
            self.loading_overlay.hide()
        
        # Detect error type and show specific help
        error_lower = error_msg.lower()
        
        if "No OCR plugins discovered" in error_msg or "Failed to create OCR layer" in error_msg:
            self._handle_missing_ocr_engines()
        elif "cuda" in error_lower or "gpu" in error_lower:
            # GPU initialization error
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "GPU Initialization Failed",
                "Failed to initialize GPU acceleration.\n\n"
                "Possible solutions:\n"
                "• Update your GPU drivers\n"
                "• Switch to CPU mode in Settings > Advanced > Performance\n"
                "• Restart your computer\n\n"
                f"Technical details:\n{error_msg}"
            )
        elif "memory" in error_lower or "out of memory" in error_lower:
            # Out of memory error
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Out of Memory",
                "Not enough RAM to load OCR models.\n\n"
                "Possible solutions:\n"
                "• Close other applications to free up memory\n"
                "• Use Tesseract (lighter OCR engine)\n"
                "• Restart your computer\n"
                "• Reduce image quality in Settings > Capture\n\n"
                f"Technical details:\n{error_msg}"
            )
        elif "import" in error_lower or "module" in error_lower:
            # Missing dependency error
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Missing Dependencies",
                "Required Python packages are missing.\n\n"
                "Possible solutions:\n"
                "• Reinstall the application\n"
                "• Run: pip install -r requirements.txt\n"
                "• Check the installation guide\n\n"
                f"Technical details:\n{error_msg}"
            )
        else:
            # Generic error dialog
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Pipeline Initialization Failed",
                f"Failed to initialize the translation pipeline.\n\n"
                f"Error: {error_msg}\n\n"
                f"Possible solutions:\n"
                f"• Install missing OCR dependencies\n"
                f"• Check if you have enough RAM (4GB+ recommended)\n"
                f"• Review the console output for detailed errors\n"
                f"• Check the logs folder for more information\n\n"
                f"The application will continue but OCR functionality will be limited."
            )
        
        # Hide loading overlay
        if self.loading_overlay:
            self.loading_overlay.hide()
    
    def _handle_missing_ocr_engines(self):
        """Handle missing OCR engines by showing installer dialog."""
        from PyQt6.QtWidgets import QMessageBox
        from ui.dialogs.ocr_engine_installer_dialog import show_ocr_engine_installer
        
        # Check if GPU is available
        has_gpu = False
        try:
            import torch
            has_gpu = torch.cuda.is_available()
        except:
            pass
        
        # Show installer dialog
        self.logger.log_info("SYSTEM", "showing_ocr_installer", "No OCR engines found - showing installer")
        
        selected_engine = show_ocr_engine_installer(has_gpu=has_gpu, parent=self)
        
        if selected_engine:
            # Engine was installed, restart application
            self.logger.log_info("SYSTEM", "ocr_installed", f"OCR engine installed: {selected_engine}")
            
            QMessageBox.information(
                self,
                "Restart Required",
                f"{selected_engine} has been installed successfully!\n\n"
                f"Please restart the application to use the new OCR engine."
            )
            
            # Close application
            self.close()
        else:
            # User cancelled installation
            self.logger.log_warning("SYSTEM", "ocr_install_cancelled", "User cancelled OCR engine installation")
            
            QMessageBox.warning(
                self,
                "No OCR Engine",
                "No OCR engine is installed.\n\n"
                "The application will continue but OCR functionality will not work.\n\n"
                "You can install an OCR engine later from the OCR Engines tab."
            )
    
    def update_system_status(self, message, status_type="ready"):
        """
        Update system status display.
        
        Args:
            message: Status message to display
            status_type: Type of status ('ready', 'loading', 'error')
        """
        # Update window title
        if status_type == "loading":
            self.setWindowTitle(f"{tr('app_title')} - {message}")
        elif status_type == "error":
            self.setWindowTitle(f"{tr('app_title')} - {message}")
        else:
            self.setWindowTitle(tr("app_title"))
        
        # Update status bar
        status_icons = {
            "ready": "●",
            "loading": "⟳",
            "error": "⚠"
        }
        icon = status_icons.get(status_type, "●")
        self.statusBar().showMessage(f"{icon} {message}")
        
        # Update sidebar status indicator
        if hasattr(self, 'sidebar'):
            self.sidebar.update_status(message, status_type)
        
        # Force UI update
        QApplication.processEvents()
    
    def toggle_translation(self):
        """Toggle translation pipeline on/off."""
        # Check if pipeline is still loading
        if hasattr(self, 'pipeline_loader') and self.pipeline_loader.isRunning():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Please Wait",
                "OCR engines are still loading in the background...\n\n"
                "This can take 20-120 seconds on first run while models download.\n\n"
                "Please wait for the status bar to show '● System Ready'.\n\n"
                "Current status: Pipeline initialization in progress"
            )
            return
        
        if not self.pipeline_running:
            # Start translation
            if not self.capture_region:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "No Capture Region",
                    "Please select a capture region first using the 'Select Capture Region' button."
                )
                return
            
            # Check if fullscreen capture is being used and warn about performance
            if self._is_fullscreen_capture():
                from PyQt6.QtWidgets import QMessageBox
                reply = QMessageBox.information(
                    self,
                    "Performance Tip",
                    "⚠️ You are capturing the entire screen.\n\n"
                    "For better performance, consider selecting a smaller capture region "
                    "that only includes the area you want to translate.\n\n"
                    "You can change the region using 'Select Capture Region' button.\n\n"
                    "Continue with fullscreen capture?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.No:
                    # User wants to change region
                    return
            
            # Check if StartupPipeline is initialized
            if not self.pipeline:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "Pipeline Not Ready",
                    "StartupPipeline failed to initialize.\n\n"
                    "Please check the console for errors and ensure:\n"
                    "• At least one OCR engine is installed\n"
                    "• At least one translation engine is available\n\n"
                    "Try restarting the application."
                )
                return
            
            # Set capture region - Multi-region is available via menu: "Select Overlay Region"
            # This code path is for programmatic multi-region setup
            multi_region_enabled = False  # Set to True to enable programmatic multi-region
            
            if multi_region_enabled:
                # Load and set multi-region config
                self.logger.log_info("PIPELINE", "using_multi_region", "Using multi-region configuration")
                
                try:
                    from app.models import MultiRegionConfig
                    regions_data = self.config_manager.get_setting('capture.regions', [])
                    active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
                    
                    config = MultiRegionConfig.from_dict({
                        'regions': regions_data,
                        'active_region_ids': active_ids
                    })
                    
                    # Set multi-region config
                    self.pipeline.set_multi_region_config(config)
                    
                    enabled_count = len(config.get_enabled_regions())
                    self.logger.log_info("PIPELINE", "multi_region_set", 
                                       f"Multi-region config set: {enabled_count} active regions")
                except Exception as e:
                    self.logger.log_error("PIPELINE", "multi_region_failed", 
                                        f"Failed to load multi-region config: {e}")
                    # Fall back to single region
                    multi_region_enabled = False
            
            if not multi_region_enabled:
                # Use single region mode (fallback)
                self.logger.log_info("PIPELINE", "setting_capture_region", 
                                   f"Setting pipeline capture region (single-region mode): {self.capture_region}")
                
                self.pipeline.set_capture_region(
                    x=self.capture_region['x'],
                    y=self.capture_region['y'],
                    width=self.capture_region['width'],
                    height=self.capture_region['height'],
                    monitor_id=self.capture_region.get('monitor_id', 0)
                )
            
            # Disable button to prevent double-click and show loading state
            self.start_btn.setEnabled(False)
            # Check if this is first run and show model download message
            try:
                from app.utils.first_run_detector import check_all_models_cached, get_first_run_message
                
                model_status = check_all_models_cached()
                
                if model_status["first_run"]:
                    # Show first-run message
                    from PyQt6.QtWidgets import QMessageBox
                    message = get_first_run_message()
                    
                    reply = QMessageBox.information(
                        self,
                        "First Time Setup",
                        message,
                        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
                    )
                    
                    if reply == QMessageBox.StandardButton.Cancel:
                        # User cancelled, don't start
                        return
            except Exception as e:
                # If first-run detection fails, just continue
                print(f"[WARNING] First-run detection failed: {e}")
            
            self.start_btn.setText("⏳ Starting...")
            self.statusBar().showMessage("⏳ Starting pipeline...", 0)
            
            # Start pipeline in a non-blocking way using QTimer
            def _start_pipeline_async():
                try:
                    self.logger.log_info("SYSTEM", "async_start_begin", "Starting pipeline async")
                    self.logger.log_info("SYSTEM", "calling_start_translation", "About to call start_translation")
                    result = self.pipeline.start_translation()
                    self.logger.log_info("SYSTEM", "start_translation_result", f"start_translation returned: {result}")
                    
                    if result:
                        self.pipeline_running = True
                        self.start_btn.setText("⏸ Stop")
                        self.start_btn.setStyleSheet("background-color: #F44336;")  # Red
                        self.start_btn.setEnabled(True)
                        self.statusBar().showMessage("● Translation Active - Capturing and translating...", 0)
                        
                        self.logger.log_info("SYSTEM", "translation_started", "Translation system started")
                    else:
                        # Reset button state on failure
                        self.start_btn.setText("▶ Start")
                        self.start_btn.setStyleSheet("background-color: #4CAF50;")  # Green
                        self.start_btn.setEnabled(True)
                        self.statusBar().showMessage("● Ready", 0)
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.critical(
                            self,
                            "Start Failed",
                            "Failed to start translation pipeline.\n"
                            "Please check your settings and try again."
                        )
                except Exception as e:
                    # Reset button state on exception
                    self.start_btn.setText("▶ Start")
                    self.start_btn.setStyleSheet("background-color: #4CAF50;")  # Green
                    self.start_btn.setEnabled(True)
                    self.statusBar().showMessage("● Ready", 0)
                    self.logger.log_error("SYSTEM", "pipeline_start_error", f"Exception starting pipeline: {e}")
                    import traceback
                    traceback.print_exc()
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Error starting pipeline:\n{str(e)}"
                    )
            
            # Start after a short delay to allow UI to update
            QTimer.singleShot(100, _start_pipeline_async)
        else:
            # Stop translation
            # Disable button to prevent double-click during stop
            self.start_btn.setEnabled(False)
            self.statusBar().showMessage("⏳ Stopping pipeline...", 0)
            
            try:
                import sys
                import time
                print("\n[STOP] ========== STOPPING PIPELINE ==========", flush=True)
                
                # CRITICAL FIX: Stop pipeline thread FIRST, then hide overlays
                # This prevents the thread from creating new overlays while we're hiding them
                
                print("[STOP] Step 1: Setting stop flags...", flush=True)
                self.pipeline_running = False
                
                print("[STOP] Step 2: Stopping pipeline thread...", flush=True)
                # This will set is_running=False and stop_event, preventing new overlays
                self.pipeline.stop_translation()
                print("[STOP] Pipeline thread stopped", flush=True)
                
                print("[STOP] Step 3: Hiding all overlays...", flush=True)
                print(f"[STOP] Main overlay system type: {type(self.overlay_system)}", flush=True)
                
                # Hide run.py's overlay system (probably empty)
                self.overlay_system.hide_all_translations(immediate=True)
                print("[STOP] Main overlay system hide completed", flush=True)
                
                # CRITICAL FIX: Also hide pipeline's overlay system (the one actually showing overlays)
                if self.pipeline and hasattr(self.pipeline, 'overlay_system') and self.pipeline.overlay_system:
                    print(f"[STOP] Pipeline overlay system type: {type(self.pipeline.overlay_system)}", flush=True)
                    print("[STOP] Hiding pipeline's overlay system...", flush=True)
                    
                    # Check if it's a process-based system
                    from ui.overlay_process import ProcessBasedOverlaySystem
                    is_process_based = isinstance(self.pipeline.overlay_system, ProcessBasedOverlaySystem)
                    
                    if is_process_based:
                        print("[STOP] Using PROCESS-BASED overlay system - cleanup will be fast", flush=True)
                        # Process-based system: hide_all is non-blocking and fast
                        self.pipeline.overlay_system.hide_all_translations(immediate=True)
                        # Give process a moment to process the command
                        time.sleep(0.1)
                    else:
                        print("[STOP] Using THREAD-BASED overlay system - processing events...", flush=True)
                        # Thread-based system: needs event processing to prevent freeze
                        self.pipeline.overlay_system.hide_all_translations(immediate=True)
                        
                        # Process events IMMEDIATELY after each hide to prevent freeze
                        from PyQt6.QtWidgets import QApplication
                        for i in range(10):  # More iterations for many overlays
                            QApplication.processEvents()
                            time.sleep(0.02)  # Small delay between each
                            if i % 3 == 0:
                                print(f"[STOP] Processing overlay cleanup... ({i+1}/10)", flush=True)
                    
                    print("[STOP] Pipeline overlay system hide completed", flush=True)
                else:
                    print("[STOP] WARNING: Pipeline has no overlay_system attribute!", flush=True)
                
                # Final event processing (less needed now since we processed during hide)
                from PyQt6.QtWidgets import QApplication
                for i in range(2):
                    QApplication.processEvents()
                    time.sleep(0.05)
                    print(f"[STOP] Final event processing ({i+1}/2)", flush=True)
                
                print("[STOP] Final cleanup complete", flush=True)
                
                print("[STOP] Step 4: Updating UI...")
                self.start_btn.setText("▶ Start")
                self.start_btn.setStyleSheet("background-color: #4CAF50;")  # Green
                self.start_btn.setEnabled(True)
                self.statusBar().showMessage("● Ready", 0)
                
                print("[STOP] ========== STOP COMPLETE ==========\n")
                
                # Offer to extract and translate individual words BEFORE cleanup
                self._offer_word_extraction()
                
                self.logger.log_info("SYSTEM", "translation_stopped", "Translation system stopped")
                
            except Exception as e:
                self.logger.log_error("SYSTEM", "pipeline_stop_error", f"Exception stopping pipeline: {e}")
                # Re-enable button even on error
                self.start_btn.setEnabled(True)
                self.start_btn.setText("▶ Start")
                self.start_btn.setStyleSheet("background-color: #4CAF50;")  # Green
                self.pipeline_running = False
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Stop Warning",
                    f"Pipeline stopped but encountered an error:\n{str(e)}"
                )
    
    def on_translation_received(self, translations):
        """Handle received translations."""
        # Check if pipeline is still running FIRST (before any processing)
        if not self.pipeline_running:
            print(f"[TRANSLATION] Pipeline stopped, discarding {len(translations)} queued translations")
            return
        
        # Double-check pipeline is still running (race condition protection)
        if not hasattr(self, 'pipeline') or not self.pipeline or not self.pipeline.is_running:
            print(f"[TRANSLATION] Pipeline not running, discarding {len(translations)} queued translations")
            return
        
        self.logger.log_info("TRANSLATION", "translations_received", f"Received {len(translations)} translations", 
                            {"count": len(translations)})
        
        # CRITICAL FIX: This callback is called from worker thread!
        # We CANNOT update Qt widgets directly from here - it causes freezes/crashes
        # Use QTimer to update overlay on main thread
        from PyQt6.QtCore import QTimer
        
        # Schedule overlay update on main thread
        QTimer.singleShot(0, lambda: self._update_overlay_on_main_thread(translations))
    
    def _update_overlay_on_main_thread(self, translations):
        """Update overlay on main thread (safe for Qt)."""
        print(f"[OVERLAY] _update_overlay_on_main_thread called with {len(translations)} translations, pipeline_running={self.pipeline_running}", flush=True)
        
        # Check if pipeline is still running (prevent showing overlays after stop)
        if not self.pipeline_running:
            print(f"[OVERLAY] Pipeline stopped, ignoring {len(translations)} translation callbacks", flush=True)
            return
        
        # Display translations using PyQt6 overlay system
        for i, trans in enumerate(translations, 1):
            self.logger.log_debug("TRANSLATION", "translation_detail", f"Translation {i}", 
                                 {"original": trans.original_text, "translated": trans.translated_text, 
                                  "confidence": trans.confidence, "engine": trans.engine_used})
            
            # Show translation overlay
            try:
                # Get position from translation object
                # IMPORTANT: OCR returns coordinates relative to capture region
                # We need to convert to absolute screen coordinates
                if hasattr(trans, 'position') and trans.position:
                    # Translation.position is a Rectangle with x, y relative to capture region
                    ocr_x = trans.position.x
                    ocr_y = trans.position.y
                elif hasattr(trans, 'region') and trans.region:
                    ocr_x = trans.region.x
                    ocr_y = trans.region.y
                elif hasattr(trans, 'x') and hasattr(trans, 'y'):
                    ocr_x = trans.x
                    ocr_y = trans.y
                else:
                    # Fallback position
                    ocr_x = 100
                    ocr_y = 100 + i * 80
                
                # Convert OCR coordinates to monitor-relative coordinates
                # OCR returns coordinates relative to capture region
                # Capture region coordinates are already monitor-relative (or absolute if monitor offset is 0)
                if self.capture_region:
                    # Add capture region offset to OCR position
                    # This gives us the position relative to the monitor
                    monitor_rel_x = self.capture_region['x'] + ocr_x
                    monitor_rel_y = self.capture_region['y'] + ocr_y
                    monitor_id = self.capture_region.get('monitor_id', 0)
                    
                    position = (monitor_rel_x, monitor_rel_y)
                    
                    self.logger.log_debug("OVERLAY", "coordinate_conversion", 
                                         f"OCR coords (region-relative): ({ocr_x}, {ocr_y}), "
                                         f"Capture region offset: ({self.capture_region['x']}, {self.capture_region['y']}), "
                                         f"Final position (monitor-relative): ({monitor_rel_x}, {monitor_rel_y}), "
                                         f"Monitor: {monitor_id}")
                else:
                    # No capture region info - use OCR coords as-is
                    position = (ocr_x, ocr_y)
                    monitor_id = 0
                    self.logger.log_warning("OVERLAY", "no_capture_region", 
                                          "No capture region available for coordinate conversion")
                
                # Get translation ID
                translation_id = str(getattr(trans, 'id', f'translation_{i}'))
                
                # Show overlay with monitor ID (now safe - we're on main thread)
                self.overlay_system.show_translation(
                    text=trans.translated_text,
                    position=position,
                    translation_id=translation_id,
                    monitor_id=monitor_id
                )
                
                self.logger.log_debug("OVERLAY", "translation_displayed", 
                                     f"Displayed translation overlay", 
                                     {"id": translation_id, "position": position, "monitor_id": monitor_id})
            except Exception as e:
                self.logger.log_error("OVERLAY", "display_failed", 
                                     "Failed to display translation overlay", 
                                     {"error": str(e)})
    
    def _offer_word_extraction(self):
        """Offer to extract and translate individual words from cached sentences."""
        try:
            # Check if word extraction is enabled
            extract_enabled = self.config_manager.get_setting('dictionary.extract_words_on_stop', True)
            if not extract_enabled:
                print("[WORD EXTRACTION] Feature disabled in settings")
                return
            
            # Get the runtime pipeline (StartupPipeline.pipeline is the RuntimePipeline)
            runtime_pipeline = None
            if self.pipeline and hasattr(self.pipeline, 'pipeline'):
                runtime_pipeline = self.pipeline.pipeline
                print(f"[WORD EXTRACTION] Found runtime pipeline: {type(runtime_pipeline)}")
            else:
                print(f"[WORD EXTRACTION] No runtime pipeline (self.pipeline={type(self.pipeline) if self.pipeline else None})")
                return
            
            # Check if we have a cache_manager with persistent dictionary
            if not hasattr(runtime_pipeline, 'cache_manager'):
                print("[WORD EXTRACTION] Runtime pipeline has no cache_manager")
                return
            
            cache_manager = runtime_pipeline.cache_manager
            if not cache_manager:
                print("[WORD EXTRACTION] cache_manager is None")
                return
                
            if not hasattr(cache_manager, 'persistent_dictionary'):
                print("[WORD EXTRACTION] cache_manager has no persistent_dictionary")
                return
            
            persistent_dict = cache_manager.persistent_dictionary
            if not persistent_dict:
                print("[WORD EXTRACTION] persistent_dictionary is None")
                return
            
            print(f"[WORD EXTRACTION] ✓ Found persistent dictionary: {type(persistent_dict)}")
            
            # Get all translations from persistent dictionary
            try:
                source_lang = self.config_manager.get_setting('translation.source_language', 'en')
                target_lang = self.config_manager.get_setting('translation.target_language', 'de')
                
                # Get dictionary stats to see how many entries we have
                stats = persistent_dict.get_stats(source_lang, target_lang)
                sentence_count = stats.total_entries if stats else 0
                
                print(f"[WORD EXTRACTION] Found {sentence_count} entries in dictionary")
                
                if sentence_count == 0:
                    print("[WORD EXTRACTION] No entries to extract words from")
                    return
                
                # Get all entries
                all_entries = persistent_dict.get_all_entries(source_lang, target_lang)
                if not all_entries:
                    print("[WORD EXTRACTION] get_all_entries returned empty")
                    return
                
                print(f"[WORD EXTRACTION] Retrieved {len(all_entries)} entries")
                    
            except Exception as e:
                print(f"[WORD EXTRACTION] Error getting dictionary entries: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # Extract word pairs from already-translated sentences
            import re
            from PyQt6.QtWidgets import QMessageBox, QProgressDialog
            from PyQt6.QtCore import Qt
            
            # Build word pair mappings from sentences
            word_pairs = {}  # {source_word: {target_word: count}}
            
            for entry in all_entries:
                # Extract words from source (alphanumeric only, 2+ characters)
                source_words = re.findall(r'\b[a-zA-Z]{2,}\b', entry.source_text.lower())
                # Extract words from target
                target_words = re.findall(r'\b[\w]{2,}\b', entry.translation.lower())
                
                # Simple heuristic: if sentence has same number of words, pair them up
                # Otherwise, we'll need to translate individual words
                if len(source_words) == len(target_words):
                    for src_word, tgt_word in zip(source_words, target_words):
                        if src_word not in word_pairs:
                            word_pairs[src_word] = {}
                        word_pairs[src_word][tgt_word] = word_pairs[src_word].get(tgt_word, 0) + 1
            
            # Get most common translation for each word
            word_translations = {}
            for src_word, tgt_counts in word_pairs.items():
                # Get most common target word
                best_tgt = max(tgt_counts.items(), key=lambda x: x[1])[0]
                word_translations[src_word] = best_tgt
            
            # Also collect words that need translation (no pair found)
            words_needing_translation = set()
            for entry in all_entries:
                source_words = re.findall(r'\b[a-zA-Z]{2,}\b', entry.source_text.lower())
                for word in source_words:
                    if word not in word_translations:
                        words_needing_translation.add(word)
            
            total_paired = len(word_translations)
            total_to_translate = len(words_needing_translation)
            
            print(f"[WORD EXTRACTION] Found {total_paired} word pairs from sentences")
            print(f"[WORD EXTRACTION] Need to translate {total_to_translate} additional words")
            
            if total_paired == 0 and total_to_translate == 0:
                print("[WORD EXTRACTION] No words to extract")
                return
            
            # Ask user if they want to extract words
            reply = QMessageBox.question(
                self,
                "Extract Individual Words?",
                f"Translation session complete!\n\n"
                f"📊 {sentence_count} sentences saved to dictionary.\n\n"
                f"Would you like to also save individual words?\n\n"
                f"Found:\n"
                f"• {total_paired} word pairs from sentences (instant)\n"
                f"• {total_to_translate} words needing translation (~{total_to_translate * 2}s)\n\n"
                f"This improves future translation quality!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                print("[WORD EXTRACTION] User declined")
                return
            
            # Create progress dialog
            total_work = total_paired + total_to_translate
            progress = QProgressDialog(
                "Extracting words from sentences...",
                "Cancel",
                0,
                total_work,
                self
            )
            progress.setWindowTitle("Word Extraction")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            saved_count = 0
            skipped_count = 0
            current_progress = 0
            
            # First, save word pairs from sentences (fast - no translation needed)
            print(f"[WORD EXTRACTION] Saving {total_paired} word pairs...")
            for src_word, tgt_word in word_translations.items():
                if progress.wasCanceled():
                    break
                
                current_progress += 1
                progress.setValue(current_progress)
                progress.setLabelText(f"Saving word pair {current_progress}/{total_work}: '{src_word}' → '{tgt_word}'")
                
                try:
                    # Check if already exists
                    existing = persistent_dict.lookup(src_word, source_lang, target_lang)
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Save word pair
                    persistent_dict.add_translation(
                        original=src_word,
                        translation=tgt_word,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        confidence=0.85,  # Lower confidence since it's extracted, not directly translated
                        engine='word_extraction_paired'
                    )
                    saved_count += 1
                    
                except Exception as e:
                    print(f"[WORD EXTRACTION] Failed to save '{src_word}': {e}")
            
            # Then translate remaining words (slower)
            if total_to_translate > 0 and not progress.wasCanceled():
                print(f"[WORD EXTRACTION] Translating {total_to_translate} additional words...")
                from app.interfaces import TranslationEngine
                
                for word in sorted(words_needing_translation):
                    if progress.wasCanceled():
                        break
                    
                    current_progress += 1
                    progress.setValue(current_progress)
                    progress.setLabelText(f"Translating word {current_progress}/{total_work}: '{word}'")
                    
                    try:
                        # Check if already exists
                        existing = persistent_dict.lookup(word, source_lang, target_lang)
                        if existing:
                            skipped_count += 1
                            continue
                        
                        # Translate word
                        translated = self.pipeline.translation_layer.translate(
                            text=word,
                            engine=TranslationEngine.MARIANMT,
                            src_lang=source_lang,
                            tgt_lang=target_lang,
                            options={}
                        )
                        
                        # Save to dictionary
                        if translated:
                            persistent_dict.add_translation(
                                original=word,
                                translation=translated,
                                source_lang=source_lang,
                                target_lang=target_lang,
                                confidence=0.9,
                                engine='word_extraction_translated'
                            )
                            saved_count += 1
                        
                        # Process events to keep UI responsive
                        from PyQt6.QtWidgets import QApplication
                        QApplication.processEvents()
                        
                    except Exception as e:
                        print(f"[WORD EXTRACTION] Failed to translate '{word}': {e}")
            
            progress.setValue(total_work)
            progress.close()
            
            print(f"[WORD EXTRACTION] Complete: {saved_count} saved, {skipped_count} skipped")
            
            # Show completion message
            QMessageBox.information(
                self,
                "Word Extraction Complete",
                f"✅ Word extraction complete!\n\n"
                f"📝 Saved: {saved_count} new words\n"
                f"⏭️ Skipped: {skipped_count} (already in dictionary)\n"
                f"📊 Processed: {total_work} total words\n\n"
                f"Breakdown:\n"
                f"• {total_paired} word pairs from sentences (instant)\n"
                f"• {total_to_translate} words translated individually\n\n"
                f"These words will improve future translations!"
            )
            
        except Exception as e:
            print(f"[ERROR] Word extraction failed: {e}")
            import traceback
            traceback.print_exc()
    
    def on_pipeline_error(self, error_message):
        """Handle pipeline errors."""
        self.logger.log_error("SYSTEM", "pipeline_error", "Pipeline error occurred", {"error": error_message})
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            self,
            "Pipeline Error",
            f"Translation pipeline error:\n\n{error_message}"
        )
    
    def on_metrics_updated(self, metrics):
        """Handle metrics updates."""
        # Calculate validation rate
        total_detected = metrics.text_blocks_validated + metrics.text_blocks_rejected
        validation_rate = (metrics.text_blocks_validated / total_detected * 100) if total_detected > 0 else 0
        
        # Update status bar with metrics
        status_text = (
            f"● Translation Active | "
            f"FPS: {metrics.average_fps:.1f} | "
            f"Latency: {metrics.average_latency_ms:.0f}ms | "
            f"Validated: {metrics.text_blocks_validated} ({validation_rate:.0f}%) | "
            f"Translations: {metrics.translations_completed} | "
            f"Dict: {metrics.dictionary_hits} | "
            f"Cache: {metrics.cache_hits}"
        )
        self.statusBar().showMessage(status_text, 0)
    
    def change_ocr_engine(self, engine_name: str, show_dialog: bool = True) -> bool:
        """
        Change OCR engine on-the-fly without restarting.
        
        Args:
            engine_name: Name of OCR engine ('easyocr', 'tesseract', 'paddleocr', 'onnx')
            show_dialog: Whether to show dialog on error (False during initialization)
            
        Returns:
            True if engine changed successfully
        """
        if not self.pipeline:
            self.logger.log_warning("OCR", "engine_change_deferred", "Pipeline not initialized - engine change will be applied when pipeline starts", 
                                   {"requested_engine": engine_name})
            
            # Only show dialog if explicitly requested (not during initialization)
            if show_dialog:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Pipeline Not Ready",
                    "Translation pipeline is not initialized yet.\n\n"
                    "The engine selection will be applied when the pipeline starts."
                )
            return False
        
        self.logger.log_info("OCR", "engine_changing", "Changing OCR engine", {"engine": engine_name})
        
        # Change engine
        success = self.pipeline.set_ocr_engine(engine_name)
        
        if success:
            self.logger.log_info("OCR", "engine_changed", "OCR engine changed successfully", {"engine": engine_name})
            
            # Update UI if OCR tab exists and is loaded
            if hasattr(self, 'ocr_tab') and self.ocr_tab:
                try:
                    self.ocr_tab.update_current_engine_display(engine_name)
                except Exception as e:
                    self.logger.log_warning("UI", "ocr_tab_update_failed", "Could not update OCR tab display", {"error": str(e)})
            
            # Show success message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Engine Changed",
                f"OCR engine changed to {engine_name}.\n\n"
                "✓ Change is effective immediately!\n"
                "✓ No restart required!\n"
                "✓ Pipeline continues running!"
            )
            return True
        else:
            self.logger.log_error("OCR", "engine_change_failed", "Failed to change OCR engine", {"engine": engine_name})
            
            # Get list of available engines
            available_engines = []
            if hasattr(self.pipeline, 'ocr_layer'):
                try:
                    available_engines = list(self.pipeline.ocr_layer.plugin_manager.get_available_engines().keys())
                except:
                    pass
            
            available_list = ", ".join(available_engines) if available_engines else "None"
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Engine Not Available",
                f"Cannot switch to {engine_name.upper()} - engine is not available.\n\n"
                f"Available engines: {available_list}\n\n"
                "Possible reasons:\n"
                "• Engine failed to load during startup\n"
                "• Required dependencies not installed\n"
                "• DLL or library loading error\n\n"
                "Check the console output for detailed error messages."
                "Check the console for details."
            )
            return False
    
    def get_available_ocr_engines(self) -> list:
        """Get list of available OCR engines."""
        if self.pipeline:
            return self.pipeline.get_available_ocr_engines()
        return []
    
    def get_current_ocr_engine(self) -> str:
        """Get currently active OCR engine."""
        if self.pipeline:
            return self.pipeline.get_current_ocr_engine()
        return "unknown"
    
    def update_sidebar_ocr_display(self):
        """Update the sidebar OCR engine display."""
        try:
            # Get the engine from pipeline or config
            if self.pipeline:
                current_engine = self.get_current_ocr_engine()
            else:
                # Get engine from config
                current_engine = self.config_manager.get_setting('ocr.default_engine', 'easyocr')
            
            # Update sidebar
            if hasattr(self, 'sidebar') and current_engine:
                self.sidebar.update_ocr_engine(current_engine)
            
        except Exception as e:
            # Silently fail - not critical
            pass
    
    def show_quick_ocr_switch(self):
        """Show quick OCR engine switch dialog with only installed engines (modeless)."""
        from ui.dialogs.quick_ocr_switch_dialog import QuickOCRSwitchDialog
        
        # Create and show dialog (modeless - allows interaction with main window)
        # Keep reference to prevent garbage collection
        if not hasattr(self, 'quick_ocr_switch_window') or not self.quick_ocr_switch_window:
            self.quick_ocr_switch_window = QuickOCRSwitchDialog(
                self.config_manager,
                self.ocr_tab if hasattr(self, 'ocr_tab') else None,
                self.pipeline,
                self
            )
        else:
            # Recreate dialog to refresh engine list
            self.quick_ocr_switch_window = QuickOCRSwitchDialog(
                self.config_manager,
                self.ocr_tab if hasattr(self, 'ocr_tab') else None,
                self.pipeline,
                self
            )
        
        # Make it modeless by using show() instead of exec()
        self.quick_ocr_switch_window.setModal(False)
        self.quick_ocr_switch_window.show()
        self.quick_ocr_switch_window.raise_()
        self.quick_ocr_switch_window.activateWindow()
    
    def toggle_theme(self, is_dark_mode):
        """
        Toggle between dark and light mode.
        
        Args:
            is_dark_mode: True for dark mode, False for light mode
        """
        try:
            # Determine which stylesheet to load
            if is_dark_mode:
                stylesheet_path = Path(__file__).parent / "app" / "styles" / "dark.qss"
                theme_name = "dark"
            else:
                stylesheet_path = Path(__file__).parent / "app" / "styles" / "base.qss"
                theme_name = "light"
            
            # Load and apply stylesheet
            if stylesheet_path.exists():
                with open(stylesheet_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                
                # Apply to application
                app = QApplication.instance()
                app.setStyleSheet(stylesheet)
                
                # Save preference
                self.config_manager.set_setting('ui.dark_mode', is_dark_mode)
                self.config_manager.save_config()
                
                self.logger.log_info("UI", "theme_changed", f"Theme changed to {theme_name} mode")
                
                # Show brief status message
                self.statusBar().showMessage(f"✓ Switched to {theme_name} mode", 2000)
            else:
                self.logger.log_error("UI", "theme_file_missing", f"Theme file not found: {stylesheet_path}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Theme Error",
                    f"Could not find {theme_name} mode stylesheet:\n{stylesheet_path}"
                )
        except Exception as e:
            self.logger.log_error("UI", "theme_change_failed", "Failed to change theme", {"error": str(e)})
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Theme Error",
                f"Failed to change theme:\n\n{str(e)}"
            )
    
    def quit_application(self):
        """Force quit the application (bypass tray minimize)."""
        print("[QUIT] Force quit requested - bypassing tray")
        self._force_quit = True
        self.close()
    
    def closeEvent(self, event):
        """Handle window close event - minimize to tray or quit."""
        # Check if this is a forced quit (from tray menu)
        force_quit = getattr(self, '_force_quit', False)
        
        if force_quit:
            print("[CLOSE EVENT] Force quit - bypassing tray")
            # Reset flag for next time
            self._force_quit = False
        else:
            # Check if minimize to tray is enabled (check tray manager state directly)
            should_minimize_to_tray = False
            
            if self.tray_manager:
                tray_enabled = self.tray_manager.is_enabled()
                print(f"[CLOSE EVENT] Tray manager exists: enabled={tray_enabled}")
                if tray_enabled:
                    # Tray manager is enabled, so minimize to tray
                    should_minimize_to_tray = True
            else:
                print("[CLOSE EVENT] No tray manager")
            
            print(f"[CLOSE EVENT] Should minimize to tray: {should_minimize_to_tray}")
            
            if should_minimize_to_tray:
                # Minimize to tray instead of closing
                event.ignore()
                self.hide()
                
                # Show notification on first minimize
                if not hasattr(self, '_tray_notification_shown'):
                    self.tray_manager.show_message(
                        "OptikR",
                        "Application minimized to system tray. Click the tray icon to restore.",
                        QSystemTrayIcon.MessageIcon.Information
                    )
                    self._tray_notification_shown = True
                
                self.logger.log_info("USER_ACTION", "minimized_to_tray", "Window minimized to system tray")
                return
        
        print("[CLOSE EVENT] Proceeding with normal close")
        
        # Normal close behavior
        # Check for unsaved changes first
        if self.has_unsaved_changes:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self,
                "Unsaved Changes",
                "You have unsaved changes.\n\nDo you want to save before closing?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_all_settings()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            # If Discard, continue with cleanup
        
        # Save window position and size before closing
        self._save_window_state()
        
        # Perform cleanup
        self._cleanup_on_exit()
        event.accept()
    
    def _save_window_state(self):
        """Save current window position and size to config."""
        try:
            # Only save if not maximized (save normal geometry)
            if not self.isMaximized():
                geometry = self.geometry()
                self.config_manager.set_setting('ui.window_x', geometry.x())
                self.config_manager.set_setting('ui.window_y', geometry.y())
                self.config_manager.set_setting('ui.window_width', geometry.width())
                self.config_manager.set_setting('ui.window_height', geometry.height())
                self.logger.log_info("UI", "window_state_saved", "Window position and size saved", {
                    "x": geometry.x(),
                    "y": geometry.y(),
                    "width": geometry.width(),
                    "height": geometry.height()
                })
            else:
                # If maximized, save the normal geometry (before maximization)
                normal_geometry = self.normalGeometry()
                self.config_manager.set_setting('ui.window_x', normal_geometry.x())
                self.config_manager.set_setting('ui.window_y', normal_geometry.y())
                self.config_manager.set_setting('ui.window_width', normal_geometry.width())
                self.config_manager.set_setting('ui.window_height', normal_geometry.height())
                self.logger.log_info("UI", "window_state_saved", "Window normal geometry saved (was maximized)", {
                    "x": normal_geometry.x(),
                    "y": normal_geometry.y(),
                    "width": normal_geometry.width(),
                    "height": normal_geometry.height()
                })
            
            # Persist to disk
            self.config_manager.save_config()
        except Exception as e:
            self.logger.log_error("UI", "window_state_save_failed", "Failed to save window state", {"error": str(e)})
    
    def _cleanup_on_exit(self):
        """Perform comprehensive cleanup before exit."""
        self.logger.log_info("SYSTEM", "cleanup_started", "Starting application cleanup")
        
        try:
            # 0. Stop metrics timer
            if hasattr(self, 'metrics_timer') and self.metrics_timer:
                self.metrics_timer.stop()
            
            # 1. Stop pipeline if running
            if self.pipeline_running and self.pipeline:
                self.logger.log_info("SYSTEM", "pipeline_stopping", "Stopping translation pipeline")
                self.pipeline.stop_translation()
                self.pipeline_running = False
            
            # 2. Hide all overlays BEFORE cleaning up pipeline
            # This ensures overlays are properly hidden before resources are freed
            if self.pipeline and hasattr(self.pipeline, 'overlay_system') and self.pipeline.overlay_system:
                self.logger.log_info("SYSTEM", "overlay_hiding", "Hiding all overlays before cleanup")
                try:
                    self.pipeline.overlay_system.hide_all_translations(immediate=True)
                    # Process events to ensure overlays are actually hidden
                    from PyQt6.QtWidgets import QApplication
                    for _ in range(3):
                        QApplication.processEvents()
                except Exception as e:
                    self.logger.log_warning("SYSTEM", "overlay_hide_failed", f"Failed to hide overlays: {e}")
            
            # 3. Clean up pipeline resources
            if self.pipeline:
                self.logger.log_info("SYSTEM", "pipeline_cleanup", "Cleaning up pipeline resources")
                
                # Stop process-based overlay system if used
                if hasattr(self.pipeline, 'overlay_system') and self.pipeline.overlay_system:
                    from ui.overlay_process import ProcessBasedOverlaySystem
                    if isinstance(self.pipeline.overlay_system, ProcessBasedOverlaySystem):
                        self.logger.log_info("SYSTEM", "process_overlay_cleanup", "Stopping process-based overlay system")
                        self.pipeline.overlay_system.stop()
                
                # Call cleanup if available
                if hasattr(self.pipeline, 'cleanup'):
                    self.pipeline.cleanup()
                self.pipeline = None
            
            # 3. Clear caches if available
            try:
                # Check if we have access to caching manager through pipeline components
                if hasattr(self, 'pipeline') and self.pipeline:
                    # Try to access OCR layer cache
                    if hasattr(self.pipeline, 'ocr_layer') and self.pipeline.ocr_layer:
                        self.logger.log_info("SYSTEM", "cache_clearing", "Clearing OCR cache")
                        self.pipeline.ocr_layer.clear_cache()
                    
                    # Try to access translation layer cache
                    if hasattr(self.pipeline, 'translation_layer') and self.pipeline.translation_layer:
                        self.logger.log_info("SYSTEM", "cache_clearing", "Clearing translation cache")
                        self.pipeline.translation_layer.clear_cache()
                    
                    # Clear translation_cache plugin (in-memory cache)
                    if hasattr(self.pipeline, 'translation_cache') and self.pipeline.translation_cache:
                        self.logger.log_info("SYSTEM", "cache_clearing", "Clearing translation_cache plugin")
                        print("[CACHE CLEAR] Clearing translation_cache plugin...")
                        self.pipeline.translation_cache.clear()
                        print("[CACHE CLEAR] ✓ Translation cache cleared")
                    
                    # Clear cache_manager caches
                    if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                        self.logger.log_info("SYSTEM", "cache_clearing", "Clearing cache_manager")
                        print("[CACHE CLEAR] Clearing cache_manager...")
                        self.pipeline.cache_manager.clear_all(clear_dictionary=False)
                        print("[CACHE CLEAR] ✓ Cache manager cleared")
            except Exception as e:
                self.logger.log_warning("SYSTEM", "cache_clear_failed", "Could not clear some caches", {"error": str(e)})
                print(f"[CACHE CLEAR] Error: {e}")
                import traceback
                traceback.print_exc()
            
            # 4. Clear GPU memory if available
            try:
                import torch
                if torch.cuda.is_available():
                    self.logger.log_info("SYSTEM", "gpu_cleanup", "Clearing GPU cache")
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except ImportError:
                pass  # PyTorch not available
            except Exception as e:
                self.logger.log_warning("SYSTEM", "gpu_clear_failed", "Could not clear GPU cache", {"error": str(e)})
            
            # 5. Force garbage collection
            self.logger.log_info("SYSTEM", "garbage_collection", "Running garbage collection")
            import gc
            gc.collect()
            
            # 6. Cleanup overlay system
            if hasattr(self, 'overlay_system'):
                self.logger.log_info("SYSTEM", "overlay_cleanup", "Cleaning up overlay system")
                self.overlay_system.cleanup()
            
            # 7. Cleanup logger
            self.logger.log_info("SYSTEM", "cleanup_complete", "Cleanup completed successfully")
            self.logger.cleanup()
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.log_error("SYSTEM", "cleanup_error", "Error during cleanup", {"error": str(e)})
            print(f"[ERROR] Error during cleanup: {e}")
            import traceback
            traceback.print_exc()



def ensure_user_data_folders():
    """Ensure all necessary user_data folders exist."""
    from app.utils.path_utils import get_user_data_path
    
    # Define required folders
    required_folders = [
        get_user_data_path(),  # user_data/
        get_user_data_path('config'),  # user_data/config/
        get_user_data_path('logs'),  # user_data/logs/
        get_user_data_path('cache'),  # user_data/cache/
    ]
    
    # Create folders if they don't exist
    for folder in required_folders:
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created folder: {folder}")


def main():
    """Run the styling test window."""
    print("\n" + "="*60)
    print("OPTIKR")
    print("="*60)
    print("Starting application...")
    print()
    
    # Ensure user_data folders exist (first run)
    ensure_user_data_folders()
    
    app = QApplication(sys.argv)
    
    # Create config manager for language and consent
    temp_config = SimpleConfigManager()
    
    # Load UI language from config and initialize translation system
    try:
        from app.translations import get_language_manager
        ui_lang = temp_config.get_setting('ui.language', 'en')
        language_manager = get_language_manager()
        language_manager.set_language(ui_lang)
        print(f"[INFO] UI language set to: {ui_lang}")
    except Exception as e:
        print(f"[WARNING] Failed to load UI language: {e}")
    
    # Load dark mode stylesheet (default)
    stylesheet_path = Path(__file__).parent / "app" / "styles" / "dark.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        print(f"[INFO] Loaded dark mode stylesheet from: {stylesheet_path}")
    else:
        # Fallback to base stylesheet
        stylesheet_path = Path(__file__).parent / "app" / "styles" / "base.qss"
        if stylesheet_path.exists():
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
            print(f"[INFO] Loaded base stylesheet from: {stylesheet_path}")
        else:
            print(f"[WARNING] No stylesheet found")
            return 1
    
    # Check for user consent
    if not check_user_consent(temp_config):
        print("\n" + "=" * 60)
        print("FIRST TIME LAUNCH - USER CONSENT REQUIRED")
        print("=" * 60)
        print("Showing consent dialog...")
        
        # Show consent dialog (pass config_manager for consolidated config)
        if not show_consent_dialog(parent=None, config_manager=temp_config):
            print("\n[INFO] User declined consent. Exiting application.")
            print("=" * 60)
            return 0  # Exit gracefully
        
        # Consent is already saved by show_consent_dialog
        
        print("[INFO] User consent obtained. Continuing...")
        print("=" * 60 + "\n")
    
    # Create window (it will show itself immediately in __init__)
    window = StyleTestWindow()
    
    # Note: window.show() is called in __init__ for instant display
    # Update OCR display after pipeline loads (handled in _on_pipeline_loaded)
    
    print("\n[INFO] OptikR started successfully")
    print("[INFO] Ready for translation")
    
    return app.exec()


if __name__ == "__main__":
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='OptikR - OCR and Translation Tool')
    parser.add_argument('--create-plugin', action='store_true', 
                       help='Launch plugin generator (no UI)')
    parser.add_argument('--plugin-type', type=str, choices=['capture', 'ocr', 'translation', 'optimizer', 'text_processor'],
                       help='Plugin type to generate')
    parser.add_argument('--plugin-generator', type=str, metavar='PATH',
                       help='Generate plugin from template at specified path (no UI)')
    parser.add_argument('--auto-generate-missing', action='store_true',
                       help='Auto-generate missing essential plugins (no UI)')
    parser.add_argument('--headless', action='store_true',
                       help='Run without UI (for testing/automation)')
    
    args = parser.parse_args()
    
    # Handle plugin generation from path
    if args.plugin_generator:
        from app.workflow.universal_plugin_generator import PluginGenerator
        from pathlib import Path
        
        plugin_path = Path(args.plugin_generator)
        if not plugin_path.exists():
            print(f"[ERROR] Plugin path does not exist: {plugin_path}")
            sys.exit(1)
        
        print(f"[INFO] Generating plugin from: {plugin_path}")
        generator = PluginGenerator(output_dir="plugins")
        
        # Try to load plugin config from path
        config_file = plugin_path / "plugin_config.json"
        if config_file.exists():
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Loaded plugin configuration")
            # Non-interactive generation from config is not yet implemented
            # For now, run interactive mode even with config file
            generator.run_interactive()
        else:
            print("[INFO] No plugin_config.json found, running interactive mode")
            generator.run_interactive()
        
        sys.exit(0)
    
    # Handle auto-generation of missing plugins
    if args.auto_generate_missing:
        print("\n" + "="*60)
        print("AUTO-GENERATING MISSING PLUGINS")
        print("="*60)
        print("\nScanning for installed packages and generating plugins...\n")
        
        # Import all plugin managers
        from app.ocr.ocr_plugin_manager import OCRPluginManager
        from app.capture.capture_plugin_manager import CapturePluginManager
        from app.optimizers.optimizer_plugin_manager import OptimizerPluginManager
        from app.text_processors.text_processor_plugin_manager import TextProcessorPluginManager
        
        success_count = 0
        total_count = 0
        
        # OCR Plugins
        print("[1/4] Checking OCR plugins...")
        try:
            ocr_manager = OCRPluginManager()
            ocr_plugins = ocr_manager.discover_plugins()
            print(f"  ✓ Discovered {len(ocr_plugins)} OCR plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1
        
        # Capture Plugins
        print("[2/4] Checking Capture plugins...")
        try:
            capture_manager = CapturePluginManager()
            capture_plugins = capture_manager.discover_plugins()
            print(f"  ✓ Discovered {len(capture_plugins)} Capture plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1
        
        # Optimizer Plugins
        print("[3/4] Checking Optimizer plugins...")
        try:
            optimizer_manager = OptimizerPluginManager()
            optimizer_plugins = optimizer_manager.discover_plugins()
            print(f"  ✓ Discovered {len(optimizer_plugins)} Optimizer plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1
        
        # Text Processor Plugins
        print("[4/4] Checking Text Processor plugins...")
        try:
            text_proc_manager = TextProcessorPluginManager()
            text_proc_plugins = text_proc_manager.discover_plugins()
            print(f"  ✓ Discovered {len(text_proc_plugins)} Text Processor plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1
        
        print("\n" + "="*60)
        print(f"COMPLETE: {success_count}/{total_count} plugin types processed")
        print("="*60 + "\n")
        
        sys.exit(0 if success_count == total_count else 1)
    
    # Handle plugin generation
    if args.create_plugin:
        from app.workflow.universal_plugin_generator import PluginGenerator
        generator = PluginGenerator(output_dir="plugins")
        generator.run_interactive()
        sys.exit(0)
    
    # Handle headless mode
    if args.headless:
        print("[INFO] Running in headless mode (no UI)")
        print("[INFO] This mode is for testing/automation only")
        sys.exit(0)
    
    # Normal GUI mode
    sys.exit(main())
