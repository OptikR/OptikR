"""
ModuleTestWorker - Background thread for running individual module and pipeline tests.

Each test method captures timing, reports pass/fail status, and emits
actionable recommendations when a component is not working.
"""

import logging
import time
import traceback

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ModuleTestWorker(QThread):
    """Worker thread that runs module-level and full-pipeline diagnostic tests.

    Signals
    -------
    progress(str)
        Emitted with a human-readable log line during test execution.
    test_finished(str, bool)
        ``(test_name, passed)`` — emitted once per test when it completes.
    all_finished()
        Emitted after every requested test has finished.
    """

    progress = pyqtSignal(str)
    test_finished = pyqtSignal(str, bool)
    all_finished = pyqtSignal()

    # Ordered list of recognised test names
    TEST_CAPTURE = "capture"
    TEST_OCR = "ocr"
    TEST_TRANSLATION = "translation"
    TEST_OVERLAY = "overlay"
    TEST_FULL_PIPELINE = "full_pipeline"

    def __init__(
        self,
        pipeline,
        config_manager=None,
        tests: list | None = None,
        parent=None,
    ):
        """
        Parameters
        ----------
        pipeline:
            ``StartupPipeline`` instance that owns capture / OCR /
            translation layers and the overlay system.
        config_manager:
            Application configuration manager for reading language /
            engine settings.
        tests:
            Which tests to run (subset of ``TEST_*`` constants).
            ``None`` means run all five in order.
        """
        super().__init__(parent)
        self.pipeline = pipeline
        self.config_manager = config_manager
        self.tests = tests or [
            self.TEST_CAPTURE,
            self.TEST_OCR,
            self.TEST_TRANSLATION,
            self.TEST_OVERLAY,
            self.TEST_FULL_PIPELINE,
        ]

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self):
        dispatch = {
            self.TEST_CAPTURE: self._test_capture,
            self.TEST_OCR: self._test_ocr,
            self.TEST_TRANSLATION: self._test_translation,
            self.TEST_OVERLAY: self._test_overlay,
            self.TEST_FULL_PIPELINE: self._test_full_pipeline,
        }
        for name in self.tests:
            handler = dispatch.get(name)
            if handler:
                try:
                    handler()
                except Exception:
                    self._log(traceback.format_exc())
                    self._fail(name, "Unexpected error — see output above.")
        self.all_finished.emit()

    # ------------------------------------------------------------------
    # Individual tests
    # ------------------------------------------------------------------

    def _test_capture(self):
        name = self.TEST_CAPTURE
        self._header(name, "Screen Capture")

        if not self.pipeline:
            return self._fail(name, "Pipeline is not initialised.",
                              self._capture_recommendations())

        capture_layer = getattr(self.pipeline, "capture_layer", None)
        if not capture_layer:
            return self._fail(name, "Capture layer is not available.",
                              self._capture_recommendations())

        capture_region = getattr(self.pipeline, "capture_region", None)

        try:
            from app.interfaces import CaptureSource
            from app.models import CaptureRegion, Rectangle

            if capture_region is None:
                capture_region = CaptureRegion(
                    rectangle=Rectangle(x=0, y=0, width=800, height=600),
                    monitor_id=0,
                )
                self._log("  No capture region set — using default (0,0 800x600)")

            source = CaptureSource.CUSTOM_REGION

            start = time.perf_counter()
            frame = capture_layer.capture_frame(source, capture_region)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if frame is None:
                return self._fail(name, "capture_frame() returned None.",
                                  self._capture_recommendations())

            frame_data = frame.data if hasattr(frame, "data") else frame
            if hasattr(frame_data, "shape"):
                h, w = frame_data.shape[:2]
                self._log(f"  Frame dimensions : {w} x {h}")
                self._log(f"  Capture time     : {elapsed_ms:.1f} ms")
            else:
                self._log(f"  Capture time     : {elapsed_ms:.1f} ms")

            self._pass(name)

        except Exception as exc:
            self._log(f"  Error: {exc}")
            self._log(traceback.format_exc())
            self._fail(name, str(exc), self._capture_recommendations())

    # ---------------------------------------------------------------

    def _test_ocr(self):
        name = self.TEST_OCR
        self._header(name, "OCR Text Extraction")

        if not self.pipeline:
            return self._fail(name, "Pipeline is not initialised.",
                              self._ocr_recommendations())

        ocr_layer = getattr(self.pipeline, "ocr_layer", None)
        if not ocr_layer:
            return self._fail(name, "OCR layer is not available.",
                              self._ocr_recommendations())

        try:
            import numpy as np
            from app.models import Frame, CaptureRegion, Rectangle

            capture_region = getattr(self.pipeline, "capture_region", None)
            frame_data = None

            # Try to capture a live frame first
            capture_layer = getattr(self.pipeline, "capture_layer", None)
            if capture_layer and capture_region:
                try:
                    from app.interfaces import CaptureSource
                    live_frame = capture_layer.capture_frame(
                        CaptureSource.CUSTOM_REGION, capture_region,
                    )
                    if live_frame is not None:
                        frame_data = live_frame.data if hasattr(live_frame, "data") else live_frame
                        self._log("  Using live captured frame for OCR test")
                except Exception as e:
                    logger.debug("Live frame capture failed, will use synthetic image: %s", e)

            # Fallback: synthetic image with text-like content
            if frame_data is None:
                frame_data = np.full((200, 400, 3), 255, dtype=np.uint8)
                frame_data[50:150, 50:350] = 0
                self._log("  Using synthetic test image (no live capture available)")

            if capture_region is None:
                capture_region = CaptureRegion(
                    rectangle=Rectangle(x=0, y=0, width=frame_data.shape[1], height=frame_data.shape[0]),
                    monitor_id=0,
                )

            test_frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=capture_region,
            )

            engine_name = "unknown"
            if hasattr(ocr_layer, "config") and hasattr(ocr_layer.config, "default_engine"):
                engine_name = ocr_layer.config.default_engine
            self._log(f"  OCR engine : {engine_name}")

            start = time.perf_counter()
            results = ocr_layer.extract_text(test_frame)
            elapsed_ms = (time.perf_counter() - start) * 1000

            block_count = len(results) if results else 0
            self._log(f"  Text blocks detected : {block_count}")
            self._log(f"  Processing time      : {elapsed_ms:.1f} ms")

            if results:
                for i, block in enumerate(results[:3], 1):
                    text = block.text if hasattr(block, "text") else str(block)
                    conf = block.confidence if hasattr(block, "confidence") else 0.0
                    self._log(f"  Block {i}: \"{text[:60]}\" (confidence: {conf:.2f})")

            self._pass(name)

        except Exception as exc:
            self._log(f"  Error: {exc}")
            self._log(traceback.format_exc())
            self._fail(name, str(exc), self._ocr_recommendations())

    # ---------------------------------------------------------------

    def _test_translation(self):
        name = self.TEST_TRANSLATION
        self._header(name, "Translation Engine")

        if not self.pipeline:
            return self._fail(name, "Pipeline is not initialised.",
                              self._translation_recommendations())

        translation_layer = getattr(self.pipeline, "translation_layer", None)
        if not translation_layer:
            return self._fail(name, "Translation layer is not available.",
                              self._translation_recommendations())

        try:
            sample_text = "Hello, how are you today?"

            src_lang = "en"
            tgt_lang = "de"
            engine = "marianmt"

            if self.config_manager:
                src_lang = self.config_manager.get_setting("translation.source_language", "en")
                tgt_lang = self.config_manager.get_setting("translation.target_language", "de")
                engine = self.config_manager.get_setting("translation.engine", "marianmt")

            self._log(f"  Sample text : \"{sample_text}\"")
            self._log(f"  Engine      : {engine}")
            self._log(f"  Direction   : {src_lang} -> {tgt_lang}")

            # Pre-flight: check engine availability before calling translate()
            available_engines = []
            if hasattr(translation_layer, "get_available_engines"):
                available_engines = translation_layer.get_available_engines() or []
                self._log(f"  Available   : {available_engines if available_engines else '(none)'}")

            if not available_engines:
                return self._fail(
                    name,
                    f"No translation engines are available. "
                    f"Engine '{engine}' is registered but not loaded/ready.",
                    self._translation_recommendations(),
                )

            pair_engines = []
            if hasattr(translation_layer, "get_engines_for_language_pair"):
                pair_engines = translation_layer.get_engines_for_language_pair(src_lang, tgt_lang) or []

            if available_engines and not pair_engines:
                return self._fail(
                    name,
                    f"No engine supports the language pair {src_lang} -> {tgt_lang}. "
                    f"Available engines: {available_engines}",
                    self._translation_recommendations(),
                )

            start = time.perf_counter()
            translated = translation_layer.translate(
                sample_text, engine, src_lang, tgt_lang, {},
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            if not translated or not translated.strip():
                return self._fail(
                    name,
                    "Translation returned empty result.",
                    self._translation_recommendations(),
                )

            # Detect silent failure: translate() returns original text on error
            if src_lang != tgt_lang and translated.strip() == sample_text.strip():
                return self._fail(
                    name,
                    f"Translation returned the original text unchanged "
                    f"(engine '{engine}' likely failed silently). "
                    f"Check console for 'Translation failed' errors.",
                    self._translation_recommendations(),
                )

            self._log(f"  Result      : \"{translated}\"")
            self._log(f"  Time        : {elapsed_ms:.1f} ms")

            self._pass(name)

        except Exception as exc:
            self._log(f"  Error: {exc}")
            self._log(traceback.format_exc())
            self._fail(name, str(exc), self._translation_recommendations())

    # ---------------------------------------------------------------

    def _test_overlay(self):
        name = self.TEST_OVERLAY
        self._header(name, "Overlay System")

        if not self.pipeline:
            return self._fail(name, "Pipeline is not initialised.",
                              self._overlay_recommendations())

        overlay_system = getattr(self.pipeline, "overlay_system", None)
        if not overlay_system:
            return self._fail(name, "Overlay system is not initialised.",
                              self._overlay_recommendations())

        try:
            has_show = hasattr(overlay_system, "show_translation")
            has_hide = (
                hasattr(overlay_system, "hide_all_translations")
                or hasattr(overlay_system, "hide_all")
            )

            if not has_show:
                return self._fail(
                    name,
                    "Overlay system does not support show_translation().",
                    self._overlay_recommendations(),
                )

            self._log("  Overlay system found and supports show_translation()")

            # Show a short-lived test overlay
            test_text = "[OptikR Test] Overlay OK"
            self._log(f"  Showing test overlay for ~2 seconds...")

            try:
                overlay_system.show_translation(test_text, (100, 100))
                self._log("  show_translation() succeeded")
            except Exception as show_exc:
                return self._fail(
                    name,
                    f"show_translation() raised: {show_exc}",
                    self._overlay_recommendations(),
                )

            time.sleep(2)

            # Hide overlays
            try:
                if hasattr(overlay_system, "hide_all_translations"):
                    overlay_system.hide_all_translations()
                elif hasattr(overlay_system, "hide_all"):
                    overlay_system.hide_all()
                self._log("  Test overlay hidden")
            except Exception:
                self._log("  Warning: could not hide test overlay")

            self._pass(name)

        except Exception as exc:
            self._log(f"  Error: {exc}")
            self._log(traceback.format_exc())
            self._fail(name, str(exc), self._overlay_recommendations())

    # ---------------------------------------------------------------

    def _test_full_pipeline(self):
        name = self.TEST_FULL_PIPELINE
        self._header(name, "Full Pipeline Dry-Run")

        if not self.pipeline:
            return self._fail(name, "Pipeline is not initialised.",
                              self._full_pipeline_recommendations())

        capture_layer = getattr(self.pipeline, "capture_layer", None)
        ocr_layer = getattr(self.pipeline, "ocr_layer", None)
        translation_layer = getattr(self.pipeline, "translation_layer", None)
        overlay_system = getattr(self.pipeline, "overlay_system", None)

        if not all([capture_layer, ocr_layer, translation_layer]):
            missing = []
            if not capture_layer:
                missing.append("capture")
            if not ocr_layer:
                missing.append("OCR")
            if not translation_layer:
                missing.append("translation")
            return self._fail(
                name,
                f"Missing component(s): {', '.join(missing)}.",
                self._full_pipeline_recommendations(),
            )

        timings = {}

        # Stage 1 — Capture
        self._log("  [1/4] Capturing frame...")
        try:
            from app.interfaces import CaptureSource
            from app.models import CaptureRegion, Rectangle, Frame

            capture_region = getattr(self.pipeline, "capture_region", None)
            if capture_region is None:
                capture_region = CaptureRegion(
                    rectangle=Rectangle(x=0, y=0, width=800, height=600),
                    monitor_id=0,
                )
                self._log("        (no region set — using default 800x600)")

            start = time.perf_counter()
            frame = capture_layer.capture_frame(CaptureSource.CUSTOM_REGION, capture_region)
            timings["Capture"] = (time.perf_counter() - start) * 1000

            if frame is None:
                return self._fail(name, "Capture returned None.",
                                  self._full_pipeline_recommendations())

            frame_data = frame.data if hasattr(frame, "data") else frame
            if hasattr(frame_data, "shape"):
                h, w = frame_data.shape[:2]
                self._log(f"        OK — {w}x{h} in {timings['Capture']:.1f} ms")
            else:
                self._log(f"        OK — {timings['Capture']:.1f} ms")
        except Exception as exc:
            self._log(f"        FAILED — {exc}")
            return self._fail(name, f"Capture stage failed: {exc}",
                              self._full_pipeline_recommendations())

        # Stage 2 — OCR
        self._log("  [2/4] Running OCR...")
        try:
            if not isinstance(frame, Frame):
                frame = Frame(
                    data=frame_data,
                    timestamp=time.time(),
                    source_region=capture_region,
                )

            start = time.perf_counter()
            ocr_results = ocr_layer.extract_text(frame)
            timings["OCR"] = (time.perf_counter() - start) * 1000

            block_count = len(ocr_results) if ocr_results else 0
            self._log(f"        OK — {block_count} block(s) in {timings['OCR']:.1f} ms")
        except Exception as exc:
            self._log(f"        FAILED — {exc}")
            return self._fail(name, f"OCR stage failed: {exc}",
                              self._full_pipeline_recommendations())

        # Stage 3 — Translation
        self._log("  [3/4] Translating...")
        try:
            src_lang = "en"
            tgt_lang = "de"
            engine = "marianmt"
            if self.config_manager:
                src_lang = self.config_manager.get_setting("translation.source_language", "en")
                tgt_lang = self.config_manager.get_setting("translation.target_language", "de")
                engine = self.config_manager.get_setting("translation.engine", "marianmt")

            # Pre-flight: verify an engine is actually available for this pair
            available_engines = []
            if hasattr(translation_layer, "get_available_engines"):
                available_engines = translation_layer.get_available_engines() or []
            if not available_engines:
                self._log(f"        FAILED — no translation engines available")
                return self._fail(
                    name,
                    f"Translation stage failed: no engines available "
                    f"(engine '{engine}' is not loaded/ready).",
                    self._full_pipeline_recommendations(),
                )

            pair_engines = []
            if hasattr(translation_layer, "get_engines_for_language_pair"):
                pair_engines = translation_layer.get_engines_for_language_pair(src_lang, tgt_lang) or []
            if available_engines and not pair_engines:
                self._log(f"        FAILED — no engine supports {src_lang} -> {tgt_lang}")
                return self._fail(
                    name,
                    f"Translation stage failed: no engine supports "
                    f"{src_lang} -> {tgt_lang}. Available engines: {available_engines}",
                    self._full_pipeline_recommendations(),
                )

            translated_count = 0
            silent_failures = 0
            start = time.perf_counter()

            if ocr_results:
                for block in ocr_results:
                    text = block.text if hasattr(block, "text") else str(block)
                    if text.strip():
                        result = translation_layer.translate(text, engine, src_lang, tgt_lang, {})
                        translated_count += 1
                        if src_lang != tgt_lang and result and result.strip() == text.strip():
                            silent_failures += 1
            else:
                sample = "Hello"
                result = translation_layer.translate(sample, engine, src_lang, tgt_lang, {})
                translated_count = 1
                self._log("        (no OCR text — used sample string)")
                if src_lang != tgt_lang and result and result.strip() == sample.strip():
                    silent_failures += 1

            timings["Translation"] = (time.perf_counter() - start) * 1000

            if silent_failures == translated_count and translated_count > 0:
                self._log(f"        FAILED — all {translated_count} translation(s) returned "
                          f"original text unchanged (engine failed silently)")
                return self._fail(
                    name,
                    f"Translation stage failed: engine '{engine}' returned input "
                    f"text unchanged for {src_lang} -> {tgt_lang}.",
                    self._full_pipeline_recommendations(),
                )

            self._log(f"        OK — {translated_count} item(s) in {timings['Translation']:.1f} ms")
            if silent_failures > 0:
                self._log(f"        ⚠ {silent_failures}/{translated_count} item(s) may not "
                          f"have been translated (returned unchanged)")
        except Exception as exc:
            self._log(f"        FAILED — {exc}")
            return self._fail(name, f"Translation stage failed: {exc}",
                              self._full_pipeline_recommendations())

        # Stage 4 — Overlay check
        self._log("  [4/4] Checking overlay system...")
        overlay_ok = overlay_system is not None and hasattr(overlay_system, "show_translation")
        timings["Overlay check"] = 0.0
        if overlay_ok:
            self._log("        OK — overlay system available")
        else:
            self._log("        SKIPPED — overlay system not available (non-fatal)")

        # Summary
        total_ms = sum(timings.values())
        self._log("")
        self._log("  Stage timings:")
        for stage, ms in timings.items():
            self._log(f"    {stage:20s} : {ms:8.1f} ms")
        self._log(f"    {'TOTAL':20s} : {total_ms:8.1f} ms")

        self._pass(name)

    # ------------------------------------------------------------------
    # Recommendation sets
    # ------------------------------------------------------------------

    @staticmethod
    def _capture_recommendations():
        return [
            "Ensure a capture method is selected in the Capture tab.",
            "Try switching the capture method to 'Screenshot (CPU)' as a fallback.",
            "Check that your display driver is up to date.",
            "If using DirectX capture, ensure no other screen-capture software is running.",
        ]

    @staticmethod
    def _ocr_recommendations():
        return [
            "Check that an OCR engine is selected in the OCR tab.",
            "Verify the OCR model is downloaded (check the Storage tab).",
            "If using EasyOCR / PaddleOCR with GPU, ensure CUDA is properly installed.",
            "Try switching to Tesseract (CPU-based, no GPU required).",
        ]

    @staticmethod
    def _translation_recommendations():
        return [
            "Check that a translation engine is configured in the Translation tab.",
            "For MarianMT: ensure the model for your language pair is downloaded.",
            "For cloud engines (Google / DeepL / Azure): verify your API key is valid.",
            "Try the 'Google Free' engine which requires no API key.",
        ]

    @staticmethod
    def _overlay_recommendations():
        return [
            "Ensure PyQt6 is properly installed.",
            "Check overlay settings in the Overlay tab.",
            "Try restarting the application.",
            "If using multiple monitors, check monitor detection in the Capture tab.",
        ]

    @staticmethod
    def _full_pipeline_recommendations():
        return [
            "Run individual module tests above to identify which component is failing.",
            "Check the System Diagnostics section for hardware / software issues.",
            "Ensure a capture region is set before running the pipeline.",
        ]

    # ------------------------------------------------------------------
    # Logging / result helpers
    # ------------------------------------------------------------------

    def _log(self, message: str):
        self.progress.emit(message)

    def _header(self, test_id: str, title: str):
        self._log("")
        self._log(f"{'=' * 60}")
        self._log(f"  TEST: {title}")
        self._log(f"{'=' * 60}")

    def _pass(self, test_id: str):
        self._log("")
        self._log(f"  RESULT: PASS")
        self.test_finished.emit(test_id, True)

    def _fail(self, test_id: str, reason: str, recommendations: list | None = None):
        self._log("")
        self._log(f"  RESULT: FAIL — {reason}")
        if recommendations:
            self._log("")
            self._log("  Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                self._log(f"    {i}. {rec}")
        self.test_finished.emit(test_id, False)
