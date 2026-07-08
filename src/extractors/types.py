"""
Модели данных пакета: источник файла и результат извлечения.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExtractionStatus(str, Enum):
    """Статус извлечения текста.

    - ``OK``           — текст успешно извлечён.
    - ``NO_TEXT_LAYER``— формат распознан, но текстового слоя нет
                          (например, скан в PDF или изображение) → кандидат на OCR.
    - ``UNSUPPORTED``  — формат не поддерживается ни одним хендлером.
    - ``ERROR``        — произошла ошибка при чтении/разборе.
    """

    OK = "ok"
    NO_TEXT_LAYER = "no_text_layer"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class FileSource(BaseModel):
    """Универсальный источник файла: путь и/или байты."""

    model_config = ConfigDict(
        extra="forbid",            # запрещаем лишние поля
        str_strip_whitespace=True,  # убираем лишние пробелы в строковых полях
        frozen=False,               # экземпляры можно дополнять (mime, filename)
    )

    path: Optional[str] = Field(default=None, description="Путь к файлу")
    data: Optional[bytes] = Field(default=None, description="Содержимое файла в байтах")
    filename: Optional[str] = Field(default=None, description="Имя файла с расширением")
    mime: Optional[str] = Field(default=None, description="Предполагаемый MIME-тип файла")

    @field_validator("data", mode="before")
    @classmethod
    def _normalize_data(cls, v):
        if v is None:
            return None
        if isinstance(v, bytes):
            return v
        if isinstance(v, (bytearray, memoryview)):
            return bytes(v)
        if isinstance(v, str):
            return v.encode("utf-8", errors="ignore")
        raise TypeError(f"Unsupported type for data: {type(v)!r}")

    @model_validator(mode="after")
    def _validate_and_autofill(self) -> "FileSource":
        if not self.path and self.data is None:
            raise ValueError("FileSource requires at least one of 'path' or 'data'")
        if self.path and not self.filename:
            self.filename = os.path.basename(self.path)
        return self

    @property
    def ext(self) -> str:
        """Расширение файла в нижнем регистре, включая точку (или пустая строка)."""
        name = (self.filename or self.path or "").lower()
        return os.path.splitext(name)[1]


class ExtractionResult(BaseModel):
    """Результат извлечения текста из файла."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
        frozen=False,
    )

    text: Optional[str] = Field(default=None, description="Извлечённый текст")
    error: Optional[str] = Field(default=None, description="Человекочитаемое описание ошибки")
    status: ExtractionStatus = Field(
        default=ExtractionStatus.OK, description="Машиночитаемый статус извлечения"
    )
    needs_ocr: bool = Field(
        default=False, description="Текстовый слой отсутствует — требуется OCR"
    )
    meta: Dict[str, str] = Field(default_factory=dict, description="Доп. сведения (код, страницы, кодировка, ...)")
    warnings: List[str] = Field(default_factory=list, description="Некритичные предупреждения")

    # --- Фабрики для единообразного создания результатов ---------------------

    @classmethod
    def success(
        cls,
        text: Optional[str],
        *,
        meta: Optional[Dict[str, str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "ExtractionResult":
        """Успешный результат. Пустой текст превращается в статус ``EMPTY``."""
        if text:
            return cls(text=text, status=ExtractionStatus.OK, meta=meta or {}, warnings=warnings or [])
        m = dict(meta or {})
        m.setdefault("code", "EMPTY")
        return cls(text=None, status=ExtractionStatus.OK, meta=m, warnings=warnings or [])

    @classmethod
    def failure(
        cls,
        error: str,
        *,
        code: str,
        meta: Optional[Dict[str, str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "ExtractionResult":
        """Результат с ошибкой."""
        m = dict(meta or {})
        m["code"] = code
        return cls(text=None, error=error, status=ExtractionStatus.ERROR, meta=m, warnings=warnings or [])

    @classmethod
    def no_text_layer(
        cls,
        *,
        meta: Optional[Dict[str, str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "ExtractionResult":
        """Формат распознан, но текстового слоя нет — кандидат на OCR."""
        from .errors import ErrorCodes

        m = dict(meta or {})
        m.setdefault("code", ErrorCodes.NO_TEXT_LAYER)
        return cls(
            text=None,
            error=None,
            status=ExtractionStatus.NO_TEXT_LAYER,
            needs_ocr=True,
            meta=m,
            warnings=warnings or [],
        )

    # --- Удобные предикаты ---------------------------------------------------

    @property
    def ok(self) -> bool:
        """Успех, если нет ошибки."""
        return self.error is None

    @property
    def failed(self) -> bool:
        """Есть ошибка."""
        return self.error is not None
