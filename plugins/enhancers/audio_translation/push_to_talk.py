"""Push-to-Talk (PTT) global hotkey listener.

Provides an alternative to Voice Activity Detection (VAD) for
controlling when the microphone is active during audio translation.
When PTT mode is enabled, audio capture is only forwarded while the
configured hotkey is held down.

Uses ``pynput`` for global hotkey listening.  Falls back to a
keyboard-polling approach via ``ctypes`` on Windows when pynput is
unavailable.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class PushToTalk:
    """Global hotkey listener for push-to-talk.

    Parameters
    ----------
    key:
        Key name to use as the PTT trigger.  Accepts pynput key names
        (e.g. ``"ctrl_l"``, ``"shift"``, ``"alt_l"``, ``"f1"``..``"f12"``,
        ``"space"``) or Windows virtual key codes as ``"vk:0xNN"``.
        Defaults to left Control.
    on_activate:
        Optional callback invoked when PTT is pressed.
    on_deactivate:
        Optional callback invoked when PTT is released.
    """

    key: str = "ctrl_l"
    on_activate: Callable[[], None] | None = None
    on_deactivate: Callable[[], None] | None = None

    _active: bool = field(default=False, init=False, repr=False)
    _listener: Any = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False, repr=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False,
    )
    _fallback_thread: threading.Thread | None = field(
        default=None, init=False, repr=False,
    )
    _stop_event: threading.Event = field(
        default_factory=threading.Event, init=False, repr=False,
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True while the PTT key is held down."""
        return self._active

    def start(self) -> None:
        """Begin listening for the PTT hotkey."""
        if self._running:
            return

        self._stop_event.clear()
        self._running = True

        if self._try_start_pynput():
            logger.info(
                "[PushToTalk] Listening via pynput (key=%s)", self.key,
            )
            return

        if sys.platform == "win32" and self._try_start_win32_polling():
            logger.info(
                "[PushToTalk] Listening via win32 polling (key=%s)", self.key,
            )
            return

        logger.error(
            "[PushToTalk] No keyboard backend available — "
            "install pynput (pip install pynput)"
        )
        self._running = False

    def stop(self) -> None:
        """Stop listening and release resources."""
        self._running = False
        self._stop_event.set()
        self._active = False

        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

        if self._fallback_thread is not None:
            self._fallback_thread.join(timeout=2.0)
            self._fallback_thread = None

    def set_key(self, key: str) -> None:
        """Change the PTT key.  Restarts the listener if already running."""
        was_running = self._running
        if was_running:
            self.stop()
        self.key = key
        if was_running:
            self.start()

    # ------------------------------------------------------------------
    # pynput backend
    # ------------------------------------------------------------------

    def _try_start_pynput(self) -> bool:
        """Attempt to start the PTT listener via pynput."""
        try:
            from pynput import keyboard  # type: ignore[import-untyped]
        except ImportError:
            return False

        target_key = self._resolve_pynput_key(keyboard)
        if target_key is None:
            logger.warning(
                "[PushToTalk] Unrecognised key '%s' for pynput", self.key,
            )
            return False

        def on_press(k: Any) -> None:
            if self._key_matches(k, target_key, keyboard):
                with self._lock:
                    if not self._active:
                        self._active = True
                        if self.on_activate:
                            self.on_activate()

        def on_release(k: Any) -> None:
            if self._key_matches(k, target_key, keyboard):
                with self._lock:
                    if self._active:
                        self._active = False
                        if self.on_deactivate:
                            self.on_deactivate()

        self._listener = keyboard.Listener(
            on_press=on_press, on_release=on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        return True

    def _resolve_pynput_key(self, keyboard: Any) -> Any:
        """Convert a string key name to a pynput Key or KeyCode."""
        key_lower = self.key.lower().strip()

        if key_lower.startswith("vk:"):
            try:
                vk = int(key_lower[3:], 0)
                return keyboard.KeyCode.from_vk(vk)
            except (ValueError, AttributeError):
                return None

        key_map = {
            "ctrl_l": keyboard.Key.ctrl_l,
            "ctrl_r": keyboard.Key.ctrl_r,
            "ctrl": keyboard.Key.ctrl_l,
            "shift_l": keyboard.Key.shift_l,
            "shift_r": keyboard.Key.shift_r,
            "shift": keyboard.Key.shift,
            "alt_l": keyboard.Key.alt_l,
            "alt_r": keyboard.Key.alt_r,
            "alt": keyboard.Key.alt_l,
            "space": keyboard.Key.space,
            "tab": keyboard.Key.tab,
            "caps_lock": keyboard.Key.caps_lock,
        }

        if key_lower in key_map:
            return key_map[key_lower]

        # F-keys
        if key_lower.startswith("f") and key_lower[1:].isdigit():
            fnum = int(key_lower[1:])
            fkey = getattr(keyboard.Key, f"f{fnum}", None)
            if fkey is not None:
                return fkey

        # Single character
        if len(key_lower) == 1:
            return keyboard.KeyCode.from_char(key_lower)

        return None

    @staticmethod
    def _key_matches(pressed: Any, target: Any, keyboard: Any) -> bool:
        """Check if *pressed* matches *target*."""
        if pressed == target:
            return True
        # Handle KeyCode vs Key comparison
        if hasattr(pressed, "vk") and hasattr(target, "vk"):
            return pressed.vk == target.vk
        return False

    # ------------------------------------------------------------------
    # Win32 polling fallback (no pynput)
    # ------------------------------------------------------------------

    _WIN32_VK_MAP: dict[str, int] = {
        "ctrl_l": 0xA2,   # VK_LCONTROL
        "ctrl_r": 0xA3,   # VK_RCONTROL
        "ctrl": 0xA2,
        "shift_l": 0xA0,  # VK_LSHIFT
        "shift_r": 0xA1,  # VK_RSHIFT
        "shift": 0xA0,
        "alt_l": 0xA4,    # VK_LMENU
        "alt_r": 0xA5,    # VK_RMENU
        "alt": 0xA4,
        "space": 0x20,
        "tab": 0x09,
        "caps_lock": 0x14,
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
        "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
        "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    }

    def _resolve_win32_vk(self) -> int | None:
        """Resolve the configured key to a Windows virtual key code."""
        key_lower = self.key.lower().strip()

        if key_lower.startswith("vk:"):
            try:
                return int(key_lower[3:], 0)
            except ValueError:
                return None

        if key_lower in self._WIN32_VK_MAP:
            return self._WIN32_VK_MAP[key_lower]

        # Single ASCII character
        if len(key_lower) == 1 and key_lower.isalnum():
            return ord(key_lower.upper())

        return None

    def _try_start_win32_polling(self) -> bool:
        """Start a polling thread that checks key state via GetAsyncKeyState."""
        vk = self._resolve_win32_vk()
        if vk is None:
            logger.warning(
                "[PushToTalk] Cannot resolve '%s' to VK code", self.key,
            )
            return False

        import ctypes

        def _poll() -> None:
            while not self._stop_event.is_set():
                try:
                    state = ctypes.windll.user32.GetAsyncKeyState(vk)
                    pressed = bool(state & 0x8000)
                except Exception:
                    pressed = False

                with self._lock:
                    was_active = self._active
                    self._active = pressed
                    if pressed and not was_active and self.on_activate:
                        self.on_activate()
                    elif not pressed and was_active and self.on_deactivate:
                        self.on_deactivate()

                self._stop_event.wait(0.02)  # ~50 Hz polling

        self._fallback_thread = threading.Thread(
            target=_poll, daemon=True, name="PTT-Win32-Poll",
        )
        self._fallback_thread.start()
        return True
