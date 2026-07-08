"""
XML: извлечение текстового содержимого всех элементов (и значений атрибутов).
"""

from __future__ import annotations

from typing import List
from xml.etree import ElementTree as ET

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class XmlExtractor(BaseExtractor):
    """Извлечение текста из XML."""

    MIME_TYPES = frozenset(
        {
            "application/xml",
            "text/xml",
            "image/svg+xml",
            "application/xliff+xml",
            "application/dita+xml",
            "application/docbook+xml",
            "application/wsdl+xml",
            "application/xhtml+xml",  # как fallback, если HTML-хендлера нет
        }
    )
    EXTENSIONS = (
        ".xml", ".svg", ".xliff", ".xlf", ".tmx", ".dita", ".ditamap",
        ".docbook", ".wsdl", ".xsd", ".plist", ".resx", ".resw", ".manifest",
        ".fodt", ".fods", ".fodp",
    )

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение XML")
        try:
            xml_str, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            return ExtractionResult.failure(f"Invalid XML: {e}", code=ErrorCodes.PARSE_ERROR, meta={"encoding": enc})

        parts: List[str] = []

        def walk(el) -> None:
            if el.text and el.text.strip():
                parts.append(el.text.strip())
            for child in el:
                walk(child)
            if el.tail and el.tail.strip():
                parts.append(el.tail.strip())

        walk(root)
        return ExtractionResult.success("\n".join(parts), meta={"encoding": enc}, warnings=warnings)
