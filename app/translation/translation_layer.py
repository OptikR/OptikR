"""
Translation Layer Implementation

This module provides the main translation layer that coordinates multiple translation
engines, handles caching, language detection, and batch processing.

Now supports plugin-based translation engines!
"""

import time
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    from ..interfaces import ITranslationLayer, TranslationEngine
    from ..models import Translation, TextBlock
    from .translation_engine_interface import (
        AbstractTranslationEngine, TranslationEngineRegistry, TranslationCache,
        LanguageDetector, TranslationOptions, TranslationResult, BatchTranslationResult,
        TranslationQuality, LanguageDetectionResult
    )
    from .translation_plugin_manager import TranslationPluginManager
except ImportError:
    try:
        from interfaces import ITranslationLayer, TranslationEngine
        from models import Translation, TextBlock
        from translation_engine_interface import (
            AbstractTranslationEngine, TranslationEngineRegistry, TranslationCache,
            LanguageDetector, TranslationOptions, TranslationResult, BatchTranslationResult,
            TranslationQuality, LanguageDetectionResult
        )
        from translation_plugin_manager import TranslationPluginManager
    except ImportError:
        from app.interfaces import ITranslationLayer, TranslationEngine
        from app.models import Translation, TextBlock
        from app.translation.translation_engine_interface import (
            AbstractTranslationEngine, TranslationEngineRegistry, TranslationCache,
            LanguageDetector, TranslationOptions, TranslationResult, BatchTranslationResult,
            TranslationQuality, LanguageDetectionResult
        )
        from app.translation.translation_plugin_manager import TranslationPluginManager


class TranslationLayer(ITranslationLayer):
    """
    Main translation layer implementation.
    
    Coordinates multiple translation engines, provides caching, language detection,
    and batch processing capabilities.
    
    Now supports plugin-based translation engines!
    """
    
    def __init__(self, cache_size: int = None, cache_ttl: int = None, 
                 config_manager=None):
        """
        Initialize translation layer.
        
        Args:
            cache_size: Maximum number of cached translations
            cache_ttl: Cache time-to-live in seconds
            config_manager: Optional configuration manager
        """
        self._logger = logging.getLogger(__name__)
        self._engine_registry = TranslationEngineRegistry()
        self._config_manager = config_manager  # Store config manager for reading settings
        
        # Get cache settings from config if not provided
        if cache_size is None and config_manager:
            cache_size = config_manager.get_setting('cache.translation_cache_size', 10000)
        elif cache_size is None:
            cache_size = 10000
            
        if cache_ttl is None and config_manager:
            cache_ttl = config_manager.get_setting('cache.translation_cache_ttl', 3600)
        elif cache_ttl is None:
            cache_ttl = 3600
        
        self._cache = TranslationCache(max_size=cache_size, ttl_seconds=cache_ttl)
        self._language_detector = LanguageDetector()
        self._default_engine = None
        self._fallback_engines = []
        self._lock = threading.RLock()
        
        # Plugin manager for translation engines
        self.plugin_manager = TranslationPluginManager(config_manager=config_manager)
        
        # Discover available translation plugins
        discovered_plugins = self.plugin_manager.discover_plugins()
        self._logger.info(f"Discovered {len(discovered_plugins)} translation plugin(s)")
        if discovered_plugins:
            plugin_names = [p.name for p in discovered_plugins]
            self._logger.info(f"Available plugins: {plugin_names}")
        
        # Performance tracking
        self._performance_stats = {
            'total_translations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_translations': 0,
            'avg_translation_time_ms': 0.0
        }
        
        self._logger.info("Translation layer initialized with plugin support")
    
    def register_engine(self, engine: AbstractTranslationEngine, 
                       is_default: bool = False, is_fallback: bool = True) -> bool:
        """
        Register a translation engine.
        
        Args:
            engine: Translation engine to register
            is_default: Whether this should be the default engine
            is_fallback: Whether this engine can be used as fallback
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            success = self._engine_registry.register_engine(engine)
            if not success:
                return False
            
            with self._lock:
                if is_default or self._default_engine is None:
                    self._default_engine = engine.engine_name
                    self._logger.info(f"Set default translation engine: {engine.engine_name}")
                
                if is_fallback and engine.engine_name not in self._fallback_engines:
                    self._fallback_engines.append(engine.engine_name)
                    self._logger.info(f"Added fallback translation engine: {engine.engine_name}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register translation engine: {e}")
            return False
    
    def load_engine(self, engine_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load a translation engine plugin.
        
        Args:
            engine_name: Name of engine plugin to load
            config: Optional configuration for engine
            
        Returns:
            True if engine loaded successfully
        """
        try:
            # Load plugin via plugin manager
            success = self.plugin_manager.load_plugin(engine_name, config)
            
            if success:
                # Get the loaded engine from plugin manager
                engine = self.plugin_manager.get_engine(engine_name)
                if engine:
                    # Register with engine registry
                    self._engine_registry.register_engine(engine)
                    self._logger.info(f"Loaded and registered engine plugin: {engine_name}")
                    return True
            
            return False
            
        except Exception as e:
            self._logger.error(f"Failed to load engine plugin {engine_name}: {e}")
            return False
    
    def set_default_engine(self, engine_name: str) -> bool:
        """
        Set the default translation engine.
        
        Args:
            engine_name: Name of engine to set as default
            
        Returns:
            True if successful
        """
        with self._lock:
            # Check if engine is loaded
            engine = self._engine_registry.get_engine(engine_name)
            if not engine:
                # Try to get from plugin manager
                engine = self.plugin_manager.get_engine(engine_name)
            
            if engine and engine.is_available():
                self._default_engine = engine_name
                self._logger.info(f"Set default engine: {engine_name}")
                return True
            
            self._logger.error(f"Cannot set default engine: {engine_name} not available")
            return False
    
    def get_available_engines(self) -> List[str]:
        """
        Get list of available translation engine names.
        
        Returns:
            List of engine names
        """
        # Get engines from both registry and plugin manager
        registry_engines = list(self._engine_registry.get_available_engines())
        plugin_engines = self.plugin_manager.get_available_engines()
        
        # Combine and deduplicate
        all_engines = list(set(registry_engines + plugin_engines))
        return all_engines
    
    def translate(self, text: str, engine: TranslationEngine, src_lang: str, 
                 tgt_lang: str, options: Dict[str, Any]) -> str:
        """
        Translate text using specified engine and language pair.
        
        Args:
            text: Text to translate
            engine: Translation engine to use
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        start_time = time.time()
        
        try:
            # Convert options dict to TranslationOptions
            translation_options = self._parse_translation_options(options)
            
            # Auto-detect source language if needed
            if src_lang == 'auto':
                detection_result = self._language_detector.detect_language(text)
                src_lang = detection_result.language_code
                self._logger.debug(f"Auto-detected language: {src_lang} (confidence: {detection_result.confidence})")
            
            # Check cache first if enabled
            if translation_options.use_cache:
                cached_result = self._cache.get(text, src_lang, tgt_lang, engine.value, translation_options)
                if cached_result:
                    self._update_performance_stats(True, time.time() - start_time)
                    return cached_result
            
            # Try dictionary engine first (if available and enabled)
            dict_engine = self._engine_registry.get_engine('dictionary')
            if dict_engine and dict_engine.is_available():
                try:
                    dict_result = dict_engine.translate_text(text, src_lang, tgt_lang, translation_options)
                    # If dictionary found a match (confidence > 0), use it
                    if dict_result.confidence > 0:
                        self._logger.debug(f"Using dictionary translation: {text} -> {dict_result.translated_text}")
                        # Cache result if enabled
                        if translation_options.use_cache:
                            self._cache.put(text, src_lang, tgt_lang, 'dictionary', 
                                          dict_result.translated_text, translation_options)
                        self._update_performance_stats(False, time.time() - start_time)
                        return dict_result.translated_text
                except Exception as e:
                    self._logger.debug(f"Dictionary lookup failed, falling back to {engine.value}: {e}")
            
            # Get translation engine (fallback to specified engine)
            engine_name = engine.value
            translation_engine = self._engine_registry.get_engine(engine_name)
            
            if not translation_engine or not translation_engine.is_available():
                # Try fallback engines
                translation_engine = self._get_fallback_engine(src_lang, tgt_lang)
                if not translation_engine:
                    raise RuntimeError(f"No available translation engine for {src_lang} -> {tgt_lang}")
                engine_name = translation_engine.engine_name
            
            # Perform translation
            result = translation_engine.translate_text(text, src_lang, tgt_lang, translation_options)
            
            # Cache result if enabled
            if translation_options.use_cache and result.translated_text:
                self._cache.put(text, src_lang, tgt_lang, engine_name, 
                              result.translated_text, translation_options)
            
            self._update_performance_stats(False, time.time() - start_time)
            return result.translated_text
            
        except Exception as e:
            self._logger.error(f"Translation failed: {e}")
            self._performance_stats['failed_translations'] += 1
            return text  # Return original text on failure
    
    def translate_batch(self, texts: List[str], engine: TranslationEngine, 
                       src_lang: str, tgt_lang: str) -> List[str]:
        """
        Translate multiple texts in batch for efficiency.
        
        Args:
            texts: List of texts to translate
            engine: Translation engine to use
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        try:
            # Auto-detect source language if needed
            if src_lang == 'auto' and texts:
                detection_result = self._language_detector.detect_language(texts[0])
                src_lang = detection_result.language_code
                self._logger.debug(f"Auto-detected language for batch: {src_lang}")
            
            # Get translation engine
            engine_name = engine.value
            translation_engine = self._engine_registry.get_engine(engine_name)
            
            if not translation_engine or not translation_engine.is_available():
                # Try fallback engines
                translation_engine = self._get_fallback_engine(src_lang, tgt_lang)
                if not translation_engine:
                    raise RuntimeError(f"No available translation engine for {src_lang} -> {tgt_lang}")
            
            # Check cache for each text
            cached_results = {}
            texts_to_translate = []
            indices_to_translate = []
            
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    cached_results[i] = text
                    continue
                
                cached_translation = self._cache.get(text, src_lang, tgt_lang, translation_engine.engine_name)
                if cached_translation:
                    cached_results[i] = cached_translation
                else:
                    texts_to_translate.append(text)
                    indices_to_translate.append(i)
            
            # Translate remaining texts
            translated_results = []
            if texts_to_translate:
                batch_result = translation_engine.translate_batch(texts_to_translate, src_lang, tgt_lang)
                translated_results = batch_result.results
                
                # Cache new translations
                for text, result in zip(texts_to_translate, translated_results):
                    if result.translated_text:
                        self._cache.put(text, src_lang, tgt_lang, translation_engine.engine_name, 
                                      result.translated_text)
            
            # Combine cached and new results
            final_results = [''] * len(texts)
            
            # Fill in cached results
            for i, translation in cached_results.items():
                final_results[i] = translation
            
            # Fill in new translations
            for i, result in enumerate(translated_results):
                original_index = indices_to_translate[i]
                final_results[original_index] = result.translated_text
            
            # Update performance stats
            cache_hits = len(cached_results)
            total_requests = len(texts)
            for _ in range(cache_hits):
                self._update_performance_stats(True, 0)  # Cache hits have minimal time
            for _ in range(total_requests - cache_hits):
                self._update_performance_stats(False, (time.time() - start_time) / (total_requests - cache_hits))
            
            return final_results
            
        except Exception as e:
            self._logger.error(f"Batch translation failed: {e}")
            self._performance_stats['failed_translations'] += len(texts)
            return texts  # Return original texts on failure
    
    def get_supported_languages(self, engine: TranslationEngine) -> List[str]:
        """
        Get supported languages for specified engine.
        
        Args:
            engine: Translation engine
            
        Returns:
            List of supported language codes
        """
        try:
            translation_engine = self._engine_registry.get_engine(engine.value)
            if translation_engine:
                return translation_engine.get_supported_languages()
            return []
            
        except Exception as e:
            self._logger.error(f"Failed to get supported languages: {e}")
            return []
    
    def cache_translation(self, source: str, target: str, translation: str) -> None:
        """
        Cache translation result for future use.
        
        Args:
            source: Source text
            target: Target language
            translation: Translation result
        """
        try:
            # This is a simplified cache entry - in practice we'd need more context
            # For now, we'll use the default engine and assume English source
            engine_name = self._default_engine or 'unknown'
            self._cache.put(source, 'en', target, engine_name, translation)
            
        except Exception as e:
            self._logger.error(f"Failed to cache translation: {e}")
    
    def clear_cache(self) -> None:
        """Clear translation cache."""
        try:
            self._cache.clear()
            self._logger.info("Translation cache cleared")
            
        except Exception as e:
            self._logger.error(f"Failed to clear cache: {e}")
    
    def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect language of input text.
        
        Args:
            text: Text to analyze
            
        Returns:
            LanguageDetectionResult with detected language and confidence
        """
        return self._language_detector.detect_language(text)
    
    def get_available_engines(self) -> List[str]:
        """Get list of available translation engines."""
        return self._engine_registry.get_available_engines()
    
    def get_engines_for_language_pair(self, src_lang: str, tgt_lang: str) -> List[str]:
        """Get engines that support specific language pair."""
        return self._engine_registry.get_engines_for_language_pair(src_lang, tgt_lang)
    
    def set_default_engine(self, engine_name: str) -> bool:
        """
        Set default translation engine.
        
        Args:
            engine_name: Name of engine to set as default
            
        Returns:
            True if successful, False otherwise
        """
        try:
            engine = self._engine_registry.get_engine(engine_name)
            if engine and engine.is_available():
                with self._lock:
                    self._default_engine = engine_name
                self._logger.info(f"Set default translation engine: {engine_name}")
                return True
            return False
            
        except Exception as e:
            self._logger.error(f"Failed to set default engine: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get translation layer performance statistics."""
        cache_stats = self._cache.get_stats()
        
        return {
            'translation_stats': self._performance_stats.copy(),
            'cache_stats': cache_stats,
            'available_engines': self.get_available_engines(),
            'default_engine': self._default_engine,
            'fallback_engines': self._fallback_engines.copy()
        }
    
    def _parse_translation_options(self, options: Dict[str, Any]) -> TranslationOptions:
        """Parse options dictionary into TranslationOptions object, reading from config if needed."""
        # Read from config if available and not explicitly provided in options
        if self._config_manager:
            # Preserve formatting
            preserve_formatting = options.get('preserve_formatting')
            if preserve_formatting is None:
                preserve_formatting = self._config_manager.get_setting('translation.preserve_formatting', True)
            
            # Use cache
            use_cache = options.get('use_cache')
            if use_cache is None:
                use_cache = self._config_manager.get_setting('translation.cache_enabled', True)
            
            # Quality level
            quality = options.get('quality')
            if quality is None:
                quality_level = self._config_manager.get_setting('translation.quality_level', 50)
                if quality_level >= 75:
                    quality = 'high'
                elif quality_level >= 25:
                    quality = 'medium'
                else:
                    quality = 'low'
        else:
            # Fallback to defaults if no config
            preserve_formatting = options.get('preserve_formatting', True)
            use_cache = options.get('use_cache', True)
            quality = options.get('quality', 'medium')
        
        return TranslationOptions(
            quality=TranslationQuality(quality),
            preserve_formatting=preserve_formatting,
            use_cache=use_cache,
            timeout_seconds=options.get('timeout_seconds', 5.0),
            context=options.get('context'),
            domain=options.get('domain')
        )
    
    def _get_fallback_engine(self, src_lang: str, tgt_lang: str) -> Optional[AbstractTranslationEngine]:
        """Get fallback engine that supports the language pair."""
        # Check if fallback is enabled in config
        if self._config_manager:
            fallback_enabled = self._config_manager.get_setting('translation.fallback_enabled', True)
            if not fallback_enabled:
                self._logger.debug("Fallback engines disabled in config")
                return None
        
        for engine_name in self._fallback_engines:
            engine = self._engine_registry.get_engine(engine_name)
            if engine and engine.is_available() and engine.supports_language_pair(src_lang, tgt_lang):
                self._logger.info(f"Using fallback engine: {engine_name}")
                return engine
        return None
    
    def _update_performance_stats(self, cache_hit: bool, duration: float) -> None:
        """Update performance statistics."""
        with self._lock:
            self._performance_stats['total_translations'] += 1
            
            if cache_hit:
                self._performance_stats['cache_hits'] += 1
            else:
                self._performance_stats['cache_misses'] += 1
            
            # Update average translation time (exponential moving average)
            duration_ms = duration * 1000
            current_avg = self._performance_stats['avg_translation_time_ms']
            alpha = 0.1  # Smoothing factor
            self._performance_stats['avg_translation_time_ms'] = (
                alpha * duration_ms + (1 - alpha) * current_avg
            )
    
    def preload_models(self, src_lang: str, tgt_lang: str) -> bool:
        """
        Pre-load translation models in the main thread to avoid threading issues.
        MUST be called from the main thread before starting background pipeline.
        
        This is especially important for MarianMT which uses transformers library
        that can crash when loading models in background threads.
        
        Args:
            src_lang: Source language
            tgt_lang: Target language
        
        Returns:
            bool: True if models loaded successfully, False otherwise
        """
        try:
            self._logger.info(f"Pre-loading translation models for {src_lang}->{tgt_lang}...")
            print(f"[TranslationLayer] Pre-loading models for {src_lang}->{tgt_lang}...")
            
            # Get the default engine using the registry
            if not self._default_engine:
                self._logger.warning("No default engine set for pre-loading")
                print(f"[TranslationLayer] No default engine set")
                return False
            
            engine = self._engine_registry.get_engine(self._default_engine)
            if not engine:
                self._logger.warning(f"Default engine '{self._default_engine}' not found in registry")
                print(f"[TranslationLayer] Engine '{self._default_engine}' not found")
                return False
            
            # Check if engine has preload method (MarianMT does)
            if hasattr(engine, 'preload_model'):
                success = engine.preload_model(src_lang, tgt_lang)
                if success:
                    self._logger.info(f"✓ Models pre-loaded successfully")
                    print(f"[TranslationLayer] ✓ Models pre-loaded successfully")
                else:
                    self._logger.warning(f"Failed to pre-load models")
                    print(f"[TranslationLayer] ✗ Failed to pre-load models")
                return success
            else:
                # Engine doesn't support pre-loading, that's okay
                self._logger.info(f"Engine {engine.engine_name} doesn't require pre-loading")
                print(f"[TranslationLayer] Engine {engine.engine_name} doesn't require pre-loading")
                return True
                
        except Exception as e:
            self._logger.error(f"Error pre-loading models: {e}")
            print(f"[TranslationLayer] Error pre-loading models: {e}")
            import traceback
            traceback.print_exc()
            return False
    def export_dictionary_wordbook(self, output_path: str, source_lang: str = None, target_lang: str = None) -> str:
        """
        Export dictionary as a human-readable wordbook.
        
        Args:
            output_path: Path to save the wordbook file
            source_lang: Source language code (uses current if None)
            target_lang: Target language code (uses current if None)
            
        Returns:
            Path to the exported file, or None if failed
        """
        try:
            from pathlib import Path
            
            # Use current languages if not specified
            if source_lang is None:
                source_lang = getattr(self, '_current_source_lang', 'en')
            if target_lang is None:
                target_lang = getattr(self, '_current_target_lang', 'de')
            
            # Get dictionary engine
            dict_engine = self._engine_registry.get_engine('dictionary')
            if not dict_engine:
                self._logger.warning("Dictionary engine not available for export")
                return None
            
            # Get dictionary data
            lang_pair = (source_lang, target_lang)
            if not hasattr(dict_engine._dictionary, '_dictionaries'):
                self._logger.warning("No dictionaries loaded")
                return None
            
            if lang_pair not in dict_engine._dictionary._dictionaries:
                self._logger.warning(f"No dictionary for {source_lang} → {target_lang}")
                return None
            
            dictionary = dict_engine._dictionary._dictionaries[lang_pair]
            
            # Create output file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write wordbook
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Dictionary Wordbook: {source_lang} → {target_lang}\n")
                f.write(f"# Total entries: {len(dictionary)}\n")
                f.write(f"# Exported: {__import__('datetime').datetime.now().isoformat()}\n")
                f.write("\n" + "="*80 + "\n\n")
                
                # Sort entries by usage count (most used first)
                sorted_entries = []
                for key, entry_data in dictionary.items():
                    # Extract source text from key
                    if ':' in key:
                        parts = key.split(':', 2)
                        source_text = parts[2] if len(parts) > 2 else key
                    else:
                        source_text = key
                    
                    if isinstance(entry_data, dict):
                        translation = entry_data.get('translation', source_text)
                        usage_count = entry_data.get('usage_count', 0)
                        confidence = entry_data.get('confidence', 0.0)
                    else:
                        translation = str(entry_data)
                        usage_count = 0
                        confidence = 0.0
                    
                    sorted_entries.append((source_text, translation, usage_count, confidence))
                
                # Sort by usage count descending
                sorted_entries.sort(key=lambda x: x[2], reverse=True)
                
                # Write entries
                for source_text, translation, usage_count, confidence in sorted_entries:
                    f.write(f"{source_text}\n")
                    f.write(f"  → {translation}\n")
                    f.write(f"  Usage: {usage_count} | Confidence: {confidence:.2f}\n")
                    f.write("\n")
            
            self._logger.info(f"Exported dictionary wordbook to {output_file}")
            return str(output_file)
            
        except Exception as e:
            self._logger.error(f"Failed to export dictionary wordbook: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_available_language_pairs(self):
        """
        Get list of all available language-pair dictionaries from SmartDictionary.
        
        Returns:
            List of tuples: (source_lang, target_lang, file_path, entry_count)
        """
        try:
            # Get dictionary engine (SmartDictionary)
            dict_engine = self._engine_registry.get_engine('dictionary')
            
            if dict_engine and hasattr(dict_engine, '_dictionary'):
                # Get loaded language pairs from SmartDictionary
                pairs = dict_engine._dictionary.get_available_language_pairs()
                
                # Deduplicate by language pair (keep the one with most entries)
                unique_pairs = {}
                for source, target, path, count in pairs:
                    key = (source, target)
                    if key not in unique_pairs or count > unique_pairs[key][3]:
                        unique_pairs[key] = (source, target, path, count)
                
                return list(unique_pairs.values())
            else:
                self._logger.warning("SmartDictionary not available")
                return []
            
        except Exception as e:
            self._logger.error(f"Failed to get available language pairs: {e}")
            return []
    
    def get_current_language_pair(self):
        """
        Get the current language pair from config.
        
        Returns:
            Tuple of (source_lang, target_lang)
        """
        try:
            if self._config_manager:
                source = self._config_manager.get_setting('translation.source_language', 'en')
                target = self._config_manager.get_setting('translation.target_language', 'de')
            else:
                source = getattr(self, '_current_source_lang', 'en')
                target = getattr(self, '_current_target_lang', 'de')
            
            return (source, target)
            
        except Exception as e:
            self._logger.error(f"Failed to get current language pair: {e}")
            return ('en', 'de')
    
    def set_language_pair(self, source_lang: str, target_lang: str):
        """
        Set the current language pair.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
        """
        try:
            if self._config_manager:
                self._config_manager.set_setting('translation.source_language', source_lang)
                self._config_manager.set_setting('translation.target_language', target_lang)
            
            self._current_source_lang = source_lang
            self._current_target_lang = target_lang
            
            self._logger.info(f"Language pair set to {source_lang} → {target_lang}")
            
        except Exception as e:
            self._logger.error(f"Failed to set language pair: {e}")
    
    def get_dictionary_stats(self):
        """
        Get statistics for the current dictionary.
        
        Returns:
            Dictionary with stats: total_entries, total_usage, etc.
        """
        try:
            dict_engine = self._engine_registry.get_engine('dictionary')
            if not dict_engine or not hasattr(dict_engine, '_dictionary'):
                return {'total_entries': 0, 'total_usage': 0}
            
            source, target = self.get_current_language_pair()
            lang_pair = (source, target)
            
            if hasattr(dict_engine._dictionary, '_dictionaries'):
                if lang_pair in dict_engine._dictionary._dictionaries:
                    dictionary = dict_engine._dictionary._dictionaries[lang_pair]
                    total_entries = len(dictionary)
                    total_usage = sum(
                        entry.get('usage_count', 0) if isinstance(entry, dict) else 0
                        for entry in dictionary.values()
                    )
                    return {
                        'total_entries': total_entries,
                        'total_usage': total_usage
                    }
            
            return {'total_entries': 0, 'total_usage': 0}
            
        except Exception as e:
            self._logger.error(f"Failed to get dictionary stats: {e}")
            return {'total_entries': 0, 'total_usage': 0}
    
    def clear_dictionary(self):
        """Clear the current dictionary."""
        try:
            dict_engine = self._engine_registry.get_engine('dictionary')
            if not dict_engine or not hasattr(dict_engine, '_dictionary'):
                self._logger.warning("Dictionary engine not available")
                return
            
            source, target = self.get_current_language_pair()
            lang_pair = (source, target)
            
            if hasattr(dict_engine._dictionary, '_dictionaries'):
                if lang_pair in dict_engine._dictionary._dictionaries:
                    dict_engine._dictionary._dictionaries[lang_pair] = {}
                    
                    # Save the empty dictionary
                    from pathlib import Path
                    dict_paths = [
                        Path(f"dev/dictionary/learned_dictionary_{source}_{target}.json.gz"),
                        Path(f"dictionary/learned_dictionary_{source}_{target}.json.gz")
                    ]
                    
                    for dict_path in dict_paths:
                        if dict_path.parent.exists():
                            dict_engine._dictionary._save_dictionary(lang_pair, dict_path)
                            break
                    
                    self._logger.info(f"Cleared dictionary for {source} → {target}")
            
        except Exception as e:
            self._logger.error(f"Failed to clear dictionary: {e}")
    
    def reload_dictionary_from_file(self, file_path: str, source_lang: str = None, target_lang: str = None):
        """
        Reload dictionary from a specific file.
        Useful when there are multiple dictionary files for the same language pair.
        
        Args:
            file_path: Path to the dictionary file to load
            source_lang: Source language code (uses current if None)
            target_lang: Target language code (uses current if None)
        """
        try:
            # Use current languages if not specified
            if source_lang is None or target_lang is None:
                source_lang, target_lang = self.get_current_language_pair()
            
            dict_engine = self._engine_registry.get_engine('dictionary')
            if not dict_engine or not hasattr(dict_engine, '_dictionary'):
                self._logger.warning("Dictionary engine not available")
                return
            
            # Reload the specific file
            dict_engine._dictionary.reload_specific_dictionary(file_path, source_lang, target_lang)
            self._logger.info(f"Reloaded dictionary from {file_path}")
            
        except Exception as e:
            self._logger.error(f"Failed to reload dictionary from file: {e}")
    
    def get_loaded_dictionary_path(self, source_lang: str = None, target_lang: str = None) -> str:
        """
        Get the file path of the currently loaded dictionary.
        
        Args:
            source_lang: Source language code (uses current if None)
            target_lang: Target language code (uses current if None)
            
        Returns:
            File path string if loaded, None otherwise
        """
        try:
            # Use current languages if not specified
            if source_lang is None or target_lang is None:
                source_lang, target_lang = self.get_current_language_pair()
            
            dict_engine = self._engine_registry.get_engine('dictionary')
            if not dict_engine or not hasattr(dict_engine, '_dictionary'):
                return None
            
            return dict_engine._dictionary.get_loaded_dictionary_path(source_lang, target_lang)
            
        except Exception as e:
            self._logger.error(f"Failed to get loaded dictionary path: {e}")
            return None
    
    def cleanup(self) -> None:
        """Clean up translation layer resources."""
        try:
            self._engine_registry.cleanup_all()
            self._cache.clear()
            self._logger.info("Translation layer cleaned up")
            
        except Exception as e:
            self._logger.error(f"Error during cleanup: {e}")


def create_translation_layer(config: Optional[Dict[str, Any]] = None) -> TranslationLayer:
    """
    Factory function to create and configure translation layer.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured TranslationLayer instance
    """
    if config is None:
        config = {}
    
    cache_size = config.get('cache_size', 10000)
    cache_ttl = config.get('cache_ttl', 3600)
    
    translation_layer = TranslationLayer(cache_size=cache_size, cache_ttl=cache_ttl)
    
    # Additional configuration can be applied here
    
    return translation_layer