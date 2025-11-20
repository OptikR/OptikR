"""
Runtime Pipeline (Subprocess-Based)

The main translation loop using subprocess-based stages.
All stages run as isolated subprocesses for crash safety.

4 Steps (repeats at 10 FPS):
1. Capture frame (subprocess)
2. Run OCR (subprocess)
3. Translate (subprocess)
4. Display overlay (main process - Qt requirement)

Author: Niklas Verhasselt
Date: 2025-11-12
"""

import time
import threading
import logging
from typing import Optional, Callable
from dataclasses import dataclass

from .subprocess_manager import SubprocessManager

try:
    from app.models import CaptureRegion
except ImportError:
    from models import CaptureRegion


@dataclass
class SubprocessPipelineConfig:
    """Configuration for subprocess-based runtime pipeline."""
    capture_region: Optional[CaptureRegion] = None
    fps: int = 10
    source_language: str = "en"
    target_language: str = "de"
    
    # Subprocess configurations
    capture_config: dict = None
    ocr_config: dict = None
    translation_config: dict = None
    
    def __post_init__(self):
        if self.capture_config is None:
            self.capture_config = {}
        if self.ocr_config is None:
            self.ocr_config = {'language': self.source_language}
        if self.translation_config is None:
            self.translation_config = {
                'source_language': self.source_language,
                'target_language': self.target_language
            }


class SubprocessRuntimePipeline:
    """
    Runtime Pipeline using subprocesses for all stages.
    
    Benefits:
    - Crash isolation (subprocess crashes don't kill app)
    - Parallel processing (stages can overlap)
    - Hot-reload (restart subprocess without restarting app)
    - User extensibility (custom plugins)
    """
    
    def __init__(self, config: SubprocessPipelineConfig):
        """
        Initialize subprocess-based runtime pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Subprocess manager
        self.subprocess_manager = SubprocessManager()
        
        # State
        self.is_running = False
        self.pipeline_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.on_translation: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Stats
        self.frames_processed = 0
        self.frames_skipped = 0
        self.translations_count = 0
        self.errors_count = 0
        
        self.logger.info("Subprocess-based runtime pipeline initialized")
    
    def start(self) -> bool:
        """Start the pipeline."""
        if self.is_running:
            self.logger.warning("Pipeline already running")
            return False
        
        if not self.config.capture_region:
            self.logger.error("No capture region set")
            return False
        
        self.logger.info("Starting subprocess-based pipeline...")
        
        # Start all subprocesses
        subprocess_config = {
            'capture': self.config.capture_config,
            'ocr': self.config.ocr_config,
            'translation': self.config.translation_config
        }
        
        if not self.subprocess_manager.start_all(subprocess_config):
            self.logger.error("Failed to start subprocesses")
            return False
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start pipeline thread
        self.pipeline_thread = threading.Thread(
            target=self._pipeline_loop,
            name="SubprocessPipeline",
            daemon=True
        )
        self.pipeline_thread.start()
        
        self.logger.info("Subprocess-based pipeline started")
        return True
    
    def stop(self):
        """Stop the pipeline."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping subprocess-based pipeline...")
        self.is_running = False
        self.stop_event.set()
        
        # Wait for pipeline thread
        if self.pipeline_thread and self.pipeline_thread.is_alive():
            self.pipeline_thread.join(timeout=2.0)
        
        # Stop all subprocesses
        self.subprocess_manager.stop_all()
        
        self.logger.info(f"Pipeline stopped. Processed {self.frames_processed} frames, {self.translations_count} translations")
    
    def _pipeline_loop(self):
        """Main pipeline loop using subprocesses."""
        try:
            frame_interval = 1.0 / self.config.fps
            last_frame_time = 0.0
            
            print(f"[SUBPROCESS PIPELINE] Started (FPS: {self.config.fps})")
            print(f"[SUBPROCESS PIPELINE] Capture region: {self.config.capture_region}")
            
            while self.is_running and not self.stop_event.is_set():
                try:
                    # FPS limiting
                    current_time = time.time()
                    if current_time - last_frame_time < frame_interval:
                        time.sleep(0.01)
                        continue
                    
                    last_frame_time = current_time
                    
                    # Check subprocess health
                    if not self.subprocess_manager.are_all_running():
                        print("[SUBPROCESS PIPELINE] Subprocess health check failed, attempting restart...")
                        self.subprocess_manager.restart_crashed()
                        time.sleep(0.5)
                        continue
                    
                    # Step 1: Capture frame (subprocess)
                    frame_result = self._capture_frame()
                    if not frame_result:
                        continue
                    
                    self.frames_processed += 1
                    
                    # Step 2: OCR (subprocess)
                    ocr_result = self._run_ocr(frame_result)
                    if not ocr_result or not ocr_result.get('text_blocks'):
                        continue
                    
                    # Step 3: Translate (subprocess)
                    translation_result = self._translate(ocr_result)
                    if not translation_result or not translation_result.get('translations'):
                        continue
                    
                    self.translations_count += len(translation_result['translations'])
                    
                    # Step 4: Notify callback (overlay in main process)
                    if self.on_translation:
                        try:
                            print(f"[SUBPROCESS PIPELINE] Calling overlay callback with {len(translation_result['translations'])} translations...")
                            self.on_translation(translation_result['translations'])
                            print(f"[SUBPROCESS PIPELINE] Overlay callback completed")
                        except Exception as e:
                            self.logger.error(f"Error in translation callback: {e}")
                            print(f"[SUBPROCESS PIPELINE] Overlay callback error: {e}")
                    
                    # Log progress
                    if self.frames_processed % 30 == 1:
                        self.logger.info(f"Processed {self.frames_processed} frames")
                    
                except Exception as e:
                    self.logger.error(f"Error in pipeline loop: {e}")
                    self.errors_count += 1
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.1)
            
            print("[SUBPROCESS PIPELINE] Loop stopped")
            
        except Exception as e:
            self.logger.error(f"FATAL: Pipeline loop crashed: {e}")
            import traceback
            traceback.print_exc()
    
    def _capture_frame(self) -> Optional[dict]:
        """Capture frame using subprocess."""
        try:
            result = self.subprocess_manager.capture_subprocess.process_data({
                'region': self.config.capture_region
            }, timeout=2.0)
            
            if result:
                print(f"[SUBPROCESS PIPELINE] Captured frame: {result.get('shape')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Capture failed: {e}")
            return None
    
    def _run_ocr(self, frame_result: dict) -> Optional[dict]:
        """Run OCR using subprocess."""
        try:
            result = self.subprocess_manager.ocr_subprocess.process_data({
                'frame': frame_result['frame'],
                'language': self.config.source_language
            }, timeout=5.0)
            
            if result:
                count = result.get('count', 0)
                print(f"[SUBPROCESS PIPELINE] OCR found {count} text blocks")
                
                # Log first few blocks
                for i, block in enumerate(result.get('text_blocks', [])[:3], 1):
                    text = block.text if hasattr(block, 'text') else str(block)
                    print(f"[SUBPROCESS PIPELINE] OCR Block {i}: '{text[:50]}'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"OCR failed: {e}")
            return None
    
    def _translate(self, ocr_result: dict) -> Optional[dict]:
        """Translate using subprocess."""
        try:
            result = self.subprocess_manager.translation_subprocess.process_data({
                'text_blocks': ocr_result['text_blocks'],
                'source_language': self.config.source_language,
                'target_language': self.config.target_language
            }, timeout=10.0)
            
            if result:
                count = result.get('count', 0)
                print(f"[SUBPROCESS PIPELINE] Translated {count} text blocks")
                
                # Log first few translations
                for i, trans in enumerate(result.get('translations', [])[:3], 1):
                    orig = trans.original_text if hasattr(trans, 'original_text') else ''
                    translated = trans.translated_text if hasattr(trans, 'translated_text') else ''
                    print(f"[SUBPROCESS PIPELINE] Translation {i}: '{orig[:20]}' -> '{translated[:20]}'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return None
    
    def get_metrics(self) -> dict:
        """Get pipeline metrics."""
        subprocess_metrics = self.subprocess_manager.get_all_metrics()
        
        return {
            'pipeline': {
                'running': self.is_running,
                'frames_processed': self.frames_processed,
                'frames_skipped': self.frames_skipped,
                'translations_count': self.translations_count,
                'errors_count': self.errors_count,
                'fps': self.config.fps
            },
            'subprocesses': subprocess_metrics
        }


def create_subprocess_pipeline(config: SubprocessPipelineConfig) -> SubprocessRuntimePipeline:
    """
    Factory function to create subprocess-based runtime pipeline.
    
    Args:
        config: Pipeline configuration
        
    Returns:
        SubprocessRuntimePipeline instance
    """
    return SubprocessRuntimePipeline(config)
