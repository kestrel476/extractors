"""Тесты DOCX-хендлера (python-docx)."""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.docx import DocxExtractor, docx_text


# ── can_handle (без опциональных зависимостей) ──────────────────────────────
def test_can_handle_mime():
    ex = DocxExtractor()
    assert ex.can_handle(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", None
    )
    assert ex.can_handle("application/vnd.ms-word.document.macroEnabled.12", None)


def test_can_handle_extension():
    ex = DocxExtractor()
    assert ex.can_handle(None, "report.docx")
    assert ex.can_handle(None, "REPORT.DOCM")
    assert ex.can_handle(None, "template.dotx")


def test_can_handle_negative():
    ex = DocxExtractor()
    assert not ex.can_handle(None, "report.pdf")
    assert not ex.can_handle("text/plain", None)
    assert not ex.can_handle(None, None)


# ── extract happy path ──────────────────────────────────────────────────────
def test_extract_text(docx_bytes):
    pytest.importorskip("docx")
    res = DocxExtractor().extract(FileSource(data=docx_bytes, filename="r.docx"))
    assert res.ok
    assert "Region" in res.text
    assert "Quarterly Report" in res.text


def test_docx_text_helper(docx_bytes):
    docx = pytest.importorskip("docx")
    from io import BytesIO

    doc = docx.Document(BytesIO(docx_bytes))
    text = docx_text(doc)
    assert "Region" in text and "North" in text


# ── markdown через фасад (markitdown) ───────────────────────────────────────
def test_markdown_via_facade(svc, docx_bytes):
    pytest.importorskip("docx")
    pytest.importorskip("markitdown")
    res = svc.extract(FileSource(data=docx_bytes, filename="r.docx"), markdown=True)
    assert res.ok
    assert "Region" in res.text
    assert res.meta.get("format") == "markdown"


# ── ветки ошибок ─────────────────────────────────────────────────────────────
def test_dependency_missing(monkeypatch, docx_bytes):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no docx")

    monkeypatch.setattr(DocxExtractor, "require", boom)
    res = DocxExtractor().extract(FileSource(data=docx_bytes, filename="r.docx"))
    assert res.failed
    assert res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_returns_read_error():
    pytest.importorskip("docx")
    res = DocxExtractor().extract(FileSource(data=b"not a docx", filename="bad.docx"))
    assert res.failed
    assert res.meta["code"] == ErrorCodes.READ_ERROR
