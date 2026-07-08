"""
PDF: извлечение текстового слоя через PyMuPDF (fitz).

Если в документе нет извлекаемого текста (скан без OCR), возвращается результат
со статусом ``NO_TEXT_LAYER`` — фасад направит файл в OCR.
"""

from __future__ import annotations

from typing import Optional

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class PdfExtractor(BaseExtractor):
    """Извлечение текста из PDF."""

    MIME_TYPES = frozenset({"application/pdf", "application/x-pdf"})
    EXTENSIONS = (".pdf",)

    def __init__(self, max_pages: Optional[int] = None, logger=None) -> None:
        super().__init__(logger=logger)
        self.max_pages = max_pages

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение PDF")
        try:
            fitz = self.require("fitz", pip_name="PyMuPDF")
        except ImportError as e:
            return self.dependency_error(e)

        try:
            if src.data is not None:
                doc = fitz.open(stream=src.data, filetype="pdf")
            elif src.path:
                doc = fitz.open(src.path)
            else:
                return ExtractionResult.failure("requires data or path", code=ErrorCodes.READ_ERROR)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Не удалось открыть PDF: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            total_pages = len(doc)
            limit = total_pages
            warnings = []
            if self.max_pages is not None and total_pages > self.max_pages:
                limit = self.max_pages
                warnings.append(f"Truncated to {self.max_pages} pages")

            chunks = []
            for pno in range(limit):
                t = doc.load_page(pno).get_text()
                if t and t.strip():
                    chunks.append(t)
            doc.close()
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Ошибка чтения PDF: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        # Нет текста ни на одной странице → текстового слоя нет, нужен OCR.
        if not chunks:
            self.logger.log("DOC_EXTRACTION", "В PDF отсутствует текстовый слой → OCR")
            return ExtractionResult.no_text_layer(meta={"pages": str(total_pages)})

        return ExtractionResult.success(
            "\n\n".join(chunks), meta={"pages": str(total_pages)}, warnings=warnings
        )
