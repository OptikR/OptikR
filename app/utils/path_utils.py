"""
Path utilities for handling both Python script and EXE execution.

This module provides utilities to get the correct application root directory
whether running as a Python script or as a compiled EXE.
"""

import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Get the application root directory.
    
    Works correctly for both:
    - Python script execution: Returns the directory containing run.py
    - EXE execution: Returns the directory containing the .exe file
    
    Returns:
        Path: Absolute path to application root directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE (PyInstaller, cx_Freeze, etc.)
        # sys.executable points to the .exe file
        app_root = Path(sys.executable).parent
    else:
        # Running as Python script
        # Go up from src/utils/ to project root (where run.py is)
        app_root = Path(__file__).parent.parent.parent
    
    return app_root.resolve()


def get_app_path(*parts: str) -> Path:
    """
    Get a path relative to the application root.
    
    Args:
        *parts: Path components to join (e.g., 'dictionary', 'learned_dictionary.json')
    
    Returns:
        Path: Absolute path relative to application root
    
    Examples:
        get_app_path('dictionary')  # -> /path/to/app/dictionary
        get_app_path('config', 'settings.json')  # -> /path/to/app/config/settings.json
    """
    return get_app_root().joinpath(*parts)


def ensure_app_directory(*parts: str) -> Path:
    """
    Ensure a directory exists relative to the application root.
    
    Args:
        *parts: Path components to join
    
    Returns:
        Path: Absolute path to the created directory
    """
    directory = get_app_path(*parts)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# ============================================================================
# NEW STRUCTURE HELPERS (Phase 2)
# Support both old and new folder structures during migration
# ============================================================================

def get_user_data_path(*parts: str) -> Path:
    """
    Get path in user_data/ folder.
    
    This is for user-generated content:
    - Configuration files
    - Learned translations
    - Exports
    - Custom plugins
    - Backups
    
    Args:
        *parts: Path components (e.g., 'config', 'user_config.json')
    
    Returns:
        Path: Absolute path in user_data/
    
    Examples:
        get_user_data_path('config')  # -> /app/user_data/config
        get_user_data_path('learned', 'translations')  # -> /app/user_data/learned/translations
        get_user_data_path('config', 'user_config.json')  # -> /app/user_data/config/user_config.json
    """
    return get_app_path('user_data', *parts)


def get_system_data_path(*parts: str) -> Path:
    """
    Get path in system_data/ folder.
    
    This is for system-managed content:
    - AI models
    - Cache files
    - Log files
    - Temporary files
    
    Args:
        *parts: Path components (e.g., 'cache', 'translation_cache.json')
    
    Returns:
        Path: Absolute path in system_data/
    
    Examples:
        get_system_data_path('cache')  # -> /app/system_data/cache
        get_system_data_path('ai_models', 'ocr')  # -> /app/system_data/ai_models/ocr
        get_system_data_path('logs', 'app.log')  # -> /app/system_data/logs/app.log
    """
    return get_app_path('system_data', *parts)


# ============================================================================
# SPECIFIC PATH HELPERS
# Convenient shortcuts for common paths
# ============================================================================

def get_config_path(filename: str = 'user_config.json') -> Path:
    """
    Get config file path.
    
    Always uses new location (user_data/config/).
    For migration: if old config exists and new doesn't, it will be copied on first load.
    
    Args:
        filename: Config filename (default: 'user_config.json')
    
    Returns:
        Path: Path to config file in user_data/config/
    
    Examples:
        get_config_path()  # -> user_data/config/user_config.json
        get_config_path('custom.json')  # -> user_data/config/custom.json
    """
    # Always use new location
    new_path = get_user_data_path('config', filename)
    
    # Migration: if old config exists and new doesn't, copy it
    if not new_path.exists():
        old_path = get_app_path('config', filename)
        if old_path.exists():
            import shutil
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_path, new_path)
            print(f"[INFO] Migrated config from {old_path} to {new_path}")
    
    return new_path


def get_learned_translations_path(source_lang: str, target_lang: str) -> Path:
    """
    Get learned translations file path.
    
    Supports migration: checks new location first, falls back to old.
    
    Args:
        source_lang: Source language code (e.g., 'en')
        target_lang: Target language code (e.g., 'de')
    
    Returns:
        Path: Path to learned dictionary file
    
    Examples:
        get_learned_translations_path('en', 'de')  # -> user_data/learned/translations/en_de.json.gz
        get_learned_translations_path('ja', 'en')  # -> user_data/learned/translations/ja_en.json.gz
    """
    # New format: en_de.json.gz
    new_filename = f'{source_lang}_{target_lang}.json.gz'
    new_path = get_user_data_path('learned', 'translations', new_filename)
    if new_path.exists():
        return new_path
    
    # Old format: learned_dictionary_en_de.json.gz
    old_filename = f'learned_dictionary_{source_lang}_{target_lang}.json.gz'
    old_path = get_app_path('dictionary', old_filename)
    return old_path


def get_ai_model_path(model_type: str, *parts: str) -> Path:
    """
    Get AI model path.
    
    Supports migration: checks new location first, falls back to old.
    
    Args:
        model_type: Type of model ('ocr' or 'translation')
        *parts: Additional path components
    
    Returns:
        Path: Path to model directory
    
    Examples:
        get_ai_model_path('ocr', 'easyocr')  # -> system_data/ai_models/ocr/easyocr
        get_ai_model_path('translation', 'marianmt')  # -> system_data/ai_models/translation/marianmt
    """
    # Check new location first
    new_path = get_system_data_path('ai_models', model_type, *parts)
    if new_path.exists():
        return new_path
    
    # Fall back to old location during migration
    if model_type == 'ocr':
        old_path = get_app_path('models', 'ocr', *parts)
    elif model_type == 'translation':
        # Old location had various names (marianmt, language, etc.)
        old_path = get_app_path('models', *parts)
    else:
        old_path = get_app_path('models', model_type, *parts)
    
    return old_path


def get_cache_path(cache_type: str) -> Path:
    """
    Get cache file or directory path.
    
    Supports migration: checks new location first, falls back to old.
    
    Args:
        cache_type: Type of cache ('translation', 'ocr', 'image')
    
    Returns:
        Path: Path to cache file or directory
    
    Examples:
        get_cache_path('translation')  # -> system_data/cache/translation_cache.json
        get_cache_path('ocr')  # -> system_data/cache/ocr_cache.json
        get_cache_path('image')  # -> system_data/cache/image_cache/
    """
    # Check new location first
    if cache_type == 'image':
        new_path = get_system_data_path('cache', 'image_cache')
    else:
        new_path = get_system_data_path('cache', f'{cache_type}_cache.json')
    
    if new_path.exists():
        return new_path
    
    # Fall back to old location during migration
    if cache_type == 'translation':
        # Old name: smart_translation_cache.json
        old_path = get_app_path('cache', 'smart_translation_cache.json')
    elif cache_type == 'image':
        old_path = get_app_path('cache', 'image_cache')
    else:
        old_path = get_app_path('cache', f'{cache_type}_cache.json')
    
    return old_path


def get_log_path(log_type: str = 'app') -> Path:
    """
    Get log file or directory path.
    
    Supports migration: checks new location first, falls back to old.
    
    Args:
        log_type: Type of log ('app', 'performance', 'errors', or 'directory')
    
    Returns:
        Path: Path to log file or directory
    
    Examples:
        get_log_path('directory')  # -> system_data/logs/
        get_log_path('app')  # -> system_data/logs/app_YYYYMMDD.log
    """
    if log_type == 'directory':
        # Check new location first
        new_path = get_system_data_path('logs')
        if new_path.exists():
            return new_path
        # Fall back to old location
        return get_app_path('logs')
    else:
        # Return directory, let logger create the file
        return get_log_path('directory')


def get_export_path(export_type: str) -> Path:
    """
    Get export folder path.
    
    Args:
        export_type: Type of export ('translations', 'screenshots', 'logs')
    
    Returns:
        Path: Path to export directory
    
    Examples:
        get_export_path('translations')  # -> user_data/exports/translations/
        get_export_path('screenshots')  # -> user_data/exports/screenshots/
    """
    return get_user_data_path('exports', export_type)


def get_backup_path() -> Path:
    """
    Get backups folder path.
    
    Returns:
        Path: Path to backups directory
    
    Examples:
        get_backup_path()  # -> user_data/backups/
    """
    return get_user_data_path('backups')


def get_temp_path(temp_type: str = 'processing') -> Path:
    """
    Get temporary folder path.
    
    Args:
        temp_type: Type of temp folder ('processing' or 'downloads')
    
    Returns:
        Path: Path to temp directory
    
    Examples:
        get_temp_path('processing')  # -> system_data/temp/processing/
        get_temp_path('downloads')  # -> system_data/temp/downloads/
    """
    return get_system_data_path('temp', temp_type)


def get_custom_plugins_path() -> Path:
    """
    Get custom plugins folder path.
    
    Returns:
        Path: Path to custom plugins directory
    
    Examples:
        get_custom_plugins_path()  # -> user_data/custom_plugins/
    """
    return get_user_data_path('custom_plugins')


# ============================================================================
# MIGRATION HELPERS
# Check if migration is needed or completed
# ============================================================================

def is_migrated() -> bool:
    """
    Check if folder structure has been migrated.
    
    Returns:
        bool: True if migrated, False if still using old structure
    """
    marker = get_user_data_path('.migrated')
    return marker.exists()


def needs_migration() -> bool:
    """
    Check if folder structure needs migration.
    
    Returns:
        bool: True if old structure exists and migration not done
    """
    # Check if old folders exist
    old_folders_exist = (
        get_app_path('config').exists() or
        get_app_path('dictionary').exists() or
        get_app_path('cache').exists()
    )
    
    # Check if already migrated
    already_migrated = is_migrated()
    
    return old_folders_exist and not already_migrated


def get_migration_status() -> dict:
    """
    Get detailed migration status.
    
    Returns:
        dict: Migration status information
    """
    return {
        'migrated': is_migrated(),
        'needs_migration': needs_migration(),
        'old_structure_exists': get_app_path('config').exists(),
        'new_structure_exists': get_user_data_path('config').exists(),
        'old_folders': {
            'config': get_app_path('config').exists(),
            'dictionary': get_app_path('dictionary').exists(),
            'cache': get_app_path('cache').exists(),
            'logs': get_app_path('logs').exists(),
            'models': get_app_path('models').exists(),
        },
        'new_folders': {
            'user_data': get_user_data_path('config').exists(),
            'system_data': get_system_data_path('cache').exists(),
        }
    }
