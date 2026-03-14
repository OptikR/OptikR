"""
Uninstall Python dependencies used by OptikR.

Usage:
  python uninstall_optikr_dependencies.py
  python uninstall_optikr_dependencies.py --yes
  python uninstall_optikr_dependencies.py --dry-run
  python uninstall_optikr_dependencies.py --core-only --yes
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


PLUGIN_EXTRA_PACKAGES = [
    # Packages installed by optional plugin setup paths.
    "mokuro",
    "qwen-vl-utils",
    "accelerate",
    "av",
    "fire",
    "loguru",
    "natsort",
    "pyclipper",
    "shapely",
    "torchsummary",
    "yattag",
    "pyyaml",
    "safetensors",
]


def normalize_name(name):
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def parse_requirement_name(line):
    text = line.strip()
    if not text or text.startswith("#"):
        return None

    # Remove inline comments.
    if " #" in text:
        text = text.split(" #", 1)[0].strip()

    # Skip pure pip options.
    if text.startswith(("--index-url", "--extra-index-url", "--find-links", "--trusted-host")):
        return None

    # Keep package token before version marker / extras / env markers.
    token = re.split(r"[<>=!~;\[\s]", text, maxsplit=1)[0].strip()
    if not token:
        return None
    if token.startswith((".", "/", "\\")) or "://" in token:
        return None
    return normalize_name(token)


def parse_requirements_file(path, seen_files=None):
    if seen_files is None:
        seen_files = set()

    path = path.resolve()
    if path in seen_files or not path.exists():
        return []
    seen_files.add(path)

    packages = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Handle nested requirements files.
        if line.startswith(("-r ", "--requirement ")):
            nested = line.split(maxsplit=1)[1].strip()
            nested_path = (path.parent / nested).resolve()
            packages.extend(parse_requirements_file(nested_path, seen_files))
            continue

        # Skip constraints and editable entries by default.
        if line.startswith(("-c ", "--constraint ", "-e ", "--editable ")):
            continue

        pkg = parse_requirement_name(line)
        if pkg:
            packages.append(pkg)

    return packages


def unique_in_order(items):
    seen = set()
    out = []
    for item in items:
        key = normalize_name(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    parser = argparse.ArgumentParser(description="Uninstall OptikR Python dependencies.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Run without confirmation prompt.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uninstalled without executing pip uninstall.",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Only uninstall packages listed in requirements files.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    requirements = script_dir / "requirements.txt"
    requirements_gpu = script_dir / "requirements-gpu.txt"

    packages = []
    packages.extend(parse_requirements_file(requirements))
    packages.extend(parse_requirements_file(requirements_gpu))

    # PyTorch is installed separately in first-run bootstrap, so always include it.
    packages.extend(["torch", "torchvision", "torchaudio"])

    if not args.core_only:
        packages.extend(PLUGIN_EXTRA_PACKAGES)

    packages = unique_in_order(packages)

    if not packages:
        print("[INFO] No package entries were found. Nothing to uninstall.")
        return 0

    print("=" * 60)
    print("OptikR dependency uninstall")
    print("=" * 60)
    print(f"Python: {sys.executable}")
    print(f"Packages selected: {len(packages)}")
    print("")
    for pkg in packages:
        print(f" - {pkg}")
    print("")

    if args.dry_run:
        print("[DRY RUN] No changes made.")
        return 0

    if not args.yes:
        answer = input("Proceed with uninstall? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return 0

    print("")
    print("[INFO] Uninstalling packages with pip...")
    overall_code = 0
    for group in chunked(packages, 40):
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y", *group]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            overall_code = result.returncode

    print("")
    if overall_code == 0:
        print("[INFO] Uninstall finished.")
    else:
        print(f"[WARN] Uninstall finished with issues (exit code {overall_code}).")
    return overall_code


if __name__ == "__main__":
    raise SystemExit(main())
