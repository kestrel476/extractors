"""
Markdown-рендер через библиотеку `markitdown` (Microsoft).

Отвечает за форматы, которые markitdown умеет конвертировать в Markdown с
сохранением структуры и таблиц: Office OOXML (docx/xlsx/pptx), PDF, HTML, EPUB,
Jupyter, Outlook .msg. Для всего остального используются нативные md-рендеры
хендлеров (см. ``BaseExtractor.extract_markdown``) либо, как резерв, обычное
извлечение текста.

Компонент необязателен: если ``markitdown`` не установлен или конвертация не
удалась, :meth:`render` возвращает ``None`` — фасад мягко откатывается на
нативный путь.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, Optional

from ._logging import NullLogger
from .types import ExtractionResult, FileSource


class MarkItDownRenderer:
    """Обёртка над ``markitdown.MarkItDown`` с интерфейсом, близким к экстрактору."""

    #: Расширения, которые в md-режиме отдаём markitdown (он справляется лучше
    #: нативных текстовых хендлеров за счёт таблиц и структуры).
    SUPPORTED_EXT = frozenset(
        {
            ".docx", ".docm", ".dotx",
            ".xlsx", ".xls",
            ".pptx", ".pptm",
            ".pdf",
            ".html", ".htm", ".xhtml",
            ".epub",
            ".ipynb",
            ".msg",
        }
    )

    #: MIME-типы, соответствующие поддерживаемым форматам (запасной путь, когда
    #: имя файла отсутствует или ненадёжно).
    SUPPORTED_MIME = frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-word.document.macroEnabled.12",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
            "application/pdf",
            "application/x-pdf",
            "text/html",
            "application/xhtml+xml",
            "application/epub+zip",
            "application/vnd.ms-outlook",
        }
    )

    def __init__(self, logger=None) -> None:
        self.logger = logger or NullLogger()
        self._mid = None  # ленивая инициализация MarkItDown

    def can_handle(self, mime: Optional[str], filename: Optional[str]) -> bool:
        if mime and mime in self.SUPPORTED_MIME:
            return True
        name = (filename or "").lower()
        return bool(name) and any(name.endswith(ext) for ext in self.SUPPORTED_EXT)

    def _engine(self):
        """Лениво создаёт экземпляр MarkItDown (может бросить ImportError)."""
        if self._mid is None:
            from markitdown import MarkItDown

            self._mid = MarkItDown()
        return self._mid

    def render(self, src: FileSource) -> Optional[ExtractionResult]:
        """Конвертирует источник в Markdown.

        Returns:
            - ``ExtractionResult`` со статусом ``OK`` и Markdown в ``text``;
            - ``ExtractionResult`` со статусом ``NO_TEXT_LAYER`` (пустой результат
              или сбой конвертации, характерный для сканов) — фасад отправит в OCR;
            - ``None`` — markitdown недоступен либо формат ему не по силам; фасад
              откатится на нативный md-рендер/извлечение текста.
        """
        try:
            mid = self._engine()
        except Exception as e:  # noqa: BLE001 - markitdown не установлен
            self.logger.log("DOC_EXTRACTION", f"markitdown недоступен, откат на нативный путь: {e}")
            return None

        stream_info_cls: Any = None
        try:
            from markitdown import StreamInfo

            stream_info_cls = StreamInfo
        except Exception:  # noqa: BLE001 - очень старый markitdown без StreamInfo
            stream_info_cls = None

        try:
            raw = src.data if src.data is not None else self._read_path(src.path)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"markitdown: не удалось прочитать источник: {e}")
            return None

        ext = src.ext or None
        try:
            if stream_info_cls is not None:
                info = stream_info_cls(extension=ext, mimetype=src.mime, filename=src.filename)
                result = mid.convert_stream(BytesIO(raw), stream_info=info)
            else:  # очень старый markitdown без StreamInfo
                result = mid.convert_stream(BytesIO(raw), file_extension=ext)
        except Exception as e:  # noqa: BLE001 - MissingDependency / FileConversion / Unsupported
            cls = type(e).__name__
            if cls == "MissingDependencyException":
                # Нет опциональной зависимости markitdown под этот формат —
                # пусть нативный хендлер попробует сам.
                self.logger.log("DOC_EXTRACTION", f"markitdown: нет зависимости ({e}) → нативный путь")
                return None
            # Битый файл / скан / неподдерживаемое содержимое: кандидат на OCR,
            # но нативный путь может справиться лучше — откатываемся.
            self.logger.log("DOC_EXTRACTION", f"markitdown не смог сконвертировать ({cls}) → нативный путь")
            return None

        markdown = (getattr(result, "markdown", None) or getattr(result, "text_content", None) or "").strip()
        if not markdown:
            # Конвертация прошла, но текста нет (например, скан в PDF) → OCR.
            self.logger.log("DOC_EXTRACTION", "markitdown: пустой результат → нет текстового слоя")
            return ExtractionResult.no_text_layer(
                meta={"renderer": "markitdown", "format": "markdown"}
            )

        meta = {"renderer": "markitdown", "format": "markdown"}
        title = getattr(result, "title", None)
        if title:
            meta["title"] = str(title)
        return ExtractionResult.success(markdown, meta=meta)

    @staticmethod
    def _read_path(path: Optional[str]) -> bytes:
        if not path:
            raise ValueError("MarkItDownRenderer requires path or data")
        with open(path, "rb") as f:
            return f.read()
