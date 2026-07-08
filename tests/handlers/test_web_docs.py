"""Тесты web_docs: NotebookExtractor (.ipynb) и MhtmlExtractor (.mht/.mhtml)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.web_docs import MhtmlExtractor, NotebookExtractor


# ── Jupyter Notebook ─────────────────────────────────────────────────────────

@pytest.fixture
def nb():
    return NotebookExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [("application/x-ipynb+json", None), (None, "a.ipynb")],
)
def test_nb_can_handle_true(nb, mime, filename):
    assert nb.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.json")])
def test_nb_can_handle_false(nb, mime, filename):
    assert nb.can_handle(mime, filename) is False


def test_nb_extract_markdown_and_code_cells(nb, ipynb_bytes):
    res = nb.extract(source(ipynb_bytes, "a.ipynb"))
    assert res.status is ExtractionStatus.OK
    text = res.text
    assert "# [markdown]" in text
    assert "Quarterly Report" in text
    assert "# [code]" in text
    assert "print('hi')" in text


def test_nb_invalid_returns_failure(nb):
    res = nb.extract(source(b"not a notebook", "a.ipynb"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "PARSE_ERROR"


def test_nb_empty_cells(nb):
    res = nb.extract(source(b'{"cells": [], "nbformat": 4}', "a.ipynb"))
    assert res.status is ExtractionStatus.OK
    assert res.text is None


# ── MHTML ────────────────────────────────────────────────────────────────────

@pytest.fixture
def mh():
    return MhtmlExtractor()


def _mhtml(html: str) -> bytes:
    return (
        "From: <Saved by Blink>\r\n"
        "Subject: Test Page\r\n"
        "MIME-Version: 1.0\r\n"
        'Content-Type: multipart/related; boundary="----BOUND"\r\n'
        "\r\n"
        "------BOUND\r\n"
        'Content-Type: text/html; charset="utf-8"\r\n'
        "\r\n"
        f"{html}\r\n"
        "------BOUND--\r\n"
    ).encode()


def _mhtml_plain(text: str) -> bytes:
    return (
        "MIME-Version: 1.0\r\n"
        'Content-Type: multipart/related; boundary="----BOUND"\r\n'
        "\r\n"
        "------BOUND\r\n"
        'Content-Type: text/plain; charset="utf-8"\r\n'
        "\r\n"
        f"{text}\r\n"
        "------BOUND--\r\n"
    ).encode()


def test_mh_can_handle_by_extension(mh):
    assert mh.can_handle(None, "page.mht") is True
    assert mh.can_handle(None, "page.mhtml") is True
    assert mh.can_handle("multipart/related", None) is True


def test_mh_does_not_grab_eml(mh):
    # message/rfc822 без .mht-расширения принадлежит письмам, не MHTML
    assert mh.can_handle("message/rfc822", "mail.eml") is False


def test_mh_extract_html_part(mh):
    pytest.importorskip("bs4")
    html = "<html><body><h1>Hello MHT</h1><p>World body</p>" \
           "<script>evil()</script></body></html>"
    res = mh.extract(source(_mhtml(html), "page.mhtml"))
    assert res.status is ExtractionStatus.OK
    assert "Hello MHT" in res.text
    assert "World body" in res.text
    # script удалён при очистке HTML
    assert "evil" not in res.text


def test_mh_extract_plain_part(mh):
    res = mh.extract(source(_mhtml_plain("Just some plain body text"), "page.mhtml"))
    assert res.status is ExtractionStatus.OK
    assert "Just some plain body text" in res.text


def test_mh_svc_end_to_end(svc):
    pytest.importorskip("bs4")
    html = "<html><body><h1>End To End</h1></body></html>"
    res = svc.extract(source(_mhtml(html), "page.mht"))
    assert res.status is ExtractionStatus.OK
    assert "End To End" in res.text
