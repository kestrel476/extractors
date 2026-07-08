"""
Абстрактные контракты пакета.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .types import ExtractionResult, FileSource


class Extractor(ABC):
    """Контракт экстрактора конкретного формата (или группы форматов)."""

    @abstractmethod
    def can_handle(self, mime: Optional[str], filename: Optional[str]) -> bool:
        """Сообщает, может ли экстрактор обработать файл по MIME-типу/имени."""
        ...

    @abstractmethod
    def extract(self, src: FileSource) -> ExtractionResult:
        """Извлекает текст или возвращает результат с описанием ошибки."""
        ...


class MimeDetector(ABC):
    """Контракт детектора MIME-типа по содержимому и/или имени файла."""

    @abstractmethod
    def detect(self, src: FileSource) -> Optional[str]:
        """Возвращает MIME-тип файла или ``None``."""
        ...


class OcrEngine(ABC):
    """Контракт OCR-движка для файлов без текстового слоя.

    Реализация-заглушка находится в :mod:`extractors.ocr`. Реальный движок
    (Tesseract, облачный OCR и т. п.) подключается через тот же интерфейс.
    """

    @abstractmethod
    def recognize(self, src: FileSource) -> ExtractionResult:
        """Распознаёт текст из файла без текстового слоя."""
        ...
