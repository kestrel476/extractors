"""
Apple iWork: Keynote (.key), Pages (.pages), Numbers (.numbers).

Современные iWork-файлы — это ZIP-пакеты с проприетарным IWA (snappy-сжатый
protobuf), полноценный разбор которого без специализированных библиотек
невозможен. Однако пакеты часто содержат готовый PDF-предпросмотр
(``preview.pdf`` / ``QuickLook/Preview.pdf``) — из него и извлекаем текст,
прогоняя через переданный фасад. Если предпросмотра нет, файл помечается как
требующий OCR (его рендер можно распознать).
"""

from __future__ import annotations

import zipfile
from typing import Optional

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource

_PREVIEW_NAMES = ("preview.pdf", "quicklook/preview.pdf", "preview-web.pdf")


class IWorkExtractor(BaseExtractor):
    """Best-effort извлечение текста из iWork через встроенный PDF-предпросмотр."""

    MIME_TYPES = frozenset(
        {
            "application/x-iwork-keynote-sffkey",
            "application/x-iwork-pages-sffpages",
            "application/x-iwork-numbers-sffnumbers",
        }
    )
    EXTENSIONS = (".key", ".pages", ".numbers")

    def __init__(self, facade=None, logger=None) -> None:
        super().__init__(logger=logger)
        self.facade = facade  # FileTextExtractor; задаётся в bootstrap

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение iWork (через PDF-предпросмотр)")
        try:
            source = self.binary_source(src)
            with zipfile.ZipFile(source) as zf:
                names = {n.lower(): n for n in zf.namelist()}
                preview = next((names[p] for p in _PREVIEW_NAMES if p in names), None)
                if preview is None:
                    # Иногда предпросмотр лежит как любой *.pdf внутри пакета.
                    preview = next((real for low, real in names.items() if low.endswith(".pdf")), None)
                if preview is None:
                    self.logger.log("DOC_EXTRACTION", "PDF-предпросмотр не найден → OCR")
                    return ExtractionResult.no_text_layer(
                        meta={"note": "iWork без PDF-предпросмотра; нужен рендер+OCR"}
                    )
                pdf_bytes = zf.read(preview)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        if self.facade is None:
            return ExtractionResult.failure("IWorkExtractor requires facade", code=ErrorCodes.READ_ERROR)
        text, err = self.facade.extract_text_from_bytes(filename="preview.pdf", data=pdf_bytes)
        if err:
            return ExtractionResult.failure(err, code=ErrorCodes.READ_ERROR)
        if not text:
            return ExtractionResult.no_text_layer(meta={"note": "PDF-предпросмотр без текстового слоя"})
        return ExtractionResult.success(text, meta={"source": "iwork-preview"})
