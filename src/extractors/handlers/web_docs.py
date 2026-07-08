"""
Jupyter Notebook (.ipynb) и MHTML web-архивы (.mht/.mhtml).
"""

from __future__ import annotations

import json
from typing import List

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class NotebookExtractor(BaseExtractor):
    """Извлечение текста из Jupyter Notebook (.ipynb): markdown + код + текстовый вывод."""

    MIME_TYPES = frozenset({"application/x-ipynb+json"})
    EXTENSIONS = (".ipynb",)

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение Jupyter Notebook")
        try:
            text, enc, warnings = self.read_text(src)
            nb = json.loads(text)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(f"Invalid notebook: {e}", code=ErrorCodes.PARSE_ERROR)

        parts: List[str] = []
        for cell in nb.get("cells", []):
            ctype = cell.get("cell_type")
            source = cell.get("source", [])
            if isinstance(source, list):
                source = "".join(source)
            if not source or not source.strip():
                continue
            prefix = {"markdown": "# [markdown]", "code": "# [code]", "raw": "# [raw]"}.get(ctype, "")
            parts.append(f"{prefix}\n{source.strip()}" if prefix else source.strip())
        return ExtractionResult.success("\n\n".join(parts), meta={"encoding": enc}, warnings=warnings)


class MhtmlExtractor(BaseExtractor):
    """Извлечение текста из MHTML web-архива (.mht/.mhtml).

    MHTML — это MIME-документ (multipart/related), внутри которого HTML и ресурсы.
    Берём HTML-часть и извлекаем из неё видимый текст.
    """

    MIME_TYPES = frozenset({"multipart/related", "message/rfc822"})
    EXTENSIONS = (".mht", ".mhtml")

    def can_handle(self, mime, filename):
        # message/rfc822 принадлежит и письмам — ловим MHTML только по расширению
        # или по multipart/related, чтобы не перехватывать .eml.
        name = (filename or "").lower()
        if name.endswith((".mht", ".mhtml")):
            return True
        return mime == "multipart/related"

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение MHTML")
        from email import message_from_bytes
        from email.policy import default

        try:
            raw = self.read_bytes(src)
            msg = message_from_bytes(raw, policy=default)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        html_parts: List[str] = []
        text_parts: List[str] = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                try:
                    html_parts.append(part.get_content())
                except Exception:  # noqa: BLE001
                    pass
            elif ctype == "text/plain":
                try:
                    text_parts.append(part.get_content())
                except Exception:  # noqa: BLE001
                    pass

        if html_parts:
            return ExtractionResult.success(self._strip_html("\n".join(html_parts)))
        if text_parts:
            return ExtractionResult.success("\n".join(p.strip() for p in text_parts))
        return ExtractionResult.success(None, meta={"code": ErrorCodes.EMPTY})

    def _strip_html(self, html: str) -> str:
        try:
            bs4 = self.require("bs4", pip_name="beautifulsoup4")
        except ImportError:
            return html
        soup = bs4.BeautifulSoup(html, features="html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text().splitlines()]
        return "\n".join(ln for ln in lines if ln)
