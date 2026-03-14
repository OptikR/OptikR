from __future__ import annotations

"""
Utility script to exercise the benchmark pipeline in a way that closely mirrors
the OptiKr UI benchmark dialog.

It runs two benchmark passes:
- A fast run with vision async guarded off (sequential-only vision)
- A full run with async enabled (including async vision where available)

Results are persisted using BenchmarkDialog._auto_save_json so the output JSON
matches what the UI would produce.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.benchmark.benchmark_runner import run_benchmark
from ui.dialogs.benchmark_dialog import BenchmarkDialog


def _create_temporary_image(path: Path) -> None:
    """Create a simple synthetic RGB image at the given path."""
    try:
        from PIL import Image
        import numpy as np
    except Exception as exc:  # pragma: no cover - environment guard
        raise RuntimeError(f"Failed to import PIL/numpy for image generation: {exc}") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    arr = (np.random.rand(64, 64, 3) * 255).astype("uint8")
    img = Image.fromarray(arr)
    img.save(path)


def main(argv: list[str] | None = None) -> int:
    _ = argv or sys.argv[1:]

    app = QApplication(sys.argv)

    tmp_img = Path("tests/tmp_benchmark_image.png")
    try:
        _create_temporary_image(tmp_img)
    except Exception as exc:
        print("ERROR: could not create temporary benchmark image:", exc, file=sys.stderr)
        return 1

    images = [tmp_img]
    dialog = BenchmarkDialog(parent=None, pipeline=None, config_manager=None)

    runs = [
        ("fast_sequential", True, False),  # Fast preset, vision async guarded off
        ("full_with_async", False, True),  # Full preset, allow async (including vision async)
    ]

    for label, fast, allow_async in runs:
        print(f"\n=== Running benchmark: {label} ===")

        def _progress(msg: str) -> None:
            print(f"[{label}] {msg}")

        try:
            results = run_benchmark(
                images=images,
                combinations=None,
                include_vision=True,
                include_text=True,
                fast=fast,
                progress_callback=_progress,
                allow_vision_async=allow_async,
            )
        except Exception as exc:
            print(f"{label}: benchmark run failed with exception:", exc, file=sys.stderr)
            continue

        print(f"{label}: completed {len(results)} result(s)")
        summary = dialog._build_summary(results)
        try:
            json_path = dialog._auto_save_json(results, summary_text=summary)
        except Exception as exc:
            print(f"{label}: failed to auto-save JSON:", exc, file=sys.stderr)
            json_path = None

        print(f"{label}: json_path={json_path}")

    try:
        if tmp_img.exists():
            tmp_img.unlink()
    except Exception:
        # Temporary cleanup failure is non-fatal
        pass

    # Prevent PyQt from complaining on exit when no event loop is running
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

