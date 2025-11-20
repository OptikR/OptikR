"""
Dictionary Entry Edit Dialog

Dialog for editing or adding dictionary entries.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QDoubleSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt


class DictionaryEntryEditDialog(QDialog):
    """Dialog for editing dictionary entries."""
    
    def __init__(self, parent=None, source_text="", translation="", 
                 confidence=0.9, usage_count=0):
        """
        Initialize entry edit dialog.
        
        Args:
            parent: Parent widget
            source_text: Source text
            translation: Translation text
            confidence: Confidence score
            usage_count: Usage count
        """
        super().__init__(parent)
        
        self.source_text = source_text
        self.translation = translation
        self.confidence = confidence
        self.usage_count = usage_count
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        if self.source_text:
            self.setWindowTitle("Edit Dictionary Entry")
        else:
            self.setWindowTitle("Add Dictionary Entry")
        
        self.setMinimumWidth(500)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create form
        form_group = QGroupBox("Entry Details")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        # Source text
        self.source_edit = QLineEdit(self.source_text)
        self.source_edit.setPlaceholderText("Enter source text (e.g., 'Hello' or 'How are you?')")
        form_layout.addRow("Source Text:", self.source_edit)
        
        # Translation
        self.translation_edit = QLineEdit(self.translation)
        self.translation_edit.setPlaceholderText("Enter translation (e.g., 'Hallo' or 'Wie geht es dir?')")
        form_layout.addRow("Translation:", self.translation_edit)
        
        # Confidence
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setValue(self.confidence)
        form_layout.addRow("Confidence:", self.confidence_spin)
        
        # Usage count (read-only display)
        usage_label = QLabel(f"{self.usage_count} times")
        usage_label.setStyleSheet("color: #666666;")
        form_layout.addRow("Usage Count:", usage_label)
        
        layout.addWidget(form_group)
        
        # Entry type hint
        self.type_hint = QLabel()
        self.type_hint.setStyleSheet("color: #666666; font-style: italic; padding: 5px;")
        self._update_type_hint()
        layout.addWidget(self.type_hint)
        
        # Connect signals to update hint
        self.source_edit.textChanged.connect(self._update_type_hint)
        self.translation_edit.textChanged.connect(self._update_type_hint)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setProperty("class", "action")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _update_type_hint(self):
        """Update the entry type hint."""
        source = self.source_edit.text().strip()
        translation = self.translation_edit.text().strip()
        
        if not source or not translation:
            self.type_hint.setText("")
            return
        
        # Determine type
        is_word = ' ' not in source and ' ' not in translation
        has_punctuation = any(p in source for p in '.!?,;:')
        
        if is_word and not has_punctuation:
            self.type_hint.setText("💡 This will be saved as a <b>single word</b> entry")
            self.type_hint.setStyleSheet("color: #2196F3; font-style: italic; padding: 5px;")
        else:
            self.type_hint.setText("💡 This will be saved as a <b>sentence</b> entry")
            self.type_hint.setStyleSheet("color: #4CAF50; font-style: italic; padding: 5px;")
    
    def _save(self):
        """Save entry."""
        source = self.source_edit.text().strip()
        translation = self.translation_edit.text().strip()
        
        if not source:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input", "Source text cannot be empty.")
            return
        
        if not translation:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input", "Translation cannot be empty.")
            return
        
        self.accept()
