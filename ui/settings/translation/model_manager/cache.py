"""
Cache management tab and cleanup logic.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QFormLayout, QMessageBox
)
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox


class CacheMixin:
    """Cache management tab creation and cleanup."""

    def _create_cache_management_tab(self, manager, cache_info):
        """Create the cache management tab."""
        cache_tab = QWidget()
        cache_layout = QVBoxLayout(cache_tab)
        cache_layout.setContentsMargins(10, 10, 10, 10)
        cache_layout.setSpacing(15)

        # Cache statistics
        stats_group = QGroupBox("Cache Statistics")
        stats_layout = QVBoxLayout(stats_group)

        stats_text = f"""Cache Directory: {cache_info['cache_directory']}
Total Models: {cache_info['total_models']}
Downloaded Models: {cache_info['downloaded_models']}
Optimized Models: {cache_info['optimized_models']}
Total Cache Size: {cache_info['total_size_mb']:.1f} MB
Available Disk Space: {cache_info['available_space_gb']:.1f} GB
Device: {cache_info['device'].upper()}"""

        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("font-family: monospace; font-size: 9pt;")
        stats_layout.addWidget(stats_label)

        cache_layout.addWidget(stats_group)

        # Cache cleanup
        cleanup_group = QGroupBox("Cache Cleanup")
        cleanup_layout = QFormLayout(cleanup_group)

        age_spin = CustomSpinBox()
        age_spin.setRange(1, 365)
        age_spin.setValue(30)
        age_spin.setSuffix("days")
        cleanup_layout.addRow("Remove models older than:", age_spin)

        size_spin = CustomDoubleSpinBox()
        size_spin.setRange(1.0, 100.0)
        size_spin.setValue(10.0)
        size_spin.setSingleStep(0.5)
        size_spin.setSuffix("GB")
        cleanup_layout.addRow("Maximum cache size:", size_spin)

        cleanup_btn = QPushButton("🧹 Clean Cache")
        cleanup_btn.setProperty("class", "action")
        cleanup_btn.clicked.connect(lambda: self._cleanup_cache(self.parent, manager, age_spin.value(), size_spin.value(), None))
        cleanup_layout.addRow("", cleanup_btn)

        cache_layout.addWidget(cleanup_group)
        cache_layout.addStretch()

        return cache_tab

    def _cleanup_cache(self, parent_dialog, manager, max_age_days, max_size_gb, refresh_callback):
        """Clean up the cache based on criteria."""
        reply = QMessageBox.question(
            parent_dialog,
            "Confirm Cleanup",
            "Clean up cache based on the specified criteria?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = manager.cleanup_cache(max_age_days=max_age_days, max_size_gb=max_size_gb)
                msg = f"Cache cleanup completed!\n\n"
                msg += f"Models deleted: {len(result['deleted_models'])}\n"
                msg += f"Space freed: {result['freed_space_mb']:.1f} MB\n"
                msg += f"Remaining models: {result['total_models']}"
                QMessageBox.information(parent_dialog, "Cleanup Complete", msg)
                if refresh_callback:
                    refresh_callback()
            except Exception as e:
                QMessageBox.critical(parent_dialog, "Error", f"Cleanup failed:\n{str(e)}")
