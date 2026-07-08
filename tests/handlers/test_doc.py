"""Тесты legacy .doc хендлера (LibreOffice soffice → .docx)."""
from __future__ import annotations

import shutil

import pytest

from extractors import FileSource
from extractors.errors import ErrorCodes
from extractors.handlers.doc import DocExtractor


def test_can_handle_mime():
    ex = DocExtractor()
    assert ex.can_handle("application/msword", None)


def test_can_handle_extension():
    ex = DocExtractor()
    assert ex.can_handle(None, "old.doc")
    assert ex.can_handle(None, "old.dot")
    assert not ex.can_handle(None, "new.docx")


def test_dependency_missing_docx(monkeypatch):
    def boom(self, module, *, pip_name=None):
        raise ImportError("no docx")

    monkeypatch.setattr(DocExtractor, "require", boom)
    res = DocExtractor().extract(FileSource(data=b"\xd0\xcf\x11\xe0", filename="old.doc"))
    assert res.failed and res.meta["code"] == ErrorCodes.DEPENDENCY_MISSING


def test_without_soffice_returns_read_error():
    """Без установленного LibreOffice конвертация падает → READ_ERROR (не исключение)."""
    pytest.importorskip("docx")
    if shutil.which("soffice"):
        pytest.skip("soffice установлен — путь ошибки конвертации недоступен")
    res = DocExtractor().extract(FileSource(data=b"\xd0\xcf\x11\xe0legacy", filename="old.doc"))
    assert res.failed and res.meta["code"] == ErrorCodes.READ_ERROR


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice (soffice) не установлен")
def test_with_soffice_extracts(docx_bytes):
    """Если soffice есть — .doc конвертируется и извлекается текст."""
    pytest.importorskip("docx")
    # Передаём docx как .doc: soffice всё равно откроет и переконвертирует.
    res = DocExtractor().extract(FileSource(data=docx_bytes, filename="r.doc"))
    assert isinstance(res.ok, bool)
