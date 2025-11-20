"""
Universal Translation Model Manager
Handles downloading, managing, and optimizing translation models for multiple types:
- MarianMT (Helsinki-NLP)
- NLLB-200 (Meta AI)
- M2M-100 (Facebook)
- mBART (Facebook)
"""

import logging
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading


@dataclass
class TranslationModel:
    """Represents a translation model (any type)."""
    model_name: str
    model_type: str  # "marianmt", "nllb", "m2m100", "mbart"
    source_language: str
    target_language: str
    size_mb: float
    accuracy_bleu: float = 0.0
    is_downloaded: bool = False
    is_optimized: bool = False
    download_url: str = ""
    description: str = ""
    languages_count: int = 2  # For multilingual models


@dataclass
class OptimizationResult:
    """Result of model optimization."""
    success: bool
    original_size_mb: float
    optimized_size_mb: float
    speed_improvement: float
    memory_reduction_mb: float
    error_message: str = ""


class UniversalModelManager:
    """Manages translation models for multiple model types with download capabilities."""
    
    # Available MarianMT models from HuggingFace (Helsinki-NLP)
    MARIANMT_MODELS = {
        "en-de": {"name": "opus-mt-en-de", "size": 298, "bleu": 41.2, "desc": "English to German"},
        "de-en": {"name": "opus-mt-de-en", "size": 301, "bleu": 43.1, "desc": "German to English"},
        "en-es": {"name": "opus-mt-en-es", "size": 301, "bleu": 42.8, "desc": "English to Spanish"},
        "es-en": {"name": "opus-mt-es-en", "size": 298, "bleu": 44.3, "desc": "Spanish to English"},
        "en-fr": {"name": "opus-mt-en-fr", "size": 290, "bleu": 40.5, "desc": "English to French"},
        "fr-en": {"name": "opus-mt-fr-en", "size": 287, "bleu": 42.7, "desc": "French to English"},
        "en-it": {"name": "opus-mt-en-it", "size": 285, "bleu": 38.9, "desc": "English to Italian"},
        "it-en": {"name": "opus-mt-it-en", "size": 283, "bleu": 41.2, "desc": "Italian to English"},
        "en-pt": {"name": "opus-mt-en-pt", "size": 295, "bleu": 39.7, "desc": "English to Portuguese"},
        "pt-en": {"name": "opus-mt-pt-en", "size": 292, "bleu": 42.1, "desc": "Portuguese to English"},
        "en-ja": {"name": "opus-mt-en-jap", "size": 312, "bleu": 28.5, "desc": "English to Japanese"},
        "ja-en": {"name": "opus-mt-jap-en", "size": 315, "bleu": 31.2, "desc": "Japanese to English"},
        "en-zh": {"name": "opus-mt-en-zh", "size": 325, "bleu": 26.8, "desc": "English to Chinese"},
        "zh-en": {"name": "opus-mt-zh-en", "size": 328, "bleu": 29.4, "desc": "Chinese to English"},
        "en-ko": {"name": "opus-mt-en-ko", "size": 308, "bleu": 24.3, "desc": "English to Korean"},
        "ko-en": {"name": "opus-mt-ko-en", "size": 310, "bleu": 27.8, "desc": "Korean to English"},
        "en-ru": {"name": "opus-mt-en-ru", "size": 318, "bleu": 32.1, "desc": "English to Russian"},
        "ru-en": {"name": "opus-mt-ru-en", "size": 320, "bleu": 35.6, "desc": "Russian to English"},
        "en-ar": {"name": "opus-mt-en-ar", "size": 295, "bleu": 27.9, "desc": "English to Arabic"},
        "ar-en": {"name": "opus-mt-ar-en", "size": 298, "bleu": 30.2, "desc": "Arabic to English"},
        "en-nl": {"name": "opus-mt-en-nl", "size": 288, "bleu": 39.4, "desc": "English to Dutch"},
        "nl-en": {"name": "opus-mt-nl-en", "size": 285, "bleu": 41.8, "desc": "Dutch to English"},
        "en-pl": {"name": "opus-mt-en-pl", "size": 292, "bleu": 33.7, "desc": "English to Polish"},
        "pl-en": {"name": "opus-mt-pl-en", "size": 290, "bleu": 36.2, "desc": "Polish to English"},
        "en-tr": {"name": "opus-mt-en-tr", "size": 285, "bleu": 31.5, "desc": "English to Turkish"},
        "tr-en": {"name": "opus-mt-tr-en", "size": 283, "bleu": 34.1, "desc": "Turkish to English"},
    }
    
    # Available NLLB-200 models from Meta AI (200 languages)
    NLLB_MODELS = {
        "distilled-600M": {
            "name": "nllb-200-distilled-600M",
            "size": 600,
            "languages": 200,
            "bleu": 38.5,
            "desc": "Distilled model - 600MB, 200 languages, good quality"
        },
        "1.3B": {
            "name": "nllb-200-1.3B",
            "size": 1300,
            "languages": 200,
            "bleu": 42.1,
            "desc": "Standard model - 1.3GB, 200 languages, high quality"
        },
        "3.3B": {
            "name": "nllb-200-3.3B",
            "size": 3300,
            "languages": 200,
            "bleu": 44.8,
            "desc": "Large model - 3.3GB, 200 languages, best quality"
        }
    }
    
    # Available M2M-100 models from Facebook (100 languages)
    M2M100_MODELS = {
        "418M": {
            "name": "m2m100_418M",
            "size": 418,
            "languages": 100,
            "bleu": 35.2,
            "desc": "Small model - 418MB, 100 languages, fast"
        },
        "1.2B": {
            "name": "m2m100_1.2B",
            "size": 1200,
            "languages": 100,
            "bleu": 39.7,
            "desc": "Large model - 1.2GB, 100 languages, high quality"
        }
    }
    
    # Available mBART models from Facebook (50 languages)
    MBART_MODELS = {
        "large-50": {
            "name": "mbart-large-50-many-to-many-mmt",
            "size": 2400,
            "languages": 50,
            "bleu": 41.3,
            "desc": "Large model - 2.4GB, 50 languages, excellent quality"
        }
    }
    
    def __init__(self, model_type: str = "marianmt", cache_dir: Optional[Path] = None, 
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the universal model manager.
        
        Args:
            model_type: Type of model ("marianmt", "nllb", "m2m100", "mbart")
            cache_dir: Optional cache directory (defaults to models/{model_type})
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.model_type = model_type.lower()
        
        # Set cache directory - use models/language/ for translation models
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to models/language/ for translation models
            base_models_dir = Path(__file__).parent.parent.parent / "models"
            self.cache_dir = base_models_dir / "language"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load model registry - separate registry per model type in language_registry subfolder
        registry_dir = self.cache_dir / "language_registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = registry_dir / f"model_registry_{self.model_type}.json"
        self.registry = self._load_registry()
        
        # Device detection
        self.device = self._detect_device()
        
        self.logger.info(f"Universal Model Manager initialized. Type: {self.model_type}, Cache: {self.cache_dir}, Device: {self.device}")
    
    def _detect_device(self) -> str:
        """Detect available compute device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
    
    def _load_registry(self) -> Dict:
        """Load the model registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load registry: {e}")
        
        return {"models": {}, "last_updated": datetime.now().isoformat()}
    
    def _save_registry(self):
        """Save the model registry to disk."""
        try:
            self.registry["last_updated"] = datetime.now().isoformat()
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
    
    def discover_models(self) -> List[str]:
        """
        Discover translation models in the cache directory that are not in the registry.
        
        Scans for HuggingFace model folders with:
        - config.json (model configuration)
        - pytorch_model.bin or model.safetensors (model weights)
        
        Returns:
            List of discovered model names (folder names) not in registry
        """
        discovered = []
        
        if not self.cache_dir.exists():
            self.logger.warning(f"Cache directory does not exist: {self.cache_dir}")
            return discovered
        
        self.logger.info(f"Scanning for models in: {self.cache_dir}")
        
        # Scan all subdirectories
        for model_dir in self.cache_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            # Skip registry directories
            if model_dir.name in ["language_registry", "ocr_registry"]:
                continue
            
            # Check for HuggingFace model structure
            has_config = (model_dir / "config.json").exists()
            has_weights = (
                (model_dir / "pytorch_model.bin").exists() or
                (model_dir / "model.safetensors").exists() or
                any(model_dir.glob("pytorch_model*.bin")) or
                any(model_dir.glob("model*.safetensors"))
            )
            
            if has_config and has_weights:
                # Check if already in registry
                model_name = model_dir.name
                if model_name not in self.registry.get("models", {}):
                    self.logger.info(f"Discovered unregistered model: {model_name}")
                    discovered.append(model_name)
                else:
                    self.logger.debug(f"Model already registered: {model_name}")
        
        self.logger.info(f"Discovered {len(discovered)} unregistered models")
        return discovered
    
    def register_discovered_model(self, model_name: str, language_pair: Optional[str] = None,
                                  description: Optional[str] = None) -> bool:
        """
        Register a manually discovered model in the registry.
        
        Args:
            model_name: Model folder name (e.g., "opus-mt-en-de" or "Helsinki-NLP/opus-mt-en-de")
            language_pair: Language pair (e.g., "en-de") - optional, will try to detect
            description: Custom description - optional
            
        Returns:
            True if registration successful
        """
        try:
            # Handle both folder names and full model names
            if "/" in model_name:
                folder_name = model_name.split("/")[-1]
            else:
                folder_name = model_name
            
            model_path = self.cache_dir / folder_name
            
            if not model_path.exists():
                self.logger.error(f"Model not found: {model_path}")
                return False
            
            # Verify it's a valid model
            has_config = (model_path / "config.json").exists()
            has_weights = (
                (model_path / "pytorch_model.bin").exists() or
                (model_path / "model.safetensors").exists()
            )
            
            if not (has_config and has_weights):
                self.logger.error(f"Invalid model structure: {model_path}")
                return False
            
            # Try to detect language pair from folder name
            if not language_pair:
                # Try to extract from opus-mt-XX-YY pattern
                if "opus-mt-" in folder_name:
                    parts = folder_name.replace("opus-mt-", "").split("-")
                    if len(parts) >= 2:
                        language_pair = f"{parts[0]}-{parts[1]}"
                        self.logger.info(f"Detected language pair: {language_pair}")
            
            # Calculate size
            size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            
            # Create registry entry
            registry_entry = {
                "model_name": folder_name,
                "downloaded": True,
                "download_date": datetime.now().isoformat(),
                "size_mb": size_mb,
                "manually_added": True,  # Mark as manually added
                "description": description or f"Manually added model ({size_mb:.1f} MB)"
            }
            
            if language_pair:
                registry_entry["language_pair"] = language_pair
            
            # Add to registry
            self.registry.setdefault("models", {})[folder_name] = registry_entry
            self._save_registry()
            
            self.logger.info(f"Successfully registered model: {folder_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register model {model_name}: {e}")
            return False
    
    def get_available_models(self, source_lang: Optional[str] = None, 
                           target_lang: Optional[str] = None) -> List[TranslationModel]:
        """
        Get list of available models based on model type.
        
        For MarianMT: Returns language-pair specific models
        For NLLB/M2M/mBART: Returns multilingual models (one model for all pairs)
        """
        models = []
        
        if self.model_type == "marianmt":
            # MarianMT: Language-pair specific models
            for lang_pair, info in self.MARIANMT_MODELS.items():
                src, tgt = lang_pair.split("-")
                
                # Apply filters
                if source_lang and src != source_lang:
                    continue
                if target_lang and tgt != target_lang:
                    continue
                
                # Check if downloaded
                is_downloaded = self.is_model_downloaded(info["name"])
                is_optimized = self.registry.get("models", {}).get(info["name"], {}).get("optimized", False)
                
                model = TranslationModel(
                    model_name=info["name"],
                    model_type=self.model_type,
                    source_language=src,
                    target_language=tgt,
                    size_mb=info["size"],
                    accuracy_bleu=info.get("bleu", 0.0),
                    is_downloaded=is_downloaded,
                    is_optimized=is_optimized,
                    download_url=f"Helsinki-NLP/{info['name']}",
                    description=info["desc"],
                    languages_count=2
                )
                models.append(model)
        
        elif self.model_type == "nllb":
            # NLLB: Multilingual models (one model for all language pairs)
            for model_id, info in self.NLLB_MODELS.items():
                is_downloaded = self.is_model_downloaded(info["name"])
                is_optimized = self.registry.get("models", {}).get(info["name"], {}).get("optimized", False)
                
                model = TranslationModel(
                    model_name=info["name"],
                    model_type=self.model_type,
                    source_language="multilingual",
                    target_language="multilingual",
                    size_mb=info["size"],
                    accuracy_bleu=info.get("bleu", 0.0),
                    is_downloaded=is_downloaded,
                    is_optimized=is_optimized,
                    download_url=f"facebook/{info['name']}",
                    description=info["desc"],
                    languages_count=info["languages"]
                )
                models.append(model)
        
        elif self.model_type == "m2m100":
            # M2M-100: Multilingual models
            for model_id, info in self.M2M100_MODELS.items():
                is_downloaded = self.is_model_downloaded(info["name"])
                is_optimized = self.registry.get("models", {}).get(info["name"], {}).get("optimized", False)
                
                model = TranslationModel(
                    model_name=info["name"],
                    model_type=self.model_type,
                    source_language="multilingual",
                    target_language="multilingual",
                    size_mb=info["size"],
                    accuracy_bleu=info.get("bleu", 0.0),
                    is_downloaded=is_downloaded,
                    is_optimized=is_optimized,
                    download_url=f"facebook/{info['name']}",
                    description=info["desc"],
                    languages_count=info["languages"]
                )
                models.append(model)
        
        elif self.model_type == "mbart":
            # mBART: Multilingual models
            for model_id, info in self.MBART_MODELS.items():
                is_downloaded = self.is_model_downloaded(info["name"])
                is_optimized = self.registry.get("models", {}).get(info["name"], {}).get("optimized", False)
                
                model = TranslationModel(
                    model_name=info["name"],
                    model_type=self.model_type,
                    source_language="multilingual",
                    target_language="multilingual",
                    size_mb=info["size"],
                    accuracy_bleu=info.get("bleu", 0.0),
                    is_downloaded=is_downloaded,
                    is_optimized=is_optimized,
                    download_url=f"facebook/{info['name']}",
                    description=info["desc"],
                    languages_count=info["languages"]
                )
                models.append(model)
        
        return models
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """Check if a model is downloaded."""
        model_path = self.cache_dir / model_name
        return model_path.exists() and (model_path / "config.json").exists()
    
    def download_model(self, model_name: str, source_lang: Optional[str] = None,
                      target_lang: Optional[str] = None, progress_callback=None, 
                      auto_generate_plugin: bool = True) -> bool:
        """
        Download a translation model from HuggingFace.
        
        Args:
            model_name: Model name (e.g., "opus-mt-en-de", "nllb-200-distilled-600M")
            source_lang: Source language (required for multilingual models)
            target_lang: Target language (required for multilingual models)
            progress_callback: Optional callback for progress updates
            auto_generate_plugin: Whether to auto-generate plugin after download
            
        Returns:
            True if download successful
        """
        try:
            self.logger.info(f"Downloading {self.model_type} model: {model_name}")
            
            # Import transformers
            try:
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            except ImportError:
                self.logger.error("transformers library not installed")
                return False
            
            # Get model info based on model type
            model_info = None
            lang_pair = None
            
            if self.model_type == "marianmt":
                # MarianMT: Find in MARIANMT_MODELS
                for pair, info in self.MARIANMT_MODELS.items():
                    if info["name"] == model_name:
                        model_info = info
                        lang_pair = pair
                        break
                
                if not model_info:
                    self.logger.error(f"Unknown MarianMT model: {model_name}")
                    return False
                
                # Get HuggingFace model ID
                model_id = f"Helsinki-NLP/{model_name}"
                
            elif self.model_type in ["nllb", "m2m100", "mbart"]:
                # Multilingual models: Find in respective dictionary
                model_dict = {
                    "nllb": self.NLLB_MODELS,
                    "m2m100": self.M2M100_MODELS,
                    "mbart": self.MBART_MODELS
                }[self.model_type]
                
                for model_id_key, info in model_dict.items():
                    if info["name"] == model_name:
                        model_info = info
                        break
                
                if not model_info:
                    self.logger.error(f"Unknown {self.model_type} model: {model_name}")
                    return False
                
                # Validate language parameters for multilingual models
                if not source_lang or not target_lang:
                    self.logger.error(f"source_lang and target_lang required for {self.model_type} models")
                    return False
                
                lang_pair = f"{source_lang}-{target_lang}"
                
                # Get HuggingFace model ID
                model_id = f"facebook/{model_name}"
            
            else:
                self.logger.error(f"Unsupported model type: {self.model_type}")
                return False
            
            # Download model and tokenizer
            model_path = self.cache_dir / model_name
            
            self.logger.info(f"Downloading from {model_id} to {model_path}")
            
            # Download tokenizer
            if progress_callback:
                progress_callback(0.3, "Downloading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            tokenizer.save_pretrained(model_path)
            
            # Download model
            if progress_callback:
                progress_callback(0.6, "Downloading model...")
            model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
            model.save_pretrained(model_path)
            
            if progress_callback:
                progress_callback(0.9, "Updating registry...")
            
            # Update registry
            registry_entry = {
                "downloaded": True,
                "download_date": datetime.now().isoformat(),
                "size_mb": model_info["size"],
                "optimized": False,
                "model_type": self.model_type
            }
            
            # Add language pair info
            if lang_pair:
                registry_entry["language_pair"] = lang_pair
            
            # Add language count for multilingual models
            if self.model_type in ["nllb", "m2m100", "mbart"]:
                registry_entry["languages_count"] = model_info.get("languages", 0)
            
            self.registry.setdefault("models", {})[model_name] = registry_entry
            self._save_registry()
            
            # Auto-generate plugin if requested
            if auto_generate_plugin and lang_pair:
                if progress_callback:
                    progress_callback(0.95, "Generating plugin...")
                
                src_lang, tgt_lang = lang_pair.split("-")
                self._generate_plugin_for_model(model_name, src_lang, tgt_lang, model_info)
            
            if progress_callback:
                progress_callback(1.0, "Complete!")
            
            self.logger.info(f"Successfully downloaded {model_name} ({self.model_type})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {model_name}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _generate_plugin_for_model(self, model_name: str, source_lang: str, 
                                   target_lang: str, model_info: dict) -> bool:
        """Generate a translation plugin for the downloaded model using universal generator."""
        try:
            from app.workflow.universal_plugin_generator import PluginGenerator
            
            generator = PluginGenerator(output_dir="plugins")
            
            # Create plugin name based on model type and languages
            plugin_name = f"{self.model_type}_{source_lang}_{target_lang}"
            
            # Check if plugin already exists
            plugin_path = Path("plugins") / "translation" / plugin_name
            if (plugin_path / "plugin.json").exists():
                self.logger.info(f"Plugin already exists for {source_lang}-{target_lang} ({self.model_type})")
                return True
            
            # Generate plugin using universal generator
            success = generator.create_plugin_programmatically(
                plugin_type='translation',
                name=plugin_name,
                display_name=f"{self.model_type.upper()} {source_lang.upper()}→{target_lang.upper()}",
                description=f"Translation plugin for {model_name} ({source_lang} to {target_lang})",
                author="OptikR Auto-Generator",
                version="1.0.0",
                dependencies=["transformers", "torch", "sentencepiece"],
                settings={
                    'model_name': {
                        'type': 'string',
                        'default': model_name,
                        'description': 'HuggingFace model name'
                    },
                    'source_language': {
                        'type': 'string',
                        'default': source_lang,
                        'description': 'Source language code'
                    },
                    'target_language': {
                        'type': 'string',
                        'default': target_lang,
                        'description': 'Target language code'
                    },
                    'max_length': {
                        'type': 'int',
                        'default': 512,
                        'description': 'Maximum sequence length'
                    }
                }
            )
            
            if success:
                self.logger.info(f"✓ Auto-generated {self.model_type} plugin for {source_lang}-{target_lang}")
            else:
                self.logger.warning(f"Failed to auto-generate {self.model_type} plugin for {source_lang}-{target_lang}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Plugin generation failed: {e}")
            return False
    
    def delete_model(self, model_name: str, delete_plugin: bool = True) -> bool:
        """Delete a downloaded model."""
        try:
            model_path = self.cache_dir / model_name
            
            if not model_path.exists():
                self.logger.warning(f"Model not found: {model_name}")
                return False
            
            # Get language pair before deleting
            lang_pair = None
            if model_name in self.registry.get("models", {}):
                lang_pair = self.registry["models"][model_name].get("language_pair")
            
            # Remove directory
            shutil.rmtree(model_path)
            
            # Update registry
            if model_name in self.registry.get("models", {}):
                del self.registry["models"][model_name]
                self._save_registry()
            
            # Delete plugin if requested
            if delete_plugin and lang_pair:
                src_lang, tgt_lang = lang_pair.split("-")
                self._delete_plugin_for_model(src_lang, tgt_lang)
            
            self.logger.info(f"Deleted model: {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {model_name}: {e}")
            return False
    
    def _delete_plugin_for_model(self, source_lang: str, target_lang: str) -> bool:
        """Delete the translation plugin for a model."""
        try:
            import shutil
            
            # Create plugin name based on model type and languages
            plugin_name = f"{self.model_type}_{source_lang}_{target_lang}"
            plugin_path = Path("plugins") / "translation" / plugin_name
            
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
                self.logger.info(f"✓ Deleted {self.model_type} plugin for {source_lang}-{target_lang}")
                return True
            else:
                self.logger.warning(f"Plugin not found: {plugin_path}")
                return False
            
        except Exception as e:
            self.logger.error(f"Plugin deletion failed: {e}")
            return False
    
    def get_model_type(self) -> str:
        """Get the current model type."""
        return self.model_type
    
    def get_supported_model_types(self) -> List[str]:
        """Get list of supported model types."""
        return ["marianmt", "nllb", "m2m100", "mbart"]
    
    def get_supported_languages(self, model_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Get list of supported languages for a model type.
        
        Args:
            model_type: Model type (defaults to current model type)
            
        Returns:
            List of (language_code, language_name) tuples
            
        For MarianMT: Returns available language pairs
        For NLLB/M2M/mBART: Returns common languages (subset of full list)
        """
        model_type = model_type or self.model_type
        
        if model_type == "marianmt":
            # Return unique languages from MarianMT models
            languages = set()
            for lang_pair in self.MARIANMT_MODELS.keys():
                src, tgt = lang_pair.split("-")
                languages.add(src)
                languages.add(tgt)
            
            # Map to language names
            lang_names = {
                "en": "English", "de": "German", "es": "Spanish", "fr": "French",
                "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
                "ko": "Korean", "ru": "Russian", "ar": "Arabic", "nl": "Dutch",
                "pl": "Polish", "tr": "Turkish"
            }
            
            return [(code, lang_names.get(code, code.upper())) for code in sorted(languages)]
        
        elif model_type == "nllb":
            # NLLB supports 200 languages - return common ones
            # Full list: https://github.com/facebookresearch/flores/blob/main/flores200/README.md
            return [
                ("eng_Latn", "English"),
                ("deu_Latn", "German"),
                ("spa_Latn", "Spanish"),
                ("fra_Latn", "French"),
                ("ita_Latn", "Italian"),
                ("por_Latn", "Portuguese"),
                ("jpn_Jpan", "Japanese"),
                ("zho_Hans", "Chinese (Simplified)"),
                ("kor_Hang", "Korean"),
                ("rus_Cyrl", "Russian"),
                ("ara_Arab", "Arabic"),
                ("nld_Latn", "Dutch"),
                ("pol_Latn", "Polish"),
                ("tur_Latn", "Turkish"),
                ("hin_Deva", "Hindi"),
                ("tha_Thai", "Thai"),
                ("vie_Latn", "Vietnamese"),
                ("ind_Latn", "Indonesian"),
                ("ukr_Cyrl", "Ukrainian"),
                ("ces_Latn", "Czech"),
            ]
        
        elif model_type == "m2m100":
            # M2M-100 supports 100 languages - return common ones
            return [
                ("en", "English"),
                ("de", "German"),
                ("es", "Spanish"),
                ("fr", "French"),
                ("it", "Italian"),
                ("pt", "Portuguese"),
                ("ja", "Japanese"),
                ("zh", "Chinese"),
                ("ko", "Korean"),
                ("ru", "Russian"),
                ("ar", "Arabic"),
                ("nl", "Dutch"),
                ("pl", "Polish"),
                ("tr", "Turkish"),
                ("hi", "Hindi"),
                ("th", "Thai"),
                ("vi", "Vietnamese"),
                ("id", "Indonesian"),
                ("uk", "Ukrainian"),
                ("cs", "Czech"),
            ]
        
        elif model_type == "mbart":
            # mBART supports 50 languages
            return [
                ("en_XX", "English"),
                ("de_DE", "German"),
                ("es_XX", "Spanish"),
                ("fr_XX", "French"),
                ("it_IT", "Italian"),
                ("pt_XX", "Portuguese"),
                ("ja_XX", "Japanese"),
                ("zh_CN", "Chinese"),
                ("ko_KR", "Korean"),
                ("ru_RU", "Russian"),
                ("ar_AR", "Arabic"),
                ("nl_XX", "Dutch"),
                ("pl_PL", "Polish"),
                ("tr_TR", "Turkish"),
                ("hi_IN", "Hindi"),
                ("th_TH", "Thai"),
                ("vi_VN", "Vietnamese"),
                ("id_ID", "Indonesian"),
                ("uk_UA", "Ukrainian"),
                ("cs_CZ", "Czech"),
            ]
        
        return []
    
    def optimize_model(self, model_name: str) -> OptimizationResult:
        """Optimize a model for faster inference."""
        try:
            if not self.is_model_downloaded(model_name):
                return OptimizationResult(
                    success=False,
                    original_size_mb=0,
                    optimized_size_mb=0,
                    speed_improvement=0,
                    memory_reduction_mb=0,
                    error_message="Model not downloaded"
                )
            
            model_path = self.cache_dir / model_name
            
            # Get original size
            original_size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
            original_size_mb = original_size / (1024 * 1024)
            
            # Optimization: Convert to half precision (FP16) if on GPU
            if self.device == "cuda":
                try:
                    from transformers import MarianMTModel
                    import torch
                    
                    model = MarianMTModel.from_pretrained(model_path)
                    model = model.half()  # Convert to FP16
                    model.save_pretrained(model_path)
                    
                    # Get optimized size
                    optimized_size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
                    optimized_size_mb = optimized_size / (1024 * 1024)
                    
                    # Update registry
                    if model_name in self.registry.get("models", {}):
                        self.registry["models"][model_name]["optimized"] = True
                        self.registry["models"][model_name]["optimization_date"] = datetime.now().isoformat()
                        self._save_registry()
                    
                    return OptimizationResult(
                        success=True,
                        original_size_mb=original_size_mb,
                        optimized_size_mb=optimized_size_mb,
                        speed_improvement=1.5,  # Typical FP16 speedup
                        memory_reduction_mb=original_size_mb - optimized_size_mb
                    )
                except Exception as e:
                    return OptimizationResult(
                        success=False,
                        original_size_mb=original_size_mb,
                        optimized_size_mb=original_size_mb,
                        speed_improvement=0,
                        memory_reduction_mb=0,
                        error_message=str(e)
                    )
            else:
                # CPU optimization: just mark as optimized (no actual optimization needed)
                if model_name in self.registry.get("models", {}):
                    self.registry["models"][model_name]["optimized"] = True
                    self._save_registry()
                
                return OptimizationResult(
                    success=True,
                    original_size_mb=original_size_mb,
                    optimized_size_mb=original_size_mb,
                    speed_improvement=1.0,
                    memory_reduction_mb=0
                )
                
        except Exception as e:
            self.logger.error(f"Failed to optimize {model_name}: {e}")
            return OptimizationResult(
                success=False,
                original_size_mb=0,
                optimized_size_mb=0,
                speed_improvement=0,
                memory_reduction_mb=0,
                error_message=str(e)
            )

    def get_cache_info(self) -> Dict:
        """Get cache statistics."""
        try:
            # Count models based on model type
            if self.model_type == "marianmt":
                total_models = len(self.MARIANMT_MODELS)
            elif self.model_type == "nllb":
                total_models = len(self.NLLB_MODELS)
            elif self.model_type == "m2m100":
                total_models = len(self.M2M100_MODELS)
            elif self.model_type == "mbart":
                total_models = len(self.MBART_MODELS)
            else:
                total_models = 0
            
            downloaded_models = sum(1 for m in self.registry.get("models", {}).values() if m.get("downloaded", False))
            optimized_models = sum(1 for m in self.registry.get("models", {}).values() if m.get("optimized", False))
            
            # Calculate cache size
            total_size = 0
            if self.cache_dir.exists():
                total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            
            # Get available disk space
            import shutil
            stat = shutil.disk_usage(self.cache_dir)
            available_space_gb = stat.free / (1024 * 1024 * 1024)
            
            return {
                "cache_directory": str(self.cache_dir),
                "model_type": self.model_type,
                "total_models": total_models,
                "downloaded_models": downloaded_models,
                "optimized_models": optimized_models,
                "total_size_mb": total_size_mb,
                "available_space_gb": available_space_gb,
                "device": self.device
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache info: {e}")
            return {
                "cache_directory": str(self.cache_dir),
                "model_type": self.model_type,
                "total_models": 0,
                "downloaded_models": 0,
                "optimized_models": 0,
                "total_size_mb": 0,
                "available_space_gb": 0,
                "device": self.device
            }
    
    def cleanup_cache(self, max_age_days: int = 30, max_size_gb: float = 10.0) -> Dict:
        """Clean up old or unused models."""
        try:
            deleted_models = []
            freed_space_mb = 0
            
            current_time = datetime.now()
            
            for model_name, info in list(self.registry.get("models", {}).items()):
                should_delete = False
                
                # Check age
                if "download_date" in info:
                    download_date = datetime.fromisoformat(info["download_date"])
                    age_days = (current_time - download_date).days
                    if age_days > max_age_days:
                        should_delete = True
                
                # Check total cache size
                cache_info = self.get_cache_info()
                if cache_info["total_size_mb"] / 1024 > max_size_gb:
                    should_delete = True
                
                if should_delete:
                    model_path = self.cache_dir / model_name
                    if model_path.exists():
                        size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
                        size_mb = size / (1024 * 1024)
                        
                        if self.delete_model(model_name):
                            deleted_models.append(model_name)
                            freed_space_mb += size_mb
            
            return {
                "deleted_models": deleted_models,
                "freed_space_mb": freed_space_mb,
                "total_models": len(self.registry.get("models", {}))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {e}")
            return {
                "deleted_models": [],
                "freed_space_mb": 0,
                "total_models": 0
            }
    
    def download_language_pairs(self, pairs: List[Tuple[str, str]], progress_callback=None) -> Dict[str, bool]:
        """Download multiple language pairs."""
        results = {}
        total = len(pairs)
        
        for idx, (src, tgt) in enumerate(pairs):
            lang_pair = f"{src}-{tgt}"
            
            if lang_pair in self.AVAILABLE_MODELS:
                model_name = self.AVAILABLE_MODELS[lang_pair]["name"]
                
                # Update progress
                if progress_callback:
                    progress_callback(idx / total, f"Downloading {lang_pair}...")
                
                success = self.download_model(model_name)
                results[lang_pair] = success
            else:
                results[lang_pair] = False
        
        if progress_callback:
            progress_callback(1.0, "Complete")
        
        return results
    
    def get_language_pairs(self) -> List[Tuple[str, str, str]]:
        """Get all available language pairs with descriptions."""
        pairs = []
        for lang_pair, info in self.AVAILABLE_MODELS.items():
            src, tgt = lang_pair.split("-")
            pairs.append((src, tgt, info["desc"]))
        return pairs


def create_universal_model_manager(model_type: str = "marianmt", 
                                   cache_dir: Optional[Path] = None) -> UniversalModelManager:
    """
    Factory function to create a universal model manager.
    
    Args:
        model_type: Type of model ("marianmt", "nllb", "m2m100", "mbart")
        cache_dir: Optional cache directory
        
    Returns:
        UniversalModelManager instance
    """
    return UniversalModelManager(model_type=model_type, cache_dir=cache_dir)


# Backward compatibility
def create_marianmt_model_manager(cache_dir: Optional[Path] = None) -> UniversalModelManager:
    """Factory function to create a MarianMT model manager (backward compatibility)."""
    return UniversalModelManager(model_type="marianmt", cache_dir=cache_dir)
