"""
Main Window for the application.

This module defines the main application window that coordinates all
major components through manager classes. It maintains a minimal
footprint by delegating responsibilities to specialized managers.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QShortcut, QKeySequence
from typing import TYPE_CHECKING
from app.localization import tr
from .ui_manager import UIManager
from .settings_coordinator import SettingsCoordinator

if TYPE_CHECKING:
    from app.workflow.startup_pipeline import StartupPipeline

logger = logging.getLogger(__name__)


@dataclass
class _WindowGeometry:
    x: int
    y: int
    width: int
    height: int
    min_width: int
    min_height: int


class MainWindow(QMainWindow):
    """
    Main application window (< 500 lines).
    
    Responsibilities:
    - Window lifecycle (initialization, show, close)
    - Component initialization and wiring
    - Event routing via signals/slots
    - Application-level state management
    
    The MainWindow acts as a minimal coordinator, delegating specific
    responsibilities to specialized manager classes:
    - UIManager: Handles all UI components
    - StartupPipeline: QObject integration layer for the translation pipeline
    - SettingsCoordinator: Handles settings operations
    - SystemTrayManager: Handles system tray (already exists)
    
    This design keeps the main window under 500 lines while maintaining
    all functionality of the original StyleTestWindow.
    """
    
    
    def __init__(self, config_manager=None):
        """
        Initialize the main window.
        
        Args:
            config_manager: The configuration manager instance
        
        This method:
        1. Creates manager instances
        2. Wires manager signals to slots
        3. Initializes the UI
        4. Loads initial configuration
        """
        super().__init__()
        
        # Store config manager
        self.config_manager = config_manager
        
        # Create manager instances
        self.ui_manager: UIManager | None = None
        self.startup_pipeline: 'StartupPipeline' | None = None
        self.settings_coordinator: SettingsCoordinator | None = None
        self.tray_manager = None  # Will be set during initialization
        
        # Metrics timer
        self.metrics_timer = None
        
        # Guard flag to prevent recursive language/engine validation
        self._validating_language = False
        
        # Periodic cache clear timer (every 6 hours while running)
        self._cache_clear_timer: QTimer | None = None
        self._pipeline_toggle_shortcut: QShortcut | None = None
        self._screenshot_shortcut: QShortcut | None = None
        self._recording_flash_shortcut: QShortcut | None = None
        self._vision_hotkey_in_progress = False

        # Initialize components
        self._init_managers()
        self._init_ui()
        self._wire_signals()
        self._load_initial_state()
        self._start_periodic_cache_timer()

    @property
    def pipeline(self):
        """Expose the pipeline instance for tabs and UI components."""
        return self.startup_pipeline

    @property
    def has_unsaved_changes(self) -> bool:
        """Single source of truth for unsaved changes, delegated to SettingsCoordinator."""
        if self.settings_coordinator:
            return self.settings_coordinator.has_unsaved_changes()
        return False
    
    def _init_managers(self) -> None:
        """
        Initialize all manager instances.
        
        Creates UIManager, SettingsCoordinator, and SystemTrayManager
        instances with appropriate configuration. The StartupPipeline is
        created later by PipelineLoader during _load_initial_state().
        """
        # Create UI Manager
        self.ui_manager = UIManager(
            config_manager=self.config_manager,
            parent=self
        )
        
        # StartupPipeline is loaded via PipelineLoader in _load_initial_state()
        
        # Create Settings Coordinator
        self.settings_coordinator = SettingsCoordinator(
            config_manager=self.config_manager,
            parent=self
        )
        
        # System tray manager will be created during UI initialization
        self._init_system_tray()
    
    def _init_system_tray(self) -> None:
        """Initialize system tray icon."""
        try:
            from ui.layout.system_tray import SystemTrayManager
            
            self.tray_manager = SystemTrayManager(self, self.config_manager)
            
            # Connect signals
            self.tray_manager.showRequested.connect(self._on_tray_show_requested)
            self.tray_manager.quitRequested.connect(self.quit_application)
            
            logger.info("System tray initialized")
            
        except Exception as e:
            logger.warning("System tray initialization failed: %s", e)
    
    def _init_ui(self) -> None:
        """
        Initialize the user interface.
        
        Sets up the main window UI including:
        - Window properties (title, size, position)
        - Central widget and layout
        - Toolbar (via UIManager)
        - Sidebar (via UIManager)
        - Tab widget (via UIManager)
        - System tray (if enabled)
        """
        if not self.config_manager:
            logger.error("Cannot initialize UI without config_manager")
            return

        # Get window settings from config
        window_x = self.config_manager.get_setting('ui.window_x', 100)
        window_y = self.config_manager.get_setting('ui.window_y', 50)
        window_width = self.config_manager.get_setting('ui.window_width', 1600)
        window_height = self.config_manager.get_setting('ui.window_height', 1050)
        min_width = self.config_manager.get_setting('ui.window_min_width', 1300)
        min_height = self.config_manager.get_setting('ui.window_min_height', 850)
        geometry = self._sanitize_window_geometry(
            window_x, window_y, window_width, window_height, min_width, min_height
        )
        
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(geometry.min_width, geometry.min_height)
        self.setGeometry(geometry.x, geometry.y, geometry.width, geometry.height)
        
        # Create central widget
        central_widget = QWidget()
        
        # Main horizontal layout (sidebar + content)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar via UIManager
        sidebar = self.ui_manager.create_sidebar(self)
        main_layout.addWidget(sidebar)
        
        # Create vertical layout for content + toolbar
        content_container = QWidget()
        content_container_layout = QVBoxLayout(content_container)
        content_container_layout.setContentsMargins(0, 0, 0, 0)
        content_container_layout.setSpacing(0)
        
        # Create tab widget for content
        from PyQt6.QtWidgets import QTabWidget
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        tab_widget.setUsesScrollButtons(True)
        
        # Create tabs via UIManager
        self.ui_manager.create_tabs(tab_widget)
        content_container_layout.addWidget(tab_widget, 1)
        
        # Create toolbar via UIManager
        toolbar = self.ui_manager.create_toolbar(self)
        content_container_layout.addWidget(toolbar)
        
        main_layout.addWidget(content_container, 1)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Status bar
        status_bar = self.statusBar()
        status_bar.showMessage(tr("status_system_ready"))
        status_bar.setStyleSheet("QStatusBar { font-size: 8pt; }")
        
        # Add version label to status bar
        from PyQt6.QtWidgets import QLabel
        version_label = QLabel(tr("version"))
        version_label.setStyleSheet("QLabel { font-size: 8pt; color: #95A5A6; padding-right: 10px; }")
        status_bar.addPermanentWidget(version_label)
        
        self._setup_shortcuts()

    def _sanitize_window_geometry(
        self, x, y, width, height, min_width, min_height
    ) -> _WindowGeometry:
        """Clamp window geometry to sane values and keep it on-screen."""
        def _as_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        x = _as_int(x, 100)
        y = _as_int(y, 50)
        width = _as_int(width, 1600)
        height = _as_int(height, 1050)
        min_width = max(_as_int(min_width, 1300), 900)
        min_height = max(_as_int(min_height, 850), 650)

        width = max(width, min_width)
        height = max(height, min_height)

        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        if screen:
            available = screen.availableGeometry()

            # Keep initial size within available screen area.
            width = min(width, max(available.width(), min_width))
            height = min(height, max(available.height(), min_height))

            # Ensure at least part of the window is visible.
            max_x = available.x() + max(available.width() - 120, 0)
            max_y = available.y() + max(available.height() - 120, 0)
            x = min(max(x, available.x()), max_x)
            y = min(max(y, available.y()), max_y)

        return _WindowGeometry(
            x=x, y=y, width=width, height=height, min_width=min_width, min_height=min_height
        )
    
    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts listed in the help dialog."""
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_all_settings)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_settings)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self.import_settings)
        QShortcut(QKeySequence("F1"), self).activated.connect(self._show_help)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._refresh_pipeline_dashboard)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.quit_application)
        self._register_pipeline_hotkey()
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.show_capture_region_selector)
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self.show_performance_monitor)
        self._register_screenshot_hotkey()
        self._register_recording_flash_hotkey()

    def _register_pipeline_hotkey(self) -> None:
        """Register (or re-register) the user-configured pipeline hotkey."""
        if self._pipeline_toggle_shortcut is not None:
            try:
                self._pipeline_toggle_shortcut.activated.disconnect(
                    self._on_pipeline_hotkey_triggered
                )
            except Exception:
                pass
            self._pipeline_toggle_shortcut.setParent(None)
            self._pipeline_toggle_shortcut.deleteLater()
            self._pipeline_toggle_shortcut = None

        hotkey = "Ctrl+T"
        if self.config_manager:
            hotkey = self.config_manager.get_setting(
                "general.pipeline_toggle_hotkey", "Ctrl+T"
            )
        hotkey = str(hotkey or "").strip() or "Ctrl+T"

        sequence = QKeySequence(hotkey)
        if sequence.isEmpty():
            hotkey = "Ctrl+T"
            sequence = QKeySequence(hotkey)

        self._pipeline_toggle_shortcut = QShortcut(sequence, self)
        self._pipeline_toggle_shortcut.activated.connect(
            self._on_pipeline_hotkey_triggered
        )
        logger.info("Registered pipeline hotkey: %s", hotkey)

    def _register_screenshot_hotkey(self) -> None:
        """Register (or re-register) the user-configured screenshot hotkey."""
        if self._screenshot_shortcut is not None:
            try:
                self._screenshot_shortcut.activated.disconnect(
                    self._take_screenshot_with_overlays
                )
            except Exception:
                pass
            self._screenshot_shortcut.setParent(None)
            self._screenshot_shortcut.deleteLater()
            self._screenshot_shortcut = None

        hotkey = "F9"
        if self.config_manager:
            hotkey = self.config_manager.get_setting(
                "general.screenshot_hotkey", "F9"
            )
        hotkey = str(hotkey or "").strip() or "F9"

        sequence = QKeySequence(hotkey)
        if sequence.isEmpty():
            hotkey = "F9"
            sequence = QKeySequence(hotkey)

        self._screenshot_shortcut = QShortcut(sequence, self)
        self._screenshot_shortcut.activated.connect(
            self._take_screenshot_with_overlays
        )
        logger.info("Registered screenshot hotkey: %s", hotkey)

    def _register_recording_flash_hotkey(self) -> None:
        """Register (or re-register) the recording flash hotkey."""
        if self._recording_flash_shortcut is not None:
            try:
                self._recording_flash_shortcut.activated.disconnect(
                    self._flash_overlays_for_recording
                )
            except Exception:
                pass
            self._recording_flash_shortcut.setParent(None)
            self._recording_flash_shortcut.deleteLater()
            self._recording_flash_shortcut = None

        hotkey = "F10"
        if self.config_manager:
            hotkey = self.config_manager.get_setting(
                "general.recording_flash_hotkey", "F10"
            )
        hotkey = str(hotkey or "").strip() or "F10"

        sequence = QKeySequence(hotkey)
        if sequence.isEmpty():
            hotkey = "F10"
            sequence = QKeySequence(hotkey)

        self._recording_flash_shortcut = QShortcut(sequence, self)
        self._recording_flash_shortcut.activated.connect(
            self._flash_overlays_for_recording
        )
        logger.info("Registered recording flash hotkey: %s", hotkey)

    def _flash_overlays_for_recording(self) -> None:
        """Show overlays to screen capture for 5 seconds (pipeline paused)."""
        if not self.startup_pipeline:
            self.statusBar().showMessage("Pipeline not initialized.", 2000)
            return

        duration = 5.0
        if self.config_manager:
            duration = self.config_manager.get_setting(
                "general.recording_flash_duration", 5.0
            )

        ok = self.startup_pipeline.flash_overlays_for_recording(duration)
        if ok:
            self.statusBar().showMessage(
                f"Recording: overlays visible for {duration:.0f}s (pipeline paused)", 
                int(duration * 1000),
            )
        else:
            self.statusBar().showMessage("Recording flash already active or no overlays.", 2000)

    def _on_pipeline_hotkey_triggered(self) -> None:
        """Handle pipeline hotkey with mode-aware behavior.

        - text/audio mode: toggle continuous pipeline
        - vision mode: run one-shot single-frame translation
        """
        mode = "text"
        if self.config_manager:
            mode = self.config_manager.get_setting("pipeline.mode", "text")

        if mode == "vision":
            self._trigger_vision_hotkey_single_frame()
            return

        self.toggle_translation()

    def _trigger_vision_hotkey_single_frame(self) -> None:
        """Run one vision frame in background to avoid UI freeze."""
        if not self.startup_pipeline:
            QMessageBox.critical(
                self,
                tr("start_failed"),
                tr("pipeline_not_initialized")
            )
            return

        if self._vision_hotkey_in_progress:
            self.statusBar().showMessage(
                "Vision hotkey is already processing a frame.",
                2000,
            )
            return

        self._vision_hotkey_in_progress = True
        self.statusBar().showMessage(
            "Vision hotkey: processing one frame...",
            2000,
        )

        def _worker():
            success = False
            count = 0
            error = ""
            try:
                success, count, error = self.startup_pipeline.run_vision_single_frame()
            except Exception as exc:
                error = str(exc)

            def _finish():
                self._vision_hotkey_in_progress = False
                if success:
                    self.statusBar().showMessage(
                        f"Vision single-frame complete ({count} block(s)).",
                        3000,
                    )
                else:
                    self.statusBar().showMessage(
                        f"Vision single-frame failed: {error}",
                        5000,
                    )

            QTimer.singleShot(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    def _take_screenshot_with_overlays(self) -> None:
        """Take a screenshot of the capture region with overlays visible."""
        logger.info("Screenshot hotkey triggered")
        if not self.startup_pipeline:
            self.statusBar().showMessage("Pipeline not initialized.", 2000)
            return

        self.statusBar().showMessage("Taking screenshot...", 2000)
        pixmap = self.startup_pipeline.capture_screenshot_with_overlays()
        if pixmap is None or pixmap.isNull():
            self.statusBar().showMessage("Screenshot failed — check logs.", 3000)
            return

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setPixmap(pixmap)

        import os, time as _time
        screenshots_dir = os.path.join("user_data", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        ts = _time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(screenshots_dir, f"optikr_{ts}.png")
        pixmap.save(path, "PNG")

        self.statusBar().showMessage(
            f"Screenshot saved to {path} and copied to clipboard.", 4000
        )
        logger.info("Screenshot with overlays saved: %s", path)

    def _show_help(self) -> None:
        """Show the help dialog (keyboard shortcut handler)."""
        if self.ui_manager:
            self.ui_manager.show_help()

    def _refresh_pipeline_dashboard(self) -> None:
        """Reload the Pipeline Dashboard tab to reflect current state."""
        if not self.ui_manager:
            return
        pipeline_tab = self.ui_manager.get_tab('pipeline')
        if pipeline_tab and hasattr(pipeline_tab, 'load_config'):
            pipeline_tab.load_config()
            self.statusBar().showMessage(tr("status_pipeline_refreshed"), 2000)

    def _wire_signals(self) -> None:
        """
        Wire signals between managers and main window.
        
        Connects signals from managers to appropriate slots to enable
        communication between components. This includes:
        - UI events -> Pipeline actions
        - Pipeline events -> UI updates (wired in _on_pipeline_loaded)
        - Settings events -> Component updates
        - System tray events -> Window actions
        """
        # Wire UI Manager signals
        if self.ui_manager:
            self.ui_manager.theme_toggled.connect(self._on_theme_toggled)
        
        # StartupPipeline signals are wired in _on_pipeline_loaded() once
        # PipelineLoader creates and returns the StartupPipeline instance.
        
        # Wire Settings Coordinator signals
        if self.settings_coordinator:
            self.settings_coordinator.settings_changed.connect(self._on_settings_changed)
            self.settings_coordinator.settings_saved.connect(self._on_settings_saved)
            self.settings_coordinator.settings_loaded.connect(self._on_settings_loaded)
            self.settings_coordinator.save_failed.connect(self._on_save_failed)
    
    def _load_initial_state(self) -> None:
        """
        Load initial application state.
        
        Loads configuration, restores window geometry, and initializes
        components to their saved state.
        """
        # Initialize pipeline synchronously via PipelineLoader
        self._init_pipeline()
        
        # Start metrics update timer for sidebar
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._update_sidebar_metrics)
        self.metrics_timer.start(1000)  # Update every 1 second

    def _start_periodic_cache_timer(self) -> None:
        """Start a background timer that re-checks periodic cache clearing every 6 hours."""
        self._cache_clear_timer = QTimer(self)
        self._cache_clear_timer.timeout.connect(self._run_periodic_cache_clear)
        self._cache_clear_timer.start(6 * 60 * 60 * 1000)  # 6 hours

    def _run_periodic_cache_clear(self) -> None:
        """Slot called by the periodic timer to clear stale cache files."""
        try:
            from app.utils.periodic_cache_cleaner import run_periodic_clear
            run_periodic_clear(self.config_manager)
        except Exception as e:
            logger.debug("Periodic cache clear error: %s", e)

    def _init_pipeline(self) -> None:
        """
        Initialize the translation pipeline synchronously via PipelineLoader.

        Creates a PipelineLoader, runs it in the main thread (to avoid
        Qt/OpenCV conflicts), and stores the resulting StartupPipeline.
        """
        from .pipeline_loader import PipelineLoader

        self.statusBar().showMessage(tr("status_loading_ocr"))
        QApplication.processEvents()

        logger.info("Starting pipeline initialization in MAIN thread...")

        loader = PipelineLoader(self.config_manager)

        pipeline_result = [None]
        error_result = [None]

        def capture_finished(pipeline):
            pipeline_result[0] = pipeline

        def capture_error(error):
            error_result[0] = error

        loader.finished.connect(capture_finished)
        loader.error.connect(capture_error)
        loader.progress.connect(lambda msg: self.statusBar().showMessage(msg))

        try:
            loader.run()
        except Exception as e:
            logger.error("Exception during pipeline initialization: %s", e)
            logger.exception(e)
            error_result[0] = str(e)

        if error_result[0]:
            logger.error("Pipeline initialization failed: %s", error_result[0])
            self._on_pipeline_error(str(error_result[0]))
        elif pipeline_result[0]:
            logger.info("Pipeline initialization completed successfully")
            self._on_pipeline_loaded(pipeline_result[0])
        else:
            logger.warning("Pipeline initialization completed but no result")
            self._on_pipeline_error(tr("no_pipeline_returned"))

    def _on_pipeline_loaded(self, pipeline) -> None:
        """
        Handle pipeline loaded event from PipelineLoader.

        Stores the StartupPipeline, wires its Qt signals, restores the
        capture region from config, warms up components, and notifies UI.
        """
        self.startup_pipeline = pipeline

        # Wire StartupPipeline Qt signals to MainWindow slots
        self.startup_pipeline.pipeline_started.connect(self._on_pipeline_started)
        self.startup_pipeline.pipeline_stopped.connect(self._on_pipeline_stopped)
        self.startup_pipeline.pipeline_error.connect(self._on_pipeline_error)

        # Track current OCR engine
        try:
            self.startup_pipeline._current_ocr_engine = (
                self.startup_pipeline.get_current_ocr_engine()
            )
        except Exception as e:
            logger.debug("Could not track current OCR engine: %s", e)

        # Restore capture region from config so the pipeline has it on startup
        self._restore_capture_region_from_config()

        # Warm up components for faster first translation
        self.statusBar().showMessage(tr("status_warming_up"))
        QApplication.processEvents()
        self.startup_pipeline.warm_up_components()

        # Notify UI
        self._on_pipeline_loaded_complete()

    def _restore_capture_region_from_config(self) -> None:
        """Restore the capture region from saved config so the pipeline has it on startup."""
        if not self.config_manager or not self.startup_pipeline:
            return
        try:
            region_type = self.config_manager.get_setting('capture.region', 'full_screen')
            if region_type == 'custom':
                cr = self.config_manager.get_setting('capture.custom_region', None)
                if cr and isinstance(cr, dict):
                    monitor_id = self.config_manager.get_setting('capture.monitor_index', 0)
                    self.startup_pipeline.set_capture_region(
                        x=cr.get('x', 0), y=cr.get('y', 0),
                        width=cr.get('width', 800), height=cr.get('height', 600),
                        monitor_id=monitor_id,
                    )
                    logger.info("Restored capture region from config: %s (monitor %s)", cr, monitor_id)

            overlay_region = self.config_manager.get_setting('overlay.region', None)
            if overlay_region and isinstance(overlay_region, dict):
                sp = self.startup_pipeline
                if hasattr(sp, 'pipeline') and sp.pipeline and hasattr(sp.pipeline, 'config'):
                    sp.pipeline.config.overlay_region = overlay_region
                    logger.info("Restored overlay region from config: %s", overlay_region)
        except Exception as e:
            logger.warning("Could not restore capture region from config: %s", e)
    
    def _update_sidebar_metrics(self) -> None:
        """Update sidebar metrics with real-time system data."""
        if self.ui_manager and self.ui_manager.get_sidebar():
            self.ui_manager.update_sidebar_metrics()
    
    def _on_theme_toggled(self, theme_name: str) -> None:
        """
        Handle theme toggle event.
        
        Args:
            theme_name: Name of the new theme
        """
        # Theme switching is handled by UIManager
        self.statusBar().showMessage(tr("status_switched_theme", theme=theme_name), 2000)
    
    def _on_pipeline_started(self) -> None:
        """
        Handle pipeline started event.
        
        Updates UI to reflect that the pipeline is running.
        """
        self.statusBar().showMessage(tr("status_translation_running"))

        # Snapshot dictionary stats so we can compute a session delta on stop
        self._session_start_learned_count = 0
        if self.startup_pipeline:
            self._session_start_learned_count = (
                self.startup_pipeline.get_session_learned_count()
            )
        
        # Update start button if available
        toolbar = self.ui_manager.get_toolbar()
        if toolbar:
            start_btn = toolbar.get_start_button()
            if start_btn:
                start_btn.setText(tr("btn_stop"))
                start_btn.setStyleSheet("background-color: #E74C3C; color: white;")
    
    def _on_pipeline_stopped(self) -> None:
        """
        Handle pipeline stopped event.
        
        Updates UI to reflect that the pipeline has stopped and performs cleanup.
        """
        self.statusBar().showMessage(tr("status_system_ready"))
        
        # Update start button if available
        toolbar = self.ui_manager.get_toolbar()
        if toolbar:
            start_btn = toolbar.get_start_button()
            if start_btn:
                start_btn.setText(tr("btn_start"))
                start_btn.setStyleSheet("background-color: #27AE60; color: white;")

        # Post-session dictionary save prompt (skip during app shutdown)
        if not getattr(self, '_closing', False):
            self._show_dictionary_save_prompt()
    
    def _show_dictionary_save_prompt(self) -> None:
        """Show a save prompt if the Smart Dictionary learned entries during this session."""
        if not self.startup_pipeline:
            return

        total_learned = self.startup_pipeline.get_session_learned_count()
        baseline = getattr(self, '_session_start_learned_count', 0)
        learned_this_session = total_learned - baseline

        if learned_this_session <= 0:
            return

        from ui.dialogs.dictionary_save_dialog import show_dictionary_save_dialog

        saved = show_dictionary_save_dialog(
            parent=self,
            startup_pipeline=self.startup_pipeline,
            learned_count=learned_this_session,
        )

        if saved:
            self.statusBar().showMessage(
                tr("status_dictionary_saved", count=learned_this_session),
                3000,
            )

    def _on_pipeline_error(self, error_message: str) -> None:
        """
        Handle pipeline error event.
        
        Args:
            error_message: Description of the error
        
        Displays error to user and updates UI appropriately.
        """
        # Log the error
        logger.error("Pipeline error: %s", error_message)
        
        # Notify user
        QMessageBox.critical(
            self,
            tr("pipeline_error"),
            tr("pipeline_error_msg", error=error_message)
        )
        self.statusBar().showMessage(tr("status_pipeline_error"), 5000)
    
    def _on_pipeline_loaded_complete(self) -> None:
        """Handle pipeline loaded event."""
        self.statusBar().showMessage(tr("status_pipeline_ready"), 2000)
        logger.info("Pipeline loaded successfully")
        
        # Update sidebar status and OCR engine display
        self.update_sidebar_ocr_display()
        sidebar = self.ui_manager.get_sidebar() if self.ui_manager else None
        if sidebar:
            sidebar.update_status(tr("sidebar_ready"), "ready")
        
        # Reload pipeline-dependent tabs that were created before pipeline was ready
        if self.ui_manager:
            for tab_name in ("dictionary_context", "pipeline", "storage"):
                if self.ui_manager.is_tab_loaded(tab_name):
                    self.ui_manager.reload_tab(tab_name)
            self.ui_manager._wire_perf_overlay_pipeline()

        # Start periodic translation cache save (every 5 minutes)
        self._cache_save_timer = QTimer(self)
        self._cache_save_timer.timeout.connect(self._auto_save_translation_cache)
        self._cache_save_timer.start(5 * 60 * 1000)

    def _auto_save_translation_cache(self) -> None:
        """Periodically persist the translation cache to disk."""
        if self.startup_pipeline:
            self.startup_pipeline.save_translation_cache()

    def update_sidebar_ocr_display(self) -> None:
        """Update sidebar OCR engine label from runtime state."""
        sidebar = self.ui_manager.get_sidebar() if self.ui_manager else None
        if not sidebar:
            return

        engine_name = None

        # Try runtime pipeline first (most accurate)
        if self.startup_pipeline:
            try:
                engine_name = self.startup_pipeline.get_current_ocr_engine()
            except Exception as e:
                logger.debug("Failed to read runtime OCR engine: %s", e)

        # Fallback to config
        if (not engine_name or engine_name == "unknown") and self.config_manager:
            engine_name = self.config_manager.get_setting('ocr.engine', 'easyocr')

        if engine_name:
            sidebar.update_ocr_engine(engine_name)
    
    def _on_settings_saved(self, success: bool) -> None:
        """
        Handle settings saved event.
        
        Args:
            success: True if save was successful, False otherwise
        
        Clears unsaved changes flag and updates UI with confirmation.
        """
        if not success:
            return
        
        # Update save button if available
        toolbar = self.ui_manager.get_toolbar()
        if toolbar:
            save_btn = toolbar.get_save_button()
            if save_btn:
                save_btn.setEnabled(False)
                save_btn.setToolTip(tr("no_unsaved_changes"))
        
        # Sync sidebar with saved settings
        self._sync_sidebar_languages()
        self.update_sidebar_ocr_display()
        self._register_pipeline_hotkey()
        self._register_screenshot_hotkey()
        self._register_recording_flash_hotkey()

        # Show confirmation message
        QMessageBox.information(
            self,
            tr("settings_saved"),
            tr("all_settings_have_been_saved_successfully")
        )
    
    def _on_settings_changed(self, key: str = "", value: object = None) -> None:
        """
        Handle settings changed event from SettingsCoordinator signal.

        Updates the toolbar save button to reflect unsaved state.
        Change tracking itself lives in SettingsCoordinator (single source of truth).
        """
        # Update save button if available
        toolbar = self.ui_manager.get_toolbar()
        if toolbar:
            save_btn = toolbar.get_save_button()
            if save_btn:
                save_btn.setEnabled(True)
                save_btn.setToolTip(tr("save_all_settings"))
    
    def _on_settings_loaded(self) -> None:
        """
        Handle settings loaded event.
        
        Updates UI to reflect the loaded settings. This is called when
        settings are reloaded from disk or imported from a file.
        """
        # Update save button if available
        toolbar = self.ui_manager.get_toolbar()
        if toolbar:
            save_btn = toolbar.get_save_button()
            if save_btn:
                save_btn.setEnabled(False)
                save_btn.setToolTip(tr("no_unsaved_changes"))
        
        # Update UI components to reflect loaded settings
        if self.ui_manager:
            # Sync sidebar with loaded settings
            self._sync_sidebar_languages()
        self._register_pipeline_hotkey()
        self._register_screenshot_hotkey()
        self._register_recording_flash_hotkey()

        # Update status bar
        self.statusBar().showMessage(tr("status_settings_loaded"), 2000)
    
    
    def _on_save_failed(self, errors: list) -> None:
        """
        Handle save failed event.
        
        Args:
            errors: List of error messages
        
        Displays error dialog to user with detailed information.
        """
        error_text = "\n\n".join(errors)
        QMessageBox.critical(
            self,
            tr("save_failed"),
            tr("save_failed_msg", errors=error_text)
        )
    
    def _on_tray_show_requested(self) -> None:
        """Handle show window request from system tray."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def quit_application(self) -> None:
        """Quit the application."""
        QApplication.quit()
    
    def toggle_translation(self) -> None:
        """Toggle translation pipeline on/off."""
        if not self.startup_pipeline:
            QMessageBox.critical(
                self,
                tr("start_failed"),
                tr("pipeline_not_initialized")
            )
            return
        try:
            self.startup_pipeline.toggle()
        except Exception as e:
            QMessageBox.critical(
                self,
                tr("start_failed"),
                tr("failed_to_start", error=str(e))
            )
    
    def save_all_settings(self) -> None:
        """Save all settings via SettingsCoordinator."""
        success, errors = self.settings_coordinator.save_all()
        # Signals will handle UI updates
    
    def import_settings(self) -> None:
        """Import settings from file."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Show warning
        reply = QMessageBox.warning(
            self,
            tr("import_settings"),
            tr("importing_settings_will_overwrite_your_current_configuration"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Get file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("import_settings"),
            "",
            tr("json_files_filter")
        )
        
        if not file_path:
            return
        
        # Import via coordinator
        success, error_msg = self.settings_coordinator.import_settings(file_path)
        
        if success:
            QMessageBox.information(
                self,
                tr("import_successful"),
                tr("settings_imported_msg", path=file_path)
            )
        else:
            QMessageBox.critical(
                self,
                tr("import_failed"),
                tr("failed_to_import_msg", error=error_msg)
            )
    
    def export_settings(self) -> None:
        """Export settings to file."""
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        
        # Get file path
        default_name = f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("export_settings_title"),
            default_name,
            tr("json_files_filter")
        )
        
        if not file_path:
            return
        
        # Export via coordinator
        success, error_msg = self.settings_coordinator.export_settings(file_path)
        
        if success:
            QMessageBox.information(
                self,
                tr("export_successful"),
                tr("settings_exported_msg", path=file_path)
            )
        else:
            QMessageBox.critical(
                self,
                tr("export_failed"),
                tr("failed_to_export_msg", error=error_msg)
            )
    
    def closeEvent(self, event) -> None:
        """
        Handle window close event.
        
        Args:
            event: The close event
        
        This method:
        1. Checks for unsaved changes
        2. Prompts user if needed
        3. Saves window state
        4. Cleans up resources
        5. Accepts or rejects the close event
        """
        # Guard: suppress post-session dictionary prompt during shutdown
        # (cleanup will save dictionaries automatically)
        self._closing = True
        
        # Check for unsaved changes
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                tr("unsaved_changes"),
                tr("you_have_unsaved_changes_do_you_want_to_save_before_closing_2"),
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
        
        # Save window state
        self._save_window_state()
        
        # Cleanup
        self._cleanup_on_exit()
        
        # Accept the event
        event.accept()
    
    def _save_window_state(self) -> None:
        """
        Save window geometry and state.
        
        Saves window size, position, and other state information
        to configuration for restoration on next launch.
        """
        if self.config_manager:
            geometry = self.geometry()
            self.config_manager.set_setting('ui.window_x', geometry.x())
            self.config_manager.set_setting('ui.window_y', geometry.y())
            self.config_manager.set_setting('ui.window_width', geometry.width())
            self.config_manager.set_setting('ui.window_height', geometry.height())
            self.config_manager.save_config()
    
    def _cleanup_on_exit(self) -> None:
        """
        Clean up resources before exit.

        Delegates pipeline cleanup to StartupPipeline, then handles
        local resources (timer, tray, config).
        """
        # Stop periodic timers before cleanup
        if hasattr(self, '_cache_save_timer') and self._cache_save_timer:
            self._cache_save_timer.stop()
        if self._cache_clear_timer:
            self._cache_clear_timer.stop()

        # Delegate all pipeline cleanup (stop, overlay, cache) to StartupPipeline
        # (StartupPipeline.cleanup() persists the translation cache first)
        if self.startup_pipeline:
            try:
                self.startup_pipeline.cleanup()
            except Exception as e:
                logger.warning("Failed to cleanup startup pipeline: %s", e)

        # Stop metrics timer
        if self.metrics_timer:
            self.metrics_timer.stop()

        # Cleanup system tray icon (Bug 1.11)
        if self.tray_manager:
            try:
                self.tray_manager.cleanup()
            except Exception as e:
                logger.warning("Failed to cleanup system tray: %s", e)

        # Cleanup config manager (Bug 1.11)
        if self.config_manager:
            try:
                if hasattr(self.config_manager, 'cleanup'):
                    self.config_manager.cleanup()
                elif hasattr(self.config_manager, 'close'):
                    self.config_manager.close()
            except Exception as e:
                logger.warning("Failed to cleanup config manager: %s", e)

    
    def on_settings_changed(self) -> None:
        """
        Called when any setting changes in tabs.

        This method is connected to tab settingChanged signals and
        notifies the SettingsCoordinator of changes. We always mark
        as changed when any tab emits so the save button enables
        reliably (e.g. after changing OCR/translation engine or other
        values). Then we sync the coordinator flag with actual state.
        """
        self.settings_coordinator.mark_changed()
        self.settings_coordinator.check_for_changes()
    
    def _sync_sidebar_languages(self) -> None:
        """
        Sync sidebar language display with current settings.
        
        Reads from the General tab combos if available, otherwise from config.
        """
        sidebar = self.ui_manager.get_sidebar() if self.ui_manager else None
        if not sidebar:
            return

        lang_map = getattr(sidebar, 'language_map', {})

        # Try to read from General tab combos first (they may have unsaved changes)
        general_tab = self.ui_manager.get_tab('general') if self.ui_manager else None

        if general_tab and hasattr(general_tab, 'source_lang_combo') and general_tab.source_lang_combo:
            sidebar.set_source_language(general_tab.source_lang_combo.currentText())
        else:
            source_code = self.config_manager.get_setting('translation.source_language', 'en')
            sidebar.set_source_language(lang_map.get(source_code, source_code.upper()))

        if general_tab and hasattr(general_tab, 'target_lang_combo') and general_tab.target_lang_combo:
            sidebar.set_target_language(general_tab.target_lang_combo.currentText())
        else:
            target_code = self.config_manager.get_setting('translation.target_language', 'de')
            sidebar.set_target_language(lang_map.get(target_code, target_code.upper()))

    # ── Bidirectional language / engine validation ─────────────────────

    def _on_source_language_changed(self, language_name: str) -> None:
        """Validate OCR + translation engine when the user changes source language."""
        if self._validating_language:
            return
        self._validating_language = True
        try:
            from ui.settings.language_engine_validator import (
                LANG_NAME_TO_CODE, LANG_CODE_TO_NAME, LanguageEngineValidator,
            )

            src_code = LANG_NAME_TO_CODE.get(language_name, language_name.lower()[:2])
            if src_code == 'auto':
                return

            validator = LanguageEngineValidator()

            # 1) Validate OCR engine
            current_ocr = self.config_manager.get_setting('ocr.engine', 'easyocr')
            ocr_result = validator.validate_ocr_engine(src_code, current_ocr)

            if not ocr_result.is_compatible and ocr_result.recommended_engine:
                lang_list = ', '.join(
                    LANG_CODE_TO_NAME.get(c, c) for c in ocr_result.engine_languages
                )
                rec_display = ocr_result.recommended_engine.replace('_', ' ').title()

                QMessageBox.information(
                    self,
                    tr("ocr_compat_title"),
                    tr("ocr_compat_msg", engine=current_ocr, languages=lang_list,
                       language=language_name, recommended=rec_display)
                )

                self.config_manager.set_setting('ocr.engine', ocr_result.recommended_engine)

                ocr_tab = self.ui_manager.get_tab('ocr') if self.ui_manager else None
                if ocr_tab:
                    ocr_tab.update_current_engine_display(ocr_result.recommended_engine)
                    ocr_tab._set_language_lock(False)

                general_tab = self.ui_manager.get_tab('general') if self.ui_manager else None
                if general_tab:
                    general_tab.set_language_lock(False)

                self.update_sidebar_ocr_display()

            # 2) Validate translation engine
            self._validate_translation_engine_for_pair()
        except Exception as exc:
            logger.warning("Language validation error: %s", exc, exc_info=True)
        finally:
            self._validating_language = False

    def _on_target_language_changed(self, _language_name: str) -> None:
        """Validate translation engine when the user changes target language."""
        if self._validating_language:
            return
        self._validating_language = True
        try:
            self._validate_translation_engine_for_pair()
        except Exception as exc:
            logger.warning("Translation engine validation error: %s", exc, exc_info=True)
        finally:
            self._validating_language = False

    def _validate_translation_engine_for_pair(self) -> None:
        """Check if the current translation engine supports the active language pair."""
        from ui.settings.language_engine_validator import (
            LANG_NAME_TO_CODE, LANG_CODE_TO_NAME, LanguageEngineValidator,
        )

        general_tab = self.ui_manager.get_tab('general') if self.ui_manager else None
        if general_tab and general_tab.source_lang_combo:
            src_name = general_tab.source_lang_combo.currentText()
            tgt_name = general_tab.target_lang_combo.currentText()
        else:
            src_code = self.config_manager.get_setting('translation.source_language', 'en')
            tgt_code = self.config_manager.get_setting('translation.target_language', 'de')
            src_name = LANG_CODE_TO_NAME.get(src_code, src_code)
            tgt_name = LANG_CODE_TO_NAME.get(tgt_code, tgt_code)

        src_code = LANG_NAME_TO_CODE.get(src_name, src_name.lower()[:2])
        tgt_code = LANG_NAME_TO_CODE.get(tgt_name, tgt_name.lower()[:2])

        current_engine = self.config_manager.get_setting(
            'translation.engine', 'marianmt_gpu'
        )

        validator = LanguageEngineValidator()
        result = validator.validate_translation_engine(src_code, tgt_code, current_engine)

        if result.is_compatible:
            if result.needs_model_download:
                QMessageBox.information(
                    self,
                    tr("trans_model_required_title"),
                    tr("trans_model_required_msg", src=src_name, tgt=tgt_name)
                )
            return

        if result.recommended_engine:
            rec_display = result.recommended_engine.replace('_', ' ').title()
            compat_display = ', '.join(
                e.replace('_', ' ').title() for e in result.compatible_engines[:5]
            )

            QMessageBox.information(
                self,
                tr("trans_compat_title"),
                tr("trans_compat_msg",
                   engine=current_engine.replace('_', ' ').title(),
                   src=src_name, tgt=tgt_name,
                   engines=compat_display, recommended=rec_display)
            )

            self.config_manager.set_setting(
                'translation.engine', result.recommended_engine
            )

            trans_tab = self.ui_manager.get_tab('translation') if self.ui_manager else None
            if trans_tab and hasattr(trans_tab, 'engine_section'):
                radio = trans_tab.engine_section.plugin_radios.get(
                    result.recommended_engine
                )
                if radio:
                    radio.setChecked(True)

    def _on_ocr_engine_changed(self, engine_name: str) -> None:
        """Handle OCR engine change — constrain source language if needed."""
        if self._validating_language:
            return
        self._validating_language = True
        try:
            from ui.settings.language_engine_validator import (
                LANG_NAME_TO_CODE, LANG_CODE_TO_NAME, LanguageEngineValidator,
            )

            validator = LanguageEngineValidator()
            supported = validator.get_constrained_languages_for_ocr(engine_name)

            general_tab = self.ui_manager.get_tab('general') if self.ui_manager else None
            sidebar = self.ui_manager.get_sidebar() if self.ui_manager else None

            if supported is None:
                if general_tab:
                    general_tab.set_language_lock(False)
                if sidebar:
                    sidebar.set_language_lock(False)
                self._validate_translation_engine_for_pair()
                return

            # Determine current source language
            if general_tab and general_tab.source_lang_combo:
                src_name = general_tab.source_lang_combo.currentText()
            else:
                src_code = self.config_manager.get_setting(
                    'translation.source_language', 'en'
                )
                src_name = LANG_CODE_TO_NAME.get(src_code, src_code)

            src_code = LANG_NAME_TO_CODE.get(src_name, src_name.lower()[:2])

            if len(supported) == 1:
                # Single-language OCR engine — config is set by OCR tab,
                # but ensure the General tab + sidebar reflect the change
                # (OCR tab's parent-walk may miss the main window).
                lang_code = supported[0]
                from ui.settings.language_engine_validator import LANG_CODE_TO_NAME as _C2N
                lang_name = _C2N.get(lang_code, lang_code.upper())

                if general_tab and general_tab.source_lang_combo:
                    idx = general_tab.source_lang_combo.findText(lang_name)
                    if idx >= 0:
                        general_tab.source_lang_combo.blockSignals(True)
                        general_tab.source_lang_combo.setCurrentIndex(idx)
                        general_tab.source_lang_combo.blockSignals(False)
                    general_tab.set_language_lock(True)

                if sidebar:
                    sidebar.set_source_language(lang_name)
                    sidebar.set_language_lock(True)

                self._sync_sidebar_languages()
                self._validate_translation_engine_for_pair()
                return

            if src_code not in supported:
                recommended_lang = 'en' if 'en' in supported else supported[0]
                rec_name = LANG_CODE_TO_NAME.get(recommended_lang, recommended_lang)

                supported_names = [
                    LANG_CODE_TO_NAME.get(c, c) for c in supported[:10]
                ]
                suffix = '...' if len(supported) > 10 else ''

                QMessageBox.information(
                    self,
                    tr("ocr_lang_title"),
                    tr("ocr_lang_msg", engine=engine_name, language=src_name,
                       supported=', '.join(supported_names) + suffix,
                       recommended=rec_name)
                )

                self.config_manager.set_setting(
                    'translation.source_language', recommended_lang
                )

                if general_tab and general_tab.source_lang_combo:
                    idx = general_tab.source_lang_combo.findText(rec_name)
                    if idx >= 0:
                        general_tab.source_lang_combo.blockSignals(True)
                        general_tab.source_lang_combo.setCurrentIndex(idx)
                        general_tab.source_lang_combo.blockSignals(False)
                    general_tab.set_language_lock(False)

                if sidebar:
                    sidebar.set_source_language(rec_name)
                    sidebar.set_language_lock(False)
            else:
                if general_tab:
                    general_tab.set_language_lock(False)
                if sidebar:
                    sidebar.set_language_lock(False)

            self._validate_translation_engine_for_pair()
        except Exception as exc:
            logger.warning("OCR engine change validation error: %s", exc, exc_info=True)
        finally:
            self._validating_language = False

    # ── End language / engine validation ─────────────────────────────────

    def show_capture_region_selector(self) -> None:
        """Show the capture region selector dialog."""
        try:
            from ui.capture import CaptureRegionSelectorDialog

            selector = CaptureRegionSelectorDialog(parent=self, config_manager=self.config_manager)
            if selector.exec():
                config = selector.get_configuration()
                active_regions = config.get('active_regions', [])

                # Persist overlay region to config so the preview picks it up
                overlay_region = config.get('overlay_region')
                if self.config_manager:
                    if overlay_region:
                        self.config_manager.set_setting('overlay.region', overlay_region)
                    # Also persist capture region to config
                    if active_regions:
                        ar = active_regions[0]
                        cr = ar.get('capture_region', {})
                        self.config_manager.set_setting('capture.region', 'custom')
                        self.config_manager.set_setting('capture.custom_region', cr)
                        self.config_manager.set_setting('capture.monitor_index', ar.get('monitor_index', 0))
                    self.config_manager.save_config()

                if len(active_regions) > 1 and hasattr(self, 'pipeline') and self.pipeline:
                    # Multiple presets selected — build MultiRegionConfig for the pipeline
                    from app.models import MultiRegionConfig, CaptureRegion, Rectangle
                    mr_config = MultiRegionConfig()
                    for i, ar in enumerate(active_regions):
                        cr = ar['capture_region']
                        region = CaptureRegion(
                            rectangle=Rectangle(
                                x=cr.get('x', 0), y=cr.get('y', 0),
                                width=cr.get('width', 800), height=cr.get('height', 600),
                            ),
                            monitor_id=ar.get('monitor_index', 0),
                            region_id=f"preset_{i}",
                            enabled=True,
                            name=ar.get('preset', f'Region {i+1}'),
                        )
                        mr_config.add_region(region)
                    self.pipeline.set_multi_region_config(mr_config)
                elif active_regions and hasattr(self, 'pipeline') and self.pipeline:
                    # Single region — use the simple path
                    ar = active_regions[0]
                    cr = ar['capture_region']
                    self.pipeline.set_capture_region(
                        x=cr.get('x', 0), y=cr.get('y', 0),
                        width=cr.get('width', 800), height=cr.get('height', 600),
                        monitor_id=ar.get('monitor_index', 0),
                    )

                # Push overlay region to running pipeline so it takes effect immediately
                if overlay_region and self.pipeline and hasattr(self.pipeline, 'pipeline'):
                    runtime = self.pipeline.pipeline
                    if runtime and hasattr(runtime, 'config'):
                        runtime.config.overlay_region = overlay_region
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("capture_region_selector"),
                tr("could_not_open_msg", dialog=tr("capture_region_selector"), error=str(e))
            )

    def show_performance_monitor(self) -> None:
        """Show the performance monitor window."""
        try:
            self.ui_manager.show_performance_monitor()
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("performance_monitor"),
                tr("could_not_open_msg", dialog=tr("performance_monitor"), error=str(e))
            )

    def show_quick_ocr_switch(self) -> None:
        """Show the quick OCR engine switch dialog."""
        try:
            from ui.dialogs.quick_ocr_switch_dialog import show_quick_ocr_switch_dialog
            ocr_tab = self.ui_manager.get_tab('ocr') if self.ui_manager else None
            show_quick_ocr_switch_dialog(
                config_manager=self.config_manager,
                ocr_tab=ocr_tab,
                pipeline=self.startup_pipeline,
                parent=self,
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("quick_ocr_switch"),
                tr("could_not_open_msg", dialog=tr("quick_ocr_switch"), error=str(e))
            )
    def _on_preset_loaded(self, preset_name: str) -> None:
        """Handle preset loaded from sidebar."""
        self.statusBar().showMessage(tr("status_preset_loaded", name=preset_name), 3000)
        if self.settings_coordinator:
            self.settings_coordinator.mark_changed()

    def _on_content_mode_changed(self, mode: str) -> None:
        """Handle content mode change from sidebar (static/dynamic).
        
        Propagates the change to the running pipeline's frame skip optimizer
        so it takes effect immediately without restarting.
        """
        mode_labels = {'static': tr("content_mode_static"), 'dynamic': tr("content_mode_dynamic")}
        self.statusBar().showMessage(tr("status_content_mode", mode=mode_labels.get(mode, mode)), 3000)
        
        # Propagate to running runtime pipeline
        if self.startup_pipeline:
            runtime = self.startup_pipeline.pipeline
            if runtime and hasattr(runtime, 'frame_skip') and runtime.frame_skip:
                if hasattr(runtime.frame_skip, 'configure'):
                    runtime.frame_skip.configure({'content_mode': mode})
                    logger.info("Content mode changed to '%s' on running pipeline", mode)
        
        if self.settings_coordinator:
            self.settings_coordinator.mark_changed()

    def _on_pipeline_mode_changed(self, mode: str) -> None:
        """Handle pipeline mode change from sidebar (text/vision/audio).

        Stops the current pipeline if running, recreates it with the new
        preset via StartupPipeline.set_pipeline_mode(), and updates the UI.
        """
        mode_tr_keys = {
            'text': 'pipeline_mode_text',
            'vision': 'pipeline_mode_vision',
            'audio': 'pipeline_mode_audio',
        }
        display = tr(mode_tr_keys.get(mode, mode))
        self.statusBar().showMessage(tr("pipeline_mode_changed", mode=display), 3000)

        if self.startup_pipeline:
            success = self.startup_pipeline.set_pipeline_mode(mode)
            if not success:
                logger.warning("Failed to switch pipeline mode to '%s'", mode)
                QMessageBox.warning(
                    self,
                    tr("pipeline_error"),
                    tr("pipeline_mode_switch_failed", mode=mode),
                )
            else:
                self.update_sidebar_ocr_display()
        else:
            if self.config_manager:
                self.config_manager.set_setting('pipeline.mode', mode)
                self.config_manager.save_config()

        # Notify settings tabs so they can react (e.g. disable text-mode-only
        # controls when vision mode is active).
        if self.settings_coordinator:
            try:
                self.settings_coordinator.notify_setting_changed(
                    'pipeline.mode', mode, source_tab=''
                )
            except Exception:
                logger.debug("Failed to broadcast pipeline.mode change to settings tabs", exc_info=True)

        if self.settings_coordinator:
            self.settings_coordinator.mark_changed()


