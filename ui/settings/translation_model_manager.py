"""
Translation Model Manager
Handles AI model management including MarianMT, NLLB, M2M-100, and mBART.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QComboBox, QMessageBox, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QSpinBox, QDoubleSpinBox, QTabWidget, QWidget, QFormLayout, QGroupBox,
    QProgressDialog, QApplication, QListWidgetItem
)
from PyQt6.QtCore import Qt
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox
import threading
import json
from pathlib import Path
from datetime import datetime


class TranslationModelManager:
    """Manages translation AI models."""
    
    def __init__(self, parent=None, config_manager=None):
        """Initialize the model manager."""
        self.parent = parent
        self.config_manager = config_manager
    
    def show_marianmt_manager(self):
        """Show Universal Translation Model Manager dialog."""
        # Create dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("🤖 Universal Translation Model Manager")
        dialog.setMinimumSize(1000, 700)
        dialog.resize(1000, 700)
        
        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Initialize model manager (Universal - supports multiple model types)
        try:
            from app.translation.universal_model_manager import create_universal_model_manager
            # Start with MarianMT as default
            current_model_type = "marianmt"
            manager = create_universal_model_manager(model_type=current_model_type)
        except ImportError:
            # Try backward compatibility import
            try:
                from app.translation.universal_model_manager import create_marianmt_model_manager
                manager = create_marianmt_model_manager()
            except ImportError:
                # Try alternative import path
                try:
                    import sys
                    import os
                    import importlib.util
                    
                    # Direct import to avoid dependency issues
                    manager_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'translation', 'universal_model_manager.py')
                    spec = importlib.util.spec_from_file_location("universal_model_manager", manager_path)
                    model_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(model_module)
                    
                    manager = model_module.create_universal_model_manager(model_type="marianmt")
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    QMessageBox.critical(
                        self.parent,
                        "Error",
                        f"Failed to initialize model manager:\n{str(e)}\n\nDetails:\n{error_details[:200]}"
                    )
                    return
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to initialize model manager:\n{str(e)}\n\nDetails:\n{error_details[:200]}"
            )
            return
        
        # Header with model type selector
        header_layout = QVBoxLayout()
        
        # Title row
        title_row = QHBoxLayout()
        title_label = QLabel("🤖 Universal Translation Model Manager")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        # Model type selector row
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Model Type:"))
        
        model_type_combo = QComboBox()
        model_type_combo.addItem("MarianMT (Helsinki-NLP)", "marianmt")
        model_type_combo.addItem("NLLB-200 (Meta AI)", "nllb")
        model_type_combo.addItem("M2M-100 (Facebook)", "m2m100")
        model_type_combo.addItem("mBART (Facebook)", "mbart")
        model_type_combo.setCurrentIndex(0)  # Default to MarianMT
        model_type_combo.setMinimumWidth(250)
        selector_row.addWidget(model_type_combo)
        
        # Cache info
        cache_info = manager.get_cache_info()
        info_text = f"Device: {cache_info['device'].upper()} | Downloaded: {cache_info['downloaded_models']}/{cache_info['total_models']} | Space: {cache_info['available_space_gb']:.1f}GB"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        selector_row.addWidget(info_label)
        selector_row.addStretch()
        
        header_layout.addLayout(selector_row)
        main_layout.addLayout(header_layout)
        
        # Store references for model type changes
        refresh_models_func = [None]  # Use list to allow modification in nested function
        manager_ref = [manager]  # Store manager in list so it can be updated
        
        # Tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Tab 1: Available Models
        available_tab = self._create_available_models_tab(manager_ref, refresh_models_func)
        tab_widget.addTab(available_tab, "Available Models")
        
        # Tab 2: Cache Management
        cache_tab = self._create_cache_management_tab(manager_ref[0], cache_info)
        tab_widget.addTab(cache_tab, "Cache Management")
        
        # Model type change handler
        def on_model_type_changed(index):
            """Handle model type change - update manager and refresh."""
            new_model_type = model_type_combo.itemData(index)
            
            # Create new manager for the selected model type
            from app.translation.universal_model_manager import create_universal_model_manager
            new_manager = create_universal_model_manager(model_type=new_model_type)
            
            # Update the manager reference
            manager_ref[0] = new_manager
            
            # Refresh the models tree if the function is available
            if refresh_models_func[0]:
                refresh_models_func[0]()
        
        model_type_combo.currentIndexChanged.connect(on_model_type_changed)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "action")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
    
    def _create_available_models_tab(self, manager_ref, refresh_models_func=None):
        """Create the available models tab.
        
        Args:
            manager_ref: List containing the manager (allows updating the reference)
            refresh_models_func: List to store the refresh function
        """
        available_tab = QWidget()
        manager = manager_ref[0]  # Get initial manager
        available_layout = QVBoxLayout(available_tab)
        available_layout.setContentsMargins(10, 10, 10, 10)
        available_layout.setSpacing(10)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        filter_layout.addWidget(QLabel("Source:"))
        source_combo = QComboBox()
        source_combo.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru"])
        filter_layout.addWidget(source_combo)
        
        filter_layout.addWidget(QLabel("Target:"))
        target_combo = QComboBox()
        target_combo.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru"])
        filter_layout.addWidget(target_combo)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("class", "action")
        filter_layout.addWidget(refresh_btn)
        
        filter_layout.addStretch()
        available_layout.addLayout(filter_layout)
        
        # Models tree
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels(["Languages", "Model Name", "Size", "BLEU Score", "Status", "Optimized"])
        models_tree.setColumnWidth(0, 120)
        models_tree.setColumnWidth(1, 250)
        models_tree.setColumnWidth(2, 80)
        models_tree.setColumnWidth(3, 80)
        models_tree.setColumnWidth(4, 120)
        models_tree.setColumnWidth(5, 80)
        models_tree.setAlternatingRowColors(True)
        available_layout.addWidget(models_tree)
        
        def refresh_models():
            """Refresh the models tree."""
            models_tree.clear()
            
            # Get current manager from reference (allows dynamic updates)
            current_manager = manager_ref[0]
            
            # Get filtered models
            src = None if source_combo.currentText() == "All" else source_combo.currentText()
            tgt = None if target_combo.currentText() == "All" else target_combo.currentText()
            models = current_manager.get_available_models(source_lang=src, target_lang=tgt)
            
            # Populate tree
            for model in models:
                status = "✓ Downloaded" if model.is_downloaded else "Available"
                optimized = "✓" if model.is_optimized else ""
                
                # Format language display based on model type
                if model.source_language == "multilingual":
                    # Multilingual model
                    lang_display = f"Multilingual ({model.languages_count} languages)"
                else:
                    # Bilingual model
                    lang_display = f"{model.source_language.upper()} → {model.target_language.upper()}"
                
                item = QTreeWidgetItem([
                    lang_display,
                    model.model_name,
                    f"{model.size_mb} MB",
                    f"{model.accuracy_bleu:.1f}",
                    status,
                    optimized
                ])
                models_tree.addTopLevelItem(item)
        
        refresh_btn.clicked.connect(refresh_models)
        source_combo.currentTextChanged.connect(refresh_models)
        target_combo.currentTextChanged.connect(refresh_models)
        
        # Store refresh function for model type changes
        if refresh_models_func is not None:
            refresh_models_func[0] = refresh_models
            # Initial refresh
            refresh_models()
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        download_pairs_btn = QPushButton("📦 Download Model")
        download_pairs_btn.setProperty("class", "action")
        
        def on_download_click():
            """Handle download button click based on model type."""
            if manager.get_model_type() == "marianmt":
                self._download_language_pairs(self.parent, manager, refresh_models)
            else:
                # For multilingual models, show the new downloader
                self.show_multilingual_model_downloader(manager, manager.get_model_type())
                refresh_models()  # Refresh after download
        
        download_pairs_btn.clicked.connect(on_download_click)
        action_layout.addWidget(download_pairs_btn)
        
        download_selected_btn = QPushButton("⬇ Download Selected")
        download_selected_btn.setProperty("class", "action")
        download_selected_btn.clicked.connect(lambda: self._download_selected_model(self.parent, manager, models_tree, refresh_models))
        action_layout.addWidget(download_selected_btn)
        
        optimize_btn = QPushButton("⚡ Optimize")
        optimize_btn.setProperty("class", "action")
        optimize_btn.clicked.connect(lambda: self._optimize_selected_model(self.parent, manager, models_tree, refresh_models))
        action_layout.addWidget(optimize_btn)
        
        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setProperty("class", "action")
        delete_btn.clicked.connect(lambda: self._delete_selected_model(self.parent, manager, models_tree, refresh_models))
        action_layout.addWidget(delete_btn)
        
        action_layout.addStretch()
        
        # Discover custom models button
        discover_btn = QPushButton("🔍 Discover Custom Models")
        discover_btn.setProperty("class", "action")
        discover_btn.setToolTip("Scan models folder for custom models and create plugins")
        discover_btn.clicked.connect(lambda: self._discover_custom_models(self.parent, manager, refresh_models))
        action_layout.addWidget(discover_btn)
        
        available_layout.addLayout(action_layout)
        
        # Initial load
        refresh_models()
        
        return available_tab
    
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
    
    def _download_language_pairs(self, parent_dialog, manager, refresh_callback):
        """Show dialog to select and download specific language pairs."""
        # Create dialog
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("📦 Download Language Pairs")
        dialog.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Select Language Pairs to Download")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Select one or more language pairs to download from HuggingFace.\n"
            "Each model is approximately 280-330 MB."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by source:"))
        source_filter = QComboBox()
        source_filter.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru", "ar", "nl", "pl", "tr", "ko", "pt"])
        filter_layout.addWidget(source_filter)
        
        filter_layout.addWidget(QLabel("Filter by target:"))
        target_filter = QComboBox()
        target_filter.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru", "ar", "nl", "pl", "tr", "ko", "pt"])
        filter_layout.addWidget(target_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Language pairs list
        pairs_list = QListWidget()
        pairs_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        def populate_pairs():
            """Populate the pairs list based on filters."""
            pairs_list.clear()
            
            src_filter = None if source_filter.currentText() == "All" else source_filter.currentText()
            tgt_filter = None if target_filter.currentText() == "All" else target_filter.currentText()
            
            # Get all available pairs
            all_pairs = manager.get_language_pairs()
            
            for src, tgt, desc in sorted(all_pairs, key=lambda x: x[2]):
                # Apply filters
                if src_filter and src != src_filter:
                    continue
                if tgt_filter and tgt != tgt_filter:
                    continue
                
                # Check if already downloaded
                lang_pair = f"{src}-{tgt}"
                model_name = manager.AVAILABLE_MODELS.get(lang_pair, {}).get("name", "")
                is_downloaded = manager.is_model_downloaded(model_name)
                
                status = "✓ Downloaded" if is_downloaded else "Available"
                item_text = f"{desc} ({src} → {tgt}) - {status}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, (src, tgt))
                
                if is_downloaded:
                    item.setForeground(Qt.GlobalColor.darkGray)
                
                pairs_list.addItem(item)
        
        source_filter.currentTextChanged.connect(populate_pairs)
        target_filter.currentTextChanged.connect(populate_pairs)
        
        layout.addWidget(pairs_list)
        
        # Info label
        info_label = QLabel("💡 Select multiple pairs and download them in batch")
        info_label.setStyleSheet("color: #666666; font-size: 8pt;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(pairs_list.selectAll)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(pairs_list.clearSelection)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        download_btn = QPushButton("Download Selected")
        download_btn.setProperty("class", "action")
        download_btn.setDefault(True)
        download_btn.clicked.connect(lambda: self._start_batch_download(dialog, pairs_list, manager, refresh_callback))
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
        
        # Initial population
        populate_pairs()
        
        dialog.exec()
    
    def _start_batch_download(self, dialog, pairs_list, manager, refresh_callback):
        """Start batch download of selected language pairs."""
        selected_items = pairs_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "No Selection", "Please select at least one language pair to download.")
            return
        
        # Extract language pairs
        pairs = []
        for item in selected_items:
            src, tgt = item.data(Qt.ItemDataRole.UserRole)
            pairs.append((src, tgt))
        
        # Confirm download
        total_size = len(pairs) * 300  # Approximate size per model
        reply = QMessageBox.question(
            dialog,
            "Confirm Download",
            f"Download {len(pairs)} language pair(s)?\n\n"
            f"Approximate total size: {total_size} MB\n"
            f"This may take several minutes depending on your connection.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Show progress dialog
        progress = QProgressDialog(
            "Downloading language pairs...",
            "Cancel",
            0,
            len(pairs),
            dialog
        )
        progress.setWindowTitle("Batch Download")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        def do_batch_download():
            try:
                results = {}
                for idx, (src, tgt) in enumerate(pairs):
                    if progress.wasCanceled():
                        break
                    
                    progress.setLabelText(f"Downloading {src} → {tgt}...")
                    progress.setValue(idx)
                    QApplication.processEvents()
                    
                    lang_pair = f"{src}-{tgt}"
                    model_name = manager.AVAILABLE_MODELS.get(lang_pair, {}).get("name", "")
                    
                    if model_name:
                        success = manager.download_model(model_name)
                        results[lang_pair] = success
                
                progress.setValue(len(pairs))
                progress.close()
                
                # Show results
                successful = sum(1 for v in results.values() if v)
                failed = len(results) - successful
                
                msg = f"Download complete!\n\n"
                msg += f"✓ Successful: {successful}\n"
                if failed > 0:
                    msg += f"✗ Failed: {failed}\n"
                
                QMessageBox.information(dialog, "Download Complete", msg)
                
                if refresh_callback:
                    refresh_callback()
                
                dialog.accept()
                
            except Exception as e:
                progress.close()
                QMessageBox.critical(dialog, "Error", f"Batch download failed:\n{str(e)}")
        
        threading.Thread(target=do_batch_download, daemon=True).start()
    
    def _download_selected_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Download the selected model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "No Selection", "Please select a model to download.")
            return
        
        model_name = selected_items[0].text(1)
        
        # Show progress dialog
        progress = QProgressDialog(
            f"Downloading {model_name}...",
            None,
            0,
            0,
            parent_dialog
        )
        progress.setWindowTitle("Downloading Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        def do_download():
            try:
                success = manager.download_model(model_name)
                progress.close()
                
                if success:
                    QMessageBox.information(parent_dialog, "Success", f"Model {model_name} downloaded successfully!")
                    refresh_callback()
                else:
                    QMessageBox.critical(parent_dialog, "Error", f"Failed to download model {model_name}")
            except Exception as e:
                progress.close()
                QMessageBox.critical(parent_dialog, "Error", f"Download failed:\n{str(e)}")
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def _optimize_selected_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Optimize the selected model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "No Selection", "Please select a model to optimize.")
            return
        
        model_name = selected_items[0].text(1)
        
        if not manager.is_model_downloaded(model_name):
            QMessageBox.warning(parent_dialog, "Not Downloaded", "Please download the model first.")
            return
        
        # Show progress
        progress = QProgressDialog(
            f"Optimizing {model_name}...",
            None,
            0,
            0,
            parent_dialog
        )
        progress.setWindowTitle("Optimizing Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        def do_optimize():
            try:
                result = manager.optimize_model(model_name)
                progress.close()
                
                if result.success:
                    msg = f"Model optimized successfully!\n\n"
                    msg += f"Size reduction: {result.original_size_mb:.1f}MB → {result.optimized_size_mb:.1f}MB\n"
                    msg += f"Speed improvement: {result.speed_improvement:.1f}x\n"
                    msg += f"Memory saved: {result.memory_reduction_mb:.1f}MB"
                    QMessageBox.information(parent_dialog, "Success", msg)
                    refresh_callback()
                else:
                    QMessageBox.critical(parent_dialog, "Error", f"Optimization failed:\n{result.error_message}")
            except Exception as e:
                progress.close()
                QMessageBox.critical(parent_dialog, "Error", f"Optimization failed:\n{str(e)}")
        
        threading.Thread(target=do_optimize, daemon=True).start()
    
    def _delete_selected_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Delete the selected model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "No Selection", "Please select a model to delete.")
            return
        
        model_name = selected_items[0].text(1)
        
        if not manager.is_model_downloaded(model_name):
            QMessageBox.information(parent_dialog, "Not Downloaded", "This model is not downloaded.")
            return
        
        reply = QMessageBox.question(
            parent_dialog,
            "Confirm Delete",
            f"Delete model {model_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if manager.delete_model(model_name):
                    QMessageBox.information(parent_dialog, "Success", f"Model {model_name} deleted successfully!")
                    refresh_callback()
                else:
                    QMessageBox.critical(parent_dialog, "Error", "Failed to delete model")
            except Exception as e:
                QMessageBox.critical(parent_dialog, "Error", f"Delete failed:\n{str(e)}")
    
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
    
    def add_marianmt_language_pair(self, model_list_widget):
        """Show dialog to add a new MarianMT language pair."""
        # Create dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("➕ Add MarianMT Language Pair")
        dialog.setMinimumSize(600, 500)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Select Language Pairs to Add")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Select one or more language pairs to add to your configuration.\n"
            "Only available MarianMT models are shown."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Get currently configured language pairs
        current_pairs = set()
        for i in range(model_list_widget.count()):
            item_text = model_list_widget.item(i).text()
            if "(" in item_text and ")" in item_text:
                lang_code = item_text.split("(")[1].split(")")[0]
                current_pairs.add(lang_code)
        
        # All available MarianMT language pairs
        all_available_pairs = self._get_available_marianmt_pairs()
        
        # Filter out already configured pairs
        available_pairs = {k: v for k, v in all_available_pairs.items() if k not in current_pairs}
        
        if not available_pairs:
            QMessageBox.information(
                dialog,
                "All Pairs Added",
                "All available MarianMT language pairs are already in your configuration!"
            )
            dialog.reject()
            return
        
        # Language pair list
        pair_list = QListWidget()
        pair_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Add available pairs sorted by name
        for lang_code, lang_name in sorted(available_pairs.items(), key=lambda x: x[1]):
            item_text = f"{lang_name} ({lang_code})"
            pair_list.addItem(item_text)
        
        layout.addWidget(pair_list)
        
        # Info label
        info_label = QLabel(f"💡 {len(available_pairs)} language pairs available to add")
        info_label.setStyleSheet("color: #666666; font-size: 8pt;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add Selected")
        add_btn.setProperty("class", "action")
        add_btn.setDefault(True)
        add_btn.clicked.connect(lambda: self._confirm_add_language_pairs(dialog, pair_list, available_pairs, model_list_widget))
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _confirm_add_language_pairs(self, dialog, pair_list, available_pairs, model_list_widget):
        """Confirm and add selected language pairs."""
        selected_items = pair_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(dialog, "No Selection", "Please select at least one language pair to add.")
            return
        
        # Extract language codes
        added_pairs = []
        for item in selected_items:
            item_text = item.text()
            if "(" in item_text and ")" in item_text:
                lang_code = item_text.split("(")[1].split(")")[0]
                lang_name = item_text.split(" (")[0]
                added_pairs.append((lang_code, lang_name))
        
        # Add to the model list
        for lang_code, lang_name in added_pairs:
            model_list_widget.addItem(f"{lang_name} ({lang_code})")
        
        # Update configuration
        self._update_translation_config_with_new_pairs(added_pairs)
        
        QMessageBox.information(
            dialog,
            "Language Pairs Added",
            f"✅ Successfully added {len(added_pairs)} language pair(s)!"
        )
        
        dialog.accept()
    
    def _update_translation_config_with_new_pairs(self, new_pairs):
        """Update translation_config.json with new language pairs."""
        try:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'translation_config.json'
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if 'marianmt' not in config:
                    config['marianmt'] = {}
                if 'models' not in config['marianmt']:
                    config['marianmt']['models'] = {}
                
                for lang_code, lang_name in new_pairs:
                    config['marianmt']['models'][lang_code] = {
                        "model_name": f"opus-mt-{lang_code}",
                        "downloaded": False,
                        "optimized": False
                    }
                
                config['last_updated'] = datetime.now().isoformat()
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                print(f"[INFO] Added {len(new_pairs)} language pairs to translation_config.json")
        except Exception as e:
            print(f"[ERROR] Failed to update translation config: {e}")
    
    def _get_available_marianmt_pairs(self):
        """Get all available MarianMT language pairs."""
        return {
            "en-de": "English → German", "de-en": "German → English",
            "en-es": "English → Spanish", "es-en": "Spanish → English",
            "en-fr": "English → French", "fr-en": "French → English",
            "en-it": "English → Italian", "it-en": "Italian → English",
            "en-pt": "English → Portuguese", "pt-en": "Portuguese → English",
            "en-ja": "English → Japanese", "ja-en": "Japanese → English",
            "en-zh": "English → Chinese", "zh-en": "Chinese → English",
            "en-ko": "English → Korean", "ko-en": "Korean → English",
            "en-ru": "English → Russian", "ru-en": "Russian → English",
        }

    
    def show_multilingual_model_downloader(self, manager, model_type="nllb"):
        """
        Show dialog to download multilingual models (NLLB, M2M-100, mBART).
        
        Args:
            manager: UniversalModelManager instance
            model_type: Type of model ("nllb", "m2m100", "mbart")
        """
        # Create dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(f"📦 Download {model_type.upper()} Model")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        model_names = {
            "nllb": "NLLB-200 (Meta AI)",
            "m2m100": "M2M-100 (Facebook)",
            "mbart": "mBART (Facebook)"
        }
        title = QLabel(f"Download {model_names.get(model_type, model_type.upper())} Model")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        descriptions = {
            "nllb": "No Language Left Behind supports 200+ languages with high quality translation.",
            "m2m100": "Many-to-Many translation supports 100 languages with direct translation.",
            "mbart": "Multilingual BART supports 50 languages with excellent quality."
        }
        desc = QLabel(descriptions.get(model_type, "Multilingual translation model."))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Model size selector (for NLLB)
        if model_type == "nllb":
            size_group = QGroupBox("Model Size")
            size_layout = QVBoxLayout()
            
            size_combo = QComboBox()
            size_combo.addItem("600MB - Distilled (Fast, Good Quality)", "nllb-200-distilled-600M")
            size_combo.addItem("1.3GB - Standard (Balanced)", "nllb-200-1.3B")
            size_combo.addItem("3.3GB - Large (Best Quality)", "nllb-200-3.3B")
            size_layout.addWidget(size_combo)
            
            size_group.setLayout(size_layout)
            layout.addWidget(size_group)
        elif model_type == "m2m100":
            size_group = QGroupBox("Model Size")
            size_layout = QVBoxLayout()
            
            size_combo = QComboBox()
            size_combo.addItem("418MB - Small (Fast)", "m2m100_418M")
            size_combo.addItem("1.2GB - Large (Better Quality)", "m2m100_1.2B")
            size_layout.addWidget(size_combo)
            
            size_group.setLayout(size_layout)
            layout.addWidget(size_group)
        else:  # mbart
            size_combo = QComboBox()
            size_combo.addItem("2.4GB - Large (Excellent Quality)", "mbart-large-50-many-to-many-mmt")
            size_combo.setVisible(False)  # Only one option
        
        # Language pair selector
        lang_group = QGroupBox("Language Pair")
        lang_layout = QFormLayout()
        
        # Get supported languages for this model type
        languages = manager.get_supported_languages(model_type)
        
        source_combo = QComboBox()
        for code, name in languages:
            source_combo.addItem(f"{name} ({code})", code)
        
        target_combo = QComboBox()
        for code, name in languages:
            target_combo.addItem(f"{name} ({code})", code)
        
        # Set default selections
        source_combo.setCurrentIndex(0)  # English
        target_combo.setCurrentIndex(1 if len(languages) > 1 else 0)  # German or second language
        
        lang_layout.addRow("Source Language:", source_combo)
        lang_layout.addRow("Target Language:", target_combo)
        
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        # Info label
        info_label = QLabel("ℹ️ The model will be downloaded from HuggingFace and a plugin will be auto-generated.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #4A9EFF; font-size: 9pt; padding: 10px; background-color: rgba(74, 158, 255, 0.1); border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        download_btn = QPushButton("📦 Download Model + Generate Plugin")
        download_btn.setProperty("class", "action")
        download_btn.clicked.connect(lambda: self._start_multilingual_download(
            dialog, manager, model_type, size_combo, source_combo, target_combo
        ))
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
    
    def _start_multilingual_download(self, dialog, manager, model_type, size_combo, source_combo, target_combo):
        """Start downloading a multilingual model."""
        # Get selections
        model_name = size_combo.currentData()
        source_lang = source_combo.currentData()
        target_lang = target_combo.currentData()
        
        if source_lang == target_lang:
            QMessageBox.warning(
                dialog,
                "Invalid Selection",
                "Source and target languages must be different!"
            )
            return
        
        # Confirm download
        reply = QMessageBox.question(
            dialog,
            "Confirm Download",
            f"Download {model_name}?\n\n"
            f"Language Pair: {source_combo.currentText()} → {target_combo.currentText()}\n"
            f"Size: {size_combo.currentText().split(' - ')[0]}\n\n"
            f"This will download the model from HuggingFace and auto-generate a plugin.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Create progress dialog
        progress = QProgressDialog(
            f"Downloading {model_name}...",
            "Cancel",
            0,
            100,
            dialog
        )
        progress.setWindowTitle("Downloading Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        def progress_callback(value, message):
            """Update progress."""
            progress.setValue(int(value * 100))
            progress.setLabelText(message)
            QApplication.processEvents()
        
        def download_thread():
            """Download in background thread."""
            try:
                success = manager.download_model(
                    model_name,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    progress_callback=progress_callback,
                    auto_generate_plugin=True
                )
                
                if success:
                    QMessageBox.information(
                        dialog,
                        "Download Complete",
                        f"✅ Successfully downloaded {model_name}!\n\n"
                        f"Plugin generated: {model_type}_{source_lang.split('_')[0]}_{target_lang.split('_')[0]}\n\n"
                        f"You can now use this model for translation."
                    )
                    dialog.accept()
                else:
                    QMessageBox.critical(
                        dialog,
                        "Download Failed",
                        f"❌ Failed to download {model_name}.\n\nCheck logs for details."
                    )
            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    "Download Error",
                    f"❌ Error downloading model:\n\n{str(e)}"
                )
            finally:
                progress.close()
        
        # Start download thread
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    
    def _discover_custom_models(self, parent_dialog, manager, refresh_callback):
        """
        Discover custom models in the models folder and create plugins for them.
        
        This allows users to add their own trained models and automatically
        generate plugins without manual configuration.
        """
        # Create dialog
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("🔍 Discover Custom Models")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Discover Custom Translation Models")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        current_type = manager.get_model_type()
        
        desc = QLabel(
            "This tool scans your models folder for custom translation models and creates plugins for them.\n\n"
            f"📁 Models folder: {manager.cache_dir}\n"
            f"📁 Current model type: {current_type.upper()}\n\n"
            "To add a custom model:\n"
            f"1. Place your model folder in: {manager.cache_dir}/your-model-name/\n"
            "2. Model folder must contain: config.json, pytorch_model.bin (or model.safetensors)\n"
            "3. Click 'Scan for Models' below\n"
            "4. Select the model and provide language pair information\n"
            "5. Plugin will be auto-generated!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; padding: 10px; background-color: rgba(100, 100, 100, 0.1); border-radius: 5px;")
        layout.addWidget(desc)
        
        # Scan button
        scan_btn = QPushButton("🔍 Scan for Models")
        scan_btn.setProperty("class", "action")
        layout.addWidget(scan_btn)
        
        # Discovered models list
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels(["Model Folder", "Has Config", "Has Weights", "Status"])
        models_tree.setColumnWidth(0, 300)
        models_tree.setColumnWidth(1, 100)
        models_tree.setColumnWidth(2, 100)
        models_tree.setColumnWidth(3, 200)
        models_tree.setAlternatingRowColors(True)
        layout.addWidget(models_tree)
        
        def scan_for_models():
            """Scan the models folder for custom models using discover_models()."""
            models_tree.clear()
            
            if not manager.cache_dir.exists():
                QMessageBox.warning(
                    dialog,
                    "Folder Not Found",
                    f"Models folder not found:\n{manager.cache_dir}\n\n"
                    f"You can manually add models to this folder."
                )
                return
            
            try:
                # Use the new discover_models() function
                unregistered_models = manager.discover_models()
                
                # Also show registered models
                registered_models = list(manager.registry.get("models", {}).keys())
                
                discovered = []
                
                # Add unregistered models
                for model_name in unregistered_models:
                    model_path = manager.cache_dir / model_name
                    has_config = (model_path / "config.json").exists()
                    has_weights = (
                        (model_path / "pytorch_model.bin").exists() or
                        (model_path / "model.safetensors").exists()
                    )
                    discovered.append((model_name, has_config, has_weights, "⚠️ Not Registered", False))
                
                # Add registered models
                for model_name in registered_models:
                    model_path = manager.cache_dir / model_name
                    if model_path.exists():
                        has_config = (model_path / "config.json").exists()
                        has_weights = (
                            (model_path / "pytorch_model.bin").exists() or
                            (model_path / "model.safetensors").exists()
                        )
                        discovered.append((model_name, has_config, has_weights, "✓ Registered", True))
                
                # Populate tree
                if not discovered:
                    item = QTreeWidgetItem(["No models found", "", "", ""])
                    item.setForeground(0, Qt.GlobalColor.darkGray)
                    models_tree.addTopLevelItem(item)
                    
                    QMessageBox.information(
                        dialog,
                        "No Models Found",
                        f"No models found in:\n{manager.cache_dir}\n\n"
                        f"To add models manually:\n"
                        f"1. Download a HuggingFace model\n"
                        f"2. Place it in the models folder\n"
                        f"3. Click 'Scan for Models' again\n"
                        f"4. Register and create plugin"
                    )
                else:
                    for model_name, has_config, has_weights, status, is_registered in discovered:
                        item = QTreeWidgetItem([
                            model_name,
                            "✓" if has_config else "✗",
                            "✓" if has_weights else "✗",
                            status
                        ])
                        
                        if is_registered:
                            item.setForeground(0, Qt.GlobalColor.darkGray)
                        else:
                            # Highlight unregistered models
                            item.setForeground(3, Qt.GlobalColor.red)
                        
                        models_tree.addTopLevelItem(item)
                    
                    unregistered_count = len(unregistered_models)
                    if unregistered_count > 0:
                        QMessageBox.information(
                            dialog,
                            "Models Found",
                            f"Found {len(discovered)} total model(s):\n"
                            f"• {len(registered_models)} registered\n"
                            f"• {unregistered_count} unregistered\n\n"
                            f"Select an unregistered model and click 'Register Model' to add it."
                        )
                    else:
                        QMessageBox.information(
                            dialog,
                            "Scan Complete",
                            f"Found {len(discovered)} model(s) - all registered.\n\n"
                            f"You can create plugins for registered models."
                        )
            
            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    "Scan Failed",
                    f"Failed to scan for models:\n{str(e)}"
                )
        
        scan_btn.clicked.connect(scan_for_models)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        register_btn = QPushButton("📝 Register Selected Model")
        register_btn.setProperty("class", "action")
        register_btn.setToolTip("Register an unregistered model in the registry")
        register_btn.clicked.connect(lambda: self._register_custom_model(
            dialog, manager, models_tree, scan_for_models
        ))
        button_layout.addWidget(register_btn)
        
        create_plugin_btn = QPushButton("🔌 Create Plugin for Selected")
        create_plugin_btn.setProperty("class", "action")
        create_plugin_btn.setToolTip("Generate a plugin for a registered model")
        create_plugin_btn.clicked.connect(lambda: self._create_plugin_for_custom_model(
            dialog, manager, models_tree, refresh_callback
        ))
        button_layout.addWidget(create_plugin_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
    
    def _register_custom_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Register a discovered but unregistered model."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        # Get selected model
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                parent_dialog,
                "No Selection",
                "Please select an unregistered model from the list first."
            )
            return
        
        model_name = selected_items[0].text(0)
        status = selected_items[0].text(3)
        
        if model_name == "No models found":
            return
        
        # Check if already registered
        if "✓ Registered" in status:
            QMessageBox.information(
                parent_dialog,
                "Already Registered",
                f"Model '{model_name}' is already registered.\n\n"
                f"You can create a plugin for it using 'Create Plugin' button."
            )
            return
        
        # Ask for language pair
        language_pair, ok = QInputDialog.getText(
            parent_dialog,
            "Language Pair",
            f"Enter language pair for model '{model_name}':\n\n"
            f"Examples:\n"
            f"  • en-de (English to German)\n"
            f"  • ja-en (Japanese to English)\n"
            f"  • zh-en (Chinese to English)\n\n"
            f"Leave empty if multilingual model:",
            text=""
        )
        
        if not ok:
            return
        
        # Ask for description (optional)
        description, ok = QInputDialog.getText(
            parent_dialog,
            "Description (Optional)",
            f"Enter a description for this model:\n\n"
            f"(Leave empty for auto-generated description)",
            text=""
        )
        
        if not ok:
            return
        
        # Register the model
        try:
            success = manager.register_discovered_model(
                model_name,
                language_pair=language_pair if language_pair else None,
                description=description if description else None
            )
            
            if success:
                QMessageBox.information(
                    parent_dialog,
                    "Registration Successful",
                    f"Model '{model_name}' has been registered!\n\n"
                    f"Language pair: {language_pair if language_pair else 'Multilingual'}\n\n"
                    f"You can now create a plugin for this model."
                )
                # Refresh the list
                if refresh_callback:
                    refresh_callback()
            else:
                QMessageBox.critical(
                    parent_dialog,
                    "Registration Failed",
                    f"Failed to register model '{model_name}'.\n\n"
                    f"Check the console for error details."
                )
        
        except Exception as e:
            QMessageBox.critical(
                parent_dialog,
                "Registration Error",
                f"Error registering model:\n{str(e)}"
            )
    
    def _create_plugin_for_custom_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Create a plugin for a selected custom model."""
        # Get selected model
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                parent_dialog,
                "No Selection",
                "Please select a model from the list first."
            )
            return
        
        model_name = selected_items[0].text(0)
        
        if model_name == "No custom models found":
            return
        
        # Check if already registered
        if "✓ Registered" in selected_items[0].text(3):
            QMessageBox.information(
                parent_dialog,
                "Already Registered",
                f"Model '{model_name}' is already registered.\n\n"
                f"A plugin may already exist for this model."
            )
            return
        
        # Show language pair dialog
        lang_dialog = QDialog(parent_dialog)
        lang_dialog.setWindowTitle(f"Configure Plugin for {model_name}")
        lang_dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(lang_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel(f"Configure Plugin for: {model_name}")
        title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Model type selector
        type_group = QGroupBox("Model Type")
        type_layout = QVBoxLayout()
        
        type_combo = QComboBox()
        type_combo.addItem("MarianMT (Bilingual)", "marianmt")
        type_combo.addItem("NLLB (Multilingual)", "nllb")
        type_combo.addItem("M2M-100 (Multilingual)", "m2m100")
        type_combo.addItem("mBART (Multilingual)", "mbart")
        type_combo.addItem("Custom (Other)", "custom")
        type_layout.addWidget(type_combo)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Language pair
        lang_group = QGroupBox("Language Pair")
        lang_layout = QFormLayout()
        
        source_input = QComboBox()
        source_input.setEditable(True)
        source_input.addItems(["en", "de", "es", "fr", "it", "pt", "ja", "zh", "ko", "ru", "ar"])
        
        target_input = QComboBox()
        target_input.setEditable(True)
        target_input.addItems(["en", "de", "es", "fr", "it", "pt", "ja", "zh", "ko", "ru", "ar"])
        
        lang_layout.addRow("Source Language:", source_input)
        lang_layout.addRow("Target Language:", target_input)
        
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        # Model info
        info_group = QGroupBox("Model Information (Optional)")
        info_layout = QFormLayout()
        
        size_input = CustomSpinBox()
        size_input.setRange(1, 10000)
        size_input.setValue(300)
        size_input.setSuffix("MB")
        
        bleu_input = CustomDoubleSpinBox()
        bleu_input.setRange(0, 100)
        bleu_input.setValue(40.0)
        bleu_input.setDecimals(1)
        
        info_layout.addRow("Model Size:", size_input)
        info_layout.addRow("BLEU Score:", bleu_input)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Info message
        info_label = QLabel(
            "ℹ️ This will create a plugin that can be used for translation.\n"
            "The plugin will be named: {model_type}_{source}_{target}"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #4A9EFF; font-size: 9pt; padding: 10px; background-color: rgba(74, 158, 255, 0.1); border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lang_dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("🔌 Create Plugin")
        create_btn.setProperty("class", "action")
        create_btn.clicked.connect(lambda: self._finalize_custom_plugin(
            lang_dialog, manager, model_name, type_combo, source_input, target_input,
            size_input, bleu_input, refresh_callback
        ))
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        lang_dialog.exec()
    
    def _finalize_custom_plugin(self, dialog, manager, model_name, type_combo, source_input, 
                                target_input, size_input, bleu_input, refresh_callback):
        """Finalize and create the plugin for custom model."""
        # Get values
        model_type = type_combo.currentData()
        source_lang = source_input.currentText().strip()
        target_lang = target_input.currentText().strip()
        size_mb = size_input.value()
        bleu_score = bleu_input.value()
        
        # Validate
        if not source_lang or not target_lang:
            QMessageBox.warning(
                dialog,
                "Invalid Input",
                "Please provide both source and target languages."
            )
            return
        
        if source_lang == target_lang:
            QMessageBox.warning(
                dialog,
                "Invalid Input",
                "Source and target languages must be different."
            )
            return
        
        # Create model info
        model_info = {
            "name": model_name,
            "size": size_mb,
            "bleu": bleu_score,
            "desc": f"Custom {model_type} model: {source_lang} → {target_lang}"
        }
        
        # Generate plugin
        try:
            success = manager._generate_plugin_for_model(
                model_name, source_lang, target_lang, model_info
            )
            
            if success:
                # Update registry
                manager.registry.setdefault("models", {})[model_name] = {
                    "downloaded": True,
                    "download_date": datetime.now().isoformat(),
                    "size_mb": size_mb,
                    "optimized": False,
                    "model_type": model_type,
                    "language_pair": f"{source_lang}-{target_lang}",
                    "custom": True
                }
                manager._save_registry()
                
                QMessageBox.information(
                    dialog,
                    "Plugin Created",
                    f"✅ Successfully created plugin for {model_name}!\n\n"
                    f"Plugin name: {model_type}_{source_lang}_{target_lang}\n"
                    f"Language pair: {source_lang} → {target_lang}\n\n"
                    f"You can now use this model for translation."
                )
                
                dialog.accept()
                
                if refresh_callback:
                    refresh_callback()
            else:
                QMessageBox.critical(
                    dialog,
                    "Plugin Creation Failed",
                    f"❌ Failed to create plugin for {model_name}.\n\n"
                    f"Check logs for details."
                )
        except Exception as e:
            QMessageBox.critical(
                dialog,
                "Error",
                f"❌ Error creating plugin:\n\n{str(e)}"
            )
