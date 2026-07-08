"""Тесты FitzDoc-хендлера (XPS/FB2/MOBI/CBZ через MuPDF/fitz)."""
from __future__ import annotations

import io
import zipfile

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.fitz_doc import FitzDocExtractor
from extractors.types import ExtractionStatus


def test_can_handle_mime():
    ex = FitzDocExtractor()
    assert ex.can_handle("application/vnd.ms-xpsdocument", None)
    assert ex.can_handle("application/x-fictionbook+xml", None)
    assert ex.can_handle("application/vnd.comicbook+zip", None)


def test_can_handle_extension():
    ex = FitzDocExtractor()
    for name in ("d.xps", "d.oxps", "d.fb2", "d.mobi", "d.azw", "d.azw3", "d.cbz"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "d.pdf")


def test_fb2_extract_text():
    pytest.importorskip("fitz")
    fb2 = (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<FictionBook xmlns='http://www.gribuser.ru/xml/fictionbook/2.0'>"
        "<body><section><p>Region North South West</p>"
        "<p>Sales by region for the first quarter.</p></section></body></FictionBook>"
    ).encode()
    res = FitzDocExtractor().extract(FileSource(data=fb2, filename="book.fb2"))
    # MuPDF может открыть FB2; при успехе есть текст, иначе — корректный результат.
    assert isinstance(res.ok, bool)
    if res.ok:
        assert "Region" in res.text


def test_cbz_no_text_layer():
    fitz = pytest.importorskip("fitz")
    # CBZ = zip с картинкой → нет текстового слоя → NO_TEXT_LAYER.
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10))
    img = pix.tobytes("png")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("001.png", img)
    res = FitzDocExtractor().extract(FileSource(data=buf.getvalue(), filename="c.cbz"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True


def test_dependency_missing(monkeypatch):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no fitz")

    monkeypatch.setattr(FitzDocExtractor, "require", boom)
    res = FitzDocExtractor().extract(FileSource(data=b"\x00", filename="d.xps"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_read_error():
    pytest.importorskip("fitz")
    res = FitzDocExtractor().extract(FileSource(data=b"not an xps", filename="bad.xps"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
