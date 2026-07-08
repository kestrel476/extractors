"""Тесты моделей данных: FileSource, ExtractionResult, ExtractionStatus."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from extractors.errors import ErrorCodes
from extractors.types import ExtractionResult, ExtractionStatus, FileSource


# ── ExtractionStatus ────────────────────────────────────────────────────────
def test_status_enum_values():
    assert ExtractionStatus.OK == "ok"
    assert ExtractionStatus.NO_TEXT_LAYER == "no_text_layer"
    assert ExtractionStatus.UNSUPPORTED == "unsupported"
    assert ExtractionStatus.ERROR == "error"
    # str-enum: значение равно строке
    assert ExtractionStatus.OK.value == "ok"
    assert isinstance(ExtractionStatus.OK, str)


# ── FileSource: нормализация data ─────────────────────────────────────────────
def test_filesource_data_from_bytes():
    fs = FileSource(data=b"hello")
    assert fs.data == b"hello"


def test_filesource_data_from_bytearray():
    fs = FileSource(data=bytearray(b"abc"))
    assert fs.data == b"abc"
    assert isinstance(fs.data, bytes)


def test_filesource_data_from_memoryview():
    fs = FileSource(data=memoryview(b"xyz"))
    assert fs.data == b"xyz"
    assert isinstance(fs.data, bytes)


def test_filesource_data_from_str():
    fs = FileSource(data="héllo")
    assert fs.data == "héllo".encode("utf-8")


def test_filesource_data_none_requires_path():
    # data=None напрямую → должно упасть на model_validator (нет path)
    with pytest.raises(ValidationError):
        FileSource(data=None)


def test_filesource_data_unsupported_type():
    # Валидатор data кидает TypeError (pydantic v2 не оборачивает его в ValidationError).
    with pytest.raises((TypeError, ValidationError)):
        FileSource(data=12345)


# ── FileSource: валидация и автозаполнение ───────────────────────────────────
def test_filesource_requires_path_or_data():
    with pytest.raises(ValidationError) as ei:
        FileSource()
    assert "at least one of 'path' or 'data'" in str(ei.value)


def test_filesource_path_only_is_valid():
    fs = FileSource(path="/tmp/report.pdf")
    assert fs.data is None
    assert fs.path == "/tmp/report.pdf"


def test_filesource_filename_autofill_from_path():
    fs = FileSource(path="/some/dir/report.pdf")
    assert fs.filename == "report.pdf"


def test_filesource_filename_not_overwritten():
    fs = FileSource(path="/some/dir/report.pdf", filename="custom.txt")
    assert fs.filename == "custom.txt"


def test_filesource_data_only_no_filename_autofill():
    fs = FileSource(data=b"x")
    assert fs.filename is None


# ── FileSource: ext property ─────────────────────────────────────────────────
def test_ext_from_filename():
    assert FileSource(data=b"x", filename="Doc.PDF").ext == ".pdf"


def test_ext_from_path_when_no_filename():
    # filename autofilled from path, so ext derives from it
    assert FileSource(path="/a/b/Sheet.XLSX").ext == ".xlsx"


def test_ext_empty_when_no_extension():
    assert FileSource(data=b"x", filename="noext").ext == ""


def test_ext_empty_when_data_only_no_name():
    assert FileSource(data=b"x").ext == ""


# ── FileSource: extra="forbid" ───────────────────────────────────────────────
def test_filesource_forbids_extra_fields():
    with pytest.raises(ValidationError):
        FileSource(data=b"x", bogus="nope")


def test_filesource_strips_whitespace():
    fs = FileSource(data=b"x", filename="  name.txt  ")
    assert fs.filename == "name.txt"


# ── ExtractionResult: success ────────────────────────────────────────────────
def test_success_with_text():
    r = ExtractionResult.success("hello")
    assert r.text == "hello"
    assert r.status == ExtractionStatus.OK
    assert r.ok is True
    assert r.failed is False
    assert "code" not in r.meta


def test_success_with_meta_and_warnings():
    r = ExtractionResult.success("t", meta={"pages": "3"}, warnings=["w"])
    assert r.meta["pages"] == "3"
    assert r.warnings == ["w"]
    assert r.status == ExtractionStatus.OK


def test_success_empty_text_becomes_empty_code():
    r = ExtractionResult.success("")
    assert r.text is None
    assert r.status == ExtractionStatus.OK
    assert r.meta["code"] == ErrorCodes.EMPTY
    assert r.ok is True


def test_success_none_text_becomes_empty_code():
    r = ExtractionResult.success(None)
    assert r.text is None
    assert r.meta["code"] == "EMPTY"
    assert r.status == ExtractionStatus.OK


def test_success_empty_does_not_override_existing_code():
    r = ExtractionResult.success("", meta={"code": "CUSTOM"})
    assert r.meta["code"] == "CUSTOM"


# ── ExtractionResult: failure ────────────────────────────────────────────────
def test_failure_sets_code_and_status():
    r = ExtractionResult.failure("boom", code=ErrorCodes.READ_ERROR)
    assert r.error == "boom"
    assert r.status == ExtractionStatus.ERROR
    assert r.meta["code"] == ErrorCodes.READ_ERROR
    assert r.text is None
    assert r.failed is True
    assert r.ok is False


def test_failure_with_meta_and_warnings():
    r = ExtractionResult.failure("e", code="X", meta={"a": "b"}, warnings=["warn"])
    assert r.meta["a"] == "b"
    assert r.meta["code"] == "X"  # code always set/overwritten
    assert r.warnings == ["warn"]


def test_failure_code_overrides_meta_code():
    r = ExtractionResult.failure("e", code="REAL", meta={"code": "OLD"})
    assert r.meta["code"] == "REAL"


# ── ExtractionResult: no_text_layer ──────────────────────────────────────────
def test_no_text_layer_defaults():
    r = ExtractionResult.no_text_layer()
    assert r.needs_ocr is True
    assert r.status == ExtractionStatus.NO_TEXT_LAYER
    assert r.meta["code"] == ErrorCodes.NO_TEXT_LAYER
    assert r.error is None
    assert r.ok is True  # no error → ok predicate True


def test_no_text_layer_custom_code_preserved():
    r = ExtractionResult.no_text_layer(meta={"code": "OCR_NOT_IMPLEMENTED"})
    assert r.meta["code"] == "OCR_NOT_IMPLEMENTED"
    assert r.needs_ocr is True


def test_no_text_layer_warnings():
    r = ExtractionResult.no_text_layer(warnings=["needs ocr"])
    assert r.warnings == ["needs ocr"]


# ── ExtractionResult: defaults & extra forbid ────────────────────────────────
def test_result_default_construction():
    r = ExtractionResult()
    assert r.status == ExtractionStatus.OK
    assert r.needs_ocr is False
    assert r.meta == {}
    assert r.warnings == []
    assert r.ok is True


def test_result_forbids_extra():
    with pytest.raises(ValidationError):
        ExtractionResult(unexpected="x")


def test_ok_failed_are_complementary():
    r = ExtractionResult(error="e")
    assert r.failed is True and r.ok is False
