"""
HTML / XHTML: извлечение видимого текста через BeautifulSoup.
"""

from __future__ import annotations

from html import unescape

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource

_BLOCK_TAGS = ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr"]


class HtmlExtractor(BaseExtractor):
    """Извлечение текста из HTML/XHTML."""

    MIME_TYPES = frozenset({"text/html", "application/xhtml+xml"})
    EXTENSIONS = (".html", ".htm", ".xhtml")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение HTML")
        try:
            bs4 = self.require("bs4", pip_name="beautifulsoup4")
        except ImportError as e:
            return self.dependency_error(e)

        try:
            html, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        # Парсер: lxml, если установлен, иначе встроенный html.parser.
        parser = "html.parser"
        try:
            self.require("lxml")
            parser = "lxml"
        except ImportError:
            pass

        try:
            from bs4 import Comment

            soup = bs4.BeautifulSoup(html, features=parser)
            for tag in soup(["script", "style", "noscript", "template"]):
                tag.decompose()
            for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
                c.extract()
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for blk in soup.find_all(_BLOCK_TAGS):
                blk.append("\n")

            raw_text = soup.get_text()
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.PARSE_ERROR, meta={"encoding": enc})

        lines = [unescape(ln).strip() for ln in raw_text.splitlines()]
        text = "\n".join(ln for ln in lines if ln)
        return ExtractionResult.success(text, meta={"encoding": enc}, warnings=warnings)
