"""Тесты PDF-хендлера (PyMuPDF / fitz)."""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.pdf import PdfExtractor
from extractors.types import ExtractionStatus


def test_can_handle_mime():
    ex = PdfExtractor()
    assert ex.can_handle("application/pdf", None)
    assert ex.can_handle("application/x-pdf", None)


def test_can_handle_extension():
    ex = PdfExtractor()
    assert ex.can_handle(None, "doc.pdf")
    assert not ex.can_handle(None, "doc.txt")


def test_extract_text(pdf_bytes):
    pytest.importorskip("fitz")
    res = PdfExtractor().extract(FileSource(data=pdf_bytes, filename="r.pdf"))
    assert res.ok
    assert "Region" in res.text
    assert res.meta.get("pages") == "1"


def test_blank_pdf_no_text_layer(pdf_blank_bytes):
    pytest.importorskip("fitz")
    res = PdfExtractor().extract(FileSource(data=pdf_blank_bytes, filename="blank.pdf"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True


def test_blank_pdf_via_facade_ocr_stub(svc, pdf_blank_bytes):
    """Через фасад пустой PDF попадает в OCR-заглушку → NO_TEXT_LAYER."""
    pytest.importorskip("fitz")
    res = svc.extract(FileSource(data=pdf_blank_bytes, filename="blank.pdf"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True


def test_max_pages_truncation(pdf_bytes):
    fitz = pytest.importorskip("fitz")
    # двухстраничный PDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    doc.new_page()
    doc[-1].insert_text((72, 72), "second page text")
    data = doc.tobytes()
    doc.close()
    ex = PdfExtractor(max_pages=1)
    res = ex.extract(FileSource(data=data, filename="r.pdf"))
    assert res.ok
    assert any("Truncated" in w for w in res.warnings)


def test_markdown_via_facade(svc, pdf_bytes):
    pytest.importorskip("fitz")
    pytest.importorskip("markitdown")
    res = svc.extract(FileSource(data=pdf_bytes, filename="r.pdf"), markdown=True)
    assert res.ok
    assert "Region" in res.text


def test_dependency_missing(monkeypatch, pdf_bytes):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no fitz")

    monkeypatch.setattr(PdfExtractor, "require", boom)
    res = PdfExtractor().extract(FileSource(data=pdf_bytes, filename="r.pdf"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_read_error():
    pytest.importorskip("fitz")
    res = PdfExtractor().extract(FileSource(data=b"%PDF-not-really", filename="bad.pdf"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
