"""
CSV / TSV: разбор табличных текстовых файлов с автоопределением разделителя.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import List, Optional

from ._markdown import md_table
from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


def _is_number(x: str) -> bool:
    x = (x or "").strip().replace(",", ".")
    if not x:
        return False
    try:
        float(x)
        return True
    except ValueError:
        return False


class CsvExtractor(BaseExtractor):
    """Извлечение текста из CSV/TSV. Сохраняет табличную структуру через табы."""

    MIME_TYPES = frozenset({"text/csv", "text/tab-separated-values", "application/csv"})
    EXTENSIONS = (".csv", ".tsv")

    def __init__(self, max_rows: Optional[int] = None, logger=None) -> None:
        super().__init__(logger=logger)
        self.max_rows = max_rows

    def _make_reader(self, text: str, filename: Optional[str]):
        """Подбирает разделитель: сначала по сигнатуре, затем по имени файла."""
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            return csv.reader(StringIO(text), dialect=dialect)
        except csv.Error:
            pass
        # Резерв: .tsv → таб, иначе ищем разделитель в первой строке.
        if (filename or "").lower().endswith(".tsv"):
            return csv.reader(StringIO(text), delimiter="\t")
        first_line = sample.splitlines()[0] if sample.splitlines() else sample
        for delim in ("\t", ";", "|", ","):
            if delim in first_line:
                return csv.reader(StringIO(text), delimiter=delim)
        return csv.reader(StringIO(text))

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение CSV/TSV")
        try:
            text, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            rows = list(self._make_reader(text, src.filename))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.PARSE_ERROR, meta={"encoding": enc})

        # Эвристика заголовка: текст в первой строке, числа во второй.
        start = 0
        if len(rows) >= 2:
            first_has_text = any((c or "").strip() and not _is_number(c) for c in rows[0])
            second_mostly_numbers = all((c == "" or _is_number(c)) for c in rows[1])
            if first_has_text and second_mostly_numbers:
                start = 1

        lines: List[str] = []
        for i, row in enumerate(rows[start:]):
            if self.max_rows is not None and i >= self.max_rows:
                warnings = list(warnings) + [f"Truncated to {self.max_rows} rows"]
                break
            lines.append("\t".join("" if c is None else str(c) for c in row))

        return ExtractionResult.success(
            "\n".join(lines), meta={"encoding": enc, "rows": str(len(lines))}, warnings=warnings
        )

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Рендерит CSV/TSV как Markdown-таблицу (первая строка — заголовок)."""
        self.logger.log("DOC_EXTRACTION", "Markdown CSV/TSV")
        try:
            text, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            rows = list(self._make_reader(text, src.filename))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.PARSE_ERROR, meta={"encoding": enc})

        if not rows:
            return ExtractionResult.success("", meta={"encoding": enc, "format": "markdown", "rows": "0"})

        warnings = list(warnings)
        body = rows[1:]
        if self.max_rows is not None and len(body) > self.max_rows:
            body = body[: self.max_rows]
            warnings.append(f"Truncated to {self.max_rows} rows")

        table = md_table(rows[0], body)
        return ExtractionResult.success(
            table,
            meta={"encoding": enc, "format": "markdown", "rows": str(len(body))},
            warnings=warnings,
        )
