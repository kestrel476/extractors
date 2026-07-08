"""
Изображения: у растровых картинок нет текстового слоя — это всегда OCR.

Фасад обычно перехватывает изображения ещё на предпроверке
(``text_layer.definitely_needs_ocr``) и не доходит до этого хендлера. Он нужен
как явная регистрация в реестре: на случай прямого вызова и для полноты карты
форматов. Возвращает ``NO_TEXT_LAYER`` → фасад направит файл в OCR.
"""

from __future__ import annotations

from .base import BaseExtractor
from ..types import ExtractionResult, FileSource


class ImageExtractor(BaseExtractor):
    """Изображения — текстового слоя нет, нужен OCR."""

    MIME_TYPES = frozenset(
        {
            "image/png", "image/jpeg", "image/tiff", "image/bmp", "image/gif",
            "image/webp", "image/heic", "image/heif", "image/avif", "image/jxl",
            "image/jp2", "image/x-portable-anymap", "image/x-portable-bitmap",
            "image/x-portable-graymap", "image/x-portable-pixmap",
            "image/vnd.microsoft.icon",
        }
    )
    EXTENSIONS = (
        ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp",
        ".heic", ".heif", ".avif", ".jxl", ".jp2", ".j2k",
        ".pnm", ".pbm", ".pgm", ".ppm", ".ico",
    )

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Изображение: текстового слоя нет → OCR")
        return ExtractionResult.no_text_layer(meta={"mime": str(src.mime)})
