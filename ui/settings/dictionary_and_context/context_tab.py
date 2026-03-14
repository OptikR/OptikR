"""
Context Manager Tab - PyQt6 Implementation

Standalone tab for managing context profiles — domain-aware translation
intelligence with pre/post translation processing through structured JSON profiles.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QCheckBox,
    QFormLayout, QComboBox, QScrollArea, QFrame, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from app.localization import TranslatableMixin, tr
from pathlib import Path

_logger = logging.getLogger(__name__)
from app.utils.path_utils import get_plugin_enhancers_dir, get_context_profiles_dir


class ContextManagerTab(TranslatableMixin, QWidget):
    """Context profile management — domain-aware translation intelligence."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.context_plugin = None
        self._init_ui()

    # ------------------------------------------------------------------
    # Plugin initialisation
    # ------------------------------------------------------------------

    def _init_context_plugin(self):
        """Initialize the Context Manager plugin and refresh the UI."""
        try:
            from plugins.enhancers.optimizers.context_manager import initialize as ctx_initialize
            import json

            plugin_json_path = get_plugin_enhancers_dir("optimizers") / "context_manager" / "plugin.json"
            if plugin_json_path.exists():
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    plugin_config = json.load(f)
            else:
                plugin_config = {}

            self.context_plugin = ctx_initialize(plugin_config)

            if hasattr(self.context_plugin, 'set_config_manager') and self.config_manager:
                self.context_plugin.set_config_manager(self.config_manager)

            if hasattr(self.context_plugin, 'initialize'):
                self.context_plugin.initialize()

            _logger.info("Context Manager plugin loaded successfully")
            self._refresh_profile_list()

        except Exception as e:
            _logger.error("Failed to load Context Manager plugin: %s", e, exc_info=True)
            self.context_plugin = None

    def set_pipeline(self, pipeline):
        """Called when the pipeline becomes available — initialise the plugin."""
        self._init_context_plugin()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ── Header + Enable toggle (stays fixed, outside scroll) ──
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 10, 10, 0)
        header_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header = QLabel()
        self.set_translatable_text(header, "ctx_header")
        header.setStyleSheet("font-size: 13pt; font-weight: bold; color: #4a9eff;")
        header_row.addWidget(header, 1)

        self.context_enabled_check = QCheckBox()
        self.set_translatable_text(self.context_enabled_check, "enabled")
        self.context_enabled_check.setChecked(True)
        self.context_enabled_check.stateChanged.connect(self._on_context_enabled_changed)
        header_row.addWidget(self.context_enabled_check)
        header_layout.addLayout(header_row)

        desc = QLabel()
        self.set_translatable_text(desc, "ctx_description")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 4px;")
        header_layout.addWidget(desc)

        outer_layout.addWidget(header_widget)

        # ── Scroll area for all content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.context_content = QWidget()
        content_layout = QVBoxLayout(self.context_content)
        content_layout.setContentsMargins(10, 8, 10, 10)
        content_layout.setSpacing(10)

        # ── Profile selector row ──
        selector_layout = QHBoxLayout()
        active_profile_label = QLabel()
        self.set_translatable_text(active_profile_label, "ctx_active_profile_label")
        selector_layout.addWidget(active_profile_label)
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.addItem(tr("ctx_none_profile"))
        self.profile_combo.currentTextChanged.connect(self._on_profile_selected)
        selector_layout.addWidget(self.profile_combo, 1)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("")
        self.set_translatable_text(refresh_btn, "ctx_refresh_tooltip", method="setToolTip")
        refresh_btn.setFixedWidth(32)
        refresh_btn.clicked.connect(self._refresh_profile_list)
        selector_layout.addWidget(refresh_btn)

        new_btn = QPushButton()
        self.set_translatable_text(new_btn, "ctx_new_btn")
        new_btn.clicked.connect(self._create_new_profile)
        selector_layout.addWidget(new_btn)

        del_btn = QPushButton()
        self.set_translatable_text(del_btn, "ctx_delete_btn")
        del_btn.clicked.connect(self._delete_selected_profile)
        selector_layout.addWidget(del_btn)
        content_layout.addLayout(selector_layout)

        # ── Import / Export row ──
        io_layout = QHBoxLayout()
        import_btn = QPushButton()
        self.set_translatable_text(import_btn, "ctx_import_btn")
        import_btn.clicked.connect(self._import_profile)
        io_layout.addWidget(import_btn)

        export_btn = QPushButton()
        self.set_translatable_text(export_btn, "ctx_export_btn")
        export_btn.clicked.connect(self._export_profile)
        io_layout.addWidget(export_btn)

        open_folder_btn = QPushButton()
        self.set_translatable_text(open_folder_btn, "ctx_open_folder_btn")
        open_folder_btn.clicked.connect(self._open_profiles_folder)
        io_layout.addWidget(open_folder_btn)

        io_layout.addStretch()
        content_layout.addLayout(io_layout)

        # ── How it works (tooltip) ──
        how_label = QLabel(tr("ctx_how_it_works_html"))
        how_label.setTextFormat(Qt.TextFormat.RichText)
        how_label.setWordWrap(True)
        how_label.setStyleSheet(
            "padding: 6px 8px; background-color: rgba(74, 158, 255, 0.08); "
            "border-radius: 4px; border: 1px solid rgba(74, 158, 255, 0.15);"
        )
        how_label.setToolTip(tr("ctx_how_it_works_tooltip"))
        content_layout.addWidget(how_label)

        # ── Profile metadata ──
        meta_group = QGroupBox()
        self.set_translatable_text(meta_group, "ctx_profile_metadata_section")
        meta_form = QFormLayout(meta_group)
        meta_form.setSpacing(4)

        self.ctx_name_edit = QLineEdit("—")
        self.ctx_name_edit.setStyleSheet("font-weight: bold; color: #4a9eff;")
        self.ctx_name_edit.textChanged.connect(lambda: self.settingChanged.emit())
        meta_form.addRow(tr("ctx_name_label"), self.ctx_name_edit)

        self.ctx_category_edit = QLineEdit("—")
        self.ctx_category_edit.textChanged.connect(lambda: self.settingChanged.emit())
        meta_form.addRow(tr("ctx_category_label"), self.ctx_category_edit)

        self.ctx_desc_edit = QTextEdit()
        self.ctx_desc_edit.setMaximumHeight(50)
        self.ctx_desc_edit.setPlaceholderText("")
        self.set_translatable_text(self.ctx_desc_edit, "ctx_profile_desc_placeholder", method="setPlaceholderText")
        self.ctx_desc_edit.textChanged.connect(lambda: self.settingChanged.emit())
        meta_form.addRow(tr("ctx_description_label"), self.ctx_desc_edit)

        lang_row = QHBoxLayout()
        self.ctx_source_lang = QComboBox()
        self.ctx_source_lang.setEditable(True)
        self.ctx_source_lang.addItems(["", "ja", "en", "de", "fr", "zh", "ko", "es", "it", "tr"])
        self.ctx_source_lang.currentTextChanged.connect(lambda: self.settingChanged.emit())
        source_label = QLabel()
        self.set_translatable_text(source_label, "ctx_source_label")
        lang_row.addWidget(source_label)
        lang_row.addWidget(self.ctx_source_lang)
        lang_row.addWidget(QLabel("→"))
        self.ctx_target_lang = QComboBox()
        self.ctx_target_lang.setEditable(True)
        self.ctx_target_lang.addItems(["", "ja", "en", "de", "fr", "zh", "ko", "es", "it", "tr"])
        self.ctx_target_lang.currentTextChanged.connect(lambda: self.settingChanged.emit())
        target_label = QLabel()
        self.set_translatable_text(target_label, "ctx_target_label")
        lang_row.addWidget(target_label)
        lang_row.addWidget(self.ctx_target_lang)
        lang_row.addStretch()
        meta_form.addRow(tr("ctx_languages_label"), lang_row)
        content_layout.addWidget(meta_group)

        # ── Locked Terms ──
        terms_group = QGroupBox()
        self.set_translatable_text(terms_group, "ctx_locked_terms_section")
        terms_layout = QVBoxLayout(terms_group)
        terms_desc = QLabel()
        self.set_translatable_text(terms_desc, "ctx_locked_terms_desc")
        terms_desc.setWordWrap(True)
        terms_desc.setStyleSheet("color: #aaa; font-size: 8pt; padding-bottom: 4px;")
        terms_layout.addWidget(terms_desc)

        terms_example = QLabel(
            "Example term entry:\n"
            "Source: ナルト | Target: Naruto | Type: name | Priority: 100 | Case Sensitive: On\n"
            "Use high priority for character names, places, and special terms that should never be mistranslated."
        )
        terms_example.setWordWrap(True)
        terms_example.setStyleSheet(
            "color: #4a9eff; font-size: 8pt; padding: 6px 8px; "
            "background-color: rgba(74, 158, 255, 0.10); border-radius: 4px; "
            "border-left: 3px solid rgba(74, 158, 255, 0.45);"
        )
        terms_layout.addWidget(terms_example)

        self.terms_table = QTableWidget(0, 6)
        self.terms_table.setHorizontalHeaderLabels([
            tr("ctx_th_source"), tr("ctx_th_target"), tr("ctx_th_type"),
            tr("ctx_th_priority"), tr("ctx_th_case_sensitive"), tr("ctx_th_notes"),
        ])
        self.terms_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.terms_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.terms_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.terms_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.terms_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.terms_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.terms_table.setMinimumHeight(160)
        self.terms_table.cellChanged.connect(lambda: self.settingChanged.emit())
        terms_layout.addWidget(self.terms_table)

        term_btn_layout = QHBoxLayout()
        add_term_btn = QPushButton()
        self.set_translatable_text(add_term_btn, "ctx_add_term_btn")
        add_term_btn.clicked.connect(self._add_locked_term_row)
        term_btn_layout.addWidget(add_term_btn)
        remove_term_btn = QPushButton()
        self.set_translatable_text(remove_term_btn, "ctx_remove_selected_btn")
        remove_term_btn.clicked.connect(self._remove_selected_term)
        term_btn_layout.addWidget(remove_term_btn)
        term_btn_layout.addStretch()
        terms_layout.addLayout(term_btn_layout)
        content_layout.addWidget(terms_group)

        # ── Translation Memory ──
        tm_group = QGroupBox()
        self.set_translatable_text(tm_group, "ctx_translation_memory_section")
        tm_layout = QVBoxLayout(tm_group)
        tm_desc = QLabel()
        self.set_translatable_text(tm_desc, "ctx_tm_desc")
        tm_desc.setWordWrap(True)
        tm_desc.setStyleSheet("color: #aaa; font-size: 8pt; padding-bottom: 4px;")
        tm_layout.addWidget(tm_desc)

        self.tm_table = QTableWidget(0, 4)
        self.tm_table.setHorizontalHeaderLabels([tr("ctx_th_source"), tr("ctx_th_target"), tr("ctx_th_priority"), tr("ctx_th_notes")])
        self.tm_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tm_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tm_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tm_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tm_table.setMinimumHeight(130)
        self.tm_table.cellChanged.connect(lambda: self.settingChanged.emit())
        tm_layout.addWidget(self.tm_table)

        tm_btn_layout = QHBoxLayout()
        add_tm_btn = QPushButton()
        self.set_translatable_text(add_tm_btn, "ctx_add_entry_btn")
        add_tm_btn.clicked.connect(self._add_tm_row)
        tm_btn_layout.addWidget(add_tm_btn)
        remove_tm_btn = QPushButton()
        self.set_translatable_text(remove_tm_btn, "ctx_remove_selected_btn_2")
        remove_tm_btn.clicked.connect(self._remove_selected_tm)
        tm_btn_layout.addWidget(remove_tm_btn)
        tm_btn_layout.addStretch()
        tm_layout.addLayout(tm_btn_layout)
        content_layout.addWidget(tm_group)

        # ── Regex Rules ──
        regex_group = QGroupBox()
        self.set_translatable_text(regex_group, "ctx_regex_rules_section")
        regex_layout = QVBoxLayout(regex_group)
        regex_desc = QLabel()
        self.set_translatable_text(regex_desc, "ctx_regex_desc")
        regex_desc.setWordWrap(True)
        regex_desc.setStyleSheet("color: #aaa; font-size: 8pt; padding-bottom: 4px;")
        regex_layout.addWidget(regex_desc)

        self.regex_table = QTableWidget(0, 5)
        self.regex_table.setHorizontalHeaderLabels([tr("ctx_th_pattern"), tr("ctx_th_action"), tr("ctx_th_replacement"), tr("ctx_th_stage"), tr("ctx_th_description")])
        self.regex_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.regex_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.regex_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.regex_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.regex_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.regex_table.setMinimumHeight(130)
        self.regex_table.cellChanged.connect(lambda: self.settingChanged.emit())
        regex_layout.addWidget(self.regex_table)

        regex_btn_layout = QHBoxLayout()
        add_regex_btn = QPushButton()
        self.set_translatable_text(add_regex_btn, "ctx_add_rule_btn")
        add_regex_btn.clicked.connect(self._add_regex_row)
        regex_btn_layout.addWidget(add_regex_btn)
        remove_regex_btn = QPushButton()
        self.set_translatable_text(remove_regex_btn, "ctx_remove_selected_btn_3")
        remove_regex_btn.clicked.connect(self._remove_selected_regex)
        regex_btn_layout.addWidget(remove_regex_btn)
        regex_btn_layout.addStretch()
        regex_layout.addLayout(regex_btn_layout)
        content_layout.addWidget(regex_group)

        # ── Formatting Rules ──
        fmt_group = QGroupBox()
        self.set_translatable_text(fmt_group, "ctx_formatting_rules_section")
        fmt_layout = QVBoxLayout(fmt_group)
        fmt_desc = QLabel()
        self.set_translatable_text(fmt_desc, "ctx_formatting_desc")
        fmt_desc.setWordWrap(True)
        fmt_desc.setStyleSheet("color: #aaa; font-size: 8pt; padding-bottom: 4px;")
        fmt_layout.addWidget(fmt_desc)

        self.fmt_honorifics = QCheckBox()
        self.set_translatable_text(self.fmt_honorifics, "ctx_preserve_honorifics")
        self.fmt_attack_upper = QCheckBox()
        self.set_translatable_text(self.fmt_attack_upper, "ctx_uppercase_attacks")
        self.fmt_sfx = QCheckBox()
        self.set_translatable_text(self.fmt_sfx, "ctx_translate_sfx")
        self.fmt_sfx.setChecked(True)
        self.fmt_brackets = QCheckBox()
        self.set_translatable_text(self.fmt_brackets, "ctx_preserve_brackets")
        self.fmt_brackets.setChecked(True)

        for cb in (self.fmt_honorifics, self.fmt_attack_upper, self.fmt_sfx, self.fmt_brackets):
            cb.stateChanged.connect(lambda: self.settingChanged.emit())
            fmt_layout.addWidget(cb)

        style_row = QHBoxLayout()
        style_label = QLabel()
        self.set_translatable_text(style_label, "ctx_language_style_label")
        style_row.addWidget(style_label)
        self.fmt_style_combo = QComboBox()
        for display_key, value in [
            ("ctx_style_neutral", "neutral"),
            ("ctx_style_formal", "formal"),
            ("ctx_style_casual", "casual"),
            ("ctx_style_technical", "technical"),
            ("ctx_style_literary", "literary"),
        ]:
            self.fmt_style_combo.addItem(tr(display_key), value)
        self.fmt_style_combo.currentIndexChanged.connect(lambda: self.settingChanged.emit())
        style_row.addWidget(self.fmt_style_combo)
        style_row.addStretch()
        fmt_layout.addLayout(style_row)
        content_layout.addWidget(fmt_group)

        # ── Save button + Status ──
        bottom_row = QHBoxLayout()
        save_btn = QPushButton()
        self.set_translatable_text(save_btn, "ctx_save_profile_btn")
        save_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        save_btn.setToolTip("")
        self.set_translatable_text(save_btn, "ctx_save_profile_tooltip", method="setToolTip")
        save_btn.clicked.connect(self._save_profile_from_ui)
        bottom_row.addWidget(save_btn)

        self.ctx_status_label = QLabel("")
        self.ctx_status_label.setStyleSheet("color: #66bb6a; font-size: 9pt; font-style: italic;")
        bottom_row.addWidget(self.ctx_status_label, 1)
        content_layout.addLayout(bottom_row)

        # Spacer at bottom so scroll feels natural
        content_layout.addSpacing(40)

        scroll.setWidget(self.context_content)
        outer_layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Config load / save
    # ------------------------------------------------------------------

    def load_config(self):
        if not self.config_manager:
            return
        # Enabled state
        enabled = self.config_manager.get_setting('plugins.context_manager.enabled', True)
        self.context_enabled_check.setChecked(enabled)
        self.context_content.setEnabled(enabled)
        # Refresh profiles (plugin may not be ready yet — that's fine)
        if self.context_plugin:
            self._refresh_profile_list()

    def save_config(self):
        if not self.config_manager:
            return True, ""
        self.config_manager.set_setting(
            'plugins.context_manager.enabled',
            self.context_enabled_check.isChecked()
        )
        return True, ""

    def validate(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_context_enabled_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.context_content.setEnabled(enabled)
        if self.config_manager:
            self.config_manager.set_setting('plugins.context_manager.enabled', enabled)
        
        # Notify other tabs via settings coordinator
        try:
            main_window = self.window()
            if hasattr(main_window, 'settings_coordinator') and main_window.settings_coordinator:
                main_window.settings_coordinator.notify_setting_changed(
                    'plugins.context_manager.enabled', enabled, source_tab='context')
        except Exception:
            pass
        
        self.settingChanged.emit()

    def on_setting_changed(self, key: str, value):
        """Handle setting changes from other tabs."""
        if key == 'plugins.context_manager.enabled':
            self.context_enabled_check.blockSignals(True)
            self.context_enabled_check.setChecked(value)
            self.context_enabled_check.blockSignals(False)
            self.context_content.setEnabled(value)

    def _refresh_profile_list(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem(tr("ctx_none_profile"))
        if self.context_plugin:
            for name in sorted(self.context_plugin.get_available_profiles().keys()):
                self.profile_combo.addItem(name)
            active = self.context_plugin.get_active_profile_name()
            if active:
                idx = self.profile_combo.findText(active)
                if idx >= 0:
                    self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)
        self._on_profile_selected(self.profile_combo.currentText())

    def _on_profile_selected(self, name: str):
        if not self.context_plugin or name == tr("ctx_none_profile"):
            self._clear_profile_display()
            return
        if self.context_plugin.load_profile(name):
            self._update_profile_display()
            self.ctx_status_label.setText(tr("ctx_profile_loaded", name=name))
        else:
            self._clear_profile_display()
            self.ctx_status_label.setText(tr("ctx_profile_load_failed", name=name))

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _update_profile_display(self):
        if not self.context_plugin:
            return
        profile = self.context_plugin.get_active_profile()
        if not profile:
            self._clear_profile_display()
            return

        self.ctx_name_edit.setText(profile.name or "")
        self.ctx_category_edit.setText(profile.category or "")
        self.ctx_desc_edit.setPlainText(profile.description or "")

        src_idx = self.ctx_source_lang.findText(profile.source_language)
        self.ctx_source_lang.setCurrentIndex(src_idx if src_idx >= 0 else 0)
        if src_idx < 0:
            self.ctx_source_lang.setCurrentText(profile.source_language)

        tgt_idx = self.ctx_target_lang.findText(profile.target_language)
        self.ctx_target_lang.setCurrentIndex(tgt_idx if tgt_idx >= 0 else 0)
        if tgt_idx < 0:
            self.ctx_target_lang.setCurrentText(profile.target_language)

        ctx = profile.global_context

        # Locked terms
        self.terms_table.setRowCount(0)
        for term in ctx.locked_terms:
            r = self.terms_table.rowCount()
            self.terms_table.insertRow(r)
            self.terms_table.setItem(r, 0, QTableWidgetItem(term.source))
            self.terms_table.setItem(r, 1, QTableWidgetItem(term.target))
            self.terms_table.setItem(r, 2, QTableWidgetItem(term.type))
            self.terms_table.setItem(r, 3, QTableWidgetItem(str(term.priority)))
            cs_item = QTableWidgetItem()
            cs_item.setFlags(cs_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            cs_item.setCheckState(
                Qt.CheckState.Checked if term.case_sensitive else Qt.CheckState.Unchecked
            )
            self.terms_table.setItem(r, 4, cs_item)
            self.terms_table.setItem(r, 5, QTableWidgetItem(term.notes))

        # Translation memory
        self.tm_table.setRowCount(0)
        for entry in ctx.translation_memory:
            r = self.tm_table.rowCount()
            self.tm_table.insertRow(r)
            self.tm_table.setItem(r, 0, QTableWidgetItem(entry.source))
            self.tm_table.setItem(r, 1, QTableWidgetItem(entry.target))
            self.tm_table.setItem(r, 2, QTableWidgetItem(str(entry.priority)))
            self.tm_table.setItem(r, 3, QTableWidgetItem(entry.notes))

        # Regex rules
        self.regex_table.setRowCount(0)
        for rule in ctx.regex_rules:
            r = self.regex_table.rowCount()
            self.regex_table.insertRow(r)
            self.regex_table.setItem(r, 0, QTableWidgetItem(rule.pattern))
            self.regex_table.setItem(r, 1, QTableWidgetItem(rule.action))
            self.regex_table.setItem(r, 2, QTableWidgetItem(rule.replacement))
            self.regex_table.setItem(r, 3, QTableWidgetItem(rule.stage))
            self.regex_table.setItem(r, 4, QTableWidgetItem(rule.description))

        # Formatting
        fmt = ctx.formatting_rules
        self.fmt_honorifics.setChecked(fmt.preserve_honorifics)
        self.fmt_attack_upper.setChecked(fmt.attack_uppercase)
        self.fmt_sfx.setChecked(fmt.translate_sound_effects)
        self.fmt_brackets.setChecked(fmt.preserve_brackets)
        idx = self.fmt_style_combo.findData(fmt.language_style)
        self.fmt_style_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _clear_profile_display(self):
        self.ctx_name_edit.setText("")
        self.ctx_category_edit.setText("")
        self.ctx_desc_edit.clear()
        self.ctx_source_lang.setCurrentIndex(0)
        self.ctx_target_lang.setCurrentIndex(0)
        self.terms_table.setRowCount(0)
        self.tm_table.setRowCount(0)
        self.regex_table.setRowCount(0)
        self.fmt_honorifics.setChecked(False)
        self.fmt_attack_upper.setChecked(False)
        self.fmt_sfx.setChecked(True)
        self.fmt_brackets.setChecked(True)
        self.fmt_style_combo.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Table row helpers
    # ------------------------------------------------------------------

    def _add_locked_term_row(self):
        r = self.terms_table.rowCount()
        self.terms_table.insertRow(r)
        for c, v in enumerate(["", "", "general", "100"]):
            self.terms_table.setItem(r, c, QTableWidgetItem(v))
        cs_item = QTableWidgetItem()
        cs_item.setFlags(cs_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        cs_item.setCheckState(Qt.CheckState.Checked)
        self.terms_table.setItem(r, 4, cs_item)
        self.terms_table.setItem(r, 5, QTableWidgetItem(""))

    def _remove_selected_term(self):
        for row in sorted({i.row() for i in self.terms_table.selectedIndexes()}, reverse=True):
            self.terms_table.removeRow(row)

    def _add_tm_row(self):
        r = self.tm_table.rowCount()
        self.tm_table.insertRow(r)
        for c, v in enumerate(["", "", "50", ""]):
            self.tm_table.setItem(r, c, QTableWidgetItem(v))

    def _remove_selected_tm(self):
        for row in sorted({i.row() for i in self.tm_table.selectedIndexes()}, reverse=True):
            self.tm_table.removeRow(row)

    def _add_regex_row(self):
        r = self.regex_table.rowCount()
        self.regex_table.insertRow(r)
        for c, v in enumerate(["", "preserve", "", "pre", ""]):
            self.regex_table.setItem(r, c, QTableWidgetItem(v))

    def _remove_selected_regex(self):
        for row in sorted({i.row() for i in self.regex_table.selectedIndexes()}, reverse=True):
            self.regex_table.removeRow(row)

    def _open_profiles_folder(self):
        import os
        try:
            d = get_context_profiles_dir()
            d.mkdir(parents=True, exist_ok=True)
            os.startfile(str(d))
        except Exception as e:
            _logger.error("Failed to open profiles folder: %s", e)

    # ------------------------------------------------------------------
    # Save / CRUD
    # ------------------------------------------------------------------

    def _save_profile_from_ui(self):
        if not self.context_plugin:
            self.ctx_status_label.setText(tr("ctx_no_plugin_loaded"))
            return
        profile = self.context_plugin.get_active_profile()
        if not profile:
            self.ctx_status_label.setText(tr("ctx_no_profile_selected"))
            return

        from plugins.enhancers.optimizers.context_manager.context_profile import (
            LockedTerm, TranslationMemoryEntry, RegexRule, FormattingRules
        )

        # Metadata
        new_name = self.ctx_name_edit.text().strip()
        if new_name:
            profile.name = new_name
        new_category = self.ctx_category_edit.text().strip()
        if new_category:
            profile.category = new_category
        desc = self.ctx_desc_edit.toPlainText().strip()
        if desc:
            profile.description = desc
        profile.source_language = self.ctx_source_lang.currentText().strip()
        profile.target_language = self.ctx_target_lang.currentText().strip()

        # Locked terms
        new_terms = []
        for row in range(self.terms_table.rowCount()):
            src = (self.terms_table.item(row, 0) or QTableWidgetItem("")).text().strip()
            tgt = (self.terms_table.item(row, 1) or QTableWidgetItem("")).text().strip()
            ttype = (self.terms_table.item(row, 2) or QTableWidgetItem("general")).text().strip()
            try:
                pri = int((self.terms_table.item(row, 3) or QTableWidgetItem("100")).text())
            except ValueError:
                pri = 100
            cs_item = self.terms_table.item(row, 4)
            case_sensitive = (
                cs_item.checkState() == Qt.CheckState.Checked if cs_item else True
            )
            notes = (self.terms_table.item(row, 5) or QTableWidgetItem("")).text().strip()
            if src and tgt:
                new_terms.append(LockedTerm(
                    source=src, target=tgt, type=ttype,
                    case_sensitive=case_sensitive, priority=pri, notes=notes,
                ))
        profile.global_context.locked_terms = new_terms

        # Translation memory
        new_tm = []
        for row in range(self.tm_table.rowCount()):
            src = (self.tm_table.item(row, 0) or QTableWidgetItem("")).text().strip()
            tgt = (self.tm_table.item(row, 1) or QTableWidgetItem("")).text().strip()
            try:
                pri = int((self.tm_table.item(row, 2) or QTableWidgetItem("50")).text())
            except ValueError:
                pri = 50
            notes = (self.tm_table.item(row, 3) or QTableWidgetItem("")).text().strip()
            if src and tgt:
                new_tm.append(TranslationMemoryEntry(source=src, target=tgt, priority=pri, notes=notes))
        profile.global_context.translation_memory = new_tm

        # Regex rules
        new_rules = []
        for row in range(self.regex_table.rowCount()):
            pat = (self.regex_table.item(row, 0) or QTableWidgetItem("")).text().strip()
            act = (self.regex_table.item(row, 1) or QTableWidgetItem("preserve")).text().strip()
            repl = (self.regex_table.item(row, 2) or QTableWidgetItem("")).text().strip()
            stg = (self.regex_table.item(row, 3) or QTableWidgetItem("pre")).text().strip()
            dsc = (self.regex_table.item(row, 4) or QTableWidgetItem("")).text().strip()
            if pat:
                new_rules.append(RegexRule(pattern=pat, action=act, replacement=repl, stage=stg, description=dsc))
        profile.global_context.regex_rules = new_rules

        # Formatting
        profile.global_context.formatting_rules = FormattingRules(
            preserve_honorifics=self.fmt_honorifics.isChecked(),
            attack_uppercase=self.fmt_attack_upper.isChecked(),
            translate_sound_effects=self.fmt_sfx.isChecked(),
            preserve_brackets=self.fmt_brackets.isChecked(),
            language_style=self.fmt_style_combo.currentData() or self.fmt_style_combo.currentText(),
        )

        if self.context_plugin.save_active_profile():
            self.ctx_status_label.setText(tr("ctx_profile_saved"))
            self.context_plugin.refresh_profiles()
            self._refresh_profile_list()
        else:
            self.ctx_status_label.setText(tr("ctx_profile_save_failed"))

    def _create_new_profile(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, tr("ctx_new_profile_title"), tr("ctx_profile_name_prompt"))
        if not ok or not name.strip():
            return
        if not self.context_plugin:
            self.ctx_status_label.setText(tr("ctx_no_plugin_loaded"))
            return
        profile = self.context_plugin.create_profile(name.strip())
        if profile:
            self._refresh_profile_list()
            idx = self.profile_combo.findText(name.strip())
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
            self.ctx_status_label.setText(tr("ctx_profile_created", name=name.strip()))
        else:
            self.ctx_status_label.setText(tr("ctx_profile_create_failed"))

    def _delete_selected_profile(self):
        name = self.profile_combo.currentText()
        if name == tr("ctx_none_profile"):
            return
        reply = QMessageBox.question(
            self, tr("ctx_delete_profile_title"),
            tr("ctx_delete_profile_confirm", name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.context_plugin and self.context_plugin.delete_profile(name):
            self._refresh_profile_list()
            self.ctx_status_label.setText(tr("ctx_profile_deleted", name=name))
        else:
            self.ctx_status_label.setText(tr("ctx_profile_delete_failed"))

    def _import_profile(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, tr("ctx_import_profile_title"), "", "JSON Files (*.json)")
        if not path or not self.context_plugin:
            return
        imported_name = self.context_plugin.import_profile(path)
        if imported_name:
            self._refresh_profile_list()
            idx = self.profile_combo.findText(imported_name)
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
            self.ctx_status_label.setText(tr("ctx_profile_imported", name=imported_name))
        else:
            detail = getattr(self.context_plugin, '_last_error', '') or ''
            msg = tr("ctx_import_failed")
            if detail:
                msg = f"{msg}\n\n{detail}"
            self.ctx_status_label.setText(tr("ctx_import_failed"))
            QMessageBox.warning(self, tr("ctx_import_profile_title"), msg)

    def _export_profile(self):
        from PyQt6.QtWidgets import QFileDialog
        name = self.profile_combo.currentText()
        if name == tr("ctx_none_profile") or not self.context_plugin:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("ctx_export_profile_title"), f"{name}.json", "JSON Files (*.json)")
        if not path:
            return
        if self.context_plugin.export_profile(name, path):
            self.ctx_status_label.setText(tr("ctx_profile_exported", path=path))
        else:
            detail = getattr(self.context_plugin, '_last_error', '') or ''
            msg = tr("ctx_export_failed")
            if detail:
                msg = f"{msg}\n\n{detail}"
            self.ctx_status_label.setText(tr("ctx_export_failed"))
            QMessageBox.warning(self, tr("ctx_export_profile_title"), msg)
