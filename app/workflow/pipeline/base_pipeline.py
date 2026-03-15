"""
Base pipeline engine.

``BasePipeline`` is the single unified pipeline that owns an ordered list of
stages and delegates their execution to a pluggable ``ExecutionStrategy``.
It manages the full lifecycle (start / stop / pause / resume), runs a
background frame loop with FPS limiting and automatic error-based shutdown,
and exposes callbacks for translation results, errors, and state changes.

Cleanup always runs in reverse stage order so late-initialised resources
are released first.

Requirements: 2.1, 2.2, 2.3, 9.1
"""
import logging
import threading
import time
from typing import Any, Callable

from .types import (
    ErrorCallback,
    ExecutionStrategy,
    PipelineConfig,
    PipelineStageProtocol,
    PipelineState,
    PipelineStats,
    ResourceOwner,
    StageResult,
    StateChangeCallback,
    TranslationCallback,
)

logger = logging.getLogger('optikr.pipeline')


class BasePipeline(ResourceOwner):
    """Unified pipeline engine.

    Parameters
    ----------
    stages:
        Ordered list of stages to execute each frame.
    strategy:
        Controls *how* the stages are executed (sequential, async, …).
    config:
        Pipeline-wide configuration knobs.
    """

    def __init__(
        self,
        stages: list[PipelineStageProtocol],
        strategy: ExecutionStrategy,
        config: PipelineConfig | None = None,
    ) -> None:
        self._stages: list[PipelineStageProtocol] = list(stages)
        self._strategy: ExecutionStrategy = strategy
        self._config: PipelineConfig = config or PipelineConfig()

        self._state = PipelineState.IDLE
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially
        self._loop_thread: threading.Thread | None = None

        self._stats = PipelineStats()
        self._stats_lock = threading.Lock()
        self._consecutive_skips = 0
        self._skip_log_interval = 50

        self._overlay_positions: list = []
        self._on_translation: TranslationCallback | None = None
        self._on_error: ErrorCallback | None = None
        self._on_state_change: StateChangeCallback | None = None
        self._pending_state_callback = None

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    @property
    def on_translation(self) -> TranslationCallback | None:
        return self._on_translation

    @on_translation.setter
    def on_translation(self, cb: TranslationCallback | None) -> None:
        self._on_translation = cb

    @property
    def on_error(self) -> ErrorCallback | None:
        return self._on_error

    @on_error.setter
    def on_error(self, cb: ErrorCallback | None) -> None:
        self._on_error = cb

    @property
    def on_state_change(self) -> StateChangeCallback | None:
        return self._on_state_change

    @on_state_change.setter
    def on_state_change(self, cb: StateChangeCallback | None) -> None:
        self._on_state_change = cb

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @property
    def stages(self) -> list[PipelineStageProtocol]:
        return list(self._stages)

    def get_stats(self) -> PipelineStats:
        """Return a snapshot of current runtime statistics.

        Merges ``frames_dropped`` and ``avg_stage_times_ms`` from the
        strategy (e.g. ``AsyncStrategy``, ``SequentialStrategy``) so
        callers see a unified view.
        """
        strategy_dropped = 0
        stage_times: dict = {}
        if hasattr(self._strategy, 'get_stats'):
            try:
                s_stats = self._strategy.get_stats()
                if isinstance(s_stats, dict):
                    strategy_dropped = s_stats.get('frames_dropped', 0)
                    stage_times = s_stats.get('avg_stage_times_ms', {})
            except Exception:
                pass

        with self._stats_lock:
            return PipelineStats(
                frames_processed=self._stats.frames_processed,
                frames_skipped=self._stats.frames_skipped,
                frames_dropped=self._stats.frames_dropped + strategy_dropped,
                consecutive_errors=self._stats.consecutive_errors,
                total_errors=self._stats.total_errors,
                total_duration_ms=self._stats.total_duration_ms,
                stage_times_ms=stage_times,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start the pipeline's background frame loop.

        Returns ``True`` if the pipeline was started, ``False`` if it was
        already running or in an invalid state for starting.
        """
        with self._state_lock:
            if self._state not in (PipelineState.IDLE, PipelineState.ERROR):
                logger.warning(
                    "Cannot start pipeline from state %s", self._state.value,
                )
                return False
            self._set_state(PipelineState.STARTING)
        self._flush_state_callback()

        self._stop_event.clear()
        self._pause_event.set()

        with self._stats_lock:
            self._stats = PipelineStats()
        self._overlay_positions = []
        self._consecutive_skips = 0
        self._reset_plugins()

        self._loop_thread = threading.Thread(
            target=self._frame_loop,
            name="BasePipeline",
            daemon=True,
        )
        self._loop_thread.start()

        with self._state_lock:
            self._set_state(PipelineState.RUNNING)
        self._flush_state_callback()

        logger.info(
            "BasePipeline started with %d stage(s), target FPS=%d",
            len(self._stages),
            self._config.target_fps,
        )
        return True

    def stop(self) -> None:
        """Signal the frame loop to stop and wait for it to finish."""
        with self._state_lock:
            if self._state in (PipelineState.IDLE, PipelineState.STOPPING):
                return
            self._set_state(PipelineState.STOPPING)
        self._flush_state_callback()

        self._stop_event.set()
        self._pause_event.set()  # unblock if paused

        if self._loop_thread is not None and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=self._config.stop_timeout)
            if self._loop_thread.is_alive():
                logger.warning(
                    "Pipeline thread did not stop within %.1fs timeout",
                    self._config.stop_timeout,
                )

        with self._state_lock:
            self._set_state(PipelineState.IDLE)
        self._flush_state_callback()

        logger.info("BasePipeline stopped")

    def _reset_plugins(self) -> None:
        """Reset all stage plugins and inner-stage caches so stale state
        doesn't carry across runs."""
        from .plugin_stage import PluginAwareStage

        for stage in self._stages:
            if not isinstance(stage, PluginAwareStage):
                if hasattr(stage, "reset"):
                    try:
                        stage.reset()
                    except Exception as exc:
                        logger.debug("Stage %s reset failed: %s",
                                     type(stage).__name__, exc)
                continue

            # Reset the inner stage (e.g. OCRStage stability cache)
            inner = stage.inner_stage
            if hasattr(inner, "reset"):
                try:
                    inner.reset()
                except Exception as exc:
                    logger.debug("Inner stage %s reset failed: %s",
                                 type(inner).__name__, exc)

            # Clear OCR layer cache if the inner stage owns one
            ocr_layer = getattr(inner, "_ocr_layer", None)
            if ocr_layer is not None:
                ocr_cache = getattr(ocr_layer, "_cache", None)
                if ocr_cache is not None and hasattr(ocr_cache, "clear"):
                    try:
                        ocr_cache.clear()
                    except Exception as exc:
                        logger.debug("OCR cache clear failed: %s", exc)

            for plugin in stage.pre_plugins + stage.post_plugins:
                if hasattr(plugin, "reset"):
                    try:
                        plugin.reset()
                    except Exception as exc:
                        logger.debug(
                            "Plugin %s reset failed: %s",
                            type(plugin).__name__, exc,
                        )

    def update_runtime_config(
        self,
        plugin_class_name: str,
        config: dict[str, Any],
        *,
        stage_attr: bool = False,
    ) -> bool:
        """Push a config update to a running plugin or inner stage.

        *plugin_class_name*: class name of the target (e.g.
        ``'FrameSkipOptimizer'``).  If the plugin has a ``configure()``
        method it is called with *config*.

        *stage_attr*: when True, set attributes directly on the inner
        stage via ``setattr`` (for updating instance variables like
        ``_STABILITY_THRESHOLD``).

        Returns True if the target was found and updated.
        """
        from .plugin_stage import PluginAwareStage

        for stage in self._stages:
            if not isinstance(stage, PluginAwareStage):
                continue

            for plugin in stage.pre_plugins + stage.post_plugins:
                if type(plugin).__name__ == plugin_class_name:
                    if hasattr(plugin, "configure"):
                        plugin.configure(config)
                        logger.info(
                            "Runtime config pushed to %s: %s",
                            plugin_class_name, config,
                        )
                        return True

            inner = stage.inner_stage
            if type(inner).__name__ == plugin_class_name:
                if stage_attr:
                    for k, v in config.items():
                        setattr(inner, k, v)
                    logger.info(
                        "Runtime config pushed to %s: %s",
                        plugin_class_name, config,
                    )
                    return True

        logger.debug("Runtime config target %s not found", plugin_class_name)
        return False

    def pause(self) -> None:
        """Pause the frame loop.  The loop thread stays alive but sleeps."""
        with self._state_lock:
            if self._state != PipelineState.RUNNING:
                return
            self._pause_event.clear()
            self._set_state(PipelineState.PAUSED)
        self._flush_state_callback()
        logger.info("BasePipeline paused")

    def resume(self) -> None:
        """Resume a paused pipeline."""
        with self._state_lock:
            if self._state != PipelineState.PAUSED:
                return
            self._pause_event.set()
            self._set_state(PipelineState.RUNNING)
        self._flush_state_callback()
        logger.info("BasePipeline resumed")

    def toggle(self) -> None:
        """Convenience: start if idle/error, stop if running/paused."""
        if self._state in (PipelineState.IDLE, PipelineState.ERROR):
            self.start()
        elif self._state in (PipelineState.RUNNING, PipelineState.PAUSED):
            self.stop()

    def is_running(self) -> bool:
        return self._state == PipelineState.RUNNING

    # ------------------------------------------------------------------
    # Frame loop
    # ------------------------------------------------------------------

    def _frame_loop(self) -> None:
        """Background loop: execute all stages once per frame, FPS-limited."""
        frame_interval = 1.0 / max(self._config.target_fps, 1)
        last_frame_time = 0.0

        while not self._stop_event.is_set():
            # Respect pause
            self._pause_event.wait(timeout=0.1)
            if self._stop_event.is_set():
                break
            if not self._pause_event.is_set():
                continue

            # FPS limiting
            now = time.monotonic()
            elapsed_since_last = now - last_frame_time
            if elapsed_since_last < frame_interval:
                sleep_for = frame_interval - elapsed_since_last
                with self._stats_lock:
                    self._stats.frames_skipped += 1
                if self._stop_event.wait(timeout=sleep_for):
                    break
                continue

            last_frame_time = time.monotonic()

            try:
                initial_data: dict[str, Any] = {}
                if self._config.capture_region is not None:
                    initial_data["region"] = self._config.capture_region
                    initial_data["source"] = "custom_region"
                initial_data["_overlay_positions"] = self._overlay_positions
                result = self._strategy.run_pipeline(self._stages, initial_data)
                self._record_frame_result(result)
                if result.success and result.data:
                    new_pos = result.data.get("_overlay_positions")
                    if new_pos is not None:
                        self._overlay_positions = new_pos
            except Exception as exc:
                logger.error("Unhandled error in frame loop: %s", exc)
                self._record_frame_error(str(exc))

            # Auto-stop on too many consecutive errors
            with self._stats_lock:
                if (
                    self._stats.consecutive_errors
                    >= self._config.max_consecutive_errors
                ):
                    logger.error(
                        "Auto-stopping pipeline after %d consecutive errors",
                        self._stats.consecutive_errors,
                    )
                    self._fire_error(
                        f"Pipeline auto-stopped after "
                        f"{self._stats.consecutive_errors} consecutive errors"
                    )
                    break

        # Transition to IDLE is done by stop(). If this loop exited on its own
        # (e.g. auto-stop), set ERROR only when we are still the active run.
        # If we are a stale loop (new run started after we got stuck in a stage),
        # do not overwrite state so the new run is not killed.
        with self._state_lock:
            if self._loop_thread is threading.current_thread() and self._state in (
                PipelineState.RUNNING,
                PipelineState.PAUSED,
            ):
                self._set_state(PipelineState.ERROR)
        self._flush_state_callback()

    # ------------------------------------------------------------------
    # Frame result handling
    # ------------------------------------------------------------------

    def _record_frame_result(self, result: StageResult) -> None:
        if result.success and not result.data and result.duration_ms == 0.0:
            return

        with self._stats_lock:
            self._stats.frames_processed += 1
            self._stats.total_duration_ms += result.duration_ms
            if result.success:
                self._stats.consecutive_errors = 0
            else:
                self._stats.consecutive_errors += 1
                self._stats.total_errors += 1
            frame_num = self._stats.frames_processed

        if result.success:
            translations = result.data.get("translations")
            if translations is not None:
                self._consecutive_skips = 0
                count = len(translations) if isinstance(translations, list) else 1
                if count > 0:
                    logger.info(
                        "[Pipeline] Frame #%d  %.0fms  %d translation(s)",
                        frame_num, result.duration_ms, count,
                    )
                else:
                    logger.debug(
                        "[Pipeline] Frame #%d  %.0fms  (no text found)",
                        frame_num, result.duration_ms,
                    )
                self._fire_translation(result.data)
            else:
                self._consecutive_skips += 1
                if self._consecutive_skips == 1:
                    logger.info(
                        "[Pipeline] Frame #%d  skipped (static content, overlay held)",
                        frame_num,
                    )
                elif self._consecutive_skips % self._skip_log_interval == 0:
                    logger.info(
                        "[Pipeline] %d frames skipped (content unchanged)",
                        self._consecutive_skips,
                    )
        else:
            logger.warning(
                "[Pipeline] Frame #%d FAILED  %.0fms  error=%s",
                frame_num, result.duration_ms, result.error,
            )
            self._fire_error(result.error or "stage returned failure")

    def _record_frame_error(self, message: str) -> None:
        with self._stats_lock:
            self._stats.frames_processed += 1
            self._stats.consecutive_errors += 1
            self._stats.total_errors += 1
        self._fire_error(message)

    # ------------------------------------------------------------------
    # Callback helpers
    # ------------------------------------------------------------------

    def _fire_translation(self, data: dict[str, Any]) -> None:
        if self._stop_event.is_set():
            logger.debug("Suppressing overlay — pipeline is stopping")
            return
        if self._on_translation is not None:
            try:
                self._on_translation(data)
            except Exception as exc:
                logger.warning("on_translation callback error: %s", exc)

    def _fire_error(self, message: str) -> None:
        if self._on_error is not None:
            try:
                self._on_error(message)
            except Exception as exc:
                logger.warning("on_error callback error: %s", exc)

    def _set_state(self, new_state: PipelineState) -> None:
        """Transition to *new_state* and fire the state-change callback.

        Must be called while holding ``_state_lock``.  The callback is
        invoked *after* releasing the lock to avoid deadlocks when the
        callback re-enters pipeline methods that also acquire the lock.
        """
        old = self._state
        self._state = new_state
        callback = self._on_state_change if old != new_state else None

        if callback is not None:
            # Release the lock before invoking the callback.  The caller
            # holds ``_state_lock`` via a ``with`` statement, so we
            # cannot truly release it here.  Instead, we schedule the
            # callback to run after the ``with`` block exits by storing
            # it for deferred invocation.
            self._pending_state_callback = (callback, old, new_state)

    def _flush_state_callback(self) -> None:
        """Invoke any pending state-change callback outside the lock."""
        cb_info = getattr(self, "_pending_state_callback", None)
        if cb_info is not None:
            self._pending_state_callback = None
            callback, old, new_state = cb_info
            try:
                callback(old, new_state)
            except Exception as exc:
                logger.warning("on_state_change callback error: %s", exc)

    # ------------------------------------------------------------------
    # ResourceOwner
    # ------------------------------------------------------------------

    def _do_cleanup(self) -> None:
        """Stop the pipeline, shut down the strategy, and clean up stages in reverse order."""
        self.stop()
        if hasattr(self._strategy, "cleanup"):
            try:
                self._strategy.cleanup()
            except Exception as exc:
                logger.warning(
                    "Strategy cleanup failed: [%s] %s",
                    type(exc).__name__,
                    exc,
                )
        for stage in reversed(self._stages):
            try:
                stage.cleanup()
            except Exception as exc:
                logger.warning(
                    "Stage cleanup failed for %s: [%s] %s",
                    type(stage).__name__,
                    type(exc).__name__,
                    exc,
                )
