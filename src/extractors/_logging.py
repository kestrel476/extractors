"""
Лёгкий встроенный логгер пакета.

Исторически пакет зависел от внешнего ``src.core.custom_logger`` с интерфейсом
``logger.log(event_code, message)``. Чтобы сделать ``extractors`` автономным и
переносимым, здесь определён совместимый минимальный логгер поверх стандартного
``logging``. Внешний логгер можно по-прежнему передать в фасад/хендлеры — он
будет использован, если предоставляет метод ``log(event, message)``.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable


@runtime_checkable
class LoggerLike(Protocol):
    """Контракт логгера, который ожидает пакет."""

    def log(self, event: str, message: str) -> None:  # pragma: no cover - протокол
        ...


class NullLogger:
    """Логгер-заглушка: ничего не делает.

    Используется по умолчанию, чтобы хендлеры не зависели от настроенного
    логирования и не засоряли вывод.
    """

    def log(self, event: str, message: str) -> None:  # noqa: D401 - простая заглушка
        return None


class StdLogger:
    """Адаптер интерфейса ``log(event, message)`` поверх стандартного ``logging``.

    Код события (event) пишется в ``extra`` и в начало сообщения, чтобы его было
    удобно фильтровать. Уровень определяется по суффиксу ``_ERROR`` в коде
    события (как было в исходном проекте: ``DOC_EXTRACTION`` / ``DOC_EXTRACTION_ERROR``).
    """

    def __init__(self, name: str = "extractors") -> None:
        self._logger = logging.getLogger(name)

    def log(self, event: str, message: str) -> None:
        level = logging.ERROR if event.endswith("_ERROR") else logging.DEBUG
        self._logger.log(level, "[%s] %s", event, message)


def get_logger(name: str = "extractors", *, enabled: bool = False) -> LoggerLike:
    """Возвращает логгер пакета.

    Args:
        name: Имя логгера ``logging``.
        enabled: Если ``True`` — настоящий логгер, иначе тихая заглушка.
    """
    return StdLogger(name) if enabled else NullLogger()
