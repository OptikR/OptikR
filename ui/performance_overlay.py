"""
Performance Overlay - On-Screen Performance Metrics Display

Shows real-time performance metrics as an overlay on the screen.
User can configure which metrics to display.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import psutil


class PerformanceOverlay(QWidget):
    """
    Transparent overlay window showing performance metrics.
    
    Features:
    - Configurable metrics (FPS, CPU, GPU, Memory, Latency, Accuracy)
    - Always on top
    - Draggable
    - Semi-transparent background
    - Auto-updates every second
    """
    
    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = None  # Will be set by parent
        
        # Load configuration
        self.visible_metrics = self._load_visible_metrics()
        self.update_interval = 1000  # 1 second
        
        # Setup window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Make draggable
        self.dragging = False
        self.drag_position = None
        
        # Initialize UI
        self.init_ui()
        
        # Load position
        self._load_position()
        
        # Start update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.start(self.update_interval)
    
    def init_ui(self):
        """Initialize the UI."""
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
        
        # Container layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(5)
        
        # Title
        title_label = QLabel("📊 Performance")
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #4A9EFF; background: transparent;")
        container_layout.addWidget(title_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(74, 158, 255, 100);")
        separator.setFixedHeight(2)
        container_layout.addWidget(separator)
        
        # Metrics labels
        self.metric_labels = {}
        
        metric_font = QFont("Consolas", 9)
        
        # Create labels for all possible metrics
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
        
        for metric_id, metric_label in metrics:
            if metric_id in self.visible_metrics:
                label = QLabel(f"{metric_label}: --")
                label.setFont(metric_font)
                label.setStyleSheet("color: #E0E0E0; background: transparent;")
                self.metric_labels[metric_id] = label
                container_layout.addWidget(label)
        
        # Close hint
        hint_label = QLabel("Right-click to configure • Drag to move")
        hint_label.setStyleSheet("color: #888888; font-size: 8pt; background: transparent;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint_label)
        
        # Adjust size
        self.adjustSize()
    
    def set_pipeline(self, pipeline):
        """Set the pipeline reference for getting real metrics."""
        self.pipeline = pipeline
    
    def update_metrics(self):
        """Update displayed metrics."""
        try:
            # Get system metrics
            cpu = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            memory_gb = memory_info.used / (1024 ** 3)
            
            # Try to get GPU
            gpu = 0.0
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0].load * 100
            except:
                pass
            
            # Get pipeline metrics if available
            fps = 0.0
            latency = 0.0
            accuracy = 0.0
            translations = 0
            errors = 0
            
            if self.pipeline and hasattr(self.pipeline, 'get_metrics'):
                try:
                    metrics = self.pipeline.get_metrics()
                    fps = getattr(metrics, 'average_fps', 0.0)
                    latency = getattr(metrics, 'average_latency', 0.0)
                    accuracy = getattr(metrics, 'average_accuracy', 0.0)
                    translations = getattr(metrics, 'translation_count', 0)
                    errors = getattr(metrics, 'error_count', 0)
                except:
                    pass
            
            # Update labels
            if 'fps' in self.metric_labels:
                self.metric_labels['fps'].setText(f"📊 FPS: {fps:.1f}")
            
            if 'cpu' in self.metric_labels:
                color = self._get_status_color(cpu, 75, 90)
                self.metric_labels['cpu'].setText(f"💻 CPU: {cpu:.1f}%")
                self.metric_labels['cpu'].setStyleSheet(f"color: {color}; background: transparent;")
            
            if 'gpu' in self.metric_labels:
                color = self._get_status_color(gpu, 80, 95)
                self.metric_labels['gpu'].setText(f"🎮 GPU: {gpu:.1f}%")
                self.metric_labels['gpu'].setStyleSheet(f"color: {color}; background: transparent;")
            
            if 'memory' in self.metric_labels:
                memory_percent = (memory_gb / (psutil.virtual_memory().total / (1024 ** 3))) * 100
                color = self._get_status_color(memory_percent, 75, 90)
                self.metric_labels['memory'].setText(f"💾 Memory: {memory_gb:.1f}GB")
                self.metric_labels['memory'].setStyleSheet(f"color: {color}; background: transparent;")
            
            if 'latency' in self.metric_labels:
                if fps > 0:
                    color = self._get_status_color(latency, 100, 200)
                    self.metric_labels['latency'].setText(f"⏱️ Latency: {latency:.0f}ms")
                    self.metric_labels['latency'].setStyleSheet(f"color: {color}; background: transparent;")
                else:
                    self.metric_labels['latency'].setText(f"⏱️ Latency: --")
                    self.metric_labels['latency'].setStyleSheet("color: #888888; background: transparent;")
            
            if 'accuracy' in self.metric_labels:
                if fps > 0:
                    color = self._get_status_color(100 - accuracy, 15, 25)  # Inverted (lower is better)
                    self.metric_labels['accuracy'].setText(f"🎯 Accuracy: {accuracy:.1f}%")
                    self.metric_labels['accuracy'].setStyleSheet(f"color: {color}; background: transparent;")
                else:
                    self.metric_labels['accuracy'].setText(f"🎯 Accuracy: --")
                    self.metric_labels['accuracy'].setStyleSheet("color: #888888; background: transparent;")
            
            if 'translations' in self.metric_labels:
                self.metric_labels['translations'].setText(f"🌐 Translations: {translations}")
            
            if 'errors' in self.metric_labels:
                color = "#E0E0E0" if errors == 0 else "#F44336"
                self.metric_labels['errors'].setText(f"❌ Errors: {errors}")
                self.metric_labels['errors'].setStyleSheet(f"color: {color}; background: transparent;")
        
        except Exception as e:
            print(f"[ERROR] Failed to update overlay metrics: {e}")
    
    def _get_status_color(self, value, warning_threshold, critical_threshold):
        """Get color based on value and thresholds."""
        if value >= critical_threshold:
            return "#F44336"  # Red
        elif value >= warning_threshold:
            return "#FF9800"  # Orange
        else:
            return "#4CAF50"  # Green
    
    def _load_visible_metrics(self):
        """Load which metrics should be visible."""
        if self.config_manager:
            return set(self.config_manager.get_setting('performance_overlay.visible_metrics', 
                                                       ['fps', 'cpu', 'gpu', 'memory']))
        return {'fps', 'cpu', 'gpu', 'memory'}
    
    def _save_visible_metrics(self):
        """Save which metrics are visible."""
        if self.config_manager:
            self.config_manager.set_setting('performance_overlay.visible_metrics', list(self.visible_metrics))
    
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
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_config_menu()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self._save_position()
            event.accept()
    
    def show_config_menu(self):
        """Show configuration menu."""
        from PyQt6.QtWidgets import QMenu, QDialog, QVBoxLayout, QCheckBox, QPushButton, QLabel
        
        # Create configuration dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Performance Overlay Settings")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Title
        title = QLabel("Select metrics to display:")
        title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(title)
        
        # Checkboxes for each metric
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
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(lambda: self._apply_config(dialog, checkboxes))
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _apply_config(self, dialog, checkboxes):
        """Apply configuration changes."""
        # Update visible metrics
        self.visible_metrics = {metric_id for metric_id, checkbox in checkboxes.items() if checkbox.isChecked()}
        
        # Save to config
        self._save_visible_metrics()
        
        # Rebuild UI
        self._rebuild_ui()
        
        dialog.accept()
    
    def _rebuild_ui(self):
        """Rebuild the UI with new metric selection."""
        # Clear existing layout
        layout = self.container.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Rebuild
        self.init_ui()
    
    def closeEvent(self, event):
        """Handle close event."""
        self.update_timer.stop()
        self._save_position()
        event.accept()
