"""
Translation Cache Manager
Handles translation cache operations and statistics.
"""

import logging

from PyQt6.QtWidgets import QMessageBox
from app.localization import tr

logger = logging.getLogger(__name__)


class TranslationCacheManager:
    """Manages translation cache operations."""
    
    def __init__(self, parent=None, pipeline=None):
        """Initialize the cache manager."""
        self.parent = parent
        self.pipeline = pipeline
    
    def clear_cache(self) -> bool:
        """
        Clear translation cache with user confirmation.
        
        Returns:
            bool: True if cache was cleared, False if cancelled
        """
        reply = QMessageBox.question(
            self.parent,
            tr("trans_cache_clear_title"),
            tr("trans_cache_clear_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear the actual translation_cache plugin
            cleared = False
            try:
                if self.pipeline:
                    # Clear translation_cache plugin
                    if hasattr(self.pipeline, 'translation_cache') and self.pipeline.translation_cache:
                        logger.info("Clearing translation_cache plugin...")
                        self.pipeline.translation_cache.clear()
                        logger.info("Translation cache plugin cleared")
                        cleared = True
                    
                    # Clear cache_manager
                    if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                        logger.info("Clearing cache_manager...")
                        self.pipeline.cache_manager.clear_all(clear_dictionary=False)
                        logger.info("Cache manager cleared")
                        cleared = True
                
                if cleared:
                    QMessageBox.information(
                        self.parent,
                        tr("trans_cache_cleared_title"),
                        tr("trans_cache_cleared_msg")
                    )
                else:
                    QMessageBox.warning(
                        self.parent,
                        tr("trans_cache_clear_warning_title"),
                        tr("trans_cache_no_active_msg")
                    )
            except Exception as e:
                logger.exception("Cache clear error: %s", e)
                QMessageBox.warning(
                    self.parent,
                    tr("trans_cache_clear_failed_title"),
                    f"{tr('trans_cache_clear_failed_msg')}\n\n{str(e)}"
                )
                return False
            
            return True
        return False
