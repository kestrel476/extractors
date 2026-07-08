"""
DOCX: извлечение текста из Word OOXML через python-docx.
"""

from __future__ import annotations

from io import BytesIO
from typing import List

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


def docx_text(document) -> str:
    """Собирает текст из объекта ``docx.Document`` (параграфы + таблицы)."""
    parts: List[str] = []
    for p in document.paragraphs:
        if p.text:
            parts.append(p.text)
    for table in document.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text or "" for cell in row.cells))
    return "\n".join(parts).strip()


class DocxExtractor(BaseExtractor):
    """Извлечение текста из .docx."""

    MIME_TYPES = frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-word.document.macroEnabled.12",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
        }
    )
    EXTENSIONS = (".docx", ".docm", ".dotx")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение DOCX")
        try:
            docx = self.require("docx", pip_name="python-docx")
        except ImportError as e:
            return self.dependency_error(e)

        try:
            if src.data is not None:
                document = docx.Document(BytesIO(src.data))
            elif src.path:
                document = docx.Document(src.path)
            else:
                return ExtractionResult.failure("requires data or path", code=ErrorCodes.READ_ERROR)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Не удалось открыть DOCX: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            text = docx_text(document)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        return ExtractionResult.success(text)
