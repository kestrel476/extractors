"""Тесты PlainTextExtractor (простой текст, код, конфиги, субтитры)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.plain_text import PlainTextExtractor


@pytest.fixture
def ext():
    return PlainTextExtractor()


# --- can_handle -------------------------------------------------------------

@pytest.mark.parametrize(
    "mime,filename",
    [
        ("text/plain", None),
        ("text/markdown", None),
        ("text/x-python", None),
        (None, "notes.txt"),
        (None, "README.md"),
        (None, "script.py"),
        (None, "app.log"),
        (None, "subtitles.srt"),
        (None, "STYLE.CFG"),  # регистр не важен
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("image/png", "a.png"),
        ("application/pdf", "a.pdf"),
        (None, "a.png"),
        (None, ""),
        (None, None),
    ],
)
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


# --- extract ----------------------------------------------------------------

def test_extract_happy(ext):
    res = ext.extract(source(b"hello world", "a.txt"))
    assert res.status is ExtractionStatus.OK
    assert res.ok
    assert res.text == "hello world"
    assert res.meta["encoding"] == "utf-8"


def test_extract_strips_surrounding_whitespace(ext):
    res = ext.extract(source(b"  \n hi there \n  ", "a.txt"))
    assert res.text == "hi there"


def test_extract_utf8_bom(ext):
    res = ext.extract(source(b"\xef\xbb\xbfcaf\xc3\xa9", "a.txt"))
    assert res.text == "café"
    assert res.meta["encoding"] == "utf-8"


def test_extract_non_utf8_falls_back_with_warning(ext):
    # Байты, невалидные как UTF-8 (latin-1 'é' = 0xE9).
    res = ext.extract(source(b"caf\xe9 lait", "a.txt"))
    assert res.status is ExtractionStatus.OK
    assert res.text is not None and "caf" in res.text
    # Была применена мягкая деградация кодировки → предупреждение.
    assert res.warnings


# --- extract_markdown (наследует базовый None → фасад откатывается на текст) --

def test_extract_markdown_returns_none(ext):
    assert ext.extract_markdown(source(b"x", "a.txt")) is None


# --- error branch -----------------------------------------------------------

def test_extract_read_error_returns_failure(ext):
    res = ext.extract(FileSource(path="/nonexistent/does_not_exist.txt"))
    assert res.status is ExtractionStatus.ERROR
    assert res.failed
    assert res.meta["code"] == "READ_ERROR"


# --- end-to-end через фасад -------------------------------------------------

def test_svc_extract_text(svc):
    res = svc.extract(source(b"plain body", "a.txt"))
    assert res.status is ExtractionStatus.OK
    assert res.text == "plain body"


def test_svc_markdown_passthrough_format_text(svc):
    res = svc.extract(source(b"plain body", "a.txt"), markdown=True)
    assert res.status is ExtractionStatus.OK
    assert res.text == "plain body"
    assert res.meta.get("format") == "text"
