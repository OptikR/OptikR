"""
Smart Dictionary Settings Tab

Main container composing StatisticsSection and OperationsSection.
Handles language pair selection, dictionary settings, and config persistence.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QCheckBox, QGridLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.localization import TranslatableMixin, tr
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox
from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel

from .statistics_section import StatisticsSection
from .operations_section import OperationsSection

logger = logging.getLogger(__name__)


class SmartDictionaryTab(TranslatableMixin, QWidget):
    """Smart Dictionary settings - learning dictionary management and configuration."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the Smart Dictionary settings tab."""
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = pipeline

        self._original_state = {}

        # Language pair selector
        self.language_pair_combo = None

        # Settings widgets
        self.auto_learn_check = None
        self.learn_words_check = None
        self.learn_sentences_check = None
        self.extract_words_on_stop_check = None
        self.min_confidence_spin = None
        self.max_entries_spin = None

        # Sections
        self.statistics_section = None
        self.operations_section = None

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)

        # Sections
        self.statistics_section = StatisticsSection()
        self.operations_section = OperationsSection(
            config_manager=self.config_manager,
            get_current_pair=lambda: self.language_pair_combo.currentData(),
        )
        self.operations_section.dictionaryModified.connect(self._on_dictionary_modified)

        self._create_overview_section(content_layout)
        self._create_language_pair_selector(content_layout)
        content_layout.addWidget(self.statistics_section)
        content_layout.addWidget(self.operations_section)
        self._create_settings_section(content_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def _create_overview_section(self, parent_layout):
        """Create overview section explaining the smart dictionary."""
        group = QGroupBox(tr("dict_tab_overview_title"))
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        overview = QLabel(tr("dict_tab_overview_body"))
        overview.setWordWrap(True)
        overview.setStyleSheet("font-size: 9pt; padding: 10px;")
        layout.addWidget(overview)

        note = QLabel(tr("dict_tab_note_pipeline"))
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #2196F3; font-size: 9pt; padding: 10px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px; "
            "border-left: 4px solid #2196F3; margin-top: 10px;"
        )
        layout.addWidget(note)

        parent_layout.addWidget(group)

    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label

    def _create_language_pair_selector(self, parent_layout):
        """Create language pair selector."""
        group = QGroupBox(tr("dict_tab_select_pair"))
        layout = QHBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        selector_label = self._create_label(tr("dict_tab_language_pair_label"), bold=True)
        layout.addWidget(selector_label)

        self.language_pair_combo = QComboBox()
        self.language_pair_combo.setMinimumWidth(300)
        self.language_pair_combo.currentIndexChanged.connect(self._on_language_pair_changed)
        layout.addWidget(self.language_pair_combo)

        refresh_btn = QPushButton(tr("_refresh"))
        refresh_btn.setProperty("class", "action")
        refresh_btn.setMinimumWidth(100)
        refresh_btn.clicked.connect(self._refresh_language_pairs)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        parent_layout.addWidget(group)

    def _create_settings_section(self, parent_layout):
        """Create dictionary settings section."""
        group = QGroupBox(tr("dictionary_settings"))
        layout = QFormLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        self.auto_learn_check = QCheckBox(tr("dict_tab_auto_learn"))
        self.auto_learn_check.setChecked(True)
        self.auto_learn_check.stateChanged.connect(self.on_change)
        layout.addRow(tr("dict_tab_auto_learn_label"), self.auto_learn_check)

        self.learn_words_check = QCheckBox(tr("dict_tab_learn_words"))
        self.learn_words_check.setChecked(True)
        self.learn_words_check.setToolTip(tr("dict_tab_learn_words_tooltip"))
        self.learn_words_check.stateChanged.connect(self.on_change)
        layout.addRow("", self.learn_words_check)

        self.learn_sentences_check = QCheckBox(tr("dict_tab_learn_sentences"))
        self.learn_sentences_check.setChecked(True)
        self.learn_sentences_check.setToolTip(tr("dict_tab_learn_sentences_tooltip"))
        self.learn_sentences_check.stateChanged.connect(self.on_change)
        layout.addRow("", self.learn_sentences_check)

        learn_help = QLabel(tr("dict_tab_learn_help"))
        learn_help.setStyleSheet("color: #666666; font-size: 8pt; font-style: italic;")
        layout.addRow("", learn_help)

        self.extract_words_on_stop_check = QCheckBox(tr("dict_tab_extract_on_stop"))
        self.extract_words_on_stop_check.setChecked(True)
        self.extract_words_on_stop_check.setToolTip(tr("dict_tab_extract_on_stop_tooltip"))
        self.extract_words_on_stop_check.stateChanged.connect(self.on_change)
        layout.addRow(tr("dict_tab_word_extraction_label"), self.extract_words_on_stop_check)

        extract_help = QLabel(tr("dict_tab_extract_help"))
        extract_help.setStyleSheet("color: #FF8C00; font-size: 8pt; font-style: italic; font-weight: bold;")
        layout.addRow("", extract_help)

        spinbox_container = QWidget()
        spinbox_grid = QGridLayout(spinbox_container)
        spinbox_grid.setHorizontalSpacing(8)
        spinbox_grid.setVerticalSpacing(8)
        spinbox_grid.setContentsMargins(0, 0, 0, 0)
        spinbox_grid.setColumnStretch(2, 1)

        self.min_confidence_spin = CustomDoubleSpinBox()
        self.min_confidence_spin.setRange(0.0, 1.0)
        self.min_confidence_spin.setSingleStep(0.1)
        self.min_confidence_spin.setValue(0.7)
        self.min_confidence_spin.setDecimals(2)
        self.min_confidence_spin.valueChanged.connect(self.on_change)

        spinbox_grid.addWidget(QLabel(tr("min_confidence")), 0, 0)
        spinbox_grid.addWidget(self.min_confidence_spin, 0, 1)

        self.max_entries_spin = CustomSpinBox()
        self.max_entries_spin.setRange(100, 999999)
        self.max_entries_spin.setSingleStep(1000)
        self.max_entries_spin.setValue(999999)
        self.max_entries_spin.setSuffix(" " + tr("dict_tab_entries_suffix"))
        self.max_entries_spin.setSpecialValueText(tr("dict_tab_unlimited"))
        self.max_entries_spin.valueChanged.connect(self.on_change)

        spinbox_grid.addWidget(QLabel(tr("max_entries")), 1, 0)
        spinbox_grid.addWidget(self.max_entries_spin, 1, 1)

        layout.addRow(spinbox_container)

        help_text = QLabel(tr("min_confidence_only_learn_translations_with_confidence_above"))
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666666; font-size: 8pt; font-style: italic; margin-top: 5px;")
        layout.addRow("", help_text)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def on_change(self):
        """Called when any setting changes."""
        self.settingChanged.emit()

    def _on_language_pair_changed(self, _index):
        """Handle language pair selection change."""
        current_data = self.language_pair_combo.currentData()
        self.statistics_section.update_statistics(current_data, self.pipeline)

    def _on_dictionary_modified(self):
        """Handle dictionary modification from operations section."""
        self._refresh_language_pairs()
        self.on_change()

    def _refresh_language_pairs(self):
        """Refresh the language pairs list by scanning dictionary directory."""
        try:
            from app.utils.path_utils import get_dictionary_dir

            dict_dir = get_dictionary_dir()

            if not dict_dir.exists():
                self.language_pair_combo.clear()
                self.language_pair_combo.addItem(tr("no_dictionaries_found"))
                self.statistics_section.clear_statistics()
                return

            all_dict_files = list(dict_dir.glob("*.json.gz"))
            dict_files = [f for f in all_dict_files if 'backup' not in f.name.lower()]

            if not dict_files:
                self.language_pair_combo.clear()
                self.language_pair_combo.addItem(tr("no_dictionaries_found"))
                self.statistics_section.clear_statistics()
                logger.debug(
                    "No valid dictionaries found in %s (%d files were backups)",
                    dict_dir, len(all_dict_files),
                )
                return

            language_pairs = []
            for dict_file in dict_files:
                try:
                    filename = dict_file.stem  # Remove .gz
                    if filename.endswith('.json'):
                        filename = filename[:-5]

                    parts = filename.split('_')
                    if len(parts) == 2 and len(parts[0]) <= 3 and len(parts[1]) <= 3:
                        source_lang = parts[0]
                        target_lang = parts[1]

                        if '.' in source_lang or '.' in target_lang:
                            logger.debug("Skipping invalid filename: %s", dict_file.name)
                            continue

                        display_name = f"{source_lang.upper()} → {target_lang.upper()}"
                        language_pairs.append(
                            (display_name, source_lang, target_lang, str(dict_file))
                        )
                except Exception as e:
                    logger.warning("Failed to parse %s: %s", dict_file.name, e)

            self.language_pair_combo.blockSignals(True)
            self.language_pair_combo.clear()
            for display_name, source_lang, target_lang, file_path in language_pairs:
                self.language_pair_combo.addItem(
                    display_name, (source_lang, target_lang, file_path)
                )
            self.language_pair_combo.blockSignals(False)

            if language_pairs:
                current_data = self.language_pair_combo.currentData()
                self.statistics_section.update_statistics(current_data, self.pipeline)

            self.statistics_section.update_language_pairs_table()

            logger.debug("Found %d language pairs", len(language_pairs))

        except Exception as e:
            logger.error("Failed to refresh language pairs: %s", e, exc_info=True)
            QMessageBox.warning(
                self,
                tr("error"),
                tr("dict_tab_refresh_error_msg", error=str(e)),
            )

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return

        try:
            auto_learn = self.config_manager.get_setting('dictionary.auto_learn', True)
            learn_words = self.config_manager.get_setting('dictionary.learn_words', True)
            learn_sentences = self.config_manager.get_setting('dictionary.learn_sentences', True)
            extract_words_on_stop = self.config_manager.get_setting('dictionary.extract_words_on_stop', True)
            min_confidence = self.config_manager.get_setting('dictionary.min_confidence', 0.7)
            max_entries = self.config_manager.get_setting('dictionary.max_entries', 999999)

            self.auto_learn_check.setChecked(auto_learn)
            self.learn_words_check.setChecked(learn_words)
            self.learn_sentences_check.setChecked(learn_sentences)
            self.extract_words_on_stop_check.setChecked(extract_words_on_stop)
            self.min_confidence_spin.setValue(min_confidence)
            self.max_entries_spin.setValue(max_entries)

            self._refresh_language_pairs()

            self._original_state = self._get_current_state()

            logger.info("Smart Dictionary settings loaded")

        except Exception as e:
            logger.error("Failed to load Smart Dictionary settings: %s", e, exc_info=True)

    def save_config(self):
        """Save configuration to config manager.

        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"

        try:
            self.config_manager.set_setting('dictionary.auto_learn', self.auto_learn_check.isChecked())
            self.config_manager.set_setting('dictionary.learn_words', self.learn_words_check.isChecked())
            self.config_manager.set_setting('dictionary.learn_sentences', self.learn_sentences_check.isChecked())
            self.config_manager.set_setting(
                'dictionary.extract_words_on_stop', self.extract_words_on_stop_check.isChecked()
            )
            self.config_manager.set_setting('dictionary.min_confidence', self.min_confidence_spin.value())
            self.config_manager.set_setting('dictionary.max_entries', self.max_entries_spin.value())

            success, error_msg = self.config_manager.save_config()
            if not success:
                return False, error_msg

            self._apply_settings_to_pipeline()

            self._original_state = self._get_current_state()

            logger.info("Smart Dictionary settings saved to disk")
            return True, ""

        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _apply_settings_to_pipeline(self):
        """Apply settings to running pipeline's SmartDictionary instance."""
        try:
            if not self.pipeline:
                return

            smart_dict = None
            if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                smart_dict = getattr(self.pipeline.cache_manager, 'persistent_dictionary', None)

            if not smart_dict:
                return

            if hasattr(smart_dict, 'auto_learn'):
                smart_dict.auto_learn = self.auto_learn_check.isChecked()
            if hasattr(smart_dict, 'min_confidence'):
                smart_dict.min_confidence = self.min_confidence_spin.value()
            if hasattr(smart_dict, 'max_entries'):
                smart_dict.max_entries = self.max_entries_spin.value()

        except Exception as e:
            logger.error("Failed to apply settings to pipeline: %s", e, exc_info=True)

    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        if self.auto_learn_check:
            state['auto_learn'] = self.auto_learn_check.isChecked()
        if self.learn_words_check:
            state['learn_words'] = self.learn_words_check.isChecked()
        if self.learn_sentences_check:
            state['learn_sentences'] = self.learn_sentences_check.isChecked()
        if self.extract_words_on_stop_check:
            state['extract_words_on_stop'] = self.extract_words_on_stop_check.isChecked()
        if self.min_confidence_spin:
            state['min_confidence'] = self.min_confidence_spin.value()
        if self.max_entries_spin:
            state['max_entries'] = self.max_entries_spin.value()
        return state

    def validate(self) -> bool:
        """Validate settings."""
        return True
