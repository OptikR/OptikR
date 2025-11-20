"""
Translation Stage

Translates detected text blocks to target language.
"""

from typing import Any, List
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig


class TranslationStage(PipelineStage):
    """
    Translates text blocks to target language.
    
    Input: List of TextBlock objects
    Output: List of Translation objects
    """
    
    def __init__(self, translation_layer=None, source_lang="en", target_lang="de", config_manager=None, cache_manager=None):
        """
        Initialize translation stage.
        
        Args:
            translation_layer: ITranslationLayer implementation
            source_lang: Source language code
            target_lang: Target language code
            config_manager: Configuration manager for reading settings
            cache_manager: PipelineCacheManager for persistent dictionary
        """
        config = StageConfig(
            name="translation",
            enabled=True,
            required=True,
            timeout=3.0,
            dependencies=["ocr"],  # Can work with or without validation
            metadata={
                "description": "Translates text to target language",
                "input": "List[TextBlock]",
                "output": "List[Translation]"
            }
        )
        super().__init__(config)
        
        self.translation_layer = translation_layer
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.config_manager = config_manager
        self.cache_manager = cache_manager  # NEW: PipelineCacheManager with persistent dictionary
        self.logger = logging.getLogger(__name__)
    
    def _get_translation_options(self) -> dict:
        """
        Get translation options from config manager.
        
        Returns:
            Dictionary of translation options
        """
        options = {}
        
        if self.config_manager:
            # Read advanced settings from config
            options['preserve_formatting'] = self.config_manager.get_setting(
                'translation.preserve_formatting', True
            )
            options['use_cache'] = self.config_manager.get_setting(
                'translation.cache_enabled', True
            )
            
            # Quality level
            quality_level = self.config_manager.get_setting('translation.quality_level', 50)
            if quality_level >= 75:
                options['quality'] = 'high'
            elif quality_level >= 25:
                options['quality'] = 'medium'
            else:
                options['quality'] = 'low'
        else:
            # Default options
            options['preserve_formatting'] = True
            options['use_cache'] = True
            options['quality'] = 'medium'
        
        return options
    
    def process(self, input_data: Any) -> Any:
        """
        Translate text blocks.
        
        Args:
            input_data: List of TextBlock objects
            
        Returns:
            List[Translation]: Translated text blocks
        """
        if not self.translation_layer:
            raise RuntimeError("Translation layer not initialized")
        
        if not input_data:
            self.logger.debug("No text blocks to translate")
            return []
        
        text_blocks = input_data
        
        # Get translation options from config
        translation_options = self._get_translation_options()
        
        # Check if batch translation is enabled
        batch_enabled = False
        if self.config_manager:
            batch_enabled = self.config_manager.get_setting('translation.batch_translation', True)
        
        # Translate blocks
        translations = []
        
        if batch_enabled and len(text_blocks) > 1:
            # Use batch translation for better performance
            try:
                texts = [block.text for block in text_blocks]
                batch_result = self.translation_layer.translate_batch(
                    texts=texts,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    options=translation_options
                )
                
                if batch_result and batch_result.translations:
                    translations = batch_result.translations
                    self.logger.debug(f"Batch translated {len(translations)} blocks")
                else:
                    self.logger.warning("Batch translation returned no results, falling back to individual")
                    batch_enabled = False  # Fall back to individual translation
                    
            except Exception as e:
                self.logger.warning(f"Batch translation failed: {e}, falling back to individual")
                batch_enabled = False  # Fall back to individual translation
        
        # Individual translation (if batch disabled or failed)
        if not batch_enabled or not translations:
            for block in text_blocks:
                try:
                    # NEW: Check PipelineCacheManager first (includes persistent dictionary)
                    cached_translation = None
                    if self.cache_manager:
                        cached_translation = self.cache_manager.get_cached_translation(
                            block.text, self.source_lang, self.target_lang
                        )
                    
                    if cached_translation:
                        # Use cached translation (from memory or persistent dictionary)
                        translation = cached_translation
                        self.logger.debug(f"Cache hit: '{block.text}' -> '{translation}'")
                    else:
                        # Translate with options
                        translation = self.translation_layer.translate(
                            text=block.text,
                            source_lang=self.source_lang,
                            target_lang=self.target_lang,
                            options=translation_options
                        )
                        
                        # Save to cache (memory + persistent dictionary)
                        if self.cache_manager and translation:
                            self.cache_manager.cache_translation(
                                text=block.text,
                                source_lang=self.source_lang,
                                target_lang=self.target_lang,
                                translation=translation,
                                confidence=0.9,  # Default confidence (actual confidence from engine if available)
                                save_to_dictionary=True
                            )
                    
                    if translation:
                        translations.append(translation)
                        
                except Exception as e:
                    self.logger.error(f"Translation failed for '{block.text}': {e}")
                    # Continue with other blocks
        
        self.logger.debug(
            f"Translated {len(translations)}/{len(text_blocks)} blocks"
        )
        
        return translations
