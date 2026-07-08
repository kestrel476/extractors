"""Тесты XmlExtractor (извлечение текста элементов stdlib ElementTree)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.xml import XmlExtractor


@pytest.fixture
def ext():
    return XmlExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("application/xml", None),
        ("text/xml", None),
        ("image/svg+xml", None),
        ("application/xhtml+xml", None),
        (None, "a.xml"),
        (None, "a.svg"),
        (None, "a.xliff"),
        (None, "a.plist"),
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.json")])
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


def test_extract_element_text(ext, xml_bytes):
    res = ext.extract(source(xml_bytes, "a.xml"))
    assert res.status is ExtractionStatus.OK
    text = res.text
    assert "Quarterly Report" in text
    assert "North" in text
    assert "1200" in text


def test_extract_nested_and_tail(ext):
    data = b"<root><a>Alpha</a>tail-text<b>Beta</b></root>"
    res = ext.extract(source(data, "a.xml"))
    lines = res.text.splitlines()
    assert "Alpha" in lines
    assert "Beta" in lines
    assert "tail-text" in lines


def test_extract_svg_text(ext):
    svg = (
        b"<svg xmlns='http://www.w3.org/2000/svg'>"
        b"<text>Hello SVG</text></svg>"
    )
    res = ext.extract(source(svg, "a.svg"))
    assert res.status is ExtractionStatus.OK
    assert "Hello SVG" in res.text


def test_invalid_xml_returns_failure(ext):
    res = ext.extract(source(b"<root><unclosed></root>", "a.xml"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "PARSE_ERROR"
    assert "Invalid XML" in res.error


def test_read_error(ext):
    res = ext.extract(FileSource(path="/nonexistent/x.xml"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "READ_ERROR"


def test_svc_markdown_passthrough_format_text(svc, xml_bytes):
    res = svc.extract(source(xml_bytes, "a.xml"), markdown=True)
    assert res.status is ExtractionStatus.OK
    assert res.meta.get("format") == "text"
    assert "Quarterly Report" in res.text
