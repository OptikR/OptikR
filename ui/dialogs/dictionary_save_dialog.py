"""
Post-Translation Dictionary Save Dialog

Shown when the pipeline stops, letting the user choose how to persist
the translations learned during the session:

- Save full sentences to the Smart Dictionary
- Extract individual words from those sentences and translate+save them
- Both
- Discard (don't save)
"""

import logging
import re
from typing import Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QGroupBox, QProgressBar,
    QCheckBox, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

logger = logging.getLogger(__name__)

_CJK_LANGUAGES = frozenset({'ja', 'zh', 'zh-cn', 'zh-tw', 'ko'})


def _extract_source_words(text: str, lang: str) -> list[str]:
    """Split source text into individual words/tokens.

    For CJK languages every CJK character sequence of length >= 1
    is treated as a potential word (since they have no whitespace).
    For other languages standard whitespace splitting is used and
    punctuation is stripped.
    """
    if lang in _CJK_LANGUAGES:
        tokens = re.findall(r'[\u3000-\u9fff\uf900-\ufaff\u4e00-\u9faf'
                            r'\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+', text)
        return [t for t in tokens if len(t) >= 1]

    raw = re.findall(r"[^\s\d\W]+", text, flags=re.UNICODE)
    return [w for w in raw if len(w) >= 2]


class _WordExtractWorker(QThread):
    """Background worker that translates individual words."""

    progress = pyqtSignal(int, int)          # current, total
    word_done = pyqtSignal(str, str, float)  # source, translation, confidence
    finished_signal = pyqtSignal(int)        # total saved

    def __init__(
        self,
        words: list[str],
        translation_layer: Any,
        source_lang: str,
        target_lang: str,
        dictionary: Any,
        parent=None,
    ):
        super().__init__(parent)
        self._words = words
        self._tl = translation_layer
        self._src = source_lang
        self._tgt = target_lang
        self._dict = dictionary
        self._saved = 0

    def run(self):
        total = len(self._words)
        for i, word in enumerate(self._words):
            self.progress.emit(i + 1, total)
            try:
                existing = self._dict.lookup(word, self._src, self._tgt)
                if existing:
                    continue

                result = self._tl.translate(
                    text=word,
                    source_lang=self._src,
                    target_lang=self._tgt,
                )
                translated = str(result) if result else ""
                if not translated or translated.strip().lower() == word.strip().lower():
                    continue

                confidence = 0.85
                self._dict.learn_from_translation(
                    source_text=word,
                    translation=translated,
                    source_language=self._src,
                    target_language=self._tgt,
                    confidence=confidence,
                )
                self._saved += 1
                self.word_done.emit(word, translated, confidence)
            except Exception as exc:
                logger.debug("Word extraction failed for '%s': %s", word, exc)

        self.finished_signal.emit(self._saved)


class DictionarySaveDialog(QDialog):
    """Post-translation dialog asking the user how to save learned translations."""

    def __init__(
        self,
        learned_count: int,
        source_lang: str = "ja",
        target_lang: str = "en",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Save Translations")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._learned_count = learned_count
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._choice: str | None = None  # "sentences", "words", "both", or None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(
            f"<b>Translation session complete</b><br>"
            f"<span style='color:#666;'>{self._learned_count} translation(s) learned "
            f"({self._source_lang.upper()} \u2192 {self._target_lang.upper()})</span>"
        )
        header.setWordWrap(True)
        header.setStyleSheet("font-size: 11pt; margin-bottom: 4px;")
        layout.addWidget(header)

        question = QLabel("How would you like to save these translations to the Smart Dictionary?")
        question.setWordWrap(True)
        question.setStyleSheet("font-size: 10pt;")
        layout.addWidget(question)

        group = QGroupBox()
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        group_layout.setContentsMargins(12, 16, 12, 12)

        self._btn_group = QButtonGroup(self)

        self._radio_sentences = QRadioButton("Save full sentences only")
        self._radio_sentences.setChecked(True)
        self._radio_sentences.setToolTip(
            "Save each translated sentence/phrase as-is to the dictionary."
        )
        self._btn_group.addButton(self._radio_sentences, 0)
        group_layout.addWidget(self._radio_sentences)

        desc_sent = QLabel(
            "  Saves each translated phrase exactly as it was translated.\n"
            "  Fast \u2014 no extra translation needed."
        )
        desc_sent.setStyleSheet("color: #666; font-size: 8pt; margin-left: 20px; margin-bottom: 4px;")
        group_layout.addWidget(desc_sent)

        self._radio_words = QRadioButton("Extract and save individual words only")
        self._radio_words.setToolTip(
            "Split sentences into words, translate each word separately, "
            "and save only the individual word translations."
        )
        self._btn_group.addButton(self._radio_words, 1)
        group_layout.addWidget(self._radio_words)

        desc_words = QLabel(
            "  Extracts words from the source text and translates each one individually.\n"
            "  Slower (requires translating each word) but builds a word-level dictionary."
        )
        desc_words.setStyleSheet("color: #666; font-size: 8pt; margin-left: 20px; margin-bottom: 4px;")
        group_layout.addWidget(desc_words)

        self._radio_both = QRadioButton("Save both sentences and individual words")
        self._radio_both.setToolTip(
            "Save the full sentence translations AND extract individual words."
        )
        self._btn_group.addButton(self._radio_both, 2)
        group_layout.addWidget(self._radio_both)

        desc_both = QLabel(
            "  Best coverage \u2014 saves sentence translations and builds word dictionary.\n"
            "  Takes the longest but gives the best results for future lookups."
        )
        desc_both.setStyleSheet("color: #666; font-size: 8pt; margin-left: 20px; margin-bottom: 4px;")
        group_layout.addWidget(desc_both)

        layout.addWidget(group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #555; font-size: 8pt;")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._discard_btn = QPushButton("Discard")
        self._discard_btn.setMinimumWidth(100)
        self._discard_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._discard_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.setMinimumWidth(120)
        self._save_btn.setDefault(True)
        self._save_btn.setStyleSheet(
            "background-color: #27AE60; color: white; font-weight: bold; padding: 6px 16px;"
        )
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        selected = self._btn_group.checkedId()
        if selected == 0:
            self._choice = "sentences"
        elif selected == 1:
            self._choice = "words"
        elif selected == 2:
            self._choice = "both"
        self.accept()

    @property
    def choice(self) -> str | None:
        return self._choice

    def show_progress(self, visible: bool):
        self._progress_bar.setVisible(visible)
        self._status_label.setVisible(visible)
        self._save_btn.setEnabled(not visible)
        self._discard_btn.setEnabled(not visible)
        for btn in self._btn_group.buttons():
            btn.setEnabled(not visible)

    def update_progress(self, current: int, total: int):
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._status_label.setText(f"Translating word {current}/{total}...")

    def set_status(self, text: str):
        self._status_label.setText(text)


def show_dictionary_save_dialog(
    parent,
    startup_pipeline: Any,
    learned_count: int,
) -> bool:
    """Show the save dialog and execute the chosen action.

    Returns True if translations were saved, False otherwise.
    """
    if learned_count <= 0:
        return False

    source_lang = "ja"
    target_lang = "en"
    if startup_pipeline and startup_pipeline.config_manager:
        source_lang = startup_pipeline.config_manager.get_setting(
            'translation.source_language', 'ja')
        target_lang = startup_pipeline.config_manager.get_setting(
            'translation.target_language', 'en')

    # Defer automatic dictionary saving so cleanup doesn't persist
    # entries before the user has made their choice.
    cache_mgr = startup_pipeline.cache_manager if startup_pipeline else None
    smart_dict = getattr(cache_mgr, 'persistent_dictionary', None) if cache_mgr else None
    if cache_mgr is not None:
        cache_mgr.defer_dictionary_save = True

    dialog = DictionarySaveDialog(
        learned_count=learned_count,
        source_lang=source_lang,
        target_lang=target_lang,
        parent=parent,
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        # User chose to discard — revert in-memory dictionary to last
        # saved state so cleanup won't persist the session's entries.
        if smart_dict is not None and hasattr(smart_dict, 'discard_unsaved_changes'):
            smart_dict.discard_unsaved_changes()
            logger.info("User discarded learned translations — reverted dictionary")
        return False

    choice = dialog.choice

    if not cache_mgr or not smart_dict:
        logger.warning("Cannot save — cache manager or dictionary unavailable")
        return False

    saved_sentences = False
    saved_words = 0

    if choice in ("sentences", "both"):
        try:
            cache_mgr.save_all_dictionaries()
            saved_sentences = True
            logger.info("Saved %d sentence translations to dictionary", learned_count)
        except Exception as exc:
            logger.warning("Failed to save sentence translations: %s", exc)

    if choice in ("words", "both"):
        source_texts = _collect_source_texts(smart_dict, source_lang, target_lang)
        if source_texts:
            all_words: list[str] = []
            seen: set[str] = set()
            for text in source_texts:
                for w in _extract_source_words(text, source_lang):
                    wl = w.lower()
                    if wl not in seen:
                        seen.add(wl)
                        all_words.append(w)

            if all_words and startup_pipeline and startup_pipeline.translation_layer:
                dialog.show_progress(True)
                dialog.show()

                worker = _WordExtractWorker(
                    words=all_words,
                    translation_layer=startup_pipeline.translation_layer,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    dictionary=smart_dict,
                    parent=dialog,
                )
                worker.progress.connect(dialog.update_progress)

                def _on_finished(count):
                    nonlocal saved_words
                    saved_words = count
                    dialog.set_status(f"Done — {count} word(s) saved.")
                    try:
                        cache_mgr.save_all_dictionaries()
                    except Exception:
                        pass
                    dialog.show_progress(False)
                    dialog.close()

                worker.finished_signal.connect(_on_finished)
                worker.start()

                while worker.isRunning():
                    QApplication.processEvents()
                    worker.wait(50)
            else:
                logger.info("No words to extract or translation layer unavailable")
        else:
            logger.info("No source texts found for word extraction")

    if choice == "words" and not saved_sentences:
        try:
            cache_mgr.save_all_dictionaries()
        except Exception:
            pass

    # User chose to save — allow future cleanup calls to persist normally
    if cache_mgr is not None:
        cache_mgr.defer_dictionary_save = False

    return saved_sentences or saved_words > 0


def _collect_source_texts(
    smart_dict: Any, source_lang: str, target_lang: str
) -> list[str]:
    """Collect source texts from the dictionary for word extraction."""
    try:
        lang_pair = (source_lang, target_lang)
        dictionaries = getattr(smart_dict, '_dictionaries', {})
        dictionary = dictionaries.get(lang_pair, {})
        return list(dictionary.keys())
    except Exception as exc:
        logger.debug("Failed to collect source texts: %s", exc)
        return []
