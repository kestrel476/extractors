"""
Тесты фасада :class:`extractors.facade.FileTextExtractor`.

Маршрутизация конвейера проверяется в изоляции через минимальные фейки
реестра / OCR / markdown-рендера, а «сквозные» ветки — на реальном
собранном фасаде (фикстура ``svc``).
"""
from __future__ import annotations

import pytest

from extractors import (
    ErrorCodes,
    ExtractionResult,
    ExtractionStatus,
    ExtractorRegistry,
    FileSource,
    FileTextExtractor,
    OcrEngine,
    OcrStub,
)

from conftest import source


# ── Фейки для изоляции маршрутизации ───────────────────────────────────────
class FakeExtractor:
    """Экстрактор-заглушка: настраиваемый результат / исключение / can_handle."""

    def __init__(self, *, result=None, exc=None, handle=True, md=None, md_exc=None):
        self._result = result
        self._exc = exc
        self._handle = handle
        self._md = md
        self._md_exc = md_exc
        self.extract_calls = 0

    def can_handle(self, mime, filename):
        return self._handle

    def extract(self, src):
        self.extract_calls += 1
        if self._exc is not None:
            raise self._exc
        return self._result

    def extract_markdown(self, src):
        if self._md_exc is not None:
            raise self._md_exc
        return self._md


class FakeOcr(OcrEngine):
    def __init__(self):
        self.called_with = None
        self.base_meta_seen = None

    def recognize(self, src):
        self.called_with = src
        return ExtractionResult.success("ocr-text", meta={"ocr": "fake"})


class RecordingDetector:
    def __init__(self, mime="application/x-fake"):
        self.mime = mime
        self.calls = 0

    def detect(self, src):
        self.calls += 1
        return self.mime


class BoomDetector:
    def detect(self, src):  # pragma: no cover - должен НЕ вызываться
        raise AssertionError("detector must not be called when src.mime preset")


def _facade(registry=None, **kw):
    return FileTextExtractor(registry=registry or ExtractorRegistry(), **kw)


# ── UNSUPPORTED ─────────────────────────────────────────────────────────────
def test_unsupported_format():
    svc = _facade()  # пустой реестр, без OCR
    res = svc.extract(source(b"payload", "file.unknownext"))
    assert res.status == ExtractionStatus.UNSUPPORTED
    assert res.meta["code"] == ErrorCodes.UNSUPPORTED_FORMAT
    assert res.error == "Unsupported format"
    assert res.text is None
    assert res.meta["filename"] == "file.unknownext"


# ── MIME-детекция ───────────────────────────────────────────────────────────
def test_mime_detection_sets_src_mime():
    det = RecordingDetector("application/x-fake")
    svc = _facade(mime_detector=det)
    src = source(b"x", "f.bin")
    svc.extract(src)
    assert det.calls == 1
    assert src.mime == "application/x-fake"


def test_preset_mime_skips_detector():
    svc = _facade(mime_detector=BoomDetector())
    src = FileSource(data=b"x", filename="f.bin", mime="text/plain")
    svc.extract(src)  # detector.detect must not be invoked
    assert src.mime == "text/plain"


# ── Предпроверка изображения → OCR ─────────────────────────────────────────
def test_image_precheck_routes_to_ocr_stub():
    svc = _facade(ocr=OcrStub())
    res = svc.extract(source(b"\x89PNG\r\n\x1a\n", "x.png"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    assert res.meta["code"] == ErrorCodes.OCR_NOT_IMPLEMENTED
    assert res.meta["ocr"] == "stub"


def test_image_precheck_with_fake_ocr():
    ocr = FakeOcr()
    svc = _facade(ocr=ocr)
    res = svc.extract(source(b"GIF89a", "x.gif"))
    assert ocr.called_with is not None
    assert res.text == "ocr-text"


def test_ocr_none_returns_no_text_layer():
    svc = _facade(ocr=None)
    res = svc.extract(source(b"\x89PNG", "x.png"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    assert res.meta["code"] == ErrorCodes.NO_TEXT_LAYER
    assert any("OCR" in w for w in res.warnings)


# ── Изоляция исключения хендлера ───────────────────────────────────────────
def test_handler_exception_isolated_to_read_error():
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(exc=RuntimeError("boom")))
    svc = _facade(reg)
    res = svc.extract(source(b"x", "f.bin"))
    assert res.status == ExtractionStatus.ERROR
    assert res.meta["code"] == ErrorCodes.READ_ERROR
    assert res.error == "Error processing file"
    assert "boom" in res.meta["detail"]


# ── Постпроверка needs_ocr / NO_TEXT_LAYER → OCR ───────────────────────────
def test_needs_ocr_postcheck_routes_to_ocr():
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(result=ExtractionResult.no_text_layer()))
    ocr = FakeOcr()
    svc = _facade(reg, ocr=ocr)
    res = svc.extract(source(b"x", "f.bin"))
    assert ocr.called_with is not None
    assert res.text == "ocr-text"


def test_no_text_layer_status_postcheck_routes_to_ocr():
    # status == NO_TEXT_LAYER без needs_ocr тоже отправляет в OCR.
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(
        result=ExtractionResult(text=None, status=ExtractionStatus.NO_TEXT_LAYER)
    ))
    ocr = FakeOcr()
    svc = _facade(reg, ocr=ocr)
    res = svc.extract(source(b"x", "f.bin"))
    assert res.text == "ocr-text"


def test_ok_result_passes_through():
    reg = ExtractorRegistry()
    ok = ExtractionResult.success("hello", meta={"x": "1"})
    reg.register(FakeExtractor(result=ok))
    svc = _facade(reg, ocr=FakeOcr())
    res = svc.extract(source(b"x", "f.bin"))
    assert res.text == "hello"
    assert res.status == ExtractionStatus.OK


def test_pdf_blank_postcheck_routes_to_ocr(svc, pdf_blank_bytes):
    res = svc.extract(source(pdf_blank_bytes, "blank.pdf"))
    assert res.status == ExtractionStatus.NO_TEXT_LAYER
    assert res.needs_ocr is True
    assert res.meta["code"] == ErrorCodes.OCR_NOT_IMPLEMENTED


# ── Markdown-режим ──────────────────────────────────────────────────────────
def test_markdown_markitdown_tier(svc, docx_bytes):
    pytest.importorskip("markitdown")
    res = svc.extract(source(docx_bytes, "r.docx"), markdown=True)
    assert res.status == ExtractionStatus.OK
    assert res.meta["renderer"] == "markitdown"
    assert res.meta["format"] == "markdown"
    assert res.text and "Quarterly" in res.text


def test_markdown_native_tier_csv(svc, csv_bytes):
    res = svc.extract(source(csv_bytes, "r.csv"), markdown=True)
    assert res.status == ExtractionStatus.OK
    assert res.meta["format"] == "markdown"
    assert "|" in res.text
    assert "Region" in res.text


def test_markdown_passthrough_tier_txt(svc):
    res = svc.extract(source(b"hello world", "note.txt"), markdown=True)
    assert res.status == ExtractionStatus.OK
    assert res.meta["format"] == "text"
    assert res.text == "hello world"


def test_markdown_unsupported_format():
    svc = _facade()  # md_renderer None, пустой реестр
    res = svc.extract(source(b"x", "f.unknownext"), markdown=True)
    assert res.status == ExtractionStatus.UNSUPPORTED
    assert res.meta["code"] == ErrorCodes.UNSUPPORTED_FORMAT


class FakeRenderer:
    def __init__(self, *, handle=True, result=None):
        self._handle = handle
        self._result = result

    def can_handle(self, mime, filename):
        return self._handle

    def render(self, src):
        return self._result


def test_markdown_markitdown_no_text_layer_routes_to_ocr():
    ocr = FakeOcr()
    renderer = FakeRenderer(result=ExtractionResult.no_text_layer())
    svc = _facade(ocr=ocr, md_renderer=renderer)
    res = svc.extract(source(b"x", "scan.pdf"), markdown=True)
    assert ocr.called_with is not None
    assert res.text == "ocr-text"


def test_markdown_markitdown_none_falls_back_to_native():
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(md=ExtractionResult.success("# native md")))
    renderer = FakeRenderer(result=None)  # markitdown "не справился"
    svc = _facade(reg, md_renderer=renderer)
    res = svc.extract(source(b"x", "f.docx"), markdown=True)
    assert res.text == "# native md"
    assert res.meta["format"] == "markdown"


def test_markdown_native_exception_isolated():
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(md_exc=RuntimeError("md boom")))
    svc = _facade(reg)  # md_renderer None
    res = svc.extract(source(b"x", "f.bin"), markdown=True)
    assert res.status == ExtractionStatus.ERROR
    assert res.meta["code"] == ErrorCodes.READ_ERROR
    assert "md boom" in res.meta["detail"]


def test_markdown_native_needs_ocr_postcheck():
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(md=ExtractionResult.no_text_layer()))
    ocr = FakeOcr()
    svc = _facade(reg, ocr=ocr)
    res = svc.extract(source(b"x", "f.bin"), markdown=True)
    assert res.text == "ocr-text"


# ── Кортежный / обёрточный API ─────────────────────────────────────────────
def test_extract_text_from_bytes(svc):
    text, error = svc.extract_text_from_bytes("note.txt", b"hello world")
    assert text == "hello world"
    assert error is None


def test_extract_text_from_path(svc, tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hi there", encoding="utf-8")
    text, error = svc.extract_text(str(p))
    assert text == "hi there"
    assert error is None


def test_extract_text_reports_error():
    reg = ExtractorRegistry()
    reg.register(FakeExtractor(exc=RuntimeError("boom")))
    svc = _facade(reg)
    text, error = svc.extract_text_from_bytes("f.bin", b"x")
    assert text is None
    assert error == "Error processing file"


def test_extract_markdown_equals_extract_markdown_true(svc, csv_bytes):
    r1 = svc.extract_markdown(source(csv_bytes, "r.csv"))
    r2 = svc.extract(source(csv_bytes, "r.csv"), markdown=True)
    assert r1.text == r2.text
    assert r1.meta == r2.meta
    assert r1.status == r2.status
