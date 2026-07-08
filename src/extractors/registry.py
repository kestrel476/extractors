"""
Реестр экстракторов: хранит зарегистрированные экстракторы и выбирает подходящий.
"""

from __future__ import annotations

from typing import List, Optional

from .interfaces import Extractor


class ExtractorRegistry:
    """Упорядоченный список экстракторов с выбором первого подходящего.

    Порядок регистрации важен: побеждает первый экстрактор, чей
    ``can_handle`` вернул ``True``. Более специфичные форматы следует
    регистрировать раньше «жадных» (например, архивы и структурированные
    форматы — раньше общего текстового хендлера).
    """

    def __init__(self) -> None:
        self._items: List[Extractor] = []

    def register(self, extractor: Extractor) -> "ExtractorRegistry":
        self._items.append(extractor)
        return self

    def pick(self, mime: Optional[str], filename: Optional[str]) -> Optional[Extractor]:
        for ex in self._items:
            if ex.can_handle(mime, filename):
                return ex
        return None

    def __len__(self) -> int:
        return len(self._items)
