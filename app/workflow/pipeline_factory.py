"""
Pipeline Factory

Factory for creating pipeline instances using modern architecture.
"""

import logging
from typing import Optional, Literal

# Modern pipeline imports
from .runtime_pipeline_optimized import OptimizedRuntimePipeline, OptimizedRuntimePipelineConfig
from .runtime_pipeline import RuntimePipeline, RuntimePipelineConfig
from .runtime_pipeline_subprocess import SubprocessRuntimePipeline, SubprocessPipelineConfig

# Type aliases for compatibility
PipelineType = Literal["runtime", "optimized", "subprocess"]


class PipelineFactory:
    """Factory for creating pipeline instances."""
    
    def __init__(self, config_manager=None):
        """Initialize pipeline factory."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
    
    def create_pipeline(self,
                       pipeline_type: PipelineType,
                       capture_layer,
                       preprocessing_layer,
                       ocr_layer,
                       translation_layer,
                       overlay_renderer,
                       config=None):
        """
        Create a pipeline instance using modern architecture.
        
        Args:
            pipeline_type: "runtime", "optimized", or "subprocess"
            capture_layer: ICaptureLayer implementation
            preprocessing_layer: IPreprocessingLayer implementation
            ocr_layer: IOCRLayer implementation
            translation_layer: ITranslationLayer implementation
            overlay_renderer: IOverlayRenderer implementation
            config: Pipeline configuration (type depends on pipeline_type)
            
        Returns:
            Pipeline instance (RuntimePipeline, OptimizedRuntimePipeline, or SubprocessRuntimePipeline)
        """
        if pipeline_type == "runtime":
            return self._create_runtime_pipeline(
                capture_layer,
                preprocessing_layer,
                ocr_layer,
                translation_layer,
                overlay_renderer,
                config
            )
        elif pipeline_type == "optimized":
            return self._create_optimized_pipeline(
                capture_layer,
                preprocessing_layer,
                ocr_layer,
                translation_layer,
                overlay_renderer,
                config
            )
        elif pipeline_type == "subprocess":
            return self._create_subprocess_pipeline(
                capture_layer,
                preprocessing_layer,
                ocr_layer,
                translation_layer,
                overlay_renderer,
                config
            )
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
    
    def _create_runtime_pipeline(self,
                                capture_layer,
                                preprocessing_layer,
                                ocr_layer,
                                translation_layer,
                                overlay_renderer,
                                config):
        """Create basic runtime pipeline."""
        self.logger.info("Creating RUNTIME pipeline")
        
        if config is None:
            config = RuntimePipelineConfig()
        
        return RuntimePipeline(
            capture_layer=capture_layer,
            preprocessing_layer=preprocessing_layer,
            ocr_layer=ocr_layer,
            translation_layer=translation_layer,
            overlay_renderer=overlay_renderer,
            config=config,
            config_manager=self.config_manager
        )
    
    def _create_optimized_pipeline(self,
                                  capture_layer,
                                  preprocessing_layer,
                                  ocr_layer,
                                  translation_layer,
                                  overlay_renderer,
                                  config):
        """Create optimized runtime pipeline with plugin support."""
        self.logger.info("Creating OPTIMIZED RUNTIME pipeline")
        self.logger.info("  ✓ Plugin support")
        self.logger.info("  ✓ Frame skip optimization")
        self.logger.info("  ✓ Translation cache")
        self.logger.info("  ✓ Batch processing")
        
        if config is None:
            config = OptimizedRuntimePipelineConfig()
        
        # Create cache manager with persistent dictionary
        from .managers.pipeline_cache_manager import PipelineCacheManager
        cache_manager = PipelineCacheManager(enable_persistent_dictionary=True, config_manager=self.config_manager)
        
        return OptimizedRuntimePipeline(
            capture_layer=capture_layer,
            ocr_layer=ocr_layer,
            translation_layer=translation_layer,
            config=config,
            overlay_system=overlay_renderer,
            config_manager=self.config_manager,
            cache_manager=cache_manager  # NEW: Pass cache manager with persistent dictionary
        )
    
    def _create_subprocess_pipeline(self,
                                   capture_layer,
                                   preprocessing_layer,
                                   ocr_layer,
                                   translation_layer,
                                   overlay_renderer,
                                   config):
        """Create subprocess-isolated runtime pipeline for maximum stability."""
        self.logger.info("Creating SUBPROCESS RUNTIME pipeline")
        self.logger.info("  ✓ Subprocess isolation")
        self.logger.info("  ✓ Maximum stability")
        self.logger.info("  ✓ Crash recovery")
        
        if config is None:
            config = SubprocessPipelineConfig()
        
        return SubprocessRuntimePipeline(
            capture_layer=capture_layer,
            preprocessing_layer=preprocessing_layer,
            ocr_layer=ocr_layer,
            translation_layer=translation_layer,
            overlay_renderer=overlay_renderer,
            config=config,
            config_manager=self.config_manager
        )


# Global factory instance
_factory = PipelineFactory()


def create_pipeline(pipeline_type: PipelineType = "optimized", **kwargs):
    """
    Convenience function to create a pipeline.
    
    Args:
        pipeline_type: "runtime", "optimized", or "subprocess" (default: "optimized")
        **kwargs: Pipeline arguments
        
    Returns:
        Pipeline instance
    """
    return _factory.create_pipeline(pipeline_type, **kwargs)
