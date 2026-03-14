"""
Enhanced Log Viewer with Analysis and Recommendations

Features:
- Browse and select log files
- Real-time log tailing
- Severity, category, and thread filtering
- Color-coded log levels with thread/category/coordinate highlighting
- Quick analysis with navigation
- Recommendation panel with keyword-based suggestions
- Pipeline summary panel
- Export analysis reports
"""

import logging
import os
import re
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QVBoxLayout, QHBoxLayout,
    QMessageBox, QTextEdit, QPushButton, QLabel, QComboBox,
    QGroupBox, QLineEdit, QCheckBox, QSplitter, QFrame, QScrollArea
)
from PyQt6.QtGui import (
    QFont, QTextCursor, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QColor
)
from PyQt6.QtCore import Qt, QTimer
from app.localization import tr

logger = logging.getLogger(__name__)

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

_LEVEL_PATTERN = re.compile(
    r'\b(DEBUG|INFO|WARNING|ERROR|FATAL)\b'
)

# Regex to extract module name from log lines:
#   Standard: [LEVEL] [TIME] [module.name] [ThreadName] msg
#   Debug:    [LEVEL] [TIME.ms] [module.name:func:line] [ThreadName] msg
_MODULE_PATTERN = re.compile(
    r'\]\s+\[([^\]]+?)(?::[\w]+:\d+)?\]\s+\[([^\]]+)\]'
)

_CATEGORY_PREFIXES: dict[str, list[str]] = {
    "Pipeline":    ["optikr.workflow.pipeline", "app.workflow.pipeline"],
    "Capture":     ["optikr.capture", "app.capture"],
    "OCR":         ["optikr.ocr", "app.ocr", "plugins.stages.ocr"],
    "Translation": ["optikr.translation", "app.translation", "plugins.stages.translation"],
    "Overlay":     ["optikr.overlay", "app.overlay", "ui.overlay"],
    "Plugin":      ["optikr.workflow.plugin", "app.workflow.plugin", "plugins.enhancers"],
    "Async":       ["optikr.workflow.pipeline.strategies", "app.workflow.pipeline.strategies"],
}

def _module_to_category(module_name: str) -> str:
    """Map a logger module name to a UI category."""
    for category, prefixes in _CATEGORY_PREFIXES.items():
        for prefix in prefixes:
            if module_name.startswith(prefix):
                return category
    return "Other"

def _extract_thread_name(line: str) -> str | None:
    """Extract the thread name field from a log line."""
    m = _MODULE_PATTERN.search(line)
    if m:
        return m.group(2)
    return None

def _extract_module_name(line: str) -> str | None:
    """Extract the module/logger name field from a log line."""
    m = _MODULE_PATTERN.search(line)
    if m:
        return m.group(1)
    return None


class LogLevelHighlighter(QSyntaxHighlighter):
    """Color-codes log lines by severity level, thread names, categories, and coordinates."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Line-level formats (applied to the whole line based on severity)
        self._line_formats: list[tuple[re.Pattern, QTextCharFormat]] = []

        fmt_error = QTextCharFormat()
        fmt_error.setForeground(QColor("#E74C3C"))
        fmt_error.setFontWeight(QFont.Weight.Bold)
        self._line_formats.append((re.compile(r'\b(ERROR|FATAL)\b'), fmt_error))

        fmt_warn = QTextCharFormat()
        fmt_warn.setForeground(QColor("#E67E22"))
        self._line_formats.append((re.compile(r'\bWARNING\b'), fmt_warn))

        fmt_exc = QTextCharFormat()
        fmt_exc.setForeground(QColor("#C0392B"))
        fmt_exc.setFontWeight(QFont.Weight.Bold)
        self._line_formats.append((re.compile(r'(Traceback|Exception|Error:)'), fmt_exc))

        # Inline formats (applied to specific spans within a line)
        self._inline_formats: list[tuple[re.Pattern, QTextCharFormat]] = []

        fmt_level_info = QTextCharFormat()
        fmt_level_info.setForeground(QColor("#2980B9"))
        fmt_level_info.setFontWeight(QFont.Weight.Bold)
        self._inline_formats.append((re.compile(r'\[INFO\]'), fmt_level_info))

        fmt_level_debug = QTextCharFormat()
        fmt_level_debug.setForeground(QColor("#95A5A6"))
        fmt_level_debug.setFontWeight(QFont.Weight.Bold)
        self._inline_formats.append((re.compile(r'\[DEBUG\]'), fmt_level_debug))

        fmt_level_warn = QTextCharFormat()
        fmt_level_warn.setForeground(QColor("#E67E22"))
        fmt_level_warn.setFontWeight(QFont.Weight.Bold)
        self._inline_formats.append((re.compile(r'\[WARNING\]'), fmt_level_warn))

        fmt_level_error = QTextCharFormat()
        fmt_level_error.setForeground(QColor("#E74C3C"))
        fmt_level_error.setFontWeight(QFont.Weight.Bold)
        self._inline_formats.append((re.compile(r'\[(?:ERROR|FATAL)\]'), fmt_level_error))

        # Thread name: the last bracketed field before the message
        fmt_thread = QTextCharFormat()
        fmt_thread.setForeground(QColor("#8E44AD"))
        self._fmt_thread = fmt_thread
        self._thread_pattern = re.compile(
            r'\]\s+\[([^\]]+?)(?::[\w]+:\d+)?\]\s+\[([^\]]+)\]\s'
        )

        # Module/category name
        fmt_module = QTextCharFormat()
        fmt_module.setForeground(QColor("#16A085"))
        self._fmt_module = fmt_module

        # Coordinate patterns like (123, 456) or (x=10, y=20, w=100, h=50)
        fmt_coord = QTextCharFormat()
        fmt_coord.setForeground(QColor("#D35400"))
        fmt_coord.setFontWeight(QFont.Weight.Bold)
        self._inline_formats.append((
            re.compile(r'\(\s*\d+\s*,\s*\d+\s*(?:,\s*\d+\s*)*\)'),
            fmt_coord,
        ))

        # Named coordinate patterns: (x=10, y=20) or key=value numeric groups
        self._inline_formats.append((
            re.compile(r'\(\s*\w+=\d+(?:\s*,\s*\w+=\d+)+\s*\)'),
            fmt_coord,
        ))

    def highlightBlock(self, text: str):
        # Check for line-level severity (error/warning/exception lines get full-line color)
        for pattern, fmt in self._line_formats:
            if pattern.search(text):
                self.setFormat(0, len(text), fmt)
                return

        # For non-error/warning lines, apply inline highlights
        for pattern, fmt in self._inline_formats:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)

        # Highlight thread name and module name fields
        m = self._thread_pattern.search(text)
        if m:
            # Module field: group(1)
            self.setFormat(m.start(1), len(m.group(1)), self._fmt_module)
            # Thread field: group(2)
            self.setFormat(m.start(2), len(m.group(2)), self._fmt_thread)


class LogRecommendationEngine:
    """Generates actionable recommendations from log content via keyword matching."""

    _PATTERNS = [
        {
            'pattern': re.compile(r'out of memory|MemoryError|OOM', re.IGNORECASE),
            'title_key': 'rec_memory_pressure',
            'suggestion_key': 'rec_memory_pressure_suggestion',
        },
        {
            'pattern': re.compile(r'CUDA error|cuda.*fail|nvml|GPU.*error', re.IGNORECASE),
            'title_key': 'rec_gpu_cuda',
            'suggestion_key': 'rec_gpu_cuda_suggestion',
        },
        {
            'pattern': re.compile(r'timeout|timed?\s*out|TimeoutError', re.IGNORECASE),
            'title_key': 'rec_timeout',
            'suggestion_key': 'rec_timeout_suggestion',
        },
        {
            'pattern': re.compile(r'permission\s+denied|PermissionError|Access.*denied', re.IGNORECASE),
            'title_key': 'rec_permission',
            'suggestion_key': 'rec_permission_suggestion',
        },
        {
            'pattern': re.compile(
                r'connection\s*(refused|reset|error)|ConnectionError|HTTPSConnectionPool',
                re.IGNORECASE,
            ),
            'title_key': 'rec_connection',
            'suggestion_key': 'rec_connection_suggestion',
        },
        {
            'pattern': re.compile(r'ImportError|ModuleNotFoundError', re.IGNORECASE),
            'title_key': 'rec_missing_dep',
            'suggestion_key': 'rec_missing_dep_suggestion',
        },
        {
            'pattern': re.compile(r'FileNotFoundError|No such file', re.IGNORECASE),
            'title_key': 'rec_missing_file',
            'suggestion_key': 'rec_missing_file_suggestion',
        },
        {
            'pattern': re.compile(r'api.?key|authentication|unauthorized|[^0-9]40[13]\b', re.IGNORECASE),
            'title_key': 'rec_api_key',
            'suggestion_key': 'rec_api_key_suggestion',
        },
        {
            'pattern': re.compile(r'disk\s*full|No space left|IOError.*space', re.IGNORECASE),
            'title_key': 'rec_disk_space',
            'suggestion_key': 'rec_disk_space_suggestion',
        },
        {
            'pattern': re.compile(r'model.*not\s*found|download.*fail|weights.*missing', re.IGNORECASE),
            'title_key': 'rec_model_unavail',
            'suggestion_key': 'rec_model_unavail_suggestion',
        },
    ]

    @staticmethod
    def generate(log_content: str) -> list[dict]:
        """Return up to 3 recommendations sorted by occurrence count."""
        hits: dict[str, dict] = {}
        for entry in LogRecommendationEngine._PATTERNS:
            matches = entry['pattern'].findall(log_content)
            if matches:
                title_key = entry['title_key']
                if title_key not in hits:
                    hits[title_key] = {
                        'title': tr(entry['title_key']),
                        'suggestion': tr(entry['suggestion_key']),
                        'count': len(matches),
                    }
                else:
                    hits[title_key]['count'] += len(matches)

        return sorted(hits.values(), key=lambda x: x['count'], reverse=True)[:3]


class LogAnalyzer:
    """Analyzes log files for errors, warnings, and crashes."""

    _ERROR_RE = re.compile(r'\b(ERROR|FATAL)\b')
    _WARNING_RE = re.compile(r'\bWARNING\b')
    _EXCEPTION_RE = re.compile(r'\b(Exception|Traceback)\b')
    _CRASH_RE = re.compile(r'\b(crash|crashed|segfault|core dump|unhandled)\b', re.IGNORECASE)

    @staticmethod
    def analyze(log_content: str) -> dict:
        lines = log_content.split('\n')

        analysis = {
            'total_lines': len(lines),
            'errors': [],
            'warnings': [],
            'crashes': [],
            'exceptions': [],
            'info_count': 0,
            'debug_count': 0,
            'error_count': 0,
            'warning_count': 0,
            'crash_detected': False,
        }

        for i, line in enumerate(lines, 1):
            if 'INFO' in line:
                analysis['info_count'] += 1
            if 'DEBUG' in line:
                analysis['debug_count'] += 1

            if LogAnalyzer._ERROR_RE.search(line):
                analysis['error_count'] += 1
                analysis['errors'].append({'line': i, 'text': line.strip()})

            if LogAnalyzer._WARNING_RE.search(line):
                analysis['warning_count'] += 1
                analysis['warnings'].append({'line': i, 'text': line.strip()})

            if LogAnalyzer._EXCEPTION_RE.search(line):
                analysis['exceptions'].append({'line': i, 'text': line.strip()})

            if LogAnalyzer._CRASH_RE.search(line):
                analysis['crash_detected'] = True
                analysis['crashes'].append({'line': i, 'text': line.strip()})

        return analysis

    @staticmethod
    def format_summary(a: dict) -> str:
        parts = [
            tr("log_total_lines", count=str(a['total_lines'])),
            f"DEBUG: {a['debug_count']}  |  INFO: {a['info_count']}",
            f"WARNING: {a['warning_count']}  |  ERROR: {a['error_count']}",
            tr("log_exceptions", count=str(len(a['exceptions']))),
        ]
        if a['crash_detected']:
            parts.append(tr("log_crash_detected", count=str(len(a['crashes']))))
        return '\n'.join(parts)


class LogViewerDialog(QDialog):
    """Enhanced log viewer with analysis, filtering, tailing, and recommendations."""

    _TAIL_INTERVAL_MS = 2000

    def __init__(self, logs_dir: str = "logs", parent=None):
        super().__init__(parent)
        self.logs_dir = Path(logs_dir)
        self.current_log_file: Path | None = None
        self.current_analysis: dict | None = None
        self._full_content: str = ""
        self._last_file_size: int = 0
        self._known_threads: set[str] = set()

        self.setWindowTitle(tr("log_viewer_analyzer"))
        self.setMinimumSize(1060, 750)

        self._tail_timer = QTimer(self)
        self._tail_timer.timeout.connect(self._tail_log)

        self._init_ui()
        self._load_log_files()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # --- Top: file selector + controls ---
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("log_file")))

        self.log_combo = QComboBox()
        self.log_combo.setMinimumWidth(300)
        self.log_combo.currentTextChanged.connect(self._on_log_selected)
        top.addWidget(self.log_combo)

        refresh_btn = QPushButton(tr("_refresh"))
        refresh_btn.clicked.connect(self._load_log_files)
        top.addWidget(refresh_btn)

        open_btn = QPushButton(tr("_open"))
        open_btn.clicked.connect(self._open_logs_folder)
        top.addWidget(open_btn)

        top.addStretch()

        self.tail_check = QCheckBox(tr("auto_refresh"))
        self.tail_check.setToolTip(tr("auto_refresh_tooltip"))
        self.tail_check.toggled.connect(self._toggle_tail)
        top.addWidget(self.tail_check)

        layout.addLayout(top)

        # --- Main area: splitter with left (log) and right (analysis) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel
        left = QFrame()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)

        # Search row
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(tr("search")))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("enter_text_to_search"))
        self.search_input.returnPressed.connect(self._search_text)
        search_row.addWidget(self.search_input)

        find_btn = QPushButton(tr("find"))
        find_btn.clicked.connect(self._search_text)
        search_row.addWidget(find_btn)

        self.case_sensitive_check = QCheckBox(tr("case_sensitive"))
        search_row.addWidget(self.case_sensitive_check)
        left_lay.addLayout(search_row)

        # Severity filter row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(tr("severity_filter")))

        self._level_checks: dict[str, QCheckBox] = {}
        for level in _LOG_LEVELS:
            cb = QCheckBox(level)
            cb.setChecked(True)
            cb.toggled.connect(self._apply_severity_filter)
            filter_row.addWidget(cb)
            self._level_checks[level] = cb

        clear_filt_btn = QPushButton(tr("clear"))
        clear_filt_btn.setFixedWidth(60)
        clear_filt_btn.clicked.connect(self._clear_filters)
        filter_row.addWidget(clear_filt_btn)
        filter_row.addStretch()
        left_lay.addLayout(filter_row)

        # Category filter row (Phase 9a)
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel(tr("category_filter")))

        self._category_checks: dict[str, QCheckBox] = {}
        for cat_name in list(_CATEGORY_PREFIXES.keys()) + ["Other"]:
            cb = QCheckBox(cat_name)
            cb.setChecked(True)
            cb.toggled.connect(self._apply_filters)
            cat_row.addWidget(cb)
            self._category_checks[cat_name] = cb

        cat_row.addStretch()
        left_lay.addLayout(cat_row)

        # Thread name filter row (Phase 9b)
        thread_row = QHBoxLayout()
        thread_row.addWidget(QLabel(tr("thread_filter")))

        self.thread_combo = QComboBox()
        self.thread_combo.setMinimumWidth(180)
        self.thread_combo.addItem(tr("all_threads"))
        self.thread_combo.currentTextChanged.connect(self._apply_filters)
        thread_row.addWidget(self.thread_combo)

        thread_row.addStretch()
        left_lay.addLayout(thread_row)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._highlighter = LogLevelHighlighter(self.log_text.document())
        left_lay.addWidget(self.log_text)

        splitter.addWidget(left)

        # Right panel
        right = QFrame()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)

        # Quick analysis group
        analysis_grp = QGroupBox(tr("quick_analysis"))
        analysis_lay = QVBoxLayout(analysis_grp)

        self.analysis_label = QLabel(tr("select_a_log_file_to_analyze"))
        self.analysis_label.setWordWrap(True)
        self.analysis_label.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 10pt;"
        )
        analysis_lay.addWidget(self.analysis_label)

        nav = QHBoxLayout()
        self.goto_error_btn = QPushButton(tr("go_to_first_error"))
        self.goto_error_btn.clicked.connect(self._goto_first_error)
        self.goto_error_btn.setEnabled(False)
        nav.addWidget(self.goto_error_btn)

        self.goto_warning_btn = QPushButton(tr("go_to_first_warning"))
        self.goto_warning_btn.clicked.connect(self._goto_first_warning)
        self.goto_warning_btn.setEnabled(False)
        nav.addWidget(self.goto_warning_btn)

        self.goto_crash_btn = QPushButton(tr("go_to_crash"))
        self.goto_crash_btn.clicked.connect(self._goto_crash)
        self.goto_crash_btn.setEnabled(False)
        nav.addWidget(self.goto_crash_btn)

        nav.addStretch()
        analysis_lay.addLayout(nav)
        right_lay.addWidget(analysis_grp)

        # Recommendations group
        rec_grp = QGroupBox(tr("recommendations"))
        rec_lay = QVBoxLayout(rec_grp)
        self.rec_label = QLabel(tr("no_issues_detected"))
        self.rec_label.setWordWrap(True)
        self.rec_label.setStyleSheet(
            "font-family: 'Segoe UI', sans-serif; font-size: 10pt; line-height: 1.4;"
        )
        rec_lay.addWidget(self.rec_label)
        right_lay.addWidget(rec_grp)

        # Pipeline Summary panel (Phase 9c)
        pipeline_grp = QGroupBox(tr("pipeline_summary"))
        pipeline_lay = QVBoxLayout(pipeline_grp)

        pipeline_scroll = QScrollArea()
        pipeline_scroll.setWidgetResizable(True)
        pipeline_scroll.setMaximumHeight(220)

        self.pipeline_summary_label = QLabel(tr("no_pipeline_info"))
        self.pipeline_summary_label.setWordWrap(True)
        self.pipeline_summary_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.pipeline_summary_label.setStyleSheet(
            "font-family: 'Consolas', monospace; font-size: 9pt; padding: 4px;"
        )
        self.pipeline_summary_label.setTextFormat(Qt.TextFormat.RichText)
        pipeline_scroll.setWidget(self.pipeline_summary_label)
        pipeline_lay.addWidget(pipeline_scroll)

        right_lay.addWidget(pipeline_grp)

        right_lay.addStretch()
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # --- Bottom bar ---
        bottom = QHBoxLayout()

        copy_btn = QPushButton(tr("copy_all"))
        copy_btn.clicked.connect(self._copy_all)
        bottom.addWidget(copy_btn)

        export_btn = QPushButton(tr("export_analysis"))
        export_btn.clicked.connect(self._export_analysis)
        bottom.addWidget(export_btn)

        bottom.addStretch()

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #7F8C8D; font-size: 9pt;")
        bottom.addWidget(self.status_label)

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.close)
        bottom.addWidget(close_btn)

        layout.addLayout(bottom)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _load_log_files(self):
        self.log_combo.blockSignals(True)
        self.log_combo.clear()

        if not self.logs_dir.exists():
            self.log_combo.addItem(tr("no_logs_directory_found"))
            self.log_combo.blockSignals(False)
            return

        log_files = sorted(
            self.logs_dir.glob("*.log*"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not log_files:
            self.log_combo.addItem(tr("no_log_files_found"))
            self.log_combo.blockSignals(False)
            return

        for f in log_files:
            self.log_combo.addItem(f.name)

        self.log_combo.blockSignals(False)
        self.log_combo.setCurrentIndex(0)
        self._on_log_selected(self.log_combo.currentText())

    def _on_log_selected(self, filename: str):
        if not filename or filename in (
            tr("no_logs_directory_found"),
            tr("no_log_files_found"),
        ):
            return

        log_path = self.logs_dir / filename
        if not log_path.exists():
            self.log_text.setPlainText(
                tr("log_file_not_found", path=str(log_path))
            )
            return

        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as fh:
                self._full_content = fh.read()

            self.current_log_file = log_path
            self._last_file_size = log_path.stat().st_size

            self._populate_thread_filter(self._full_content)
            self._apply_filters()

            self.current_analysis = LogAnalyzer.analyze(self._full_content)
            self._display_analysis()
            self._display_recommendations()
            self._display_pipeline_summary()

        except Exception as e:
            logger.exception("Failed to read log file: %s", log_path)
            self.log_text.setPlainText(
                tr("error_reading_log_file", error=str(e))
            )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _get_active_levels(self) -> set[str]:
        active = set()
        for level, cb in self._level_checks.items():
            if cb.isChecked():
                active.add(level)
        if active == set(_LOG_LEVELS):
            active.add("FATAL")
        return active

    def _get_active_categories(self) -> set[str]:
        return {cat for cat, cb in self._category_checks.items() if cb.isChecked()}

    def _get_selected_thread(self) -> str | None:
        """Return the selected thread name, or None for 'all threads'."""
        current = self.thread_combo.currentText()
        if current == tr("all_threads") or self.thread_combo.currentIndex() == 0:
            return None
        return current

    def _apply_severity_filter(self):
        """Legacy entry point — redirects to combined filter."""
        self._apply_filters()

    def _apply_filters(self):
        """Apply severity, category, and thread filters together (AND logic)."""
        if not self._full_content:
            self.log_text.setPlainText("")
            self._update_status(0, 0)
            return

        active_levels = self._get_active_levels()
        all_levels_active = len(active_levels) >= len(_LOG_LEVELS)

        active_cats = self._get_active_categories()
        all_cats_active = len(active_cats) >= len(_CATEGORY_PREFIXES) + 1  # +1 for "Other"

        selected_thread = self._get_selected_thread()

        # Fast path: no filtering needed
        if all_levels_active and all_cats_active and selected_thread is None:
            self.log_text.setPlainText(self._full_content)
            total = self._full_content.count('\n') + 1
            self._update_status(total, total)
            return

        lines = self._full_content.split('\n')
        filtered = []
        for line in lines:
            # Severity filter
            level_match = _LEVEL_PATTERN.search(line)
            if level_match:
                level = level_match.group(1)
                if level not in active_levels and not (level == 'FATAL' and 'ERROR' in active_levels):
                    continue
            # else: lines without a level tag always pass severity filter

            # Category filter
            if not all_cats_active:
                module = _extract_module_name(line)
                if module is not None:
                    cat = _module_to_category(module)
                    if cat not in active_cats:
                        continue

            # Thread filter
            if selected_thread is not None:
                thread = _extract_thread_name(line)
                if thread is not None and thread != selected_thread:
                    continue

            filtered.append(line)

        text = '\n'.join(filtered)
        self.log_text.setPlainText(text)
        self._update_status(len(filtered), len(lines))

    def _clear_filters(self):
        for cb in self._level_checks.values():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        for cb in self._category_checks.values():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        self.thread_combo.blockSignals(True)
        self.thread_combo.setCurrentIndex(0)
        self.thread_combo.blockSignals(False)
        self._apply_filters()

    def _update_status(self, shown: int, total: int):
        if shown == total:
            self.status_label.setText(
                tr("lines_displayed", shown=str(total))
            )
        else:
            self.status_label.setText(
                tr("lines_filtered", shown=str(shown), total=str(total))
            )

    # ------------------------------------------------------------------
    # Analysis display
    # ------------------------------------------------------------------

    def _display_analysis(self):
        if not self.current_analysis:
            return
        a = self.current_analysis
        self.analysis_label.setText(LogAnalyzer.format_summary(a))
        self.goto_error_btn.setEnabled(a['error_count'] > 0)
        self.goto_warning_btn.setEnabled(a['warning_count'] > 0)
        self.goto_crash_btn.setEnabled(a['crash_detected'])

    def _display_recommendations(self):
        recs = LogRecommendationEngine.generate(self._full_content)
        if not recs:
            self.rec_label.setText(tr("no_issues_detected"))
            return

        parts = []
        for i, r in enumerate(recs, 1):
            parts.append(
                f"<b>{i}. {r['title']}</b> ({r['count']}x)<br/>"
                f"<span style='color:#555;'>{r['suggestion']}</span>"
            )
        self.rec_label.setText("<br/><br/>".join(parts))

    # ------------------------------------------------------------------
    # Thread filter population
    # ------------------------------------------------------------------

    def _populate_thread_filter(self, content: str, incremental: bool = False):
        """Populate the thread combo with unique thread names from log content."""
        if not incremental:
            self._known_threads = set()

        for line in content.split('\n'):
            thread = _extract_thread_name(line)
            if thread:
                self._known_threads.add(thread)

        prev = self.thread_combo.currentText()
        self.thread_combo.blockSignals(True)
        self.thread_combo.clear()
        self.thread_combo.addItem(tr("all_threads"))
        for name in sorted(self._known_threads):
            self.thread_combo.addItem(name)

        idx = self.thread_combo.findText(prev)
        if idx >= 0:
            self.thread_combo.setCurrentIndex(idx)
        else:
            self.thread_combo.setCurrentIndex(0)
        self.thread_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Pipeline summary display
    # ------------------------------------------------------------------

    _SUMMARY_START_RE = re.compile(r'={3,}\s*PIPELINE\s+(?:STARTUP\s+)?SUMMARY\s*={3,}', re.IGNORECASE)
    _SUMMARY_END_RE = re.compile(r'={3,}\s*$')

    def _display_pipeline_summary(self):
        """Parse and display the pipeline startup summary banner from the log."""
        if not self._full_content:
            self.pipeline_summary_label.setText(tr("no_pipeline_info"))
            return

        # Find all summary banners; use the last one
        lines = self._full_content.split('\n')
        summary_blocks: list[list[str]] = []
        in_block = False
        current_block: list[str] = []

        for line in lines:
            if not in_block:
                if self._SUMMARY_START_RE.search(line):
                    in_block = True
                    current_block = []
                    continue
            else:
                if self._SUMMARY_END_RE.match(line.strip()) and current_block:
                    summary_blocks.append(current_block)
                    in_block = False
                    current_block = []
                else:
                    msg = line
                    # Strip the log prefix to get just the message part
                    bracket_count = 0
                    idx = 0
                    for i, ch in enumerate(msg):
                        if ch == '[':
                            bracket_count += 1
                        elif ch == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                idx = i + 1
                    if idx > 0 and idx < len(msg):
                        msg = msg[idx:].strip()
                    current_block.append(msg)

        if not summary_blocks:
            self.pipeline_summary_label.setText(tr("no_pipeline_info"))
            return

        block = summary_blocks[-1]
        html_parts = []
        for raw_line in block:
            line = raw_line.strip()
            if not line:
                continue
            # Section headers (lines like "Stages:" or "Plugins:")
            if line.endswith(':') and not line.startswith('-') and not line.startswith('•'):
                html_parts.append(f"<b style='color:#2C3E50;'>{line}</b>")
            elif line.startswith(('-', '•', '*')):
                html_parts.append(f"&nbsp;&nbsp;{line}")
            else:
                html_parts.append(line)

        self.pipeline_summary_label.setText("<br/>".join(html_parts))

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _goto_first_error(self):
        if not self.current_analysis or not self.current_analysis['errors']:
            return
        self._clear_filters()
        self._goto_line(self.current_analysis['errors'][0]['line'])

    def _goto_first_warning(self):
        if not self.current_analysis or not self.current_analysis['warnings']:
            return
        self._clear_filters()
        self._goto_line(self.current_analysis['warnings'][0]['line'])

    def _goto_crash(self):
        if not self.current_analysis or not self.current_analysis['crashes']:
            return
        self._clear_filters()
        self._goto_line(self.current_analysis['crashes'][0]['line'])

    def _goto_line(self, line_number: int):
        doc = self.log_text.document()
        block = doc.findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search_text(self):
        term = self.search_input.text()
        if not term:
            return

        flags = QTextDocument.FindFlags()
        if self.case_sensitive_check.isChecked():
            flags = QTextDocument.FindFlag.FindCaseSensitively

        if not self.log_text.find(term, flags):
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.log_text.setTextCursor(cursor)
            self.log_text.find(term, flags)

    # ------------------------------------------------------------------
    # Real-time tailing
    # ------------------------------------------------------------------

    def _toggle_tail(self, enabled: bool):
        if enabled:
            self._tail_timer.start(self._TAIL_INTERVAL_MS)
        else:
            self._tail_timer.stop()

    def _tail_log(self):
        if not self.current_log_file or not self.current_log_file.exists():
            return
        try:
            new_size = self.current_log_file.stat().st_size
            if new_size == self._last_file_size:
                return
            if new_size < self._last_file_size:
                self._on_log_selected(self.current_log_file.name)
                return

            with open(self.current_log_file, 'r', encoding='utf-8', errors='replace') as fh:
                fh.seek(self._last_file_size)
                new_data = fh.read()

            self._full_content += new_data
            self._last_file_size = new_size

            self._populate_thread_filter(new_data, incremental=True)

            self.current_analysis = LogAnalyzer.analyze(self._full_content)
            self._display_analysis()
            self._display_recommendations()
            self._display_pipeline_summary()

            self._apply_filters()

            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()

        except Exception:
            logger.debug("Tail read failed", exc_info=True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _copy_all(self):
        QApplication.clipboard().setText(self.log_text.toPlainText())

    def _export_analysis(self):
        if not self.current_analysis or not self.current_log_file:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            tr("export_analysis"),
            f"log_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            tr("text_files_filter"),
        )

        if not filename:
            return

        try:
            with open(filename, 'w', encoding='utf-8') as fh:
                fh.write(f"{tr('log_analysis_report')}\n")
                fh.write("=" * 60 + "\n")
                fh.write(f"{tr('log_export_file')}: {self.current_log_file.name}\n")
                fh.write(f"{tr('log_export_date')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                fh.write(LogAnalyzer.format_summary(self.current_analysis) + "\n")

                for section, label in [
                    ('errors', 'ERRORS'),
                    ('warnings', 'WARNINGS'),
                    ('crashes', 'CRASHES'),
                    ('exceptions', 'EXCEPTIONS'),
                ]:
                    items = self.current_analysis[section]
                    if items:
                        fh.write(f"\n{'=' * 60}\n")
                        fh.write(f"{label} ({len(items)})\n")
                        fh.write(f"{'=' * 60}\n")
                        for item in items:
                            fh.write(f"Line {item['line']}: {item['text']}\n")

                recs = LogRecommendationEngine.generate(self._full_content)
                if recs:
                    fh.write(f"\n{'=' * 60}\n")
                    fh.write(f"{tr('recommendations').upper()}\n")
                    fh.write(f"{'=' * 60}\n")
                    for r in recs:
                        fh.write(f"  [{r['count']}x] {r['title']}: {r['suggestion']}\n")

            QMessageBox.information(
                self,
                tr("export_successful"),
                tr("analysis_exported_to", path=filename),
            )
        except Exception as e:
            logger.exception("Failed to export analysis")
            QMessageBox.critical(
                self,
                tr("export_failed"),
                tr("failed_to_export", error=str(e)),
            )

    def _open_logs_folder(self):
        try:
            os.startfile(self.logs_dir)
        except Exception as e:
            logger.exception("Failed to open logs folder: %s", self.logs_dir)
            QMessageBox.warning(self, tr("error"), str(e))

    def closeEvent(self, event):
        self._tail_timer.stop()
        super().closeEvent(event)
