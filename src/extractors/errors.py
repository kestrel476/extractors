"""
Коды ошибок и статусов для унификации логирования и обработки результатов.
"""

from __future__ import annotations


class ErrorCodes:
    """Машиночитаемые коды, попадающие в ``ExtractionResult.meta['code']``."""

    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    READ_ERROR = "READ_ERROR"
    ENCODING_ERROR = "ENCODING_ERROR"
    NO_TEXT_LAYER = "NO_TEXT_LAYER"
    TOO_LARGE = "TOO_LARGE"
    ARCHIVE_ERROR = "ARCHIVE_ERROR"
    ARCHIVE_PASSWORD = "ARCHIVE_PASSWORD"
    ARCHIVE_NO_CANDIDATE = "ARCHIVE_NO_CANDIDATE"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    PARSE_ERROR = "PARSE_ERROR"
    OCR_NOT_IMPLEMENTED = "OCR_NOT_IMPLEMENTED"
    EMPTY = "EMPTY"
