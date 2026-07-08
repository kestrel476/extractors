"""
EPUB: извлечение текста из электронных книг.

EPUB — это ZIP-контейнер с XHTML-главами. Парсим через ebooklib + BeautifulSoup,
а при их отсутствии — резервно читаем XHTML напрямую из ZIP.
"""

from __future__ import annotations

from typing import List

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


def _html_to_text(bs4, html: str) -> str:
    soup = bs4.BeautifulSoup(html, features="html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    lines = [ln.strip() for ln in soup.get_text().splitlines()]
    return "\n".join(ln for ln in lines if ln)


class EpubExtractor(BaseExtractor):
    """Извлечение текста из .epub."""

    MIME_TYPES = frozenset({"application/epub+zip"})
    EXTENSIONS = (".epub",)

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение EPUB")
        try:
            bs4 = self.require("bs4", pip_name="beautifulsoup4")
        except ImportError as e:
            return self.dependency_error(e)

        # Предпочтительно ebooklib (соблюдает порядок чтения spine).
        try:
            ebooklib = self.require("ebooklib")
            epub = self.require("ebooklib.epub", pip_name="EbookLib")
        except ImportError:
            return self._fallback_zip(bs4, src)

        try:
            if src.data is not None:
                # ebooklib читает только из файла → используем резервный ZIP-путь для байтов.
                if not src.path:
                    return self._fallback_zip(bs4, src)
            book = epub.read_epub(src.path)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"ebooklib не справился, fallback: {e}")
            return self._fallback_zip(bs4, src)

        parts: List[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            t = _html_to_text(bs4, item.get_content().decode("utf-8", errors="ignore"))
            if t:
                parts.append(t)
        return ExtractionResult.success("\n\n".join(parts))

    def _fallback_zip(self, bs4, src: FileSource) -> ExtractionResult:
        """Резерв: читаем XHTML-главы прямо из ZIP-контейнера EPUB."""
        import zipfile

        try:
            source = self.binary_source(src)
            with zipfile.ZipFile(source) as zf:
                names = sorted(
                    n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))
                )
                parts: List[str] = []
                for n in names:
                    t = _html_to_text(bs4, zf.read(n).decode("utf-8", errors="ignore"))
                    if t:
                        parts.append(t)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        return ExtractionResult.success("\n\n".join(parts))
