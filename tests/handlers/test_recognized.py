"""Тесты RecognizedUnsupportedExtractor (распознан, но не извлекаем)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus
from extractors.handlers.recognized import (
    RECOGNIZED_UNSUPPORTED,
    RecognizedUnsupportedExtractor,
)


@pytest.fixture
def ext():
    return RecognizedUnsupportedExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("application/onenote", None),
        ("application/x-indesign", None),
        ("application/x-apple-diskimage", None),
        (None, "notes.one"),
        (None, "layout.indd"),
        (None, "book.lit"),
        (None, "reader.lrf"),
        (None, "db.pdb"),
        (None, "image.dmg"),
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.pdf")])
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


def test_extract_returns_unsupported_with_reason(ext):
    res = ext.extract(source(b"whatever", "notes.one"))
    assert res.status is ExtractionStatus.UNSUPPORTED
    assert res.failed
    assert res.text is None
    assert res.error == RECOGNIZED_UNSUPPORTED[".one"]
    assert res.meta["code"] == "UNSUPPORTED_FORMAT"
    assert res.meta["ext"] == ".one"


@pytest.mark.parametrize("ext_name", list(RECOGNIZED_UNSUPPORTED))
def test_every_known_ext_has_reason(ext, ext_name):
    res = ext.extract(source(b"x", f"file{ext_name}"))
    assert res.status is ExtractionStatus.UNSUPPORTED
    assert res.error == RECOGNIZED_UNSUPPORTED[ext_name]


def test_svc_end_to_end(svc):
    res = svc.extract(source(b"x", "layout.indd"))
    assert res.status is ExtractionStatus.UNSUPPORTED
    assert res.meta["code"] == "UNSUPPORTED_FORMAT"
