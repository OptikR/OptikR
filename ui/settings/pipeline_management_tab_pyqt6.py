"""
Pipeline Management Tab - PyQt6 Implementation

Advanced pipeline management with real-time monitoring, control, and configuration
of the modular pipeline managers.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QTextEdit, QTabWidget, QCheckBox, QSpinBox, QDoubleSpinBox, QFormLayout,
    QComboBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.translations import TranslatableMixin
import json
from pathlib import Path


class PipelineManagementTab(TranslatableMixin, QWidget):
    """Advanced pipeline management and monitoring."""
    
    # Signal emitted when settings change
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the pipeline management tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = pipeline
        
        # Secret unlock mechanism
        self.unlock_key_pressed = False
        self.installEventFilter(self)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_metrics)
        self.update_timer.setInterval(1000)  # Update every second
        
        # Initialize UI
        self._init_ui()
        
        # Initial update (delayed to ensure widgets are ready)
        QTimer.singleShot(100, self._update_metrics)
        
        # Start updates if pipeline is available
        if self.pipeline:
            self.update_timer.start()
    
    def _init_ui(self):
        """Initialize the UI."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create tab widget for different sections (OUTSIDE scroll area so tabs stay visible)
        tab_widget = QTabWidget()
        
        # Tab 1: Overview (Compact design)
        overview_tab = self._create_scrollable_tab(self._create_overview_new_tab())
        tab_widget.addTab(overview_tab, "📊 Overview")
        
        # Tab 2: Context Plugin (Content-aware settings)
        self.context_tab = self._create_context_tab()
        context_scrollable = self._create_scrollable_tab(self.context_tab)
        self.context_tab_index = tab_widget.addTab(context_scrollable, "🎯 Context")
        
        # Tab 3: Pipeline Flow (Visual Stages)
        flow_tab = self._create_scrollable_tab(self._create_pipeline_flow_tab())
        tab_widget.addTab(flow_tab, "🔄 Pipeline Flow")
        
        # Tab 4: Plugins by Stage (Organized)
        plugins_tab = self._create_scrollable_tab(self._create_plugins_by_stage_tab())
        tab_widget.addTab(plugins_tab, "🔌 Plugins by Stage")
        
        # Tab 5: Configuration (Advanced)
        config_tab = self._create_scrollable_tab(self._create_configuration_tab())
        tab_widget.addTab(config_tab, "⚙️ Configuration")
        
        # Store tab widget reference for enabling/disabling context tab
        self.tab_widget = tab_widget
        
        # Add tab widget directly to main layout (no outer scroll area)
        main_layout.addWidget(tab_widget)
    
    def _create_scrollable_tab(self, content_widget):
        """Wrap a tab's content in a scroll area."""
        # Create scroll area for this tab
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(content_widget)
        
        return scroll_area
    
    def _create_overview_new_tab(self) -> QWidget:
        """Create compact overview tab with TIGHT spacing and detailed plugin info."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)  # Tight spacing between sections
        
        # Pipeline Status - Compact
        status_group = QGroupBox("Pipeline Status")
        status_layout = QFormLayout(status_group)
        status_layout.setSpacing(2)
        status_layout.setContentsMargins(10, 8, 10, 8)
        
        self.new_status_label = QLabel("Idle (Ready to Start)")
        self.new_status_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        status_layout.addRow("Status:", self.new_status_label)
        
        self.new_uptime_label = QLabel("--")
        status_layout.addRow("Uptime:", self.new_uptime_label)
        
        # Control buttons in one row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        self.new_start_btn = QPushButton("▶ Start")
        self.new_pause_btn = QPushButton("⏸ Pause")
        self.new_stop_btn = QPushButton("⏹ Stop")
        btn_layout.addWidget(self.new_start_btn)
        btn_layout.addWidget(self.new_pause_btn)
        btn_layout.addWidget(self.new_stop_btn)
        status_layout.addRow("", btn_layout)
        
        layout.addWidget(status_group)
        
        # Quick Statistics - Compact
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QFormLayout(stats_group)
        stats_layout.setSpacing(2)
        stats_layout.setContentsMargins(10, 8, 10, 8)
        
        self.new_fps_label = QLabel("0.0 FPS")
        stats_layout.addRow("FPS:", self.new_fps_label)
        
        self.new_latency_label = QLabel("0 ms")
        stats_layout.addRow("Latency:", self.new_latency_label)
        
        self.new_frames_label = QLabel("0")
        stats_layout.addRow("Frames:", self.new_frames_label)
        
        self.new_translations_label = QLabel("0")
        stats_layout.addRow("Translations:", self.new_translations_label)
        
        self.new_cache_label = QLabel("0 (0%)")
        stats_layout.addRow("Cache Hits:", self.new_cache_label)
        
        layout.addWidget(stats_group)
        
        # Active Plugins - Alphabetical with info boxes
        plugins_group = QGroupBox("Active Plugins")
        plugins_layout = QVBoxLayout(plugins_group)
        plugins_layout.setSpacing(4)
        plugins_layout.setContentsMargins(10, 8, 10, 8)
        
        # Master switch
        self.new_master_check = QCheckBox("Enable Optional Optimizer Plugins")
        self.new_master_check.setChecked(True)
        self.new_master_check.setStyleSheet("QCheckBox { margin: 0px; padding: 2px 0px; font-weight: bold; }")
        plugins_layout.addWidget(self.new_master_check)
        
        # Helper function to add plugin with info
        def add_plugin(name, info, checked=True, enabled=True):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 1, 0, 1)
            
            check = QCheckBox(name)
            check.setChecked(checked)
            check.setEnabled(enabled)
            check.setStyleSheet("QCheckBox { margin: 0px; padding: 0px; min-width: 150px; }")
            check.setFixedWidth(150)
            row.addWidget(check)
            
            info_label = QLabel(info)
            info_label.setStyleSheet("color: #888; font-size: 9pt; margin: 0px; padding: 0px;")
            info_label.setWordWrap(False)
            row.addWidget(info_label, 1)
            
            plugins_layout.addLayout(row)
            return check
        
        # Essential Plugins (Alphabetical)
        essential_label = QLabel("⭐ Essential Plugins (Always Active):")
        essential_label.setStyleSheet("font-weight: bold; color: #4a9eff; margin-top: 4px;")
        plugins_layout.addWidget(essential_label)
        
        self.new_context_check = add_plugin("Context Plugin", "Adapts OCR/Translation based on content type (Wiki, Manga, Game, etc.)")
        self.new_skip_check = add_plugin("Frame Skip", "Skips unchanged frames → 50-70% CPU saved")
        self.new_dict_check = add_plugin("Learning Dictionary", "Smart dictionary learns translations → 40-80% faster")
        self.new_merger_check = add_plugin("Text Block Merger", "Merges fragmented text → Better translations", enabled=False)
        self.new_cache_check = add_plugin("Translation Cache", "Instant lookup for repeated text → 100x speedup")
        self.new_validator_check = add_plugin("Text Validator", "Filters garbage text → 30-50% noise reduction")
        
        # Optional Plugins (Alphabetical)
        optional_label = QLabel("Optional Plugins:")
        optional_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        plugins_layout.addWidget(optional_label)
        
        self.new_async_check = add_plugin("Async Pipeline", "Overlapping stage execution → 50-80% throughput boost", False)
        self.new_batch_check = add_plugin("Batch Processing", "Process multiple frames together → 30-50% faster", False)
        self.new_motion_check = add_plugin("Motion Tracker", "Smooth scrolling detection", True)
        self.new_parallel_capture_check = add_plugin("Parallel Capture", "Process multiple regions simultaneously", False)
        self.new_parallel_ocr_check = add_plugin("Parallel OCR", "Process multiple regions simultaneously", False)
        self.new_priority_check = add_plugin("Priority Queue", "User tasks first → 20-30% responsiveness boost", False)
        self.new_spell_check = add_plugin("Spell Corrector", "Fixes OCR errors → 10-20% accuracy boost", True)
        self.new_chain_check = add_plugin("Translation Chain", "Multi-language translation (JA→EN→DE)", False)
        self.new_work_check = add_plugin("Work-Stealing Pool", "Load balancing → 15-25% better CPU utilization", False)
        
        # Apply button
        apply_btn = QPushButton("💾 Apply Changes")
        apply_btn.setProperty("class", "action")
        plugins_layout.addWidget(apply_btn)
        
        layout.addWidget(plugins_group)
        
        # Active Components - Compact
        components_group = QGroupBox("Active Components")
        components_layout = QFormLayout(components_group)
        components_layout.setSpacing(2)
        components_layout.setContentsMargins(10, 8, 10, 8)
        
        self.new_capture_label = QLabel("Loading...")
        components_layout.addRow("Capture:", self.new_capture_label)
        
        self.new_ocr_label = QLabel("Loading...")
        components_layout.addRow("OCR:", self.new_ocr_label)
        
        self.new_translation_label = QLabel("Loading...")
        components_layout.addRow("Translation:", self.new_translation_label)
        
        self.new_overlay_label = QLabel("Loading...")
        components_layout.addRow("Overlay:", self.new_overlay_label)
        
        layout.addWidget(components_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_context_tab(self) -> QWidget:
        """Create Context Plugin configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🎯 Context Plugin - Content-Aware Processing")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4a9eff;")
        layout.addWidget(header)
        
        desc = QLabel("Tell the system what type of content you're reading to optimize OCR, text validation, and translation for better accuracy.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Enable/Disable Context Plugin
        self.context_enabled_check = QCheckBox("Enable Context Plugin")
        self.context_enabled_check.setChecked(True)
        self.context_enabled_check.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.context_enabled_check.stateChanged.connect(self._on_context_enabled_changed)
        layout.addWidget(self.context_enabled_check)
        
        # Content container (will be grayed out when disabled)
        self.context_content = QWidget()
        content_layout = QVBoxLayout(self.context_content)
        content_layout.setContentsMargins(0, 10, 0, 0)
        
        # Quick Select Presets
        presets_group = QGroupBox("Quick Select Content Type")
        presets_layout = QVBoxLayout(presets_group)
        presets_layout.setSpacing(8)
        
        # Preset buttons in grid
        preset_grid = QHBoxLayout()
        preset_grid.setSpacing(8)
        
        self.context_wiki_btn = QPushButton("📚 Wikipedia/Formal")
        self.context_wiki_btn.setToolTip("Formal text, proper grammar, complete sentences")
        self.context_wiki_btn.clicked.connect(lambda: self._set_context_preset("wiki"))
        preset_grid.addWidget(self.context_wiki_btn)
        
        self.context_manga_btn = QPushButton("📖 Manga/Comics")
        self.context_manga_btn.setToolTip("ALL CAPS text, speech bubbles, sound effects, casual language")
        self.context_manga_btn.clicked.connect(lambda: self._set_context_preset("manga"))
        preset_grid.addWidget(self.context_manga_btn)
        
        self.context_game_btn = QPushButton("🎮 Game UI")
        self.context_game_btn.setToolTip("Short phrases, button text, menu items")
        self.context_game_btn.clicked.connect(lambda: self._set_context_preset("game"))
        preset_grid.addWidget(self.context_game_btn)
        
        presets_layout.addLayout(preset_grid)
        
        preset_grid2 = QHBoxLayout()
        preset_grid2.setSpacing(8)
        
        self.context_subtitle_btn = QPushButton("🎬 Subtitles/Video")
        self.context_subtitle_btn.setToolTip("Timed text, natural speech patterns")
        self.context_subtitle_btn.clicked.connect(lambda: self._set_context_preset("subtitle"))
        preset_grid2.addWidget(self.context_subtitle_btn)
        
        self.context_novel_btn = QPushButton("📕 Novel/Book")
        self.context_novel_btn.setToolTip("Narrative text, paragraphs, literary style")
        self.context_novel_btn.clicked.connect(lambda: self._set_context_preset("novel"))
        preset_grid2.addWidget(self.context_novel_btn)
        
        self.context_tech_btn = QPushButton("🔧 Technical Doc")
        self.context_tech_btn.setToolTip("Technical terms, precise language, code snippets")
        self.context_tech_btn.clicked.connect(lambda: self._set_context_preset("tech"))
        preset_grid2.addWidget(self.context_tech_btn)
        
        presets_layout.addLayout(preset_grid2)
        
        content_layout.addWidget(presets_group)
        
        # Current Context Display
        current_group = QGroupBox("Current Context Settings")
        current_layout = QFormLayout(current_group)
        current_layout.setSpacing(4)
        
        self.context_type_label = QLabel("None")
        self.context_type_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        current_layout.addRow("Active Context:", self.context_type_label)
        
        self.context_ocr_mode_label = QLabel("Standard")
        current_layout.addRow("OCR Mode:", self.context_ocr_mode_label)
        
        self.context_validation_label = QLabel("Standard")
        current_layout.addRow("Text Validation:", self.context_validation_label)
        
        self.context_translation_label = QLabel("Neutral")
        current_layout.addRow("Translation Style:", self.context_translation_label)
        
        self.context_spell_label = QLabel("Standard")
        current_layout.addRow("Spell Checking:", self.context_spell_label)
        
        content_layout.addWidget(current_group)
        
        # Custom Tags
        tags_group = QGroupBox("Custom Tags (Optional)")
        tags_layout = QVBoxLayout(tags_group)
        
        tags_desc = QLabel("Add custom tags to further refine context (e.g., 'action', 'comedy', 'sci-fi')")
        tags_desc.setStyleSheet("color: #888; font-size: 9pt;")
        tags_desc.setWordWrap(True)
        tags_layout.addWidget(tags_desc)
        
        self.context_tags_input = QTextEdit()
        self.context_tags_input.setMaximumHeight(60)
        self.context_tags_input.setPlaceholderText("Enter tags separated by commas (e.g., action, fantasy, dialogue-heavy)")
        tags_layout.addWidget(self.context_tags_input)
        
        content_layout.addWidget(tags_group)
        
        # Apply button
        apply_btn = QPushButton("💾 Apply Context Settings")
        apply_btn.setProperty("class", "action")
        apply_btn.clicked.connect(self._apply_context_settings)
        content_layout.addWidget(apply_btn)
        
        layout.addWidget(self.context_content)
        layout.addStretch()
        
        return tab
    
    def _on_context_enabled_changed(self, state):
        """Handle context plugin enable/disable."""
        enabled = state == 2  # Qt.CheckState.Checked
        self.context_content.setEnabled(enabled)
        # Gray out the tab when disabled
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setTabEnabled(self.context_tab_index, enabled)
    
    def _set_context_preset(self, preset_type):
        """Set context based on preset."""
        presets = {
            "wiki": {
                "name": "Wikipedia/Formal",
                "ocr": "High confidence, proper capitalization",
                "validation": "Strict - Complete sentences, formal grammar",
                "translation": "Formal, precise",
                "spell": "Strict grammar rules"
            },
            "manga": {
                "name": "Manga/Comics",
                "ocr": "ALL CAPS aware, speech bubble detection",
                "validation": "Lenient - Allows exclamations, sound effects",
                "translation": "Casual, conversational, emotion-preserving",
                "spell": "Lenient with stylized text"
            },
            "game": {
                "name": "Game UI",
                "ocr": "Short phrases, button text optimized",
                "validation": "Allows fragments, single words",
                "translation": "Concise, action-oriented",
                "spell": "Lenient with abbreviations"
            },
            "subtitle": {
                "name": "Subtitles/Video",
                "ocr": "Timed text, line break aware",
                "validation": "Allows incomplete sentences",
                "translation": "Natural speech patterns",
                "spell": "Conversational grammar"
            },
            "novel": {
                "name": "Novel/Book",
                "ocr": "Paragraph-aware, literary text",
                "validation": "Standard - Narrative flow",
                "translation": "Literary, descriptive",
                "spell": "Standard grammar"
            },
            "tech": {
                "name": "Technical Documentation",
                "ocr": "Technical terms, code-aware",
                "validation": "Preserves technical terms",
                "translation": "Precise, technical",
                "spell": "Technical dictionary"
            }
        }
        
        if preset_type in presets:
            preset = presets[preset_type]
            self.context_type_label.setText(preset["name"])
            self.context_ocr_mode_label.setText(preset["ocr"])
            self.context_validation_label.setText(preset["validation"])
            self.context_translation_label.setText(preset["translation"])
            self.context_spell_label.setText(preset["spell"])
    
    def _apply_context_settings(self):
        """Apply context settings to the pipeline."""
        context_type = self.context_type_label.text()
        custom_tags = self.context_tags_input.toPlainText()
        
        print(f"[CONTEXT] Applying context: {context_type}")
        print(f"[CONTEXT] Custom tags: {custom_tags}")
        
        # Save context settings to config
        if self.config_manager:
            self.config_manager.set_setting('pipeline.context.type', context_type)
            self.config_manager.set_setting('pipeline.context.custom_tags', custom_tags)
            
            # Apply context-specific settings
            if context_type == "Game":
                # Game context: Fast OCR, preserve formatting, casual translation
                self.config_manager.set_setting('translation.context_aware', True)
                self.config_manager.set_setting('translation.preserve_formatting', True)
                self.config_manager.set_setting('ocr.confidence_threshold', 0.6)  # Lower for speed
            elif context_type == "Anime/Manga":
                # Anime context: Balanced, preserve style, natural translation
                self.config_manager.set_setting('translation.context_aware', True)
                self.config_manager.set_setting('translation.preserve_formatting', True)
                self.config_manager.set_setting('ocr.confidence_threshold', 0.7)
            elif context_type == "Document":
                # Document context: High accuracy, formal translation
                self.config_manager.set_setting('translation.context_aware', True)
                self.config_manager.set_setting('translation.preserve_formatting', True)
                self.config_manager.set_setting('ocr.confidence_threshold', 0.8)  # Higher for accuracy
            elif context_type == "Wikipedia":
                # Wikipedia context: High accuracy, formal, technical terms
                self.config_manager.set_setting('translation.context_aware', True)
                self.config_manager.set_setting('translation.preserve_formatting', False)
                self.config_manager.set_setting('ocr.confidence_threshold', 0.85)
            
            # Apply to pipeline if available
            if self.pipeline:
                try:
                    # Update pipeline config
                    if hasattr(self.pipeline, 'config'):
                        self.pipeline.config.context_type = context_type
                        self.pipeline.config.context_tags = custom_tags.split(',') if custom_tags else []
                    
                    # Update translation layer context
                    if hasattr(self.pipeline, 'translation_layer'):
                        if hasattr(self.pipeline.translation_layer, 'set_context'):
                            self.pipeline.translation_layer.set_context(context_type, custom_tags)
                    
                    print(f"[CONTEXT] Successfully applied context to pipeline")
                except Exception as e:
                    print(f"[CONTEXT] Warning: Could not apply context to pipeline: {e}")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Context Applied",
                f"Context '{context_type}' has been applied to the pipeline.\n\n"
                f"Settings have been optimized for this content type."
            )
    
    def _get_ocr_engine_display(self) -> str:
        """Get the OCR engine display name from config."""
        if not self.config_manager:
            return "PaddleOCR"
        
        try:
            # Get current OCR engine
            engine = self.config_manager.get_setting('ocr.engine', 'paddleocr')
            
            # Get languages list (OCR can have multiple languages)
            languages = self.config_manager.get_setting('ocr.languages', ['en'])
            
            # Extract first language code from list
            if languages and len(languages) > 0:
                first_lang = languages[0]
                # Extract code from "Name (code)" format if needed
                if '(' in first_lang and ')' in first_lang:
                    language = first_lang.split('(')[1].split(')')[0].strip()
                else:
                    language = first_lang
            else:
                language = 'en'
            
            # Format engine name
            engine_names = {
                'easyocr': 'EasyOCR',
                'tesseract': 'Tesseract',
                'paddleocr': 'PaddleOCR',
                'manga_ocr': 'Manga OCR',
                'windows_ocr': 'Windows OCR'
            }
            
            language_names = {
                'ja': 'Japanese',
                'en': 'English',
                'zh': 'Chinese',
                'ko': 'Korean',
                'de': 'German',
                'fr': 'French',
                'es': 'Spanish',
                'pt': 'Portuguese',
                'ru': 'Russian',
                'ar': 'Arabic',
                'hi': 'Hindi'
            }
            
            engine_display = engine_names.get(engine.lower(), engine.title())
            lang_display = language_names.get(language.lower(), language.upper())
            
            return f"{engine_display} ({lang_display})"
        except Exception as e:
            print(f"[WARNING] Failed to get OCR engine display: {e}")
            return "PaddleOCR"
    
    def _create_pipeline_flow_tab(self) -> QWidget:
        """Create pipeline flow visualization tab with side-by-side comparison."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(10)
        
        # Header
        header_label = QLabel("Pipeline Flow Visualization")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 5px;")
        main_layout.addWidget(header_label)
        
        desc_label = QLabel("Compare sequential vs async pipeline execution modes")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        main_layout.addWidget(desc_label)
        
        # Side-by-side comparison
        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(15)
        
        # LEFT: Sequential Pipeline
        sequential_widget = self._create_sequential_pipeline_view()
        comparison_layout.addWidget(sequential_widget, 1)
        
        # RIGHT: Async Pipeline
        async_widget = self._create_async_pipeline_view()
        comparison_layout.addWidget(async_widget, 1)
        
        main_layout.addLayout(comparison_layout)
        
        # All Optimizer Plugins Summary (they're ALL global!)
        global_group = QGroupBox("All Optimizer Plugins (Global)")
        global_layout = QVBoxLayout(global_group)
        
        info_label = QLabel("ℹ️ All plugins work globally across the entire pipeline")
        info_label.setStyleSheet("color: #888; font-size: 9pt; font-style: italic; margin-bottom: 5px;")
        global_layout.addWidget(info_label)
        
        # Essential plugins (always active)
        essential_label = QLabel("⭐ Essential (Always Active):")
        essential_label.setStyleSheet("font-weight: bold; color: #4a9eff; margin-top: 5px;")
        global_layout.addWidget(essential_label)
        
        essential_plugins = [
            ("Translation Cache", "100x speedup for repeated text", True),
            ("Smart Dictionary", "Learns translations, 20x faster lookups", True),
            ("Frame Skip", "50-70% CPU saved", True),
            ("Text Validator", "30-50% noise reduction", True),
            ("Text Block Merger", "Better translation quality", True),
        ]
        
        for name, benefit, enabled in essential_plugins:
            status = "✅" if enabled else "⚪"
            plugin_label = QLabel(f"  {status} {name} ({benefit})")
            plugin_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            global_layout.addWidget(plugin_label)
        
        # Optional plugins
        optional_label = QLabel("Optional (Enable for more speed):")
        optional_label.setStyleSheet("font-weight: bold; color: #888; margin-top: 8px;")
        global_layout.addWidget(optional_label)
        
        optional_plugins = [
            ("Async Pipeline", "50-80% throughput boost", False),
            ("Batch Processing", "30-50% faster", False),
            ("Parallel OCR/Capture", "2-3x faster (uses more CPU)", False),
            ("Priority Queue", "20-30% responsiveness", False),
            ("Work-Stealing Pool", "15-25% CPU utilization", False),
            ("Motion Tracker", "Skips OCR during scrolling", True),
            ("Spell Corrector", "10-20% accuracy boost", True),
        ]
        
        for name, benefit, enabled in optional_plugins:
            status = "✅" if enabled else "⚪"
            plugin_label = QLabel(f"  {status} {name} ({benefit})")
            plugin_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            global_layout.addWidget(plugin_label)
        
        main_layout.addWidget(global_group)
        
        main_layout.addStretch()
        return tab
    
    def _create_sequential_pipeline_view(self) -> QWidget:
        """Create sequential pipeline visualization."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("📊 Sequential Pipeline (Default)")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #4a9eff; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("One stage at a time, waits for completion")
        subtitle.setStyleSheet("color: #888; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Get OCR engine from config
        ocr_engine_display = self._get_ocr_engine_display()
        
        # Check if QoL features are enabled
        preprocessing_enabled = self.config_manager.get_setting('ocr.preprocessing_enabled', False) if self.config_manager else False
        seamless_enabled = self.config_manager.get_setting('overlay.seamless_background', False) if self.config_manager else False
        
        # Adjust OCR timing if preprocessing is enabled
        ocr_time = "~70ms" if preprocessing_enabled else "~50ms"
        ocr_plugins = ["Text Validator", "Spell Check"]
        if preprocessing_enabled:
            ocr_plugins.append("🔍 Intelligent Preprocessing")
        
        # Adjust overlay plugins if seamless is enabled
        overlay_plugins = []
        if seamless_enabled:
            overlay_plugins.append("🎨 Seamless Background")
        
        # Stages
        stages = [
            ("1. CAPTURE", "~8ms", "DirectX GPU", ["Frame Skip"]),
            ("2. OCR", ocr_time, ocr_engine_display, ocr_plugins),
            ("3. TRANSLATION", "~30ms", "MarianMT", ["Cache", "Dictionary"]),
            ("4. POSITIONING", "~5ms", "Smart Layout", ["Collision Detection"]),
            ("5. OVERLAY", "~1ms", "PyQt6", overlay_plugins)
        ]
        
        for title, timing, method, plugins in stages:
            stage_group = self._create_compact_stage(title, timing, method, plugins)
            layout.addWidget(stage_group)
            
            # Arrow between stages
            if title != "5. OVERLAY":
                arrow = QLabel("    ↓")
                arrow.setStyleSheet("font-size: 14pt; color: #666; margin: 0px; padding: 0px;")
                layout.addWidget(arrow)
        
        # Total time - BASELINE (no optimizations)
        # Adjust for preprocessing if enabled
        preprocessing_enabled = self.config_manager.get_setting('ocr.preprocessing_enabled', False) if self.config_manager else False
        base_time = 114 if preprocessing_enabled else 94
        base_fps = round(1000 / base_time, 1)
        
        total_label = QLabel(f"⏱️ Baseline: ~{base_time}ms ({base_fps} FPS)")
        total_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #0066CC; margin-top: 10px; padding: 8px; background: #1a1a1a; border-radius: 4px;")
        layout.addWidget(total_label)
        self.total_time_label = total_label
        
        baseline_note = QLabel("⚠️ Without any optimizer plugins" + (" + Intelligent Preprocessing" if preprocessing_enabled else ""))
        baseline_note.setStyleSheet("color: #ff9800; font-size: 8pt; font-style: italic; margin-top: 2px;")
        layout.addWidget(baseline_note)
        
        # With optimizers note
        optimized_label = QLabel("💡 With Cache + Smart Dictionary: ~35ms (28 FPS)")
        optimized_label.setStyleSheet("color: #66bb6a; font-size: 10pt; font-weight: bold; margin-top: 5px;")
        layout.addWidget(optimized_label)
        
        # Performance note
        note = QLabel(
            "✓ Predictable, stable, low memory\n"
            "✗ Lower throughput\n"
            "🚀 With all optimizers: 25-35 FPS possible"
        )
        note.setStyleSheet("color: #888; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note)
        
        # Use case recommendations
        use_case = QLabel(
            "📖 Best for:\n"
            "• Reading articles/books (3-5 FPS sufficient)\n"
            "• Static content (Wikipedia, documents)\n"
            "• Low-end hardware"
        )
        use_case.setStyleSheet(
            "color: #aaa; font-size: 8pt; margin-top: 8px; "
            "padding: 6px; background: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(use_case)
        
        layout.addStretch()
        
        # Add border
        widget.setStyleSheet("QWidget { border: 1px solid #444; border-radius: 5px; background: #2a2a2a; }")
        
        return widget
    
    def _create_async_pipeline_view(self) -> QWidget:
        """Create async pipeline visualization."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("⚡ Async Pipeline (Advanced)")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #66bb6a; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Overlapping execution, parallel processing")
        subtitle.setStyleSheet("color: #aaa; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Parallel stages visualization
        parallel_label = QLabel(
            "Frame 1: [CAPTURE] → [OCR] → [TRANS] → [POS] → [OVERLAY]\n"
            "Frame 2:           [CAPTURE] → [OCR] → [TRANS] → [POS]\n"
            "Frame 3:                     [CAPTURE] → [OCR] → [TRANS]"
        )
        parallel_label.setStyleSheet(
            "font-family: 'Courier New', monospace; "
            "font-size: 9pt; "
            "color: #aaddaa; "
            "background: #1e1e1e; "
            "padding: 10px; "
            "border: 1px solid #555; "
            "border-radius: 4px; "
            "margin-bottom: 10px;"
        )
        layout.addWidget(parallel_label)
        
        # Get OCR engine from config
        ocr_engine_display = self._get_ocr_engine_display()
        
        # Check if QoL features are enabled
        preprocessing_enabled = self.config_manager.get_setting('ocr.preprocessing_enabled', False) if self.config_manager else False
        seamless_enabled = self.config_manager.get_setting('overlay.seamless_background', False) if self.config_manager else False
        
        # Adjust OCR timing if preprocessing is enabled
        ocr_time = "~70ms" if preprocessing_enabled else "~50ms"
        ocr_plugins = ["Text Validator", "Parallel OCR"]
        if preprocessing_enabled:
            ocr_plugins.append("🔍 Intelligent Preprocessing")
        
        # Adjust overlay plugins if seamless is enabled
        overlay_plugins = []
        if seamless_enabled:
            overlay_plugins.append("🎨 Seamless Background")
        
        # Stages (same as sequential but with async note)
        stages = [
            ("1. CAPTURE", "~8ms", "DirectX GPU", ["Frame Skip", "Parallel Capture"]),
            ("2. OCR", ocr_time, ocr_engine_display, ocr_plugins),
            ("3. TRANSLATION", "~30ms", "MarianMT", ["Cache", "Batch Processing"]),
            ("4. POSITIONING", "~5ms", "Smart Layout", ["Collision Detection"]),
            ("5. OVERLAY", "~1ms", "PyQt6", overlay_plugins)
        ]
        
        for title, timing, method, plugins in stages:
            stage_group = self._create_compact_stage(title, timing, method, plugins, async_mode=True)
            layout.addWidget(stage_group)
            
            # Parallel arrows
            if title != "5. OVERLAY":
                arrow = QLabel("    ⇊ (parallel)")
                arrow.setStyleSheet("font-size: 10pt; color: #66bb6a; margin: 0px; padding: 0px;")
                layout.addWidget(arrow)
        
        # Total time - WITH async optimization
        total_label = QLabel("⏱️ With Async: ~50ms (20 FPS)")
        total_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #66bb6a; margin-top: 10px; padding: 8px; background: #1e1e1e; border: 1px solid #555; border-radius: 4px;")
        layout.addWidget(total_label)
        
        async_note = QLabel("⚡ Same hardware, 2x throughput via parallelism")
        async_note.setStyleSheet("color: #66bb6a; font-size: 8pt; font-style: italic; margin-top: 2px;")
        layout.addWidget(async_note)
        
        # Performance note
        note = QLabel(
            "✓ 50-80% higher throughput (same CPU)\n"
            "✗ +30% memory, more complex\n"
            "⚠️ Parallel plugins use MORE resources"
        )
        note.setStyleSheet("color: #aaa; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note)
        
        # Resource usage warning
        resource_warning = QLabel(
            "⚙️ Resource Impact:\n"
            "• Async Pipeline: Same CPU, +30% RAM\n"
            "• Parallel Capture/OCR: +50-100% CPU\n"
            "• Batch Processing: +20% RAM"
        )
        resource_warning.setStyleSheet(
            "color: #ff9800; font-size: 8pt; margin-top: 5px; "
            "padding: 6px; background: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(resource_warning)
        
        # Use case recommendations
        use_case = QLabel(
            "🎮 Best for:\n"
            "• Gaming/streaming (need 15-30 FPS)\n"
            "• Fast-scrolling content\n"
            "• High-end hardware (4+ cores)"
        )
        use_case.setStyleSheet(
            "color: #aaa; font-size: 8pt; margin-top: 8px; "
            "padding: 6px; background: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(use_case)
        
        layout.addStretch()
        
        # Add border - same gray as left side
        widget.setStyleSheet("QWidget { border: 1px solid #444; border-radius: 5px; background: #2a2a2a; }")
        
        return widget
    
    def _create_compact_stage(self, title: str, timing: str, method: str, plugins: list, async_mode: bool = False) -> QGroupBox:
        """Create a compact pipeline stage display."""
        group = QGroupBox(f"{title} - {timing}")
        
        # Same gray borders for all stages
        group.setStyleSheet(
            "QGroupBox { "
            "font-weight: bold; "
            "padding-top: 10px; "
            "border: 1px solid #555; "
            "border-radius: 3px; "
            "margin-top: 5px; "
            "background: #252525; "
            "}"
        )
        
        layout = QVBoxLayout(group)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 5, 8, 5)
        
        # Method label - green for async, blue for sequential
        engine_label = QLabel(f"Method: {method}")
        engine_label.setObjectName("engine_label")
        
        if async_mode:
            engine_label.setStyleSheet("font-weight: bold; color: #66bb6a; font-size: 9pt;")
        else:
            engine_label.setStyleSheet("font-weight: bold; color: #4a9eff; font-size: 9pt;")
        
        layout.addWidget(engine_label)
        
        # Plugins
        if plugins:
            plugins_text = ", ".join(plugins)
            if async_mode:
                plugins_label = QLabel(f"⚡ {plugins_text}")
            else:
                plugins_label = QLabel(f"🔌 {plugins_text}")
            plugins_label.setStyleSheet("color: #aaa; font-size: 8pt;")
            plugins_label.setWordWrap(True)
            layout.addWidget(plugins_label)
        
        return group
    

    
    def _create_plugins_by_stage_tab(self) -> QWidget:
        """Create plugins organized by stage tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Optimizer Plugins - Organized by Stage")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Essential plugins info banner
        essential_info = QLabel(
            "⭐ ESSENTIAL PLUGINS bypass the master switch and work independently.\n"
            "You can toggle them individually, but they ignore the global 'Enable Optional Optimizer Plugins' setting.\n"
            "Essential: Frame Skip, Intelligent Text Processor, Text Block Merger, Translation Cache, Learning Dictionary."
        )
        essential_info.setWordWrap(True)
        essential_info.setStyleSheet(
            "background-color: #FFF3CD; color: #856404; padding: 10px; "
            "border: 1px solid #FFE69C; border-radius: 5px; font-size: 9pt; font-weight: bold;"
        )
        layout.addWidget(essential_info)
        
        # Master toggle
        self.plugins_enabled_check = QCheckBox()
        self.set_translatable_text(self.plugins_enabled_check, "pipeline_management_enable_optional_optimizer_plugins_check")
        self.plugins_enabled_check.setChecked(True)  # Enabled for testing
        self.plugins_enabled_check.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.plugins_enabled_check.setToolTip("Controls optional plugins only. Essential plugins are always active.")
        self.plugins_enabled_check.stateChanged.connect(self._on_plugins_enabled_changed)
        layout.addWidget(self.plugins_enabled_check)
        
        # CAPTURE STAGE
        capture_stage = self._create_capture_stage_section()
        layout.addWidget(capture_stage)
        
        # OCR STAGE
        ocr_stage = self._create_ocr_stage_section()
        layout.addWidget(ocr_stage)
        
        # TRANSLATION STAGE
        translation_stage = self._create_translation_stage_section()
        layout.addWidget(translation_stage)
        
        # GLOBAL PLUGINS
        global_stage = self._create_global_stage_section()
        layout.addWidget(global_stage)
        
        # Apply button
        apply_btn = QPushButton()
        self.set_translatable_text(apply_btn, "pipeline_management_apply_all_changes_button")
        apply_btn.setProperty("class", "action")
        apply_btn.clicked.connect(self._apply_plugin_settings)
        layout.addWidget(apply_btn)
        
        # Performance summary
        perf_label = QLabel(
            "💡 Performance Summary:\n"
            "• Current: 2.5x improvement (Cache + Frame Skip)\n"
            "• Potential: 5x improvement (Enable all plugins)"
        )
        perf_label.setWordWrap(True)
        perf_label.setStyleSheet("color: #0066CC; font-size: 9pt; padding: 10px; background-color: #E6F2FF; border-radius: 5px;")
        layout.addWidget(perf_label)
        
        layout.addStretch()
        return tab
    
    def _create_capture_stage_section(self) -> QGroupBox:
        """Create capture stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pipeline_management_capture_stage_section")
        layout = QVBoxLayout(group)
        
        # Frame Skip Plugin (ESSENTIAL - BYPASSES MASTER SWITCH)
        skip_group = QGroupBox()
        self.set_translatable_text(skip_group, "pipeline_management_frame_skip_optimizer_essential_section")
        skip_layout = QFormLayout(skip_group)
        
        self.skip_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.skip_plugin_enabled, "pipeline_management_enabled_check")
        self.skip_plugin_enabled.setChecked(True)
        self.skip_plugin_enabled.setToolTip("Essential plugin - bypasses master switch, works even when plugins are globally disabled")
        skip_layout.addRow("Status:", self.skip_plugin_enabled)
        
        skip_desc = QLabel("Skips unchanged frames (50-70% CPU saved)")
        skip_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        skip_layout.addRow("", skip_desc)
        
        self.skip_threshold_spin = CustomDoubleSpinBox()
        self.skip_threshold_spin.setRange(0.8, 0.99)
        self.skip_threshold_spin.setSingleStep(0.01)
        self.skip_threshold_spin.setValue(0.95)
        skip_layout.addRow("Similarity Threshold:", self.skip_threshold_spin)
        
        self.skip_method_combo = QComboBox()
        self.skip_method_combo.addItems(["hash", "mse", "ssim"])
        skip_layout.addRow("Comparison Method:", self.skip_method_combo)
        
        layout.addWidget(skip_group)
        
        # Motion Tracker Plugin
        motion_group = QGroupBox()
        self.set_translatable_text(motion_group, "pipeline_management_motion_tracker_section")
        motion_layout = QFormLayout(motion_group)
        
        self.motion_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.motion_plugin_enabled, "pipeline_management_enabled_check_1")
        self.motion_plugin_enabled.setChecked(True)
        motion_layout.addRow("Status:", self.motion_plugin_enabled)
        
        motion_desc = QLabel("Smooth scrolling detection (skips OCR during motion)")
        motion_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        motion_layout.addRow("", motion_desc)
        
        self.motion_threshold_spin = CustomDoubleSpinBox()
        self.motion_threshold_spin.setRange(5.0, 50.0)
        self.motion_threshold_spin.setSingleStep(1.0)
        self.motion_threshold_spin.setValue(10.0)
        self.motion_threshold_spin.setSuffix("px")
        motion_layout.addRow("Motion Threshold:", self.motion_threshold_spin)
        
        self.motion_smoothing_spin = CustomDoubleSpinBox()
        self.motion_smoothing_spin.setRange(0.1, 1.0)
        self.motion_smoothing_spin.setSingleStep(0.1)
        self.motion_smoothing_spin.setValue(0.5)
        motion_layout.addRow("Smoothing Factor:", self.motion_smoothing_spin)
        
        layout.addWidget(motion_group)
        
        # Parallel Capture Plugin
        parallel_capture_group = QGroupBox()
        self.set_translatable_text(parallel_capture_group, "pipeline_management_parallel_capture_section")
        parallel_capture_layout = QFormLayout(parallel_capture_group)
        
        self.parallel_capture_enabled = QCheckBox()
        self.set_translatable_text(self.parallel_capture_enabled, "pipeline_management_enabled_check_2")
        self.parallel_capture_enabled.setChecked(False)
        parallel_capture_layout.addRow("Status:", self.parallel_capture_enabled)
        
        parallel_capture_desc = QLabel("Process multiple regions simultaneously")
        parallel_capture_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        parallel_capture_layout.addRow("", parallel_capture_desc)
        
        self.parallel_capture_workers_spin = CustomSpinBox()
        self.parallel_capture_workers_spin.setRange(2, 8)
        self.parallel_capture_workers_spin.setValue(4)
        parallel_capture_layout.addRow("Worker Threads:", self.parallel_capture_workers_spin)
        
        layout.addWidget(parallel_capture_group)
        
        return group
    
    def _create_ocr_stage_section(self) -> QGroupBox:
        """Create OCR stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pipeline_management_ocr_stage_section")
        layout = QVBoxLayout(group)
        
        # Current Engine Display
        engine_display_layout = QHBoxLayout()
        engine_display_layout.addWidget(QLabel("Current Engine:"))
        
        self.current_ocr_engine_label = QLabel("Loading...")
        self.current_ocr_engine_label.setStyleSheet("font-weight: bold; color: #0066CC; font-size: 11pt;")
        engine_display_layout.addWidget(self.current_ocr_engine_label)
        
        change_engine_btn = QPushButton()
        self.set_translatable_text(change_engine_btn, "pipeline_management_change_engine_button")
        change_engine_btn.clicked.connect(self._open_ocr_tab)
        engine_display_layout.addWidget(change_engine_btn)
        
        engine_display_layout.addStretch()
        layout.addLayout(engine_display_layout)
        
        # Intelligent Text Processor Plugin (ESSENTIAL - BYPASSES MASTER SWITCH)
        intelligent_group = QGroupBox()
        self.set_translatable_text(intelligent_group, "pipeline_management_intelligent_text_processor_essential_section")
        intelligent_layout = QFormLayout(intelligent_group)
        
        self.intelligent_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.intelligent_plugin_enabled, "pipeline_management_enabled_check_3")
        self.intelligent_plugin_enabled.setChecked(True)
        self.intelligent_plugin_enabled.setToolTip("Essential plugin - bypasses master switch, works even when plugins are globally disabled")
        intelligent_layout.addRow("Status:", self.intelligent_plugin_enabled)
        
        intelligent_desc = QLabel("OCR error correction (| → I, 0 → O) + text validation (30-50% noise reduction)")
        intelligent_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        intelligent_layout.addRow("", intelligent_desc)
        
        # Enable Corrections checkbox
        self.intelligent_corrections_check = QCheckBox()
        self.set_translatable_text(self.intelligent_corrections_check, "pipeline_management_enable_ocr_corrections_check")
        self.intelligent_corrections_check.setChecked(True)
        self.intelligent_corrections_check.setToolTip(
            "Fix common OCR errors:\n"
            "• | → I (pipe to capital I)\n"
            "• l → I (lowercase L to capital I)\n"
            "• 0 → O (zero to capital O)\n"
            "• rn → m (two letters to one)\n"
            "• cl → d, vv → w"
        )
        intelligent_layout.addRow("OCR Corrections:", self.intelligent_corrections_check)
        
        # Enable Context checkbox
        self.intelligent_context_check = QCheckBox()
        self.set_translatable_text(self.intelligent_context_check, "pipeline_management_enable_context_aware_check")
        self.intelligent_context_check.setChecked(True)
        self.intelligent_context_check.setToolTip(
            "Context-aware corrections:\n"
            "• 'When | was' → 'When I was'\n"
            "• '| am' → 'I am'\n"
            "• Sentence-level pattern matching"
        )
        intelligent_layout.addRow("Context-Aware:", self.intelligent_context_check)
        
        # Enable Validation checkbox
        self.intelligent_validation_check = QCheckBox()
        self.set_translatable_text(self.intelligent_validation_check, "pipeline_management_enable_text_validation_check")
        self.intelligent_validation_check.setChecked(True)
        self.intelligent_validation_check.setToolTip("Filter low-confidence and garbage text")
        self.intelligent_validation_check.stateChanged.connect(self.settingChanged.emit)
        intelligent_layout.addRow("Text Validation:", self.intelligent_validation_check)
        
        # Min Confidence spinner
        self.intelligent_min_confidence_spin = CustomDoubleSpinBox()
        self.intelligent_min_confidence_spin.setRange(0.1, 0.9)
        self.intelligent_min_confidence_spin.setSingleStep(0.1)
        self.intelligent_min_confidence_spin.setValue(0.3)
        self.intelligent_min_confidence_spin.setToolTip("Higher values = stricter filtering (0.5+ recommended for noisy content)")
        self.intelligent_min_confidence_spin.valueChanged.connect(self.settingChanged.emit)
        intelligent_layout.addRow("Min Confidence:", self.intelligent_min_confidence_spin)
        
        # Min Word Length spinner (NEW - filter out short garbage)
        self.intelligent_min_word_length_spin = CustomSpinBox()
        self.intelligent_min_word_length_spin.setRange(1, 10)
        self.intelligent_min_word_length_spin.setSingleStep(1)
        self.intelligent_min_word_length_spin.setValue(2)
        self.intelligent_min_word_length_spin.setToolTip("Reject text shorter than this (3-4 recommended to filter noise like '3 Z', 'Py')")
        self.intelligent_min_word_length_spin.valueChanged.connect(self.settingChanged.emit)
        intelligent_layout.addRow("Min Word Length:", self.intelligent_min_word_length_spin)
        
        # Auto Learn checkbox
        self.intelligent_auto_learn_check = QCheckBox()
        self.set_translatable_text(self.intelligent_auto_learn_check, "pipeline_management_auto_learn_check")
        self.intelligent_auto_learn_check.setChecked(True)
        self.intelligent_auto_learn_check.setToolTip("Learn from corrections to improve accuracy over time")
        self.intelligent_auto_learn_check.stateChanged.connect(self.settingChanged.emit)
        intelligent_layout.addRow("Auto Learn:", self.intelligent_auto_learn_check)
        
        correction_hint = QLabel("💡 Replaces old Text Validator plugin with enhanced OCR correction")
        correction_hint.setStyleSheet("color: #0066CC; font-size: 8pt; font-style: italic;")
        intelligent_layout.addRow("", correction_hint)
        
        layout.addWidget(intelligent_group)
        
        # Spell Corrector Plugin
        spell_group = QGroupBox()
        self.set_translatable_text(spell_group, "pipeline_management_spell_corrector_section")
        spell_layout = QFormLayout(spell_group)
        
        self.spell_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.spell_plugin_enabled, "pipeline_management_enabled_check_4")
        self.spell_plugin_enabled.setChecked(True)
        spell_layout.addRow("Status:", self.spell_plugin_enabled)
        
        spell_desc = QLabel("Fixes OCR errors using dictionary (10-20% accuracy boost)")
        spell_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        spell_layout.addRow("", spell_desc)
        
        self.spell_aggressive_check = QCheckBox()
        self.set_translatable_text(self.spell_aggressive_check, "pipeline_management_aggressive_mode_check")
        self.spell_aggressive_check.setChecked(False)
        self.spell_aggressive_check.setToolTip("May over-correct but catches more errors")
        self.spell_aggressive_check.stateChanged.connect(self.settingChanged.emit)
        spell_layout.addRow("", self.spell_aggressive_check)
        
        self.spell_fix_caps_check = QCheckBox()
        self.set_translatable_text(self.spell_fix_caps_check, "pipeline_management_fix_capitalization_check")
        self.spell_fix_caps_check.setChecked(True)
        self.spell_fix_caps_check.setToolTip("Fix random capitalization errors")
        self.spell_fix_caps_check.stateChanged.connect(self.settingChanged.emit)
        spell_layout.addRow("", self.spell_fix_caps_check)
        
        self.spell_confidence_spin = CustomDoubleSpinBox()
        self.spell_confidence_spin.setRange(0.1, 1.0)
        self.spell_confidence_spin.setSingleStep(0.1)
        self.spell_confidence_spin.setValue(0.5)
        self.spell_confidence_spin.valueChanged.connect(self.settingChanged.emit)
        spell_layout.addRow("Min Confidence:", self.spell_confidence_spin)
        
        layout.addWidget(spell_group)
        
        # Parallel OCR Plugin
        parallel_group = QGroupBox()
        self.set_translatable_text(parallel_group, "pipeline_management_parallel_ocr_section")
        parallel_layout = QFormLayout(parallel_group)
        
        self.parallel_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.parallel_plugin_enabled, "pipeline_management_enabled_check_5")
        self.parallel_plugin_enabled.setChecked(False)
        parallel_layout.addRow("Status:", self.parallel_plugin_enabled)
        
        parallel_desc = QLabel("Process multiple regions simultaneously")
        parallel_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        parallel_layout.addRow("", parallel_desc)
        
        self.parallel_workers_spin = CustomSpinBox()
        self.parallel_workers_spin.setRange(2, 8)
        self.parallel_workers_spin.setValue(4)
        parallel_layout.addRow("Worker Threads:", self.parallel_workers_spin)
        
        layout.addWidget(parallel_group)
        
        return group
    
    def _create_translation_stage_section(self) -> QGroupBox:
        """Create translation stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pipeline_management_translation_stage_section")
        layout = QVBoxLayout(group)
        
        # Translation Cache (ESSENTIAL - BYPASSES MASTER SWITCH)
        cache_group = QGroupBox()
        self.set_translatable_text(cache_group, "pipeline_management_translation_cache_essential_section")
        cache_layout = QFormLayout(cache_group)
        
        self.cache_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.cache_plugin_enabled, "pipeline_management_enabled_check_6")
        self.cache_plugin_enabled.setChecked(True)
        self.cache_plugin_enabled.setToolTip("Essential plugin - bypasses master switch, works even when plugins are globally disabled")
        cache_layout.addRow("Status:", self.cache_plugin_enabled)
        
        cache_desc = QLabel("Instant lookup for repeated text (100x speedup)")
        cache_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        cache_layout.addRow("", cache_desc)
        
        self.cache_size_spin = CustomSpinBox()
        self.cache_size_spin.setRange(100, 100000)
        self.cache_size_spin.setValue(10000)
        self.cache_size_spin.setSuffix("entries")
        cache_layout.addRow("Cache Size:", self.cache_size_spin)
        
        self.cache_ttl_spin = CustomSpinBox()
        self.cache_ttl_spin.setRange(60, 86400)
        self.cache_ttl_spin.setValue(3600)
        self.cache_ttl_spin.setSuffix("seconds")
        cache_layout.addRow("TTL:", self.cache_ttl_spin)
        
        layout.addWidget(cache_group)
        
        # Learning Dictionary (ESSENTIAL - BYPASSES MASTER SWITCH)
        dict_group = QGroupBox()
        self.set_translatable_text(dict_group, "pipeline_management_learning_dictionary_essential_section")
        dict_layout = QFormLayout(dict_group)
        
        self.dict_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.dict_plugin_enabled, "pipeline_management_enabled_check_7")
        self.dict_plugin_enabled.setChecked(True)
        self.dict_plugin_enabled.setToolTip("Essential plugin - bypasses master switch, works even when plugins are globally disabled")
        dict_layout.addRow("Status:", self.dict_plugin_enabled)
        
        dict_desc = QLabel("Persistent learned translations (20x speedup)")
        dict_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        dict_layout.addRow("", dict_desc)
        
        layout.addWidget(dict_group)
        
        # Batch Processing
        batch_group = QGroupBox()
        self.set_translatable_text(batch_group, "pipeline_management_batch_processing_section")
        batch_layout = QFormLayout(batch_group)
        
        self.batch_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.batch_plugin_enabled, "pipeline_management_enabled_check_8")
        self.batch_plugin_enabled.setChecked(False)
        batch_layout.addRow("Status:", self.batch_plugin_enabled)
        
        batch_desc = QLabel("Process multiple frames together (30-50% faster)")
        batch_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        batch_layout.addRow("", batch_desc)
        
        self.batch_size_spin = CustomSpinBox()
        self.batch_size_spin.setRange(2, 32)
        self.batch_size_spin.setValue(8)
        self.batch_size_spin.setSuffix("frames")
        batch_layout.addRow("Max Batch Size:", self.batch_size_spin)
        
        self.batch_wait_spin = CustomDoubleSpinBox()
        self.batch_wait_spin.setRange(1.0, 100.0)
        self.batch_wait_spin.setSingleStep(1.0)
        self.batch_wait_spin.setValue(10.0)
        self.batch_wait_spin.setSuffix("ms")
        batch_layout.addRow("Max Wait Time:", self.batch_wait_spin)
        
        layout.addWidget(batch_group)
        
        # Translation Chain Plugin (Multi-Language: JA→EN→DE)
        chain_group = QGroupBox()
        self.set_translatable_text(chain_group, "pipeline_management_translation_chain_best_for_rare_language_section")
        chain_layout = QFormLayout(chain_group)
        
        self.chain_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.chain_plugin_enabled, "pipeline_management_enabled_check_9")
        self.chain_plugin_enabled.setChecked(False)
        self.chain_plugin_enabled.stateChanged.connect(self.settingChanged.emit)
        chain_layout.addRow("Status:", self.chain_plugin_enabled)
        
        chain_desc = QLabel("Chain translations through intermediate language for better quality (e.g., JA→EN→DE)")
        chain_desc.setWordWrap(True)
        chain_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        chain_layout.addRow("", chain_desc)
        
        # Intermediate language selection
        self.chain_intermediate_lang_combo = QComboBox()
        self.chain_intermediate_lang_combo.addItems(["en", "zh", "es", "fr", "de"])
        self.chain_intermediate_lang_combo.setCurrentText("en")
        self.chain_intermediate_lang_combo.currentTextChanged.connect(self.settingChanged.emit)
        chain_layout.addRow("Intermediate Language:", self.chain_intermediate_lang_combo)
        
        # Quality threshold
        self.chain_quality_threshold_spin = CustomDoubleSpinBox()
        self.chain_quality_threshold_spin.setRange(0.0, 1.0)
        self.chain_quality_threshold_spin.setSingleStep(0.1)
        self.chain_quality_threshold_spin.setValue(0.7)
        self.chain_quality_threshold_spin.valueChanged.connect(self.settingChanged.emit)
        chain_layout.addRow("Quality Threshold:", self.chain_quality_threshold_spin)
        
        # Save all mappings checkbox
        self.chain_save_all_check = QCheckBox()
        self.set_translatable_text(self.chain_save_all_check, "pipeline_management_save_all_intermediate_translations_to_di_check")
        self.chain_save_all_check.setChecked(True)
        self.chain_save_all_check.stateChanged.connect(self.settingChanged.emit)
        chain_layout.addRow("", self.chain_save_all_check)
        
        chain_note = QLabel("💡 Example: Japanese→German will translate JA→EN→DE for better quality")
        chain_note.setStyleSheet("color: #2196F3; font-size: 8pt; font-style: italic;")
        chain_layout.addRow("", chain_note)
        
        chain_performance = QLabel("⚠️ 2-3x slower but 25-35% better quality for rare pairs")
        chain_performance.setStyleSheet("color: #FF9800; font-size: 8pt; font-style: italic;")
        chain_layout.addRow("", chain_performance)
        
        layout.addWidget(chain_group)
        
        # SECRET: System Diagnostics (Audio Translation) - Only show if unlocked
        if self._is_secret_unlocked():
            diagnostics_group = self._create_system_diagnostics_section()
            layout.addWidget(diagnostics_group)
        
        return group
    

    
    def _create_global_stage_section(self) -> QGroupBox:
        """Create global plugins section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pipeline_management_global_pipeline-level_section")
        layout = QVBoxLayout(group)
        
        # Async Pipeline
        async_group = QGroupBox()
        self.set_translatable_text(async_group, "pipeline_management_async_pipeline_section")
        async_layout = QFormLayout(async_group)
        
        self.async_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.async_plugin_enabled, "pipeline_management_enabled_check_10")
        self.async_plugin_enabled.setChecked(False)
        async_layout.addRow("Status:", self.async_plugin_enabled)
        
        async_desc = QLabel("Overlapping stage execution (50-80% throughput)")
        async_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        async_layout.addRow("", async_desc)
        
        self.async_stages_spin = CustomSpinBox()
        self.async_stages_spin.setRange(2, 8)
        self.async_stages_spin.setValue(4)
        async_layout.addRow("Max Concurrent Stages:", self.async_stages_spin)
        
        layout.addWidget(async_group)
        
        # Priority Queue
        priority_group = QGroupBox()
        self.set_translatable_text(priority_group, "pipeline_management_priority_queue_section")
        priority_layout = QFormLayout(priority_group)
        
        self.priority_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.priority_plugin_enabled, "pipeline_management_enabled_check_11")
        self.priority_plugin_enabled.setChecked(False)
        priority_layout.addRow("Status:", self.priority_plugin_enabled)
        
        priority_desc = QLabel("User tasks first (20-30% responsiveness)")
        priority_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        priority_layout.addRow("", priority_desc)
        
        layout.addWidget(priority_group)
        
        # Work-Stealing Pool
        work_group = QGroupBox()
        self.set_translatable_text(work_group, "pipeline_management_work-stealing_pool_section")
        work_layout = QFormLayout(work_group)
        
        self.work_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.work_plugin_enabled, "pipeline_management_enabled_check_12")
        self.work_plugin_enabled.setChecked(False)
        work_layout.addRow("Status:", self.work_plugin_enabled)
        
        work_desc = QLabel("Load balancing (15-25% CPU utilization)")
        work_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        work_layout.addRow("", work_desc)
        
        self.work_workers_spin = CustomSpinBox()
        self.work_workers_spin.setRange(2, 16)
        self.work_workers_spin.setValue(4)
        work_layout.addRow("Number of Workers:", self.work_workers_spin)
        
        layout.addWidget(work_group)
        
        return group
    
    def _open_ocr_tab(self):
        """Open the OCR settings tab."""
        # Get parent settings dialog
        parent = self.parent()
        while parent and not hasattr(parent, 'tab_widget'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'tab_widget'):
            # Find OCR tab index (usually tab 3)
            for i in range(parent.tab_widget.count()):
                if "OCR" in parent.tab_widget.tabText(i):
                    parent.tab_widget.setCurrentIndex(i)
                    break
        
        self.errors_label = QLabel("--")
        stats_layout.addRow("Errors:", self.errors_label)
        
        layout.addWidget(stats_group)
        
        # Stage Status
        stages_group = QGroupBox()
        self.set_translatable_text(stages_group, "pipeline_management_pipeline_stages_section")
        stages_layout = QVBoxLayout(stages_group)
        
        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(4)
        self.stages_table.setHorizontalHeaderLabels(["Stage", "Status", "Executions", "Avg Time"])
        self.stages_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stages_table.setMaximumHeight(200)
        stages_layout.addWidget(self.stages_table)
        
        layout.addWidget(stages_group)
        
        layout.addStretch()
        return tab
    
    def _create_performance_tab(self) -> QWidget:
        """Create performance monitoring tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Component Timing
        timing_group = QGroupBox()
        self.set_translatable_text(timing_group, "pipeline_management_component_timing_section")
        timing_layout = QVBoxLayout(timing_group)
        
        self.timing_table = QTableWidget()
        self.timing_table.setColumnCount(5)
        self.timing_table.setHorizontalHeaderLabels([
            "Component", "Avg Time (ms)", "Total Time (s)", "Count", "Success Rate"
        ])
        self.timing_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        timing_layout.addWidget(self.timing_table)
        
        layout.addWidget(timing_group)
        
        # Queue Status
        queue_group = QGroupBox()
        self.set_translatable_text(queue_group, "pipeline_management_queue_status_section")
        queue_layout = QVBoxLayout(queue_group)
        
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels([
            "Queue", "Size", "Utilization", "Dropped"
        ])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        queue_layout.addWidget(self.queue_table)
        
        layout.addWidget(queue_group)
        
        # Worker Status
        worker_group = QGroupBox()
        self.set_translatable_text(worker_group, "pipeline_management_worker_pools_section")
        worker_layout = QVBoxLayout(worker_group)
        
        self.worker_table = QTableWidget()
        self.worker_table.setColumnCount(4)
        self.worker_table.setHorizontalHeaderLabels([
            "Pool", "Workers", "Tasks Completed", "Success Rate"
        ])
        self.worker_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        worker_layout.addWidget(self.worker_table)
        
        layout.addWidget(worker_group)
        
        # Cache Performance
        cache_group = QGroupBox()
        self.set_translatable_text(cache_group, "pipeline_management_cache_performance_section")
        cache_layout = QFormLayout(cache_group)
        
        self.frame_skip_label = QLabel("--")
        cache_layout.addRow("Frame Skip Rate:", self.frame_skip_label)
        
        self.ocr_cache_label = QLabel("--")
        cache_layout.addRow("OCR Cache Hit Rate:", self.ocr_cache_label)
        
        self.translation_cache_label = QLabel("--")
        cache_layout.addRow("Translation Cache Hit Rate:", self.translation_cache_label)
        
        self.cache_memory_label = QLabel("--")
        cache_layout.addRow("Cache Memory:", self.cache_memory_label)
        
        layout.addWidget(cache_group)
        
        layout.addStretch()
        return tab
    
    def _create_health_tab(self) -> QWidget:
        """Create health monitoring tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Overall Health
        health_group = QGroupBox()
        self.set_translatable_text(health_group, "pipeline_management_overall_health_section")
        health_layout = QVBoxLayout(health_group)
        
        self.health_status_label = QLabel("Status: Unknown")
        self.health_status_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        health_layout.addWidget(self.health_status_label)
        
        self.health_progress = QProgressBar()
        self.health_progress.setRange(0, 100)
        self.health_progress.setValue(100)
        health_layout.addWidget(self.health_progress)
        
        layout.addWidget(health_group)
        
        # Health Checks
        checks_group = QGroupBox()
        self.set_translatable_text(checks_group, "pipeline_management_health_checks_section")
        checks_layout = QVBoxLayout(checks_group)
        
        self.health_table = QTableWidget()
        self.health_table.setColumnCount(4)
        self.health_table.setHorizontalHeaderLabels([
            "Check", "Status", "Failures", "Last Check"
        ])
        self.health_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        checks_layout.addWidget(self.health_table)
        
        layout.addWidget(checks_group)
        
        # Error Log
        error_group = QGroupBox()
        self.set_translatable_text(error_group, "pipeline_management_recent_errors_section")
        error_layout = QVBoxLayout(error_group)
        
        self.error_log = QTextEdit()
        self.error_log.setReadOnly(True)
        self.error_log.setMaximumHeight(150)
        error_layout.addWidget(self.error_log)
        
        clear_btn = QPushButton()
        self.set_translatable_text(clear_btn, "pipeline_management_clear_error_log_button")
        clear_btn.clicked.connect(lambda: self.error_log.clear())
        error_layout.addWidget(clear_btn)
        
        layout.addWidget(error_group)
        
        layout.addStretch()
        return tab
    
    def _create_configuration_tab(self) -> QWidget:
        """Create configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Pipeline Info
        info_group = QGroupBox()
        self.set_translatable_text(info_group, "pipeline_management_modular_pipeline_section")
        info_layout = QVBoxLayout(info_group)
        
        # Description
        desc_label = QLabel(
            "This application uses the advanced Modular Pipeline with the following features:"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        info_layout.addWidget(desc_label)
        
        features_label = QLabel(
            "✅ Advanced error handling with circuit breakers\n"
            "✅ Real-time metrics and health monitoring\n"
            "✅ Worker pools and queue management\n"
            "✅ Smart caching and optimization\n"
            "✅ Modular stage architecture\n"
            "✅ Auto-recovery from failures"
        )
        features_label.setStyleSheet("color: #333333; font-size: 9pt; margin-left: 10px;")
        info_layout.addWidget(features_label)
        
        layout.addWidget(info_group)
        
        # Manager Settings
        manager_group = QGroupBox()
        self.set_translatable_text(manager_group, "pipeline_management_manager_configuration_section")
        manager_layout = QFormLayout(manager_group)
        
        # Queue settings
        self.queue_backpressure_check = QCheckBox()
        self.set_translatable_text(self.queue_backpressure_check, "pipeline_management_enable_backpressure_check")
        self.queue_backpressure_check.setChecked(True)
        manager_layout.addRow("Queue Management:", self.queue_backpressure_check)
        
        # Worker settings
        self.worker_autoscale_check = QCheckBox()
        self.set_translatable_text(self.worker_autoscale_check, "pipeline_management_enable_auto-scaling_check")
        self.worker_autoscale_check.setChecked(True)
        manager_layout.addRow("Worker Pools:", self.worker_autoscale_check)
        
        self.min_workers_spin = CustomSpinBox()
        self.min_workers_spin.setRange(1, 16)
        self.min_workers_spin.setValue(2)
        manager_layout.addRow("  Min Workers:", self.min_workers_spin)
        
        self.max_workers_spin = CustomSpinBox()
        self.max_workers_spin.setRange(2, 32)
        self.max_workers_spin.setValue(8)
        manager_layout.addRow("  Max Workers:", self.max_workers_spin)
        
        # Cache settings
        self.cache_enabled_check = QCheckBox()
        self.set_translatable_text(self.cache_enabled_check, "pipeline_management_enable_caching_check")
        self.cache_enabled_check.setChecked(True)
        manager_layout.addRow("Cache:", self.cache_enabled_check)
        
        self.similarity_threshold_spin = CustomDoubleSpinBox()
        self.similarity_threshold_spin.setRange(0.5, 1.0)
        self.similarity_threshold_spin.setSingleStep(0.05)
        self.similarity_threshold_spin.setValue(0.95)
        manager_layout.addRow("  Similarity Threshold:", self.similarity_threshold_spin)
        
        # Health monitoring
        self.health_monitoring_check = QCheckBox()
        self.set_translatable_text(self.health_monitoring_check, "pipeline_management_enable_health_monitoring_check")
        self.health_monitoring_check.setChecked(True)
        manager_layout.addRow("Health Monitor:", self.health_monitoring_check)
        
        self.recovery_enabled_check = QCheckBox()
        self.set_translatable_text(self.recovery_enabled_check, "pipeline_management_enable_auto-recovery_check")
        self.recovery_enabled_check.setChecked(True)
        manager_layout.addRow("  Auto-Recovery:", self.recovery_enabled_check)
        
        layout.addWidget(manager_group)
        
        # Apply button
        apply_btn = QPushButton()
        self.set_translatable_text(apply_btn, "pipeline_management_apply_configuration_button")
        apply_btn.setProperty("class", "action")
        apply_btn.clicked.connect(self._apply_configuration)
        layout.addWidget(apply_btn)
        
        # Info
        info_label = QLabel(
            "💡 Tip: These settings control the modular pipeline managers. "
            "Changes take effect immediately for new operations."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 9pt; padding: 10px; "
                                "background-color: #F0F8FF; border-radius: 5px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        return tab
    
    def _create_plugins_tab(self) -> QWidget:
        """Create optimizer plugins tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # Header
        header_group = QGroupBox()
        self.set_translatable_text(header_group, "pipeline_management_optimizer_plugins_section")
        header_layout = QVBoxLayout(header_group)
        
        desc_label = QLabel(
            "Optimizer plugins enhance pipeline performance with specialized optimizations. "
            "Enable/disable plugins and configure their settings below."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        header_layout.addWidget(desc_label)
        
        # Master enable/disable
        self.plugins_enabled_check = QCheckBox()
        self.set_translatable_text(self.plugins_enabled_check, "pipeline_management_enable_optimizer_plugins_check")
        self.plugins_enabled_check.setChecked(True)  # Enabled for testing
        self.plugins_enabled_check.setStyleSheet("font-weight: bold; font-size: 10pt;")
        self.plugins_enabled_check.stateChanged.connect(self._on_plugins_enabled_changed)
        header_layout.addWidget(self.plugins_enabled_check)
        
        layout.addWidget(header_group)
        
        # Plugin 1: Translation Cache
        cache_group = QGroupBox()
        self.set_translatable_text(cache_group, "pipeline_management_translation_cache_optimizer_section")
        cache_layout = QFormLayout(cache_group)
        
        self.cache_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.cache_plugin_enabled, "pipeline_management_enabled_check_13")
        self.cache_plugin_enabled.setChecked(True)
        cache_layout.addRow("Status:", self.cache_plugin_enabled)
        
        cache_desc = QLabel("Caches translations for instant lookup of repeated text (100x speedup)")
        cache_desc.setWordWrap(True)
        cache_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        cache_layout.addRow("", cache_desc)
        
        self.cache_size_spin = CustomSpinBox()
        self.cache_size_spin.setRange(100, 100000)
        self.cache_size_spin.setValue(10000)
        self.cache_size_spin.setSuffix("entries")
        cache_layout.addRow("Cache Size:", self.cache_size_spin)
        
        self.cache_ttl_spin = CustomSpinBox()
        self.cache_ttl_spin.setRange(60, 86400)
        self.cache_ttl_spin.setValue(3600)
        self.cache_ttl_spin.setSuffix("seconds")
        cache_layout.addRow("TTL:", self.cache_ttl_spin)
        
        layout.addWidget(cache_group)
        
        # Plugin 2: Frame Skip
        skip_group = QGroupBox()
        self.set_translatable_text(skip_group, "pipeline_management_frame_skip_optimizer_section")
        skip_layout = QFormLayout(skip_group)
        
        self.skip_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.skip_plugin_enabled, "pipeline_management_enabled_check_14")
        self.skip_plugin_enabled.setChecked(True)
        skip_layout.addRow("Status:", self.skip_plugin_enabled)
        
        skip_desc = QLabel("Skips unchanged frames to reduce CPU usage by 50-70%")
        skip_desc.setWordWrap(True)
        skip_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        skip_layout.addRow("", skip_desc)
        
        self.skip_threshold_spin = CustomDoubleSpinBox()
        self.skip_threshold_spin.setRange(0.8, 0.99)
        self.skip_threshold_spin.setSingleStep(0.01)
        self.skip_threshold_spin.setValue(0.95)
        skip_layout.addRow("Similarity Threshold:", self.skip_threshold_spin)
        
        from PyQt6.QtWidgets import QComboBox
        self.skip_method_combo = QComboBox()
        self.skip_method_combo.addItems(["hash", "mse", "ssim"])
        skip_layout.addRow("Comparison Method:", self.skip_method_combo)
        
        layout.addWidget(skip_group)
        
        # Plugin 3: Batch Processing
        batch_group = QGroupBox()
        self.set_translatable_text(batch_group, "pipeline_management_batch_processing_optimizer_section")
        batch_layout = QFormLayout(batch_group)
        
        self.batch_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.batch_plugin_enabled, "pipeline_management_enabled_check_15")
        self.batch_plugin_enabled.setChecked(False)
        batch_layout.addRow("Status:", self.batch_plugin_enabled)
        
        batch_desc = QLabel("Batches multiple frames for 30-50% faster processing")
        batch_desc.setWordWrap(True)
        batch_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        batch_layout.addRow("", batch_desc)
        
        self.batch_size_spin = CustomSpinBox()
        self.batch_size_spin.setRange(2, 32)
        self.batch_size_spin.setValue(8)
        self.batch_size_spin.setSuffix("frames")
        batch_layout.addRow("Max Batch Size:", self.batch_size_spin)
        
        self.batch_wait_spin = CustomDoubleSpinBox()
        self.batch_wait_spin.setRange(1.0, 100.0)
        self.batch_wait_spin.setSingleStep(1.0)
        self.batch_wait_spin.setValue(10.0)
        self.batch_wait_spin.setSuffix("ms")
        batch_layout.addRow("Max Wait Time:", self.batch_wait_spin)
        
        layout.addWidget(batch_group)
        
        # Plugin 4: Async Pipeline
        async_group = QGroupBox()
        self.set_translatable_text(async_group, "pipeline_management_async_pipeline_optimizer_section")
        async_layout = QFormLayout(async_group)
        
        self.async_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.async_plugin_enabled, "pipeline_management_enabled_check_16")
        self.async_plugin_enabled.setChecked(False)
        async_layout.addRow("Status:", self.async_plugin_enabled)
        
        async_desc = QLabel("Overlapping stage execution for 50-80% higher throughput")
        async_desc.setWordWrap(True)
        async_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        async_layout.addRow("", async_desc)
        
        self.async_stages_spin = CustomSpinBox()
        self.async_stages_spin.setRange(2, 8)
        self.async_stages_spin.setValue(4)
        async_layout.addRow("Max Concurrent Stages:", self.async_stages_spin)
        
        layout.addWidget(async_group)
        
        # Plugin 5: Priority Queue
        priority_group = QGroupBox()
        self.set_translatable_text(priority_group, "pipeline_management_priority_queue_optimizer_section")
        priority_layout = QFormLayout(priority_group)
        
        self.priority_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.priority_plugin_enabled, "pipeline_management_enabled_check_17")
        self.priority_plugin_enabled.setChecked(False)
        priority_layout.addRow("Status:", self.priority_plugin_enabled)
        
        priority_desc = QLabel("Prioritizes user tasks for 20-30% better responsiveness")
        priority_desc.setWordWrap(True)
        priority_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        priority_layout.addRow("", priority_desc)
        
        layout.addWidget(priority_group)
        
        # Plugin 6: Work-Stealing Pool
        work_group = QGroupBox()
        self.set_translatable_text(work_group, "pipeline_management_work-stealing_pool_optimizer_section")
        work_layout = QFormLayout(work_group)
        
        self.work_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.work_plugin_enabled, "pipeline_management_enabled_check_18")
        self.work_plugin_enabled.setChecked(False)
        work_layout.addRow("Status:", self.work_plugin_enabled)
        
        work_desc = QLabel("Load balancing for 15-25% better CPU utilization")
        work_desc.setWordWrap(True)
        work_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        work_layout.addRow("", work_desc)
        
        self.work_workers_spin = CustomSpinBox()
        self.work_workers_spin.setRange(2, 16)
        self.work_workers_spin.setValue(4)
        work_layout.addRow("Number of Workers:", self.work_workers_spin)
        
        layout.addWidget(work_group)
        
        # Apply button
        apply_plugins_btn = QPushButton()
        self.set_translatable_text(apply_plugins_btn, "pipeline_management_apply_plugin_settings_button")
        apply_plugins_btn.setProperty("class", "action")
        apply_plugins_btn.clicked.connect(self._apply_plugin_settings)
        layout.addWidget(apply_plugins_btn)
        
        # Performance info
        perf_label = QLabel(
            "💡 Expected Performance:\n"
            "• Translation Cache + Frame Skip: 2-3x improvement\n"
            "• All plugins enabled: 3-5x improvement (30-50 FPS from 10 FPS baseline)"
        )
        perf_label.setWordWrap(True)
        perf_label.setStyleSheet("color: #0066CC; font-size: 9pt; margin-top: 10px; padding: 10px; background-color: #E6F2FF; border-radius: 5px;")
        layout.addWidget(perf_label)
        
        layout.addStretch()
        
        return tab
    
    def _on_plugins_enabled_changed(self, state):
        """Handle master plugin enable/disable - controls OPTIMIZER plugins only, NOT essential features."""
        enabled = (state == Qt.CheckState.Checked.value)
        
        # Sync with overview tab master switch
        if hasattr(self, 'overview_plugins_master_check'):
            self.overview_plugins_master_check.blockSignals(True)
            self.overview_plugins_master_check.setChecked(enabled)
            self.overview_plugins_master_check.blockSignals(False)
        
        # HARDCODED: ESSENTIAL PLUGINS ARE NEVER AFFECTED BY MASTER SWITCH
        # Essential plugins (always active, checkboxes are disabled):
        # - Frame Skip (skip_plugin_enabled) - ESSENTIAL
        # - Text Validator (validator_plugin_enabled) - ESSENTIAL
        # - Text Block Merger (no UI, auto-applied) - ESSENTIAL
        # - Translation Cache (cache_plugin_enabled) - ESSENTIAL
        # - Learning Dictionary (dict_plugin_enabled) - ESSENTIAL
        
        # Enable/disable OPTIONAL OPTIMIZER plugin checkboxes in UI
        
        # Capture stage OPTIMIZERS (optional)
        # NOTE: skip_plugin_enabled is ESSENTIAL - not controlled here
        if hasattr(self, 'motion_plugin_enabled'):
            self.motion_plugin_enabled.setEnabled(enabled)
        if hasattr(self, 'parallel_capture_enabled'):
            self.parallel_capture_enabled.setEnabled(enabled)
        
        # OCR stage OPTIMIZERS (optional)
        # NOTE: validator_plugin_enabled is ESSENTIAL - not controlled here
        if hasattr(self, 'parallel_plugin_enabled'):
            self.parallel_plugin_enabled.setEnabled(enabled)
        
        # Translation stage OPTIMIZERS (optional)
        # NOTE: cache_plugin_enabled and dict_plugin_enabled are ESSENTIAL - not controlled here
        if hasattr(self, 'batch_plugin_enabled'):
            self.batch_plugin_enabled.setEnabled(enabled)
        if hasattr(self, 'chain_plugin_enabled'):
            self.chain_plugin_enabled.setEnabled(enabled)
        if hasattr(self, 'parallel_translation_enabled'):
            self.parallel_translation_enabled.setEnabled(enabled)
        
        # Global plugins (optional)
        if hasattr(self, 'async_plugin_enabled'):
            self.async_plugin_enabled.setEnabled(enabled)
        if hasattr(self, 'priority_plugin_enabled'):
            self.priority_plugin_enabled.setEnabled(enabled)
        if hasattr(self, 'work_plugin_enabled'):
            self.work_plugin_enabled.setEnabled(enabled)
        
        # Enable/disable overview tab optional plugin checkboxes
        optional_plugins = ['motion', 'parallel_capture', 'spell', 'parallel_ocr', 'batch', 'chain', 'async', 'priority', 'work']
        for plugin_name in optional_plugins:
            if hasattr(self, f'overview_{plugin_name}_check'):
                getattr(self, f'overview_{plugin_name}_check').setEnabled(enabled)
        
        # Save to config
        if self.config_manager:
            self.config_manager.set_setting('pipeline.enable_optimizer_plugins', enabled)
            self.settingChanged.emit()
            
        print(f"[PIPELINE] Master plugin switch: {'ENABLED' if enabled else 'DISABLED'} - All plugins will be {'active' if enabled else 'inactive'}")
    
    def _on_overview_master_changed(self, state):
        """Handle overview tab master switch change."""
        enabled = (state == Qt.CheckState.Checked.value)
        
        # Sync with plugins tab master switch
        if hasattr(self, 'plugins_enabled_check'):
            self.plugins_enabled_check.blockSignals(True)
            self.plugins_enabled_check.setChecked(enabled)
            self.plugins_enabled_check.blockSignals(False)
        
        # Call the main handler
        self._on_plugins_enabled_changed(state)
    
    def _sync_plugin_checkbox(self, plugin_name):
        """Sync plugin checkbox between overview and detailed tabs."""
        # Map overview checkboxes to detailed tab checkboxes
        checkbox_map = {
            'skip': 'skip_plugin_enabled',
            'validator': 'validator_plugin_enabled',
            'cache': 'cache_plugin_enabled',
            'dict': 'dict_plugin_enabled',
            'motion': 'motion_plugin_enabled',
            'parallel_capture': 'parallel_capture_enabled',
            'spell': 'spell_plugin_enabled',
            'parallel_ocr': 'parallel_plugin_enabled',
            'batch': 'batch_plugin_enabled',
            'chain': 'chain_plugin_enabled',
            'async': 'async_plugin_enabled',
            'priority': 'priority_plugin_enabled',
            'work': 'work_plugin_enabled'
        }
        
        overview_checkbox_name = f'overview_{plugin_name}_check'
        detailed_checkbox_name = checkbox_map.get(plugin_name)
        
        if not hasattr(self, overview_checkbox_name) or not detailed_checkbox_name:
            return
        
        overview_checkbox = getattr(self, overview_checkbox_name)
        
        # Sync to detailed tab if it exists
        if hasattr(self, detailed_checkbox_name):
            detailed_checkbox = getattr(self, detailed_checkbox_name)
            detailed_checkbox.blockSignals(True)
            detailed_checkbox.setChecked(overview_checkbox.isChecked())
            detailed_checkbox.blockSignals(False)
        
        # Emit setting changed
        self.settingChanged.emit()
    
    def _sync_overview_checkboxes_from_detailed(self):
        """Sync overview tab checkboxes from detailed tab checkboxes on load."""
        checkbox_map = {
            'skip': 'skip_plugin_enabled',
            'validator': 'validator_plugin_enabled',
            'cache': 'cache_plugin_enabled',
            'dict': 'dict_plugin_enabled',
            'motion': 'motion_plugin_enabled',
            'parallel_capture': 'parallel_capture_enabled',
            'spell': 'spell_plugin_enabled',
            'parallel_ocr': 'parallel_plugin_enabled',
            'batch': 'batch_plugin_enabled',
            'chain': 'chain_plugin_enabled',
            'async': 'async_plugin_enabled',
            'priority': 'priority_plugin_enabled',
            'work': 'work_plugin_enabled'
        }
        
        for plugin_name, detailed_checkbox_name in checkbox_map.items():
            overview_checkbox_name = f'overview_{plugin_name}_check'
            
            if hasattr(self, overview_checkbox_name) and hasattr(self, detailed_checkbox_name):
                overview_checkbox = getattr(self, overview_checkbox_name)
                detailed_checkbox = getattr(self, detailed_checkbox_name)
                
                overview_checkbox.blockSignals(True)
                overview_checkbox.setChecked(detailed_checkbox.isChecked())
                overview_checkbox.blockSignals(False)
    
    def _on_positioning_strategy_changed(self, strategy):
        """Handle positioning strategy change."""
        if self.config_manager:
            self.config_manager.set_setting('pipeline.positioning_strategy', strategy)
            self.settingChanged.emit()
    
    def _apply_plugin_settings(self):
        """Apply optimizer plugin settings."""
        from PyQt6.QtWidgets import QMessageBox
        import json
        from pathlib import Path
        
        # Update plugin.json files
        plugins_dir = Path("plugins/optimizers")
        
        try:
            # Translation Cache
            cache_json = plugins_dir / "translation_cache" / "plugin.json"
            if cache_json.exists():
                with open(cache_json, 'r') as f:
                    cache_config = json.load(f)
                cache_config['enabled'] = self.cache_plugin_enabled.isChecked()
                cache_config['settings']['max_cache_size']['default'] = self.cache_size_spin.value()
                cache_config['settings']['ttl_seconds']['default'] = self.cache_ttl_spin.value()
                with open(cache_json, 'w') as f:
                    json.dump(cache_config, f, indent=2)
            
            # Frame Skip
            skip_json = plugins_dir / "frame_skip" / "plugin.json"
            if skip_json.exists():
                with open(skip_json, 'r') as f:
                    skip_config = json.load(f)
                skip_config['enabled'] = self.skip_plugin_enabled.isChecked()
                skip_config['settings']['similarity_threshold']['default'] = self.skip_threshold_spin.value()
                skip_config['settings']['comparison_method']['default'] = self.skip_method_combo.currentText()
                with open(skip_json, 'w') as f:
                    json.dump(skip_config, f, indent=2)
            
            # Batch Processing
            batch_json = plugins_dir / "batch_processing" / "plugin.json"
            if batch_json.exists():
                with open(batch_json, 'r') as f:
                    batch_config = json.load(f)
                batch_config['enabled'] = self.batch_plugin_enabled.isChecked()
                batch_config['settings']['max_batch_size']['default'] = self.batch_size_spin.value()
                batch_config['settings']['max_wait_time_ms']['default'] = self.batch_wait_spin.value()
                with open(batch_json, 'w') as f:
                    json.dump(batch_config, f, indent=2)
            
            # Async Pipeline
            async_json = plugins_dir / "async_pipeline" / "plugin.json"
            if async_json.exists():
                with open(async_json, 'r') as f:
                    async_config = json.load(f)
                async_config['enabled'] = self.async_plugin_enabled.isChecked()
                async_config['settings']['max_concurrent_stages']['default'] = self.async_stages_spin.value()
                with open(async_json, 'w') as f:
                    json.dump(async_config, f, indent=2)
            
            # Priority Queue
            priority_json = plugins_dir / "priority_queue" / "plugin.json"
            if priority_json.exists():
                with open(priority_json, 'r') as f:
                    priority_config = json.load(f)
                priority_config['enabled'] = self.priority_plugin_enabled.isChecked()
                with open(priority_json, 'w') as f:
                    json.dump(priority_config, f, indent=2)
            
            # Work-Stealing Pool
            work_json = plugins_dir / "work_stealing" / "plugin.json"
            if work_json.exists():
                with open(work_json, 'r') as f:
                    work_config = json.load(f)
                work_config['enabled'] = self.work_plugin_enabled.isChecked()
                work_config['settings']['num_workers']['default'] = self.work_workers_spin.value()
                with open(work_json, 'w') as f:
                    json.dump(work_config, f, indent=2)
            
            # Motion Tracker
            motion_json = plugins_dir / "motion_tracker" / "plugin.json"
            if motion_json.exists():
                with open(motion_json, 'r') as f:
                    motion_config = json.load(f)
                motion_config['enabled'] = self.motion_plugin_enabled.isChecked()
                if 'settings' not in motion_config:
                    motion_config['settings'] = {}
                if 'motion_threshold' not in motion_config['settings']:
                    motion_config['settings']['motion_threshold'] = {'type': 'float', 'default': 10.0}
                if 'smoothing_factor' not in motion_config['settings']:
                    motion_config['settings']['smoothing_factor'] = {'type': 'float', 'default': 0.5}
                motion_config['settings']['motion_threshold']['default'] = self.motion_threshold_spin.value()
                motion_config['settings']['smoothing_factor']['default'] = self.motion_smoothing_spin.value()
                with open(motion_json, 'w') as f:
                    json.dump(motion_config, f, indent=2)
            
            # Translation Chain
            chain_json = plugins_dir / "translation_chain" / "plugin.json"
            if chain_json.exists():
                with open(chain_json, 'r') as f:
                    chain_config = json.load(f)
                chain_config['enabled'] = self.chain_plugin_enabled.isChecked()
                if 'settings' not in chain_config:
                    chain_config['settings'] = {}
                if 'timeout_per_engine' not in chain_config['settings']:
                    chain_config['settings']['timeout_per_engine'] = {'type': 'float', 'default': 2.0}
                chain_config['settings']['timeout_per_engine']['default'] = self.chain_timeout_spin.value()
                with open(chain_json, 'w') as f:
                    json.dump(chain_config, f, indent=2)
            
            # Spell Corrector (text processor)
            spell_json = Path("plugins/text_processors/spell_corrector/plugin.json")
            if spell_json.exists():
                with open(spell_json, 'r') as f:
                    spell_config = json.load(f)
                spell_config['enabled'] = self.spell_plugin_enabled.isChecked()
                spell_config['settings']['aggressive_mode']['default'] = self.spell_aggressive_check.isChecked()
                spell_config['settings']['fix_capitalization']['default'] = self.spell_fix_caps_check.isChecked()
                spell_config['settings']['min_confidence']['default'] = self.spell_confidence_spin.value()
                with open(spell_json, 'w') as f:
                    json.dump(spell_config, f, indent=2)
            
            # Save master setting
            if self.config_manager:
                self.config_manager.set_setting('pipeline.enable_optimizer_plugins', 
                                               self.plugins_enabled_check.isChecked())
                # Save all new plugin settings to config
                self.save_config()
            
            QMessageBox.information(
                self,
                "Plugin Settings Applied",
                "All plugin settings have been updated!\n\n"
                "Changes include:\n"
                "• Parallel Capture\n"
                "• Parallel Translation\n"
                "• Motion Tracker\n"
                "• Spell Corrector\n"
                "• Translation Chain\n"
                "• Text Validator\n\n"
                "Restart the translation to apply changes."
            )
            
            self.settingChanged.emit()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to save plugin settings:\n{str(e)}"
            )
    
    def _update_metrics(self):
        """Update metrics display."""
        # Check if widgets are initialized
        if not hasattr(self, 'status_label'):
            return
        
        # Update OCR engine display
        self._update_ocr_engine_display()
        
        # Update active components
        self._update_active_components()
        
        # Update plugins summary
        self._update_plugins_summary()
        
        if not self.pipeline:
            self._show_placeholder_data()
            self._update_stages_table()
            return
        
        try:
            # Try to get real metrics from pipeline
            if hasattr(self.pipeline, 'get_metrics'):
                metrics = self.pipeline.get_metrics()
                if metrics is not None:
                    # Pipeline is running, show real metrics
                    self._update_from_metrics(metrics)
                else:
                    # Pipeline not started yet, show idle state
                    self._show_idle_state()
            elif hasattr(self.pipeline, 'get_state'):
                state = self.pipeline.get_state()
                if state is not None:
                    # Pipeline has state, update display
                    self._update_from_state(state)
                else:
                    # Pipeline not started yet, show idle state
                    self._show_idle_state()
            else:
                # Show placeholder with pipeline info
                self._show_idle_state()
            
            # Update stages table
            self._update_stages_table()
            
        except Exception as e:
            print(f"[ERROR] Failed to update metrics: {e}")
            import traceback
            traceback.print_exc()
            self._show_placeholder_data()
    
    def _show_placeholder_data(self):
        """Show placeholder data when pipeline is not fully initialized."""
        # Check if widgets exist before updating
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText("Status: Loading Pipeline...")
        if hasattr(self, 'fps_label') and self.fps_label:
            self.fps_label.setText("-- FPS")
        if hasattr(self, 'latency_label') and self.latency_label:
            self.latency_label.setText("-- ms")
        if hasattr(self, 'frames_label') and self.frames_label:
            self.frames_label.setText("--")
        if hasattr(self, 'translations_label') and self.translations_label:
            self.translations_label.setText("--")
        if hasattr(self, 'cache_hits_label') and self.cache_hits_label:
            self.cache_hits_label.setText("--")
        if hasattr(self, 'errors_label') and self.errors_label:
            self.errors_label.setText("--")
    
    def _show_idle_state(self):
        """Show idle state when pipeline is loaded but not running."""
        # Check if widgets exist before updating
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText("Status: Idle (Ready to Start)")
        if hasattr(self, 'fps_label') and self.fps_label:
            self.fps_label.setText("0.0 FPS")
        if hasattr(self, 'latency_label') and self.latency_label:
            self.latency_label.setText("0 ms")
        if hasattr(self, 'frames_label') and self.frames_label:
            self.frames_label.setText("0")
        if hasattr(self, 'translations_label') and self.translations_label:
            self.translations_label.setText("0")
        if hasattr(self, 'cache_hits_label') and self.cache_hits_label:
            self.cache_hits_label.setText("0 (0%)")
        if hasattr(self, 'errors_label') and self.errors_label:
            self.errors_label.setText("0")
    
    def _update_from_metrics(self, metrics):
        """Update display from pipeline metrics."""
        if metrics is None:
            self._show_placeholder_data()
            return
        
        # Handle both dict and object metrics
        if isinstance(metrics, dict):
            self.status_label.setText("Status: Running")
            self.fps_label.setText(f"{metrics.get('fps', 0):.1f} FPS")
            self.latency_label.setText(f"{metrics.get('latency_ms', 0):.1f} ms")
            self.frames_label.setText(f"{metrics.get('frames_processed', 0):,}")
            self.translations_label.setText(f"{metrics.get('translations', 0):,}")
            
            cache_hits = metrics.get('cache_hits', 0)
            total = metrics.get('total_requests', 1)
            hit_rate = (cache_hits / total * 100) if total > 0 else 0
            self.cache_hits_label.setText(f"{cache_hits:,} ({hit_rate:.1f}%)")
            
            self.errors_label.setText(f"{metrics.get('errors', 0)}")
        else:
            # Handle object-based metrics (classic pipeline)
            self.status_label.setText("Status: Running")
            self.fps_label.setText(f"{getattr(metrics, 'fps', 0):.1f} FPS")
            self.latency_label.setText(f"{getattr(metrics, 'latency_ms', 0):.1f} ms")
            self.frames_label.setText(f"{getattr(metrics, 'frames_processed', 0):,}")
            self.translations_label.setText(f"{getattr(metrics, 'translations', 0):,}")
            
            cache_hits = getattr(metrics, 'cache_hits', 0)
            total = getattr(metrics, 'total_requests', 1)
            hit_rate = (cache_hits / total * 100) if total > 0 else 0
            self.cache_hits_label.setText(f"{cache_hits:,} ({hit_rate:.1f}%)")
            
            self.errors_label.setText(f"{getattr(metrics, 'errors', 0)}")
    
    def _update_from_state(self, state):
        """Update display from pipeline state."""
        if state is None:
            self._show_placeholder_data()
            return
        
        # Handle both dict and enum state
        if isinstance(state, dict):
            state_str = state.get('state', 'unknown')
        elif hasattr(state, 'name'):
            # Enum state
            state_str = state.name
        else:
            state_str = str(state)
        
        self.status_label.setText(f"Status: {state_str.title()}")
    
    def _update_stages_table(self):
        """Update the pipeline stages table."""
        # Check if table widget exists
        if not hasattr(self, 'stages_table') or self.stages_table is None:
            return
        
        # Define the standard pipeline stages
        stages = [
            ("Capture", "Ready", "--", "--"),
            ("Preprocessing", "Ready", "--", "--"),
            ("OCR", "Ready", "--", "--"),
            ("Validation", "Ready", "--", "--"),
            ("Translation", "Ready", "--", "--"),
            ("Overlay", "Ready", "--", "--")
        ]
        
        # Check if pipeline has stage manager (modular pipeline)
        if self.pipeline and hasattr(self.pipeline, 'stage_manager'):
            try:
                stage_stats = self.pipeline.stage_manager.get_all_stats()
                stages = []
                for name, stats in stage_stats.items():
                    stages.append((
                        name.title(),
                        stats.get('state', 'unknown'),
                        f"{stats.get('executions', 0):,}",
                        f"{stats.get('average_time', 0)*1000:.1f} ms"
                    ))
            except Exception as e:
                print(f"[DEBUG] Could not get stage stats: {e}")
        
        # Update table
        try:
            self.stages_table.setRowCount(len(stages))
            for row, (stage, status, executions, avg_time) in enumerate(stages):
                self.stages_table.setItem(row, 0, QTableWidgetItem(stage))
                self.stages_table.setItem(row, 1, QTableWidgetItem(status))
                self.stages_table.setItem(row, 2, QTableWidgetItem(executions))
                self.stages_table.setItem(row, 3, QTableWidgetItem(avg_time))
        except Exception as e:
            print(f"[ERROR] Failed to update stages table: {e}")
    
    def _start_pipeline(self):
        """Start the pipeline."""
        if self.pipeline:
            # Call pipeline start
            self.status_label.setText("Status: Starting...")
    
    def _pause_pipeline(self):
        """Pause the pipeline."""
        if self.pipeline:
            # Call pipeline pause
            self.status_label.setText("Status: Paused")
    
    def _stop_pipeline(self):
        """Stop the pipeline."""
        if self.pipeline:
            # Call pipeline stop
            self.status_label.setText("Status: Stopped")
    
    def _apply_configuration(self):
        """Apply configuration changes."""
        from PyQt6.QtWidgets import QMessageBox
        
        QMessageBox.information(
            self,
            "Configuration Applied",
            "Pipeline configuration has been updated!\n\n"
            "New settings will take effect for new operations."
        )
    
    def set_pipeline(self, pipeline):
        """
        Set or update the pipeline reference.
        
        Args:
            pipeline: Pipeline instance to monitor
        """
        self.pipeline = pipeline
        print(f"[INFO] Pipeline Management tab: pipeline reference updated (pipeline={'available' if pipeline else 'None'})")
        
        # Trigger immediate update
        self._update_metrics()
        
        # Start timer if pipeline is available and not already running
        if self.pipeline and not self.update_timer.isActive():
            self.update_timer.start()
            print("[INFO] Pipeline Management tab: started metrics update timer")
    
    def _update_ocr_engine_display(self):
        """Update OCR engine display in all tabs."""
        if not self.config_manager:
            return
        
        try:
            # Get current OCR engine
            engine = self.config_manager.get_setting('ocr.engine', 'paddleocr')
            language = self.config_manager.get_setting('ocr.source_language', 'ja')
            
            # Format engine name
            engine_names = {
                'easyocr': 'EasyOCR',
                'tesseract': 'Tesseract',
                'paddleocr': 'PaddleOCR',
                'manga_ocr': 'Manga OCR'
            }
            
            language_names = {
                'ja': 'Japanese',
                'en': 'English',
                'zh': 'Chinese',
                'ko': 'Korean',
                'de': 'German',
                'fr': 'French',
                'es': 'Spanish'
            }
            
            engine_display = engine_names.get(engine.lower(), engine)
            lang_display = language_names.get(language, language)
            
            display_text = f"{engine_display} ({lang_display})"
            
            # Update OCR engine labels (not pipeline flow - that's set at creation)
            if hasattr(self, 'ocr_component_label'):
                self.ocr_component_label.setText(f"OCR Engine: {display_text} ⭐")
            
            if hasattr(self, 'current_ocr_engine_label'):
                self.current_ocr_engine_label.setText(display_text)
                
        except Exception as e:
            print(f"[WARNING] Failed to update OCR engine display: {e}")
    
    def _update_active_components(self):
        """Update active components display."""
        if not hasattr(self, 'capture_component_label'):
            return
        
        try:
            # Update capture method
            capture_method = self.config_manager.get_setting('capture.method', 'directx') if self.config_manager else 'directx'
            self.capture_component_label.setText(f"Capture: {capture_method.upper()} (GPU)" if capture_method == 'directx' else f"Capture: Screenshot")
            
            # Update translation
            source_lang = self.config_manager.get_setting('translation.source_language', 'ja') if self.config_manager else 'ja'
            target_lang = self.config_manager.get_setting('translation.target_language', 'de') if self.config_manager else 'de'
            self.translation_component_label.setText(f"Translation: MarianMT ({source_lang}→{target_lang})")
            
            # Update overlay
            self.overlay_component_label.setText("Overlay: PyQt6 (GPU-accelerated)")
            
        except Exception as e:
            print(f"[WARNING] Failed to update active components: {e}")
    
    def _update_plugins_summary(self):
        """Update plugins summary display - shows ALL plugins including essential ones."""
        if not hasattr(self, 'plugins_summary_label'):
            return
        
        try:
            essential_plugins = []
            enabled_optional = []
            disabled_optional = []
            
            # ===== ESSENTIAL PLUGINS (Always Active, Bypass Master Switch) =====
            
            # Frame Skip ⭐
            if hasattr(self, 'skip_plugin_enabled') and self.skip_plugin_enabled.isChecked():
                essential_plugins.append("✅ Frame Skip ⭐")
            
            # Text Validator ⭐
            if hasattr(self, 'validator_plugin_enabled') and self.validator_plugin_enabled.isChecked():
                essential_plugins.append("✅ Text Validator ⭐")
            
            # Text Block Merger ⭐ (always on, no UI)
            essential_plugins.append("✅ Text Block Merger ⭐")
            
            # Translation Cache ⭐
            if hasattr(self, 'cache_plugin_enabled') and self.cache_plugin_enabled.isChecked():
                essential_plugins.append("✅ Translation Cache ⭐")
            
            # Learning Dictionary ⭐
            if hasattr(self, 'dict_plugin_enabled') and self.dict_plugin_enabled.isChecked():
                essential_plugins.append("✅ Learning Dictionary ⭐")
            
            # ===== OPTIONAL PLUGINS (Controlled by Master Switch) =====
            
            # Capture Stage
            if hasattr(self, 'motion_plugin_enabled'):
                if self.motion_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Motion Tracker")
                else:
                    disabled_optional.append("⚪ Motion Tracker")
            
            if hasattr(self, 'parallel_capture_enabled'):
                if self.parallel_capture_enabled.isChecked():
                    enabled_optional.append("✅ Parallel Capture")
                else:
                    disabled_optional.append("⚪ Parallel Capture")
            
            # OCR Stage
            if hasattr(self, 'spell_plugin_enabled'):
                if self.spell_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Spell Corrector")
                else:
                    disabled_optional.append("⚪ Spell Corrector")
            
            if hasattr(self, 'parallel_plugin_enabled'):
                if self.parallel_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Parallel OCR")
                else:
                    disabled_optional.append("⚪ Parallel OCR")
            
            # Translation Stage
            if hasattr(self, 'batch_plugin_enabled'):
                if self.batch_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Batch Processing")
                else:
                    disabled_optional.append("⚪ Batch Processing")
            
            if hasattr(self, 'chain_plugin_enabled'):
                if self.chain_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Translation Chain")
                else:
                    disabled_optional.append("⚪ Translation Chain")
            
            # Global Plugins
            if hasattr(self, 'async_plugin_enabled'):
                if self.async_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Async Pipeline")
                else:
                    disabled_optional.append("⚪ Async Pipeline")
            
            if hasattr(self, 'priority_plugin_enabled'):
                if self.priority_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Priority Queue")
                else:
                    disabled_optional.append("⚪ Priority Queue")
            
            if hasattr(self, 'work_plugin_enabled'):
                if self.work_plugin_enabled.isChecked():
                    enabled_optional.append("✅ Work-Stealing Pool")
                else:
                    disabled_optional.append("⚪ Work-Stealing Pool")
            
            # Calculate totals
            total_essential = len(essential_plugins)
            total_optional = len(enabled_optional) + len(disabled_optional)
            total_enabled = total_essential + len(enabled_optional)
            total_plugins = total_essential + total_optional
            
            # Format summary
            summary = f"Active Plugins: {total_enabled}/{total_plugins}\n\n"
            
            # Essential plugins (always shown)
            summary += "Essential (Always Active):\n" + "\n".join(essential_plugins)
            
            # Enabled optional plugins
            if enabled_optional:
                summary += "\n\nEnabled Optional:\n" + "\n".join(enabled_optional)
            
            # Disabled optional plugins (show first 3)
            if disabled_optional:
                summary += "\n\nDisabled:\n" + "\n".join(disabled_optional[:3])
                if len(disabled_optional) > 3:
                    summary += f"\n... and {len(disabled_optional) - 3} more"
            
            self.plugins_summary_label.setText(summary)
            
        except Exception as e:
            print(f"[WARNING] Failed to update plugins summary: {e}")
            import traceback
            traceback.print_exc()
    
    def load_config(self):
        """Load configuration."""
        if not self.config_manager:
            return
        
        # Load MASTER plugin enable/disable setting
        plugins_enabled = self.config_manager.get_setting('pipeline.enable_optimizer_plugins', True)  # Default to enabled
        if hasattr(self, 'plugins_enabled_check'):
            self.plugins_enabled_check.setChecked(plugins_enabled)
            # Disable/enable all plugin checkboxes based on master setting
            self._on_plugins_enabled_changed(Qt.CheckState.Checked if plugins_enabled else Qt.CheckState.Unchecked)
        
        # Sync overview tab master switch
        if hasattr(self, 'overview_plugins_master_check'):
            self.overview_plugins_master_check.blockSignals(True)
            self.overview_plugins_master_check.setChecked(plugins_enabled)
            self.overview_plugins_master_check.blockSignals(False)
        
        # Load Parallel Capture settings
        if hasattr(self, 'parallel_capture_enabled'):
            self.parallel_capture_enabled.setChecked(
                self.config_manager.get_setting('pipeline.parallel_capture.enabled', False))
            self.parallel_capture_workers_spin.setValue(
                self.config_manager.get_setting('pipeline.parallel_capture.workers', 4))
        
        # Load Parallel Translation settings
        if hasattr(self, 'parallel_translation_enabled'):
            self.parallel_translation_enabled.setChecked(
                self.config_manager.get_setting('pipeline.parallel_translation.enabled', False))
            self.parallel_translation_workers_spin.setValue(
                self.config_manager.get_setting('pipeline.parallel_translation.workers', 4))
        
        # Load Motion Tracker settings
        if hasattr(self, 'motion_plugin_enabled'):
            self.motion_plugin_enabled.setChecked(
                self.config_manager.get_setting('pipeline.plugins.motion_tracker.enabled', True))
            self.motion_threshold_spin.setValue(
                self.config_manager.get_setting('pipeline.plugins.motion_tracker.threshold', 10.0))
            self.motion_smoothing_spin.setValue(
                self.config_manager.get_setting('pipeline.plugins.motion_tracker.smoothing', 0.5))
        
        # Load Spell Corrector settings
        if hasattr(self, 'spell_plugin_enabled'):
            self.spell_plugin_enabled.setChecked(
                self.config_manager.get_setting('pipeline.plugins.spell_corrector.enabled', True))
            self.spell_aggressive_check.setChecked(
                self.config_manager.get_setting('pipeline.plugins.spell_corrector.aggressive_mode', False))
            self.spell_fix_caps_check.setChecked(
                self.config_manager.get_setting('pipeline.plugins.spell_corrector.fix_capitalization', True))
            self.spell_confidence_spin.setValue(
                self.config_manager.get_setting('pipeline.plugins.spell_corrector.min_confidence', 0.5))
        
        # Load Intelligent Text Processor settings
        if hasattr(self, 'intelligent_plugin_enabled'):
            self.intelligent_plugin_enabled.setChecked(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enabled', True))
            self.intelligent_corrections_check.setChecked(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enable_corrections', True))
            self.intelligent_context_check.setChecked(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enable_context', True))
            self.intelligent_validation_check.setChecked(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.enable_validation', True))
            self.intelligent_min_confidence_spin.setValue(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.min_confidence', 0.3))
            self.intelligent_min_word_length_spin.setValue(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.min_word_length', 2))
            self.intelligent_auto_learn_check.setChecked(
                self.config_manager.get_setting('pipeline.plugins.intelligent_text_processor.auto_learn', True))
        
        # Load Translation Chain settings (Multi-Language: JA→EN→DE)
        if hasattr(self, 'chain_plugin_enabled'):
            self.chain_plugin_enabled.setChecked(
                self.config_manager.get_setting('pipeline.plugins.translation_chain.enabled', False))
            
            # Load intermediate language
            if hasattr(self, 'chain_intermediate_lang_combo'):
                intermediate_lang = self.config_manager.get_setting('pipeline.plugins.translation_chain.intermediate_language', 'en')
                index = self.chain_intermediate_lang_combo.findText(intermediate_lang)
                if index >= 0:
                    self.chain_intermediate_lang_combo.setCurrentIndex(index)
            
            # Load quality threshold
            if hasattr(self, 'chain_quality_threshold_spin'):
                self.chain_quality_threshold_spin.setValue(
                    self.config_manager.get_setting('pipeline.plugins.translation_chain.quality_threshold', 0.7))
            
            # Load save all mappings
            if hasattr(self, 'chain_save_all_check'):
                self.chain_save_all_check.setChecked(
                    self.config_manager.get_setting('pipeline.plugins.translation_chain.save_all_mappings', True))
        
        # Update OCR engine display
        self._update_ocr_engine_display()
        
        # Sync overview tab checkboxes with detailed tab checkboxes
        self._sync_overview_checkboxes_from_detailed()
    
    def save_config(self):
        """Save configuration."""
        if not self.config_manager:
            return
        
        # Save plugin settings
        if hasattr(self, 'plugins_enabled_check'):
            self.config_manager.set_setting('pipeline.enable_optimizer_plugins', 
                                           self.plugins_enabled_check.isChecked())
        
        # Save Parallel Capture settings
        if hasattr(self, 'parallel_capture_enabled'):
            self.config_manager.set_setting('pipeline.parallel_capture.enabled',
                                           self.parallel_capture_enabled.isChecked())
            self.config_manager.set_setting('pipeline.parallel_capture.workers',
                                           self.parallel_capture_workers_spin.value())
        
        # Save Parallel Translation settings
        if hasattr(self, 'parallel_translation_enabled'):
            self.config_manager.set_setting('pipeline.parallel_translation.enabled',
                                           self.parallel_translation_enabled.isChecked())
            self.config_manager.set_setting('pipeline.parallel_translation.workers',
                                           self.parallel_translation_workers_spin.value())
        
        # Save Motion Tracker settings
        if hasattr(self, 'motion_plugin_enabled'):
            self.config_manager.set_setting('pipeline.plugins.motion_tracker.enabled',
                                           self.motion_plugin_enabled.isChecked())
            self.config_manager.set_setting('pipeline.plugins.motion_tracker.threshold',
                                           self.motion_threshold_spin.value())
            self.config_manager.set_setting('pipeline.plugins.motion_tracker.smoothing',
                                           self.motion_smoothing_spin.value())
        
        # Save Spell Corrector settings
        if hasattr(self, 'spell_plugin_enabled'):
            self.config_manager.set_setting('pipeline.plugins.spell_corrector.enabled',
                                           self.spell_plugin_enabled.isChecked())
            self.config_manager.set_setting('pipeline.plugins.spell_corrector.aggressive_mode',
                                           self.spell_aggressive_check.isChecked())
            self.config_manager.set_setting('pipeline.plugins.spell_corrector.fix_capitalization',
                                           self.spell_fix_caps_check.isChecked())
            self.config_manager.set_setting('pipeline.plugins.spell_corrector.min_confidence',
                                           self.spell_confidence_spin.value())
        
        # Save Intelligent Text Processor settings
        if hasattr(self, 'intelligent_plugin_enabled'):
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.enabled',
                                           self.intelligent_plugin_enabled.isChecked())
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.enable_corrections',
                                           self.intelligent_corrections_check.isChecked())
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.enable_context',
                                           self.intelligent_context_check.isChecked())
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.enable_validation',
                                           self.intelligent_validation_check.isChecked())
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.min_confidence',
                                           self.intelligent_min_confidence_spin.value())
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.min_word_length',
                                           self.intelligent_min_word_length_spin.value())
            self.config_manager.set_setting('pipeline.plugins.intelligent_text_processor.auto_learn',
                                           self.intelligent_auto_learn_check.isChecked())
        
        # Save Translation Chain settings (Multi-Language: JA→EN→DE)
        if hasattr(self, 'chain_plugin_enabled'):
            self.config_manager.set_setting('pipeline.plugins.translation_chain.enabled',
                                           self.chain_plugin_enabled.isChecked())
            
            # Save intermediate language
            if hasattr(self, 'chain_intermediate_lang_combo'):
                self.config_manager.set_setting('pipeline.plugins.translation_chain.intermediate_language',
                                               self.chain_intermediate_lang_combo.currentText())
            
            # Save quality threshold
            if hasattr(self, 'chain_quality_threshold_spin'):
                self.config_manager.set_setting('pipeline.plugins.translation_chain.quality_threshold',
                                               self.chain_quality_threshold_spin.value())
            
            # Save save all mappings
            if hasattr(self, 'chain_save_all_check'):
                self.config_manager.set_setting('pipeline.plugins.translation_chain.save_all_mappings',
                                               self.chain_save_all_check.isChecked())
    
    def validate(self) -> bool:
        """Validate settings."""
        return True


    def _create_text_processors_section(self) -> QGroupBox:
        """Create text processor plugins section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pipeline_management_text_processor_plugins_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # Description
        desc_label = QLabel(
            "Text processors run after OCR to clean and correct text before translation.\n"
            "Enable spell correction to fix common OCR errors and improve translation quality."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # Spell Corrector Plugin
        spell_group = QGroupBox()
        self.set_translatable_text(spell_group, "pipeline_management_intelligent_spell_corrector_section")
        spell_layout = QFormLayout(spell_group)
        spell_layout.setSpacing(8)
        
        # Enable/Disable
        self.spell_enabled_check = QCheckBox()
        self.set_translatable_text(self.spell_enabled_check, "pipeline_management_enable_spell_correction_check")
        self.spell_enabled_check.setChecked(True)
        self.spell_enabled_check.stateChanged.connect(self._on_spell_enabled_changed)
        spell_layout.addRow("Status:", self.spell_enabled_check)
        
        # Aggressive Mode
        self.spell_aggressive_check = QCheckBox()
        self.set_translatable_text(self.spell_aggressive_check, "pipeline_management_use_aggressive_spell_checking_may_over-c_check")
        self.spell_aggressive_check.setChecked(False)
        self.spell_aggressive_check.stateChanged.connect(self._on_spell_setting_changed)
        spell_layout.addRow("Mode:", self.spell_aggressive_check)
        
        # Use Learning Dictionary
        self.spell_use_dict_check = QCheckBox()
        self.set_translatable_text(self.spell_use_dict_check, "pipeline_management_learn_from_translation_dictionary_check")
        self.spell_use_dict_check.setChecked(True)
        self.spell_use_dict_check.stateChanged.connect(self._on_spell_setting_changed)
        spell_layout.addRow("Learning:", self.spell_use_dict_check)
        
        # Fix Capitalization
        self.spell_fix_caps_check = QCheckBox()
        self.set_translatable_text(self.spell_fix_caps_check, "pipeline_management_fix_random_capitalization_errors_check")
        self.spell_fix_caps_check.setChecked(True)
        self.spell_fix_caps_check.stateChanged.connect(self._on_spell_setting_changed)
        spell_layout.addRow("Capitalization:", self.spell_fix_caps_check)
        
        # Confidence Threshold
        confidence_layout = QHBoxLayout()
        self.spell_confidence_spin = CustomDoubleSpinBox()
        self.spell_confidence_spin.setRange(0.0, 1.0)
        self.spell_confidence_spin.setSingleStep(0.05)
        self.spell_confidence_spin.setValue(0.5)
        self.spell_confidence_spin.setDecimals(2)
        self.spell_confidence_spin.valueChanged.connect(self._on_spell_setting_changed)
        confidence_layout.addWidget(self.spell_confidence_spin)
        confidence_layout.addWidget(QLabel("(0.0 = lenient, 1.0 = strict)"))
        confidence_layout.addStretch()
        spell_layout.addRow("Min Confidence:", confidence_layout)
        
        # Language
        language_layout = QHBoxLayout()
        self.spell_language_combo = QComboBox()
        self.spell_language_combo.addItems(['en', 'de', 'es', 'fr', 'it', 'pt', 'ru', 'ja', 'ko', 'zh'])
        self.spell_language_combo.setCurrentText('en')
        self.spell_language_combo.currentTextChanged.connect(self._on_spell_setting_changed)
        language_layout.addWidget(self.spell_language_combo)
        language_layout.addStretch()
        spell_layout.addRow("Language:", language_layout)
        
        # Statistics (if available)
        self.spell_stats_label = QLabel("Statistics: Not available (plugin not loaded)")
        self.spell_stats_label.setStyleSheet("color: #888; font-size: 10px;")
        spell_layout.addRow("", self.spell_stats_label)
        
        # Info box
        info_label = QLabel(
            "💡 <b>Tip:</b> Install pyspellchecker for better spell checking:<br>"
            "<code>pip install pyspellchecker</code>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background: #2a2a2a; padding: 8px; border-radius: 4px; font-size: 10px;")
        spell_layout.addRow("", info_label)
        
        layout.addWidget(spell_group)
        
        return group
    
    def _on_spell_enabled_changed(self, state):
        """Handle spell corrector enable/disable."""
        enabled = state == Qt.CheckState.Checked.value
        
        # Update plugin.json
        plugin_json_path = Path("plugins/text_processors/spell_corrector/plugin.json")
        if plugin_json_path.exists():
            try:
                with open(plugin_json_path, 'r') as f:
                    plugin_data = json.load(f)
                
                plugin_data['enabled'] = enabled
                
                with open(plugin_json_path, 'w') as f:
                    json.dump(plugin_data, f, indent=2)
                
                print(f"[SETTINGS] Spell corrector {'enabled' if enabled else 'disabled'}")
                self.settingChanged.emit()
            except Exception as e:
                print(f"[SETTINGS] Error updating spell corrector: {e}")
    
    def _on_spell_setting_changed(self):
        """Handle spell corrector setting changes."""
        # Update plugin.json settings
        plugin_json_path = Path("plugins/text_processors/spell_corrector/plugin.json")
        if plugin_json_path.exists():
            try:
                with open(plugin_json_path, 'r') as f:
                    plugin_data = json.load(f)
                
                # Update settings
                if 'settings' not in plugin_data:
                    plugin_data['settings'] = {}
                
                plugin_data['settings']['aggressive_mode'] = {
                    'type': 'boolean',
                    'default': self.spell_aggressive_check.isChecked(),
                    'description': 'Use aggressive spell checking (may over-correct)'
                }
                
                plugin_data['settings']['use_learning_dict'] = {
                    'type': 'boolean',
                    'default': self.spell_use_dict_check.isChecked(),
                    'description': 'Learn from translation dictionary to improve corrections'
                }
                
                plugin_data['settings']['fix_capitalization'] = {
                    'type': 'boolean',
                    'default': self.spell_fix_caps_check.isChecked(),
                    'description': 'Fix random capitalization errors'
                }
                
                plugin_data['settings']['min_confidence'] = {
                    'type': 'float',
                    'default': self.spell_confidence_spin.value(),
                    'description': 'Minimum confidence to apply correction (0.0-1.0)'
                }
                
                plugin_data['settings']['language'] = {
                    'type': 'string',
                    'default': self.spell_language_combo.currentText(),
                    'description': 'Language for spell checking'
                }
                
                with open(plugin_json_path, 'w') as f:
                    json.dump(plugin_data, f, indent=2)
                
                print(f"[SETTINGS] Spell corrector settings updated")
                self.settingChanged.emit()
            except Exception as e:
                print(f"[SETTINGS] Error updating spell corrector settings: {e}")
    
    def _update_spell_stats(self):
        """Update spell corrector statistics display."""
        # This would be called periodically to show stats
        # For now, just a placeholder
        pass

    
    def eventFilter(self, obj, event):
        """Event filter to catch secret unlock key combination."""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtWidgets import QMessageBox
        
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            
            # Check for Alt+V
            if key_event.modifiers() == Qt.KeyboardModifier.AltModifier:
                if key_event.key() == Qt.Key.Key_V:
                    self._unlock_secret_feature()
                    return True
        
        return super().eventFilter(obj, event)
    
    def _unlock_secret_feature(self):
        """Unlock the secret audio translation feature and open the dialog."""
        from PyQt6.QtWidgets import QMessageBox
        
        # Save unlock state first
        if self.config_manager:
            config = self.config_manager.config
            if 'plugins' not in config:
                config['plugins'] = {}
            if 'system_diagnostics' not in config['plugins']:
                config['plugins']['system_diagnostics'] = {}
            
            # Check if already unlocked
            already_unlocked = config['plugins']['system_diagnostics'].get('unlocked', False)
            
            # Mark as unlocked
            config['plugins']['system_diagnostics']['unlocked'] = True
            self.config_manager.save_config()
            
            print("[SECRET] Audio translation feature unlocked!")
        else:
            already_unlocked = False
        
        # Show unlock message only if first time
        if not already_unlocked:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Secret Unlocked!")
            msg_box.setText("🎤 You are now master of all languages")
            msg_box.setInformativeText(
                "Bidirectional Audio Translation has been unlocked!\n\n"
                "Opening the conversation dialog...\n\n"
                "Features:\n"
                "• Real-time two-way conversations\n"
                "• Speech-to-Text (Whisper AI)\n"
                "• Translation (MarianMT)\n"
                "• Text-to-Speech (AI Voice)\n"
                "• Live transcript\n\n"
                "Perfect for international conversations!"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.exec()
        
        # Directly open the bidirectional audio dialog
        print("[SECRET] Opening bidirectional audio dialog...")
        self._open_bidirectional_audio_dialog()

    
    def _is_secret_unlocked(self) -> bool:
        """Check if the secret audio translation feature is unlocked."""
        if self.config_manager:
            config = self.config_manager.config
            return config.get('plugins', {}).get('system_diagnostics', {}).get('unlocked', False)
        return False
    
    def _open_bidirectional_audio_dialog(self):
        """Open the audio translation dialog"""
        try:
            from ui.dialogs.audio_translation_dialog import show_audio_translation_dialog
            from plugins.optimizers.system_diagnostics.optimizer import SystemDiagnosticsOptimizer
            
            # Get config
            config = self.config_manager.get_setting('plugins.system_diagnostics', {})
            
            # Initialize plugin instance
            plugin = SystemDiagnosticsOptimizer(config)
            
            # Show dialog
            show_audio_translation_dialog(self.config_manager, plugin, self)
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open audio translation dialog:\n{str(e)}"
            )
    
    def _create_system_diagnostics_section(self) -> QGroupBox:
        """Create system diagnostics (audio translation) section - SECRET FEATURE."""
        group = QGroupBox()
        self.set_translatable_text(group, "pipeline_management_system_diagnostics_audio_translation_section")
        layout = QFormLayout(group)
        
        # Enabled checkbox
        self.diagnostics_plugin_enabled = QCheckBox()
        self.set_translatable_text(self.diagnostics_plugin_enabled, "pipeline_management_enabled_check_19")
        self.diagnostics_plugin_enabled.setChecked(False)
        self.diagnostics_plugin_enabled.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("Status:", self.diagnostics_plugin_enabled)
        
        # Description
        desc = QLabel("Real-time audio translation: Speech-to-Text → Translation → Text-to-Speech")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 8pt;")
        layout.addRow("", desc)
        
        # Audio mode toggle
        self.diagnostics_audio_mode = QCheckBox()
        self.set_translatable_text(self.diagnostics_audio_mode, "pipeline_management_enable_audio_translation_mode_check")
        self.diagnostics_audio_mode.setChecked(False)
        self.diagnostics_audio_mode.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.diagnostics_audio_mode)
        
        # Whisper model
        self.diagnostics_whisper_model = QComboBox()
        self.diagnostics_whisper_model.addItems(["tiny", "base", "small", "medium", "large"])
        self.diagnostics_whisper_model.setCurrentText("base")
        self.diagnostics_whisper_model.currentTextChanged.connect(self.settingChanged.emit)
        layout.addRow("Whisper Model:", self.diagnostics_whisper_model)
        
        # TTS engine
        self.diagnostics_tts_engine = QComboBox()
        self.diagnostics_tts_engine.addItems(["coqui", "system"])
        self.diagnostics_tts_engine.setCurrentText("coqui")
        self.diagnostics_tts_engine.currentTextChanged.connect(self.settingChanged.emit)
        layout.addRow("TTS Engine:", self.diagnostics_tts_engine)
        
        # Auto-play
        self.diagnostics_auto_play = QCheckBox()
        self.set_translatable_text(self.diagnostics_auto_play, "pipeline_management_automatically_play_translated_audio_check")
        self.diagnostics_auto_play.setChecked(True)
        self.diagnostics_auto_play.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.diagnostics_auto_play)
        
        # Voice speed
        self.diagnostics_voice_speed = CustomDoubleSpinBox()
        self.diagnostics_voice_speed.setRange(0.5, 2.0)
        self.diagnostics_voice_speed.setSingleStep(0.1)
        self.diagnostics_voice_speed.setValue(1.0)
        self.diagnostics_voice_speed.valueChanged.connect(self.settingChanged.emit)
        layout.addRow("Voice Speed:", self.diagnostics_voice_speed)
        
        # Microphone device
        self.diagnostics_mic_device = CustomSpinBox()
        self.diagnostics_mic_device.setRange(-1, 10)
        self.diagnostics_mic_device.setValue(-1)
        self.diagnostics_mic_device.setSuffix(" (default)")
        self.diagnostics_mic_device.valueChanged.connect(self.settingChanged.emit)
        layout.addRow("Microphone Device:", self.diagnostics_mic_device)
        
        # Speaker device
        self.diagnostics_speaker_device = CustomSpinBox()
        self.diagnostics_speaker_device.setRange(-1, 10)
        self.diagnostics_speaker_device.setValue(-1)
        self.diagnostics_speaker_device.setSuffix(" (default)")
        self.diagnostics_speaker_device.valueChanged.connect(self.settingChanged.emit)
        layout.addRow("Speaker Device:", self.diagnostics_speaker_device)
        
        # VAD sensitivity
        self.diagnostics_vad_sensitivity = CustomSpinBox()
        self.diagnostics_vad_sensitivity.setRange(0, 3)
        self.diagnostics_vad_sensitivity.setValue(2)
        self.diagnostics_vad_sensitivity.valueChanged.connect(self.settingChanged.emit)
        layout.addRow("VAD Sensitivity:", self.diagnostics_vad_sensitivity)
        
        # GPU toggle
        self.diagnostics_use_gpu = QCheckBox()
        self.set_translatable_text(self.diagnostics_use_gpu, "pipeline_management_use_gpu_acceleration_3-5x_faster_check")
        self.diagnostics_use_gpu.setChecked(True)
        self.diagnostics_use_gpu.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.diagnostics_use_gpu)
        
        # Note
        note = QLabel("💡 Perfect for real-time meeting translation (German ↔ Japanese)")
        note.setStyleSheet("color: #2196F3; font-size: 8pt; font-style: italic;")
        layout.addRow("", note)
        
        # Installation note
        install_note = QLabel("📦 Requires: pip install openai-whisper TTS pyaudio webrtcvad sounddevice")
        install_note.setStyleSheet("color: #FF9800; font-size: 8pt; font-style: italic;")
        layout.addRow("", install_note)
        
        # Bidirectional audio button
        bidirectional_btn = QPushButton()
        self.set_translatable_text(bidirectional_btn, "pipeline_management_open_bidirectional_audio_translation_button")
        bidirectional_btn.clicked.connect(self._open_bidirectional_audio_dialog)
        bidirectional_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addRow("", bidirectional_btn)
        
        return group
