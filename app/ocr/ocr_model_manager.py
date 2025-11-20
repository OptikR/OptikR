"""
OCR Model Manager
Handles downloading, managing, and discovering OCR models.
Similar to Universal Model Manager but for OCR engines.
"""

import logging
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OCRModel:
    """Represents an OCR model."""
    model_name: str
    engine_type: str  # "easyocr", "tesseract", "paddleocr", "manga_ocr"
    language: str
    size_mb: float
    is_downloaded: bool = False
    description: str = ""


class OCRModelManager:
    """Manages OCR models with discovery and plugin generation."""
    
    def __init__(self, cache_dir: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """Initialize the OCR model manager."""
        self.logger = logger or logging.getLogger(__name__)
        
        # Set cache directory - use models/ocr/ for OCR models
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to models/ocr/
            base_models_dir = Path(__file__).parent.parent.parent / "models"
            self.cache_dir = base_models_dir / "ocr"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load model registry
        registry_dir = self.cache_dir / "ocr_registry"
        registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = registry_dir / "ocr_models.json"
        self.registry = self._load_registry()
        
        self.logger.info(f"OCR Model Manager initialized. Cache: {self.cache_dir}")
    
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
    
    def discover_models(self) -> List[OCRModel]:
        """
        Discover OCR models in the models/ocr/ folder.
        
        Returns:
            List of discovered OCR models
        """
        discovered = []
        
        if not self.cache_dir.exists():
            return discovered
        
        # Scan all subdirectories
        for model_dir in self.cache_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name in ["ocr_registry"]:
                continue
            
            # Check for model files
            has_config = (model_dir / "config.json").exists() or (model_dir / "model.json").exists()
            has_weights = (
                (model_dir / "pytorch_model.bin").exists() or
                (model_dir / "model.safetensors").exists() or
                (model_dir / "model.pth").exists() or
                any(model_dir.glob("*.pth")) or
                any(model_dir.glob("*.bin"))
            )
            
            if has_config or has_weights:
                # Calculate size
                size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                
                # Check if registered
                is_registered = model_dir.name in self.registry.get("models", {})
                
                # Get engine type from registry or guess
                engine_type = "unknown"
                language = "unknown"
                if is_registered:
                    model_info = self.registry["models"][model_dir.name]
                    engine_type = model_info.get("engine_type", "unknown")
                    language = model_info.get("language", "unknown")
                
                model = OCRModel(
                    model_name=model_dir.name,
                    engine_type=engine_type,
                    language=language,
                    size_mb=size_mb,
                    is_downloaded=True,
                    description=f"Custom OCR model ({size_mb:.1f} MB)"
                )
                discovered.append(model)
        
        return discovered
    
    def register_model(self, model_name: str, engine_type: str, language: str) -> bool:
        """
        Register a discovered model in the registry.
        
        Args:
            model_name: Model folder name
            engine_type: OCR engine type (easyocr, tesseract, etc.)
            language: Language code
            
        Returns:
            True if registration successful
        """
        try:
            model_path = self.cache_dir / model_name
            
            if not model_path.exists():
                self.logger.error(f"Model not found: {model_name}")
                return False
            
            # Calculate size
            size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            
            # Update registry
            self.registry.setdefault("models", {})[model_name] = {
                "engine_type": engine_type,
                "language": language,
                "size_mb": size_mb,
                "registered_date": datetime.now().isoformat(),
                "custom": True
            }
            self._save_registry()
            
            self.logger.info(f"Registered OCR model: {model_name} ({engine_type}, {language})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register {model_name}: {e}")
            return False
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics."""
        try:
            # Count models
            total_models = len(self.registry.get("models", {}))
            
            # Calculate cache size
            total_size = 0
            if self.cache_dir.exists():
                total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            
            # Get available disk space
            stat = shutil.disk_usage(self.cache_dir)
            available_space_gb = stat.free / (1024 * 1024 * 1024)
            
            return {
                "cache_directory": str(self.cache_dir),
                "total_models": total_models,
                "total_size_mb": total_size_mb,
                "available_space_gb": available_space_gb
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache info: {e}")
            return {
                "cache_directory": str(self.cache_dir),
                "total_models": 0,
                "total_size_mb": 0,
                "available_space_gb": 0
            }


def create_ocr_model_manager(cache_dir: Optional[Path] = None) -> OCRModelManager:
    """Create an OCR model manager."""
    return OCRModelManager(cache_dir=cache_dir)
