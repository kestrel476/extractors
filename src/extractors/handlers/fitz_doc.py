"""
Документы с фиксированным макетом и e-books, которые читает MuPDF (PyMuPDF/fitz):
XPS, OpenXPS, FictionBook (FB2), Mobipocket/Kindle (MOBI/AZW/AZW3), Comic Book ZIP (CBZ).

MuPDF извлекает текстовый слой так же, как из PDF. Если текста нет (например, CBZ —
это набор изображений), возвращается ``NO_TEXT_LAYER`` → фасад направит файл в OCR.
"""

from __future__ import annotations

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource

# Сопоставление расширения и типа, который понимает fitz.open(filetype=...).
_FILETYPE_BY_EXT = {
    ".xps": "xps",
    ".oxps": "xps",
    ".fb2": "fb2",
    ".mobi": "mobi",
    ".azw": "mobi",
    ".azw3": "mobi",
    ".cbz": "cbz",
}


class FitzDocExtractor(BaseExtractor):
    """Извлечение текста из XPS/OXPS/FB2/MOBI/AZW/CBZ через MuPDF."""

    MIME_TYPES = frozenset(
        {
            "application/oxps",
            "application/vnd.ms-xpsdocument",
            "application/x-fictionbook+xml",
            "application/x-mobipocket-ebook",
            "application/vnd.amazon.ebook",
            "application/vnd.comicbook+zip",
        }
    )
    EXTENSIONS = (".xps", ".oxps", ".fb2", ".mobi", ".azw", ".azw3", ".cbz")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение через MuPDF (xps/fb2/mobi/cbz)")
        try:
            fitz = self.require("fitz", pip_name="PyMuPDF")
        except ImportError as e:
            return self.dependency_error(e)

        filetype = _FILETYPE_BY_EXT.get(src.ext)
        try:
            if src.data is not None:
                doc = fitz.open(stream=src.data, filetype=filetype)
            elif src.path:
                doc = fitz.open(src.path, filetype=filetype)
            else:
                return ExtractionResult.failure("requires data or path", code=ErrorCodes.READ_ERROR)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"MuPDF не открыл файл: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            total = len(doc)
            chunks = []
            for pno in range(total):
                t = doc.load_page(pno).get_text()
                if t and t.strip():
                    chunks.append(t)
            doc.close()
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        if not chunks:
            return ExtractionResult.no_text_layer(meta={"pages": str(total)})
        return ExtractionResult.success("\n\n".join(chunks), meta={"pages": str(total)})
