"""
E-mail: .eml (RFC 822, стандартная библиотека) и .msg (Outlook, extract-msg).
"""

from __future__ import annotations

from typing import List

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class EmailExtractor(BaseExtractor):
    """Извлечение текста из писем .eml и .msg (заголовки + тело)."""

    MIME_TYPES = frozenset({"message/rfc822", "application/vnd.ms-outlook"})
    EXTENSIONS = (".eml", ".msg")

    def extract(self, src: FileSource) -> ExtractionResult:
        name = (src.filename or "").lower()
        if name.endswith(".msg") or src.mime == "application/vnd.ms-outlook":
            return self._extract_msg(src)
        return self._extract_eml(src)

    # --- .eml (стандартная библиотека) ---------------------------------------

    def _extract_eml(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение EML")
        from email import message_from_bytes
        from email.policy import default

        try:
            raw = self.read_bytes(src)
            msg = message_from_bytes(raw, policy=default)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        parts: List[str] = []
        for header in ("From", "To", "Cc", "Subject", "Date"):
            value = msg.get(header)
            if value:
                parts.append(f"{header}: {value}")

        try:
            body = msg.get_body(preferencelist=("plain", "html"))
            if body is not None:
                content = body.get_content()
                if body.get_content_subtype() == "html":
                    content = self._strip_html(content)
                if content and content.strip():
                    parts.append("")
                    parts.append(content.strip())
        except Exception as e:  # noqa: BLE001
            parts.append(f"[не удалось разобрать тело письма: {e}]")

        return ExtractionResult.success("\n".join(parts))

    # --- .msg (extract-msg) --------------------------------------------------

    def _extract_msg(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение MSG")
        try:
            extract_msg = self.require("extract_msg", pip_name="extract-msg")
        except ImportError as e:
            return self.dependency_error(e)

        import os
        import tempfile

        tmp = None
        try:
            if src.path:
                msg = extract_msg.Message(src.path)
            else:
                fd, tmp = tempfile.mkstemp(suffix=".msg")
                with os.fdopen(fd, "wb") as f:
                    f.write(src.data or b"")
                msg = extract_msg.Message(tmp)

            parts: List[str] = []
            for label, value in (
                ("From", msg.sender),
                ("To", msg.to),
                ("Cc", msg.cc),
                ("Subject", msg.subject),
                ("Date", msg.date),
            ):
                if value:
                    parts.append(f"{label}: {value}")
            if msg.body:
                parts.append("")
                parts.append(str(msg.body).strip())
            return ExtractionResult.success("\n".join(parts))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    # --- helpers -------------------------------------------------------------

    def _strip_html(self, html: str) -> str:
        try:
            bs4 = self.require("bs4", pip_name="beautifulsoup4")
        except ImportError:
            return html
        soup = bs4.BeautifulSoup(html, features="html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text().splitlines()]
        return "\n".join(ln for ln in lines if ln)
