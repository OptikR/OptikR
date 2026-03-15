"""
Frame Skip Optimizer Plugin
Skips processing of unchanged frames to reduce CPU usage.

Two content modes:
- static:  For manga, wikipedia, etc. Uses MSE thumbnail comparison + adaptive
           backoff. Cheap and effective when content rarely changes.
- dynamic: For games, video, live UIs. Uses the frame differencing engine to
           detect which regions changed, enabling partial OCR on just those areas.

Both modes skip identical frames immediately (no warmup gate).
"""

import hashlib
import logging
import numpy as np
from typing import Any
from PIL import Image


class FrameSkipOptimizer:
    """Skips unchanged frames with optional region-level change detection.

    content_mode='static' (default):
        Thumbnail MSE comparison + adaptive backoff. ~1-2ms per frame.
        Best for content that stays still most of the time.

    content_mode='dynamic':
        Same thumbnail check for full-skip, but when a change IS detected,
        runs the frame differencing engine on the full frame to identify
        which regions changed. Adds ~5-10ms but enables partial OCR.
    """

    # Backoff tiers: (skip_threshold, extra_sleep_seconds)
    BACKOFF_TIERS = [
        (10, 0.0),
        (30, 0.1),
        (60, 0.3),
        (120, 0.5),
        (999999, 1.0),
    ]

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.threshold = config.get('similarity_threshold', 0.97)
        self.max_skip = config.get('max_skip_frames', 300)
        self.method = config.get('comparison_method', 'mse')
        self.enable_backoff = config.get('adaptive_backoff', True)
        self.content_mode = config.get('content_mode', 'static')
        self.manga_mode = config.get('manga_mode', False)

        # Frame differencing engine (lazy-loaded, only used in dynamic mode)
        self._diff_engine = None
        self._previous_full_frame = None  # Full-res frame for differencing

        # State
        self.previous_frame = None  # Thumbnail for MSE
        self.previous_hash = None
        self.consecutive_skips = 0

        # Statistics
        self.total_frames = 0
        self.skipped_frames = 0
        self.processed_frames = 0
        self.partial_ocr_frames = 0

        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Frame differencing (dynamic mode only)
    # ------------------------------------------------------------------

    def _get_diff_engine(self):
        """Lazy-load the frame differencing engine."""
        if self._diff_engine is None:
            try:
                from app.preprocessing.frame_differencing import (
                    FrameDifferenceEngine, DifferenceConfig,
                    DifferenceMethod, SensitivityLevel
                )
                diff_config = DifferenceConfig(
                    method=DifferenceMethod.ABSOLUTE,
                    sensitivity=SensitivityLevel.MEDIUM,
                    enable_noise_reduction=True,
                    enable_morphology=True,
                    min_change_area=100,
                )
                self._diff_engine = FrameDifferenceEngine(config=diff_config)
                self.logger.info("[FRAME SKIP] Frame differencing engine loaded (dynamic mode)")
            except Exception as e:
                self.logger.warning(f"[FRAME SKIP] Could not load frame differencing engine: {e}")
                self._diff_engine = None
        return self._diff_engine

    def _detect_changed_regions(self, frame: np.ndarray) -> list[dict[str, Any]] | None:
        """Use frame differencing to find which regions changed.

        Returns a list of {'id': int, 'bbox': (x, y, w, h)} dicts suitable
        for passing to ocr_layer.extract_text_from_regions(), or None if
        differencing is unavailable or the whole frame changed.
        """
        engine = self._get_diff_engine()
        if engine is None or self._previous_full_frame is None:
            return None

        try:
            from app.models import Frame as FrameModel
            current = FrameModel(data=frame, timestamp=0.0)
            previous = FrameModel(data=self._previous_full_frame, timestamp=0.0)

            result = engine.calculate_difference(current, previous)

            if not result.has_changes:
                return []  # Empty list = no changes (shouldn't happen since MSE said changed)

            significant = result.significant_changes
            if not significant:
                return None  # No significant regions, fall back to full OCR

            # If change covers most of the frame, not worth doing partial OCR
            if result.change_percentage > 0.5:
                return None

            regions = []
            for i, change in enumerate(significant):
                r = change.rectangle
                regions.append({
                    'id': i,
                    'bbox': (r.x, r.y, r.width, r.height),
                })

            self.partial_ocr_frames += 1
            return regions

        except Exception as e:
            self.logger.debug(f"[FRAME SKIP] Region detection failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Comparison methods
    # ------------------------------------------------------------------

    def _compute_hash(self, frame: np.ndarray) -> str:
        """Compute perceptual hash of frame."""
        img = Image.fromarray(frame)
        img = img.resize((16, 16), Image.Resampling.LANCZOS)
        img = img.convert('L')
        pixels = np.array(img).flatten()
        return hashlib.md5(pixels.tobytes()).hexdigest()

    _THUMB_SIZE = (256, 256)
    _BLOCK_SIZE = 8  # 32x32 grid of 8x8 blocks

    # Pixels that differ by more than this (0-255) are counted as "changed".
    _PIXEL_CHANGE_LEVEL = 12
    # If this fraction of pixels changed significantly, the frame is different.
    _PIXEL_CHANGE_CAP = 0.005  # 0.5%

    def _compute_mse(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Compute similarity between frames (0-1, higher = more similar).

        Three complementary checks (returns the minimum):

        1. **Global MSE** – catches large-scale brightness shifts.
        2. **Block-max MSE** – catches localised region changes.
        3. **Changed-pixel ratio** – catches text-content swaps where
           individual pixels shift by more than ``_PIXEL_CHANGE_LEVEL``
           but the overall MSE stays high because text-on-text changes
           are small in a thumbnail.
        """
        sz = self._THUMB_SIZE
        img1 = Image.fromarray(frame1).resize(sz)
        img2 = Image.fromarray(frame2).resize(sz)
        arr1 = np.array(img1, dtype=np.float32)
        arr2 = np.array(img2, dtype=np.float32)

        diff_sq = (arr1 - arr2) ** 2
        max_mse = 255.0 ** 2
        global_sim = 1.0 - (float(np.mean(diff_sq)) / max_mse)

        # Block-level: find the single most-changed block.
        if diff_sq.ndim == 3:
            block_diff = diff_sq.mean(axis=2)
        else:
            block_diff = diff_sq

        bs = self._BLOCK_SIZE
        h, w = block_diff.shape
        bh, bw = h // bs, w // bs
        trimmed = block_diff[:bh * bs, :bw * bs]
        blocks = trimmed.reshape(bh, bs, bw, bs).mean(axis=(1, 3))
        block_sim = 1.0 - (float(blocks.max()) / max_mse)

        # Changed-pixel ratio: count pixels that shifted by more than
        # the noise floor.  Highly sensitive to text-content swaps.
        diff_abs = np.abs(arr1 - arr2)
        if diff_abs.ndim == 3:
            diff_gray = diff_abs.max(axis=2)
        else:
            diff_gray = diff_abs
        changed_frac = float((diff_gray > self._PIXEL_CHANGE_LEVEL).mean())
        pixel_sim = 1.0 - (changed_frac / self._PIXEL_CHANGE_CAP)
        pixel_sim = max(0.0, min(1.0, pixel_sim))

        return min(global_sim, block_sim, pixel_sim)

    def _compute_ssim(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Compute structural similarity between frames (0-1, higher = more similar).

        Uses a simplified SSIM that operates on downscaled grayscale thumbnails
        for speed (~2-3ms per call).  Constants follow Wang et al. 2004.
        """
        size = self._THUMB_SIZE
        img1 = np.array(Image.fromarray(frame1).resize(size).convert("L"), dtype=np.float64)
        img2 = np.array(Image.fromarray(frame2).resize(size).convert("L"), dtype=np.float64)

        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2

        mu1 = img1.mean()
        mu2 = img2.mean()
        sigma1_sq = img1.var()
        sigma2_sq = img2.var()
        sigma12 = ((img1 - mu1) * (img2 - mu2)).mean()

        numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
        denominator = (mu1 ** 2 + mu2 ** 2 + C1) * (sigma1_sq + sigma2_sq + C2)
        ssim_value = numerator / denominator

        return float(max(0.0, min(1.0, (ssim_value + 1.0) / 2.0)))

    def _effective_threshold(self) -> float:
        """Threshold for considering frames similar; lower = skip more (e.g. ignore mouse)."""
        if self.manga_mode:
            return min(self.threshold, 0.88)
        return self.threshold

    def _is_similar(self, frame: np.ndarray) -> bool:
        """Check if frame is similar to previous frame."""
        if self.previous_frame is None:
            return False
        effective = self._effective_threshold()
        if self.method == 'hash':
            current_hash = self._compute_hash(frame)
            similar = (current_hash == self.previous_hash)
            self.previous_hash = current_hash
            return similar
        elif self.method in ('mse', 'ssim'):
            compute = self._compute_mse if self.method == 'mse' else self._compute_ssim
            score = compute(frame, self.previous_frame)
            similar = score >= effective
            if not similar:
                self.logger.info(
                    "[FRAME SKIP] Change detected (%s=%.4f, threshold=%.4f)",
                    self.method, score, effective,
                )
            else:
                self.logger.debug(
                    "[FRAME SKIP] Similar (%s=%.4f, threshold=%.4f)",
                    self.method, score, effective,
                )
            return similar
        return False

    # ------------------------------------------------------------------
    # Adaptive backoff
    # ------------------------------------------------------------------

    def get_adaptive_interval(self) -> float:
        """Return extra sleep seconds based on content stability."""
        if not self.enable_backoff:
            return 0.0
        for threshold, extra_sleep in self.BACKOFF_TIERS:
            if self.consecutive_skips < threshold:
                return extra_sleep
        return self.BACKOFF_TIERS[-1][1]

    # ------------------------------------------------------------------
    # Main process
    # ------------------------------------------------------------------

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Decide if frame should be skipped.

        In both modes, skipping starts on the very first similar frame.

        In dynamic mode, when a frame IS different, we additionally run
        the frame differencing engine and attach 'changed_regions' to the
        data dict so the pipeline can do partial OCR.
        """
        self.total_frames += 1

        raw_frame = data.get('frame')
        if raw_frame is None:
            return data

        frame = getattr(raw_frame, 'data', raw_frame)

        if isinstance(frame, Image.Image):
            frame = np.array(frame)

        if not isinstance(frame, np.ndarray):
            return data

        is_similar = self._is_similar(frame)
        should_skip = False

        if is_similar:
            self.consecutive_skips += 1
            if self.consecutive_skips < self.max_skip:
                should_skip = True
            else:
                self.consecutive_skips = 0
        else:
            self.consecutive_skips = 0

        if not should_skip:
            self.previous_frame = frame.copy()
            if self.method == 'hash':
                self.previous_hash = self._compute_hash(frame)

            if self.content_mode == 'dynamic' and not is_similar:
                changed_regions = self._detect_changed_regions(frame)
                if changed_regions is not None:
                    data['changed_regions'] = changed_regions

            if self.content_mode == 'dynamic':
                self._previous_full_frame = frame.copy()

        if should_skip:
            data['skip_processing'] = True
            self.skipped_frames += 1
        else:
            data['skip_processing'] = False
            data['frame_changed'] = not is_similar
            self.processed_frames += 1

        return data

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, new_config: dict[str, Any]) -> None:
        """Update configuration at runtime."""
        if 'similarity_threshold' in new_config:
            self.threshold = new_config['similarity_threshold']
        if 'max_skip_frames' in new_config:
            self.max_skip = new_config['max_skip_frames']
        if 'comparison_method' in new_config:
            self.method = new_config['comparison_method']
        if 'adaptive_backoff' in new_config:
            self.enable_backoff = new_config['adaptive_backoff']
        if 'manga_mode' in new_config:
            self.manga_mode = new_config['manga_mode']
        if 'content_mode' in new_config:
            old_mode = self.content_mode
            self.content_mode = new_config['content_mode']
            if old_mode != self.content_mode:
                self.logger.info(f"[FRAME SKIP] Content mode changed: {old_mode} -> {self.content_mode}")
                # Reset differencing state on mode change
                self._diff_engine = None
                self._previous_full_frame = None

    # ------------------------------------------------------------------
    # Stats / reset
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get optimizer statistics."""
        skip_rate = (self.skipped_frames / self.total_frames * 100) if self.total_frames > 0 else 0
        return {
            'total_frames': self.total_frames,
            'skipped_frames': self.skipped_frames,
            'processed_frames': self.processed_frames,
            'partial_ocr_frames': self.partial_ocr_frames,
            'consecutive_skips': self.consecutive_skips,
            'adaptive_extra_sleep': self.get_adaptive_interval(),
            'content_mode': self.content_mode,
            'skip_rate': f"{skip_rate:.1f}%",
            'cpu_saved': f"{skip_rate:.0f}%",
        }

    def reset(self):
        """Reset optimizer state."""
        self.previous_frame = None
        self.previous_hash = None
        self._previous_full_frame = None
        self.consecutive_skips = 0
        self.total_frames = 0
        self.skipped_frames = 0
        self.processed_frames = 0
        self.partial_ocr_frames = 0
    def cleanup(self):
        """Clean up optimizer resources."""
        self.reset()



def initialize(config: dict[str, Any]) -> FrameSkipOptimizer:
    """Initialize the optimizer plugin."""
    return FrameSkipOptimizer(config)
