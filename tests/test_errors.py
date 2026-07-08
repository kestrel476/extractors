"""Тесты кодов ошибок ErrorCodes."""
from __future__ import annotations

from extractors.errors import ErrorCodes


def test_all_codes_present_and_are_strings():
    expected = {
        "UNSUPPORTED_FORMAT": "UNSUPPORTED_FORMAT",
        "READ_ERROR": "READ_ERROR",
        "ENCODING_ERROR": "ENCODING_ERROR",
        "NO_TEXT_LAYER": "NO_TEXT_LAYER",
        "TOO_LARGE": "TOO_LARGE",
        "ARCHIVE_ERROR": "ARCHIVE_ERROR",
        "ARCHIVE_PASSWORD": "ARCHIVE_PASSWORD",
        "ARCHIVE_NO_CANDIDATE": "ARCHIVE_NO_CANDIDATE",
        "DEPENDENCY_MISSING": "DEPENDENCY_MISSING",
        "PARSE_ERROR": "PARSE_ERROR",
        "OCR_NOT_IMPLEMENTED": "OCR_NOT_IMPLEMENTED",
        "EMPTY": "EMPTY",
    }
    for attr, value in expected.items():
        assert getattr(ErrorCodes, attr) == value
        assert isinstance(getattr(ErrorCodes, attr), str)


def test_codes_are_unique():
    codes = [
        ErrorCodes.UNSUPPORTED_FORMAT, ErrorCodes.READ_ERROR, ErrorCodes.ENCODING_ERROR,
        ErrorCodes.NO_TEXT_LAYER, ErrorCodes.TOO_LARGE, ErrorCodes.ARCHIVE_ERROR,
        ErrorCodes.ARCHIVE_PASSWORD, ErrorCodes.ARCHIVE_NO_CANDIDATE,
        ErrorCodes.DEPENDENCY_MISSING, ErrorCodes.PARSE_ERROR,
        ErrorCodes.OCR_NOT_IMPLEMENTED, ErrorCodes.EMPTY,
    ]
    assert len(codes) == len(set(codes))
