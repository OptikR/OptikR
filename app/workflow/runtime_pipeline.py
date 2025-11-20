"""
Runtime Translation Pipeline

The main translation loop that runs continuously when active.
Processes frames in real-time and displays translation overlays.

4 Steps (repeats at 10 FPS):
1. Capture frame from screen
2. Run OCR to find text
3. Translate text
4. Display overlay

Author: Niklas Verhasselt
Date: 2025-11-12
"""

import time
import threading
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass

try:
    from app.models import Frame, CaptureRegion, Rectangle
    from app.interfaces import CaptureSource
except ImportError:
    from models import Frame, CaptureRegion, Rectangle
    from interfaces import CaptureSource


@dataclass
class RuntimePipelineConfig:
    """Configuration for runtime translation pipeline."""
    capture_region: Optional[CaptureRegion] = None
    fps: int = 10  # Lower FPS for stability
    source_language: str = "ja"
    target_language: str = "de"


class RuntimePipeline:
    """
    Runtime Translation Pipeline - Runs continuously when active.
    
    Processes frames in real-time:
    - Capture from screen region
    - OCR to find text
    - Translate text
    - Display overlays
    """
    
    def __init__(self, capture_layer, ocr_layer, translation_layer, config: RuntimePipelineConfig):
        """
        Initialize runtime translation pipeline.
        
        Args:
            capture_layer: Screen capture implementation
            ocr_layer: OCR engine implementation
            translation_layer: Translation engine implementation
            config: Runtime pipeline configuration
        """
        self.capture_layer = capture_layer
        self.ocr_layer = ocr_layer
        self.translation_layer = translation_layer
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        
        # State
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.on_translation: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Stats
        self.frames_processed = 0
        self.translations_count = 0
        
        self.logger.info("Runtime pipeline initialized")
    
    def start(self) -> bool:
        """Start the pipeline."""
        if self.is_running:
            self.logger.warning("Pipeline already running")
            return False
        
        if not self.config.capture_region:
            self.logger.error("No capture region set")
            return False
        
        self.logger.info("Starting minimal pipeline...")
        self.logger.info(f"Capture region: {self.config.capture_region}")
        
        # CRITICAL: Pre-load translation models in main thread BEFORE starting background thread
        # This prevents transformers library crashes when loading models in background threads
        try:
            self.logger.info(f"Pre-loading translation models for {self.config.source_language}->{self.config.target_language}...")
            print(f"[RUNTIME] Pre-loading translation models...")
            
            if hasattr(self.translation_layer, 'preload_models'):
                success = self.translation_layer.preload_models(
                    self.config.source_language,
                    self.config.target_language
                )
                if not success:
                    self.logger.warning("Failed to pre-load models, continuing anyway...")
                    print(f"[RUNTIME] WARNING: Model pre-loading failed, may crash in background thread")
            else:
                self.logger.info("Translation layer doesn't support pre-loading")
                print(f"[RUNTIME] Translation layer doesn't support pre-loading")
        except Exception as e:
            self.logger.error(f"Error pre-loading models: {e}")
            print(f"[RUNTIME] ERROR pre-loading models: {e}")
            import traceback
            traceback.print_exc()
            # Continue anyway, but warn user
            print(f"[RUNTIME] WARNING: Continuing without pre-loaded models, may crash")
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start capture thread
        self.capture_thread = threading.Thread(
            target=self._pipeline_loop,
            name="MinimalPipeline",
            daemon=True
        )
        self.capture_thread.start()
        
        self.logger.info("Runtime pipeline thread started")
        
        # Give thread a moment to start
        import time
        time.sleep(0.1)
        
        if self.capture_thread.is_alive():
            self.logger.info("Pipeline thread is running")
        else:
            self.logger.error("Pipeline thread died immediately!")
        
        return True
    
    def stop(self):
        """Stop the pipeline."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping runtime pipeline...")
        self.is_running = False
        self.stop_event.set()
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        self.logger.info(f"Runtime pipeline stopped. Processed {self.frames_processed} frames, {self.translations_count} translations")
    
    def _pipeline_loop(self):
        """Main pipeline loop - simple and straightforward."""
        try:
            frame_interval = 1.0 / self.config.fps
            last_frame_time = 0.0
            
            self.logger.info(f"Pipeline loop started (FPS: {self.config.fps})")
            self.logger.info(f"Capture region: {self.config.capture_region}")
            print(f"[MINIMAL] Pipeline loop started (FPS: {self.config.fps})")
            print(f"[MINIMAL] Capture region: {self.config.capture_region}")
            
            while self.is_running and not self.stop_event.is_set():
                try:
                    # FPS limiting
                    current_time = time.time()
                    if current_time - last_frame_time < frame_interval:
                        time.sleep(0.01)
                        continue
                    
                    last_frame_time = current_time
                    
                    # Step 1: Capture frame
                    frame = self._capture_frame()
                    if not frame:
                        continue
                    
                    self.frames_processed += 1
                    
                    # Log progress
                    if self.frames_processed % 30 == 1:
                        self.logger.info(f"[MINIMAL] Processed {self.frames_processed} frames")
                    
                    # Step 2: OCR
                    text_blocks = self._run_ocr(frame)
                    if not text_blocks:
                        continue
                    
                    # Step 3: Translate
                    translations = self._translate(text_blocks)
                    if not translations:
                        continue
                    
                    self.translations_count += len(translations)
                    
                    # Step 4: Notify callback (CRITICAL: wrap defensively to prevent crashes)
                    if self.on_translation:
                        try:
                            print(f"[MINIMAL] Calling overlay callback with {len(translations)} translations...")
                            self.on_translation(translations)
                            print(f"[MINIMAL] Overlay callback completed successfully")
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            self.logger.error(f"CRASH in translation callback: {e}")
                            print(f"[MINIMAL] CRASH in overlay callback: {e}")
                            import traceback
                            traceback.print_exc()
                            # Continue pipeline even if overlay crashes
                            print("[MINIMAL] Continuing pipeline despite overlay crash...")
                    
                except Exception as e:
                    self.logger.error(f"Error in pipeline loop: {e}")
                    import traceback
                    traceback.print_exc()
                    if self.on_error:
                        try:
                            self.on_error(str(e))
                        except:
                            pass
                    time.sleep(0.1)
            
            self.logger.info("Pipeline loop stopped")
        except Exception as e:
            self.logger.error(f"FATAL: Pipeline loop crashed: {e}")
            import traceback
            traceback.print_exc()
    
    def _capture_frame(self) -> Optional[Frame]:
        """Capture a frame - simple and direct."""
        try:
            frame = self.capture_layer.capture_frame(
                CaptureSource.CUSTOM_REGION,
                self.config.capture_region
            )
            if frame:
                print(f"[MINIMAL] Captured frame: {frame.data.shape}")
            else:
                print("[MINIMAL] Capture returned None")
            return frame
        except Exception as e:
            self.logger.error(f"Capture failed: {e}")
            print(f"[MINIMAL] Capture exception: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_ocr(self, frame: Frame) -> List:
        """Run OCR on frame - simple and direct."""
        try:
            # Call EasyOCR directly
            text_blocks = self.ocr_layer.extract_text(frame)
            
            if text_blocks and len(text_blocks) > 0:
                self.logger.info(f"[OCR] Found {len(text_blocks)} text blocks")
                print(f"[MINIMAL] OCR found {len(text_blocks)} text blocks")
                # Log first few texts for debugging
                for i, block in enumerate(text_blocks[:3]):
                    text = block.text if hasattr(block, 'text') else str(block)
                    self.logger.info(f"[OCR] Block {i+1}: '{text[:50]}'")
                    print(f"[MINIMAL] OCR Block {i+1}: '{text[:50]}'")
            else:
                self.logger.info("[OCR] No text blocks found in frame")
                print("[MINIMAL] OCR: No text found")
            
            return text_blocks if text_blocks else []
        except Exception as e:
            self.logger.error(f"OCR failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _translate(self, text_blocks: List) -> List:
        """Translate text blocks - use subprocess to avoid crashes."""
        translations = []
        
        try:
            print(f"[MINIMAL] Starting translation for {len(text_blocks)} blocks")
            
            # Use subprocess pool (keeps model loaded for fast translations)
            from app.translation.engines.marianmt_subprocess_pool import translate_with_pool
            
            for i, block in enumerate(text_blocks, 1):
                text = block.text if hasattr(block, 'text') else str(block)
                
                if not text or len(text.strip()) == 0:
                    continue
                
                try:
                    if i == 1:
                        print(f"[MINIMAL] First translation via subprocess: '{text[:30]}'")
                        print(f"[MINIMAL] This may take 5-10 seconds (subprocess startup + model loading)")
                    
                    # Translate in subprocess pool (crash-safe, fast)
                    result = translate_with_pool(text, "en", "de", timeout=15.0)
                    
                    if result.get('error'):
                        # Subprocess failed, use dummy
                        if i == 1:
                            print(f"[MINIMAL] Subprocess failed: {result['error']}")
                            print(f"[MINIMAL] Switching to dummy translations")
                        return self._create_dummy_translations(text_blocks)
                    
                    translated_text = result.get('translated_text')
                    confidence = result.get('confidence', 0.9)
                    
                    if translated_text:
                        if i <= 3:
                            print(f"[MINIMAL] Subprocess {i}: '{text[:20]}' -> '{translated_text[:20]}'")
                        
                        # Get position from OCR block (EasyOCR uses 'position', not 'bbox')
                        if hasattr(block, 'position'):
                            position = block.position
                        elif hasattr(block, 'bbox'):
                            position = block.bbox
                        else:
                            position = Rectangle(0, 0, 100, 50)
                        
                        translation = type('Translation', (), {
                            'original_text': text,
                            'translated_text': translated_text,
                            'position': position,
                            'confidence': confidence,
                            'source_language': self.config.source_language,
                            'target_language': self.config.target_language
                        })()
                        
                        translations.append(translation)
                    else:
                        # No translation returned
                        if i == 1:
                            print(f"[MINIMAL] Subprocess returned no translation")
                        return self._create_dummy_translations(text_blocks)
                        
                except Exception as e:
                    # Subprocess call failed
                    print(f"[MINIMAL] Subprocess exception: {e}")
                    self.logger.error(f"Subprocess translation failed: {e}")
                    return self._create_dummy_translations(text_blocks)
            
            if translations:
                print(f"[MINIMAL] Subprocess translated {len(translations)} blocks successfully")
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            print(f"[MINIMAL] Translation exception: {e}")
            import traceback
            traceback.print_exc()
            return self._create_dummy_translations(text_blocks)
        
        return translations
    
    def _create_dummy_translations(self, text_blocks: List) -> List:
        """Create dummy translations as fallback."""
        translations = []
        
        try:
            for i, block in enumerate(text_blocks, 1):
                text = block.text if hasattr(block, 'text') else str(block)
                
                if not text or len(text.strip()) == 0:
                    continue
                
                dummy_text = f"[DE] {text}"
                
                # Get position from OCR block (EasyOCR uses 'position', not 'bbox')
                if hasattr(block, 'position'):
                    position = block.position
                elif hasattr(block, 'bbox'):
                    position = block.bbox
                else:
                    position = Rectangle(0, 0, 100, 50)
                
                translation = type('Translation', (), {
                    'original_text': text,
                    'translated_text': dummy_text,
                    'position': position,
                    'confidence': 0.5,  # Lower confidence for dummy
                    'source_language': self.config.source_language,
                    'target_language': self.config.target_language
                })()
                
                translations.append(translation)
                
                if i <= 3:
                    print(f"[MINIMAL] Dummy {i}: '{text[:30]}' -> '{dummy_text[:30]}'")
            
            if translations:
                print(f"[MINIMAL] Created {len(translations)} dummy translations")
                
        except Exception as e:
            print(f"[MINIMAL] Dummy translation error: {e}")
        
        return translations


def create_runtime_pipeline(capture_layer, ocr_layer, translation_layer, 
                           config: RuntimePipelineConfig) -> RuntimePipeline:
    """
    Factory function to create runtime translation pipeline.
    
    Args:
        capture_layer: Screen capture implementation
        ocr_layer: OCR engine implementation
        translation_layer: Translation engine implementation
        config: Runtime pipeline configuration
        
    Returns:
        RuntimePipeline instance
    """
    return RuntimePipeline(capture_layer, ocr_layer, translation_layer, config)
