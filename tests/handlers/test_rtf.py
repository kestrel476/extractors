"""Тесты RtfExtractor (текст и markdown-таблицы через striprtf)."""
from __future__ import annotations

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.rtf import RtfExtractor

pytest.importorskip("striprtf")


@pytest.fixture
def ext():
    return RtfExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [("application/rtf", None), ("text/rtf", None), (None, "a.rtf")],
)
def test_can_handle_true(ext, mime, filename):
    assert ext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.docx")])
def test_can_handle_false(ext, mime, filename):
    assert ext.can_handle(mime, filename) is False


def test_extract_text(ext, rtf_bytes):
    res = ext.extract(source(rtf_bytes, "a.rtf"))
    assert res.status is ExtractionStatus.OK
    assert "Quarterly Report" in res.text
    assert "Sales by region" in res.text


def test_extract_markdown_table(ext, rtf_bytes):
    res = ext.extract_markdown(source(rtf_bytes, "a.rtf"))
    assert res.status is ExtractionStatus.OK
    assert res.meta["format"] == "markdown"
    text = res.text
    # striprtf pipe-строки собраны в markdown-таблицу
    assert "| Region | Sales | Growth |" in text
    assert "| --- | --- | --- |" in text
    assert "| North | 1200 | 12 |" in text
    # обычные абзацы сохранены
    assert "Quarterly Report" in text


def test_dependency_missing_extract(ext, rtf_bytes, monkeypatch):
    def _no_dep(*args, **kwargs):
        raise ImportError("striprtf недоступен")

    monkeypatch.setattr(ext, "require", _no_dep)
    res = ext.extract(source(rtf_bytes, "a.rtf"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "DEPENDENCY_MISSING"


def test_dependency_missing_markdown(ext, rtf_bytes, monkeypatch):
    def _no_dep(*args, **kwargs):
        raise ImportError("striprtf недоступен")

    monkeypatch.setattr(ext, "require", _no_dep)
    res = ext.extract_markdown(source(rtf_bytes, "a.rtf"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "DEPENDENCY_MISSING"


def test_svc_markdown_end_to_end(svc, rtf_bytes):
    res = svc.extract(source(rtf_bytes, "a.rtf"), markdown=True)
    assert res.status is ExtractionStatus.OK
    assert res.meta.get("format") == "markdown"
    assert "| Region | Sales | Growth |" in res.text
