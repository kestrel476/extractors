"""Тесты PowerPoint-хендлера (python-pptx)."""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.powerpoint import PptxExtractor, _pptx_text


def test_can_handle_mime():
    ex = PptxExtractor()
    assert ex.can_handle(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", None
    )
    assert ex.can_handle("application/vnd.ms-powerpoint", None)


def test_can_handle_extension():
    ex = PptxExtractor()
    for name in ("deck.pptx", "deck.pptm", "deck.ppt"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "deck.key")


def test_extract_text(pptx_bytes):
    pytest.importorskip("pptx")
    res = PptxExtractor().extract(FileSource(data=pptx_bytes, filename="d.pptx"))
    assert res.ok
    assert "Quarterly Report" in res.text
    assert "Region" in res.text


def test_pptx_text_helper(pptx_bytes):
    pptx = pytest.importorskip("pptx")
    from io import BytesIO

    prs = pptx.Presentation(BytesIO(pptx_bytes))
    text = _pptx_text(prs)
    assert "Region" in text


def test_markdown_via_facade(svc, pptx_bytes):
    pytest.importorskip("pptx")
    pytest.importorskip("markitdown")
    res = svc.extract(FileSource(data=pptx_bytes, filename="d.pptx"), markdown=True)
    assert res.ok
    assert "Region" in res.text
    assert res.meta.get("format") == "markdown"


def test_dependency_missing(monkeypatch, pptx_bytes):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no pptx")

    monkeypatch.setattr(PptxExtractor, "require", boom)
    res = PptxExtractor().extract(FileSource(data=pptx_bytes, filename="d.pptx"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_read_error():
    pytest.importorskip("pptx")
    res = PptxExtractor().extract(FileSource(data=b"not pptx", filename="bad.pptx"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR


def test_legacy_ppt_without_soffice(monkeypatch):
    """.ppt без LibreOffice → READ_ERROR (SofficeError перехвачен)."""
    pytest.importorskip("pptx")
    res = PptxExtractor().extract(FileSource(data=b"\xd0\xcf\x11\xe0legacy", filename="old.ppt"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
