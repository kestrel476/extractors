"""
DOC: устаревший бинарный формат Word.

Стратегия: конвертация .doc → .docx через headless LibreOffice, затем извлечение
текста той же логикой, что и для .docx.
"""

from __future__ import annotations

from io import BytesIO

from ._soffice import SofficeError, convert
from .base import BaseExtractor
from .docx import docx_text
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class DocExtractor(BaseExtractor):
    """Извлечение текста из .doc (через LibreOffice → .docx → python-docx)."""

    MIME_TYPES = frozenset({"application/msword"})
    EXTENSIONS = (".doc", ".dot")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение DOC через LibreOffice")
        try:
            docx = self.require("docx", pip_name="python-docx")
        except ImportError as e:
            return self.dependency_error(e)

        try:
            docx_bytes = convert(src, in_suffix=".doc", to_format="docx")
        except SofficeError as e:
            self.logger.log("DOC_EXTRACTION_ERROR", f"Конвертация .doc не удалась: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            document = docx.Document(BytesIO(docx_bytes))
            return ExtractionResult.success(docx_text(document))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)
