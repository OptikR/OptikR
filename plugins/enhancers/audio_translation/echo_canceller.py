"""Echo cancellation for audio translation loopback capture.

Prevents TTS output from being recaptured by WASAPI loopback, which
would otherwise create an infinite feedback loop (TTS -> capture ->
transcribe -> translate -> TTS -> ...).

Two modes are supported:

* **gate** (default): Timestamp-based gating.  While TTS is playing
  (plus a configurable tail buffer), captured audio is silenced.
  Simple, lightweight, and effective when speech and TTS don't overlap.

* **spectral**: Spectral subtraction.  The TTS waveform is subtracted
  from the captured signal in the frequency domain, preserving any
  concurrent speech.  More computationally expensive but handles
  overlap better.

The ``EchoCanceller`` instance is shared between ``TTSStage`` (which
calls :meth:`mark_playing`) and ``AudioCaptureStage`` (which calls
:meth:`filter`).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_TAIL_MS = 250


@dataclass
class _PlaybackWindow:
    """A recorded TTS playback interval."""
    start: float  # time.monotonic()
    end: float
    waveform: np.ndarray | None = None


@dataclass
class EchoCanceller:
    """Shared echo-cancellation state between TTS and capture stages.

    Parameters
    ----------
    mode:
        ``"gate"`` for timestamp gating, ``"spectral"`` for spectral
        subtraction.
    tail_ms:
        Extra milliseconds of silence added after each TTS window to
        account for latency/reverb.
    sample_rate:
        Expected sample rate of audio buffers (default 16 000 Hz).
    """

    mode: str = "gate"
    tail_ms: float = DEFAULT_TAIL_MS
    sample_rate: int = 16_000

    _windows: list[_PlaybackWindow] = field(
        default_factory=list, init=False, repr=False,
    )
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False,
    )
    _max_window_age: float = field(default=30.0, init=False, repr=False)

    # ------------------------------------------------------------------
    # Called by TTSStage
    # ------------------------------------------------------------------

    def mark_playing(
        self,
        start_time: float,
        duration_seconds: float,
        waveform: np.ndarray | None = None,
    ) -> None:
        """Record a TTS playback window.

        Parameters
        ----------
        start_time:
            ``time.monotonic()`` when playback began.
        duration_seconds:
            Duration of the TTS audio in seconds.
        waveform:
            Raw int16 mono audio of the TTS output (optional, only
            used by the ``spectral`` mode).
        """
        tail = self.tail_ms / 1000.0
        window = _PlaybackWindow(
            start=start_time,
            end=start_time + duration_seconds + tail,
            waveform=waveform if self.mode == "spectral" else None,
        )
        with self._lock:
            self._windows.append(window)
            self._prune_old_windows()
        logger.debug(
            "[EchoCanceller] Marked %.2fs TTS window (mode=%s, tail=%.0fms)",
            duration_seconds, self.mode, self.tail_ms,
        )

    def mark_playing_start(self) -> float:
        """Convenience: record the current monotonic time as TTS start.

        Returns the start timestamp so the caller can later call
        :meth:`mark_playing` with the exact duration.
        """
        return time.monotonic()

    # ------------------------------------------------------------------
    # Called by AudioCaptureStage / audio source
    # ------------------------------------------------------------------

    def filter(
        self,
        audio_buffer: np.ndarray,
        timestamp: float | None = None,
    ) -> np.ndarray:
        """Filter captured audio to remove TTS echo.

        Parameters
        ----------
        audio_buffer:
            16 kHz mono int16 audio from the capture stage.
        timestamp:
            ``time.monotonic()`` when the buffer was captured.
            Defaults to *now* if not provided.

        Returns
        -------
        np.ndarray
            Filtered audio buffer (may be zeroed, attenuated, or
            spectrally subtracted depending on mode).
        """
        if audio_buffer is None or audio_buffer.size == 0:
            return audio_buffer

        if timestamp is None:
            timestamp = time.monotonic()

        with self._lock:
            overlapping = self._find_overlapping_windows(timestamp, audio_buffer)

        if not overlapping:
            return audio_buffer

        if self.mode == "spectral":
            return self._apply_spectral_subtraction(
                audio_buffer, timestamp, overlapping,
            )

        return self._apply_gate(audio_buffer, timestamp, overlapping)

    def is_tts_playing(self, timestamp: float | None = None) -> bool:
        """Return True if TTS is currently playing at *timestamp*."""
        if timestamp is None:
            timestamp = time.monotonic()
        with self._lock:
            return any(w.start <= timestamp <= w.end for w in self._windows)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prune_old_windows(self) -> None:
        """Remove windows older than ``_max_window_age`` seconds."""
        cutoff = time.monotonic() - self._max_window_age
        self._windows = [w for w in self._windows if w.end > cutoff]

    def _find_overlapping_windows(
        self,
        timestamp: float,
        audio_buffer: np.ndarray,
    ) -> list[_PlaybackWindow]:
        """Return windows that overlap with the audio buffer's time span."""
        buf_duration = len(audio_buffer) / self.sample_rate
        buf_start = timestamp - buf_duration
        buf_end = timestamp
        return [
            w for w in self._windows
            if w.start < buf_end and w.end > buf_start
        ]

    def _apply_gate(
        self,
        audio_buffer: np.ndarray,
        timestamp: float,
        overlapping: list[_PlaybackWindow],
    ) -> np.ndarray:
        """Zero out portions of the buffer that fall within TTS windows."""
        buf_duration = len(audio_buffer) / self.sample_rate
        buf_start = timestamp - buf_duration
        samples = len(audio_buffer)

        result = audio_buffer.copy()

        for window in overlapping:
            gate_start_sample = max(
                0,
                int((window.start - buf_start) * self.sample_rate),
            )
            gate_end_sample = min(
                samples,
                int((window.end - buf_start) * self.sample_rate),
            )
            if gate_start_sample < gate_end_sample:
                result[gate_start_sample:gate_end_sample] = 0

        gated_fraction = np.count_nonzero(result == 0) / max(samples, 1)
        if gated_fraction > 0.5:
            logger.debug(
                "[EchoCanceller] Gate mode: %.0f%% of buffer silenced",
                gated_fraction * 100,
            )

        return result

    def _apply_spectral_subtraction(
        self,
        audio_buffer: np.ndarray,
        timestamp: float,
        overlapping: list[_PlaybackWindow],
    ) -> np.ndarray:
        """Subtract TTS spectrum from the captured signal."""
        buf_duration = len(audio_buffer) / self.sample_rate
        buf_start = timestamp - buf_duration
        n = len(audio_buffer)

        # Build composite TTS reference aligned to the buffer timeframe
        tts_ref = np.zeros(n, dtype=np.float32)
        for window in overlapping:
            if window.waveform is None or window.waveform.size == 0:
                return self._apply_gate(audio_buffer, timestamp, overlapping)

            wf = window.waveform.astype(np.float32)
            wf_duration = len(wf) / self.sample_rate

            # Offset of the buffer start relative to the TTS waveform start
            offset_seconds = buf_start - window.start
            wf_start = int(offset_seconds * self.sample_rate)
            wf_end = wf_start + n

            src_start = max(0, wf_start)
            src_end = min(len(wf), wf_end)
            dst_start = max(0, -wf_start)
            dst_end = dst_start + (src_end - src_start)

            if src_start < src_end and dst_start < n:
                dst_end = min(dst_end, n)
                length = min(src_end - src_start, dst_end - dst_start)
                tts_ref[dst_start:dst_start + length] += wf[src_start:src_start + length]

        if np.max(np.abs(tts_ref)) < 1.0:
            return audio_buffer

        # Spectral subtraction in frequency domain
        n_fft = max(256, 1 << (n - 1).bit_length())  # next power of 2
        sig_fft = np.fft.rfft(audio_buffer.astype(np.float32), n=n_fft)
        ref_fft = np.fft.rfft(tts_ref, n=n_fft)

        sig_mag = np.abs(sig_fft)
        ref_mag = np.abs(ref_fft)

        # Subtract with spectral floor to avoid musical noise
        alpha = 1.5  # over-subtraction factor
        beta = 0.01  # spectral floor
        cleaned_mag = np.maximum(sig_mag - alpha * ref_mag, beta * sig_mag)

        # Preserve original phase
        phase = np.angle(sig_fft)
        cleaned_fft = cleaned_mag * np.exp(1j * phase)

        cleaned = np.fft.irfft(cleaned_fft, n=n_fft)[:n]
        return np.clip(cleaned, -32768, 32767).astype(np.int16)
