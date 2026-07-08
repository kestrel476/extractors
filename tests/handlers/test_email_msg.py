"""Тесты e-mail хендлера (.eml = stdlib; .msg = extract_msg опционально)."""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.email_msg import EmailExtractor

EML = (
    b"From: alice@example.com\r\n"
    b"To: bob@example.com\r\n"
    b"Subject: Quarterly Report\r\n"
    b"Date: Mon, 1 Jan 2024 00:00:00 +0000\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n"
    b"\r\n"
    b"Sales by region for the first quarter.\r\n"
)

EML_HTML = (
    b"From: alice@example.com\r\n"
    b"Subject: HTML mail\r\n"
    b"Content-Type: text/html; charset=utf-8\r\n"
    b"\r\n"
    b"<html><body><p>Region North</p><script>x=1</script></body></html>\r\n"
)


def test_can_handle_mime():
    ex = EmailExtractor()
    assert ex.can_handle("message/rfc822", None)
    assert ex.can_handle("application/vnd.ms-outlook", None)


def test_can_handle_extension():
    ex = EmailExtractor()
    assert ex.can_handle(None, "mail.eml")
    assert ex.can_handle(None, "mail.msg")
    assert not ex.can_handle(None, "mail.txt")


# ── .eml (stdlib) ────────────────────────────────────────────────────────────
def test_eml_extract():
    res = EmailExtractor().extract(FileSource(data=EML, filename="m.eml"))
    assert res.ok
    assert "From: alice@example.com" in res.text
    assert "To: bob@example.com" in res.text
    assert "Subject: Quarterly Report" in res.text
    assert "Sales by region" in res.text


def test_eml_html_body_stripped():
    # _strip_html использует bs4, если доступен; иначе возвращает html как есть.
    res = EmailExtractor().extract(FileSource(data=EML_HTML, filename="m.eml"))
    assert res.ok
    assert "Region North" in res.text


def test_eml_corrupt_still_returns_result():
    # message_from_bytes крайне толерантен → результат остаётся OK (заголовков нет).
    res = EmailExtractor().extract(FileSource(data=b"\x00\x01garbage", filename="m.eml"))
    assert isinstance(res.ok, bool)  # ExtractionResult вернулся, исключения нет


# ── .msg (extract_msg опционально) ───────────────────────────────────────────
def test_msg_dependency_missing(monkeypatch):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no extract_msg")

    monkeypatch.setattr(EmailExtractor, "require", boom)
    res = EmailExtractor().extract(FileSource(data=b"\x00", filename="m.msg"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_msg_corrupt_read_error():
    pytest.importorskip("extract_msg")
    res = EmailExtractor().extract(FileSource(data=b"not a real msg", filename="m.msg"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
