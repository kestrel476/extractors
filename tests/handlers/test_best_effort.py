"""Тесты «best-effort» хендлеров: DjVu, PostScript/EPS/AI, PSD."""
from __future__ import annotations

import shutil

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.best_effort import DjvuExtractor, PostScriptExtractor, PsdExtractor
from extractors.types import ExtractionStatus


# ── DjVu ─────────────────────────────────────────────────────────────────────
def test_djvu_can_handle():
    ex = DjvuExtractor()
    assert ex.can_handle("image/vnd.djvu", None)
    assert ex.can_handle("image/x-djvu", None)
    assert ex.can_handle(None, "s.djvu")
    assert ex.can_handle(None, "s.djv")
    assert not ex.can_handle(None, "s.pdf")


def test_djvu_without_tool_no_text_layer():
    """Без djvutxt → NO_TEXT_LAYER (кандидат на OCR), не исключение."""
    if shutil.which("djvutxt"):
        pytest.skip("djvutxt установлен")
    res = DjvuExtractor().extract(FileSource(data=b"AT&TFORM djvu", filename="s.djvu"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True


# ── PostScript / EPS / AI ────────────────────────────────────────────────────
def test_ps_can_handle():
    ex = PostScriptExtractor()
    assert ex.can_handle("application/postscript", None)
    assert ex.can_handle("application/eps", None)
    for name in ("d.ps", "d.eps", "d.ai"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "d.pdf")


def test_ps_without_ghostscript_dependency_missing():
    """Без Ghostscript → DEPENDENCY_MISSING."""
    if shutil.which("gs"):
        pytest.skip("Ghostscript установлен")
    res = PostScriptExtractor().extract(FileSource(data=b"%!PS-Adobe-3.0\n", filename="d.ps"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


# ── PSD ──────────────────────────────────────────────────────────────────────
def test_psd_can_handle():
    ex = PsdExtractor()
    assert ex.can_handle("image/vnd.adobe.photoshop", None)
    assert ex.can_handle("application/x-photoshop", None)
    assert ex.can_handle(None, "a.psd")
    assert not ex.can_handle(None, "a.png")


def test_psd_dependency_missing(monkeypatch):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no psd_tools")

    monkeypatch.setattr(PsdExtractor, "require", boom)
    res = PsdExtractor().extract(FileSource(data=b"8BPS", filename="a.psd"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_psd_corrupt_read_error():
    pytest.importorskip("psd_tools")
    res = PsdExtractor().extract(FileSource(data=b"not a psd", filename="bad.psd"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR
