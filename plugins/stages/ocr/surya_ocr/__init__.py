"""
Surya OCR Plugin - Main Entry Point

Vision-transformer OCR using surya-ocr.
Supports 90+ languages with line-level bounding boxes, GPU accelerated.
"""

import logging
from pathlib import Path

try:
    from surya.recognition import RecognitionPredictor
    from surya.detection import DetectionPredictor
    SURYA_AVAILABLE = True
except ImportError:
    SURYA_AVAILABLE = False

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.ocr.ocr_engine_interface import IOCREngine, OCRProcessingOptions, OCREngineType, OCREngineStatus
from app.models import Frame, TextBlock, Rectangle


class OCREngine(IOCREngine):
    """Surya OCR engine implementation."""

    _MAX_DIMENSION = 1280

    def __init__(self, engine_name: str = "surya_ocr", engine_type=None):
        if engine_type is None:
            engine_type = OCREngineType.SURYA_OCR
        super().__init__(engine_name, engine_type)

        self.recognition_predictor = None
        self.detection_predictor = None
        self.current_language = "en"
        self.logger = logging.getLogger(__name__)

    def initialize(self, config: dict) -> bool:
        try:
            if not SURYA_AVAILABLE:
                self.logger.error("surya-ocr library not available")
                self.status = OCREngineStatus.ERROR
                return False

            self.status = OCREngineStatus.INITIALIZING

            self.current_language = config.get("language", "en")
            use_gpu = config.get("gpu", True)

            self.logger.info(
                f"Initializing Surya OCR (language={self.current_language}, gpu={use_gpu})"
            )

            if not use_gpu:
                import os
                os.environ["TORCH_DEVICE"] = "cpu"

            from surya.foundation import FoundationPredictor
            foundation = FoundationPredictor()
            self.recognition_predictor = RecognitionPredictor(foundation)
            self.detection_predictor = DetectionPredictor()

            self.capabilities.has_text_detection = True
            self.status = OCREngineStatus.READY
            self.logger.info("Surya OCR initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Surya OCR: {e}")
            self.status = OCREngineStatus.ERROR
            return False

    def extract_text(self, frame: Frame, options: OCRProcessingOptions) -> list[TextBlock]:
        if not self.is_ready():
            return []

        try:
            import cv2
            import numpy as np
            from PIL import Image as PILImage

            image = frame.data
            h, w = image.shape[:2]
            scale = 1.0

            if max(h, w) > self._MAX_DIMENSION:
                scale = self._MAX_DIMENSION / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            pil_image = PILImage.fromarray(image)

            predictions = self.recognition_predictor(
                [pil_image], det_predictor=self.detection_predictor
            )

            text_blocks = []
            min_confidence = options.confidence_threshold if options else 0.5
            inv_scale = 1.0 / scale

            if predictions:
                pred = predictions[0]
                for line in pred.text_lines:
                    if line.confidence < min_confidence:
                        continue

                    if not line.text or not line.text.strip():
                        continue

                    # bbox is (x1, y1, x2, y2)
                    x1, y1, x2, y2 = line.bbox
                    px_x = int(x1 * inv_scale)
                    px_y = int(y1 * inv_scale)
                    px_w = int((x2 - x1) * inv_scale)
                    px_h = int((y2 - y1) * inv_scale)

                    text_block = TextBlock(
                        text=line.text,
                        position=Rectangle(px_x, px_y, px_w, px_h),
                        confidence=float(line.confidence),
                        language=options.language if options else self.current_language,
                    )
                    text_blocks.append(text_block)

            return text_blocks

        except Exception as e:
            self.logger.error(f"OCR processing failed: {e}")
            return []

    def extract_text_batch(self, frames: list[Frame], options: OCRProcessingOptions) -> list[list[TextBlock]]:
        results = []
        for frame in frames:
            results.append(self.extract_text(frame, options))
        return results

    def set_language(self, language: str) -> bool:
        try:
            if language != self.current_language:
                self.logger.info(f"Changing language from {self.current_language} to {language}")
                self.current_language = language
            return True
        except Exception as e:
            self.logger.error(f"Failed to set language: {e}")
            return False

    def get_supported_languages(self) -> list[str]:
        return [
            "en", "ja", "ko", "zh", "de", "fr", "es", "ru", "ar", "it", "pt", "nl",
            "tr", "pl", "hi", "th", "vi", "id", "cs", "ro", "hu", "sv", "da", "fi",
            "el", "uk", "he", "bn", "ta", "te", "ml", "mr", "gu", "kn", "pa", "ur",
            "fa", "ms", "my", "km", "lo", "ka",
        ]

    def cleanup(self) -> None:
        self.recognition_predictor = None
        self.detection_predictor = None
        self.status = OCREngineStatus.UNINITIALIZED

        try:
            from app.utils.pytorch_manager import release_gpu_memory
            release_gpu_memory()
        except ImportError:
            pass

        self.logger.info("Surya OCR engine cleaned up")
