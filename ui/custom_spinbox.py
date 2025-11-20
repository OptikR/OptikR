"""
Custom Spinbox Widget with Horizontal Layout

Displays: [−] [Value] [+]
- Minus button on left
- Value in center (larger, more prominent)
- Plus button on right
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QIntValidator, QDoubleValidator


class CustomSpinBox(QWidget):
    """
    Custom spinbox with horizontal button layout.
    
    Layout: [−] [Value] [+]
    """
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._value = 0
        self._minimum = 0
        self._maximum = 100
        self._single_step = 1
        self._suffix = ""
        self._special_value_text = ""
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)  # Ultra-tight: 1px spacing (matches ROI Detection Settings)
        
        # Minus button
        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedSize(28, 26)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #5A5A5A;
                color: #FFFFFF;
                border: 1px solid #707070;
                border-radius: 0px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #4A9EFF;
                border: 1px solid #6AB0FF;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #3A7FCC;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #555555;
                border: 1px solid #333333;
            }
        """)
        self.minus_btn.clicked.connect(self._decrement)
        layout.addWidget(self.minus_btn)
        
        # Value input (editable)
        self.value_input = QLineEdit("0")
        self.value_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_input.setMinimumWidth(80)
        self.value_input.setMaximumWidth(150)
        self.value_input.setFixedHeight(26)
        
        # Set strict integer validator
        self._validator = QIntValidator()
        self.value_input.setValidator(self._validator)
        
        self.value_input.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 2px 4px;
                font-size: 9pt;
                margin: 0px;
            }
            QLineEdit:focus {
                border: 1px solid #4A9EFF;
                background-color: #353535;
            }
        """)
        self.value_input.editingFinished.connect(self._on_manual_input)
        self.value_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.value_input)
        
        # Plus button
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(28, 26)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #5A5A5A;
                color: #FFFFFF;
                border: 1px solid #707070;
                border-radius: 0px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #4A9EFF;
                border: 1px solid #6AB0FF;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #3A7FCC;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #555555;
                border: 1px solid #333333;
            }
        """)
        self.plus_btn.clicked.connect(self._increment)
        layout.addWidget(self.plus_btn)
        
        self._update_display()
        self._update_buttons()
    
    def _increment(self):
        """Increment value."""
        if self._value < self._maximum:
            self.setValue(self._value + self._single_step)
    
    def _decrement(self):
        """Decrement value."""
        if self._value > self._minimum:
            self.setValue(self._value - self._single_step)
    
    def _update_display(self):
        """Update the value display."""
        # Check if we should show special value text
        if self._special_value_text and self._value == self._minimum:
            text = self._special_value_text
        else:
            text = str(self._value)
            if self._suffix:
                text += " " + self._suffix
        self.value_input.setText(text)
    
    def _on_text_changed(self, text):
        """Handle text changes to filter out non-numeric characters."""
        # Remove suffix for validation
        clean_text = text.replace(self._suffix, "").strip()
        
        # If text is empty or just a minus sign, allow it (intermediate state)
        if clean_text in ("", "-"):
            return
        
        # Check if the text is a valid integer
        try:
            int(clean_text)
        except ValueError:
            # Invalid input - restore to current value
            self._update_display()
    
    def _on_manual_input(self):
        """Handle manual input from user typing."""
        try:
            text = self.value_input.text().replace(self._suffix, "").strip()
            if text:
                new_value = int(text)
                # Clamp to min/max
                new_value = max(self._minimum, min(self._maximum, new_value))
                self.setValue(new_value)
            else:
                # If empty, restore current value
                self._update_display()
        except ValueError:
            # Invalid input, restore current value
            self._update_display()
    
    def _update_buttons(self):
        """Update button enabled states."""
        self.minus_btn.setEnabled(self._value > self._minimum)
        self.plus_btn.setEnabled(self._value < self._maximum)
    
    # Public API (compatible with QSpinBox)
    
    def value(self) -> int:
        """Get current value."""
        return self._value
    
    def setValue(self, value: int):
        """Set value."""
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self._update_display()
            self._update_buttons()
            self.valueChanged.emit(self._value)
    
    def setMinimum(self, minimum: int):
        """Set minimum value."""
        self._minimum = minimum
        self._validator.setBottom(minimum)
        if self._value < minimum:
            self.setValue(minimum)
        self._update_buttons()
    
    def setMaximum(self, maximum: int):
        """Set maximum value."""
        self._maximum = maximum
        self._validator.setTop(maximum)
        if self._value > maximum:
            self.setValue(maximum)
        self._update_buttons()
    
    def setRange(self, minimum: int, maximum: int):
        """Set value range."""
        self._minimum = minimum
        self._maximum = maximum
        self._validator.setRange(minimum, maximum)
        if self._value < minimum:
            self.setValue(minimum)
        elif self._value > maximum:
            self.setValue(maximum)
        self._update_buttons()
    
    def setSuffix(self, suffix: str):
        """Set suffix text."""
        self._suffix = suffix
        self._update_display()
    
    def setSingleStep(self, step: int):
        """Set single step value."""
        self._single_step = step
    
    def setSpecialValueText(self, text: str):
        """Set special text to display for minimum value (e.g., 'Auto', 'Permanent')."""
        self._special_value_text = text
        self._update_display()
    
    def setMinimumWidth(self, width: int):
        """Set minimum width for the entire widget."""
        super().setMinimumWidth(width)
    
    def blockSignals(self, block: bool) -> bool:
        """Block or unblock signals."""
        return super().blockSignals(block)
    
    def setEnabled(self, enabled: bool):
        """Enable/disable the spinbox."""
        super().setEnabled(enabled)
        self.minus_btn.setEnabled(enabled and self._value > self._minimum)
        self.plus_btn.setEnabled(enabled and self._value < self._maximum)
        self.value_input.setEnabled(enabled)
    
    def minimum(self) -> int:
        """Get minimum value."""
        return self._minimum
    
    def maximum(self) -> int:
        """Get maximum value."""
        return self._maximum
    
    def singleStep(self) -> int:
        """Get single step value."""
        return self._single_step


class CustomDoubleSpinBox(QWidget):
    """
    Custom double spinbox with horizontal button layout.
    
    Layout: [−] [Value] [+]
    """
    
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._value = 0.0
        self._minimum = 0.0
        self._maximum = 100.0
        self._single_step = 0.1
        self._decimals = 1
        self._suffix = ""
        self._special_value_text = ""
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)  # Ultra-tight: 1px spacing (matches ROI Detection Settings)
        
        # Minus button
        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedSize(28, 26)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #5A5A5A;
                color: #FFFFFF;
                border: 1px solid #707070;
                border-radius: 0px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #4A9EFF;
                border: 1px solid #6AB0FF;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #3A7FCC;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #555555;
                border: 1px solid #333333;
            }
        """)
        self.minus_btn.clicked.connect(self._decrement)
        layout.addWidget(self.minus_btn)
        
        # Value input (editable)
        self.value_input = QLineEdit("0.0")
        self.value_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_input.setMinimumWidth(80)
        self.value_input.setMaximumWidth(150)
        self.value_input.setFixedHeight(26)
        
        # Set strict double validator
        self._validator = QDoubleValidator()
        self._validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.value_input.setValidator(self._validator)
        
        self.value_input.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 2px 4px;
                font-size: 9pt;
                margin: 0px;
            }
            QLineEdit:focus {
                border: 1px solid #4A9EFF;
                background-color: #353535;
            }
        """)
        self.value_input.editingFinished.connect(self._on_manual_input)
        self.value_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.value_input)
        
        # Plus button
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedSize(28, 26)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #5A5A5A;
                color: #FFFFFF;
                border: 1px solid #707070;
                border-radius: 0px;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #4A9EFF;
                border: 1px solid #6AB0FF;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #3A7FCC;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #555555;
                border: 1px solid #333333;
            }
        """)
        self.plus_btn.clicked.connect(self._increment)
        layout.addWidget(self.plus_btn)
        
        self._update_display()
        self._update_buttons()
    
    def _increment(self):
        """Increment value."""
        if self._value < self._maximum:
            self.setValue(self._value + self._single_step)
    
    def _decrement(self):
        """Decrement value."""
        if self._value > self._minimum:
            self.setValue(self._value - self._single_step)
    
    def _update_display(self):
        """Update the value display."""
        # Check if we should show special value text
        if self._special_value_text and abs(self._value - self._minimum) < 1e-10:
            text = self._special_value_text
        else:
            text = f"{self._value:.{self._decimals}f}"
            if self._suffix:
                text += " " + self._suffix
        self.value_input.setText(text)
    
    def _on_text_changed(self, text):
        """Handle text changes to filter out non-numeric characters."""
        # Remove suffix for validation
        clean_text = text.replace(self._suffix, "").strip()
        
        # If text is empty or just a minus sign or decimal point, allow it (intermediate state)
        if clean_text in ("", "-", ".", "-."):
            return
        
        # Check if the text is a valid float
        try:
            float(clean_text)
        except ValueError:
            # Invalid input - restore to current value
            self._update_display()
    
    def _on_manual_input(self):
        """Handle manual input from user typing."""
        try:
            text = self.value_input.text().replace(self._suffix, "").strip()
            if text:
                new_value = float(text)
                # Clamp to min/max
                new_value = max(self._minimum, min(self._maximum, new_value))
                self.setValue(new_value)
            else:
                # If empty, restore current value
                self._update_display()
        except ValueError:
            # Invalid input, restore current value
            self._update_display()
    
    def _update_buttons(self):
        """Update button enabled states."""
        self.minus_btn.setEnabled(self._value > self._minimum)
        self.plus_btn.setEnabled(self._value < self._maximum)
    
    # Public API (compatible with QDoubleSpinBox)
    
    def value(self) -> float:
        """Get current value."""
        return self._value
    
    def setValue(self, value: float):
        """Set value."""
        value = max(self._minimum, min(self._maximum, value))
        if abs(value - self._value) > 1e-10:  # Float comparison
            self._value = value
            self._update_display()
            self._update_buttons()
            self.valueChanged.emit(self._value)
    
    def setMinimum(self, minimum: float):
        """Set minimum value."""
        self._minimum = minimum
        self._validator.setBottom(minimum)
        if self._value < minimum:
            self.setValue(minimum)
        self._update_buttons()
    
    def setMaximum(self, maximum: float):
        """Set maximum value."""
        self._maximum = maximum
        self._validator.setTop(maximum)
        if self._value > maximum:
            self.setValue(maximum)
        self._update_buttons()
    
    def setRange(self, minimum: float, maximum: float):
        """Set value range."""
        self._minimum = minimum
        self._maximum = maximum
        self._validator.setRange(minimum, maximum)
        if self._value < minimum:
            self.setValue(minimum)
        elif self._value > maximum:
            self.setValue(maximum)
        self._update_buttons()
    
    def setSingleStep(self, step: float):
        """Set single step value."""
        self._single_step = step
    
    def setDecimals(self, decimals: int):
        """Set number of decimal places."""
        self._decimals = decimals
        self._update_display()
    
    def setSuffix(self, suffix: str):
        """Set suffix text."""
        self._suffix = suffix
        self._update_display()
    
    def setSpecialValueText(self, text: str):
        """Set special text to display for minimum value (e.g., 'Auto', 'Permanent')."""
        self._special_value_text = text
        self._update_display()
    
    def setMinimumWidth(self, width: int):
        """Set minimum width for the entire widget."""
        super().setMinimumWidth(width)
    
    def blockSignals(self, block: bool) -> bool:
        """Block or unblock signals."""
        return super().blockSignals(block)
    
    def setEnabled(self, enabled: bool):
        """Enable/disable the spinbox."""
        super().setEnabled(enabled)
        self.minus_btn.setEnabled(enabled and self._value > self._minimum)
        self.plus_btn.setEnabled(enabled and self._value < self._maximum)
        self.value_input.setEnabled(enabled)
    
    def minimum(self) -> float:
        """Get minimum value."""
        return self._minimum
    
    def maximum(self) -> float:
        """Get maximum value."""
        return self._maximum
    
    def singleStep(self) -> float:
        """Get single step value."""
        return self._single_step
