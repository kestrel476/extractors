"""
Фасад — главная точка входа сервиса извлечения текста.

Конвейер обработки:

1. Определение MIME-типа (по содержимому и/или расширению).
2. Предпроверка текстового слоя: если файл заведомо без него (изображение) —
   сразу в OCR.
3. Выбор экстрактора по MIME/имени; если нет — статус ``UNSUPPORTED``.
4. Запуск экстрактора.
5. Постпроверка: если экстрактор сообщил об отсутствии текстового слоя
   (``needs_ocr``) — запуск OCR.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from ._logging import NullLogger
from .errors import ErrorCodes
from .interfaces import OcrEngine
from .mime_detect import MagicMimeDetector
from .registry import ExtractorRegistry
from .text_layer import definitely_needs_ocr
from .types import ExtractionResult, ExtractionStatus, FileSource


class FileTextExtractor:
    """Высокоуровневый сервис извлечения текста из файлов произвольного формата."""

    def __init__(
        self,
        registry: ExtractorRegistry,
        mime_detector: Optional[MagicMimeDetector] = None,
        ocr: Optional[OcrEngine] = None,
        md_renderer=None,
        logger=None,
    ) -> None:
        self.registry = registry
        self.logger = logger or NullLogger()
        self.mime_detector = mime_detector or MagicMimeDetector()
        self.ocr = ocr  # может быть None — тогда OCR-маршрут не используется
        self.md_renderer = md_renderer  # markitdown-рендер для md-режима (может быть None)

    # --- Обратносовместимый «кортежный» API ---------------------------------

    def extract_text(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает текст из файла по пути. Возвращает ``(text, error)``."""
        self.logger.log("DOC_EXTRACTION", f"Начало извлечения текста из файла: {file_path}")
        src = FileSource(path=file_path, filename=os.path.basename(file_path))
        res = self.extract(src)
        return res.text, res.error

    def extract_text_from_bytes(
        self, filename: str, data: bytes
    ) -> Tuple[Optional[str], Optional[str]]:
        """Извлекает текст из байтов. Возвращает ``(text, error)``."""
        self.logger.log("DOC_EXTRACTION", f"Начало извлечения текста из байтов: {filename}")
        src = FileSource(data=data, filename=filename)
        res = self.extract(src)
        return res.text, res.error

    # --- Богатый API ---------------------------------------------------------

    def extract(self, src: FileSource, *, markdown: bool = False) -> ExtractionResult:
        """Извлекает содержимое и возвращает полный :class:`ExtractionResult`.

        Args:
            src: Источник файла (путь и/или байты).
            markdown: Если ``True`` — возвращает содержимое в формате Markdown
                (таблицы сохраняются), пригодное для подачи в LLM. Иначе —
                обычный текстовый слой.
        """
        # 1) MIME
        mime = src.mime or self.mime_detector.detect(src)
        src.mime = mime
        self.logger.log("DOC_EXTRACTION", f"Определён тип файла: {mime}")

        # 2) Предпроверка текстового слоя: изображения сразу в OCR.
        if definitely_needs_ocr(mime, src.filename):
            self.logger.log("DOC_EXTRACTION", "Текстовый слой отсутствует (изображение) → OCR")
            return self._run_ocr(src)

        # Markdown-режим обрабатывается отдельным конвейером.
        if markdown:
            return self._extract_markdown(src, mime)

        # 3) Выбор экстрактора.
        extractor = self.registry.pick(mime, src.filename)
        if not extractor:
            self.logger.log(
                "DOC_EXTRACTION_ERROR",
                f"Не найден экстрактор для mime='{mime}', файла '{src.filename}'",
            )
            return ExtractionResult(
                text=None,
                error="Unsupported format",
                status=ExtractionStatus.UNSUPPORTED,
                meta={
                    "code": ErrorCodes.UNSUPPORTED_FORMAT,
                    "mime": str(mime),
                    "filename": str(src.filename),
                },
            )

        # 4) Запуск экстрактора.
        try:
            self.logger.log("DOC_EXTRACTION", f"Выбран экстрактор: {extractor.__class__.__name__}")
            result = extractor.extract(src)
        except Exception as e:  # noqa: BLE001 - изоляция любых сбоев хендлера
            self.logger.log("DOC_EXTRACTION_ERROR", f"Ошибка обработки файла: {e}")
            return ExtractionResult.failure(
                "Error processing file",
                code=ErrorCodes.READ_ERROR,
                meta={"mime": str(mime), "filename": str(src.filename), "detail": str(e)},
            )

        # 5) Постпроверка: нет текстового слоя → OCR.
        if result.needs_ocr or result.status == ExtractionStatus.NO_TEXT_LAYER:
            self.logger.log("DOC_EXTRACTION", "Экстрактор не нашёл текстовый слой → OCR")
            return self._run_ocr(src, base_meta=result.meta)

        self.logger.log("DOC_EXTRACTION", f"Экстрактор {extractor.__class__.__name__} завершил работу")
        return result

    # --- Markdown-конвейер ---------------------------------------------------

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Удобная обёртка: то же, что ``extract(src, markdown=True)``."""
        return self.extract(src, markdown=True)

    def _extract_markdown(self, src: FileSource, mime: Optional[str]) -> ExtractionResult:
        """Конвейер Markdown-режима: markitdown → нативный md-рендер → текст."""
        # Тир 1: markitdown для поддерживаемых форматов (docx/xlsx/pptx/pdf/...).
        if self.md_renderer is not None and self.md_renderer.can_handle(mime, src.filename):
            self.logger.log("DOC_EXTRACTION", "Markdown через markitdown")
            md = self.md_renderer.render(src)
            if md is not None:
                if md.needs_ocr or md.status == ExtractionStatus.NO_TEXT_LAYER:
                    return self._run_ocr(src, base_meta=md.meta)
                return md
            # None → markitdown не справился, откат на нативный путь.

        # Тир 2/3: нативный md-рендер хендлера, иначе — обычный текст как Markdown.
        extractor = self.registry.pick(mime, src.filename)
        if not extractor:
            self.logger.log(
                "DOC_EXTRACTION_ERROR",
                f"Не найден экстрактор для mime='{mime}', файла '{src.filename}'",
            )
            return ExtractionResult(
                text=None,
                error="Unsupported format",
                status=ExtractionStatus.UNSUPPORTED,
                meta={
                    "code": ErrorCodes.UNSUPPORTED_FORMAT,
                    "mime": str(mime),
                    "filename": str(src.filename),
                },
            )

        try:
            md_method = getattr(extractor, "extract_markdown", None)
            result = md_method(src) if callable(md_method) else None
            if result is None:
                # Нативного md-рендера нет: текст хендлера сам по себе валиден
                # как Markdown (plain-text, код, разметка, XML/JSON).
                self.logger.log(
                    "DOC_EXTRACTION",
                    f"Markdown-рендер отсутствует у {extractor.__class__.__name__}, "
                    "используется текстовое извлечение",
                )
                result = extractor.extract(src)
                if result.status == ExtractionStatus.OK:
                    result.meta.setdefault("format", "text")
            else:
                result.meta.setdefault("format", "markdown")
        except Exception as e:  # noqa: BLE001 - изоляция любых сбоев хендлера
            self.logger.log("DOC_EXTRACTION_ERROR", f"Ошибка Markdown-рендера: {e}")
            return ExtractionResult.failure(
                "Error processing file",
                code=ErrorCodes.READ_ERROR,
                meta={"mime": str(mime), "filename": str(src.filename), "detail": str(e)},
            )

        # Постпроверка: нет текстового слоя → OCR.
        if result.needs_ocr or result.status == ExtractionStatus.NO_TEXT_LAYER:
            self.logger.log("DOC_EXTRACTION", "Markdown-рендер не нашёл текстовый слой → OCR")
            return self._run_ocr(src, base_meta=result.meta)
        return result

    # --- OCR-маршрут ---------------------------------------------------------

    def _run_ocr(self, src: FileSource, base_meta: Optional[dict] = None) -> ExtractionResult:
        if self.ocr is None:
            # OCR-движок не сконфигурирован: честно отдаём статус NO_TEXT_LAYER.
            meta = dict(base_meta or {})
            meta.setdefault("code", ErrorCodes.NO_TEXT_LAYER)
            meta["mime"] = str(src.mime)
            meta["filename"] = str(src.filename)
            return ExtractionResult.no_text_layer(
                meta=meta, warnings=["OCR-движок не подключён"]
            )
        return self.ocr.recognize(src)
