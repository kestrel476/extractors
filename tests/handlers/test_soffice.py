"""Тесты helper-а конвертации через LibreOffice (_soffice.convert)."""
from __future__ import annotations

import shutil

import pytest

from extractors import FileSource
from extractors.handlers._soffice import SofficeError, convert


def test_soffice_error_is_runtime_error():
    assert issubclass(SofficeError, RuntimeError)


def test_convert_without_soffice_raises():
    """Без установленного soffice convert() бросает SofficeError."""
    if shutil.which("soffice"):
        pytest.skip("soffice установлен — ветка отсутствия недоступна")
    src = FileSource(data=b"\xd0\xcf\x11\xe0legacy doc", filename="old.doc")
    with pytest.raises(SofficeError):
        convert(src, in_suffix=".doc", to_format="docx")


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice (soffice) не установлен")
def test_convert_with_soffice(docx_bytes):
    """Если soffice есть — конвертация docx→docx возвращает непустые байты."""
    src = FileSource(data=docx_bytes, filename="r.docx")
    out = convert(src, in_suffix=".docx", to_format="docx")
    assert isinstance(out, bytes) and len(out) > 0
