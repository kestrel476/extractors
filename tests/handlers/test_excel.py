"""Тесты Excel-хендлера (pandas + openpyxl)."""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.excel import ExcelExtractor


def test_can_handle_mime():
    ex = ExcelExtractor()
    assert ex.can_handle(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", None
    )
    assert ex.can_handle("application/vnd.ms-excel", None)


def test_can_handle_extension():
    ex = ExcelExtractor()
    for name in ("book.xlsx", "book.xls", "book.xlsm", "book.xlsb"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "book.csv")


def test_engine_selection():
    assert ExcelExtractor._engine_for(FileSource(data=b"x", filename="a.xlsb")) == "pyxlsb"
    assert ExcelExtractor._engine_for(FileSource(data=b"x", filename="a.xls")) == "xlrd"
    assert ExcelExtractor._engine_for(FileSource(data=b"x", filename="a.xlsx")) == "openpyxl"
    assert ExcelExtractor._engine_for(FileSource(data=b"x", filename="a.bin")) is None


# ── extract текстом ──────────────────────────────────────────────────────────
def test_extract_text(xlsx_bytes):
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    res = ExcelExtractor().extract(FileSource(data=xlsx_bytes, filename="r.xlsx"))
    assert res.ok
    assert "Sales" in res.text          # заголовок листа
    assert "Region" in res.text
    assert res.meta.get("sheets") == "1"


# ── extract_markdown (нативный df_to_md) ────────────────────────────────────
def test_extract_markdown_native(xlsx_bytes):
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    # .xlsm форсирует нативный md-путь хендлера (facade использовал бы markitdown)
    res = ExcelExtractor().extract_markdown(FileSource(data=xlsx_bytes, filename="r.xlsm"))
    assert res.ok
    assert res.meta.get("format") == "markdown"
    assert "## Sales" in res.text
    assert "| Region | Sales | Growth |" in res.text
    assert "| --- |" in res.text


def test_max_rows_truncation(xlsx_bytes):
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    ex = ExcelExtractor(max_rows_per_sheet=1)
    res = ex.extract(FileSource(data=xlsx_bytes, filename="r.xlsx"))
    assert res.ok
    assert any("Truncated" in w for w in res.warnings)


# ── ветки ошибок ─────────────────────────────────────────────────────────────
def test_dependency_missing(monkeypatch, xlsx_bytes):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no pandas")

    monkeypatch.setattr(ExcelExtractor, "require", boom)
    res = ExcelExtractor().extract(FileSource(data=xlsx_bytes, filename="r.xlsx"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING
    res_md = ExcelExtractor().extract_markdown(FileSource(data=xlsx_bytes, filename="r.xlsx"))
    assert res_md.failed and res_md.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_read_error():
    pytest.importorskip("pandas")
    pytest.importorskip("openpyxl")
    res = ExcelExtractor().extract(FileSource(data=b"garbage", filename="bad.xlsx"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
