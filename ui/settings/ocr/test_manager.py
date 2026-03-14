"""
OCR Test Manager
Handles OCR testing functionality including quick tests and full test windows.
"""

from PyQt6.QtWidgets import QMessageBox

from app.localization import tr


class OCRTestManager:
    """Manages OCR testing operations."""
    
    def __init__(self, parent=None):
        """Initialize the test manager."""
        self.parent = parent
    
    def _get_pipeline(self):
        """Get the pipeline from the main window."""
        # Use window() method to get the top-level window (StyleTestWindow)
        # This works even when the widget is nested in tab containers
        if hasattr(self.parent, 'window') and callable(self.parent.window):
            main_window = self.parent.window()
            if hasattr(main_window, 'pipeline'):
                return main_window.pipeline
        
        # Fallback: try direct parent chain
        if hasattr(self.parent, 'parent') and callable(self.parent.parent):
            potential_window = self.parent.parent()
            if hasattr(potential_window, 'pipeline'):
                return potential_window.pipeline
        
        return None
    
    def run_quick_test(self):
        """Run a quick OCR test with real OCR engine."""
        try:
            # Get the main window's pipeline
            pipeline = self._get_pipeline()
            
            if not pipeline:
                QMessageBox.warning(
                    self.parent,
                    tr("ocr_test_pipeline_not_ready"),
                    tr("ocr_test_pipeline_not_initialized")
                )
                return
            
            # Get current OCR engine
            if hasattr(pipeline, 'ocr_layer') and pipeline.ocr_layer:
                current_engine = pipeline.get_current_ocr_engine()
                available_engines = pipeline.get_available_ocr_engines()
                
                # Get engine status
                engine_status = tr("ocr_test_status_ready") if current_engine in available_engines else tr("ocr_test_status_not_available")
                
                # Get language info
                if hasattr(self.parent, 'config_manager'):
                    languages = self.parent.config_manager.get_setting('ocr.languages', [])
                    language_str = ", ".join(languages[:3])
                    if len(languages) > 3:
                        language_str += tr("ocr_test_langs_more").format(count=len(languages)-3)
                else:
                    language_str = tr("ocr_test_unknown")
                
                # Get performance profile
                if hasattr(self.parent, 'config_manager'):
                    parallel = self.parent.config_manager.get_setting('performance.enable_parallel_ocr', True)
                    confidence = self.parent.config_manager.get_setting('ocr.confidence_threshold', 0.5)
                    perf_str = tr("ocr_test_perf_parallel") if parallel else tr("ocr_test_perf_standard")
                else:
                    perf_str = tr("ocr_test_perf_standard")
                    confidence = 0.5
                
                result_msg = tr("ocr_test_quick_results").format(
                    current_engine=current_engine.upper(),
                    engine_status=engine_status,
                    num_engines=len(available_engines),
                    engine_list=', '.join(available_engines),
                    language_str=language_str,
                    confidence=f"{confidence:.0%}",
                    perf_str=perf_str
                )
                
                QMessageBox.information(
                    self.parent,
                    tr("ocr_test_quick_test_title"),
                    result_msg
                )
            else:
                QMessageBox.warning(
                    self.parent,
                    tr("ocr_test_not_available"),
                    tr("ocr_test_not_available_msg")
                )
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                tr("ocr_test_test_failed"),
                tr("ocr_test_failed_msg").format(error=str(e))
            )
    
