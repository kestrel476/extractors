"""
Тесты :class:`extractors.mime_detect.MagicMimeDetector`.

Детекция libmagic (``python-magic``) необязательна: если библиотека
недоступна, работает резерв по расширению. Приоритет libmagic/расширения
проверяется детерминированно через подмену модуля ``magic``.
"""
from __future__ import annotations

import pytest

from extractors import FileSource
from extractors import mime_detect
from extractors.mime_detect import EXT_TO_MIME, MagicMimeDetector, _sniff_ooxml

from conftest import source


COMMON = [
    (".pdf", "application/pdf"),
    (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    (".csv", "text/csv"),
    (".html", "text/html"),
    (".json", "application/json"),
    (".png", "image/png"),
    (".txt", "text/plain"),
    (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
]


@pytest.mark.parametrize("ext,expected", COMMON)
def test_detect_by_extension(ext, expected):
    d = MagicMimeDetector()
    # Данные не соответствуют формату — libmagic (если есть) вернёт общий тип,
    # тогда авторитетно расширение; для двоичных типов результат совпадает.
    assert d.detect(source(b"placeholder", f"file{ext}")) == expected


@pytest.mark.parametrize("ext,expected", COMMON)
def test_by_ext_map(ext, expected):
    assert MagicMimeDetector._by_ext(source(b"x", f"a{ext}")) == expected


def test_by_ext_unknown_returns_none():
    assert MagicMimeDetector._by_ext(source(b"x", "a.zzzz")) is None


def test_by_ext_no_name_returns_none():
    assert MagicMimeDetector._by_ext(FileSource(data=b"x")) is None


def test_by_ext_double_extensions():
    assert MagicMimeDetector._by_ext(source(b"x", "a.tar.gz")) == "application/gzip"
    assert MagicMimeDetector._by_ext(source(b"x", "a.tar.bz2")) == "application/x-bzip2"
    assert MagicMimeDetector._by_ext(source(b"x", "a.tar.xz")) == "application/x-xz"


# ── OOXML-дизамбигуация по содержимому ──────────────────────────────────────
def test_sniff_ooxml_helper():
    assert _sniff_ooxml(b"...word/document.xml...") == EXT_TO_MIME[".docx"]
    assert _sniff_ooxml(b"...xl/workbook.xml...") == EXT_TO_MIME[".xlsx"]
    assert _sniff_ooxml(b"...ppt/presentation.xml...") == EXT_TO_MIME[".pptx"]
    assert _sniff_ooxml(b"plain zip content") is None


def test_ooxml_sniff_wins_over_wrong_name(docx_bytes):
    d = MagicMimeDetector()
    # Даже с «неправильным» именем содержимое docx распознаётся по сигнатуре.
    res = d.detect(FileSource(data=docx_bytes, filename="mystery.bin"))
    assert res == EXT_TO_MIME[".docx"]


def test_ooxml_sniff_xlsx(xlsx_bytes):
    d = MagicMimeDetector()
    assert d.detect(FileSource(data=xlsx_bytes, filename="s.xlsx")) == EXT_TO_MIME[".xlsx"]


# ── Подмена magic: приоритеты libmagic vs расширение ────────────────────────
class _FakeMagicMod:
    """Мини-имитация модуля python-magic."""

    def __init__(self, ret, raise_exc=False):
        self._ret = ret
        self._raise = raise_exc

    def Magic(self, mime=True):
        ret, raise_exc = self._ret, self._raise

        class _M:
            def from_buffer(self, data):
                if raise_exc:
                    raise RuntimeError("libmagic failed")
                return ret

            def from_file(self, path):
                if raise_exc:
                    raise RuntimeError("libmagic failed")
                return ret

        return _M()


def test_missing_magic_extension_fallback(monkeypatch):
    monkeypatch.setattr(mime_detect, "magic", None)
    d = MagicMimeDetector()
    # Содержимое произвольное — при отсутствии libmagic решает расширение.
    assert d.detect(source(b"random-bytes", "doc.pdf")) == "application/pdf"


def test_magic_generic_type_defers_to_extension(monkeypatch):
    # libmagic отдаёт общий application/zip → авторитетно расширение (.docx).
    monkeypatch.setattr(mime_detect, "magic", _FakeMagicMod("application/zip"))
    d = MagicMimeDetector()
    res = d.detect(FileSource(data=b"no-ooxml-marker", filename="a.docx"))
    assert res == EXT_TO_MIME[".docx"]


def test_magic_specific_type_wins(monkeypatch):
    # Конкретный тип от libmagic возвращается как есть (расширения нет).
    monkeypatch.setattr(mime_detect, "magic", _FakeMagicMod("text/x-python"))
    d = MagicMimeDetector()
    res = d.detect(FileSource(data=b"print('hi')", filename="script-noext"))
    assert res == "text/x-python"


def test_magic_exception_falls_back_to_extension(monkeypatch):
    monkeypatch.setattr(mime_detect, "magic", _FakeMagicMod(None, raise_exc=True))
    d = MagicMimeDetector()
    assert d.detect(source(b"x", "a.pdf")) == "application/pdf"


def test_detect_no_name_no_magic_returns_none(monkeypatch):
    monkeypatch.setattr(mime_detect, "magic", None)
    d = MagicMimeDetector()
    assert d.detect(FileSource(data=b"random")) is None
