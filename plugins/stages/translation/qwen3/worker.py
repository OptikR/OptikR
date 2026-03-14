"""
Qwen3 LLM Translation Worker

Translation plugin using Qwen3 causal language models with prompt-based
translation.  Unlike seq2seq models (MarianMT, NLLB), translation is
achieved by constructing an instruction prompt and generating the target
text with ``AutoModelForCausalLM``.
"""

import logging
import re
import time
from typing import Any

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from app.text_translation.translation_engine_interface import (
    AbstractTranslationEngine,
    BatchTranslationResult,
    TranslationOptions,
    TranslationResult,
)

logger = logging.getLogger("optikr.pipeline.qwen3_translation")

_LANG_NAMES: dict[str, str] = {
    "ja": "Japanese",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ko": "Korean",
    "ar": "Arabic",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
}

_SUPPORTED_LANGUAGES = list(_LANG_NAMES.keys())


def _lang_name(code: str) -> str:
    return _LANG_NAMES.get(code, code)


_DEFAULT_PROMPT_TEMPLATE = (
    "You are a deterministic machine translation engine.\n"
    "Translate the provided SOURCE_TEXT into {target_lang}.\n"
    "Rules:\n"
    "1) Return ONLY the translation in {target_lang}.\n"
    "2) Do NOT explain, summarize, answer, or add notes.\n"
    "3) Preserve names, numbers, punctuation, and line breaks where possible.\n"
    "4) If text is already in {target_lang}, return it unchanged."
)


def _is_valid_prompt_template(template: str) -> bool:
    """Accept only templates that can be formatted with language placeholders."""
    if not template or not template.strip():
        return False
    if "{target_lang}" not in template:
        return False
    # Keep backward compatibility with existing templates that still use source_lang.
    if "{source_lang}" in template:
        return True
    return True


class TranslationEngine(AbstractTranslationEngine):
    """Qwen3 prompt-based translation engine."""

    def __init__(self) -> None:
        super().__init__("qwen3")
        self._logger = logger
        self.model = None
        self.tokenizer = None
        self.model_name = "Qwen/Qwen3-1.7B"
        self._device: "torch.device | None" = None
        self._max_length = 512
        self._temperature = 0.3
        self._using_shared_model = False
        self._prompt_template: str = _DEFAULT_PROMPT_TEMPLATE

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", text))

    @staticmethod
    def _contains_hangul(text: str) -> bool:
        return bool(re.search(r"[\uac00-\ud7af]", text))

    def _looks_wrong_for_target(self, translated: str, tgt_lang: str) -> bool:
        if not translated or not translated.strip():
            return True
        latin_targets = {"en", "de", "fr", "es", "it", "pt", "nl", "pl", "tr"}
        if tgt_lang in latin_targets:
            return self._contains_cjk(translated) or self._contains_hangul(translated)
        return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: dict[str, Any]) -> bool:
        if not TRANSFORMERS_AVAILABLE:
            self._logger.error("transformers / torch not available")
            return False
        try:
            self.model_name = config.get("model_name", self.model_name)
            self._max_length = int(config.get("max_length", self._max_length))
            self._temperature = float(config.get("temperature", self._temperature))
            quantization = config.get("quantization", "none")
            use_gpu = config.get("gpu", True) or config.get("use_gpu", True)

            prompt_tpl = str(config.get("prompt_template", "") or "").strip()
            if _is_valid_prompt_template(prompt_tpl):
                self._prompt_template = prompt_tpl
            elif prompt_tpl:
                self._logger.warning(
                    "Ignoring invalid Qwen3 prompt template from config; "
                    "falling back to built-in default"
                )

            self._device = (
                torch.device("cuda")
                if use_gpu and torch.cuda.is_available()
                else torch.device("cpu")
            )

            device_str = str(self._device)

            # Check SharedModelRegistry for an already-loaded instance
            try:
                from app.llm.llm_layer import SharedModelRegistry
                shared = SharedModelRegistry.instance().get(self.model_name, device_str)
                if shared is not None:
                    self.model = shared["model"]
                    self.tokenizer = shared["tokenizer"]
                    self._using_shared_model = True
                    self._logger.info(
                        "Qwen3 translation engine sharing model from registry: "
                        "%s on %s", self.model_name, device_str,
                    )
                    return True
            except ImportError:
                pass

            self._logger.info(
                "Loading Qwen3 model: %s on %s (quantization=%s)",
                self.model_name,
                self._device,
                quantization,
            )

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True,
            )

            load_kwargs: dict[str, Any] = {
                "trust_remote_code": True,
                "dtype": torch.float16,
            }

            if quantization == "4bit":
                load_kwargs["load_in_4bit"] = True
                load_kwargs["device_map"] = "auto"
            elif quantization == "8bit":
                load_kwargs["load_in_8bit"] = True
                load_kwargs["device_map"] = "auto"

            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name, use_safetensors=True, **load_kwargs,
                )
            except Exception:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name, use_safetensors=False, **load_kwargs,
                )

            if "device_map" not in load_kwargs:
                self.model = self.model.to(self._device)

            self.model.eval()

            # Override model's generation config to prevent thinking mode
            if hasattr(self.model, "generation_config"):
                gc = self.model.generation_config
                gc.do_sample = False
                gc.temperature = 1.0
                gc.top_p = 1.0
                gc.top_k = 0

            # Register in SharedModelRegistry so the LLM plugin can reuse it
            try:
                from app.llm.llm_layer import SharedModelRegistry
                SharedModelRegistry.instance().register(
                    self.model_name, device_str, self.model, self.tokenizer,
                )
            except ImportError:
                pass

            self._logger.info("Qwen3 model loaded on %s", self._device)
            return True
        except Exception as e:
            self._logger.error("Failed to initialize Qwen3: %s", e)
            return False

    def is_available(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def cleanup(self) -> None:
        should_free = True
        if self._device is not None:
            try:
                from app.llm.llm_layer import SharedModelRegistry
                should_free = SharedModelRegistry.instance().release(
                    self.model_name, str(self._device),
                )
            except ImportError:
                pass

        if should_free:
            self.model = None
            self.tokenizer = None
            try:
                from app.utils.pytorch_manager import release_gpu_memory
                release_gpu_memory()
            except ImportError:
                pass
            self._logger.info("Qwen3 translation engine cleaned up (model freed)")
        else:
            self.model = None
            self.tokenizer = None
            self._logger.info(
                "Qwen3 translation engine cleaned up "
                "(model kept alive — still used by another component)"
            )
        self._using_shared_model = False

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        text: str,
        src_lang: str,
        tgt_lang: str,
        options: TranslationOptions | None = None,
        strict_mode: bool = False,
    ) -> list[dict[str, str]]:
        """Build chat-style messages for translation."""
        src_name = _lang_name(src_lang)
        tgt_name = _lang_name(tgt_lang)
        try:
            system_content = self._prompt_template.format(
                source_lang=src_name,
                target_lang=tgt_name,
            )
        except Exception:
            system_content = _DEFAULT_PROMPT_TEMPLATE.format(
                source_lang=src_name,
                target_lang=tgt_name,
            )
        if options and getattr(options, "context", None) and str(options.context).strip():
            system_content = (
                f"Context: {options.context.strip()}\n\n{system_content}"
            )
        if strict_mode:
            system_content = (
                f"{system_content}\n\n"
                f"STRICT OUTPUT REQUIREMENT: Respond in {tgt_name} only. "
                "No source language text, no explanations."
            )
        user_content = (
            f"TARGET_LANGUAGE: {tgt_name}\n"
            "SOURCE_TEXT_START\n"
            f"{text}\n"
            "SOURCE_TEXT_END"
        )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def _make_fallback(
        self, text: str, src: str, tgt: str,
    ) -> TranslationResult:
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language=src,
            target_language=tgt,
            confidence=0.0,
            engine_used=self.engine_name,
            processing_time_ms=0.0,
            from_cache=False,
        )

    def translate_text(
        self,
        text: str,
        src_lang: str,
        tgt_lang: str,
        options: TranslationOptions | None = None,
    ) -> TranslationResult:
        if not self.is_available():
            return self._make_fallback(text, src_lang, tgt_lang)

        start = time.time()
        try:
            translated = ""
            # Allow one strict retry if first pass ignores target language.
            for strict_mode in (False, True):
                messages = self._build_messages(
                    text, src_lang, tgt_lang, options, strict_mode=strict_mode
                )
                prompt = self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                    enable_thinking=False,
                )
                inputs = self.tokenizer(
                    prompt, return_tensors="pt", truncation=True,
                    max_length=self._max_length,
                ).to(self._device)

                input_len = inputs["input_ids"].shape[1]

                # Token IDs for <think> / </think> in Qwen3
                _THINK_START = 151667
                _THINK_END = 151668

                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=min(self._max_length, 64),
                        do_sample=False,
                        repetition_penalty=1.1,
                        pad_token_id=self.tokenizer.eos_token_id,
                        suppress_tokens=[_THINK_START],
                    )

                output_ids = outputs[0][input_len:].tolist()

                # If </think> is present despite suppression, skip past it
                try:
                    think_end = len(output_ids) - output_ids[::-1].index(_THINK_END)
                    output_ids = output_ids[think_end:]
                except ValueError:
                    pass

                translated = self.tokenizer.decode(
                    output_ids, skip_special_tokens=True,
                ).strip()

                # Final safety net: aggressively strip any thinking content
                if "<think>" in translated:
                    parts = translated.split("</think>")
                    translated = parts[-1] if len(parts) > 1 else ""
                    translated = re.sub(r"</?think>", "", translated).strip()

                if not self._looks_wrong_for_target(translated, tgt_lang):
                    break

            elapsed = (time.time() - start) * 1000
            return TranslationResult(
                original_text=text,
                translated_text=translated,
                source_language=src_lang,
                target_language=tgt_lang,
                confidence=0.85,
                engine_used=self.engine_name,
                processing_time_ms=elapsed,
                from_cache=False,
            )
        except Exception as e:
            self._logger.error("Qwen3 translation failed: %s", e)
            return self._make_fallback(text, src_lang, tgt_lang)

    def translate_batch(
        self,
        texts: list[str],
        src_lang: str,
        tgt_lang: str,
        options: TranslationOptions | None = None,
    ) -> BatchTranslationResult:
        start = time.time()
        results: list[TranslationResult] = []
        failed: list[tuple[int, str]] = []

        for i, text in enumerate(texts):
            try:
                result = self.translate_text(text, src_lang, tgt_lang, options)
                results.append(result)
            except Exception as e:
                self._logger.error("Qwen3 batch item %d failed: %s", i, e)
                failed.append((i, str(e)))
                results.append(self._make_fallback(text, src_lang, tgt_lang))

        elapsed = (time.time() - start) * 1000
        return BatchTranslationResult(
            results=results,
            total_processing_time_ms=elapsed,
            cache_hit_rate=0.0,
            failed_translations=failed,
        )

    # ------------------------------------------------------------------
    # Language support
    # ------------------------------------------------------------------

    def get_supported_languages(self) -> list[str]:
        return list(_SUPPORTED_LANGUAGES)

    def supports_language_pair(self, src_lang: str, tgt_lang: str) -> bool:
        return src_lang in _LANG_NAMES and tgt_lang in _LANG_NAMES
