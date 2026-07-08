"""
Базовый класс экстрактора.

Содержит общую для всех хендлеров логику:
- объявление поддерживаемых MIME-типов и расширений + реализация ``can_handle``;
- чтение байтов из источника (путь или ``data``);
- декодирование байтов в строку с автоопределением кодировки;
- ленивый импорт необязательной зависимости с понятной ошибкой.

Конкретный хендлер задаёт ``MIME_TYPES`` / ``EXTENSIONS`` и реализует ``extract``.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Optional, Tuple, Union

from .._logging import NullLogger
from ..errors import ErrorCodes
from ..interfaces import Extractor
from ..types import ExtractionResult, FileSource


class BaseExtractor(Extractor):
    """Общая основа для экстракторов форматов."""

    #: MIME-типы, которые обрабатывает экстрактор.
    MIME_TYPES: frozenset = frozenset()
    #: Расширения файлов (с точкой, в нижнем регистре).
    EXTENSIONS: Tuple[str, ...] = ()

    def __init__(self, logger=None) -> None:
        self.logger = logger or NullLogger()

    # --- Выбор экстрактора ---------------------------------------------------

    def can_handle(self, mime: Optional[str], filename: Optional[str]) -> bool:
        if mime and mime in self.MIME_TYPES:
            return True
        name = (filename or "").lower()
        return bool(name) and any(name.endswith(ext) for ext in self.EXTENSIONS)

    # --- Markdown-режим ------------------------------------------------------

    def extract_markdown(self, src: FileSource) -> Optional[ExtractionResult]:
        """Извлекает содержимое в формате Markdown.

        По умолчанию возвращает ``None`` — «нативного» Markdown-рендера нет, и
        фасад откатывается на обычный :meth:`extract` (его текст сам по себе
        является валидным Markdown для plain-text/кода/разметки). Хендлеры
        форматов с таблицами (ODF, CSV/TSV, SQLite, колоночные данные)
        переопределяют этот метод и возвращают Markdown-таблицы.
        """
        return None

    # --- Ввод-вывод ----------------------------------------------------------

    def read_bytes(self, src: FileSource) -> bytes:
        """Читает содержимое источника в байты."""
        if src.data is not None:
            return src.data
        if not src.path:
            raise ValueError(f"{type(self).__name__} requires path or data")
        with open(src.path, "rb") as f:
            return f.read()

    def binary_source(self, src: FileSource) -> Union[BytesIO, str]:
        """Источник для библиотек, принимающих путь **или** файловый объект.

        Возвращает ``BytesIO(data)`` при наличии байтов, иначе путь к файлу —
        и никогда ``None`` (``FileSource`` гарантирует хотя бы одно из
        ``path``/``data``).
        """
        if src.data is not None:
            return BytesIO(src.data)
        if src.path:
            return src.path
        raise ValueError(f"{type(self).__name__} requires path or data")

    def decode_bytes(self, raw: bytes) -> Tuple[str, str, List[str]]:
        """Декодирует байты в строку.

        Порядок: UTF-8 → автоопределение (charset-normalizer) → резерв latin-1.

        Returns:
            (текст, имя_кодировки, предупреждения)
        """
        # BOM-варианты UTF обрабатываются через utf-8-sig прозрачно.
        try:
            return raw.decode("utf-8-sig"), "utf-8", []
        except UnicodeDecodeError:
            pass

        try:
            from charset_normalizer import from_bytes

            best = from_bytes(raw).best()
            if best is not None:
                enc = best.encoding or "unknown"
                return str(best), enc, [f"Re-encoded from detected encoding '{enc}'"]
        except Exception:
            pass

        # Последний резерв: latin-1 не падает никогда.
        return raw.decode("latin-1", errors="ignore"), "latin-1", ["Re-encoded from fallback latin-1"]

    def read_text(self, src: FileSource) -> Tuple[str, str, List[str]]:
        """Читает источник и декодирует в текст за один шаг."""
        return self.decode_bytes(self.read_bytes(src))

    # --- Вспомогательное -----------------------------------------------------

    def require(self, module: str, *, pip_name: Optional[str] = None):
        """Лениво импортирует необязательную зависимость.

        Бросает ``ImportError`` с понятным сообщением, если модуль не установлен;
        хендлер должен поймать его и вернуть ``ExtractionResult.failure(... DEPENDENCY_MISSING)``.
        """
        import importlib

        try:
            return importlib.import_module(module)
        except Exception as e:  # noqa: BLE001
            pkg = pip_name or module
            raise ImportError(f"'{module}' недоступен (установите: pip install {pkg}): {e}") from e

    def dependency_error(self, e: Exception) -> ExtractionResult:
        """Унифицированный результат для отсутствующей зависимости."""
        self.logger.log("DOC_EXTRACTION_ERROR", f"Отсутствует зависимость: {e}")
        return ExtractionResult.failure(str(e), code=ErrorCodes.DEPENDENCY_MISSING)
