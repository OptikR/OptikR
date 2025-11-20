"""
Translation Engine Registry Initialization

This module initializes and registers all available translation engines
with the translation layer.

Now uses plugin-based system for extensibility!
"""

import logging
from typing import Optional

# Import path utilities for EXE compatibility
from app.utils.path_utils import ensure_app_directory

logger = logging.getLogger(__name__)


def initialize_translation_engines(translation_layer, config_manager=None):
    """
    Initialize and register all available translation engines.
    
    Now uses plugin-based system for better extensibility!
    
    Args:
        translation_layer: TranslationLayer instance to register engines with
        config_manager: Optional configuration manager for engine settings
        
    Returns:
        dict: Status of each engine initialization {engine_name: success}
    """
    results = {}
    
    # Get configuration
    if config_manager:
        primary_engine = config_manager.get_setting('translation.primary_engine', 'marianmt')
        fallback_enabled = config_manager.get_setting('translation.fallback_enabled', True)
    else:
        primary_engine = 'marianmt'
        fallback_enabled = True
    
    logger.info("Initializing translation engines via plugin system...")
    
    # Discover all available translation plugins
    logger.info("Discovering translation plugins...")
    discovered = translation_layer.plugin_manager.discover_plugins()
    logger.info(f"Discovered {len(discovered)} translation plugins")
    
    # 1. Load Primary Engine (Plugin-Based)
    logger.info(f"Loading primary engine: {primary_engine}")
    try:
        # Prepare config for engine
        engine_config = {
            'source_language': config_manager.get_setting('translation.source_language', 'en') if config_manager else 'en',
            'target_language': config_manager.get_setting('translation.target_language', 'de') if config_manager else 'de'
        }
        
        # Load via plugin system
        success = translation_layer.load_engine(primary_engine, engine_config)
        
        if success:
            # Set as default
            translation_layer.set_default_engine(primary_engine)
            results[primary_engine] = True
            logger.info(f"✓ {primary_engine} engine loaded and set as default")
        else:
            results[primary_engine] = False
            logger.warning(f"✗ Failed to load {primary_engine} engine")
    except Exception as e:
        results[primary_engine] = False
        logger.error(f"✗ Failed to initialize {primary_engine}: {e}")
    
    # 2. Load Fallback Engines (if enabled)
    if fallback_enabled:
        logger.info("Loading fallback engines...")
        
        # Try to load other discovered plugins as fallbacks
        for plugin in discovered:
            if plugin.name != primary_engine:
                try:
                    logger.info(f"Loading fallback engine: {plugin.name}")
                    success = translation_layer.load_engine(plugin.name, engine_config)
                    results[plugin.name] = success
                    if success:
                        logger.info(f"✓ {plugin.name} loaded as fallback")
                    else:
                        logger.warning(f"✗ Failed to load {plugin.name}")
                except Exception as e:
                    results[plugin.name] = False
                    logger.error(f"✗ Failed to load {plugin.name}: {e}")
    
    # 3. Initialize Legacy Engines (Backward Compatibility)
    # These are engines that haven't been converted to plugins yet
    logger.info("Checking for legacy engines...")
    
    # Google Translate Free (Legacy)
    try:
        from .engines.google_free_engine import GoogleFreeTranslationEngine
        
        google_free = GoogleFreeTranslationEngine()
        if google_free.is_available():
            is_default = (primary_engine == 'google_free' and primary_engine not in results)
            translation_layer.register_engine(
                google_free,
                is_default=is_default,
                is_fallback=fallback_enabled
            )
            results['google_free'] = True
            logger.info("✓ Google Translate Free engine registered (legacy)")
        else:
            results['google_free'] = False
            logger.warning("✗ Google Translate Free not available")
    except Exception as e:
        results['google_free'] = False
        logger.error(f"✗ Failed to initialize Google Translate Free: {e}")
    
    # LibreTranslate (Legacy)
    try:
        from .engines.libretranslate_engine import LibreTranslateEngine
        
        api_url = "https://libretranslate.com"
        api_key = None
        if config_manager:
            api_url = config_manager.get_setting('translation.libretranslate_url', api_url)
            api_key = config_manager.get_setting('translation.libretranslate_api_key')
        
        libretranslate = LibreTranslateEngine(api_url=api_url, api_key=api_key)
        if libretranslate.is_available():
            is_default = (primary_engine == 'libretranslate' and primary_engine not in results)
            translation_layer.register_engine(
                libretranslate,
                is_default=is_default,
                is_fallback=fallback_enabled
            )
            results['libretranslate'] = True
            logger.info("✓ LibreTranslate engine registered (legacy)")
        else:
            results['libretranslate'] = False
            logger.warning("✗ LibreTranslate not available")
    except Exception as e:
        results['libretranslate'] = False
        logger.error(f"✗ Failed to initialize LibreTranslate: {e}")
    
    # 4. Initialize Google Translate API (if API key provided)
    if config_manager:
        google_api_key = config_manager.get_setting('translation.google_api_key')
        if google_api_key:
            try:
                from .engines.google_api_engine import GoogleAPITranslationEngine
                
                google_api = GoogleAPITranslationEngine(api_key=google_api_key)
                if google_api.initialize({'api_key': google_api_key}):
                    is_default = (primary_engine == 'google' and primary_engine not in results)
                    translation_layer.register_engine(
                        google_api,
                        is_default=is_default,
                        is_fallback=fallback_enabled
                    )
                    results['google'] = True
                    logger.info("✓ Google Translate API engine registered")
                else:
                    results['google'] = False
                    logger.warning("✗ Google Translate API initialization failed")
            except Exception as e:
                results['google'] = False
                logger.error(f"✗ Failed to initialize Google Translate API: {e}")
    
    # 5. Initialize DeepL (if API key provided)
    if config_manager:
        deepl_api_key = config_manager.get_setting('translation.deepl_api_key')
        if deepl_api_key:
            try:
                from .engines.deepl_engine import DeepLTranslationEngine
                
                deepl = DeepLTranslationEngine(api_key=deepl_api_key)
                if deepl.initialize({'api_key': deepl_api_key}):
                    is_default = (primary_engine == 'deepl' and primary_engine not in results)
                    translation_layer.register_engine(
                        deepl,
                        is_default=is_default,
                        is_fallback=fallback_enabled
                    )
                    results['deepl'] = True
                    logger.info("✓ DeepL engine registered")
                else:
                    results['deepl'] = False
                    logger.warning("✗ DeepL initialization failed")
            except Exception as e:
                results['deepl'] = False
                logger.error(f"✗ Failed to initialize DeepL: {e}")
    
    # 6. Initialize Azure Translator (if API key provided)
    if config_manager:
        azure_api_key = config_manager.get_setting('translation.azure_api_key')
        if azure_api_key:
            try:
                from .engines.azure_engine import AzureTranslatorEngine
                
                azure_region = config_manager.get_setting('translation.azure_region', 'global')
                azure = AzureTranslatorEngine(api_key=azure_api_key, region=azure_region)
                if azure.initialize({'api_key': azure_api_key, 'region': azure_region}):
                    is_default = (primary_engine == 'azure' and primary_engine not in results)
                    translation_layer.register_engine(
                        azure,
                        is_default=is_default,
                        is_fallback=fallback_enabled
                    )
                    results['azure'] = True
                    logger.info("✓ Azure Translator engine registered")
                else:
                    results['azure'] = False
                    logger.warning("✗ Azure Translator initialization failed")
            except Exception as e:
                results['azure'] = False
                logger.error(f"✗ Failed to initialize Azure Translator: {e}")
    
    # Note: Dictionary is now integrated directly into PipelineCacheManager
    # No separate engine needed - it's handled by the cache layer
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    logger.info(f"Translation engines initialized: {successful}/{total} successful")
    
    # Log available engines
    available_engines = translation_layer.get_available_engines()
    if available_engines:
        logger.info(f"Available translation engines: {', '.join(available_engines)}")
    else:
        logger.warning("No translation engines available!")
    
    return results
