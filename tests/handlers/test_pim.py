"""Тесты IcsVcfExtractor (iCalendar .ics и vCard .vcf)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.pim import IcsVcfExtractor


@pytest.fixture
def ext():
    return IcsVcfExtractor()


ICS = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-1@example.com\r\n"
    "SUMMARY:Team Meeting\r\n"
    "DESCRIPTION:Discuss the quarterly\r\n"
    " roadmap and goals\r\n"  # folded continuation
    "LOCATION:Room 5\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
).encode()

VCF = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "FN:John Doe\r\n"
    "ORG:Acme Inc\r\n"
    "EMAIL;TYPE=work:john@example.com\r\n"
    "TEL:+1-555-0100\r\n"
    "END:VCARD\r\n"
).encode()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("text/calendar", None),
        ("text/vcard", None),
        ("text/x-vcard", None),
        (None, "a.ics"),
        (None, "a.vcf"),
    ],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.json")])
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


def test_ics_extract_fields(ext):
    res = ext.extract(source(ICS, "cal.ics"))
    assert res.status is ExtractionStatus.OK
    text = res.text
    assert "SUMMARY: Team Meeting" in text
    assert "LOCATION: Room 5" in text
    # развёрнутая (folded) строка склеена
    assert "DESCRIPTION: Discuss the quarterlyroadmap and goals" in text
    # технические поля опущены
    assert "UID" not in text
    assert "VERSION" not in text


def test_vcf_extract_fields(ext):
    res = ext.extract(source(VCF, "card.vcf"))
    assert res.status is ExtractionStatus.OK
    text = res.text
    assert "FN: John Doe" in text
    assert "ORG: Acme Inc" in text
    # параметры (TYPE=work) отброшены, само поле извлечено
    assert "EMAIL: john@example.com" in text
    assert "TEL: +1-555-0100" in text
    assert "VERSION" not in text


def test_vcf_detected_by_mime(ext):
    src = FileSource(data=VCF, filename="contact")
    src.mime = "text/vcard"
    res = ext.extract(src)
    assert "FN: John Doe" in res.text


def test_malformed_returns_empty_ok(ext):
    # строки без ':' пропускаются → пустой, но валидный результат
    res = ext.extract(source(b"no colon here\nanother line\n", "a.ics"))
    assert res.status is ExtractionStatus.OK
    assert res.text is None


def test_read_error(ext):
    res = ext.extract(FileSource(path="/nonexistent/x.ics"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "READ_ERROR"


def test_svc_end_to_end_ics(svc):
    res = svc.extract(source(ICS, "cal.ics"))
    assert res.status is ExtractionStatus.OK
    assert "SUMMARY: Team Meeting" in res.text
