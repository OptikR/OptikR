"""
Translation Model Manager — split into domain-specific modules.

Submodules:
    catalog_adapter – CatalogTranslationAdapter (ModelCatalog ↔ UI bridge)
    marianmt        – MarianMT pair download / optimize / delete / add
    multilingual    – NLLB / M2M-100 / mBART download
    custom_models   – Custom model discovery, registration, plugin creation
    cache           – Cache management tab and cleanup
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTabWidget
)

from .catalog_adapter import CatalogTranslationAdapter
from .marianmt import MarianMTMixin
from .multilingual import MultilingualMixin
from .custom_models import CustomModelsMixin
from .cache import CacheMixin


class TranslationModelManager(MarianMTMixin, MultilingualMixin, CustomModelsMixin, CacheMixin):
    """Manages translation AI models."""

    def __init__(self, parent=None, config_manager=None):
        self.parent = parent
        self.config_manager = config_manager

    def show_marianmt_manager(self):
        """Show Universal Translation Model Manager dialog."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Universal Translation Model Manager")
        dialog.setMinimumSize(1000, 700)
        dialog.resize(1000, 700)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        manager = CatalogTranslationAdapter(model_type="marianmt")

        # Header with model type selector
        header_layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title_label = QLabel("Universal Translation Model Manager")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        header_layout.addLayout(title_row)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Model Type:"))

        model_type_combo = QComboBox()
        model_type_combo.addItem("MarianMT (Helsinki-NLP)", "marianmt")
        model_type_combo.addItem("NLLB-200 (Meta AI)", "nllb")
        model_type_combo.addItem("M2M-100 (Facebook)", "m2m100")
        model_type_combo.addItem("mBART (Facebook)", "mbart")
        model_type_combo.addItem("Qwen3 (LLM Translation)", "qwen3")
        model_type_combo.setCurrentIndex(0)
        model_type_combo.setMinimumWidth(250)
        selector_row.addWidget(model_type_combo)

        cache_info = manager.get_cache_info()
        info_label = QLabel("")
        info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        selector_row.addWidget(info_label)
        selector_row.addStretch()

        header_layout.addLayout(selector_row)
        main_layout.addLayout(header_layout)

        refresh_models_func = [None]
        manager_ref = [manager]

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        available_tab = self._create_available_models_tab(manager_ref, refresh_models_func)
        tab_widget.addTab(available_tab, "Available Models")

        cache_tab = self._create_cache_management_tab(manager_ref[0], cache_info)
        tab_widget.addTab(cache_tab, "Cache Management")

        def _update_header_info():
            current_info = manager_ref[0].get_cache_info()
            info_label.setText(
                f"Device: {current_info['device'].upper()} | "
                f"Downloaded: {current_info['downloaded_models']}/{current_info['total_models']} | "
                f"Space: {current_info['available_space_gb']:.1f}GB"
            )

        def on_model_type_changed(index):
            new_model_type = model_type_combo.itemData(index)
            manager_ref[0] = CatalogTranslationAdapter(model_type=new_model_type)
            _update_header_info()
            if refresh_models_func[0]:
                refresh_models_func[0]()

        model_type_combo.currentIndexChanged.connect(on_model_type_changed)
        _update_header_info()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "action")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

        dialog.exec()


__all__ = ['TranslationModelManager', 'CatalogTranslationAdapter']
