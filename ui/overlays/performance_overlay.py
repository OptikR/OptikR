"""
Performance Overlay - On-Screen Performance Metrics Display

Shows real-time performance metrics as a lightweight, draggable,
always-on-top transparent overlay. Right-click to configure visible metrics.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import psutil
from app.localization import tr

logger = logging.getLogger(__name__)


class PerformanceOverlay(QWidget):
    """
    Transparent overlay window showing performance metrics.

    Features:
    - Configurable metrics (FPS, CPU, GPU, Memory, Latency, Accuracy)
    - Always on top, draggable, semi-transparent
    - Position and metric selection persisted to config
    - Right-click to configure, drag to move
    - Auto-updates every second (non-blocking)
    """

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = None

        # Load configuration
        self.visible_metrics = self._load_visible_metrics()

        # Cache total memory for percentage calculation
        try:
            self._total_memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        except Exception:
            self._total_memory_gb = 16.0

        # Setup window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Dragging state
        self.dragging = False
        self.drag_position = None

        # Initialize UI
        self.metric_labels = {}
        self._build_ui()

        # Load saved position
        self._load_position()

        # Start update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.start(1000)

    def _build_ui(self):
        """Build the overlay UI."""
        # Main container with semi-transparent background
        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 200);
                border: 2px solid rgba(74, 158, 255, 180);
                border-radius: 10px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(5)

        # Title
        title_label = QLabel("📊 Performance")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #4A9EFF; background: transparent;")
        container_layout.addWidget(title_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(74, 158, 255, 100);")
        separator.setFixedHeight(2)
        container_layout.addWidget(separator)

        # Metric labels
        self.metric_labels = {}
        metric_font = QFont("Consolas", 9)

        metrics = [
            ('fps', '📊 FPS'),
            ('cpu', '💻 CPU'),
            ('gpu', '🎮 GPU'),
            ('memory', '💾 Memory'),
            ('latency', '⏱️ Latency'),
            ('accuracy', '🎯 Accuracy'),
            ('translations', '🌐 Translations'),
            ('errors', '❌ Errors')
        ]

        active = self.visible_metrics if self.visible_metrics else self._ALL_METRIC_IDS
        for metric_id, metric_label in metrics:
            if metric_id in active:
                label = QLabel(f"{metric_label}: --")
                label.setFont(metric_font)
                label.setStyleSheet("color: #E0E0E0; background: transparent;")
                self.metric_labels[metric_id] = label
                container_layout.addWidget(label)

        # Hint
        hint_label = QLabel(tr("right_click_to_configure_drag_to_move"))
        hint_label.setStyleSheet("color: #888888; font-size: 8pt; background: transparent;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint_label)

        self.adjustSize()

    def set_pipeline(self, pipeline):
        """Set the pipeline reference for getting real metrics."""
        self.pipeline = pipeline

    def update_metrics(self):
        """Update displayed metrics with real system data."""
        try:
            # Non-blocking CPU % (returns average since last call)
            cpu = psutil.cpu_percent(interval=0)
            memory_info = psutil.virtual_memory()
            memory_gb = memory_info.used / (1024 ** 3)

            gpu = self._read_gpu_usage()

            # Pipeline metrics (if available)
            fps = 0.0
            latency = 0.0
            accuracy = 0.0
            translations = 0
            errors = 0

            if self.pipeline and hasattr(self.pipeline, 'get_metrics'):
                try:
                    metrics = self.pipeline.get_metrics()
                    fps = getattr(metrics, 'average_fps', 0.0)
                    latency = getattr(metrics, 'average_latency_ms', 0.0)
                    accuracy = getattr(metrics, 'average_accuracy', 0.0)
                    translations = getattr(metrics, 'total_translations', 0)
                    errors = getattr(metrics, 'total_errors', 0)
                except Exception:
                    pass

            # Update labels
            if 'fps' in self.metric_labels:
                self.metric_labels['fps'].setText(f"📊 FPS: {fps:.1f}")

            if 'cpu' in self.metric_labels:
                color = self._get_status_color(cpu, 75, 90)
                self.metric_labels['cpu'].setText(f"💻 CPU: {cpu:.1f}%")
                self.metric_labels['cpu'].setStyleSheet(f"color: {color}; background: transparent;")

            if 'gpu' in self.metric_labels:
                if gpu is None:
                    self.metric_labels['gpu'].setText("🎮 GPU: N/A")
                    self.metric_labels['gpu'].setStyleSheet("color: #888888; background: transparent;")
                else:
                    color = self._get_status_color(gpu, 80, 95)
                    self.metric_labels['gpu'].setText(f"🎮 GPU: {gpu:.1f}%")
                    self.metric_labels['gpu'].setStyleSheet(f"color: {color}; background: transparent;")

            if 'memory' in self.metric_labels:
                memory_percent = (memory_gb / self._total_memory_gb) * 100 if self._total_memory_gb > 0 else 0
                color = self._get_status_color(memory_percent, 75, 90)
                self.metric_labels['memory'].setText(f"💾 Memory: {memory_gb:.1f}GB")
                self.metric_labels['memory'].setStyleSheet(f"color: {color}; background: transparent;")

            if 'latency' in self.metric_labels:
                if fps > 0:
                    color = self._get_status_color(latency, 100, 200)
                    self.metric_labels['latency'].setText(f"⏱️ Latency: {latency:.0f}ms")
                    self.metric_labels['latency'].setStyleSheet(f"color: {color}; background: transparent;")
                else:
                    self.metric_labels['latency'].setText("⏱️ Latency: --")
                    self.metric_labels['latency'].setStyleSheet("color: #888888; background: transparent;")

            if 'accuracy' in self.metric_labels:
                if fps > 0:
                    color = self._get_status_color(100 - accuracy, 15, 25)
                    self.metric_labels['accuracy'].setText(f"🎯 Accuracy: {accuracy:.1f}%")
                    self.metric_labels['accuracy'].setStyleSheet(f"color: {color}; background: transparent;")
                else:
                    self.metric_labels['accuracy'].setText("🎯 Accuracy: --")
                    self.metric_labels['accuracy'].setStyleSheet("color: #888888; background: transparent;")

            if 'translations' in self.metric_labels:
                self.metric_labels['translations'].setText(f"🌐 Translations: {translations}")

            if 'errors' in self.metric_labels:
                color = "#E0E0E0" if errors == 0 else "#F44336"
                self.metric_labels['errors'].setText(f"❌ Errors: {errors}")
                self.metric_labels['errors'].setStyleSheet(f"color: {color}; background: transparent;")

        except Exception as e:
            logger.error("Failed to update overlay metrics: %s", e)

    @staticmethod
    def _read_gpu_usage():
        """Read GPU utilization via pynvml (NVML). Returns None on failure."""
        try:
            import pynvml
            pynvml.nvmlInit()
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                return float(util.gpu)
            finally:
                pynvml.nvmlShutdown()
        except Exception:
            pass
        return None

    @staticmethod
    def _get_status_color(value, warning_threshold, critical_threshold):
        """Get color based on value and thresholds."""
        if value >= critical_threshold:
            return "#F44336"  # Red
        elif value >= warning_threshold:
            return "#FF9800"  # Orange
        return "#4CAF50"  # Green

    _ALL_METRIC_IDS = frozenset(
        ('fps', 'cpu', 'gpu', 'memory', 'latency', 'accuracy', 'translations', 'errors')
    )

    def _load_visible_metrics(self):
        """Load which metrics should be visible.

        An empty set is treated as "show all" so the overlay is never blank.
        """
        if self.config_manager:
            loaded = set(self.config_manager.get_setting(
                'performance_overlay.visible_metrics',
                ['fps', 'cpu', 'gpu', 'memory']))
            return loaded if loaded else set(self._ALL_METRIC_IDS)
        return {'fps', 'cpu', 'gpu', 'memory'}

    def _save_visible_metrics(self):
        """Save which metrics are visible."""
        if self.config_manager:
            self.config_manager.set_setting(
                'performance_overlay.visible_metrics', list(self.visible_metrics))

    def _load_position(self):
        """Load overlay position from config."""
        if self.config_manager:
            x = self.config_manager.get_setting('performance_overlay.x', 50)
            y = self.config_manager.get_setting('performance_overlay.y', 50)
            self.move(x, y)

    def _save_position(self):
        """Save overlay position to config."""
        if self.config_manager:
            self.config_manager.set_setting('performance_overlay.x', self.x())
            self.config_manager.set_setting('performance_overlay.y', self.y())

    # --- Drag handling ---

    def mousePressEvent(self, event):
        """Handle mouse press for dragging or config menu."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_config_dialog()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release — save position."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self._save_position()
            event.accept()

    # --- Config dialog ---

    def _show_config_dialog(self):
        """Show metric selection dialog."""
        from PyQt6.QtWidgets import QDialog, QCheckBox, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("performance_overlay_settings"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        title = QLabel(tr("select_metrics_to_display"))
        title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(title)

        checkboxes = {}
        metrics = [
            ('fps', '📊 FPS'),
            ('cpu', '💻 CPU Usage'),
            ('gpu', '🎮 GPU Usage'),
            ('memory', '💾 Memory Usage'),
            ('latency', '⏱️ Translation Latency'),
            ('accuracy', '🎯 OCR Accuracy'),
            ('translations', '🌐 Translation Count'),
            ('errors', '❌ Error Count')
        ]

        for metric_id, metric_label in metrics:
            checkbox = QCheckBox(metric_label)
            checkbox.setChecked(metric_id in self.visible_metrics)
            checkboxes[metric_id] = checkbox
            layout.addWidget(checkbox)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton(tr("apply"))
        ok_btn.clicked.connect(lambda: self._apply_config(dialog, checkboxes))
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        dialog.exec()

    def _apply_config(self, dialog, checkboxes):
        """Apply configuration changes and rebuild UI."""
        self.visible_metrics = {
            metric_id for metric_id, cb in checkboxes.items() if cb.isChecked()
        }
        self._save_visible_metrics()
        self._rebuild_ui()
        dialog.accept()

    def _rebuild_ui(self):
        """Rebuild the UI with new metric selection."""
        # Remove old container
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                child = old_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            # Remove the layout itself
            from PyQt6.QtWidgets import QWidget as _QW
            _QW().setLayout(old_layout)

        # Rebuild
        self._build_ui()

    def closeEvent(self, event):
        """Handle close event — stop timer, save position."""
        self.update_timer.stop()
        self._save_position()
        event.accept()
