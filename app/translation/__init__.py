"""
Translation module for OptikR text translation.

This module provides translation engine interfaces, caching, language detection,
and batch processing capabilities for OptikR.

Author: Niklas Verhasselt
Date: November 2025
"""

# Import with fallbacks for optional components
try:
    from .translation_engine_interface import (
        AbstractTranslationEngine,
        TranslationEngineRegistry,
        TranslationCache,
        LanguageDetector,
        TranslationOptions,
        TranslationResult,
        BatchTranslationResult,
        TranslationQuality,
        LanguageDetectionResult,
        LanguageDetectionConfidence
    )
except ImportError as e:
    print(f"Warning: Could not import translation_engine_interface: {e}")
    AbstractTranslationEngine = None
    TranslationEngineRegistry = None

try:
    from .translation_layer import (
        TranslationLayer,
        create_translation_layer
    )
except ImportError as e:
    print(f"Warning: Could not import translation_layer: {e}")
    TranslationLayer = None

try:
    from .smart_dictionary import (
        SmartDictionary,
        DictionaryEntry,
        DictionaryStats,
        DictionaryLookupCache,
        create_smart_dictionary
    )
except ImportError:
    # Dictionary module not implemented yet - silently use None
    SmartDictionary = None
    DictionaryEntry = None
    DictionaryStats = None
    DictionaryLookupCache = None
    create_smart_dictionary = None

try:
    from .dictionary_translation_engine import (
        DictionaryTranslationEngine,
        DictionaryTranslationOptions,
        create_dictionary_translation_engine
    )
except ImportError:
    # Dictionary engine not implemented yet - silently use None
    DictionaryTranslationEngine = None
    DictionaryTranslationOptions = None
    create_dictionary_translation_engine = None

# Cloud translation engines removed - not implemented yet
# from .cloud_translation_engines import ...
# from .cloud_fallback_system import ...
# from .cloud_translation_manager import ...

__all__ = [
    # Engine interfaces and base classes
    'AbstractTranslationEngine',
    'TranslationEngineRegistry',
    
    # Caching and language detection
    'TranslationCache',
    'LanguageDetector',
    
    # Data classes and enums
    'TranslationOptions',
    'TranslationResult',
    'BatchTranslationResult',
    'TranslationQuality',
    'LanguageDetectionResult',
    'LanguageDetectionConfidence',
    
    # Main translation layer
    'TranslationLayer',
    'create_translation_layer',
    
    # Smart dictionary system
    'SmartDictionary',
    'DictionaryEntry',
    'DictionaryStats',
    'DictionaryLookupCache',
    'create_smart_dictionary',
    
    # Dictionary translation engine
    'DictionaryTranslationEngine',
    'DictionaryTranslationOptions',
    'create_dictionary_translation_engine',
    
    # Cloud translation engines - not implemented yet
    # 'GoogleTranslateEngine',
    # 'AzureTranslatorEngine',
    # etc.
]