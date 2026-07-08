"""
PowerPoint: PPTX (python-pptx) и устаревший PPT (LibreOffice → PPTX).
"""

from __future__ import annotations

from io import BytesIO
from typing import List

from ._soffice import SofficeError, convert
from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


def _pptx_text(presentation) -> str:
    """Собирает текст из всех слайдов: фигуры с текстом, таблицы, заметки."""
    parts: List[str] = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs)
                    if line.strip():
                        parts.append(line)
            if shape.has_table:
                for row in shape.table.rows:
                    parts.append("\t".join(cell.text or "" for cell in row.cells))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            note = slide.notes_slide.notes_text_frame.text
            if note and note.strip():
                parts.append(note.strip())
    return "\n".join(parts).strip()


class PptxExtractor(BaseExtractor):
    """Извлечение текста из .pptx и (через LibreOffice) .ppt."""

    MIME_TYPES = frozenset(
        {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
            "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
        }
    )
    EXTENSIONS = (".pptx", ".pptm", ".ppt")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение PowerPoint")
        try:
            pptx = self.require("pptx", pip_name="python-pptx")
        except ImportError as e:
            return self.dependency_error(e)

        name = (src.filename or "").lower()
        is_legacy = name.endswith(".ppt") or src.mime == "application/vnd.ms-powerpoint"

        data = src.data
        try:
            if is_legacy and not name.endswith(".pptx"):
                # .ppt → .pptx через LibreOffice.
                data = convert(src, in_suffix=".ppt", to_format="pptx")
                presentation = pptx.Presentation(BytesIO(data))
            elif data is not None:
                presentation = pptx.Presentation(BytesIO(data))
            elif src.path:
                presentation = pptx.Presentation(src.path)
            else:
                return ExtractionResult.failure("requires data or path", code=ErrorCodes.READ_ERROR)
        except SofficeError as e:
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Не удалось открыть презентацию: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            return ExtractionResult.success(_pptx_text(presentation))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)
