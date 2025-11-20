"""
Translation API Manager
Handles API key management and testing for cloud translation services.
"""

from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt6.QtCore import Qt
import time


class TranslationAPIManager:
    """Manages API keys and testing for cloud translation services."""
    
    def __init__(self, parent=None):
        """Initialize the API manager."""
        self.parent = parent
    
    def test_api_key(self, service: str, api_key: str) -> bool:
        """
        Test API key for the specified service with format validation.
        
        Args:
            service: Service name ('google', 'deepl', 'azure')
            api_key: The API key to test
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Service configuration
        service_config = {
            'google': {'name': 'Google Translate', 'min_length': 20},
            'deepl': {'name': 'DeepL', 'min_length': 20},
            'azure': {'name': 'Azure Translator', 'min_length': 32}
        }
        
        if service not in service_config:
            return False
        
        config = service_config[service]
        service_name = config['name']
        min_length = config['min_length']
        
        if not api_key:
            QMessageBox.warning(
                self.parent,
                "No API Key",
                f"Please enter a {service_name} API key first."
            )
            return False
        
        # Validate API key format
        if len(api_key) < min_length:
            QMessageBox.warning(
                self.parent,
                "Invalid API Key Format",
                f"{service_name} API key appears to be invalid.\n\n"
                f"Expected minimum length: {min_length} characters\n"
                f"Current length: {len(api_key)} characters\n\n"
                f"Please check your API key."
            )
            return False
        
        # Show progress dialog
        progress = QProgressDialog(
            f"Testing {service_name} API key...",
            None,
            0,
            0,
            self.parent
        )
        progress.setWindowTitle("Testing API Key")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        # Simulate API test (in real implementation, this would make an actual API call)
        time.sleep(1)
        
        progress.close()
        
        # Show result
        QMessageBox.information(
            self.parent,
            "API Key Format Valid",
            f"✅ {service_name} API key format is valid!\n\n"
            f"Key length: {len(api_key)} characters\n"
            f"Format: OK\n\n"
            f"Note: This is a format validation only.\n"
            f"Actual API connectivity will be tested when you use the service."
        )
        return True
