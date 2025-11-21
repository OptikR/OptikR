"""
First Run Detector
Detects if this is the first run and models need to be downloaded.
"""

import os
from pathlib import Path
from typing import Tuple


def check_easyocr_models_cached() -> Tuple[bool, str]:
    """
    Check if EasyOCR models are already cached.
    
    Returns:
        Tuple of (models_exist, cache_path)
    """
    # EasyOCR default cache location
    cache_dir = Path.home() / ".EasyOCR" / "model"
    
    if not cache_dir.exists():
        return False, str(cache_dir)
    
    # Check for essential model files
    essential_models = [
        "craft_mlt_25k.pth",  # Text detection model
    ]
    
    for model_file in essential_models:
        model_path = cache_dir / model_file
        if not model_path.exists():
            return False, str(cache_dir)
    
    return True, str(cache_dir)


def check_translation_models_cached(language_pair: str = "en-de") -> Tuple[bool, str]:
    """
    Check if translation models are already cached.
    
    Args:
        language_pair: Language pair to check (e.g., "en-de")
    
    Returns:
        Tuple of (models_exist, cache_path)
    """
    # HuggingFace transformers cache location
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    
    if not cache_dir.exists():
        return False, str(cache_dir)
    
    # Check for MarianMT model for the language pair
    # Model folder format: models--Helsinki-NLP--opus-mt-{src}-{tgt}
    src, tgt = language_pair.split("-")
    model_folder_pattern = f"models--Helsinki-NLP--opus-mt-{src}-{tgt}"
    
    # Check if any matching model folder exists
    if cache_dir.exists():
        for item in cache_dir.iterdir():
            if item.is_dir() and model_folder_pattern in item.name:
                return True, str(cache_dir)
    
    return False, str(cache_dir)


def check_all_models_cached() -> dict:
    """
    Check if all required models are cached.
    
    Returns:
        Dictionary with status for each model type
    """
    ocr_cached, ocr_path = check_easyocr_models_cached()
    translation_cached, translation_path = check_translation_models_cached()
    
    return {
        "ocr": {
            "cached": ocr_cached,
            "path": ocr_path,
            "size_mb": 200,  # Approximate size
            "description": "OCR models (text detection and recognition)"
        },
        "translation": {
            "cached": translation_cached,
            "path": translation_path,
            "size_mb": 300,  # Approximate size per language pair
            "description": "Translation models (language-specific)"
        },
        "first_run": not (ocr_cached and translation_cached),
        "total_download_mb": (0 if ocr_cached else 200) + (0 if translation_cached else 300)
    }


def get_first_run_message() -> str:
    """
    Get a user-friendly message about first-run model downloads.
    
    Returns:
        Message string
    """
    status = check_all_models_cached()
    
    if not status["first_run"]:
        return ""
    
    download_size = status["total_download_mb"]
    
    message = "🚀 First Time Setup\n\n"
    
    if not status["ocr"]["cached"]:
        message += f"• OCR models (~{status['ocr']['size_mb']}MB)\n"
    
    if not status["translation"]["cached"]:
        message += f"• Translation models (~{status['translation']['size_mb']}MB)\n"
    
    message += f"\nTotal download: ~{download_size}MB\n"
    message += "Time: 2-3 minutes (one-time only)\n\n"
    message += "These models will be cached for future use.\n"
    message += "All subsequent runs will be instant!\n\n"
    message += "Please ensure you have an internet connection."
    
    return message
