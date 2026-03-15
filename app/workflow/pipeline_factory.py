"""
Pipeline Factory — preset-based pipeline creation.

``PipelineFactory`` is the single entry-point for building ``BasePipeline``
instances.  Callers pick a *preset* name (``"sequential"``, ``"async"``,
``"custom"``, ``"audio"``) and supply the required domain layers; the
factory assembles stages, wraps them with ``PluginAwareStage`` hooks, selects
the matching execution strategy, and returns a ready-to-start pipeline.

Requirements: 2A.4
"""
import logging
from typing import Any, Literal

from .pipeline.base_pipeline import BasePipeline
from .pipeline.plugin_stage import PluginAwareStage
from .pipeline.stages import (
    AudioCaptureStage,
    AudioTextAdapterStage,
    CaptureStage,
    LLMStage,
    OCRStage,
    OverlayStage,
    PreprocessingStage,
    SpeechToTextStage,
    TTSStage,
    TranslationStage,
    VisionTranslateStage,
)
from .pipeline.strategies import (
    AsyncStrategy,
    CustomStrategy,
    SequentialStrategy,
    SubprocessStrategy,
)
from .pipeline.types import (
    ExecutionMode,
    PipelineConfig,
    PipelineStageProtocol,
)
from .plugin_loaders import OptimizerPluginLoader, TextProcessorPluginLoader
from app.utils.path_utils import get_plugin_enhancers_dir


logger = logging.getLogger('optikr.pipeline.factory')


Preset = Literal["sequential", "async", "custom", "subprocess", "audio", "vision"]


class _PostProcessAdapter:
    """Thin wrapper so a plugin's post-processing method is called via ``.process()``."""

    def __init__(self, plugin: Any) -> None:
        self._plugin = plugin
        if hasattr(plugin, "post_process_pipeline"):
            self._method = plugin.post_process_pipeline
        else:
            self._method = plugin.post_process

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._method(data)

_PRESET_TO_MODE: dict[str, ExecutionMode] = {
    "sequential": ExecutionMode.SEQUENTIAL,
    "async": ExecutionMode.ASYNC,
    "custom": ExecutionMode.CUSTOM,
    "subprocess": ExecutionMode.SUBPROCESS,
}


class PipelineFactory:
    """Factory for creating ``BasePipeline`` instances from presets.

    Parameters
    ----------
    config_manager:
        Application-wide configuration manager.  Passed through to plugin
        loaders so they can read runtime-mode and per-plugin settings.
    """

    def __init__(self, config_manager: Any = None) -> None:
        self.logger = logging.getLogger('optikr.pipeline.factory')
        self.config_manager = config_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        preset: Preset,
        *,
        capture_layer: Any = None,
        ocr_layer: Any = None,
        translation_layer: Any = None,
        llm_layer: Any = None,
        vision_layer: Any = None,
        overlay_renderer: Any = None,
        audio_source: Any = None,
        stt_engine: Any = None,
        tts_engine: Any = None,
        config: PipelineConfig | None = None,
        audio_config: dict[str, Any] | None = None,
        stage_modes: dict[str, ExecutionMode] | None = None,
        subprocess_manager: Any = None,
        enable_all_plugins: bool = True,
    ) -> BasePipeline:
        """Create a ``BasePipeline`` for the given *preset*.

        Parameters
        ----------
        preset:
            One of ``"sequential"``, ``"async"``, ``"custom"``, ``"audio"``,
            ``"vision"``.
        capture_layer, ocr_layer, translation_layer, llm_layer, overlay_renderer:
            Domain layers for the visual translation pipeline.
            *llm_layer* is optional; when ``None`` the LLM stage is a
            transparent pass-through.
        vision_layer:
            Vision translation engine (e.g. Qwen3-VL) for the ``"vision"``
            preset.  Combines OCR + translation into a single model pass.
        audio_source, stt_engine, tts_engine:
            Dependencies for the audio translation pipeline.
        config:
            Pipeline configuration; defaults are filled per-preset.
        audio_config:
            Dict of audio-specific settings (``source_language``,
            ``target_language``, ``whisper_model``, ``input_device``, etc.)
            passed directly to each audio stage's constructor.
        stage_modes:
            Per-stage execution mode overrides (only used by ``"custom"``).
        subprocess_manager:
            Subprocess manager instance (unused by current presets but
            available for future ``"subprocess"`` preset).
        enable_all_plugins:
            If *True* (default) load all enabled enhancer plugins.
            If *False* only load plugins marked ``essential``.

        Returns
        -------
        BasePipeline
            A fully-wired pipeline ready to ``start()``.

        Raises
        ------
        ValueError
            If *preset* is not recognised.
        """
        if preset in ("sequential", "async", "custom", "subprocess"):
            return self._create_visual(
                preset=preset,
                capture_layer=capture_layer,
                ocr_layer=ocr_layer,
                translation_layer=translation_layer,
                llm_layer=llm_layer,
                overlay_renderer=overlay_renderer,
                config=config,
                stage_modes=stage_modes,
                subprocess_manager=subprocess_manager,
                enable_all_plugins=enable_all_plugins,
            )

        if preset == "vision":
            return self._create_vision(
                capture_layer=capture_layer,
                vision_layer=vision_layer,
                overlay_renderer=overlay_renderer,
                config=config,
                enable_all_plugins=enable_all_plugins,
            )

        if preset == "audio":
            return self._create_audio(
                translation_layer=translation_layer,
                audio_source=audio_source,
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                config=config,
                audio_config=audio_config,
                enable_all_plugins=enable_all_plugins,
            )

        raise ValueError(f"Unknown preset: {preset!r}")

    # ------------------------------------------------------------------
    # Visual pipeline
    # ------------------------------------------------------------------

    def _create_visual(
        self,
        *,
        preset: str,
        capture_layer: Any,
        ocr_layer: Any,
        translation_layer: Any,
        llm_layer: Any = None,
        overlay_renderer: Any,
        config: PipelineConfig | None,
        stage_modes: dict[str, ExecutionMode] | None,
        subprocess_manager: Any,
        enable_all_plugins: bool,
    ) -> BasePipeline:
        mode = _PRESET_TO_MODE[preset]
        if config is None:
            config = PipelineConfig(execution_mode=mode)
        else:
            config.execution_mode = mode

        self.logger.info("Creating %s visual pipeline", preset.upper())

        confidence_threshold = 0.5
        preprocessing_enabled = False
        preprocessing_intelligent = True
        small_text_enhance = False
        small_text_denoise = False
        small_text_binarize = False
        stability_threshold = 0.80
        if self.config_manager is not None:
            confidence_threshold = self.config_manager.get_setting(
                'ocr.confidence_threshold', 0.5,
            )
            stability_threshold = self.config_manager.get_setting(
                'ocr.stability_threshold', 0.80,
            )
            preprocessing_enabled = self.config_manager.get_setting(
                'ocr.preprocessing_enabled', False,
            )
            preprocessing_intelligent = self.config_manager.get_setting(
                'ocr.preprocessing_intelligent', True,
            )
            small_text_enhance = self.config_manager.get_setting(
                'capture.enhance_small_text', False,
            )
            small_text_denoise = self.config_manager.get_setting(
                'capture.enhance_denoise', False,
            )
            small_text_binarize = self.config_manager.get_setting(
                'capture.enhance_binarize', False,
            )

        needs_preprocessing = preprocessing_enabled or small_text_enhance
        if not needs_preprocessing and self.config_manager is not None:
            needs_preprocessing = self.config_manager.get_setting(
                'ocr.manga_bubble_detection', False,
            )
        preprocessing_layer = self._create_preprocessing_layer(
            needs_preprocessing,
        )

        llm_mode = "refine"
        llm_custom_prompt = ""
        if self.config_manager is not None:
            llm_mode = self.config_manager.get_setting('llm.mode', 'refine')
            # Custom mode: use system_prompt (UI) with fallback to legacy custom_prompt
            llm_custom_prompt = self.config_manager.get_setting(
                'llm.system_prompt', ''
            ) or self.config_manager.get_setting('llm.custom_prompt', '')

        stages: list[PipelineStageProtocol] = [
            CaptureStage(capture_layer),
            PreprocessingStage(
                preprocessing_layer,
                enabled=needs_preprocessing,
                intelligent=preprocessing_intelligent,
                small_text_enhance=small_text_enhance,
                small_text_denoise=small_text_denoise,
                small_text_binarize=small_text_binarize,
            ),
            OCRStage(
                ocr_layer,
                confidence_threshold=confidence_threshold,
                source_lang=config.source_language,
                stability_threshold=stability_threshold,
            ),
            TranslationStage(
                translation_layer,
                source_lang=config.source_language,
                target_lang=config.target_language,
            ),
            LLMStage(
                llm_layer,
                mode=llm_mode,
                custom_prompt=llm_custom_prompt,
                source_lang=config.source_language,
                target_lang=config.target_language,
            ),
            OverlayStage(None),  # rendering handled by on_translation callback
        ]

        cache_manager = self._create_cache_manager()

        optimizer_loader, text_proc_loader = self._load_plugins(enable_all_plugins)
        self._configure_optimizer_plugins(optimizer_loader, config, cache_manager)
        plugin_map = self._build_plugin_map(optimizer_loader, text_proc_loader)
        wrapped = self._wrap_stages(stages, plugin_map)

        strategy = self._create_strategy(
            mode,
            stage_modes=stage_modes,
            subprocess_manager=subprocess_manager,
        )

        self.logger.info(
            "Visual pipeline: %d stage(s), strategy=%s",
            len(wrapped), type(strategy).__name__,
        )
        pipeline = BasePipeline(stages=wrapped, strategy=strategy, config=config)

        pipeline._optimizer_loader = optimizer_loader
        pipeline._text_proc_loader = text_proc_loader
        pipeline.cache_manager = cache_manager

        self._log_pipeline_summary(
            preset=preset,
            strategy=strategy,
            stages=wrapped,
            config=config,
            ocr_layer=ocr_layer,
            translation_layer=translation_layer,
        )

        return pipeline

    # ------------------------------------------------------------------
    # Vision pipeline  (Capture -> VisionTranslate -> Overlay)
    # ------------------------------------------------------------------

    def _create_vision(
        self,
        *,
        capture_layer: Any,
        vision_layer: Any,
        overlay_renderer: Any,
        config: PipelineConfig | None,
        enable_all_plugins: bool,
    ) -> BasePipeline:
        if config is None:
            config = PipelineConfig(execution_mode=ExecutionMode.SEQUENTIAL)
        mode = config.execution_mode

        self.logger.info(
            "Creating VISION pipeline (Capture -> VisionTranslate -> Overlay) mode=%s",
            mode.value,
        )

        stages: list[PipelineStageProtocol] = [
            CaptureStage(capture_layer),
            VisionTranslateStage(
                vision_layer,
                source_lang=config.source_language,
                target_lang=config.target_language,
            ),
            OverlayStage(None),
        ]

        cache_manager = self._create_cache_manager()

        optimizer_loader, text_proc_loader = self._load_plugins(enable_all_plugins)
        self._configure_optimizer_plugins(optimizer_loader, config, cache_manager)
        # vision_translate gets translation-stage plugins (dict, cache, context) and
        # ocr-stage pre-plugins (e.g. frame_skip) so we skip the vision model when frame unchanged.
        plugin_map = self._build_plugin_map(
            optimizer_loader,
            text_proc_loader,
            stage_aliases={"vision_translate": ["translation", "ocr"]},
        )
        wrapped = self._wrap_stages(stages, plugin_map)

        strategy = self._create_strategy(mode)

        self.logger.info(
            "Vision pipeline: %d stage(s), strategy=%s",
            len(wrapped), type(strategy).__name__,
        )
        pipeline = BasePipeline(stages=wrapped, strategy=strategy, config=config)

        pipeline._optimizer_loader = optimizer_loader
        pipeline._text_proc_loader = text_proc_loader
        pipeline.cache_manager = cache_manager

        self._log_pipeline_summary(
            preset="vision",
            strategy=strategy,
            stages=wrapped,
            config=config,
        )

        return pipeline

    # ------------------------------------------------------------------
    # Preprocessing layer construction
    # ------------------------------------------------------------------

    def _create_preprocessing_layer(self, enabled: bool) -> Any:
        """Create a ``PreprocessingLayer`` when preprocessing is enabled.

        Returns ``None`` when disabled so the ``PreprocessingStage``
        acts as a transparent pass-through.
        """
        if not enabled:
            return None
        try:
            from app.preprocessing import PreprocessingLayer
            return PreprocessingLayer(
                config_manager=self.config_manager,
            )
        except Exception as exc:
            self.logger.warning(
                "Failed to create PreprocessingLayer, preprocessing disabled: %s",
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Audio pipeline
    # ------------------------------------------------------------------

    def _create_audio(
        self,
        *,
        translation_layer: Any,
        audio_source: Any,
        stt_engine: Any,
        tts_engine: Any,
        config: PipelineConfig | None,
        audio_config: dict[str, Any] | None = None,
        enable_all_plugins: bool = True,
    ) -> BasePipeline:
        stage_cfg = audio_config or {}
        parallel = stage_cfg.get("parallel_processing", False)
        exec_mode = ExecutionMode.ASYNC if parallel else ExecutionMode.SEQUENTIAL

        if config is None:
            config = PipelineConfig(
                execution_mode=exec_mode,
                target_fps=1,
                max_consecutive_errors=100,
                stop_timeout=10.0,
            )
        else:
            config.execution_mode = exec_mode

        source_mode = stage_cfg.get("audio_source_mode", "microphone")
        self.logger.info(
            "Creating AUDIO pipeline (mode=%s, parallel=%s)", source_mode, parallel,
        )

        source_lang = stage_cfg.get("source_language", "en")
        target_lang = stage_cfg.get("target_language", "ja")
        bidirectional = stage_cfg.get("bidirectional", True)

        # -- Volume ducker (used by TTSStage in system/youtube modes) --
        volume_ducker = self._create_volume_ducker(stage_cfg, source_mode)

        # -- Build stage list based on audio source mode -----------------
        stages: list[PipelineStageProtocol] = self._build_audio_stages(
            source_mode=source_mode,
            audio_source=audio_source,
            stt_engine=stt_engine,
            tts_engine=tts_engine,
            translation_layer=translation_layer,
            volume_ducker=volume_ducker,
            stage_cfg=stage_cfg,
            source_lang=source_lang,
            target_lang=target_lang,
            bidirectional=bidirectional,
        )

        cache_manager = self._create_cache_manager()

        optimizer_loader, text_proc_loader = self._load_plugins(enable_all_plugins)
        self._configure_optimizer_plugins(optimizer_loader, config, cache_manager)
        plugin_map = self._build_plugin_map(optimizer_loader, text_proc_loader)
        wrapped = self._wrap_stages(stages, plugin_map)

        strategy = self._create_strategy(exec_mode)
        strategy_name = "AsyncStrategy" if parallel else "SequentialStrategy"

        self.logger.info(
            "Audio pipeline: %d stage(s), strategy=%s, mode=%s",
            len(wrapped), strategy_name, source_mode,
        )
        pipeline = BasePipeline(stages=wrapped, strategy=strategy, config=config)

        pipeline._optimizer_loader = optimizer_loader
        pipeline._text_proc_loader = text_proc_loader
        pipeline.cache_manager = cache_manager

        if volume_ducker is not None:
            pipeline._volume_ducker = volume_ducker

        self._log_pipeline_summary(
            preset="audio",
            strategy=strategy,
            stages=wrapped,
            config=config,
            translation_layer=translation_layer,
            stt_engine=stt_engine,
            tts_engine=tts_engine,
        )

        return pipeline

    # ------------------------------------------------------------------
    # Audio pipeline helpers
    # ------------------------------------------------------------------

    def _build_audio_stages(
        self,
        *,
        source_mode: str,
        audio_source: Any,
        stt_engine: Any,
        tts_engine: Any,
        translation_layer: Any,
        volume_ducker: Any,
        stage_cfg: dict[str, Any],
        source_lang: str,
        target_lang: str,
        bidirectional: bool,
    ) -> list[PipelineStageProtocol]:
        """Assemble the audio stage list depending on ``source_mode``."""

        # -- Echo canceller (shared between capture and TTS) ----------------
        echo_canceller = self._create_echo_canceller(stage_cfg, source_mode)

        # -- Push-to-talk (shared with capture stage) -----------------------
        ptt = self._create_push_to_talk(stage_cfg)

        adapter_stage = AudioTextAdapterStage(
            source_lang=source_lang,
            target_lang=target_lang,
            bidirectional=bidirectional,
        )
        translation_stage = TranslationStage(
            translation_layer,
            source_lang=source_lang,
            target_lang=target_lang,
            bidirectional=bidirectional,
        )
        tts_stage = TTSStage(
            tts_engine=tts_engine,
            config=stage_cfg,
            volume_ducker=volume_ducker,
            echo_canceller=echo_canceller,
        )

        if source_mode == "youtube":
            yt_stage = self._create_youtube_stage(stage_cfg, source_lang)
            return [yt_stage, adapter_stage, translation_stage, tts_stage]

        if source_mode == "process":
            process_source = self._create_process_audio_source(stage_cfg)
            capture = AudioCaptureStage(
                audio_source=process_source, config=stage_cfg,
                echo_canceller=echo_canceller, push_to_talk=ptt,
            )
        elif source_mode == "system":
            system_source = self._create_system_audio_source(stage_cfg)
            capture = AudioCaptureStage(
                audio_source=system_source, config=stage_cfg,
                echo_canceller=echo_canceller, push_to_talk=ptt,
            )
        else:
            capture = AudioCaptureStage(
                audio_source=audio_source, config=stage_cfg,
                echo_canceller=echo_canceller, push_to_talk=ptt,
            )

        stt = SpeechToTextStage(stt_engine=stt_engine, config=stage_cfg)
        return [capture, stt, adapter_stage, translation_stage, tts_stage]

    def _create_system_audio_source(self, stage_cfg: dict[str, Any]) -> Any:
        """Instantiate a ``SystemAudioCapture`` for WASAPI loopback."""
        try:
            from plugins.enhancers.audio_translation.system_audio_capture import (
                SystemAudioCapture,
            )
        except ImportError:
            self.logger.error(
                "SystemAudioCapture import failed — falling back to default mic"
            )
            return None

        device_index = stage_cfg.get("loopback_device", None)
        input_volume = stage_cfg.get("input_volume", 100) / 100.0

        source = SystemAudioCapture(
            device_index=device_index,
            input_volume=input_volume,
        )
        self.logger.info(
            "SystemAudioCapture created (device=%s, volume=%.0f%%)",
            device_index, input_volume * 100,
        )
        return source

    def _create_process_audio_source(self, stage_cfg: dict[str, Any]) -> Any:
        """Instantiate a ``ProcessAudioCapture`` for per-app WASAPI loopback."""
        try:
            from plugins.enhancers.audio_translation.process_audio_capture import (
                ProcessAudioCapture,
            )
        except ImportError:
            self.logger.error(
                "ProcessAudioCapture import failed — "
                "falling back to system loopback"
            )
            return self._create_system_audio_source(stage_cfg)

        target_pid = stage_cfg.get("process_pid", None)
        if target_pid is None:
            self.logger.warning(
                "Process mode selected but no process_pid provided — "
                "falling back to system loopback"
            )
            return self._create_system_audio_source(stage_cfg)

        input_volume = stage_cfg.get("input_volume", 100) / 100.0
        loopback_device = stage_cfg.get("loopback_device", None)

        source = ProcessAudioCapture(
            target_pid=target_pid,
            input_volume=input_volume,
            loopback_device=loopback_device,
        )
        self.logger.info(
            "ProcessAudioCapture created (pid=%s, volume=%.0f%%)",
            target_pid, input_volume * 100,
        )
        return source

    @staticmethod
    def _create_echo_canceller(
        stage_cfg: dict[str, Any], source_mode: str,
    ) -> Any | None:
        """Create an ``EchoCanceller`` when echo cancellation is enabled.

        Echo cancellation is most important for system/process loopback
        modes where TTS output gets recaptured.
        """
        if source_mode in ("microphone", "youtube"):
            return None

        ec_enabled = stage_cfg.get("echo_cancellation_enabled", True)
        if not ec_enabled:
            return None

        try:
            from plugins.enhancers.audio_translation.echo_canceller import (
                EchoCanceller,
            )
        except ImportError:
            logger.info(
                "echo_canceller not available — echo cancellation disabled"
            )
            return None

        mode = stage_cfg.get("echo_cancel_mode", "gate")
        canceller = EchoCanceller(mode=mode)
        logger.info("EchoCanceller created (mode=%s)", mode)
        return canceller

    @staticmethod
    def _create_push_to_talk(stage_cfg: dict[str, Any]) -> Any | None:
        """Create a ``PushToTalk`` instance when PTT is enabled."""
        ptt_enabled = stage_cfg.get("ptt_enabled", False)
        if not ptt_enabled:
            return None

        try:
            from plugins.enhancers.audio_translation.push_to_talk import (
                PushToTalk,
            )
        except ImportError:
            logger.info(
                "push_to_talk not available — PTT disabled"
            )
            return None

        ptt_key = stage_cfg.get("ptt_key", "ctrl_l")
        ptt = PushToTalk(key=ptt_key)
        ptt.start()
        logger.info("PushToTalk created (key=%s)", ptt_key)
        return ptt

    def _create_youtube_stage(
        self, stage_cfg: dict[str, Any], source_lang: str,
    ) -> Any:
        """Create a ``YouTubeTranscriptStage`` from the configured URL."""
        from plugins.enhancers.audio_translation.youtube_transcript import (
            YouTubeTranscriptSource,
            YouTubeTranscriptStage,
        )

        youtube_url: str = stage_cfg.get("youtube_url", "")
        if not youtube_url:
            raise ValueError(
                "YouTube Transcript mode selected but no youtube_url provided"
            )

        auto_detect = stage_cfg.get("auto_detect_language", False)
        preferred = None if auto_detect else [source_lang]

        yt_source = YouTubeTranscriptSource(preferred_languages=preferred)
        yt_source.fetch(youtube_url)

        self.logger.info(
            "YouTubeTranscriptStage created for %s (language=%s, segments=%d)",
            youtube_url,
            yt_source.language,
            len(yt_source.segments),
        )

        return YouTubeTranscriptStage(source=yt_source, auto_start=True)

    @staticmethod
    def _create_volume_ducker(
        stage_cfg: dict[str, Any], source_mode: str,
    ) -> Any | None:
        """Create a ``VolumeDucker`` if ducking is enabled and applicable.

        Ducking is only meaningful in system-audio and YouTube modes
        where external audio is playing that should be lowered during TTS.
        """
        duck_enabled = stage_cfg.get("duck_enabled", False)
        if not duck_enabled:
            return None

        if source_mode == "microphone":
            return None

        try:
            from plugins.enhancers.audio_translation.volume_ducker import VolumeDucker
        except ImportError:
            logger.info(
                "pycaw / volume_ducker not available — ducking disabled"
            )
            return None

        duck_level = stage_cfg.get("duck_level", 20)
        ducker = VolumeDucker(duck_level=duck_level)
        if not ducker.available:
            return None

        logger.info(
            "VolumeDucker created (duck_level=%d%%)", duck_level,
        )
        return ducker

    # ------------------------------------------------------------------
    # Dictionary engine injection (learning_dictionary plugin)
    # ------------------------------------------------------------------

    def _configure_optimizer_plugins(
        self,
        optimizer_loader: Any,
        config: PipelineConfig,
        cache_manager: Any = None,
    ) -> None:
        """Post-load configuration for optimizer plugins.

        Gives the ``context_manager`` plugin a reference to the
        ``config_manager`` and injects the ``SmartDictionary`` instance
        from *cache_manager* into the ``learning_dictionary`` plugin.
        """
        opt_plugins = getattr(optimizer_loader, "plugins", {})

        # Context Manager: inject config_manager and initialize
        cm_info = opt_plugins.get("context_manager")
        if cm_info:
            cm = cm_info.get("optimizer")
            if cm is not None:
                if hasattr(cm, "set_config_manager") and self.config_manager:
                    cm.set_config_manager(self.config_manager)
                if hasattr(cm, "initialize"):
                    cm.initialize()
                self.logger.info("Context Manager plugin configured")

        # Learning Dictionary: inject dictionary engine + context manager + quality filter config
        ld_info = opt_plugins.get("learning_dictionary")
        if ld_info:
            ld = ld_info.get("optimizer")
            if ld is not None:
                # Inject the SmartDictionary from PipelineCacheManager
                if cache_manager is not None:
                    dict_engine = getattr(
                        cache_manager, "persistent_dictionary", None,
                    )
                    if dict_engine is not None and hasattr(ld, "set_dictionary_engine"):
                        ld.set_dictionary_engine(dict_engine)
                        self.logger.info(
                            "Learning Dictionary: injected SmartDictionary engine"
                        )

                # Inject Context Manager for priority lookup
                # (Context Manager > Smart Dictionary > Translation engine)
                if cm_info and hasattr(ld, "set_context_manager"):
                    cm_plugin = cm_info.get("optimizer")
                    if cm_plugin is not None:
                        ld.set_context_manager(cm_plugin)
                        self.logger.info(
                            "Learning Dictionary: injected Context Manager "
                            "for locked-term priority lookup"
                        )

                # Wire learn_words / learn_sentences toggles
                if self.config_manager is not None and hasattr(ld, "set_learn_config"):
                    ld.set_learn_config(
                        learn_words=self.config_manager.get_setting(
                            "dictionary.learn_words", True,
                        ),
                        learn_sentences=self.config_manager.get_setting(
                            "dictionary.learn_sentences", True,
                        ),
                    )

                # Wire dictionary.auto_learn to optimizer's auto_save
                if self.config_manager is not None:
                    auto_learn = self.config_manager.get_setting(
                        "dictionary.auto_learn", True,
                    )
                    ld.auto_save = auto_learn

                # Wire source/target languages from pipeline config
                if config is not None and hasattr(ld, "set_languages"):
                    src = config.source_language or "en"
                    tgt = config.target_language or "de"
                    # Also check config_manager for the authoritative values
                    if self.config_manager is not None:
                        src = self.config_manager.get_setting(
                            "translation.source_language", src,
                        )
                        tgt = self.config_manager.get_setting(
                            "translation.target_language", tgt,
                        )
                        # If source is still the schema default, check
                        # whether the OCR engine constrains the language
                        # (e.g. Manga OCR → Japanese).  The ocr.languages
                        # list is the ground truth for what the OCR engine
                        # actually detects.
                        if src == "en":
                            ocr_langs = self.config_manager.get_setting(
                                "ocr.languages", [],
                            )
                            if (
                                ocr_langs
                                and len(ocr_langs) == 1
                                and ocr_langs[0] != "en"
                            ):
                                src = ocr_langs[0]
                                self.logger.info(
                                    "Learning Dictionary source language "
                                    "overridden by OCR language: %s",
                                    src,
                                )
                    ld.set_languages(src, tgt)
                    self.logger.info(
                        "Learning Dictionary languages set: %s → %s",
                        src, tgt,
                    )

                # Wire quality filter config from schema
                if self.config_manager is not None:
                    qf_enabled = self.config_manager.get_setting(
                        "translation.quality_filter_enabled", True,
                    )
                    qf_mode = self.config_manager.get_setting(
                        "translation.quality_filter_mode", 0,
                    )
                    if hasattr(ld, "set_quality_filter_config"):
                        ld.set_quality_filter_config(qf_enabled, qf_mode)
                        self.logger.info(
                            "Learning Dictionary quality filter configured "
                            "(enabled=%s, mode=%s)",
                            qf_enabled,
                            "strict" if qf_mode == 1 else "balanced",
                        )

    # ------------------------------------------------------------------
    # Plugin loading and stage wrapping
    # ------------------------------------------------------------------

    def _load_plugins(
        self,
        enable_all: bool = True,
    ) -> tuple:
        """Load optimizer and text-processor enhancer plugins.

        Returns ``(optimizer_loader, text_processor_loader)`` with their
        plugin dicts already populated.
        """
        optimizer_loader = OptimizerPluginLoader(
            str(get_plugin_enhancers_dir("optimizers")),
            config_manager=self.config_manager,
        )
        text_proc_loader = TextProcessorPluginLoader(
            str(get_plugin_enhancers_dir("text_processors")),
        )

        try:
            optimizer_loader.load_plugins(enable_all=enable_all)
        except Exception as exc:
            self.logger.warning("Failed to load optimizer plugins: %s", exc)

        try:
            text_proc_loader.load_plugins()
        except Exception as exc:
            self.logger.warning("Failed to load text-processor plugins: %s", exc)

        return optimizer_loader, text_proc_loader

    @staticmethod
    def _wrap_stages(
        stages: list[PipelineStageProtocol],
        plugin_map: dict[str, dict[str, list[Any]]],
    ) -> list[PipelineStageProtocol]:
        """Wrap each stage with ``PluginAwareStage`` if plugins target it."""
        if not plugin_map:
            return stages

        wrapped: list[PipelineStageProtocol] = []
        for stage in stages:
            stage_name = getattr(stage, "name", type(stage).__name__)
            hooks = plugin_map.get(stage_name)
            if hooks and (hooks.get("pre") or hooks.get("post")):
                wrapped.append(
                    PluginAwareStage(
                        stage,
                        pre_plugins=hooks.get("pre"),
                        post_plugins=hooks.get("post"),
                        name=stage_name,
                    )
                )
            else:
                wrapped.append(stage)
        return wrapped

    # ------------------------------------------------------------------
    # Strategy selection
    # ------------------------------------------------------------------

    def _create_strategy(
        self,
        mode: ExecutionMode,
        *,
        stage_modes: dict[str, ExecutionMode] | None = None,
        subprocess_manager: Any = None,
    ) -> Any:
        """Instantiate the execution strategy for *mode*."""
        queue_size = 16
        max_workers = 4
        thread_join_timeout = 2.0
        if self.config_manager is not None:
            queue_size = self.config_manager.get_setting(
                'pipeline.queue_size', 16,
            )
            max_workers = self.config_manager.get_setting(
                'pipeline.max_workers', 4,
            )
            thread_join_timeout = self.config_manager.get_setting(
                'timeouts.thread_join_seconds', 2.0,
            )

        if mode == ExecutionMode.SEQUENTIAL:
            return SequentialStrategy()
        if mode == ExecutionMode.ASYNC:
            return AsyncStrategy(
                queue_size=queue_size,
                max_workers=max_workers,
                thread_join_timeout=thread_join_timeout,
            )
        if mode == ExecutionMode.CUSTOM:
            return CustomStrategy(
                stage_modes=stage_modes,
                max_workers=max_workers,
            )
        if mode == ExecutionMode.SUBPROCESS:
            return SubprocessStrategy(subprocess_manager=subprocess_manager)
        return SequentialStrategy()

    # ------------------------------------------------------------------
    # Cache manager
    # ------------------------------------------------------------------

    def _create_cache_manager(self) -> Any:
        """Create a ``PipelineCacheManager`` for dictionary persistence and cache clearing.

        Returns ``None`` when construction fails so the pipeline can
        still operate without it.
        """
        try:
            from .managers.pipeline_cache_manager import PipelineCacheManager

            enable_dict = True
            if self.config_manager is not None:
                enable_dict = self.config_manager.get_setting(
                    "performance.enable_smart_dictionary", True,
                )

            return PipelineCacheManager(
                enable_persistent_dictionary=enable_dict,
                config_manager=self.config_manager,
            )
        except Exception as exc:
            self.logger.warning("Failed to create PipelineCacheManager: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Pipeline startup summary banner
    # ------------------------------------------------------------------

    def _log_pipeline_summary(
        self,
        *,
        preset: str,
        strategy: Any,
        stages: list[PipelineStageProtocol],
        config: PipelineConfig,
        ocr_layer: Any = None,
        translation_layer: Any = None,
        stt_engine: Any = None,
        tts_engine: Any = None,
    ) -> None:
        """Log a readable startup summary banner at INFO level."""
        sep = "=" * 60
        lines = ["", sep, "  PIPELINE STARTUP SUMMARY", sep]

        lines.append(f"  Preset       : {preset.upper()}")
        lines.append(f"  Strategy     : {type(strategy).__name__}")
        lines.append(
            f"  Languages    : {config.source_language} \u2192 {config.target_language}"
        )

        if ocr_layer is not None:
            ocr_name = getattr(ocr_layer, "name", type(ocr_layer).__name__)
            lines.append(f"  OCR engine   : {ocr_name}")
        if translation_layer is not None:
            trans_name = getattr(
                translation_layer, "name", type(translation_layer).__name__,
            )
            lines.append(f"  Translation  : {trans_name}")
        if stt_engine is not None:
            stt_name = getattr(stt_engine, "name", type(stt_engine).__name__)
            lines.append(f"  STT engine   : {stt_name}")
        if tts_engine is not None:
            tts_name = getattr(tts_engine, "name", type(tts_engine).__name__)
            lines.append(f"  TTS engine   : {tts_name}")

        if config.capture_region is not None:
            lines.append(f"  Capture rgn  : {config.capture_region}")
        if config.overlay_region is not None:
            lines.append(f"  Overlay rgn  : {config.overlay_region}")

        if isinstance(strategy, AsyncStrategy):
            queue_size = 16
            max_workers = 4
            if self.config_manager is not None:
                queue_size = self.config_manager.get_setting(
                    "pipeline.queue_size", 16,
                )
                max_workers = self.config_manager.get_setting(
                    "pipeline.max_workers", 4,
                )
            lines.append(f"  Queue size   : {queue_size}")
            lines.append(f"  Max workers  : {max_workers}")

        debug_mode = False
        if self.config_manager is not None:
            debug_mode = self.config_manager.get_setting(
                "advanced.debug_mode", False,
            )
        lines.append(f"  Debug mode   : {'ON' if debug_mode else 'OFF'}")

        lines.append("")
        lines.append("  Stages:")
        for i, stage in enumerate(stages, 1):
            if isinstance(stage, PluginAwareStage):
                pre_names = [type(p).__name__ for p in stage.pre_plugins]
                post_names = [type(p).__name__ for p in stage.post_plugins]
                parts: list[str] = []
                if pre_names:
                    parts.append(f"pre: {', '.join(pre_names)}")
                if post_names:
                    parts.append(f"post: {', '.join(post_names)}")
                suffix = f"  [{'; '.join(parts)}]" if parts else ""
                lines.append(f"    {i}. {stage.name}{suffix}")
            else:
                stage_name = getattr(stage, "name", type(stage).__name__)
                lines.append(f"    {i}. {stage_name}")

        lines.append(sep)
        self.logger.info("\n".join(lines))

    # ------------------------------------------------------------------
    # Plugin map (Phase 2A.3)
    # ------------------------------------------------------------------

    def _build_plugin_map(
        self,
        optimizer_loader: Any = None,
        text_processor_loader: Any = None,
        *,
        stage_aliases: dict[str, list[str]] | None = None,
    ) -> dict[str, dict[str, list[Any]]]:
        """Build a mapping from pipeline-stage name to pre/post enhancer plugins.

        Reads ``target_stage`` and ``stage`` from each loaded plugin's
        ``plugin.json`` metadata.  Optimizer plugins declare both fields
        explicitly.  Text-processor plugins default to
        ``target_stage="ocr", stage="post"`` when the fields are absent
        (they operate on OCR output before translation).

        Plugins whose ``stage`` is not ``"pre"`` or ``"post"`` (e.g.
        ``"global"``, ``"standalone"``) are pipeline-wide and are excluded
        from the per-stage map.

        If *stage_aliases* is provided, e.g. ``{"vision_translate": ["translation"]}``,
        plugins registered for the source stage(s) are also attached to the
        alias stage (so vision pipeline can use translation-stage plugins
        like learning_dictionary and context_manager).

        Returns
        -------
        dict
            ``{stage_name: {"pre": [plugin_obj, …], "post": [plugin_obj, …]}}``
        """
        plugin_map: dict[str, dict[str, list[Any]]] = {}

        def _ensure_stage(stage_name: str) -> None:
            if stage_name not in plugin_map:
                plugin_map[stage_name] = {"pre": [], "post": []}

        # -- Optimizer plugins ------------------------------------------------
        opt_plugins: dict[str, Any] = (
            getattr(optimizer_loader, "plugins", {})
            if optimizer_loader is not None
            else {}
        )
        for _name, info in opt_plugins.items():
            metadata = info.get("metadata", {})
            target = metadata.get("target_stage", "")
            hook = metadata.get("stage", "")
            if hook not in ("pre", "post") or not target:
                continue
            plugin_obj = info.get("optimizer")
            if plugin_obj is None:
                continue
            _ensure_stage(target)
            plugin_map[target][hook].append(plugin_obj)

            # Auto-register as post-plugin too when the optimizer
            # exposes a post-processing method (e.g. learning_dictionary,
            # context_manager).
            if hook == "pre" and (
                hasattr(plugin_obj, "post_process")
                or hasattr(plugin_obj, "post_process_pipeline")
            ):
                plugin_map[target]["post"].append(
                    _PostProcessAdapter(plugin_obj)
                )

        # -- Text-processor plugins -------------------------------------------
        tp_plugins: dict[str, Any] = (
            getattr(text_processor_loader, "plugins", {})
            if text_processor_loader is not None
            else {}
        )
        tp_entries: list[tuple] = []
        for _name, info in tp_plugins.items():
            metadata = info.get("metadata", {})
            target = metadata.get("target_stage", "ocr")
            hook = metadata.get("stage", "post")
            if hook not in ("pre", "post"):
                hook = "post"
            if not target:
                target = "ocr"
            plugin_obj = info.get("processor")
            if plugin_obj is None:
                continue
            priority = metadata.get("priority", 50)
            tp_entries.append((target, hook, priority, plugin_obj))

        tp_entries.sort(key=lambda entry: entry[2])
        for target, hook, _prio, plugin_obj in tp_entries:
            _ensure_stage(target)
            plugin_map[target][hook].append(plugin_obj)

        # Apply stage aliases (e.g. vision_translate uses translation-stage plugins)
        if stage_aliases:
            for alias_stage, source_stages in stage_aliases.items():
                _ensure_stage(alias_stage)
                for src in source_stages:
                    if src not in plugin_map:
                        continue
                    for hook in ("pre", "post"):
                        plugin_map[alias_stage][hook].extend(plugin_map[src][hook])
                self.logger.debug(
                    "Plugin map alias: %s <- %s",
                    alias_stage, source_stages,
                )

        self.logger.debug(
            "Plugin map: %s",
            {k: {h: len(v) for h, v in plugin_map[k].items()} for k in plugin_map},
        )
        return plugin_map
