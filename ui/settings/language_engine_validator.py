"""
Language-Engine Validator

Bidirectional validation between language selection and engine compatibility.
Checks OCR engine support for source language and translation engine support
for language pairs.  Returns structured results so the caller can show UI
dialogs and apply automatic switches.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Shared language maps ────────────────────────────────────────────────────

LANG_NAME_TO_CODE: dict[str, str] = {
    'English': 'en', 'German': 'de', 'Spanish': 'es', 'French': 'fr',
    'Japanese': 'ja', 'Chinese': 'zh', 'Korean': 'ko', 'Russian': 'ru',
    'Italian': 'it', 'Portuguese': 'pt', 'Dutch': 'nl', 'Polish': 'pl',
    'Arabic': 'ar', 'Hindi': 'hi', 'Thai': 'th', 'Vietnamese': 'vi',
    'Turkish': 'tr', 'Swedish': 'sv', 'Indonesian': 'id',
    'Auto-Detect': 'auto',
}

LANG_CODE_TO_NAME: dict[str, str] = {v: k for k, v in LANG_NAME_TO_CODE.items()}

# ── Plugin-JSON helpers ─────────────────────────────────────────────────────

_PLUGINS_BASE: Path = Path(__file__).resolve().parents[2] / 'plugins'


def _read_plugin_json(stage: str, engine_name: str) -> dict | None:
    """Read and parse a plugin.json for the given stage/engine."""
    plugin_json = _PLUGINS_BASE / 'stages' / stage / engine_name / 'plugin.json'
    try:
        if plugin_json.exists():
            with open(plugin_json, 'r', encoding='utf-8') as fh:
                return json.load(fh)
    except Exception as exc:
        logger.warning("Failed to read %s plugin.json for %s: %s", stage, engine_name, exc)
    return None


def get_ocr_supported_languages(engine_name: str) -> list[str] | None:
    """Return ``supported_languages`` from an OCR plugin.json, or *None*."""
    data = _read_plugin_json('ocr', engine_name)
    if data:
        return data.get('supported_languages')
    return None


def get_translation_plugin_metadata(engine_name: str) -> dict | None:
    """Return the full metadata dict from a translation plugin.json."""
    return _read_plugin_json('translation', engine_name)


# ── Result containers ───────────────────────────────────────────────────────

class OCRValidationResult:
    __slots__ = ('is_compatible', 'current_engine', 'compatible_engines',
                 'recommended_engine', 'engine_languages')

    def __init__(self, is_compatible: bool, current_engine: str,
                 compatible_engines: list[str],
                 recommended_engine: str | None,
                 engine_languages: list[str] | None = None):
        self.is_compatible = is_compatible
        self.current_engine = current_engine
        self.compatible_engines = compatible_engines
        self.recommended_engine = recommended_engine
        self.engine_languages = engine_languages or []


class TranslationValidationResult:
    __slots__ = ('is_compatible', 'current_engine', 'compatible_engines',
                 'recommended_engine', 'needs_model_download')

    def __init__(self, is_compatible: bool, current_engine: str,
                 compatible_engines: list[str],
                 recommended_engine: str | None,
                 needs_model_download: bool = False):
        self.is_compatible = is_compatible
        self.current_engine = current_engine
        self.compatible_engines = compatible_engines
        self.recommended_engine = recommended_engine
        self.needs_model_download = needs_model_download


# ── Validator ───────────────────────────────────────────────────────────────

class LanguageEngineValidator:
    """Pure-logic validator — no Qt imports, no dialogs."""

    UNIVERSAL_ENGINES = frozenset({
        'google_free', 'libretranslate', 'google_api', 'deepl', 'azure',
    })

    OCR_PRIORITY = ['mokuro', 'easyocr', 'hybrid_ocr', 'judge_ocr', 'paddleocr', 'tesseract']

    TRANSLATION_PRIORITY = [
        'marianmt_gpu', 'google_free', 'libretranslate',
        'deepl', 'google_api', 'azure',
    ]

    # ── OCR validation ──────────────────────────────────────────────────

    def validate_ocr_engine(
        self,
        source_lang_code: str,
        current_ocr_engine: str,
        available_engines: list[str] | None = None,
    ) -> OCRValidationResult:
        if source_lang_code == 'auto':
            return OCRValidationResult(True, current_ocr_engine, [], None)

        engine_languages = get_ocr_supported_languages(current_ocr_engine)

        if engine_languages is None:
            return OCRValidationResult(True, current_ocr_engine, [], None)

        if source_lang_code in engine_languages:
            return OCRValidationResult(True, current_ocr_engine, [], None,
                                       engine_languages)

        if available_engines is None:
            available_engines = self._discover_ocr_engines()

        compatible: list[str] = []
        for eng in available_engines:
            if eng == current_ocr_engine:
                continue
            langs = get_ocr_supported_languages(eng)
            if langs and source_lang_code in langs:
                compatible.append(eng)

        recommended = next(
            (e for e in self.OCR_PRIORITY if e in compatible), None
        )
        if recommended is None and compatible:
            recommended = compatible[0]

        return OCRValidationResult(False, current_ocr_engine, compatible,
                                   recommended, engine_languages)

    # ── Translation validation ──────────────────────────────────────────

    def validate_translation_engine(
        self,
        src_lang_code: str,
        tgt_lang_code: str,
        current_engine: str,
    ) -> TranslationValidationResult:
        if src_lang_code == 'auto':
            return TranslationValidationResult(True, current_engine, [], None)

        if current_engine in self.UNIVERSAL_ENGINES:
            return TranslationValidationResult(True, current_engine, [], None)

        metadata = get_translation_plugin_metadata(current_engine)
        is_compatible = True

        if metadata:
            settings = metadata.get('settings', {})
            src_opts = settings.get('source_language', {}).get('options', [])
            tgt_opts = settings.get('target_language', {}).get('options', [])
            if src_opts and tgt_opts:
                is_compatible = src_lang_code in src_opts and tgt_lang_code in tgt_opts

        if is_compatible:
            needs_dl = False
            if current_engine == 'marianmt_gpu':
                needs_dl = not self._is_marianmt_model_downloaded(
                    src_lang_code, tgt_lang_code
                )
            return TranslationValidationResult(True, current_engine, [], None,
                                                needs_dl)

        compatible = self._find_compatible_translation_engines(
            src_lang_code, tgt_lang_code, exclude=current_engine
        )
        recommended = compatible[0] if compatible else None
        return TranslationValidationResult(False, current_engine, compatible,
                                            recommended)

    # ── OCR language constraints ────────────────────────────────────────

    def get_constrained_languages_for_ocr(
        self, ocr_engine: str
    ) -> list[str] | None:
        """Return supported source languages, or *None* if unconstrained."""
        langs = get_ocr_supported_languages(ocr_engine)
        return langs if langs else None

    # ── Private helpers ─────────────────────────────────────────────────

    def _discover_ocr_engines(self) -> list[str]:
        ocr_dir = _PLUGINS_BASE / 'stages' / 'ocr'
        engines: list[str] = []
        try:
            if ocr_dir.exists():
                for item in ocr_dir.iterdir():
                    if item.is_dir() and (item / 'plugin.json').exists():
                        engines.append(item.name)
        except Exception as exc:
            logger.warning("Failed to discover OCR engines: %s", exc)
        return engines

    def _find_compatible_translation_engines(
        self, src: str, tgt: str, exclude: str = ''
    ) -> list[str]:
        compatible: list[str] = []
        for eng in self.TRANSLATION_PRIORITY:
            if eng == exclude:
                continue
            if eng in self.UNIVERSAL_ENGINES:
                compatible.append(eng)
                continue
            meta = get_translation_plugin_metadata(eng)
            if meta:
                s = meta.get('settings', {})
                so = s.get('source_language', {}).get('options', [])
                to = s.get('target_language', {}).get('options', [])
                if (not so or src in so) and (not to or tgt in to):
                    compatible.append(eng)
        return compatible

    @staticmethod
    def _is_marianmt_model_downloaded(src_lang: str, tgt_lang: str) -> bool:
        try:
            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
            if not cache_dir.exists():
                return False
            model_name = f"opus-mt-{src_lang}-{tgt_lang}"
            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and model_name in model_dir.name:
                    snapshots = model_dir / 'snapshots'
                    if snapshots.exists():
                        for snap in snapshots.iterdir():
                            if snap.is_dir() and any(snap.iterdir()):
                                return True
            return False
        except Exception:
            return False
