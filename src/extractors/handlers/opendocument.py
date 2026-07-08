"""
OpenDocument: ODT (текст), ODS (таблицы), ODP (презентации) через odfpy.
"""

from __future__ import annotations

from io import BytesIO
from typing import List

from ._markdown import md_section, md_table
from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class OpenDocumentExtractor(BaseExtractor):
    """Извлечение текста из форматов OpenDocument (.odt/.ods/.odp)."""

    MIME_TYPES = frozenset(
        {
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.oasis.opendocument.presentation",
            "application/vnd.oasis.opendocument.graphics",
            "application/vnd.oasis.opendocument.formula",
        }
    )
    EXTENSIONS = (".odt", ".ods", ".odp", ".odg", ".odf")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение OpenDocument")
        try:
            teletype = self.require("odf.teletype", pip_name="odfpy")
            text_ns = self.require("odf.text", pip_name="odfpy")
            opendocument = self.require("odf.opendocument", pip_name="odfpy")
        except ImportError as e:
            return self.dependency_error(e)

        try:
            source = BytesIO(src.data) if src.data is not None else src.path
            doc = opendocument.load(source)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Не удалось открыть ODF: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            parts: List[str] = []
            # Параграфы покрывают текст ODT/ODP; ячейки ODS также представлены параграфами.
            for para in doc.getElementsByType(text_ns.P):
                t = teletype.extractText(para)
                if t and t.strip():
                    parts.append(t.strip())
            for heading in doc.getElementsByType(text_ns.H):
                t = teletype.extractText(heading)
                if t and t.strip():
                    parts.append(t.strip())
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        return ExtractionResult.success("\n".join(parts))

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Рендерит ODF в Markdown: заголовки, абзацы и настоящие md-таблицы."""
        self.logger.log("DOC_EXTRACTION", "Markdown OpenDocument")
        try:
            teletype = self.require("odf.teletype", pip_name="odfpy")
            opendocument = self.require("odf.opendocument", pip_name="odfpy")
        except ImportError as e:
            return self.dependency_error(e)

        try:
            source = BytesIO(src.data) if src.data is not None else src.path
            doc = opendocument.load(source)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Не удалось открыть ODF: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        try:
            parts: List[str] = []
            # Обходим тело документа в порядке следования, чтобы сохранить
            # структуру (заголовки/абзацы/таблицы) для подачи в LLM.
            self._walk(doc.body, teletype, parts)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        md = "\n\n".join(p for p in parts if p.strip()).strip()
        return ExtractionResult.success(md, meta={"format": "markdown"})

    # --- Обход дерева ODF -----------------------------------------------------

    def _walk(self, node, teletype, parts: List[str]) -> None:
        """Рекурсивно обходит узлы ODF, наполняя ``parts`` блоками Markdown."""
        for child in getattr(node, "childNodes", []):
            tag = getattr(child, "tagName", "")
            if tag == "text:h":
                level = self._heading_level(child)
                text = teletype.extractText(child).strip()
                if text:
                    parts.append(f"{'#' * level} {text}")
            elif tag == "text:p":
                text = teletype.extractText(child).strip()
                if text:
                    parts.append(text)
            elif tag == "table:table":
                parts.append(self._render_table(child, teletype))
            else:
                # Списки, секции, фреймы, страницы презентаций и т. п. — вглубь.
                self._walk(child, teletype, parts)

    @staticmethod
    def _heading_level(node) -> int:
        try:
            level = int(node.getAttribute("outlinelevel"))
            return max(1, min(level, 6))
        except (TypeError, ValueError):
            return 1

    def _render_table(self, table, teletype) -> str:
        """Собирает Markdown-таблицу из ``table:table`` (первая строка — заголовок)."""
        rows: List[List[str]] = []
        for tr in table.childNodes:
            if getattr(tr, "tagName", "") != "table:table-row":
                continue
            cells: List[str] = []
            for tc in tr.childNodes:
                ctag = getattr(tc, "tagName", "")
                if ctag not in ("table:table-cell", "table:covered-table-cell"):
                    continue
                text = teletype.extractText(tc).strip()
                # Ячейка может повторяться (number-columns-repeated).
                repeat = 1
                try:
                    repeat = int(tc.getAttribute("numbercolumnsrepeated") or 1)
                except (TypeError, ValueError):
                    repeat = 1
                repeat = min(repeat, 1024)  # защита от гигантских «пустых» диапазонов
                cells.extend([text] * repeat)
            # Обрезаем хвостовые пустые ячейки от repeated-диапазонов.
            while cells and cells[-1] == "":
                cells.pop()
            if cells:
                rows.append(cells)

        name = ""
        try:
            name = table.getAttribute("name") or ""
        except (TypeError, ValueError):
            name = ""
        if not rows:
            return md_section(name, "")

        table_md = md_table(rows[0], rows[1:])
        # Имя таблицы полезно для листов ODS; для ODT-таблиц оно обычно "TableN" —
        # добавляем как заголовок только если оно осмысленно короткое.
        return md_section(name, table_md) if name else table_md

