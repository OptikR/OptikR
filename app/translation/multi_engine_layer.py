"""
Multi-Engine Translation Layer

Automatically selects the best translation engine for each language pair.
Works seamlessly with translation chain optimizer for optimal quality.
"""

import logging
from typing import Dict, Any, List, Optional

try:
    from .translation_layer import TranslationLayer
    from .translation_engine_interface import AbstractTranslationEngine, TranslationOptions
    from ..interfaces import TranslationEngine
except ImportError:
    try:
        from translation_layer import TranslationLayer
        from translation_engine_interface import AbstractTranslationEngine, TranslationOptions
        from interfaces import TranslationEngine
    except ImportError:
        from app.translation.translation_layer import TranslationLayer
        from app.translation.translation_engine_interface import AbstractTranslationEngine, TranslationOptions
        from app.interfaces import TranslationEngine


class MultiEngineTranslationLayer(TranslationLayer):
    """
    Multi-engine translation layer with automatic engine selection.
    
    Features:
    - Automatic engine selection per language pair
    - Configurable engine mapping
    - Fallback to default engine if specific engine unavailable
    - Full compatibility with translation chain optimizer
    - Inherits all caching and batch processing from TranslationLayer
    """
    
    def __init__(self, config_manager=None, cache_size: int = None, cache_ttl: int = None):
        """
        Initialize multi-engine translation layer.
        
        Args:
            config_manager: Configuration manager for loading settings
            cache_size: Maximum number of cached translations
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__(cache_size=cache_size, cache_ttl=cache_ttl)
        
        self.config_manager = config_manager
        self._engine_mapping: Dict[str, str] = {}
        self._default_engine_name: str = 'marianmt'
        
        # Load engine mapping from config
        self._load_engine_mapping()
        
        self._logger.info("Multi-engine translation layer initialized")
        print("[MULTI_ENGINE] Translation layer initialized with engine mapping")
    
    def _load_engine_mapping(self):
        """Load engine mapping from configuration."""
        if self.config_manager:
            try:
                # Load engine mapping from config
                self._engine_mapping = self.config_manager.get_setting(
                    'translation.engine_mapping',
                    {}
                )
                
                # Load default engine
                self._default_engine_name = self.config_manager.get_setting(
                    'translation.default_engine',
                    'marianmt'
                )
                
                if self._engine_mapping:
                    self._logger.info(f"Loaded engine mapping: {len(self._engine_mapping)} pairs")
                    print(f"[MULTI_ENGINE] Loaded {len(self._engine_mapping)} engine mappings")
                    for pair, engine in self._engine_mapping.items():
                        print(f"[MULTI_ENGINE]   {pair} → {engine}")
                else:
                    self._logger.info("No engine mapping configured, using default engine for all pairs")
                    print("[MULTI_ENGINE] No engine mapping configured, using default engine")
                
            except Exception as e:
                self._logger.warning(f"Failed to load engine mapping: {e}")
                print(f"[MULTI_ENGINE] WARNING: Failed to load engine mapping: {e}")
                self._engine_mapping = {}
        else:
            # Default mapping if no config manager
            self._engine_mapping = {
                'ja->en': 'marianmt',
                'en->de': 'marianmt',
                'zh->en': 'marianmt',
                'ko->en': 'marianmt',
                'default': 'marianmt'
            }
            self._logger.info("Using default engine mapping")
            print("[MULTI_ENGINE] Using default engine mapping")
    
    def _select_engine_for_pair(self, src_lang: str, tgt_lang: str) -> str:
        """
        Select best engine for language pair.
        
        Args:
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            Engine name to use
        """
        # Create language pair key
        pair_key = f"{src_lang}->{tgt_lang}"
        
        # Check if specific mapping exists
        if pair_key in self._engine_mapping:
            engine_name = self._engine_mapping[pair_key]
            self._logger.debug(f"Selected engine for {pair_key}: {engine_name}")
            return engine_name
        
        # Check for default mapping
        if 'default' in self._engine_mapping:
            engine_name = self._engine_mapping['default']
            self._logger.debug(f"Using default engine for {pair_key}: {engine_name}")
            return engine_name
        
        # Fallback to default engine name
        self._logger.debug(f"Using fallback engine for {pair_key}: {self._default_engine_name}")
        return self._default_engine_name
    
    def translate(self, text: str, engine: TranslationEngine, src_lang: str, 
                 tgt_lang: str, options: Dict[str, Any]) -> str:
        """
        Translate text using automatically selected engine for language pair.
        
        Args:
            text: Text to translate
            engine: Translation engine (may be overridden by mapping)
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            Translated text
        """
        # Select best engine for this language pair
        selected_engine_name = self._select_engine_for_pair(src_lang, tgt_lang)
        
        # Try to get the selected engine
        selected_engine = self._engine_registry.get_engine(selected_engine_name)
        
        if selected_engine and selected_engine.is_available():
            # Use selected engine
            try:
                # Convert engine name to TranslationEngine enum
                engine_enum = TranslationEngine(selected_engine_name)
            except ValueError:
                # If engine name not in enum, use provided engine
                engine_enum = engine
            
            return super().translate(text, engine_enum, src_lang, tgt_lang, options)
        else:
            # Fallback to provided engine
            self._logger.warning(f"Selected engine {selected_engine_name} not available, using fallback")
            return super().translate(text, engine, src_lang, tgt_lang, options)
    
    def translate_batch(self, texts: List[str], engine: TranslationEngine, 
                       src_lang: str, tgt_lang: str) -> List[str]:
        """
        Translate multiple texts using automatically selected engine.
        
        Args:
            texts: List of texts to translate
            engine: Translation engine (may be overridden by mapping)
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            List of translated texts
        """
        # Select best engine for this language pair
        selected_engine_name = self._select_engine_for_pair(src_lang, tgt_lang)
        
        # Try to get the selected engine
        selected_engine = self._engine_registry.get_engine(selected_engine_name)
        
        if selected_engine and selected_engine.is_available():
            # Use selected engine
            try:
                # Convert engine name to TranslationEngine enum
                engine_enum = TranslationEngine(selected_engine_name)
            except ValueError:
                # If engine name not in enum, use provided engine
                engine_enum = engine
            
            return super().translate_batch(texts, engine_enum, src_lang, tgt_lang)
        else:
            # Fallback to provided engine
            self._logger.warning(f"Selected engine {selected_engine_name} not available, using fallback")
            return super().translate_batch(texts, engine, src_lang, tgt_lang)
    
    def set_engine_mapping(self, mapping: Dict[str, str]) -> None:
        """
        Set engine mapping for language pairs.
        
        Args:
            mapping: Dictionary mapping language pairs to engine names
                    Format: {'ja->en': 'marianmt', 'en->de': 'google', 'default': 'marianmt'}
        """
        self._engine_mapping = mapping.copy()
        self._logger.info(f"Updated engine mapping: {len(mapping)} pairs")
        print(f"[MULTI_ENGINE] Updated engine mapping: {len(mapping)} pairs")
        
        # Save to config if available
        if self.config_manager:
            try:
                self.config_manager.set_setting('translation.engine_mapping', mapping)
                self._logger.info("Saved engine mapping to config")
            except Exception as e:
                self._logger.warning(f"Failed to save engine mapping: {e}")
    
    def get_engine_mapping(self) -> Dict[str, str]:
        """Get current engine mapping."""
        return self._engine_mapping.copy()
    
    def add_engine_mapping(self, src_lang: str, tgt_lang: str, engine_name: str) -> None:
        """
        Add or update engine mapping for specific language pair.
        
        Args:
            src_lang: Source language code
            tgt_lang: Target language code
            engine_name: Engine name to use for this pair
        """
        pair_key = f"{src_lang}->{tgt_lang}"
        self._engine_mapping[pair_key] = engine_name
        self._logger.info(f"Added engine mapping: {pair_key} → {engine_name}")
        print(f"[MULTI_ENGINE] Added mapping: {pair_key} → {engine_name}")
        
        # Save to config if available
        if self.config_manager:
            try:
                self.config_manager.set_setting('translation.engine_mapping', self._engine_mapping)
            except Exception as e:
                self._logger.warning(f"Failed to save engine mapping: {e}")
    
    def remove_engine_mapping(self, src_lang: str, tgt_lang: str) -> bool:
        """
        Remove engine mapping for specific language pair.
        
        Args:
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            True if mapping was removed, False if not found
        """
        pair_key = f"{src_lang}->{tgt_lang}"
        if pair_key in self._engine_mapping:
            del self._engine_mapping[pair_key]
            self._logger.info(f"Removed engine mapping: {pair_key}")
            print(f"[MULTI_ENGINE] Removed mapping: {pair_key}")
            
            # Save to config if available
            if self.config_manager:
                try:
                    self.config_manager.set_setting('translation.engine_mapping', self._engine_mapping)
                except Exception as e:
                    self._logger.warning(f"Failed to save engine mapping: {e}")
            
            return True
        return False
    
    def get_engine_for_pair(self, src_lang: str, tgt_lang: str) -> str:
        """
        Get engine name that will be used for specific language pair.
        
        Args:
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            Engine name
        """
        return self._select_engine_for_pair(src_lang, tgt_lang)


def create_multi_engine_translation_layer(config_manager=None, 
                                         config: Optional[Dict[str, Any]] = None) -> MultiEngineTranslationLayer:
    """
    Factory function to create and configure multi-engine translation layer.
    
    Args:
        config_manager: Configuration manager
        config: Optional configuration dictionary
        
    Returns:
        Configured MultiEngineTranslationLayer instance
    """
    if config is None:
        config = {}
    
    cache_size = config.get('cache_size', 10000)
    cache_ttl = config.get('cache_ttl', 3600)
    
    translation_layer = MultiEngineTranslationLayer(
        config_manager=config_manager,
        cache_size=cache_size,
        cache_ttl=cache_ttl
    )
    
    # Apply engine mapping if provided in config
    if 'engine_mapping' in config:
        translation_layer.set_engine_mapping(config['engine_mapping'])
    
    return translation_layer
