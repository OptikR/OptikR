"""
Language Code Mapper Utility

Converts between different OCR engine language code formats:
- ISO 639-1 (2-letter codes): en, de, es, fr, ja, etc.
- Tesseract (3-letter codes): eng, deu, spa, fra, jpn, etc.
- EasyOCR (ISO 639-1 + special codes): en, de, ch_sim, ch_tra, etc.

Author: Niklas Verhasselt
Date: November 2025
"""

from typing import Dict, Optional
import logging


class LanguageCodeMapper:
    """
    Maps between different OCR engine language code formats.
    
    Supports conversion between:
    - ISO 639-1 (2-letter): Used by EasyOCR, PaddleOCR, ONNX, Translation engines
    - Tesseract (3-letter): Used by Tesseract OCR
    """
    
    # ISO 639-1 (2-letter) to Tesseract (3-letter) mapping
    ISO_TO_TESSERACT: Dict[str, str] = {
        'en': 'eng',      # English
        'de': 'deu',      # German
        'es': 'spa',      # Spanish
        'fr': 'fra',      # French
        'ja': 'jpn',      # Japanese
        'zh': 'chi_sim',  # Chinese (Simplified)
        'ko': 'kor',      # Korean
        'ru': 'rus',      # Russian
        'it': 'ita',      # Italian
        'pt': 'por',      # Portuguese
        'nl': 'nld',      # Dutch
        'pl': 'pol',      # Polish
        'tr': 'tur',      # Turkish
        'ar': 'ara',      # Arabic
        'hi': 'hin',      # Hindi
        'th': 'tha',      # Thai
        'vi': 'vie',      # Vietnamese
        'id': 'ind',      # Indonesian
        'uk': 'ukr',      # Ukrainian
        'cs': 'ces',      # Czech
        'sv': 'swe',      # Swedish
        'da': 'dan',      # Danish
        'fi': 'fin',      # Finnish
        'no': 'nor',      # Norwegian
        'hu': 'hun',      # Hungarian
        'ro': 'ron',      # Romanian
        'bg': 'bul',      # Bulgarian
        'el': 'ell',      # Greek
        'he': 'heb',      # Hebrew
        'fa': 'fas',      # Persian
    }
    
    # Tesseract to ISO 639-1 (reverse mapping)
    TESSERACT_TO_ISO: Dict[str, str] = {v: k for k, v in ISO_TO_TESSERACT.items()}
    
    # Alternative Tesseract codes (some languages have multiple codes)
    TESSERACT_ALTERNATIVES: Dict[str, str] = {
        'ger': 'deu',      # German alternative
        'fre': 'fra',      # French alternative
        'dut': 'nld',      # Dutch alternative
        'chi_tra': 'chi_tra',  # Chinese Traditional (keep as-is)
        'chi_sim': 'chi_sim',  # Chinese Simplified (keep as-is)
    }
    
    # EasyOCR special codes (codes that don't follow ISO 639-1)
    EASYOCR_SPECIAL: Dict[str, str] = {
        'ch_sim': 'chi_sim',   # Chinese Simplified
        'ch_tra': 'chi_tra',   # Chinese Traditional
        'rs_cyrillic': 'rs_cyrillic',  # Serbian Cyrillic
    }
    
    # Language name to ISO code mapping (for UI)
    NAME_TO_ISO: Dict[str, str] = {
        'English': 'en',
        'German': 'de',
        'Spanish': 'es',
        'French': 'fr',
        'Japanese': 'ja',
        'Chinese': 'zh',
        'Chinese (Simplified)': 'zh',
        'Chinese (Traditional)': 'zh',
        'Korean': 'ko',
        'Russian': 'ru',
        'Italian': 'it',
        'Portuguese': 'pt',
        'Dutch': 'nl',
        'Polish': 'pl',
        'Turkish': 'tr',
        'Arabic': 'ar',
        'Hindi': 'hi',
        'Thai': 'th',
        'Vietnamese': 'vi',
        'Indonesian': 'id',
        'Ukrainian': 'uk',
        'Czech': 'cs',
        'Swedish': 'sv',
        'Danish': 'da',
        'Finnish': 'fi',
        'Norwegian': 'no',
        'Hungarian': 'hu',
        'Romanian': 'ro',
        'Bulgarian': 'bg',
        'Greek': 'el',
        'Hebrew': 'he',
        'Persian': 'fa',
    }
    
    # ISO code to language name (reverse mapping)
    ISO_TO_NAME: Dict[str, str] = {v: k for k, v in NAME_TO_ISO.items() if k in [
        'English', 'German', 'Spanish', 'French', 'Japanese', 'Chinese',
        'Korean', 'Russian', 'Italian', 'Portuguese', 'Dutch', 'Polish',
        'Turkish', 'Arabic', 'Hindi', 'Thai', 'Vietnamese', 'Indonesian',
        'Ukrainian', 'Czech', 'Swedish', 'Danish', 'Finnish', 'Norwegian',
        'Hungarian', 'Romanian', 'Bulgarian', 'Greek', 'Hebrew', 'Persian'
    ]}
    
    @classmethod
    def to_easyocr(cls, code: str) -> str:
        """
        Convert any language code to EasyOCR format (ISO 639-1).
        
        Args:
            code: Language code in any format
            
        Returns:
            Language code in EasyOCR format
        """
        if not code:
            return 'en'
        
        code = code.lower().strip()
        
        # Already in ISO format (2 letters)
        if len(code) == 2 and code in cls.ISO_TO_TESSERACT:
            return code
        
        # Check if it's a special EasyOCR code
        if code in cls.EASYOCR_SPECIAL:
            return code
        
        # Convert from Tesseract format
        if code in cls.TESSERACT_TO_ISO:
            return cls.TESSERACT_TO_ISO[code]
        
        # Check Tesseract alternatives
        if code in cls.TESSERACT_ALTERNATIVES:
            tesseract_code = cls.TESSERACT_ALTERNATIVES[code]
            if tesseract_code in cls.TESSERACT_TO_ISO:
                return cls.TESSERACT_TO_ISO[tesseract_code]
        
        # Try to extract first 2 letters if it's a longer code
        if len(code) > 2:
            potential_iso = code[:2]
            if potential_iso in cls.ISO_TO_TESSERACT:
                return potential_iso
        
        # Default to English
        logging.warning(f"Unknown language code '{code}', defaulting to 'en'")
        return 'en'
    
    @classmethod
    def to_tesseract(cls, code: str) -> str:
        """
        Convert any language code to Tesseract format.
        
        Args:
            code: Language code in any format
            
        Returns:
            Language code in Tesseract format
        """
        if not code:
            return 'eng'
        
        code = code.lower().strip()
        
        # Already in Tesseract format (3+ letters)
        if code in cls.TESSERACT_TO_ISO or code in cls.TESSERACT_ALTERNATIVES:
            return code
        
        # Convert from ISO format
        if code in cls.ISO_TO_TESSERACT:
            return cls.ISO_TO_TESSERACT[code]
        
        # Handle special cases
        if code == 'zh' or code == 'chi_sim' or code == 'ch_sim':
            return 'chi_sim'
        if code == 'chi_tra' or code == 'ch_tra':
            return 'chi_tra'
        
        # Default to English
        logging.warning(f"Unknown language code '{code}', defaulting to 'eng'")
        return 'eng'
    
    @classmethod
    def normalize(cls, code: str, target_engine: str) -> str:
        """
        Normalize language code for a specific OCR engine.
        
        Args:
            code: Language code in any format
            target_engine: Target OCR engine name ('easyocr', 'tesseract', 'paddleocr', 'onnx', 'manga_ocr')
            
        Returns:
            Normalized language code for the target engine
            
        Engine-specific formats:
            - EasyOCR: ISO 639-1 (en, de, ja, etc.)
            - Tesseract: 3-letter codes (eng, deu, jpn, etc.)
            - PaddleOCR: ISO 639-1 (en, de, ja, etc.)
            - ONNX: ISO 639-1 (en, de, ja, etc.)
            - Manga OCR: Always 'ja' (Japanese only)
        """
        if not code or not target_engine:
            return 'en'
        
        engine = target_engine.lower().strip()
        
        # Manga OCR only supports Japanese
        if engine == 'manga_ocr':
            # Convert any Japanese code to 'ja'
            if code.lower() in ['ja', 'jpn', 'japanese']:
                return 'ja'
            # Default to Japanese for Manga OCR
            logging.warning(f"Manga OCR only supports Japanese, converting '{code}' to 'ja'")
            return 'ja'
        
        # Tesseract uses 3-letter codes (eng, deu, jpn, etc.)
        elif engine == 'tesseract':
            return cls.to_tesseract(code)
        
        # EasyOCR, PaddleOCR, and ONNX all use ISO 639-1 format (en, de, ja, etc.)
        elif engine in ['easyocr', 'paddleocr', 'onnx']:
            return cls.to_easyocr(code)
        
        # Unknown engine, default to ISO format
        else:
            logging.warning(f"Unknown OCR engine '{target_engine}', using ISO format")
            return cls.to_easyocr(code)
    
    @classmethod
    def from_name(cls, name: str) -> str:
        """
        Convert language name to ISO 639-1 code.
        
        Args:
            name: Language name (e.g., 'English', 'German')
            
        Returns:
            ISO 639-1 language code
        """
        if not name:
            return 'en'
        
        name = name.strip()
        return cls.NAME_TO_ISO.get(name, 'en')
    
    @classmethod
    def to_name(cls, code: str) -> str:
        """
        Convert language code to language name.
        
        Args:
            code: Language code in any format
            
        Returns:
            Language name
        """
        if not code:
            return 'English'
        
        # First normalize to ISO format
        iso_code = cls.to_easyocr(code)
        
        # Get name from mapping
        return cls.ISO_TO_NAME.get(iso_code, 'English')
    
    @classmethod
    def is_valid_code(cls, code: str, engine: Optional[str] = None) -> bool:
        """
        Check if a language code is valid.
        
        Args:
            code: Language code to validate
            engine: Optional engine name to validate against
            
        Returns:
            True if code is valid, False otherwise
        """
        if not code:
            return False
        
        code = code.lower().strip()
        
        # Check ISO format
        if code in cls.ISO_TO_TESSERACT:
            return True
        
        # Check Tesseract format
        if code in cls.TESSERACT_TO_ISO or code in cls.TESSERACT_ALTERNATIVES:
            return True
        
        # Check special codes
        if code in cls.EASYOCR_SPECIAL:
            return True
        
        return False
    
    @classmethod
    def get_supported_languages(cls, engine: str) -> list:
        """
        Get list of supported language codes for an engine.
        
        Args:
            engine: OCR engine name
            
        Returns:
            List of supported language codes
        """
        engine = engine.lower().strip()
        
        if engine in ['easyocr', 'paddleocr', 'onnx']:
            # Return ISO codes
            return list(cls.ISO_TO_TESSERACT.keys())
        elif engine == 'tesseract':
            # Return Tesseract codes
            return list(cls.TESSERACT_TO_ISO.keys())
        else:
            # Default to ISO codes
            return list(cls.ISO_TO_TESSERACT.keys())


# Convenience functions for quick access
def normalize_language_code(code: str, engine: str) -> str:
    """Convenience function to normalize language code."""
    return LanguageCodeMapper.normalize(code, engine)


def language_name_to_code(name: str) -> str:
    """Convenience function to convert language name to code."""
    return LanguageCodeMapper.from_name(name)


def language_code_to_name(code: str) -> str:
    """Convenience function to convert language code to name."""
    return LanguageCodeMapper.to_name(code)
