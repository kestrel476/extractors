"""
Тесты сборки фасада по умолчанию :func:`extractors.build_default_extractor`.
"""
from __future__ import annotations

from extractors import (
    FileTextExtractor,
    OcrEngine,
    OcrStub,
    build_default_extractor,
)
from extractors.handlers.pdf import PdfExtractor
from extractors.markdown_render import MarkItDownRenderer


def test_returns_file_text_extractor():
    svc = build_default_extractor()
    assert isinstance(svc, FileTextExtractor)


def test_registry_is_populated():
    svc = build_default_extractor()
    assert len(svc.registry) > 0


def test_md_renderer_is_markitdown():
    svc = build_default_extractor()
    assert isinstance(svc.md_renderer, MarkItDownRenderer)


def test_default_ocr_is_stub():
    svc = build_default_extractor()
    assert isinstance(svc.ocr, OcrStub)


def test_custom_ocr_is_kept():
    class MyOcr(OcrEngine):
        def recognize(self, src):  # pragma: no cover - не вызывается
            return None

    my = MyOcr()
    svc = build_default_extractor(ocr=my)
    assert svc.ocr is my


def _find(registry, cls):
    return [x for x in registry._items if isinstance(x, cls)]


def test_pdf_max_pages_forwarded_to_handler():
    svc = build_default_extractor(pdf_max_pages=3)
    pdfs = _find(svc.registry, PdfExtractor)
    assert pdfs, "PdfExtractor должен быть зарегистрирован"
    assert pdfs[0].max_pages == 3


def test_pdf_max_pages_default_none():
    svc = build_default_extractor()
    pdfs = _find(svc.registry, PdfExtractor)
    assert pdfs[0].max_pages is None
