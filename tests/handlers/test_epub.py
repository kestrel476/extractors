"""Тесты EPUB-хендлера (ebooklib предпочтительно, bs4-fallback из ZIP)."""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.epub import EpubExtractor, _html_to_text


def test_can_handle_mime():
    ex = EpubExtractor()
    assert ex.can_handle("application/epub+zip", None)


def test_can_handle_extension():
    ex = EpubExtractor()
    assert ex.can_handle(None, "book.epub")
    assert not ex.can_handle(None, "book.pdf")


def test_extract_text(epub_bytes):
    # bs4 нужен всегда; ebooklib опционален — с байтами (без path) идёт fallback-ZIP.
    pytest.importorskip("bs4")
    res = EpubExtractor().extract(FileSource(data=epub_bytes, filename="b.epub"))
    assert res.ok
    assert "Quarterly Report" in res.text
    assert "Region" in res.text


def test_html_to_text_helper():
    bs4 = pytest.importorskip("bs4")
    html = "<html><body><h1>Title</h1><script>x=1</script><p>Body</p></body></html>"
    text = _html_to_text(bs4, html)
    assert "Title" in text and "Body" in text
    assert "x=1" not in text  # script вырезан


def test_fallback_zip_directly(epub_bytes):
    bs4 = pytest.importorskip("bs4")
    ex = EpubExtractor()
    res = ex._fallback_zip(bs4, FileSource(data=epub_bytes, filename="b.epub"))
    assert res.ok and "Region" in res.text


def test_dependency_missing_bs4(monkeypatch, epub_bytes):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no bs4")

    monkeypatch.setattr(EpubExtractor, "require", boom)
    res = EpubExtractor().extract(FileSource(data=epub_bytes, filename="b.epub"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_corrupt_bytes_read_error():
    pytest.importorskip("bs4")
    # не-ZIP содержимое → fallback падает при открытии ZIP → READ_ERROR
    res = EpubExtractor().extract(FileSource(data=b"not a zip", filename="bad.epub"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
