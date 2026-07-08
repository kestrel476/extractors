"""
Сборка реестра по умолчанию и фасада.

Порядок регистрации важен: более специфичные форматы — раньше «жадных».
Контейнеры и структурированные форматы регистрируются до общего plain-text
хендлера, который идёт последним.
"""

from __future__ import annotations

from typing import Optional

from ._logging import NullLogger
from .facade import FileTextExtractor
from .handlers.archives import ArchiveExtractor
from .handlers.best_effort import DjvuExtractor, PostScriptExtractor, PsdExtractor
from .handlers.csv_tsv import CsvExtractor
from .handlers.data import SqliteExtractor, TabularDataExtractor
from .handlers.doc import DocExtractor
from .handlers.docx import DocxExtractor
from .handlers.email_msg import EmailExtractor
from .handlers.epub import EpubExtractor
from .handlers.excel import ExcelExtractor
from .handlers.fitz_doc import FitzDocExtractor
from .handlers.html import HtmlExtractor
from .handlers.image import ImageExtractor
from .handlers.iwork import IWorkExtractor
from .handlers.opendocument import OpenDocumentExtractor
from .handlers.pdf import PdfExtractor
from .handlers.pim import IcsVcfExtractor
from .handlers.plain_text import PlainTextExtractor
from .handlers.powerpoint import PptxExtractor
from .handlers.recognized import RecognizedUnsupportedExtractor
from .handlers.rtf import RtfExtractor
from .handlers.structured import JsonExtractor, YamlExtractor
from .handlers.web_docs import MhtmlExtractor, NotebookExtractor
from .handlers.xml import XmlExtractor
from .interfaces import OcrEngine
from .markdown_render import MarkItDownRenderer
from .registry import ExtractorRegistry


def build_default_extractor(
    logger=None,
    *,
    ocr: Optional[OcrEngine] = None,
    pdf_max_pages: Optional[int] = None,
) -> FileTextExtractor:
    """Собирает фасад со всеми зарегистрированными экстракторами.

    Args:
        logger: Логгер с интерфейсом ``log(event, message)`` (по умолчанию — тихий).
        ocr: OCR-движок для файлов без текстового слоя. Если ``None``, подключается
            :class:`extractors.ocr.OcrStub`.
        pdf_max_pages: Ограничение числа страниц PDF (``None`` — без ограничения).
    """
    log = logger or NullLogger()

    if ocr is None:
        from .ocr import OcrStub

        ocr = OcrStub(logger=log)

    reg = ExtractorRegistry()
    facade = FileTextExtractor(
        registry=reg, ocr=ocr, md_renderer=MarkItDownRenderer(logger=log), logger=log
    )

    # 1) Контейнеры/архивы (используют фасад для рекурсии).
    reg.register(ArchiveExtractor(facade=facade, logger=log))
    reg.register(IWorkExtractor(facade=facade, logger=log))

    # 2) PDF и фиксированные макеты / e-books через MuPDF.
    reg.register(PdfExtractor(max_pages=pdf_max_pages, logger=log))
    reg.register(FitzDocExtractor(logger=log))

    # 3) Офисные документы.
    reg.register(DocxExtractor(logger=log))
    reg.register(DocExtractor(logger=log))
    reg.register(ExcelExtractor(logger=log))
    reg.register(PptxExtractor(logger=log))
    reg.register(OpenDocumentExtractor(logger=log))
    reg.register(RtfExtractor(logger=log))
    reg.register(EpubExtractor(logger=log))

    # 4) Почта и web-архивы (Mhtml — раньше Email, чтобы не путать message/rfc822).
    reg.register(MhtmlExtractor(logger=log))
    reg.register(EmailExtractor(logger=log))

    # 5) Структурированные текстовые форматы (раньше plain-text).
    reg.register(NotebookExtractor(logger=log))
    reg.register(JsonExtractor(logger=log))
    reg.register(YamlExtractor(logger=log))
    reg.register(CsvExtractor(logger=log))
    reg.register(HtmlExtractor(logger=log))
    reg.register(XmlExtractor(logger=log))

    # 6) Данные / базы данных.
    reg.register(SqliteExtractor(logger=log))
    reg.register(TabularDataExtractor(logger=log))

    # 7) PIM (календари/контакты).
    reg.register(IcsVcfExtractor(logger=log))

    # 8) Форматы с ограниченной поддержкой.
    reg.register(DjvuExtractor(logger=log))
    reg.register(PostScriptExtractor(logger=log))
    reg.register(PsdExtractor(logger=log))

    # 9) Изображения (нет текстового слоя → OCR).
    reg.register(ImageExtractor(logger=log))

    # 10) Распознанные, но неизвлекаемые проприетарные форматы.
    reg.register(RecognizedUnsupportedExtractor(logger=log))

    # 11) Общий plain-text / исходный код — последним (самый «жадный»).
    reg.register(PlainTextExtractor(logger=log))

    return facade
