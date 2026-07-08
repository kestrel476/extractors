"""
RTF: извлечение чистого текста через striprtf.
"""

from __future__ import annotations

from typing import List, Tuple

from ._markdown import md_table
from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class RtfExtractor(BaseExtractor):
    """Извлечение текста из .rtf."""

    MIME_TYPES = frozenset({"application/rtf", "text/rtf"})
    EXTENSIONS = (".rtf",)

    def _to_text(self, src: FileSource) -> Tuple[str, str, List[str]]:
        """Возвращает ``(текст, кодировка, предупреждения)`` через striprtf.

        striprtf сохраняет табличную структуру: ячейки строки разделяются ``|``
        с завершающим ``|``, каждая строка таблицы — на своей строке.
        """
        striprtf = self.require("striprtf.striprtf", pip_name="striprtf")
        rtf_str, enc, warnings = self.read_text(src)
        text = (striprtf.rtf_to_text(rtf_str) or "").replace("\r\n", "\n").strip()
        return text, enc, warnings

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение RTF")
        try:
            text, enc, warnings = self._to_text(src)
        except ImportError as e:
            return self.dependency_error(e)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.PARSE_ERROR)

        return ExtractionResult.success(text, meta={"encoding": enc}, warnings=warnings)

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Рендерит RTF в Markdown: строки-таблицы striprtf → md-таблицы."""
        self.logger.log("DOC_EXTRACTION", "Markdown RTF")
        try:
            text, enc, warnings = self._to_text(src)
        except ImportError as e:
            return self.dependency_error(e)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.PARSE_ERROR)

        return ExtractionResult.success(
            self._to_markdown(text), meta={"encoding": enc, "format": "markdown"}, warnings=warnings
        )

    @staticmethod
    def _to_markdown(text: str) -> str:
        """Преобразует вывод striprtf в Markdown, собирая таблицы из pipe-строк.

        Строка таблицы у striprtf оканчивается на ``|`` (завершающий разделитель
        ячейки); идущие подряд такие строки объединяются в одну Markdown-таблицу,
        первая строка блока считается заголовком. Остальные строки — абзацы.
        """
        blocks: List[str] = []
        table_rows: List[List[str]] = []
        para_lines: List[str] = []

        def flush_table() -> None:
            if table_rows:
                blocks.append(md_table(table_rows[0], table_rows[1:]))
                table_rows.clear()

        def flush_para() -> None:
            if para_lines:
                blocks.append("\n".join(para_lines))
                para_lines.clear()

        for line in text.split("\n"):
            s = line.rstrip()
            if s.endswith("|"):
                flush_para()
                cells = s.split("|")
                if cells and cells[-1] == "":  # убираем артефакт завершающего разделителя
                    cells.pop()
                table_rows.append(cells)
            elif s.strip():
                flush_table()
                para_lines.append(s)
            else:  # пустая строка — граница абзаца
                flush_table()
                flush_para()

        flush_table()
        flush_para()
        return "\n\n".join(b for b in blocks if b.strip()).strip()
