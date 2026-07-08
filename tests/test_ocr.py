"""Тесты OCR-заглушки (OcrStub)."""
from __future__ import annotations

from extractors._logging import NullLogger
from extractors.errors import ErrorCodes
from extractors.ocr import OcrStub
from extractors.types import ExtractionStatus, FileSource


def test_recognize_returns_no_text_layer():
    res = OcrStub().recognize(FileSource(data=b"\x00\x01", filename="scan.png"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    assert res.text is None


def test_recognize_meta_and_warnings():
    src = FileSource(data=b"x", filename="scan.png", mime="image/png")
    res = OcrStub().recognize(src)
    assert res.meta["code"] == ErrorCodes.OCR_NOT_IMPLEMENTED
    assert res.meta["ocr"] == "stub"
    assert res.meta["mime"] == "image/png"
    assert res.meta["filename"] == "scan.png"
    assert res.warnings and "OCR" in res.warnings[0]


def test_recognize_with_custom_logger():
    logged = []

    class L(NullLogger):
        def log(self, event, message):
            logged.append((event, message))

    OcrStub(logger=L()).recognize(FileSource(data=b"x", filename="a.png"))
    assert logged and logged[0][0] == "DOC_EXTRACTION"


def test_default_logger_is_null():
    stub = OcrStub()
    assert isinstance(stub.logger, NullLogger)
