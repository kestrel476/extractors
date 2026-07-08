"""
Excel: XLSX/XLSM (openpyxl) и устаревший XLS (xlrd) — через pandas.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Optional

from ._markdown import df_to_md, md_section
from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class ExcelExtractor(BaseExtractor):
    """Извлечение текста из Excel-книг (все листы)."""

    MIME_TYPES = frozenset(
        {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
            "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
        }
    )
    EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".xlsb")

    def __init__(self, max_rows_per_sheet: Optional[int] = None, logger=None) -> None:
        super().__init__(logger=logger)
        self.max_rows_per_sheet = max_rows_per_sheet

    @staticmethod
    def _engine_for(src: FileSource) -> Optional[str]:
        """Подбирает движок pandas по расширению/MIME (None → автоопределение)."""
        name = (src.filename or src.path or "").lower()
        if name.endswith(".xlsb") or (src.mime or "").endswith("binary.macroEnabled.12"):
            return "pyxlsb"
        if name.endswith(".xls") or src.mime == "application/vnd.ms-excel":
            return "xlrd"
        if name.endswith((".xlsx", ".xlsm")):
            return "openpyxl"
        return None

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение Excel")
        try:
            pd = self.require("pandas", pip_name="pandas openpyxl xlrd")
        except ImportError as e:
            return self.dependency_error(e)

        io_obj = BytesIO(src.data) if src.data is not None else src.path
        if io_obj is None:
            return ExtractionResult.failure("requires data or path", code=ErrorCodes.READ_ERROR)

        try:
            xls = pd.ExcelFile(io_obj, engine=self._engine_for(src))
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Не удалось открыть Excel: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        warnings: List[str] = []
        parts: List[str] = []
        try:
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                if self.max_rows_per_sheet is not None and len(df) > self.max_rows_per_sheet:
                    df = df.head(self.max_rows_per_sheet)
                    warnings.append(f"Truncated to {self.max_rows_per_sheet} rows on '{sheet}'")
                parts.append(f"# {sheet}")
                parts.append(df.to_string(index=False))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        return ExtractionResult.success(
            "\n".join(parts).strip(), meta={"sheets": str(len(xls.sheet_names))}, warnings=warnings
        )

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Рендерит книгу как набор Markdown-таблиц (по одной на лист)."""
        self.logger.log("DOC_EXTRACTION", "Markdown Excel")
        try:
            pd = self.require("pandas", pip_name="pandas openpyxl xlrd")
        except ImportError as e:
            return self.dependency_error(e)

        io_obj = BytesIO(src.data) if src.data is not None else src.path
        if io_obj is None:
            return ExtractionResult.failure("requires data or path", code=ErrorCodes.READ_ERROR)

        try:
            xls = pd.ExcelFile(io_obj, engine=self._engine_for(src))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        warnings: List[str] = []
        parts: List[str] = []
        try:
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                if self.max_rows_per_sheet is not None and len(df) > self.max_rows_per_sheet:
                    df = df.head(self.max_rows_per_sheet)
                    warnings.append(f"Truncated to {self.max_rows_per_sheet} rows on '{sheet}'")
                parts.append(md_section(str(sheet), df_to_md(df)))
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        return ExtractionResult.success(
            "\n\n".join(parts).strip(),
            meta={"sheets": str(len(xls.sheet_names)), "format": "markdown"},
            warnings=warnings,
        )
