"""
Базы данных и колоночные форматы данных.

- SQLite (.sqlite/.sqlite3/.db) — выгрузка текстовых значений из всех таблиц.
- Parquet/Feather/Arrow/ORC/Avro — чтение в DataFrame и сериализация в текст.
"""

from __future__ import annotations

import os
import tempfile
from typing import List, Optional

from ._markdown import df_to_md, md_section, md_table
from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class SqliteExtractor(BaseExtractor):
    """Извлечение текста из SQLite-базы (имена таблиц/столбцов + содержимое строк)."""

    MIME_TYPES = frozenset({"application/vnd.sqlite3", "application/x-sqlite3"})
    EXTENSIONS = (".sqlite", ".sqlite3", ".db")

    def __init__(self, max_rows_per_table: int = 1000, logger=None) -> None:
        super().__init__(logger=logger)
        self.max_rows_per_table = max_rows_per_table

    def can_handle(self, mime, filename):
        # .db слишком обобщённое — дополнительно проверяем сигнатуру при наличии данных.
        return super().can_handle(mime, filename)

    def _read_tables(self, src: FileSource):
        """Читает все таблицы БД. Возвращает ``(tables, warnings)``.

        ``tables`` — список ``(name, cols, rows)``; чтение выполняется в
        режиме read-only, временный файл (для источника-байтов) удаляется.
        """
        import sqlite3

        tmp = None
        tables_data = []
        warnings: List[str] = []
        try:
            if src.path:
                db_path = src.path
            else:
                fd, tmp = tempfile.mkstemp(suffix=".sqlite")
                with os.fdopen(fd, "wb") as f:
                    f.write(src.data or b"")
                db_path = tmp

            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            con.text_factory = lambda b: b.decode("utf-8", errors="replace")
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            names = [r[0] for r in cur.fetchall()]

            for table in names:
                try:
                    cur.execute(f'SELECT * FROM "{table}" LIMIT {self.max_rows_per_table + 1}')
                    cols = [d[0] for d in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    if len(rows) > self.max_rows_per_table:
                        rows = rows[: self.max_rows_per_table]
                        warnings.append(f"Truncated table '{table}' to {self.max_rows_per_table} rows")
                    tables_data.append((table, cols, rows))
                except sqlite3.Error as e:
                    warnings.append(f"table '{table}': {e}")
                    tables_data.append((table, [], []))
            con.close()
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        return tables_data, warnings

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение SQLite")
        try:
            tables_data, warnings = self._read_tables(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        parts: List[str] = []
        for table, cols, rows in tables_data:
            parts.append(f"# {table}")
            if cols:
                parts.append("\t".join(cols))
            for row in rows:
                parts.append("\t".join("" if v is None else str(v) for v in row))

        return ExtractionResult.success(
            "\n".join(parts), meta={"tables": str(len(tables_data))}, warnings=warnings
        )

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Рендерит каждую таблицу БД как Markdown-таблицу под заголовком ``## name``."""
        self.logger.log("DOC_EXTRACTION", "Markdown SQLite")
        try:
            tables_data, warnings = self._read_tables(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        parts: List[str] = []
        for table, cols, rows in tables_data:
            body = md_table(cols, rows) if cols else ""
            parts.append(md_section(table, body))

        return ExtractionResult.success(
            "\n\n".join(parts).strip(),
            meta={"tables": str(len(tables_data)), "format": "markdown"},
            warnings=warnings,
        )


class TabularDataExtractor(BaseExtractor):
    """Извлечение текста из колоночных форматов: Parquet, Feather/Arrow, ORC, Avro."""

    MIME_TYPES = frozenset(
        {
            "application/vnd.apache.parquet",
            "application/vnd.apache.arrow.file",
            "application/x-orc",
            "application/avro",
        }
    )
    EXTENSIONS = (".parquet", ".feather", ".arrow", ".orc", ".avro")

    def __init__(self, max_rows: int = 5000, logger=None) -> None:
        super().__init__(logger=logger)
        self.max_rows = max_rows

    def extract(self, src: FileSource) -> ExtractionResult:
        ext = src.ext
        self.logger.log("DOC_EXTRACTION", f"Извлечение колоночных данных ({ext})")
        if ext == ".avro":
            return self._extract_avro(src)
        return self._extract_via_pandas(src, ext)

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        ext = src.ext
        self.logger.log("DOC_EXTRACTION", f"Markdown колоночных данных ({ext})")
        if ext == ".avro":
            return self._extract_avro(src, as_markdown=True)
        return self._extract_via_pandas(src, ext, as_markdown=True)

    def _source(self, src: FileSource):
        import io

        return io.BytesIO(src.data) if src.data is not None else src.path

    def _extract_via_pandas(self, src: FileSource, ext: str, *, as_markdown: bool = False) -> ExtractionResult:
        try:
            pd = self.require("pandas", pip_name="pandas pyarrow")
        except ImportError as e:
            return self.dependency_error(e)
        try:
            source = self._source(src)
            if ext in (".feather", ".arrow"):
                df = pd.read_feather(source)
            elif ext == ".orc":
                df = pd.read_orc(source)
            else:  # .parquet
                df = pd.read_parquet(source)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        warnings = []
        if len(df) > self.max_rows:
            df = df.head(self.max_rows)
            warnings.append(f"Truncated to {self.max_rows} rows")
        if as_markdown:
            return ExtractionResult.success(
                df_to_md(df), meta={"rows": str(len(df)), "format": "markdown"}, warnings=warnings
            )
        return ExtractionResult.success(df.to_string(index=False), meta={"rows": str(len(df))}, warnings=warnings)

    def _extract_avro(self, src: FileSource, *, as_markdown: bool = False) -> ExtractionResult:
        try:
            fastavro = self.require("fastavro", pip_name="fastavro")
        except ImportError as e:
            return self.dependency_error(e)
        try:
            source = self._source(src)
            opener = open(source, "rb") if isinstance(source, str) else source
            reader = fastavro.reader(opener)
            records: List[dict] = []
            for i, record in enumerate(reader):
                if i >= self.max_rows:
                    break
                records.append(dict(record))
            if isinstance(source, str):
                opener.close()
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        if as_markdown:
            headers: List[str] = []
            for rec in records:
                for k in rec:
                    if k not in headers:
                        headers.append(k)
            rows = [[rec.get(h, "") for h in headers] for rec in records]
            return ExtractionResult.success(
                md_table(headers, rows), meta={"rows": str(len(records)), "format": "markdown"}
            )

        parts = ["\t".join(f"{k}={v}" for k, v in rec.items()) for rec in records]
        return ExtractionResult.success("\n".join(parts), meta={"rows": str(len(parts))})
