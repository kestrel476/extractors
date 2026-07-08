"""
extractors — сервис извлечения текстового слоя из документов разных форматов.

Быстрый старт::

    from extractors import build_default_extractor, FileSource

    extractor = build_default_extractor()
    text, error = extractor.extract_text("document.pdf")

    # или богатый результат:
    result = extractor.extract(FileSource(path="document.pdf"))
    if result.needs_ocr:
        ...  # файл без текстового слоя — нужен OCR
"""

from __future__ import annotations

__version__ = "0.1.0"

from ._logging import NullLogger, StdLogger, get_logger
from .bootstrap import build_default_extractor
from .errors import ErrorCodes
from .facade import FileTextExtractor
from .interfaces import Extractor, MimeDetector, OcrEngine
from .ocr import OcrStub
from .registry import ExtractorRegistry
from .types import ExtractionResult, ExtractionStatus, FileSource

__all__ = [
    "__version__",
    "build_default_extractor",
    "FileTextExtractor",
    "FileSource",
    "ExtractionResult",
    "ExtractionStatus",
    "ErrorCodes",
    "Extractor",
    "MimeDetector",
    "OcrEngine",
    "OcrStub",
    "ExtractorRegistry",
    "NullLogger",
    "StdLogger",
    "get_logger",
]
