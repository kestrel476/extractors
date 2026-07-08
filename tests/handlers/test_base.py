"""Тесты BaseExtractor (общая логика хендлеров)."""
from __future__ import annotations

from io import BytesIO

import pytest

from extractors.errors import ErrorCodes
from extractors.handlers.base import BaseExtractor
from extractors.types import ExtractionResult, FileSource


class _Concrete(BaseExtractor):
    MIME_TYPES = frozenset({"application/x-demo"})
    EXTENSIONS = (".demo",)

    def extract(self, src: FileSource) -> ExtractionResult:  # pragma: no cover - не используется
        return ExtractionResult.success("ok")


@pytest.fixture
def ex():
    return _Concrete()


# ── can_handle ─────────────────────────────────────────────────────────────
def test_can_handle_by_mime(ex):
    assert ex.can_handle("application/x-demo", None) is True


def test_can_handle_by_extension(ex):
    assert ex.can_handle(None, "file.demo") is True
    assert ex.can_handle(None, "FILE.DEMO") is True


def test_can_handle_false(ex):
    assert ex.can_handle("text/plain", "file.txt") is False
    assert ex.can_handle(None, None) is False


# ── read_bytes ─────────────────────────────────────────────────────────────
def test_read_bytes_from_data(ex):
    assert ex.read_bytes(FileSource(data=b"hello", filename="a.demo")) == b"hello"


def test_read_bytes_from_path(ex, tmp_path):
    p = tmp_path / "a.demo"
    p.write_bytes(b"disk")
    assert ex.read_bytes(FileSource(path=str(p))) == b"disk"


def test_read_bytes_raises_without_source(ex):
    src = FileSource.model_construct(path=None, data=None, filename=None, mime=None)
    with pytest.raises(ValueError):
        ex.read_bytes(src)


# ── decode_bytes / read_text ─────────────────────────────────────────────
def test_decode_utf8(ex):
    text, enc, warns = ex.decode_bytes("привет".encode("utf-8"))
    assert text == "привет"
    assert enc == "utf-8"
    assert warns == []


def test_decode_utf8_bom(ex):
    text, enc, _ = ex.decode_bytes("﻿hi".encode("utf-8"))
    assert text == "hi"
    assert enc == "utf-8"


def test_decode_fallback_for_invalid_utf8(ex):
    # Байты, не валидные в UTF-8 → charset-normalizer/latin-1: без исключения,
    # с определённой кодировкой и предупреждением (конкретный текст зависит от детектора).
    text, enc, warns = ex.decode_bytes(b"caf\xe9")
    assert isinstance(text, str) and text
    assert enc  # какая-то кодировка определена
    assert warns  # об этом предупреждено


def test_decode_pure_latin1_fallback(ex, monkeypatch):
    # Форсируем ветку latin-1: делаем вид, что charset-normalizer «не смог».
    import charset_normalizer

    monkeypatch.setattr(
        charset_normalizer, "from_bytes",
        lambda raw: type("E", (), {"best": lambda self: None})(),
    )
    text, enc, warns = ex.decode_bytes(b"\xff\xfe\x00bad")
    assert enc == "latin-1"
    assert any("latin-1" in w for w in warns)


def test_read_text(ex):
    text, enc, _ = ex.read_text(FileSource(data=b"plain", filename="a.demo"))
    assert text == "plain"


# ── require / dependency_error ─────────────────────────────────────────────
def test_require_returns_module(ex):
    mod = ex.require("os")
    import os
    assert mod is os


def test_require_missing_raises_importerror(ex):
    with pytest.raises(ImportError) as exc:
        ex.require("nonexistent_module_xyz_123", pip_name="somepkg")
    assert "somepkg" in str(exc.value)


def test_dependency_error(ex):
    res = ex.dependency_error(ImportError("boom"))
    assert res.failed
    assert res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


# ── binary_source ─────────────────────────────────────────────────────────
def test_binary_source_data_returns_bytesio(ex):
    obj = ex.binary_source(FileSource(data=b"x", filename="a.demo"))
    assert isinstance(obj, BytesIO)
    assert obj.read() == b"x"


def test_binary_source_path_returns_str(ex, tmp_path):
    p = tmp_path / "a.demo"
    p.write_bytes(b"x")
    assert ex.binary_source(FileSource(path=str(p))) == str(p)


def test_binary_source_raises_without_source(ex):
    src = FileSource.model_construct(path=None, data=None, filename=None, mime=None)
    with pytest.raises(ValueError):
        ex.binary_source(src)


# ── extract_markdown default ─────────────────────────────────────────────
def test_extract_markdown_default_none(ex):
    assert ex.extract_markdown(FileSource(data=b"x", filename="a.demo")) is None


# ── defaults ─────────────────────────────────────────────────────────────
def test_default_logger_and_empty_class_attrs():
    from extractors._logging import NullLogger

    class Bare(BaseExtractor):
        def extract(self, src):  # pragma: no cover
            return ExtractionResult.success("x")

    b = Bare()
    assert isinstance(b.logger, NullLogger)
    assert b.MIME_TYPES == frozenset()
    assert b.EXTENSIONS == ()
