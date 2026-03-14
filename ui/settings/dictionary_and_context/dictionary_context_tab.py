"""
Dictionary & Context Tab

Merged container that embeds SmartDictionaryTab and ContextManagerTab
as sub-tabs within a single top-level tab.
"""

import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import pyqtSignal

from app.localization import TranslatableMixin, tr
from .dictionary_tab import SmartDictionaryTab
from .context_tab import ContextManagerTab

logger = logging.getLogger(__name__)


class DictionaryContextTab(TranslatableMixin, QWidget):
    """Combined Dictionary & Context settings tab."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        super().__init__(parent)

        self.config_manager = config_manager

        self.dictionary_tab = SmartDictionaryTab(
            config_manager=config_manager,
            pipeline=pipeline,
            parent=self,
        )
        self.context_tab = ContextManagerTab(
            config_manager=config_manager,
            parent=self,
        )

        self.dictionary_tab.settingChanged.connect(self.settingChanged)
        self.context_tab.settingChanged.connect(self.settingChanged)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sub_tabs = QTabWidget()
        sub_tabs.addTab(self.dictionary_tab, tr("smart_dictionary"))
        sub_tabs.addTab(self.context_tab, tr("context"))
        self._sub_tab_widget = sub_tabs

        layout.addWidget(sub_tabs)

    # ------------------------------------------------------------------
    # Pipeline delegation
    # ------------------------------------------------------------------

    def set_pipeline(self, pipeline):
        """Forward pipeline reference to child tabs that need it."""
        self.dictionary_tab.pipeline = pipeline
        self.context_tab.set_pipeline(pipeline)

    # ------------------------------------------------------------------
    # Config persistence (delegates to both child tabs)
    # ------------------------------------------------------------------

    def load_config(self):
        self.dictionary_tab.load_config()
        self.context_tab.load_config()

    def save_config(self):
        dict_ok, dict_err = self.dictionary_tab.save_config()
        ctx_ok, ctx_err = self.context_tab.save_config()

        if not dict_ok:
            return False, dict_err
        if not ctx_ok:
            return False, ctx_err
        return True, ""

    def validate(self) -> bool:
        return self.dictionary_tab.validate() and self.context_tab.validate()

    # ------------------------------------------------------------------
    # Cross-tab setting sync
    # ------------------------------------------------------------------

    def on_setting_changed(self, key: str, value):
        """Forward external setting changes to child tabs."""
        if hasattr(self.context_tab, 'on_setting_changed'):
            self.context_tab.on_setting_changed(key, value)
