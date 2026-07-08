"""Тесты ImageExtractor (нет текстового слоя → OCR)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus
from extractors.handlers.image import ImageExtractor


@pytest.fixture
def ext():
    return ImageExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("image/png", None),
        ("image/jpeg", None),
        ("image/tiff", None),
        ("image/webp", None),
        (None, "a.png"),
        (None, "a.jpg"),
        (None, "a.jpeg"),
        (None, "a.gif"),
        (None, "a.ico"),
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize(
    "mime,filename",
    [("text/plain", "a.txt"), (None, "a.txt"), ("application/pdf", "a.pdf")],
)
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


def test_extract_returns_no_text_layer(ext):
    src = source(b"\x89PNG\r\n\x1a\n", "a.png")
    src.mime = "image/png"
    res = ext.extract(src)
    assert res.status is ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    assert res.meta["code"] == "NO_TEXT_LAYER"
    assert res.meta["mime"] == "image/png"


def test_svc_routes_image_to_ocr(svc):
    # Фасад перехватывает изображение на предпроверке и уходит в OCR-заглушку.
    res = svc.extract(source(b"\x89PNG\r\n\x1a\n", "a.png"))
    assert res.status is ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    # заглушка OCR помечает результат своим кодом
    assert res.meta["code"] == "OCR_NOT_IMPLEMENTED"
    assert res.meta.get("ocr") == "stub"
