"""
Распознанные, но не извлекаемые форматы.

Для проприетарных/закрытых форматов, у которых нет надёжного открытого способа
извлечь текст, мы всё равно хотим *распознавать* файл и возвращать понятный
ответ (а не «Unsupported format»). Это даёт полное покрытие списка форматов и
ясную причину, почему текст не извлечён.

Регистрируется в реестре ПОСЛЕДНИМ среди специализированных, но ПЕРЕД общим
plain-text хендлером, чтобы перехватывать именно эти расширения.
"""

from __future__ import annotations

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, ExtractionStatus, FileSource

# Расширение -> причина, почему извлечение не поддерживается.
RECOGNIZED_UNSUPPORTED = {
    ".one": "Microsoft OneNote — закрытый формат, извлечение не поддерживается",
    ".onenote": "Microsoft OneNote — закрытый формат, извлечение не поддерживается",
    ".indd": "Adobe InDesign — проприетарный бинарный формат, нужен InDesign/IDML",
    ".lit": "Microsoft LIT — устаревший DRM-формат, извлечение не поддерживается",
    ".lrf": "Sony BBeB (LRF) — закрытый формат, извлечение не поддерживается",
    ".pdb": "Palm Database (PDB) — формат зависит от типа БД, не поддерживается",
    ".dmg": "macOS disk image — образ ФС, требует распаковки на macOS",
}


class RecognizedUnsupportedExtractor(BaseExtractor):
    """Распознаёт известные, но неизвлекаемые форматы и возвращает причину."""

    MIME_TYPES = frozenset(
        {
            "application/onenote",
            "application/x-indesign",
            "application/x-ms-reader",
            "application/x-sony-bbeb",
            "application/vnd.palm",
            "application/x-apple-diskimage",
        }
    )
    EXTENSIONS = tuple(RECOGNIZED_UNSUPPORTED.keys())

    def extract(self, src: FileSource) -> ExtractionResult:
        reason = RECOGNIZED_UNSUPPORTED.get(src.ext, "Формат распознан, но извлечение не поддерживается")
        self.logger.log("DOC_EXTRACTION", f"Распознан неизвлекаемый формат: {src.ext} — {reason}")
        return ExtractionResult(
            text=None,
            error=reason,
            status=ExtractionStatus.UNSUPPORTED,
            meta={"code": ErrorCodes.UNSUPPORTED_FORMAT, "ext": src.ext, "mime": str(src.mime)},
        )
