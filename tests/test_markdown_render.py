"""
Тесты :class:`extractors.markdown_render.MarkItDownRenderer`.

Реальная конвертация проверяется на docx (``importorskip markitdown``);
ветки обработки результата/ошибок движка — детерминированно через фейковый
движок, подменяемый ``monkeypatch``.
"""
from __future__ import annotations

import pytest

from extractors import ExtractionStatus, FileSource
from extractors.markdown_render import MarkItDownRenderer

from conftest import source


# ── can_handle ──────────────────────────────────────────────────────────────
def test_can_handle_by_extension():
    r = MarkItDownRenderer()
    assert r.can_handle(None, "report.docx") is True
    assert r.can_handle(None, "book.EPUB") is True  # регистронезависимо
    assert r.can_handle(None, "notes.txt") is False


def test_can_handle_by_mime():
    r = MarkItDownRenderer()
    assert r.can_handle("application/pdf", None) is True
    assert r.can_handle(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", None
    ) is True
    assert r.can_handle("text/plain", None) is False


def test_can_handle_empty():
    r = MarkItDownRenderer()
    assert r.can_handle(None, None) is False
    assert r.can_handle(None, "") is False


# ── _read_path ──────────────────────────────────────────────────────────────
def test_read_path_reads_file(tmp_path):
    p = tmp_path / "blob.bin"
    p.write_bytes(b"\x00\x01\x02data")
    assert MarkItDownRenderer._read_path(str(p)) == b"\x00\x01\x02data"


def test_read_path_none_raises():
    with pytest.raises(ValueError):
        MarkItDownRenderer._read_path(None)


def test_read_path_empty_raises():
    with pytest.raises(ValueError):
        MarkItDownRenderer._read_path("")


# ── render: реальная конвертация ────────────────────────────────────────────
def test_render_docx(docx_bytes):
    pytest.importorskip("markitdown")
    r = MarkItDownRenderer()
    res = r.render(source(docx_bytes, "r.docx"))
    assert res is not None
    assert res.status == ExtractionStatus.OK
    assert res.meta["renderer"] == "markitdown"
    assert res.meta["format"] == "markdown"
    assert "Quarterly" in res.text


# ── render: подмена движка (детерминированные ветки) ────────────────────────
class _FakeResult:
    def __init__(self, markdown=None, text_content=None, title=None):
        self.markdown = markdown
        self.text_content = text_content
        self.title = title


class _FakeEngine:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    def convert_stream(self, stream, **kw):
        if self._exc is not None:
            raise self._exc
        return self._result


def test_render_engine_unavailable_returns_none(monkeypatch):
    r = MarkItDownRenderer()
    monkeypatch.setattr(r, "_engine", lambda: (_ for _ in ()).throw(ImportError("no markitdown")))
    assert r.render(source(b"data", "r.docx")) is None


def test_render_success_with_title(monkeypatch):
    pytest.importorskip("markitdown")
    r = MarkItDownRenderer()
    monkeypatch.setattr(r, "_engine", lambda: _FakeEngine(_FakeResult(markdown="# Hi", title="T")))
    res = r.render(source(b"data", "r.docx"))
    assert res.status == ExtractionStatus.OK
    assert res.text == "# Hi"
    assert res.meta["title"] == "T"


def test_render_text_content_fallback_field(monkeypatch):
    pytest.importorskip("markitdown")
    r = MarkItDownRenderer()
    monkeypatch.setattr(r, "_engine", lambda: _FakeEngine(_FakeResult(text_content="plain md")))
    res = r.render(source(b"data", "r.docx"))
    assert res.text == "plain md"


def test_render_empty_result_is_no_text_layer(monkeypatch):
    pytest.importorskip("markitdown")
    r = MarkItDownRenderer()
    monkeypatch.setattr(r, "_engine", lambda: _FakeEngine(_FakeResult(markdown="   ")))
    res = r.render(source(b"data", "scan.pdf"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    assert res.meta["renderer"] == "markitdown"


def test_render_missing_dependency_returns_none(monkeypatch):
    pytest.importorskip("markitdown")

    class MissingDependencyException(Exception):
        pass

    r = MarkItDownRenderer()
    monkeypatch.setattr(
        r, "_engine", lambda: _FakeEngine(exc=MissingDependencyException("no dep"))
    )
    assert r.render(source(b"data", "r.docx")) is None


def test_render_conversion_error_returns_none(monkeypatch):
    pytest.importorskip("markitdown")
    r = MarkItDownRenderer()
    monkeypatch.setattr(r, "_engine", lambda: _FakeEngine(exc=RuntimeError("bad file")))
    assert r.render(source(b"data", "r.docx")) is None


def test_render_reads_from_path(monkeypatch, tmp_path):
    pytest.importorskip("markitdown")
    p = tmp_path / "r.docx"
    p.write_bytes(b"raw-bytes")
    r = MarkItDownRenderer()
    monkeypatch.setattr(r, "_engine", lambda: _FakeEngine(_FakeResult(markdown="from path")))
    res = r.render(FileSource(path=str(p)))
    assert res.text == "from path"
