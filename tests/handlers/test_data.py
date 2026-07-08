"""Тесты хендлеров данных: SQLite (stdlib) и колоночные форматы."""
from __future__ import annotations

import io

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.data import SqliteExtractor, TabularDataExtractor


# ── SQLite (stdlib — без skip) ──────────────────────────────────────────────
def test_sqlite_can_handle():
    ex = SqliteExtractor()
    assert ex.can_handle("application/vnd.sqlite3", None)
    assert ex.can_handle("application/x-sqlite3", None)
    for name in ("db.sqlite", "db.sqlite3", "db.db"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "db.parquet")


def test_sqlite_extract_text(sqlite_path):
    res = SqliteExtractor().extract(FileSource(path=sqlite_path))
    assert res.ok
    assert "# sales" in res.text
    assert "# totals" in res.text
    assert "North" in res.text
    assert res.meta.get("tables") == "2"


def test_sqlite_extract_markdown(sqlite_path):
    res = SqliteExtractor().extract_markdown(FileSource(path=sqlite_path))
    assert res.ok
    assert res.meta.get("format") == "markdown"
    assert "## sales" in res.text
    assert "| region | amount | growth |" in res.text
    assert "| --- |" in res.text


def test_sqlite_from_bytes(sqlite_path):
    with open(sqlite_path, "rb") as f:
        data = f.read()
    res = SqliteExtractor().extract(FileSource(data=data, filename="r.sqlite"))
    assert res.ok and "North" in res.text


def test_sqlite_row_truncation(sqlite_path):
    ex = SqliteExtractor(max_rows_per_table=1)
    res = ex.extract(FileSource(path=sqlite_path))
    assert res.ok
    assert any("Truncated" in w for w in res.warnings)


def test_sqlite_bad_data_read_error():
    res = SqliteExtractor().extract(FileSource(data=b"not a sqlite db", filename="bad.sqlite"))
    # sqlite открывает файл лениво; чтение таблиц падает → READ_ERROR
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR


# ── Колоночные форматы ───────────────────────────────────────────────────────
def test_tabular_can_handle():
    ex = TabularDataExtractor()
    assert ex.can_handle("application/vnd.apache.parquet", None)
    assert ex.can_handle("application/avro", None)
    for name in ("d.parquet", "d.feather", "d.arrow", "d.orc", "d.avro"):
        assert ex.can_handle(None, name)


def test_parquet_extract_text(parquet_bytes):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    res = TabularDataExtractor().extract(FileSource(data=parquet_bytes, filename="d.parquet"))
    assert res.ok
    assert "North" in res.text and "Region" in res.text


def test_parquet_extract_markdown(parquet_bytes):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    res = TabularDataExtractor().extract_markdown(FileSource(data=parquet_bytes, filename="d.parquet"))
    assert res.ok
    assert res.meta.get("format") == "markdown"
    assert "| Region | Sales | Growth |" in res.text
    assert "| --- |" in res.text


def test_parquet_row_truncation(parquet_bytes):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    ex = TabularDataExtractor(max_rows=1)
    res = ex.extract(FileSource(data=parquet_bytes, filename="d.parquet"))
    assert res.ok
    assert any("Truncated" in w for w in res.warnings)


def test_parquet_dependency_missing(monkeypatch, parquet_bytes):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no pandas")

    monkeypatch.setattr(TabularDataExtractor, "require", boom)
    res = TabularDataExtractor().extract(FileSource(data=parquet_bytes, filename="d.parquet"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_parquet_corrupt_read_error():
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    res = TabularDataExtractor().extract(FileSource(data=b"garbage", filename="d.parquet"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR


# ── Avro ─────────────────────────────────────────────────────────────────────
def _make_avro_bytes(fastavro):
    schema = {
        "type": "record",
        "name": "Row",
        "fields": [{"name": "region", "type": "string"}, {"name": "sales", "type": "int"}],
    }
    buf = io.BytesIO()
    fastavro.writer(buf, schema, [{"region": "North", "sales": 1200}, {"region": "South", "sales": 980}])
    return buf.getvalue()


def test_avro_extract_text():
    fastavro = pytest.importorskip("fastavro")
    data = _make_avro_bytes(fastavro)
    res = TabularDataExtractor().extract(FileSource(data=data, filename="d.avro"))
    assert res.ok and "North" in res.text


def test_avro_extract_markdown():
    fastavro = pytest.importorskip("fastavro")
    data = _make_avro_bytes(fastavro)
    res = TabularDataExtractor().extract_markdown(FileSource(data=data, filename="d.avro"))
    assert res.ok
    assert res.meta.get("format") == "markdown"
    assert "| region | sales |" in res.text


def test_avro_dependency_missing(monkeypatch):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no fastavro")

    monkeypatch.setattr(TabularDataExtractor, "require", boom)
    res = TabularDataExtractor().extract(FileSource(data=b"\x00", filename="d.avro"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING
