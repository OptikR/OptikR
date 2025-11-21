"""
Simple encryption utility for API keys and sensitive data.
Uses Fernet symmetric encryption from cryptography library.
"""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet


class EncryptionManager:
    """Manages encryption and decryption of sensitive data like API keys."""
    
    def __init__(self, key_file: str = None):
        """
        Initialize encryption manager.
        
        Args:
            key_file: Path to encryption key file. If None, uses default location.
        """
        if key_file is None:
            # Use default key file location
            config_dir = Path.home() / '.cache' / 'live_translator'
            config_dir.mkdir(parents=True, exist_ok=True)
            key_file = config_dir / 'encryption.key'
        
        self.key_file = Path(key_file)
        self.cipher = None
        self._load_or_create_key()
    
    def _load_or_create_key(self):
        """Load existing encryption key or create a new one."""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Save key to file
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions (owner read/write only)
            try:
                os.chmod(self.key_file, 0o600)
            except:
                pass  # Windows doesn't support chmod
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        try:
            # Convert to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Encrypt
            encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
            
            # Return as base64 string
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"[ERROR] Encryption failed: {e}")
            return plaintext  # Return plaintext if encryption fails
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return ""
        
        try:
            # Convert to bytes
            encrypted_bytes = encrypted.encode('utf-8')
            
            # Decrypt
            plaintext_bytes = self.cipher.decrypt(encrypted_bytes)
            
            # Return as string
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            # If decryption fails, assume it's already plaintext
            # This handles migration from unencrypted to encrypted storage
            print(f"[WARNING] Decryption failed, assuming plaintext: {e}")
            return encrypted
    
    def is_encrypted(self, text: str) -> bool:
        """
        Check if a string appears to be encrypted.
        
        Args:
            text: String to check
            
        Returns:
            True if string appears to be encrypted
        """
        if not text:
            return False
        
        try:
            # Fernet tokens start with 'gAAAAA'
            return text.startswith('gAAAAA')
        except:
            return False


# Global encryption manager instance
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key.
    
    Args:
        api_key: API key to encrypt
        
    Returns:
        Encrypted API key
    """
    manager = get_encryption_manager()
    return manager.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key.
    
    Args:
        encrypted_key: Encrypted API key
        
    Returns:
        Decrypted API key
    """
    manager = get_encryption_manager()
    return manager.decrypt(encrypted_key)
