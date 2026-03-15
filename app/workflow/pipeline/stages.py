"""
Pipeline stage implementations.

Each stage wraps a domain layer (capture, OCR, translation, overlay) and
conforms to the ``PipelineStageProtocol`` so the orchestrator can compose
them generically.

The audio stages (``AudioCaptureStage``, ``SpeechToTextStage``, ``TTSStage``)
contain real logic extracted from ``AudioTranslationPlugin`` (formerly
``SystemDiagnosticsOptimizer``).  Each manages its own resources (PyAudio,
Whisper, TTS engine) and handles missing dependencies gracefully by
returning ``StageResult(success=False)``.  An external engine/source can
still be injected for testing or custom backends.

Requirements: 2.1, 2.2
"""
import logging
import os
import threading
import time
from typing import Any

from .types import StageResult

from app.models import Frame, Rectangle
import numpy as np

logger = logging.getLogger('optikr.pipeline.stages')


# ---------------------------------------------------------------------------
# CaptureStage
# ---------------------------------------------------------------------------

class CaptureStage:
    """Captures a screen frame via the injected capture layer."""

    name = "capture"

    def __init__(self, capture_layer: Any = None) -> None:
        self._capture_layer = capture_layer

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()
        try:
            if self._capture_layer is None:
                return StageResult(success=False, error="Capture layer not initialised")
            region = input_data.get("region")
            source = input_data.get("source")
            logger.debug("[CaptureStage] region=%s source=%s", region, source)
            args = []
            if source is not None:
                args.append(source)
            if region is not None:
                args.append(region)
            frame = self._capture_layer.capture_frame(*args) if args else self._capture_layer.capture_frame()
            elapsed = (time.perf_counter() - start) * 1000
            shape = getattr(frame, "shape", None)
            dtype = getattr(frame, "dtype", type(frame).__name__)
            logger.debug(
                "[CaptureStage] frame shape=%s dtype=%s  %.1fms",
                shape, dtype, elapsed,
            )
            return StageResult(success=True, data={"frame": frame}, duration_ms=elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("CaptureStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=False, error=str(exc), duration_ms=elapsed)

    def cleanup(self) -> None:
        if self._capture_layer is not None and hasattr(self._capture_layer, "cleanup"):
            self._capture_layer.cleanup()


# ---------------------------------------------------------------------------
# PreprocessingStage
# ---------------------------------------------------------------------------

class PreprocessingStage:
    """Preprocesses a captured frame before OCR.

    When *enabled* is ``False`` the stage is a transparent pass-through
    (returns the frame unchanged).  When *intelligent* is ``True`` and
    the preprocessing layer supports ``should_enhance()``, enhancement
    is only applied when small text is detected.
    """

    name = "preprocessing"

    def __init__(
        self,
        preprocessing_layer: Any = None,
        *,
        enabled: bool = True,
        intelligent: bool = True,
        small_text_enhance: bool = False,
        small_text_denoise: bool = False,
        small_text_binarize: bool = False,
    ) -> None:
        self._preprocessing_layer = preprocessing_layer
        self._enabled = enabled
        self._intelligent = intelligent
        self._small_text_enhance = small_text_enhance
        self._small_text_denoise = small_text_denoise
        self._small_text_binarize = small_text_binarize
        self._small_text_applied = False

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()
        frame = input_data.get("frame")
        if frame is None:
            return StageResult(success=False, error="No frame provided for preprocessing")

        if not self._enabled or self._preprocessing_layer is None:
            mode = "disabled" if not self._enabled else "no_layer"
            logger.debug("[PreprocessingStage] skipped (mode=%s)", mode)
            elapsed = (time.perf_counter() - start) * 1000
            return StageResult(success=True, data={"frame": frame}, duration_ms=elapsed)

        try:
            small_text_result: bool | None = None
            if self._small_text_enhance:
                if not self._small_text_applied:
                    self._preprocessing_layer.set_small_text_enhancement_enabled(
                        True,
                        denoise=self._small_text_denoise,
                        binarize=self._small_text_binarize,
                    )
                    self._small_text_applied = True
                mode_name = "forced_small_text"
            elif self._intelligent:
                enhancer = getattr(self._preprocessing_layer, "_small_text_enhancer", None)
                if enhancer is not None and hasattr(enhancer, "should_enhance"):
                    small_text_result = enhancer.should_enhance(frame)
                    self._preprocessing_layer.set_small_text_enhancement_enabled(small_text_result)
                mode_name = "intelligent"
            else:
                mode_name = "standard"

            logger.debug(
                "[PreprocessingStage] applied=True mode=%s small_text_detected=%s",
                mode_name, small_text_result,
            )

            preprocessed = self._preprocessing_layer.preprocess(frame)
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("[PreprocessingStage] duration=%.1fms", elapsed)
            return StageResult(success=True, data={"frame": preprocessed}, duration_ms=elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("PreprocessingStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=False, error=str(exc), duration_ms=elapsed)

    def cleanup(self) -> None:
        pass


# ---------------------------------------------------------------------------
# OCRStage
# ---------------------------------------------------------------------------

class OCRStage:
    """Runs OCR on a captured frame.

    Includes two stabilisation mechanisms:

    * **Result cache** – when a new frame is visually similar to the
      previous one (e.g. only the overlay changed), the cached OCR
      results are returned immediately.  This prevents overlay
      flickering caused by the feedback loop where rendered overlays
      get re-captured and trigger a fresh OCR pass.

    * **Oversized-ROI filter** – ROI regions that cover more than
      ``_MAX_ROI_AREA_RATIO`` of the frame area are dropped (when at
      least two smaller regions remain).  This stops MangaOCR from
      merging an entire manga panel into one text block at (0, 0).
    """

    name = "ocr"

    _MAX_ROI_AREA_RATIO = 0.40
    _STABILITY_THRESHOLD_DEFAULT = 0.80
    _MIN_ROI_WIDTH = 50
    _MIN_ROI_HEIGHT = 40
    _MIN_ROI_AREA = 3000

    # Characters that Manga OCR hallucinates on blank / non-text crops
    _HALLUCINATION_CHARS = set("．…・、。.!！ \t\n")

    _OVERLAY_LATIN_THRESHOLD = 0.30
    _OVERLAY_MASK_MARGIN = 4

    def __init__(
        self,
        ocr_layer: Any = None,
        confidence_threshold: float = 0.5,
        source_lang: str = "",
        stability_threshold: float | None = None,
    ) -> None:
        self._ocr_layer = ocr_layer
        self._confidence_threshold = confidence_threshold
        self._source_lang = source_lang
        thresh = (stability_threshold if stability_threshold is not None
                  else self._STABILITY_THRESHOLD_DEFAULT)
        self._STABILITY_THRESHOLD = max(0.50, min(0.99, thresh))
        self._HIGH_SIMILARITY_THRESHOLD = min(
            0.99, self._STABILITY_THRESHOLD + 0.04)
        self._prev_thumb: np.ndarray | None = None
        self._prev_results: list[Any] | None = None
        self._prev_roi_fingerprint: int = 0

    def reset(self) -> None:
        """Clear the frame-stability cache so the next frame is OCR'd fresh."""
        self._prev_thumb = None
        self._prev_results = None
        self._prev_roi_fingerprint = 0

    # ------------------------------------------------------------------
    # Frame stability helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_thumb(data: np.ndarray) -> np.ndarray:
        """Downsample the **center 50 %** of *data* to a ~32x32 thumbnail.

        Using the center crop avoids the edges/corners where overlays
        are rendered, preventing the overlay-capture feedback loop from
        defeating the stability cache.
        """
        h, w = data.shape[:2]
        y0, y1 = h // 4, h - h // 4
        x0, x1 = w // 4, w - w // 4
        center = data[y0:y1, x0:x1]
        ch, cw = center.shape[:2]
        thumb = center[:: max(1, ch // 32), :: max(1, cw // 32)]
        return thumb.astype(np.float32)

    def _frame_similarity(self, data: np.ndarray) -> float:
        """Return the visual similarity [0.0, 1.0] between *data* and
        the cached thumbnail.  Returns 0.0 when there is no cache."""
        if self._prev_thumb is None:
            return 0.0
        thumb = self._make_thumb(data)
        if thumb.shape != self._prev_thumb.shape:
            return 0.0
        mse = float(np.mean((thumb - self._prev_thumb) ** 2))
        return 1.0 - mse / (255.0 ** 2)
    @staticmethod
    def _roi_fingerprint(regions: list[Rectangle]) -> int:
        """Return a hash summarising the ROI region list.

        Used to invalidate the stability cache when the bubble detector
        finds different regions (e.g. after scrolling to a new page)
        even if the 32×32 thumbnail looks similar.
        """
        if not regions:
            return 0
        # Hash the count + bounding coordinates — cheap and effective
        parts = tuple(
            (r.x, r.y, r.width, r.height) for r in sorted(
                regions, key=lambda r: (r.x, r.y),
            )
        )
        return hash((len(regions), parts))

    # ------------------------------------------------------------------
    # Hallucination / noise helpers
    # ------------------------------------------------------------------

    @classmethod
    def _is_hallucination(cls, text: str) -> bool:
        """Return True when *text* looks like a Manga OCR hallucination.

        Manga OCR is a seq2seq model — it *always* produces output, even
        for blank or non-text crops.  Common hallucination patterns:
        - Dots / ellipsis only: ``．．．``, ``…``
        - Single kana / punctuation: ``ッ``, ``、``, ``く``
        - Very short text with no real content
        - Short text padded with dots: ``それは．．．``, ``いや．．．``
        """
        stripped = text.strip()
        if not stripped:
            return True
        # All characters are hallucination filler
        if all(ch in cls._HALLUCINATION_CHARS for ch in stripped):
            return True
        # Single character (almost always noise from tiny crops)
        if len(stripped) <= 1:
            return True
        # Short text padded with filler — e.g. "それは．．．" or "いや．．．"
        # When more than half the characters are filler and the real
        # content is ≤3 chars, it's almost certainly a hallucination
        # from a blank/noisy crop.
        real_chars = [ch for ch in stripped if ch not in cls._HALLUCINATION_CHARS]
        if len(real_chars) <= 3 and len(real_chars) <= len(stripped) * 0.5:
            return True
        return False

    @staticmethod
    def _is_latin_char(ch: str) -> bool:
        """Return True for ASCII or fullwidth Latin letters (A-Z, a-z)."""
        cp = ord(ch)
        return (
            0x41 <= cp <= 0x5A         # A-Z
            or 0x61 <= cp <= 0x7A      # a-z
            or 0xFF21 <= cp <= 0xFF3A  # Ａ-Ｚ
            or 0xFF41 <= cp <= 0xFF5A  # ａ-ｚ
        )

    def _is_overlay_contamination(self, text: str) -> bool:
        """Detect English overlay text leaking into Japanese OCR output.

        When the pipeline source language is Japanese, OCR output that
        consists predominantly of Latin letters (either regular ASCII or
        fullwidth variants like Ａ-Ｚ, ａ-ｚ) is almost certainly the
        overlay renderer's own English translations being re-captured and
        fed back into OCR.

        Returns False immediately for non-Japanese source languages.
        """
        if self._source_lang not in ("ja", "jpn", "japanese"):
            return False
        stripped = text.strip()
        if not stripped:
            return False
        non_ws = [ch for ch in stripped if not ch.isspace()]
        if not non_ws:
            return False
        latin_count = sum(1 for ch in non_ws if self._is_latin_char(ch))
        ratio = latin_count / len(non_ws)
        if ratio >= self._OVERLAY_LATIN_THRESHOLD:
            logger.debug(
                "[OCRStage] overlay contamination: %.0f%% Latin in '%s'",
                ratio * 100, stripped[:60],
            )
            return True
        return False

    # ------------------------------------------------------------------
    # Overlay masking
    # ------------------------------------------------------------------

    @staticmethod
    def _mask_overlay_regions(
        data: np.ndarray,
        positions: list,
        margin: int = 4,
    ) -> np.ndarray:
        """Return a copy of *data* with previous-frame overlay regions whited out.

        Painting overlay areas white prevents the OCR engine from
        re-reading its own rendered translations (feedback loop).
        """
        masked = data.copy()
        h, w = masked.shape[:2]
        for pos in positions:
            x0 = max(0, getattr(pos, "x", 0) - margin)
            y0 = max(0, getattr(pos, "y", 0) - margin)
            x1 = min(w, getattr(pos, "x", 0) + getattr(pos, "width", 0) + margin)
            y1 = min(h, getattr(pos, "y", 0) + getattr(pos, "height", 0) + margin)
            if x1 > x0 and y1 > y0:
                masked[y0:y1, x0:x1] = 255
        return masked

    # ------------------------------------------------------------------
    # Position helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_full_input_bbox(pos: Rectangle, input_w: int, input_h: int) -> bool:
        """Return True when *pos* covers (nearly) the entire input image.

        MangaOCR always returns ``[0, 0, w, h]`` matching its input
        dimensions.  This bbox carries no real positional information and
        should not be used for overlay placement at ``(0, 0)``.
        """
        return (
            pos.x == 0
            and pos.y == 0
            and abs(pos.width - input_w) <= 5
            and abs(pos.height - input_h) <= 5
        )

    @classmethod
    def _offset_position(
        cls,
        pos: Rectangle,
        region: Rectangle,
        crop_w: int,
        crop_h: int,
    ) -> Rectangle:
        """Map an OCR bbox back into frame coordinates.

        When the bbox covers the entire crop (typical of MangaOCR) the
        overlay is placed at the **centre** of the ROI region instead of
        at its top-left corner, giving a much better visual result.
        """
        if cls._is_full_input_bbox(pos, crop_w, crop_h):
            return Rectangle(
                x=region.x + region.width // 4,
                y=region.y + region.height // 4,
                width=region.width // 2,
                height=region.height // 2,
            )
        return Rectangle(
            x=pos.x + region.x,
            y=pos.y + region.y,
            width=pos.width,
            height=pos.height,
        )

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()
        try:
            if self._ocr_layer is None:
                return StageResult(success=False, error="OCR layer not initialised")
            frame = input_data.get("frame")
            if frame is None:
                return StageResult(success=False, error="No frame provided for OCR")

            # --- Extract ROI regions early (needed for cache validation) ---
            roi_regions: list[Rectangle] = []
            if hasattr(frame, "metadata") and isinstance(frame.metadata, dict):
                roi_regions = frame.metadata.get("roi_regions", [])

            # --- Stability cache: reuse previous results for similar frames ---
            # Bypassed when the FrameSkipOptimizer signals a content
            # change (frame_changed=True), ensuring fresh OCR runs
            # immediately after user-visible changes.
            force_fresh = input_data.get("frame_changed", False)
            roi_fingerprint = self._roi_fingerprint(roi_regions)
            similarity = self._frame_similarity(frame.data)
            frame_is_stable = similarity >= self._STABILITY_THRESHOLD
            roi_match = roi_fingerprint == self._prev_roi_fingerprint
            cache_valid = (
                not force_fresh
                and self._prev_results is not None
                and frame_is_stable
                and (similarity >= self._HIGH_SIMILARITY_THRESHOLD or roi_match)
            )
            if cache_valid:
                if not roi_match:
                    logger.debug(
                        "[OCRStage] ROI fingerprint changed but similarity=%.4f "
                        ">= %.2f, trusting frame cache",
                        similarity, self._HIGH_SIMILARITY_THRESHOLD,
                    )
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug(
                    "[OCRStage] stable frame -> reusing %d cached blocks  %.1fms",
                    len(self._prev_results), elapsed,
                )
                return StageResult(
                    success=True,
                    data={"text_blocks": self._prev_results},
                    duration_ms=elapsed,
                )
            if force_fresh:
                logger.info(
                    "[OCRStage] Frame change detected by FrameSkipOptimizer "
                    "-> forcing fresh OCR (similarity=%.4f)", similarity,
                )

            # --- Mask previous-frame overlay regions to prevent feedback ---
            overlay_positions = input_data.get("_overlay_positions", [])
            if overlay_positions:
                masked_data = self._mask_overlay_regions(
                    frame.data, overlay_positions, self._OVERLAY_MASK_MARGIN,
                )
                frame = Frame(
                    data=masked_data,
                    timestamp=frame.timestamp,
                    source_region=frame.source_region,
                    metadata=frame.metadata,
                )
                logger.debug(
                    "[OCRStage] masked %d overlay region(s) from previous frame",
                    len(overlay_positions),
                )

            # --- Check if the engine has built-in text detection ---
            # Engines like Mokuro include their own text detector that
            # outperforms the generic bubble detector.  When available,
            # skip per-region cropping and feed the full frame directly.
            engine_has_detection = (
                hasattr(self._ocr_layer, "engine_has_text_detection")
                and self._ocr_layer.engine_has_text_detection()
            )

            if engine_has_detection:
                if roi_regions:
                    logger.debug(
                        "[OCRStage] engine has built-in detection — "
                        "ignoring %d ROI region(s), using full frame",
                        len(roi_regions),
                    )
                roi_regions = []

            if roi_regions:
                logger.info(
                    "[OCRStage] %d ROI region(s) from preprocessing: %s",
                    len(roi_regions),
                    ", ".join(
                        f"({r.x},{r.y},{r.width}x{r.height})"
                        for r in roi_regions[:5]
                    )
                    + ("..." if len(roi_regions) > 5 else ""),
                )

            # --- Filter oversized ROI regions (panel-level, not bubble-level) --
            if roi_regions:
                frame_area = frame.data.shape[0] * frame.data.shape[1]
                max_area = frame_area * self._MAX_ROI_AREA_RATIO
                small = [r for r in roi_regions if r.width * r.height <= max_area]
                if small:
                    dropped = len(roi_regions) - len(small)
                    if dropped:
                        logger.debug(
                            "[OCRStage] dropped %d oversized ROI region(s) (>%.0f%% frame)",
                            dropped, self._MAX_ROI_AREA_RATIO * 100,
                        )
                    roi_regions = small

            # --- Filter undersized ROI regions (noise, tiny fragments) ---
            if roi_regions:
                before = len(roi_regions)
                roi_regions = [
                    r for r in roi_regions
                    if r.width >= self._MIN_ROI_WIDTH
                    and r.height >= self._MIN_ROI_HEIGHT
                    and r.width * r.height >= self._MIN_ROI_AREA
                ]
                dropped = before - len(roi_regions)
                if dropped:
                    logger.debug(
                        "[OCRStage] dropped %d undersized ROI region(s) (<%dx%d or area<%d)",
                        dropped, self._MIN_ROI_WIDTH, self._MIN_ROI_HEIGHT,
                        self._MIN_ROI_AREA,
                    )

            if roi_regions:
                all_blocks: list[Any] = []
                for region in roi_regions:
                    crop = frame.data[
                        region.y : region.y + region.height,
                        region.x : region.x + region.width,
                    ]
                    crop_h, crop_w = crop.shape[:2]
                    sub_frame = Frame(
                        data=crop,
                        timestamp=frame.timestamp,
                        source_region=frame.source_region,
                    )
                    blocks = self._ocr_layer.extract_text(sub_frame)
                    for blk in blocks:
                        pos = getattr(blk, "position", None)
                        if pos is not None:
                            blk.position = self._offset_position(
                                pos, region, crop_w, crop_h,
                            )
                        all_blocks.append(blk)
                logger.debug(
                    "[OCRStage] per-region OCR: %d regions -> %d blocks",
                    len(roi_regions), len(all_blocks),
                )
                text_blocks = all_blocks if all_blocks else self._ocr_layer.extract_text(frame)
            else:
                text_blocks = self._ocr_layer.extract_text(frame)

            # Centre-correct any full-frame bboxes from the fallback path
            if not roi_regions and not engine_has_detection:
                fh, fw = frame.data.shape[:2]
                for blk in text_blocks:
                    pos = getattr(blk, "position", None)
                    if pos is not None and self._is_full_input_bbox(pos, fw, fh):
                        blk.position = Rectangle(
                            x=fw // 4, y=fh // 4,
                            width=fw // 2, height=fh // 2,
                        )

            filtered = [
                b for b in text_blocks
                if getattr(b, "confidence", 1.0) >= self._confidence_threshold
                and getattr(b, "text", "").strip()
                and not self._is_hallucination(getattr(b, "text", ""))
                and not self._is_overlay_contamination(getattr(b, "text", ""))
            ]

            # Cache results + thumbnail + ROI fingerprint for next frame
            self._prev_thumb = self._make_thumb(frame.data)
            self._prev_results = filtered
            self._prev_roi_fingerprint = roi_fingerprint

            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(
                "[OCRStage] raw=%d  filtered=%d  threshold=%.2f  %.1fms",
                len(text_blocks), len(filtered), self._confidence_threshold, elapsed,
            )
            for i, blk in enumerate(filtered):
                text = getattr(blk, "text", str(blk))
                pos = getattr(blk, "position", None)
                conf = getattr(blk, "confidence", None)
                logger.debug(
                    "[OCRStage]   [%d] '%.60s'  conf=%.2f  pos=%s",
                    i, text, conf if conf is not None else 0.0, pos,
                )
            return StageResult(success=True, data={"text_blocks": filtered}, duration_ms=elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("OCRStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=False, error=str(exc), duration_ms=elapsed)

    def cleanup(self) -> None:
        if self._ocr_layer is not None and hasattr(self._ocr_layer, "cleanup"):
            self._ocr_layer.cleanup()


# ---------------------------------------------------------------------------
# TranslationStage
# ---------------------------------------------------------------------------

class TranslationStage:
    """Translates text blocks via the injected translation layer."""

    name = "translation"

    def __init__(
        self,
        translation_layer: Any = None,
        source_lang: str = "en",
        target_lang: str = "de",
        bidirectional: bool = False,
    ) -> None:
        self._translation_layer = translation_layer
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._bidirectional = bidirectional

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()
        try:
            if self._translation_layer is None:
                return StageResult(success=False, error="Translation layer not initialised")

            text_blocks = input_data.get("text_blocks", [])

            if not text_blocks:
                transcribed = input_data.get("transcribed_text", "")
                if not transcribed:
                    logger.debug("[TranslationStage] no text to translate, skipping")
                    elapsed = (time.perf_counter() - start) * 1000
                    return StageResult(success=True, data={"translations": []}, duration_ms=elapsed)
                return self._translate_audio_text(transcribed, input_data, start)

            source_lang = input_data.get("source_lang", self._source_lang)
            target_lang = input_data.get("target_lang", self._target_lang)

            translations: list[str] = [""] * len(text_blocks)
            texts_to_translate: list[str] = []
            indices_to_translate: list[int] = []

            for i, block in enumerate(text_blocks):
                skip = (
                    block.get("skip_translation", False)
                    if isinstance(block, dict)
                    else getattr(block, "skip_translation", False)
                )
                if skip:
                    pre_translated = (
                        block.get("translated_text", "")
                        if isinstance(block, dict)
                        else getattr(block, "translated_text", "")
                    )
                    translations[i] = pre_translated
                    continue

                text = (
                    block.get("text", str(block))
                    if isinstance(block, dict)
                    else getattr(block, "text", str(block))
                )
                texts_to_translate.append(text)
                indices_to_translate.append(i)

            skip_count = len(text_blocks) - len(texts_to_translate)

            if texts_to_translate:
                batch_fn = getattr(self._translation_layer, "translate_batch", None)
                engine_mode: str
                if batch_fn is not None:
                    engine = self._resolve_engine(input_data)
                    engine_mode = f"batch (engine={engine or 'default'})"
                    batch_results = batch_fn(
                        texts_to_translate, engine, source_lang, target_lang,
                    )
                    for idx, result in zip(indices_to_translate, batch_results):
                        translations[idx] = result
                else:
                    engine_mode = "single"
                    for idx, text in zip(indices_to_translate, texts_to_translate):
                        result = self._translation_layer.translate(
                            text=text,
                            source_lang=source_lang,
                            target_lang=target_lang,
                        )
                        if result is not None:
                            translations[idx] = result
            else:
                engine_mode = "none (all skipped)"

            elapsed = (time.perf_counter() - start) * 1000

            logger.debug(
                "[TranslationStage] blocks=%d  translate=%d  skipped=%d  "
                "mode=%s  %s->%s  %.1fms",
                len(text_blocks), len(texts_to_translate), skip_count,
                engine_mode, source_lang, target_lang, elapsed,
            )
            for i, t in enumerate(translations):
                src_block = text_blocks[i] if i < len(text_blocks) else None
                src_text = (
                    src_block.get("text", "") if isinstance(src_block, dict)
                    else getattr(src_block, "text", "")
                ) if src_block else ""
                pos = (
                    src_block.get("position", src_block.get("bbox"))
                    if isinstance(src_block, dict)
                    else getattr(src_block, "position", None)
                ) if src_block else None
                t_str = str(t) if t else ""
                if t_str and t_str != src_text:
                    logger.info(
                        "[Translation] '%s' -> '%s'  pos=%s",
                        src_text[:40], t_str[:60], pos,
                    )
                elif t_str:
                    logger.warning(
                        "[Translation] UNTRANSLATED '%s' (engine returned original)  pos=%s",
                        src_text[:40], pos,
                    )

            translated_text = " ".join(str(t) for t in translations if t) if translations else ""
            return StageResult(
                success=True,
                data={
                    "translations": translations,
                    "text_blocks": text_blocks,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "translated_text": translated_text,
                },
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("TranslationStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=False, error=str(exc), duration_ms=elapsed)

    def _resolve_engine(self, input_data: dict[str, Any]) -> str:
        """Determine the translation engine name for batch calls."""
        engine = input_data.get("engine", "")
        if not engine:
            default = getattr(self._translation_layer, "_default_engine", None)
            if default:
                engine = default
        return engine or ""

    def _translate_audio_text(
        self,
        text: str,
        input_data: dict[str, Any],
        start: float,
    ) -> StageResult:
        """Translate a single text string (audio pipeline path).

        In bidirectional mode, if the detected language differs from the
        configured source language the translation direction is flipped.
        """
        detected = input_data.get("detected_language", self._source_lang)

        if self._bidirectional and detected != self._source_lang:
            target = self._source_lang
        else:
            target = self._target_lang

        result = self._translation_layer.translate(
            text=text,
            source_lang=detected,
            target_lang=target,
        )

        elapsed = (time.perf_counter() - start) * 1000
        translated = str(result) if result is not None else text
        return StageResult(
            success=True,
            data={
                "translations": [translated] if result is not None else [],
                "translated_text": translated,
                "source_language": detected,
                "target_language": target,
            },
            duration_ms=elapsed,
        )

    def cleanup(self) -> None:
        if self._translation_layer is not None and hasattr(self._translation_layer, "cleanup"):
            self._translation_layer.cleanup()


# ---------------------------------------------------------------------------
# LLMStage
# ---------------------------------------------------------------------------

class LLMStage:
    """Optional LLM post-processing stage between Translation and Overlay.

    When an ``llm_layer`` is provided and enabled, each translated text
    block is passed through the LLM engine for refinement, replacement,
    or custom prompt processing.  When ``llm_layer`` is ``None`` the
    stage is a transparent pass-through so the rest of the pipeline is
    unaffected.

    Modes (configured via ``mode`` parameter):
    * ``"refine"``   – post-translation polish of translated texts
    * ``"translate"`` – LLM-based translation replacing the previous
                        translation stage output
    * ``"custom"``   – freeform prompt driven by ``custom_prompt``
    """

    name = "llm"

    def __init__(
        self,
        llm_layer: Any = None,
        *,
        mode: str = "refine",
        custom_prompt: str = "",
        source_lang: str = "",
        target_lang: str = "",
    ) -> None:
        self._llm_layer = llm_layer
        self._mode = mode
        self._custom_prompt = custom_prompt
        self._source_lang = source_lang
        self._target_lang = target_lang

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()

        if self._llm_layer is None:
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("[LLMStage] skipped (no llm_layer)")
            return StageResult(success=True, data=input_data, duration_ms=elapsed)

        translations: list[str] = input_data.get("translations", [])
        text_blocks: list[Any] = input_data.get("text_blocks", [])

        if not translations:
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug("[LLMStage] no translations to process, pass-through")
            return StageResult(success=True, data=input_data, duration_ms=elapsed)

        try:
            from app.llm.llm_engine_interface import LLMProcessingOptions, LLMProcessingMode

            mode_map = {
                "refine": LLMProcessingMode.REFINE,
                "translate": LLMProcessingMode.TRANSLATE,
                "custom": LLMProcessingMode.CUSTOM,
            }
            processing_mode = mode_map.get(self._mode, LLMProcessingMode.REFINE)

            source_lang = input_data.get("source_lang", self._source_lang)
            target_lang = input_data.get("target_lang", self._target_lang)

            options = LLMProcessingOptions(
                mode=processing_mode,
                source_language=source_lang,
                target_language=target_lang,
            )
            if self._custom_prompt:
                options.prompt_template = self._custom_prompt

            refined: list[str] = []
            for i, translated_text in enumerate(translations):
                if not translated_text:
                    refined.append(translated_text)
                    continue

                if self._mode == "translate":
                    block = text_blocks[i] if i < len(text_blocks) else None
                    original = (
                        block.get("text", str(block))
                        if isinstance(block, dict)
                        else getattr(block, "text", str(block))
                    ) if block else str(translated_text)
                    result = self._llm_layer.process_text(original, options=options)
                else:
                    result = self._llm_layer.process_text(str(translated_text), options=options)

                refined.append(result)

            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(
                "[LLMStage] mode=%s  processed=%d  %.1fms",
                self._mode, len(refined), elapsed,
            )

            output = dict(input_data)
            output["translations"] = refined
            return StageResult(success=True, data=output, duration_ms=elapsed)

        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("LLMStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=True, data=input_data, duration_ms=elapsed)

    def cleanup(self) -> None:
        if self._llm_layer is not None and hasattr(self._llm_layer, "cleanup"):
            self._llm_layer.cleanup()


# ---------------------------------------------------------------------------
# VisionTranslateStage
# ---------------------------------------------------------------------------

class VisionTranslateStage:
    """Combined OCR + Translation using a vision-language model.

    Replaces the OCR -> Translation -> LLM stages with a single model
    pass that reads text directly from the captured frame and returns
    translated text blocks with bounding boxes.

    Expects ``input_data["frame"]`` (from CaptureStage).
    Produces ``translations`` and ``text_blocks`` compatible with
    OverlayStage.
    """

    name = "vision_translate"

    def __init__(
        self,
        vision_layer: Any = None,
        *,
        source_lang: str = "",
        target_lang: str = "",
    ) -> None:
        self._vision_layer = vision_layer
        self._source_lang = source_lang
        self._target_lang = target_lang

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()

        if self._vision_layer is None:
            return StageResult(success=False, error="Vision layer not initialised")

        frame = input_data.get("frame")
        if frame is None:
            return StageResult(success=False, error="No frame provided for vision translation")

        try:
            frame_data = frame.data if hasattr(frame, "data") else frame

            source_lang = input_data.get("source_lang", self._source_lang)
            target_lang = input_data.get("target_lang", self._target_lang)

            results = self._vision_layer.translate_frame(
                frame_data, source_lang, target_lang,
            )

            text_blocks = []
            translations = []
            for item in results:
                original = item.get("original", "").strip()
                text = item.get("text", "").strip()
                bbox = item.get("bbox", [0, 0, 100, 30])
                # Use original (source) text in block so cache/dictionary plugins can
                # save (original -> translation) for reuse in text pipeline.
                block_source_text = original if original else text

                block = {
                    "text": block_source_text,
                    "position": Rectangle(
                        x=bbox[0], y=bbox[1],
                        width=bbox[2], height=bbox[3],
                    ),
                    "confidence": 1.0,
                    "source": "vision",
                }
                text_blocks.append(block)
                translations.append(text)

            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(
                "[VisionTranslateStage] %d block(s) in %.1fms",
                len(text_blocks), elapsed,
            )
            return StageResult(
                success=True,
                data={
                    "translations": translations,
                    "text_blocks": text_blocks,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                },
                duration_ms=elapsed,
            )

        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("VisionTranslateStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=False, error=str(exc), duration_ms=elapsed)

    def cleanup(self) -> None:
        if self._vision_layer is not None and hasattr(self._vision_layer, "cleanup"):
            self._vision_layer.cleanup()


# ---------------------------------------------------------------------------
# OverlayStage
# ---------------------------------------------------------------------------

class OverlayStage:
    """Renders translated text as an overlay."""

    name = "overlay"

    def __init__(self, overlay_renderer: Any = None, stop_event: "threading.Event | None" = None) -> None:
        self._overlay_renderer = overlay_renderer
        self._stop_event = stop_event

    @staticmethod
    def _extract_position(block: Any) -> tuple[int, int]:
        """Pull (x, y) from a TextBlock / dict / list, falling back to (0, 0)."""
        if block is None:
            return (0, 0)
        pos = (
            block.get("position", block.get("bbox"))
            if isinstance(block, dict)
            else getattr(block, "position", None)
        )
        if pos is None:
            return (0, 0)
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            return (int(pos[0]), int(pos[1]))
        x = getattr(pos, "x", None)
        y = getattr(pos, "y", None)
        if x is not None and y is not None:
            return (int(x), int(y))
        return (0, 0)

    @staticmethod
    def _get_region_offset(input_data: dict[str, Any]) -> tuple[int, int]:
        """Extract the capture region's screen-space (x, y) origin.

        OCR positions are relative to the captured crop; the overlay needs
        absolute screen coordinates, so we add this offset.
        """
        region = input_data.get("region")
        if region is None:
            return (0, 0)

        if isinstance(region, dict):
            return (int(region.get("x", 0)), int(region.get("y", 0)))

        rect = getattr(region, "rectangle", None)
        if rect is not None:
            return (int(getattr(rect, "x", 0)), int(getattr(rect, "y", 0)))

        x = getattr(region, "x", None)
        y = getattr(region, "y", None)
        if x is not None and y is not None:
            return (int(x), int(y))

        return (0, 0)

    @staticmethod
    def _extract_full_position(block: Any) -> Rectangle | None:
        """Extract the full bounding rectangle from a text block.

        Returns *None* when the block carries no usable size info.
        """
        if block is None:
            return None
        pos = (
            block.get("position", block.get("bbox"))
            if isinstance(block, dict)
            else getattr(block, "position", None)
        )
        if pos is None:
            return None
        if isinstance(pos, Rectangle):
            return pos
        if isinstance(pos, (list, tuple)) and len(pos) >= 4:
            return Rectangle(
                x=int(pos[0]), y=int(pos[1]),
                width=int(pos[2]), height=int(pos[3]),
            )
        x = getattr(pos, "x", None)
        y = getattr(pos, "y", None)
        w = getattr(pos, "width", None)
        h = getattr(pos, "height", None)
        if all(v is not None for v in (x, y, w, h)):
            return Rectangle(x=int(x), y=int(y), width=int(w), height=int(h))
        return None

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()
        try:
            if self._stop_event is not None and self._stop_event.is_set():
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug("[OverlayStage] pipeline stopped, discarding frame  %.1fms", elapsed)
                return StageResult(
                    success=True,
                    data={"rendered": False, "_overlay_positions": []},
                    duration_ms=elapsed,
                )

            if self._overlay_renderer is None:
                elapsed = (time.perf_counter() - start) * 1000
                return StageResult(
                    success=True,
                    data={"rendered": False, "_overlay_positions": []},
                    duration_ms=elapsed,
                )

            if input_data.get("skip_processing", False):
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug("[OverlayStage] frame skipped, keeping overlay  %.1fms", elapsed)
                return StageResult(
                    success=True,
                    data={
                        "rendered": True,
                        "_overlay_positions": input_data.get("_overlay_positions", []),
                    },
                    duration_ms=elapsed,
                )

            translations = input_data.get("translations", [])
            text_blocks = input_data.get("text_blocks", [])

            region_offset = self._get_region_offset(input_data)

            overlay_positions: list[Rectangle] = []
            if not translations or all(not t for t in translations):
                if hasattr(self._overlay_renderer, "hide_all_translations"):
                    self._overlay_renderer.hide_all_translations()
                elif hasattr(self._overlay_renderer, "clear"):
                    self._overlay_renderer.clear()
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug("[OverlayStage] cleared  %.1fms", elapsed)
            else:
                if hasattr(self._overlay_renderer, "hide_all_translations"):
                    self._overlay_renderer.hide_all_translations(immediate=True)
                for i, translated_text in enumerate(translations):
                    if not translated_text:
                        continue
                    t_str = str(translated_text)
                    block = text_blocks[i] if i < len(text_blocks) else None
                    local_pos = self._extract_position(block)
                    screen_pos = (
                        local_pos[0] + region_offset[0],
                        local_pos[1] + region_offset[1],
                    )
                    tid = f"t_{i}"
                    self._overlay_renderer.show_translation(t_str, screen_pos, tid)
                    logger.info(
                        "[Overlay] '%s' at screen(%d, %d)",
                        t_str[:50], screen_pos[0], screen_pos[1],
                    )
                    full_pos = self._extract_full_position(block)
                    if full_pos is not None:
                        overlay_positions.append(full_pos)
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug(
                    "[OverlayStage] rendered %d overlay(s)  %.1fms",
                    len([t for t in translations if t]), elapsed,
                )
            return StageResult(
                success=True,
                data={"rendered": True, "_overlay_positions": overlay_positions},
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("OverlayStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(success=False, error=str(exc), duration_ms=elapsed)

    def cleanup(self) -> None:
        if self._overlay_renderer is not None and hasattr(self._overlay_renderer, "cleanup"):
            self._overlay_renderer.cleanup()


# ===================================================================
# Audio-pipeline stages (real implementations)
#
# Extracted from AudioTranslationPlugin (formerly
# SystemDiagnosticsOptimizer).  Each stage manages its own heavy
# resources (PyAudio, Whisper, TTS engine) via lazy initialisation
# and handles missing dependencies gracefully.  An external
# engine/source can still be injected for testing or custom backends.
# ===================================================================


class AudioTextAdapterStage:
    """Converts STT output into the ``text_blocks`` list format expected by
    optimizer plugins (Context Manager, Learning Dictionary, etc.).

    Without this adapter the audio pipeline passes a plain
    ``transcribed_text`` string, which the plugins cannot process because
    they operate on ``data["text_blocks"]``.  This stage sits between
    SpeechToText and Translation so that plugin hooks on the translation
    stage see the data in the standard format.

    Bidirectional language handling is also resolved here: when the
    detected language differs from the configured source language, the
    ``source_lang`` / ``target_lang`` keys in the data dict are swapped
    so downstream stages translate in the correct direction.
    """

    name = "audio_text_adapter"

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "ja",
        bidirectional: bool = True,
    ) -> None:
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._bidirectional = bidirectional

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()

        transcribed = input_data.get("transcribed_text", "")
        if not transcribed:
            elapsed = (time.perf_counter() - start) * 1000
            return StageResult(
                success=True,
                data={"text_blocks": [], "transcribed_text": ""},
                duration_ms=elapsed,
            )

        detected = input_data.get("detected_language", self._source_lang)
        source = self._source_lang
        target = self._target_lang

        if self._bidirectional and detected != self._source_lang:
            source = detected
            target = self._source_lang

        block = {
            "text": transcribed,
            "confidence": 1.0,
            "source": "audio",
        }

        elapsed = (time.perf_counter() - start) * 1000
        return StageResult(
            success=True,
            data={
                "text_blocks": [block],
                "transcribed_text": transcribed,
                "detected_language": detected,
                "source_lang": source,
                "target_lang": target,
            },
            duration_ms=elapsed,
        )

    def cleanup(self) -> None:
        pass


class AudioCaptureStage:
    """Captures audio from a microphone using PyAudio with optional VAD.

    Opens a non-blocking mic stream via a PyAudio callback.  Each
    ``execute()`` call accumulates audio chunks until either a silence
    gap (detected by WebRTC VAD) or a maximum buffer duration is
    reached, then returns the complete utterance as a NumPy int16 array.

    When *audio_source* is injected (an object with a ``read(frames)``
    method), the stage delegates to it instead of managing PyAudio
    internally -- useful for testing or custom capture backends.
    """

    name = "audio_capture"

    def __init__(
        self,
        audio_source: Any = None,
        config: Any = None,
    ) -> None:
        self._audio_source = audio_source
        self._config: dict[str, Any] = config if isinstance(config, dict) else {}

        self._sample_rate: int = self._config.get("sample_rate", 16000)
        self._input_device: int | None = self._config.get("input_device", None)
        self._input_volume: float = self._config.get("input_volume", 100) / 100.0
        self._vad_enabled: bool = self._config.get("vad_enabled", True)
        self._vad_sensitivity: int = self._config.get("vad_sensitivity", 2)
        self._silence_threshold: float = self._config.get("silence_threshold", 0.3)
        self._min_audio_length: float = self._config.get("min_audio_length", 0.4)
        self._max_buffer_duration: float = self._config.get("max_buffer_duration", 4.0)

        self._pyaudio_instance: Any = None
        self._stream: Any = None
        self._vad: Any = None
        self._audio_queue: Any = None
        self._initialized: bool = False
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> str | None:
        """Set up PyAudio + VAD on first call.  Returns an error string
        or *None* on success."""
        if self._initialized:
            return None

        try:
            import pyaudio  # type: ignore[import-untyped]
        except ImportError:
            return "pyaudio not installed (pip install pyaudio)"
        try:
            import numpy  # noqa: F401
        except ImportError:
            return "numpy not installed (pip install numpy)"

        import queue as _queue

        self._audio_queue = _queue.Queue(maxsize=400)
        self._pyaudio_instance = pyaudio.PyAudio()

        if self._vad_enabled:
            try:
                import webrtcvad  # type: ignore[import-untyped]
                self._vad = webrtcvad.Vad(self._vad_sensitivity)
            except ImportError:
                logger.info("[AudioCaptureStage] webrtcvad unavailable, continuing without VAD")
                self._vad_enabled = False

        try:
            self._stream = self._pyaudio_instance.open(
                format=self._pyaudio_instance.get_format_from_width(2),
                channels=1,
                rate=self._sample_rate,
                input=True,
                input_device_index=self._input_device,
                frames_per_buffer=int(self._sample_rate * 0.05),
                stream_callback=self._on_audio,
            )
        except Exception as exc:
            self._terminate_pyaudio()
            return f"Failed to open audio input stream: {exc}"

        self._initialized = True
        return None

    def _terminate_pyaudio(self) -> None:
        if self._pyaudio_instance is not None:
            try:
                self._pyaudio_instance.terminate()
            except Exception:
                pass
            self._pyaudio_instance = None

    # ------------------------------------------------------------------
    # PyAudio stream callback (runs on PyAudio's I/O thread)
    # ------------------------------------------------------------------

    def _on_audio(self, in_data: bytes, frame_count: int, time_info: Any, status_flags: int) -> tuple:
        """Non-blocking callback that applies volume scaling and VAD,
        then enqueues speech chunks (or *None* silence sentinels)."""
        import numpy as np
        import pyaudio as _pa

        if status_flags:
            logger.debug("[AudioCaptureStage] stream status: %s", status_flags)

        audio_data = np.frombuffer(in_data, dtype=np.int16)

        if self._input_volume != 1.0:
            audio_data = np.clip(
                audio_data.astype(np.float32) * self._input_volume,
                -32768, 32767,
            ).astype(np.int16)
            in_data = audio_data.tobytes()

        if self._vad_enabled and self._vad is not None:
            try:
                if not self._vad.is_speech(in_data, self._sample_rate):
                    try:
                        self._audio_queue.put_nowait(None)
                    except Exception:
                        pass
                    return (in_data, _pa.paContinue)
            except Exception:
                pass

        try:
            self._audio_queue.put_nowait(audio_data)
        except Exception:
            pass  # drop frame rather than block the audio thread

        return (in_data, _pa.paContinue)

    # ------------------------------------------------------------------
    # execute / cleanup
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Accumulate audio until a silence gap or max duration, then
        return the complete utterance buffer."""
        start = time.perf_counter()
        self._stop_event.clear()

        # Injected audio_source path (backward compat / testing)
        if self._audio_source is not None:
            try:
                frames = input_data.get("frames", 1024)
                audio_buffer = self._audio_source.read(frames)
                elapsed = (time.perf_counter() - start) * 1000
                return StageResult(
                    success=True,
                    data={"audio_buffer": audio_buffer},
                    duration_ms=elapsed,
                )
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error("AudioCaptureStage failed: [%s] %s", type(exc).__name__, exc)
                return StageResult(success=False, error=str(exc), duration_ms=elapsed)

        # Self-managed PyAudio capture with VAD-based utterance detection
        err = self._ensure_initialized()
        if err:
            return StageResult(success=False, error=err)

        import numpy as np
        import queue as _queue

        silence_threshold = input_data.get("silence_threshold", self._silence_threshold)
        max_duration = input_data.get("max_buffer_duration", self._max_buffer_duration)
        min_length = input_data.get("min_audio_length", self._min_audio_length)

        audio_chunks: list[Any] = []
        buffer_duration = 0.0
        last_speech = time.time()

        while not self._stop_event.is_set():
            try:
                chunk = self._audio_queue.get(timeout=0.05)
            except _queue.Empty:
                silence = time.time() - last_speech
                if audio_chunks and silence > silence_threshold:
                    break
                # Yield control when idle for too long with no speech at all
                if not audio_chunks and silence > max_duration + 1.0:
                    elapsed = (time.perf_counter() - start) * 1000
                    return StageResult(
                        success=True,
                        data={"audio_buffer": None},
                        duration_ms=elapsed,
                    )
                continue

            if chunk is None:
                # Silence sentinel from VAD
                if audio_chunks and (time.time() - last_speech) > silence_threshold:
                    break
                continue

            audio_chunks.append(chunk)
            buffer_duration += len(chunk) / self._sample_rate
            last_speech = time.time()

            if buffer_duration >= max_duration:
                break

        elapsed = (time.perf_counter() - start) * 1000

        if not audio_chunks or buffer_duration < min_length:
            return StageResult(
                success=True,
                data={"audio_buffer": None},
                duration_ms=elapsed,
            )

        combined = np.concatenate(audio_chunks)
        return StageResult(
            success=True,
            data={
                "audio_buffer": combined,
                "buffer_duration": buffer_duration,
                "sample_rate": self._sample_rate,
            },
            duration_ms=elapsed,
        )

    def cleanup(self) -> None:
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._terminate_pyaudio()
        if self._audio_source is not None and hasattr(self._audio_source, "cleanup"):
            self._audio_source.cleanup()
        self._initialized = False


class SpeechToTextStage:
    """Converts an audio buffer to text using OpenAI Whisper.

    Loads the Whisper model lazily on first ``execute()`` and caches it
    for subsequent calls.  Supports GPU acceleration with fp16 when a
    CUDA device is available.

    When an external *stt_engine* with a
    ``transcribe(audio_buffer) -> str`` method is injected, the stage
    delegates to it instead -- useful for testing or alternative STT
    backends.
    """

    name = "speech_to_text"

    def __init__(
        self,
        stt_engine: Any = None,
        config: Any = None,
    ) -> None:
        self._stt_engine = stt_engine
        self._config: dict[str, Any] = config if isinstance(config, dict) else {}

        self._whisper_model_size: str = self._config.get("whisper_model", "base")
        self._use_gpu: bool = self._config.get("use_gpu", True)
        self._source_language: str = self._config.get("source_language", "en")
        self._bidirectional: bool = self._config.get("bidirectional", True)
        self._no_speech_threshold: float = self._config.get("no_speech_threshold", 0.5)

        self._whisper_model: Any = None
        self._whisper_device: str = "cpu"
        self._use_fp16: bool = False

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    def _ensure_model(self) -> str | None:
        """Load the Whisper model on first use.  Returns an error string
        or *None* on success."""
        if self._whisper_model is not None:
            return None

        try:
            import whisper  # type: ignore[import-untyped]
        except ImportError:
            return "whisper not installed (pip install openai-whisper)"
        try:
            import torch  # type: ignore[import-untyped]
        except ImportError:
            return "torch not installed (pip install torch)"

        device = "cuda" if self._use_gpu and torch.cuda.is_available() else "cpu"
        self._whisper_device = device
        self._use_fp16 = device == "cuda"

        try:
            logger.info(
                "[SpeechToTextStage] Loading Whisper '%s' on %s",
                self._whisper_model_size,
                device,
            )
            self._whisper_model = whisper.load_model(
                self._whisper_model_size, device=device,
            )
            logger.info("[SpeechToTextStage] Whisper model loaded")
        except Exception as exc:
            return f"Failed to load Whisper model: {exc}"

        return None

    # ------------------------------------------------------------------
    # execute / cleanup
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()

        audio_buffer = input_data.get("audio_buffer")
        if audio_buffer is None:
            return StageResult(
                success=True,
                data={
                    "transcribed_text": "",
                    "detected_language": self._source_language,
                },
                duration_ms=0,
            )

        # Injected STT engine path (backward compat / testing)
        if self._stt_engine is not None:
            try:
                text = self._stt_engine.transcribe(audio_buffer)
                elapsed = (time.perf_counter() - start) * 1000
                return StageResult(
                    success=True,
                    data={"transcribed_text": text},
                    duration_ms=elapsed,
                )
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(
                    "SpeechToTextStage failed: [%s] %s",
                    type(exc).__name__, exc,
                )
                return StageResult(
                    success=False, error=str(exc), duration_ms=elapsed,
                )

        # Self-managed Whisper transcription
        err = self._ensure_model()
        if err:
            return StageResult(success=False, error=err)

        try:
            import numpy as np
        except ImportError:
            return StageResult(
                success=False, error="numpy not installed (pip install numpy)",
            )

        try:
            # Normalise int16 -> float32 [-1, 1] as Whisper expects
            if audio_buffer.dtype != np.float32:
                audio_float = audio_buffer.astype(np.float32) / 32768.0
            else:
                audio_float = audio_buffer

            # Pin source language when not bidirectional so Whisper
            # skips its language-detection pass (~30 % faster).
            lang_hint = self._source_language if not self._bidirectional else None

            result = self._whisper_model.transcribe(
                audio_float,
                language=lang_hint,
                fp16=self._use_fp16,
                no_speech_threshold=self._no_speech_threshold,
                condition_on_previous_text=False,
            )

            text = result["text"].strip()
            detected_lang = result.get("language", self._source_language)

            elapsed = (time.perf_counter() - start) * 1000

            if not text:
                return StageResult(
                    success=True,
                    data={
                        "transcribed_text": "",
                        "detected_language": detected_lang,
                    },
                    duration_ms=elapsed,
                )

            logger.info(
                "[SpeechToTextStage] Transcribed (%s, %.2fs): %s",
                detected_lang,
                elapsed / 1000,
                text[:80],
            )
            return StageResult(
                success=True,
                data={
                    "transcribed_text": text,
                    "detected_language": detected_lang,
                },
                duration_ms=elapsed,
            )

        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(
                "SpeechToTextStage failed: [%s] %s",
                type(exc).__name__, exc,
            )
            return StageResult(
                success=False, error=str(exc), duration_ms=elapsed,
            )

    def cleanup(self) -> None:
        self._whisper_model = None
        if self._stt_engine is not None and hasattr(self._stt_engine, "cleanup"):
            self._stt_engine.cleanup()


class TTSStage:
    """Converts text to speech and plays it on an audio output device.

    Supports multiple TTS backends extracted from AudioTranslationPlugin:

    * **pyttsx3** system voices (default fallback)
    * **Coqui TTS** neural models
    * **Coqui voice cloning** with a reference audio file
    * **Voice packs** (bundled model + config zips)

    When an external *tts_engine* with a ``speak(text) -> bytes | None``
    method is injected, the stage delegates to it instead -- useful for
    testing or custom TTS backends.
    """

    name = "tts"

    def __init__(
        self,
        tts_engine: Any = None,
        config: Any = None,
        volume_ducker: Any = None,
    ) -> None:
        self._tts_engine = tts_engine
        self._config: dict[str, Any] = config if isinstance(config, dict) else {}

        self._voice_id: str | None = self._config.get("voice_id", None)
        self._tts_speed: int = self._config.get("tts_speed", 170)
        self._output_device: int | None = self._config.get("output_device", None)
        self._output_volume: float = self._config.get("output_volume", 100) / 100.0

        self._duck_enabled: bool = self._config.get("duck_enabled", False)
        self._duck_level: int = self._config.get("duck_level", 20)
        self._volume_ducker = volume_ducker

        self._tts_type: str | None = None
        self._voice_reference_file: str | None = None
        self._tts_lock = threading.Lock()
        self._pyaudio_instance: Any = None
        self._output_stream: Any = None
        self._output_stream_rate: int | None = None
        self._managed_engine: Any = None
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> str | None:
        """Set up the TTS engine on first call.  Returns an error string
        or *None* on success."""
        if self._initialized:
            return None

        if self._tts_engine is not None:
            self._initialized = True
            return None

        err = self._init_tts_engine()
        if err:
            return err

        self._initialized = True
        return None

    def _init_tts_engine(self) -> str | None:
        """Initialise a TTS engine based on ``voice_id`` selection.

        Tries backends in order: custom voice clone -> voice pack ->
        Coqui neural model -> pyttsx3 system voice -> Coqui default.
        Returns an error string only when *all* backends fail.
        """
        voice_id = self._voice_id

        # ----- Custom voice (Coqui voice cloning with reference audio) -----
        if voice_id and voice_id.startswith("custom:"):
            try:
                from plugins.enhancers.audio_translation.voice_manager import (
                    get_custom_voices,
                )
                voice = next(
                    (v for v in get_custom_voices() if v["id"] == voice_id),
                    None,
                )
                if voice and os.path.exists(voice.get("reference_file", "")):
                    from TTS.api import TTS  # type: ignore[import-untyped]
                    self._managed_engine = TTS(
                        model_name="tts_models/multilingual/multi-dataset/your_tts",
                    )
                    self._tts_type = "coqui_clone"
                    self._voice_reference_file = voice["reference_file"]
                    logger.info(
                        "[TTSStage] TTS: custom voice clone '%s'", voice["name"],
                    )
                    return None
            except Exception as exc:
                logger.warning(
                    "[TTSStage] Custom voice failed, falling back: %s", exc,
                )

        # ----- Voice pack (bundled model) -----
        if voice_id and voice_id.startswith("pack:"):
            try:
                from plugins.enhancers.audio_translation.voice_manager import (
                    get_voice_packs,
                )
                pack = next(
                    (p for p in get_voice_packs() if p["id"] == voice_id),
                    None,
                )
                if pack:
                    from TTS.api import TTS  # type: ignore[import-untyped]
                    model_path = os.path.join(
                        pack["path"],
                        pack["manifest"].get("model_file", "model.pth"),
                    )
                    config_path = os.path.join(
                        pack["path"],
                        pack["manifest"].get("config_file", "config.json"),
                    )
                    self._managed_engine = TTS(
                        model_path=model_path, config_path=config_path,
                    )
                    self._tts_type = "voice_pack"
                    logger.info(
                        "[TTSStage] TTS: voice pack '%s'", pack["name"],
                    )
                    return None
            except Exception as exc:
                logger.warning(
                    "[TTSStage] Voice pack failed, falling back: %s", exc,
                )

        # ----- Coqui neural model (selected by model id) -----
        if voice_id and not voice_id.startswith("pyttsx3:"):
            try:
                from TTS.api import TTS  # type: ignore[import-untyped]
                self._managed_engine = TTS(model_name=voice_id)
                self._tts_type = "coqui"
                logger.info("[TTSStage] TTS: Coqui model '%s'", voice_id)
                return None
            except Exception as exc:
                logger.warning(
                    "[TTSStage] Coqui model '%s' failed: %s", voice_id, exc,
                )

        # ----- pyttsx3 system voice (specific voice or default) -----
        try:
            import pyttsx3  # type: ignore[import-untyped]
            self._managed_engine = pyttsx3.init()
            self._managed_engine.setProperty("rate", self._tts_speed)
            if voice_id and voice_id.startswith("pyttsx3:"):
                real_id = voice_id[len("pyttsx3:"):]
                for v in self._managed_engine.getProperty("voices"):
                    if v.id == real_id or v.name == real_id:
                        self._managed_engine.setProperty("voice", v.id)
                        break
            self._tts_type = "pyttsx3"
            logger.info("[TTSStage] TTS: pyttsx3 system voice")
            return None
        except Exception as exc:
            logger.warning("[TTSStage] pyttsx3 not available: %s", exc)

        # ----- Last resort: Coqui default -----
        try:
            from TTS.api import TTS  # type: ignore[import-untyped]
            self._managed_engine = TTS(
                model_name="tts_models/multilingual/multi-dataset/your_tts",
            )
            self._tts_type = "coqui"
            logger.info("[TTSStage] TTS: Coqui default fallback")
            return None
        except Exception as exc:
            return f"No TTS engine available: {exc}"

    # ------------------------------------------------------------------
    # Speech synthesis helpers
    # ------------------------------------------------------------------

    def _speak(self, text: str, language: str) -> bytes | None:
        """Generate speech from *text*.  Returns raw audio bytes when a
        file-based backend (Coqui) is used, or *None* for pyttsx3
        (which plays audio directly)."""
        engine = (
            self._tts_engine
            if self._tts_engine is not None
            else self._managed_engine
        )
        if engine is None:
            raise RuntimeError("No TTS engine initialised")

        # Injected engine with simple speak() API
        if self._tts_engine is not None:
            return self._tts_engine.speak(text)

        if self._tts_type == "pyttsx3":
            with self._tts_lock:
                engine.say(text)
                engine.runAndWait()
            return None

        # Coqui-based engines write to a temp wav then play it
        from app.utils.path_utils import ensure_dir

        processing_dir = ensure_dir("temp_processing")
        tmp_path = str(processing_dir / f"tts_{threading.get_ident()}.wav")

        try:
            if self._tts_type == "coqui_clone" and self._voice_reference_file:
                engine.tts_to_file(
                    text=text,
                    file_path=tmp_path,
                    speaker_wav=self._voice_reference_file,
                    language=language,
                )
            else:
                engine.tts_to_file(
                    text=text, file_path=tmp_path, language=language,
                )
            return self._play_audio_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _play_audio_file(self, audio_file: str) -> bytes | None:
        """Play a wav file to the configured output device.  Returns the
        raw PCM bytes so callers can forward them if needed."""
        try:
            from scipy.io import wavfile  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "[TTSStage] scipy not installed — cannot play audio file",
            )
            return None

        import numpy as np

        sample_rate, audio_data = wavfile.read(audio_file)

        if self._output_volume != 1.0:
            audio_data = np.clip(
                audio_data.astype(np.float32) * self._output_volume,
                -32768, 32767,
            ).astype(np.int16)

        raw_bytes: bytes = audio_data.tobytes()

        try:
            if self._pyaudio_instance is None:
                import pyaudio  # type: ignore[import-untyped]
                self._pyaudio_instance = pyaudio.PyAudio()

            if self._output_stream is not None and self._output_stream_rate != sample_rate:
                try:
                    self._output_stream.stop_stream()
                    self._output_stream.close()
                except Exception:
                    pass
                self._output_stream = None

            if self._output_stream is None:
                self._output_stream = self._pyaudio_instance.open(
                    format=self._pyaudio_instance.get_format_from_width(2),
                    channels=1,
                    rate=sample_rate,
                    output=True,
                    output_device_index=self._output_device,
                )
                self._output_stream_rate = sample_rate

            self._output_stream.write(raw_bytes)
        except Exception as exc:
            logger.error("[TTSStage] Audio playback error: %s", exc)

        return raw_bytes

    # ------------------------------------------------------------------
    # execute / cleanup
    # ------------------------------------------------------------------

    def execute(self, input_data: dict[str, Any]) -> StageResult:
        start = time.perf_counter()

        err = self._ensure_initialized()
        if err:
            return StageResult(success=False, error=err)

        # Resolve the text to speak: prefer "translations", fall back
        # to "transcribed_text" (direct STT -> TTS without translation).
        text: Any = input_data.get("translations")
        if isinstance(text, list):
            text = " ".join(str(t) for t in text if t)
        if not text:
            text = input_data.get("transcribed_text", "")
        if not text:
            elapsed = (time.perf_counter() - start) * 1000
            return StageResult(
                success=True, data={"spoken": False}, duration_ms=elapsed,
            )

        language = input_data.get(
            "target_language",
            input_data.get("detected_language", "en"),
        )

        try:
            if self._duck_enabled and self._volume_ducker is not None:
                with self._volume_ducker.ducked(self._duck_level):
                    audio_out = self._speak(text, language)
            else:
                audio_out = self._speak(text, language)
            elapsed = (time.perf_counter() - start) * 1000
            return StageResult(
                success=True,
                data={"spoken": True, "audio_output": audio_out},
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("TTSStage failed: [%s] %s", type(exc).__name__, exc)
            return StageResult(
                success=False, error=str(exc), duration_ms=elapsed,
            )

    def cleanup(self) -> None:
        if self._volume_ducker is not None:
            try:
                self._volume_ducker.restore()
            except Exception:
                pass

        if self._output_stream is not None:
            try:
                self._output_stream.stop_stream()
                self._output_stream.close()
            except Exception:
                pass
            self._output_stream = None

        if self._pyaudio_instance is not None:
            try:
                self._pyaudio_instance.terminate()
            except Exception:
                pass
            self._pyaudio_instance = None

        if self._managed_engine is not None:
            if hasattr(self._managed_engine, "stop"):
                try:
                    self._managed_engine.stop()
                except Exception:
                    pass
            self._managed_engine = None

        if self._tts_engine is not None and hasattr(self._tts_engine, "cleanup"):
            self._tts_engine.cleanup()

        self._cleanup_temp_wav_files()
        self._initialized = False

    def _cleanup_temp_wav_files(self) -> None:
        """Remove leftover TTS .wav files from the temp_processing directory."""
        try:
            from app.utils.path_utils import get_dir
            processing_dir = get_dir("temp_processing")
            if not processing_dir.is_dir():
                return
            for f in processing_dir.glob("tts_*.wav"):
                try:
                    f.unlink()
                except OSError:
                    pass
        except Exception:
            pass
