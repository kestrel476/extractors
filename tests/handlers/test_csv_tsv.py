"""Тесты CsvExtractor (CSV/TSV: сниффинг разделителя, заголовок, markdown)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.csv_tsv import CsvExtractor


@pytest.fixture
def ext():
    return CsvExtractor()


# --- can_handle -------------------------------------------------------------

@pytest.mark.parametrize(
    "mime,filename",
    [
        ("text/csv", None),
        ("text/tab-separated-values", None),
        ("application/csv", None),
        (None, "data.csv"),
        (None, "data.tsv"),
        (None, "DATA.CSV"),
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize(
    "mime,filename",
    [("text/plain", "a.txt"), (None, "a.txt"), ("application/json", "a.json")],
)
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


# --- extract (text mode) ----------------------------------------------------

def test_extract_csv_tab_joined(ext, csv_bytes):
    res = ext.extract(source(csv_bytes, "a.csv"))
    assert res.status is ExtractionStatus.OK
    assert "Region\tSales\tGrowth" in res.text
    assert "North\t1200\t12" in res.text
    # заголовок сохранён (вторая строка не «числовая») → 4 строки
    assert res.meta["rows"] == "4"


def test_extract_tsv_path(ext, tsv_bytes):
    res = ext.extract(source(tsv_bytes, "a.tsv"))
    assert res.status is ExtractionStatus.OK
    assert "Region\tSales\tGrowth" in res.text
    assert "South\t980\t-3" in res.text


def test_header_heuristic_drops_header_when_second_row_numeric(ext):
    # первая строка — текст, вторая — числа → заголовок отбрасывается
    data = b"x,y\n1,2\n3,4\n"
    res = ext.extract(source(data, "a.csv"))
    assert res.text == "1\t2\n3\t4"


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"a,b,c\nx,y,z\n", "a\tb\tc\nx\ty\tz"),      # запятая
        (b"a;b;c\nx;y;z\n", "a\tb\tc\nx\ty\tz"),      # точка с запятой
        (b"a\tb\tc\nx\ty\tz\n", "a\tb\tc\nx\ty\tz"),  # таб
        (b"a|b|c\nx|y|z\n", "a\tb\tc\nx\ty\tz"),      # вертикальная черта
    ],
)
def test_delimiter_sniffing(ext, data, expected):
    res = ext.extract(source(data, "a.csv"))
    assert res.text == expected


def test_max_rows_truncation_text(csv_bytes):
    ext = CsvExtractor(max_rows=2)
    res = ext.extract(source(csv_bytes, "a.csv"))
    assert res.status is ExtractionStatus.OK
    assert len(res.text.splitlines()) == 2
    assert any("Truncated to 2 rows" in w for w in res.warnings)


def test_empty_input_text(ext):
    res = ext.extract(source(b"", "a.csv"))
    assert res.status is ExtractionStatus.OK
    assert res.text is None
    assert res.meta["code"] == "EMPTY"


def test_extract_read_error(ext):
    res = ext.extract(FileSource(path="/nonexistent/x.csv"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "READ_ERROR"


# --- extract_markdown -------------------------------------------------------

def test_markdown_table(ext, csv_bytes):
    res = ext.extract_markdown(source(csv_bytes, "a.csv"))
    assert res.status is ExtractionStatus.OK
    assert res.meta["format"] == "markdown"
    lines = res.text.splitlines()
    assert lines[0] == "| Region | Sales | Growth |"
    assert lines[1] == "| --- | --- | --- |"
    assert "| North | 1200 | 12 |" in res.text
    # заголовок отделён от тела → 3 строки данных
    assert res.meta["rows"] == "3"


def test_markdown_max_rows(csv_bytes):
    ext = CsvExtractor(max_rows=1)
    res = ext.extract_markdown(source(csv_bytes, "a.csv"))
    assert res.meta["format"] == "markdown"
    assert res.meta["rows"] == "1"
    assert any("Truncated to 1 rows" in w for w in res.warnings)


def test_markdown_empty(ext):
    res = ext.extract_markdown(source(b"", "a.csv"))
    assert res.status is ExtractionStatus.OK
    assert res.text is None
    assert res.meta["format"] == "markdown"
    assert res.meta["rows"] == "0"


# --- end-to-end -------------------------------------------------------------

def test_svc_markdown_uses_native_table(svc, csv_bytes):
    res = svc.extract(source(csv_bytes, "a.csv"), markdown=True)
    assert res.status is ExtractionStatus.OK
    assert res.meta.get("format") == "markdown"
    assert "| Region | Sales | Growth |" in res.text
