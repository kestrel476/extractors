"""Тесты встроенного логгера: NullLogger, StdLogger, get_logger, LoggerLike."""
from __future__ import annotations

import logging

from extractors._logging import (
    LoggerLike,
    NullLogger,
    StdLogger,
    get_logger,
)


# ── NullLogger ───────────────────────────────────────────────────────────────
def test_null_logger_returns_none_and_no_output(caplog):
    lg = NullLogger()
    with caplog.at_level(logging.DEBUG):
        assert lg.log("ANY_EVENT", "message") is None
    assert caplog.records == []


def test_null_logger_satisfies_protocol():
    assert isinstance(NullLogger(), LoggerLike)


# ── StdLogger ────────────────────────────────────────────────────────────────
def test_std_logger_debug_level_for_normal_event(caplog):
    lg = StdLogger("extractors.test.debug")
    with caplog.at_level(logging.DEBUG, logger="extractors.test.debug"):
        lg.log("DOC_EXTRACTION", "hello")
    assert len(caplog.records) == 1
    rec = caplog.records[0]
    assert rec.levelno == logging.DEBUG
    assert "DOC_EXTRACTION" in rec.getMessage()
    assert "hello" in rec.getMessage()


def test_std_logger_error_level_for_error_suffix(caplog):
    lg = StdLogger("extractors.test.err")
    with caplog.at_level(logging.DEBUG, logger="extractors.test.err"):
        lg.log("DOC_EXTRACTION_ERROR", "boom")
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.ERROR
    assert "boom" in caplog.records[0].getMessage()


def test_std_logger_default_name():
    lg = StdLogger()
    assert lg._logger.name == "extractors"


def test_std_logger_satisfies_protocol():
    assert isinstance(StdLogger(), LoggerLike)


# ── get_logger ───────────────────────────────────────────────────────────────
def test_get_logger_disabled_returns_null():
    lg = get_logger(enabled=False)
    assert isinstance(lg, NullLogger)


def test_get_logger_enabled_returns_std():
    lg = get_logger("extractors.custom", enabled=True)
    assert isinstance(lg, StdLogger)
    assert lg._logger.name == "extractors.custom"


def test_get_logger_default_is_disabled():
    assert isinstance(get_logger(), NullLogger)
