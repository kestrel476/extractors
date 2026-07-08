"""
Проверка наличия текстового слоя.

«Текстовый слой» — это извлекаемый без распознавания текст. У части форматов
его не может быть в принципе (растровые изображения), у части он может
отсутствовать в конкретном файле (PDF-скан без OCR, пустой документ). Этот
модуль даёт дешёвую предварительную проверку *до* запуска тяжёлого хендлера,
чтобы такие файлы можно было сразу направить в OCR.

Важно: SVG — это XML с текстом, поэтому НЕ считается «изображением без текста».
Окончательное решение по PDF/XPS/DjVu принимает соответствующий хендлер.
"""

from __future__ import annotations

from typing import Optional

# Растровые изображения: текстового слоя нет никогда — только OCR.
RASTER_IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp",
    ".heic", ".heif", ".avif", ".jxl", ".jp2", ".j2k",
    ".pnm", ".pbm", ".pgm", ".ppm", ".ico",
}

# MIME-типы с префиксом image/, которые НЕ являются «растром без текста»:
# SVG — это XML с текстом; DjVu имеет текстовый слой; PSD — текстовые слои.
# Такие файлы должны дойти до своих хендлеров, а не уходить сразу в OCR.
_TEXTUAL_IMAGE_MIMES = {"image/svg+xml", "image/vnd.djvu", "image/vnd.adobe.photoshop"}


def is_image(mime: Optional[str], filename: Optional[str]) -> bool:
    """Является ли файл растровым изображением (заведомо без текстового слоя)."""
    if mime and mime.startswith("image/") and mime not in _TEXTUAL_IMAGE_MIMES:
        return True
    name = (filename or "").lower()
    return any(name.endswith(ext) for ext in RASTER_IMAGE_EXTS)


def definitely_needs_ocr(mime: Optional[str], filename: Optional[str]) -> bool:
    """Быстрая проверка: точно ли у файла нет текстового слоя.

    Возвращает ``True`` только для случаев, где OCR неизбежен ещё до разбора
    (растровые изображения). Для PDF/XPS/DjVu и контейнеров возвращает
    ``False`` — наличие текста определяется уже внутри хендлера.
    """
    return is_image(mime, filename)
