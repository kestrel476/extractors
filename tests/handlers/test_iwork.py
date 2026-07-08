"""Тесты iWork-хендлера (.key/.pages/.numbers — zip с PDF-предпросмотром)."""
from __future__ import annotations

import io
import zipfile

import pytest

from extractors import FileSource, build_default_extractor
from extractors.errors import ErrorCodes
from extractors.handlers.iwork import IWorkExtractor
from extractors.types import ExtractionStatus


def test_can_handle_mime():
    ex = IWorkExtractor()
    assert ex.can_handle("application/x-iwork-keynote-sffkey", None)
    assert ex.can_handle("application/x-iwork-pages-sffpages", None)
    assert ex.can_handle("application/x-iwork-numbers-sffnumbers", None)


def test_can_handle_extension():
    ex = IWorkExtractor()
    for name in ("d.key", "d.pages", "d.numbers"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "d.pptx")


def _make_iwork_with_preview():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Quarterly Report")
    page.insert_text((72, 100), "Sales by region: Region North South West")
    pdf_bytes = doc.tobytes()
    doc.close()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("preview.pdf", pdf_bytes)
        z.writestr("index.iwa", b"binary")
    return buf.getvalue()


def test_extract_with_preview(svc):
    pytest.importorskip("fitz")
    data = _make_iwork_with_preview()
    ex = IWorkExtractor(facade=svc)
    res = ex.extract(FileSource(data=data, filename="d.key"))
    assert res.ok
    assert "Region" in res.text
    assert res.meta.get("source") == "iwork-preview"


def test_no_preview_no_text_layer(svc):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("index.iwa", b"binary")
    ex = IWorkExtractor(facade=svc)
    res = ex.extract(FileSource(data=buf.getvalue(), filename="d.key"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True


def test_no_facade_read_error():
    data_buf = io.BytesIO()
    with zipfile.ZipFile(data_buf, "w") as z:
        z.writestr("preview.pdf", b"%PDF-1.4 fake")
    ex = IWorkExtractor(facade=None)
    res = ex.extract(FileSource(data=data_buf.getvalue(), filename="d.key"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR


def test_corrupt_zip_read_error(svc):
    ex = IWorkExtractor(facade=svc)
    res = ex.extract(FileSource(data=b"not a zip", filename="d.key"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
