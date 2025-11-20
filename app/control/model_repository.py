"""
Model Repository System

Provides a curated collection of AI models with metadata, compatibility information,
and download capabilities for the Real-Time Translation Overlay System.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

try:
    from .hardware_compatibility import (
        AIModelInfo, ModelType, HardwareRequirements, 
        CompatibilityEngine, CompatibilityResult
    )
    from ..interfaces import ILogger
except ImportError:
    from hardware_compatibility import (
        AIModelInfo, ModelType, HardwareRequirements,
        CompatibilityEngine, CompatibilityResult
    )
    from interfaces import ILogger

# Alias for backward compatibility
HardwareCompatibilityEngine = CompatibilityEngine


class ModelRepository:
    """Repository of curated AI models."""
    
    def __init__(self, logger: Optional[ILogger] = None):
        """Initialize model repository.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self._models = self._initialize_default_models()
    
    def get_available_models(self, model_type: Optional[ModelType] = None) -> List[AIModelInfo]:
        """Get available models, optionally filtered by type.
        
        Args:
            model_type: Optional model type filter
            
        Returns:
            List of available models
        """
        if model_type is None:
            return list(self._models.values())
        
        return [model for model in self._models.values() if model.model_type == model_type]
    
    def get_model_by_id(self, model_id: str) -> Optional[AIModelInfo]:
        """Get model by ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            AIModelInfo if found, None otherwise
        """
        return self._models.get(model_id)
    
    def search_models(self, query: str, model_type: Optional[ModelType] = None) -> List[AIModelInfo]:
        """Search models by name or description.
        
        Args:
            query: Search query
            model_type: Optional model type filter
            
        Returns:
            List of matching models
        """
        query_lower = query.lower()
        results = []
        
        for model in self._models.values():
            if model_type and model.model_type != model_type:
                continue
            
            if (query_lower in model.name.lower() or 
                query_lower in model.description.lower() or
                any(query_lower in lang.lower() for lang in model.supported_languages)):
                results.append(model)
        
        return results
    
    def get_models_by_language(self, language: str, model_type: Optional[ModelType] = None) -> List[AIModelInfo]:
        """Get models that support a specific language.
        
        Args:
            language: Language code (e.g., 'en', 'es', 'fr')
            model_type: Optional model type filter
            
        Returns:
            List of models supporting the language
        """
        results = []
        
        for model in self._models.values():
            if model_type and model.model_type != model_type:
                continue
            
            if language.lower() in [lang.lower() for lang in model.supported_languages]:
                results.append(model)
        
        return results
    
    def _initialize_default_models(self) -> Dict[str, AIModelInfo]:
        """Initialize repository with default models.
        
        Returns:
            Dictionary of model_id -> AIModelInfo
        """
        models = {}
        
        # OCR Models
        models.update(self._create_ocr_models())
        
        # Translation Models
        models.update(self._create_translation_models())
        
        # Preprocessing Models
        models.update(self._create_preprocessing_models())
        
        self.logger.info(f"Initialized model repository with {len(models)} models")
        
        return models
    
    def _create_ocr_models(self) -> Dict[str, AIModelInfo]:
        """Create OCR model definitions.
        
        Returns:
            Dictionary of OCR models
        """
        ocr_models = {}
        
        # Tesseract English
        ocr_models["tesseract_eng"] = AIModelInfo(
            model_id="tesseract_eng",
            name="Tesseract English",
            description="High-accuracy OCR for English text with excellent performance on printed text",
            model_type=ModelType.OCR,
            size_mb=15,
            download_url="https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata",
            checksum="c0515c9f1e0c79e1069fcc05c2b2f6a6d8e5c5c5c5c5c5c5c5c5c5c5c5c5c5c5",
            signature="tesseract_official",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=512,
                min_cpu_cores=1,
                min_cpu_frequency_ghz=1.0,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en"],
            accuracy_metrics={"accuracy": 95.0, "speed": 85.0},
            license="Apache 2.0",
            version="4.1.0"
        )
        
        # Tesseract Multilingual
        ocr_models["tesseract_multi"] = AIModelInfo(
            model_id="tesseract_multi",
            name="Tesseract Multilingual",
            description="Multi-language OCR supporting 100+ languages with good accuracy",
            model_type=ModelType.OCR,
            size_mb=45,
            download_url="https://github.com/tesseract-ocr/tessdata/archive/main.zip",
            checksum="d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2",
            signature="tesseract_official",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=1024,
                min_cpu_cores=2,
                min_cpu_frequency_ghz=1.5,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar"],
            accuracy_metrics={"accuracy": 90.0, "speed": 75.0},
            license="Apache 2.0",
            version="4.1.0"
        )
        
        # EasyOCR
        ocr_models["easyocr_standard"] = AIModelInfo(
            model_id="easyocr_standard",
            name="EasyOCR Standard",
            description="Neural network-based OCR with excellent accuracy on various text types",
            model_type=ModelType.OCR,
            size_mb=120,
            download_url="https://github.com/JaidedAI/EasyOCR/releases/download/v1.6.2/english_g2.zip",
            checksum="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
            signature="easyocr_official",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=2048,
                min_vram_mb=1024,
                requires_gpu=False,  # Can run on CPU
                min_cpu_cores=2,
                min_cpu_frequency_ghz=2.0,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"],
            accuracy_metrics={"accuracy": 92.0, "speed": 70.0},
            license="Apache 2.0",
            version="1.6.2"
        )
        
        # EasyOCR GPU Optimized
        ocr_models["easyocr_gpu"] = AIModelInfo(
            model_id="easyocr_gpu",
            name="EasyOCR GPU Optimized",
            description="GPU-accelerated EasyOCR for high-speed text recognition",
            model_type=ModelType.OCR,
            size_mb=150,
            download_url="https://github.com/JaidedAI/EasyOCR/releases/download/v1.6.2/english_g2_gpu.zip",
            checksum="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
            signature="easyocr_official",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=3072,
                min_vram_mb=2048,
                requires_gpu=True,
                cuda_compute_capability="6.0",
                min_cpu_cores=4,
                min_cpu_frequency_ghz=2.5,
                supported_os=["Windows", "Linux"]
            ),
            supported_languages=["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"],
            accuracy_metrics={"accuracy": 94.0, "speed": 95.0},
            license="Apache 2.0",
            version="1.6.2"
        )
        
        # PaddleOCR
        ocr_models["paddleocr_standard"] = AIModelInfo(
            model_id="paddleocr_standard",
            name="PaddleOCR Standard",
            description="High-performance OCR with excellent multilingual support",
            model_type=ModelType.OCR,
            size_mb=85,
            download_url="https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_det_infer.tar",
            checksum="c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
            signature="paddlepaddle_official",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=1536,
                min_vram_mb=512,
                requires_gpu=False,
                min_cpu_cores=2,
                min_cpu_frequency_ghz=2.0,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "zh", "es", "fr", "de", "it", "pt", "ru", "ja", "ko"],
            accuracy_metrics={"accuracy": 93.0, "speed": 80.0},
            license="Apache 2.0",
            version="3.0"
        )
        
        return ocr_models
    
    def _create_translation_models(self) -> Dict[str, AIModelInfo]:
        """Create translation model definitions.
        
        Returns:
            Dictionary of translation models
        """
        translation_models = {}
        
        # MarianMT English to Spanish
        translation_models["marian_en_es"] = AIModelInfo(
            model_id="marian_en_es",
            name="MarianMT English-Spanish",
            description="High-quality neural machine translation from English to Spanish",
            model_type=ModelType.TRANSLATION,
            size_mb=280,
            download_url="https://huggingface.co/Helsinki-NLP/opus-mt-en-es/resolve/main/pytorch_model.bin",
            checksum="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
            signature="helsinki_nlp",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=2048,
                min_vram_mb=1024,
                requires_gpu=False,
                min_cpu_cores=2,
                min_cpu_frequency_ghz=2.0,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "es"],
            accuracy_metrics={"bleu_score": 28.5, "speed": 75.0},
            license="Apache 2.0",
            version="1.0"
        )
        
        # MarianMT English to French
        translation_models["marian_en_fr"] = AIModelInfo(
            model_id="marian_en_fr",
            name="MarianMT English-French",
            description="High-quality neural machine translation from English to French",
            model_type=ModelType.TRANSLATION,
            size_mb=285,
            download_url="https://huggingface.co/Helsinki-NLP/opus-mt-en-fr/resolve/main/pytorch_model.bin",
            checksum="e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
            signature="helsinki_nlp",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=2048,
                min_vram_mb=1024,
                requires_gpu=False,
                min_cpu_cores=2,
                min_cpu_frequency_ghz=2.0,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "fr"],
            accuracy_metrics={"bleu_score": 30.2, "speed": 75.0},
            license="Apache 2.0",
            version="1.0"
        )
        
        # MarianMT Multilingual
        translation_models["marian_multi"] = AIModelInfo(
            model_id="marian_multi",
            name="MarianMT Multilingual",
            description="Multi-language neural translation supporting major European languages",
            model_type=ModelType.TRANSLATION,
            size_mb=450,
            download_url="https://huggingface.co/Helsinki-NLP/opus-mt-mul-en/resolve/main/pytorch_model.bin",
            checksum="f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7",
            signature="helsinki_nlp",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=3072,
                min_vram_mb=1536,
                requires_gpu=False,
                min_cpu_cores=4,
                min_cpu_frequency_ghz=2.5,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "es", "fr", "de", "it", "pt", "nl", "sv", "da", "no"],
            accuracy_metrics={"bleu_score": 26.8, "speed": 65.0},
            license="Apache 2.0",
            version="1.0"
        )
        
        # Fast Translation Model
        translation_models["fast_translate"] = AIModelInfo(
            model_id="fast_translate",
            name="Fast Translation Model",
            description="Lightweight translation model optimized for speed over accuracy",
            model_type=ModelType.TRANSLATION,
            size_mb=95,
            download_url="https://example.com/models/fast_translate.bin",
            checksum="a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8",
            signature="custom_model",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=1024,
                min_cpu_cores=1,
                min_cpu_frequency_ghz=1.5,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["en", "es", "fr", "de"],
            accuracy_metrics={"bleu_score": 22.0, "speed": 95.0},
            license="MIT",
            version="1.0"
        )
        
        return translation_models
    
    def _create_preprocessing_models(self) -> Dict[str, AIModelInfo]:
        """Create preprocessing model definitions.
        
        Returns:
            Dictionary of preprocessing models
        """
        preprocessing_models = {}
        
        # Text Detection Model
        preprocessing_models["text_detector"] = AIModelInfo(
            model_id="text_detector",
            name="Text Detection Model",
            description="Neural network for detecting text regions in images",
            model_type=ModelType.PREPROCESSING,
            size_mb=65,
            download_url="https://example.com/models/text_detector.onnx",
            checksum="b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9",
            signature="custom_model",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=1024,
                min_vram_mb=512,
                requires_gpu=False,
                min_cpu_cores=2,
                min_cpu_frequency_ghz=2.0,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["universal"],
            accuracy_metrics={"precision": 88.0, "recall": 85.0},
            license="MIT",
            version="1.0"
        )
        
        # Image Enhancement Model
        preprocessing_models["image_enhancer"] = AIModelInfo(
            model_id="image_enhancer",
            name="Image Enhancement Model",
            description="AI-powered image enhancement for better OCR accuracy",
            model_type=ModelType.PREPROCESSING,
            size_mb=45,
            download_url="https://example.com/models/image_enhancer.onnx",
            checksum="c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0",
            signature="custom_model",
            hardware_requirements=HardwareRequirements(
                min_ram_mb=768,
                min_vram_mb=256,
                requires_gpu=False,
                min_cpu_cores=1,
                min_cpu_frequency_ghz=1.5,
                supported_os=["Windows", "Linux", "Darwin"]
            ),
            supported_languages=["universal"],
            accuracy_metrics={"enhancement_quality": 92.0, "speed": 88.0},
            license="MIT",
            version="1.0"
        )
        
        return preprocessing_models


class ModelRecommendationEngine:
    """Engine for recommending optimal models based on hardware and requirements."""
    
    def __init__(self, repository: ModelRepository, 
                 compatibility_engine: CompatibilityEngine,
                 logger: Optional[ILogger] = None):
        """Initialize recommendation engine.
        
        Args:
            repository: Model repository
            compatibility_engine: Hardware compatibility engine
            logger: Optional logger
        """
        self.repository = repository
        self.compatibility_engine = compatibility_engine
        self.logger = logger or logging.getLogger(__name__)
    
    def recommend_models_for_task(self, model_type: ModelType, 
                                 language_pair: Optional[tuple] = None,
                                 performance_priority: str = "balanced") -> List[tuple]:
        """Recommend models for a specific task.
        
        Args:
            model_type: Type of model needed
            language_pair: Optional (source, target) language pair
            performance_priority: "speed", "accuracy", or "balanced"
            
        Returns:
            List of (model, compatibility_result, recommendation_score) tuples
        """
        try:
            # Get available models of the requested type
            available_models = self.repository.get_available_models(model_type)
            
            # Filter by language support if specified
            if language_pair:
                source_lang, target_lang = language_pair
                filtered_models = []
                for model in available_models:
                    if (source_lang in model.supported_languages and 
                        target_lang in model.supported_languages):
                        filtered_models.append(model)
                available_models = filtered_models
            
            # Get compatibility assessments
            recommendations = []
            for model in available_models:
                compatibility = self.compatibility_engine.check_model_compatibility(model)
                
                if compatibility.is_compatible:
                    # Calculate recommendation score
                    score = self._calculate_recommendation_score(
                        model, compatibility, performance_priority
                    )
                    recommendations.append((model, compatibility, score))
            
            # Sort by recommendation score (descending)
            recommendations.sort(key=lambda x: x[2], reverse=True)
            
            self.logger.info(f"Generated {len(recommendations)} recommendations for {model_type.value}")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []
    
    def get_best_model_for_hardware(self, model_type: ModelType) -> Optional[AIModelInfo]:
        """Get the best model for current hardware.
        
        Args:
            model_type: Type of model needed
            
        Returns:
            Best compatible model or None
        """
        recommendations = self.recommend_models_for_task(model_type)
        
        if recommendations:
            return recommendations[0][0]  # Return the top-rated model
        
        return None
    
    def _calculate_recommendation_score(self, model: AIModelInfo, 
                                     compatibility: CompatibilityResult,
                                     performance_priority: str) -> float:
        """Calculate recommendation score for a model.
        
        Args:
            model: AI model
            compatibility: Compatibility assessment
            performance_priority: Performance priority setting
            
        Returns:
            Recommendation score (0.0 to 1.0)
        """
        try:
            # Base score from compatibility
            base_score = compatibility.compatibility_score
            
            # Accuracy factor
            accuracy = model.accuracy_metrics.get("accuracy", 
                      model.accuracy_metrics.get("bleu_score", 50.0))
            accuracy_factor = accuracy / 100.0
            
            # Speed factor (inverse of size for approximation)
            speed_factor = max(0.1, 1.0 - (model.size_mb - 50) / 500.0)
            
            # Performance estimate factor
            performance_factor = 1.0
            if compatibility.performance_estimate:
                perf = compatibility.performance_estimate
                fps_factor = min(1.0, perf.get("estimated_fps", 30) / 60.0)
                latency_factor = max(0.1, 1.0 - perf.get("estimated_latency_ms", 100) / 500.0)
                performance_factor = (fps_factor + latency_factor) / 2.0
            
            # Weight factors based on priority
            if performance_priority == "speed":
                weights = {"base": 0.3, "accuracy": 0.2, "speed": 0.3, "performance": 0.2}
            elif performance_priority == "accuracy":
                weights = {"base": 0.3, "accuracy": 0.4, "speed": 0.1, "performance": 0.2}
            else:  # balanced
                weights = {"base": 0.3, "accuracy": 0.25, "speed": 0.25, "performance": 0.2}
            
            # Calculate weighted score
            score = (base_score * weights["base"] +
                    accuracy_factor * weights["accuracy"] +
                    speed_factor * weights["speed"] +
                    performance_factor * weights["performance"])
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating recommendation score: {e}")
            return 0.0