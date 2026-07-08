"""Тесты ExtractorRegistry."""
from __future__ import annotations

from extractors.interfaces import Extractor
from extractors.registry import ExtractorRegistry
from extractors.types import ExtractionResult, FileSource


class _Fake(Extractor):
    def __init__(self, tag, exts=(), mimes=()):
        self.tag = tag
        self._exts = exts
        self._mimes = mimes

    def can_handle(self, mime, filename):
        name = (filename or "").lower()
        return (mime in self._mimes) or any(name.endswith(e) for e in self._exts)

    def extract(self, src: FileSource) -> ExtractionResult:
        return ExtractionResult.success(self.tag)


def test_register_is_chainable_and_counts():
    reg = ExtractorRegistry()
    assert len(reg) == 0
    ret = reg.register(_Fake("a", exts=(".a",)))
    assert ret is reg  # возвращает self для цепочки
    reg.register(_Fake("b", exts=(".b",)))
    assert len(reg) == 2


def test_pick_returns_first_match_in_order():
    reg = ExtractorRegistry()
    reg.register(_Fake("first", exts=(".x",)))
    reg.register(_Fake("second", exts=(".x",)))  # тоже подходит, но позже
    picked = reg.pick(None, "file.x")
    assert picked.tag == "first"


def test_pick_by_mime():
    reg = ExtractorRegistry()
    reg.register(_Fake("pdf", mimes=("application/pdf",)))
    assert reg.pick("application/pdf", None).tag == "pdf"


def test_pick_none_when_no_match():
    reg = ExtractorRegistry()
    reg.register(_Fake("a", exts=(".a",)))
    assert reg.pick("text/plain", "file.zzz") is None


def test_pick_empty_registry():
    assert ExtractorRegistry().pick("application/pdf", "x.pdf") is None
