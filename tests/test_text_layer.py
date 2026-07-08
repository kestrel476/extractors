"""Тесты предпроверки текстового слоя (text_layer)."""
from __future__ import annotations

import pytest

from extractors.text_layer import (
    RASTER_IMAGE_EXTS,
    definitely_needs_ocr,
    is_image,
)


@pytest.mark.parametrize("ext", sorted(RASTER_IMAGE_EXTS))
def test_raster_extensions_are_images(ext):
    assert is_image(None, f"scan{ext}") is True
    assert definitely_needs_ocr(None, f"scan{ext}") is True


def test_image_mime_is_image():
    assert is_image("image/png", None) is True
    assert is_image("image/jpeg", "unknown") is True


@pytest.mark.parametrize("mime", ["image/svg+xml", "image/vnd.djvu", "image/vnd.adobe.photoshop"])
def test_textual_image_mimes_are_not_images(mime):
    # SVG/DjVu/PSD имеют текст → не должны сразу уходить в OCR.
    assert is_image(mime, None) is False
    assert definitely_needs_ocr(mime, None) is False


def test_non_image_is_false():
    assert is_image("application/pdf", "doc.pdf") is False
    assert is_image("text/plain", "notes.txt") is False
    assert definitely_needs_ocr("application/pdf", "doc.pdf") is False


def test_none_inputs():
    assert is_image(None, None) is False
    assert definitely_needs_ocr(None, None) is False


def test_extension_case_insensitive():
    assert is_image(None, "PHOTO.JPG") is True
