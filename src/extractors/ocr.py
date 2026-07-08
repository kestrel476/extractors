"""
OCR-слой (заглушка).

Когда у документа нет текстового слоя (скан в PDF, фотография, изображение),
извлечение «текстом» невозможно — нужен OCR. Реальный движок пока не подключён,
поэтому здесь находится заглушка :class:`OcrStub`, которая возвращает корректный
:class:`ExtractionResult` со статусом ``NO_TEXT_LAYER`` и пометкой ``needs_ocr``.

Чтобы подключить настоящий OCR, реализуйте :class:`extractors.interfaces.OcrEngine`
(например, через ``pytesseract``/``pdf2image`` или облачный сервис) и передайте
экземпляр в фасад: ``build_default_extractor(ocr=MyOcrEngine())``.
"""

from __future__ import annotations

from ._logging import NullLogger
from .errors import ErrorCodes
from .interfaces import OcrEngine
from .types import ExtractionResult, FileSource


class OcrStub(OcrEngine):
    """Заглушка OCR-движка.

    Не выполняет распознавания: фиксирует факт, что файл требует OCR, и
    возвращает результат с ``needs_ocr=True`` и статусом ``NO_TEXT_LAYER``.
    Служит точкой интеграции для будущего реального движка и позволяет всему
    конвейеру работать уже сейчас.
    """

    def __init__(self, logger=None) -> None:
        self.logger = logger or NullLogger()

    def recognize(self, src: FileSource) -> ExtractionResult:
        self.logger.log(
            "DOC_EXTRACTION",
            f"OCR-заглушка вызвана для '{src.filename}' (mime={src.mime}); "
            "распознавание не реализовано",
        )
        return ExtractionResult.no_text_layer(
            meta={
                "code": ErrorCodes.OCR_NOT_IMPLEMENTED,
                "mime": str(src.mime),
                "filename": str(src.filename),
                "ocr": "stub",
            },
            warnings=["OCR не реализован: возвращена заглушка"],
        )
