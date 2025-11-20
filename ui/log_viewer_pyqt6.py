"""
Enhanced Log Viewer with Analysis

Features:
- Browse through all log files
- Quick analysis showing errors, warnings, crashes
- Search and filter
- Auto-detect crash points
"""

import os
import re
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QGroupBox, QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor


class LogAnalyzer:
    """Analyzes log files for errors, warnings, and crashes."""
    
    @staticmethod
    def analyze_log(log_content: str) -> dict:
        """
        Analyze log content and extract key information.
        
        Returns:
            dict with analysis results
        """
        lines = log_content.split('\n')
        
        analysis = {
            'total_lines': len(lines),
            'errors': [],
            'warnings': [],
            'crashes': [],
            'exceptions': [],
            'info_count': 0,
            'error_count': 0,
            'warning_count': 0,
            'crash_detected': False,
            'last_operation': None,
            'summary': ''
        }
        
        # Patterns to detect
        error_pattern = re.compile(r'ERROR|Error|error|FATAL|Fatal', re.IGNORECASE)
        warning_pattern = re.compile(r'WARNING|Warning|warning', re.IGNORECASE)
        exception_pattern = re.compile(r'Exception|Traceback|raise |except ', re.IGNORECASE)
        crash_pattern = re.compile(r'crash|crashed|segfault|core dump|unhandled', re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            # Count log levels
            if 'INFO' in line:
                analysis['info_count'] += 1
            
            # Detect errors
            if error_pattern.search(line):
                analysis['error_count'] += 1
                analysis['errors'].append({'line': i, 'text': line.strip()})
            
            # Detect warnings
            if warning_pattern.search(line):
                analysis['warning_count'] += 1
                analysis['warnings'].append({'line': i, 'text': line.strip()})
            
            # Detect exceptions
            if exception_pattern.search(line):
                analysis['exceptions'].append({'line': i, 'text': line.strip()})
            
            # Detect crashes
            if crash_pattern.search(line):
                analysis['crash_detected'] = True
                analysis['crashes'].append({'line': i, 'text': line.strip()})
        
        # Generate summary
        summary_parts = []
        summary_parts.append(f"📊 Total Lines: {analysis['total_lines']}")
        summary_parts.append(f"ℹ️  Info: {analysis['info_count']}")
        summary_parts.append(f"⚠️  Warnings: {analysis['warning_count']}")
        summary_parts.append(f"❌ Errors: {analysis['error_count']}")
        summary_parts.append(f"💥 Exceptions: {len(analysis['exceptions'])}")
        
        if analysis['crash_detected']:
            summary_parts.append(f"🔴 CRASH DETECTED at {len(analysis['crashes'])} location(s)")
        
        analysis['summary'] = '\n'.join(summary_parts)
        
        return analysis


class LogViewerDialog(QDialog):
    """Enhanced log viewer with analysis and navigation."""
    
    def __init__(self, logs_dir="logs", parent=None):
        super().__init__(parent)
        self.logs_dir = Path(logs_dir)
        self.current_log_file = None
        self.current_analysis = None
        
        self.setWindowTitle("Log Viewer & Analyzer")
        self.setMinimumSize(1000, 700)
        
        self._init_ui()
        self._load_log_files()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # Log file selector
        controls_layout.addWidget(QLabel("Log File:"))
        self.log_combo = QComboBox()
        self.log_combo.setMinimumWidth(300)
        self.log_combo.currentTextChanged.connect(self._on_log_selected)
        controls_layout.addWidget(self.log_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_log_files)
        controls_layout.addWidget(refresh_btn)
        
        # Open folder button
        open_folder_btn = QPushButton("📁 Open Folder")
        open_folder_btn.clicked.connect(self._open_logs_folder)
        controls_layout.addWidget(open_folder_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Analysis panel
        analysis_group = QGroupBox("📊 Quick Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_label = QLabel("Select a log file to analyze...")
        self.analysis_label.setWordWrap(True)
        self.analysis_label.setStyleSheet("font-family: 'Consolas', monospace; font-size: 10pt;")
        analysis_layout.addWidget(self.analysis_label)
        
        # Quick navigation buttons
        nav_layout = QHBoxLayout()
        
        self.goto_error_btn = QPushButton("❌ Go to First Error")
        self.goto_error_btn.clicked.connect(self._goto_first_error)
        self.goto_error_btn.setEnabled(False)
        nav_layout.addWidget(self.goto_error_btn)
        
        self.goto_warning_btn = QPushButton("⚠️  Go to First Warning")
        self.goto_warning_btn.clicked.connect(self._goto_first_warning)
        self.goto_warning_btn.setEnabled(False)
        nav_layout.addWidget(self.goto_warning_btn)
        
        self.goto_crash_btn = QPushButton("💥 Go to Crash")
        self.goto_crash_btn.clicked.connect(self._goto_crash)
        self.goto_crash_btn.setEnabled(False)
        nav_layout.addWidget(self.goto_crash_btn)
        
        nav_layout.addStretch()
        analysis_layout.addLayout(nav_layout)
        
        layout.addWidget(analysis_group)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search...")
        self.search_input.returnPressed.connect(self._search_text)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Find")
        search_btn.clicked.connect(self._search_text)
        search_layout.addWidget(search_btn)
        
        self.case_sensitive_check = QCheckBox("Case Sensitive")
        search_layout.addWidget(self.case_sensitive_check)
        
        layout.addLayout(search_layout)
        
        # Log content viewer
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_text)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy All")
        copy_btn.clicked.connect(self._copy_all)
        button_layout.addWidget(copy_btn)
        
        export_btn = QPushButton("💾 Export Analysis")
        export_btn.clicked.connect(self._export_analysis)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_log_files(self):
        """Load all log files from the logs directory."""
        self.log_combo.clear()
        
        if not self.logs_dir.exists():
            self.log_combo.addItem("No logs directory found")
            return
        
        # Get all log files, sorted by modification time (newest first)
        log_files = []
        for file in self.logs_dir.glob("*.log"):
            log_files.append((file.stat().st_mtime, file.name))
        
        log_files.sort(reverse=True)  # Newest first
        
        if not log_files:
            self.log_combo.addItem("No log files found")
            return
        
        for _, filename in log_files:
            self.log_combo.addItem(filename)
        
        # Auto-select the newest log
        if log_files:
            self.log_combo.setCurrentIndex(0)
    
    def _on_log_selected(self, filename):
        """Load and analyze the selected log file."""
        if not filename or filename in ["No logs directory found", "No log files found"]:
            return
        
        log_path = self.logs_dir / filename
        if not log_path.exists():
            self.log_text.setPlainText(f"Error: Log file not found: {log_path}")
            return
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.current_log_file = log_path
            self.log_text.setPlainText(content)
            
            # Analyze the log
            self.current_analysis = LogAnalyzer.analyze_log(content)
            self._display_analysis()
            
        except Exception as e:
            self.log_text.setPlainText(f"Error reading log file: {e}")
    
    def _display_analysis(self):
        """Display the analysis results."""
        if not self.current_analysis:
            return
        
        analysis = self.current_analysis
        
        # Update analysis label
        self.analysis_label.setText(analysis['summary'])
        
        # Enable/disable navigation buttons
        self.goto_error_btn.setEnabled(analysis['error_count'] > 0)
        self.goto_warning_btn.setEnabled(analysis['warning_count'] > 0)
        self.goto_crash_btn.setEnabled(analysis['crash_detected'])
    
    def _goto_first_error(self):
        """Jump to the first error in the log."""
        if not self.current_analysis or not self.current_analysis['errors']:
            return
        
        first_error = self.current_analysis['errors'][0]
        self._goto_line(first_error['line'])
    
    def _goto_first_warning(self):
        """Jump to the first warning in the log."""
        if not self.current_analysis or not self.current_analysis['warnings']:
            return
        
        first_warning = self.current_analysis['warnings'][0]
        self._goto_line(first_warning['line'])
    
    def _goto_crash(self):
        """Jump to the crash location in the log."""
        if not self.current_analysis or not self.current_analysis['crashes']:
            return
        
        first_crash = self.current_analysis['crashes'][0]
        self._goto_line(first_crash['line'])
    
    def _goto_line(self, line_number):
        """Jump to a specific line number."""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Move to the line
        for _ in range(line_number - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
        
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
        
        # Highlight the line
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.log_text.setTextCursor(cursor)
    
    def _search_text(self):
        """Search for text in the log."""
        search_term = self.search_input.text()
        if not search_term:
            return
        
        flags = QTextCursor.FindFlag(0)
        if self.case_sensitive_check.isChecked():
            flags = QTextCursor.FindFlag.FindCaseSensitively
        
        # Search from current position
        found = self.log_text.find(search_term, flags)
        
        if not found:
            # Try from beginning
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.log_text.setTextCursor(cursor)
            self.log_text.find(search_term, flags)
    
    def _copy_all(self):
        """Copy all log content to clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_text.toPlainText())
    
    def _export_analysis(self):
        """Export analysis to a text file."""
        if not self.current_analysis:
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analysis",
            f"log_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Log Analysis Report\n")
                    f.write(f"=" * 60 + "\n")
                    f.write(f"File: {self.current_log_file.name}\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(self.current_analysis['summary'] + "\n\n")
                    
                    if self.current_analysis['errors']:
                        f.write(f"\n{'=' * 60}\n")
                        f.write(f"ERRORS ({len(self.current_analysis['errors'])})\n")
                        f.write(f"{'=' * 60}\n")
                        for error in self.current_analysis['errors']:
                            f.write(f"Line {error['line']}: {error['text']}\n")
                    
                    if self.current_analysis['warnings']:
                        f.write(f"\n{'=' * 60}\n")
                        f.write(f"WARNINGS ({len(self.current_analysis['warnings'])})\n")
                        f.write(f"{'=' * 60}\n")
                        for warning in self.current_analysis['warnings']:
                            f.write(f"Line {warning['line']}: {warning['text']}\n")
                    
                    if self.current_analysis['crashes']:
                        f.write(f"\n{'=' * 60}\n")
                        f.write(f"CRASHES ({len(self.current_analysis['crashes'])})\n")
                        f.write(f"{'=' * 60}\n")
                        for crash in self.current_analysis['crashes']:
                            f.write(f"Line {crash['line']}: {crash['text']}\n")
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Export Successful", f"Analysis exported to:\n{filename}")
            
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Export Failed", f"Failed to export analysis:\n{e}")
    
    def _open_logs_folder(self):
        """Open the logs folder in file explorer."""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(self.logs_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.logs_dir])
            else:  # Linux
                subprocess.run(["xdg-open", self.logs_dir])
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open folder:\n{e}")
