"""Тесты HtmlExtractor (видимый текст через BeautifulSoup)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.html import HtmlExtractor

pytest.importorskip("bs4")


@pytest.fixture
def ext():
    return HtmlExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("text/html", None),
        ("application/xhtml+xml", None),
        (None, "a.html"),
        (None, "a.htm"),
        (None, "a.xhtml"),
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.json")])
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


def test_extract_heading_paragraph_table(ext, html_bytes):
    res = ext.extract(source(html_bytes, "a.html"))
    assert res.status is ExtractionStatus.OK
    text = res.text
    assert "Quarterly Report" in text
    assert "Sales by region" in text
    # содержимое таблицы
    assert "Region" in text
    assert "North" in text
    assert "1200" in text


def test_script_and_style_removed(ext):
    html = (
        b"<html><head><style>.a{color:red}</style></head>"
        b"<body><p>Visible text</p>"
        b"<script>var secret = 1;</script></body></html>"
    )
    res = ext.extract(source(html, "a.html"))
    assert "Visible text" in res.text
    assert "secret" not in res.text
    assert "color:red" not in res.text


def test_entities_unescaped(ext):
    res = ext.extract(source(b"<html><body><p>a &amp; b &lt; c</p></body></html>", "a.html"))
    assert "a & b < c" in res.text


def test_dependency_missing(ext, html_bytes, monkeypatch):
    def _no_bs4(module, *args, **kwargs):
        raise ImportError(f"{module} недоступен")

    monkeypatch.setattr(ext, "require", _no_bs4)
    res = ext.extract(source(html_bytes, "a.html"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "DEPENDENCY_MISSING"


def test_read_error(ext):
    res = ext.extract(FileSource(path="/nonexistent/x.html"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "READ_ERROR"


def test_svc_end_to_end(svc, html_bytes):
    # HTML в text-режиме идёт через нативный HtmlExtractor.
    res = svc.extract(source(html_bytes, "a.html"))
    assert res.status is ExtractionStatus.OK
    assert "Quarterly Report" in res.text
