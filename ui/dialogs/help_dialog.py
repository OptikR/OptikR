"""
Help Dialog Module

Comprehensive help dialog with multiple tabs covering all aspects
of the Real-Time Translation System.

Author: Real-Time Translation System
Date: 2024
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QPushButton
)


class HelpDialog(QDialog):
    """
    Help dialog with tabbed interface.
    
    Tabs:
    - Getting Started: Quick start guide
    - Settings Guide: Detailed settings documentation
    - Troubleshooting: Common issues and solutions
    - Shortcuts: Keyboard shortcuts
    - About: Version and credits
    """
    
    def __init__(self, config_manager=None, parent=None):
        """
        Initialize help dialog.
        
        Args:
            config_manager: Configuration manager for version info (optional)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Real-Time Translation System - Help")
        self.setMinimumSize(700, 600)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the help dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different help sections
        tab_widget = QTabWidget()
        
        # Add all tabs
        tab_widget.addTab(self._create_getting_started_tab(), "Getting Started")
        tab_widget.addTab(self._create_settings_guide_tab(), "Settings Guide")
        tab_widget.addTab(self._create_troubleshooting_tab(), "Troubleshooting")
        tab_widget.addTab(self._create_shortcuts_tab(), "Shortcuts")
        tab_widget.addTab(self._create_about_tab(), "About")
        
        layout.addWidget(tab_widget)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def _create_getting_started_tab(self):
        """Create Getting Started tab."""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h2>Getting Started</h2>
        <p>Welcome to the Real-Time Translation System! This guide will help you get started.</p>
        
        <h3>Quick Start</h3>
        <ol>
            <li><b>Configure Languages:</b> Go to the <b>General</b> tab and select your source and target languages.</li>
            <li><b>Select Capture Region:</b> Click the <b>🖥 Select Capture Region</b> button to choose what area of your screen to translate.</li>
            <li><b>Configure OCR:</b> Go to the <b>OCR Engines</b> tab and select your preferred OCR engine (EasyOCR recommended).</li>
            <li><b>Start Translation:</b> Click the <b>▶ Start</b> button to begin real-time translation.</li>
        </ol>
        
        <h3>System Requirements</h3>
        <ul>
            <li>Windows 10/11 (64-bit)</li>
            <li>Python 3.8 or higher</li>
            <li>4GB RAM minimum (8GB recommended)</li>
            <li>GPU recommended for better performance</li>
        </ul>
        
        <h3>First Time Setup</h3>
        <p>On first launch, the system will:</p>
        <ul>
            <li>Create default configuration files</li>
            <li>Initialize OCR engines (may take a few minutes)</li>
            <li>Download required language models</li>
        </ul>
        """)
        return text_edit
    
    def _create_settings_guide_tab(self):
        """Create Settings Guide tab."""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h2>Settings Guide</h2>
        
        <h3>General Tab</h3>
        <p>Configure basic system settings:</p>
        <ul>
            <li><b>Runtime Mode:</b> Choose between Auto, GPU, or CPU mode</li>
            <li><b>Languages:</b> Select source (OCR) and target (translation) languages</li>
            <li><b>Startup Options:</b> Configure auto-start and tray behavior</li>
        </ul>
        
        <h3>Capture Tab</h3>
        <p>Configure screen capture settings:</p>
        <ul>
            <li><b>Capture Mode:</b> DirectX (fastest), GDI, or Auto</li>
            <li><b>FPS:</b> Higher = more responsive, but uses more CPU</li>
            <li><b>Quality:</b> Higher = better OCR accuracy, but slower</li>
        </ul>
        
        <h3>OCR Engines Tab</h3>
        <p>Configure text recognition:</p>
        <ul>
            <li><b>EasyOCR:</b> Best accuracy, GPU-accelerated (recommended)</li>
            <li><b>Tesseract:</b> Fast, CPU-based, good for simple text</li>
            <li><b>PaddleOCR:</b> Good for Asian languages</li>
            <li><b>Confidence Threshold:</b> Higher = fewer false positives</li>
        </ul>
        
        <h3>Translation Tab</h3>
        <p>Configure translation engines:</p>
        <ul>
            <li><b>MarianMT:</b> Offline, fast, good quality (default)</li>
            <li><b>Google Translate:</b> Requires API key, excellent quality</li>
            <li><b>DeepL:</b> Requires API key, best quality</li>
            <li><b>Cache:</b> Stores translations to avoid re-translating</li>
        </ul>
        
        <h3>Overlay Tab</h3>
        <p>Configure how translations are displayed:</p>
        <ul>
            <li><b>Font:</b> Choose font family and size</li>
            <li><b>Colors:</b> Text and background colors</li>
            <li><b>Transparency:</b> Overlay opacity</li>
            <li><b>Animation:</b> Fade effects for smooth appearance</li>
        </ul>
        
        <h3>Pipeline Tab (Dashboard)</h3>
        <p>View current configuration and navigate to settings:</p>
        <ul>
            <li><b>Read-Only:</b> Displays current settings status</li>
            <li><b>Configure Buttons:</b> Navigate to appropriate settings tabs</li>
            <li><b>Test Configuration:</b> Verify your settings are correct</li>
        </ul>
        
        <h3>Storage Tab</h3>
        <p>Configure data storage:</p>
        <ul>
            <li><b>Cache:</b> Temporary data storage</li>
            <li><b>Models:</b> OCR and translation model files</li>
            <li><b>Retention:</b> How long to keep old data</li>
        </ul>
        
        <h3>Advanced Tab</h3>
        <p>Configure advanced performance settings:</p>
        <ul>
            <li><b>Multithreading:</b> Use multiple CPU cores</li>
            <li><b>Worker Threads:</b> Number of parallel workers</li>
            <li><b>Frame Skip:</b> Skip similar frames to save CPU</li>
            <li><b>Experimental Features:</b> Enable beta features</li>
        </ul>
        """)
        return text_edit
    
    def _create_troubleshooting_tab(self):
        """Create Troubleshooting tab."""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h2>Troubleshooting</h2>
        
        <h3>Common Issues</h3>
        
        <h4>❌ OCR Not Working</h4>
        <ul>
            <li>Check that OCR engines are installed</li>
            <li>Try lowering the confidence threshold</li>
            <li>Ensure capture region contains text</li>
            <li>Try a different OCR engine</li>
        </ul>
        
        <h4>❌ Translation Not Appearing</h4>
        <ul>
            <li>Check that translation is enabled in Pipeline tab</li>
            <li>Verify overlay is enabled</li>
            <li>Check overlay transparency (not too transparent)</li>
            <li>Ensure capture region is selected</li>
        </ul>
        
        <h4>❌ Poor Performance / Low FPS</h4>
        <ul>
            <li>Lower capture FPS in Capture tab</li>
            <li>Enable frame skipping in Advanced tab</li>
            <li>Reduce capture quality</li>
            <li>Enable GPU acceleration if available</li>
            <li>Close other resource-intensive applications</li>
        </ul>
        
        <h4>❌ Inaccurate Translations</h4>
        <ul>
            <li>Increase OCR confidence threshold</li>
            <li>Use higher capture quality</li>
            <li>Try a different OCR engine</li>
            <li>Ensure correct source language is selected</li>
        </ul>
        
        <h4>❌ System Crashes or Freezes</h4>
        <ul>
            <li>Check system requirements</li>
            <li>Reduce worker threads in Advanced tab</li>
            <li>Disable experimental features</li>
            <li>Check logs in Storage tab location</li>
        </ul>
        
        <h3>Performance Tips</h3>
        <ul>
            <li><b>Use GPU Mode:</b> Much faster than CPU for OCR and translation</li>
            <li><b>Enable Caching:</b> Avoids re-translating same text</li>
            <li><b>Optimize FPS:</b> 15-20 FPS is usually sufficient</li>
            <li><b>Use Frame Skip:</b> Reduces processing of duplicate frames</li>
            <li><b>Select Smaller Region:</b> Less area = faster processing</li>
        </ul>
        
        <h3>Getting Help</h3>
        <p>If you continue to experience issues:</p>
        <ul>
            <li>Check the log files in the logs directory</li>
            <li>Export your configuration for debugging</li>
            <li>Review the Pipeline Dashboard for warnings</li>
            <li>Test your configuration using the Test button</li>
        </ul>
        """)
        return text_edit
    
    def _create_shortcuts_tab(self):
        """Create Keyboard Shortcuts tab."""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h2>Keyboard Shortcuts</h2>
        
        <h3>Main Window</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #E3F2FD;">
                <th>Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><b>Ctrl + S</b></td>
                <td>Save all settings</td>
            </tr>
            <tr>
                <td><b>Ctrl + E</b></td>
                <td>Export configuration</td>
            </tr>
            <tr>
                <td><b>Ctrl + I</b></td>
                <td>Import configuration</td>
            </tr>
            <tr>
                <td><b>F1</b></td>
                <td>Show this help dialog</td>
            </tr>
            <tr>
                <td><b>F5</b></td>
                <td>Refresh Pipeline Dashboard</td>
            </tr>
            <tr>
                <td><b>Ctrl + Q</b></td>
                <td>Quit application</td>
            </tr>
        </table>
        
        <h3>Translation Control</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #E3F2FD;">
                <th>Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><b>Ctrl + T</b></td>
                <td>Start/Stop translation</td>
            </tr>
            <tr>
                <td><b>Ctrl + R</b></td>
                <td>Select capture region</td>
            </tr>
            <tr>
                <td><b>Ctrl + M</b></td>
                <td>Open performance monitor</td>
            </tr>
        </table>
        
        <p><i>Note: Some shortcuts may not be implemented yet.</i></p>
        """)
        return text_edit
    
    def _create_about_tab(self):
        """Create About tab."""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # Get version from config
        version = '0.1.0 (Early Release)'
        if self.config_manager:
            version = self.config_manager.get_setting('ui.version', '0.1.0')
        
        text_edit.setHtml(f"""
        <h2>About</h2>
        
        <h3>Real-Time Translation System</h3>
        <p><b>Version:</b> {version}</p>
        <p><b>Build:</b> PyQt6 Implementation</p>
        
        <h3>Features</h3>
        <ul>
            <li>Real-time screen capture and translation</li>
            <li>Multiple OCR engines (EasyOCR, Tesseract, PaddleOCR)</li>
            <li>Multiple translation engines (MarianMT, Google, DeepL, Azure)</li>
            <li>GPU acceleration support</li>
            <li>Customizable overlay display</li>
            <li>Translation caching for performance</li>
            <li>Intelligent dictionary support</li>
            <li>Performance monitoring and optimization</li>
        </ul>
        
        <h3>Technology Stack</h3>
        <ul>
            <li><b>UI Framework:</b> PyQt6</li>
            <li><b>OCR:</b> EasyOCR, Tesseract, PaddleOCR</li>
            <li><b>Translation:</b> MarianMT, Transformers</li>
            <li><b>Screen Capture:</b> DirectX, GDI</li>
            <li><b>GPU:</b> CUDA, DirectML</li>
        </ul>
        
        <h3>License</h3>
        <p>This software is provided as-is for personal and educational use.</p>
        
        <h3>Credits</h3>
        <p>Built with open-source technologies and community contributions.</p>

        <h3>Special Thanks</h3>
        <p>Tony without you this wouldnt be possible!</p>
        <p>Deniz Uluer Thank you for listining to my rubmbles while Testing and Debbuging</p>
        <p>Laura Thank you for the Motivation to make this you dont have any excuse anymore :D</p>

        <p style="margin-top: 30px; text-align: center; color: #666;">
            <i>Thank you for using Real-Time Translation System!</i>
        </p>
        """)
        return text_edit


def show_help_dialog(config_manager=None, parent=None):
    """
    Show help dialog.
    
    Args:
        config_manager: Configuration manager for version info (optional)
        parent: Parent widget (optional)
    """
    dialog = HelpDialog(config_manager, parent)
    dialog.exec()
