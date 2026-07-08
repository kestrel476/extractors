"""
PIM-форматы: iCalendar (.ics) и vCard (.vcf).

Парсятся как текст со складыванием «развёрнутых» строк (line folding по RFC 5545/6350).
Извлекаются значимые поля; технические свойства (UID, версии) опускаются.
"""

from __future__ import annotations

from typing import List

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource

# Свойства, несущие осмысленный текст.
_ICS_FIELDS = {"SUMMARY", "DESCRIPTION", "LOCATION", "COMMENT", "ATTENDEE", "ORGANIZER", "DTSTART", "DTEND"}
_VCF_FIELDS = {"FN", "N", "ORG", "TITLE", "EMAIL", "TEL", "ADR", "NOTE", "URL", "BDAY"}


def _unfold(text: str) -> List[str]:
    """Склеивает строки, продолженные через пробел/таб в начале (RFC line folding)."""
    out: List[str] = []
    for line in text.splitlines():
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


class IcsVcfExtractor(BaseExtractor):
    """Извлечение текста из календарей (.ics) и контактов (.vcf)."""

    MIME_TYPES = frozenset({"text/calendar", "text/vcard", "text/x-vcard"})
    EXTENSIONS = (".ics", ".vcf")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение ICS/VCF")
        try:
            text, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        is_vcf = src.ext == ".vcf" or src.mime in ("text/vcard", "text/x-vcard")
        fields = _VCF_FIELDS if is_vcf else _ICS_FIELDS

        parts: List[str] = []
        for line in _unfold(text):
            if ":" not in line:
                continue
            name, _, value = line.partition(":")
            prop = name.split(";", 1)[0].strip().upper()  # отбрасываем параметры (TYPE=...)
            if prop in fields and value.strip():
                parts.append(f"{prop}: {value.strip()}")
        return ExtractionResult.success("\n".join(parts), meta={"encoding": enc}, warnings=warnings)
