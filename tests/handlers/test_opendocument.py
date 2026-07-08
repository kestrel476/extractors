"""Тесты OpenDocument-хендлера (odfpy)."""
from __future__ import annotations

import io

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.opendocument import OpenDocumentExtractor


def _make_odt():
    """Строит минимальный ODT в памяти (odfpy)."""
    from odf.opendocument import OpenDocumentText
    from odf.text import H, P

    doc = OpenDocumentText()
    doc.text.addElement(H(outlinelevel=1, text="Quarterly Report"))
    doc.text.addElement(P(text="Sales by region for the first quarter."))
    doc.text.addElement(P(text="Region North South West"))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── can_handle (без зависимостей) ────────────────────────────────────────────
def test_can_handle_mime():
    ex = OpenDocumentExtractor()
    assert ex.can_handle("application/vnd.oasis.opendocument.text", None)
    assert ex.can_handle("application/vnd.oasis.opendocument.spreadsheet", None)
    assert ex.can_handle("application/vnd.oasis.opendocument.presentation", None)


def test_can_handle_extension():
    ex = OpenDocumentExtractor()
    for name in ("d.odt", "d.ods", "d.odp", "d.odg", "d.odf"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "d.docx")


# ── extract ──────────────────────────────────────────────────────────────────
def test_extract_text():
    pytest.importorskip("odf")
    data = _make_odt()
    res = OpenDocumentExtractor().extract(FileSource(data=data, filename="d.odt"))
    assert res.ok
    assert "Quarterly Report" in res.text
    assert "Region" in res.text


def test_extract_markdown():
    pytest.importorskip("odf")
    data = _make_odt()
    res = OpenDocumentExtractor().extract_markdown(FileSource(data=data, filename="d.odt"))
    assert res.ok
    assert res.meta.get("format") == "markdown"
    assert "# Quarterly Report" in res.text


# ── ветки ошибок ─────────────────────────────────────────────────────────────
def test_dependency_missing(monkeypatch):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no odfpy")

    monkeypatch.setattr(OpenDocumentExtractor, "require", boom)
    res = OpenDocumentExtractor().extract(FileSource(data=b"\x00", filename="d.odt"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING
    res_md = OpenDocumentExtractor().extract_markdown(FileSource(data=b"\x00", filename="d.odt"))
    assert res_md.failed and res_md.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_read_error():
    pytest.importorskip("odf")
    res = OpenDocumentExtractor().extract(FileSource(data=b"not an odf", filename="bad.odt"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
