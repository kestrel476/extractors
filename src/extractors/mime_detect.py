"""
Детектор MIME-типа: по содержимому (libmagic, если доступен) и по расширению.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    import magic  # python-magic; необязательная зависимость
except Exception:  # pragma: no cover - окружение без libmagic
    magic = None

from .interfaces import MimeDetector
from .types import FileSource

# Карта «расширение -> MIME». Используется как резерв, если libmagic недоступен,
# и как авторитетный источник для форматов, которые libmagic путает
# (например, OOXML-контейнеры он часто отдаёт как application/zip).
EXT_TO_MIME = {
    # --- Простой текст и разметка ---
    ".txt": "text/plain",
    ".text": "text/plain",
    ".log": "text/plain",
    ".nfo": "text/plain",
    ".me": "text/plain",
    ".1st": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".rst": "text/x-rst",
    ".asciidoc": "text/plain",
    ".adoc": "text/plain",
    ".org": "text/plain",
    ".tex": "text/x-tex",
    ".latex": "text/x-tex",
    ".rmd": "text/markdown",
    ".qmd": "text/markdown",
    # --- Конфиги ---
    ".ini": "text/plain",
    ".cfg": "text/plain",
    ".conf": "text/plain",
    ".env": "text/plain",
    ".properties": "text/plain",
    ".toml": "application/toml",
    # --- Исходный код ---
    ".py": "text/x-python",
    ".rs": "text/x-rust",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".ts": "text/x-typescript",
    ".tsx": "text/x-typescript",
    ".jsx": "text/javascript",
    ".vue": "text/plain",
    ".svelte": "text/plain",
    ".java": "text/x-java",
    ".c": "text/x-c",
    ".h": "text/x-c",
    ".cpp": "text/x-c++",
    ".cc": "text/x-c++",
    ".cxx": "text/x-c++",
    ".hpp": "text/x-c++",
    ".cs": "text/x-csharp",
    ".go": "text/x-go",
    ".rb": "text/x-ruby",
    ".php": "text/x-php",
    ".swift": "text/x-swift",
    ".kt": "text/x-kotlin",
    ".kts": "text/x-kotlin",
    ".scala": "text/x-scala",
    ".r": "text/x-r",
    ".m": "text/x-objcsrc",
    ".lua": "text/x-lua",
    ".sh": "application/x-sh",
    ".bash": "application/x-sh",
    ".zsh": "application/x-sh",
    ".ps1": "text/plain",
    ".bat": "text/plain",
    ".cmd": "text/plain",
    ".pl": "text/x-perl",
    ".pm": "text/x-perl",
    ".ex": "text/x-elixir",
    ".exs": "text/x-elixir",
    ".erl": "text/x-erlang",
    ".hrl": "text/x-erlang",
    ".hs": "text/x-haskell",
    ".lhs": "text/x-haskell",
    ".clj": "text/x-clojure",
    ".cljs": "text/x-clojure",
    ".sql": "application/sql",
    ".graphql": "application/graphql",
    ".gql": "application/graphql",
    ".proto": "text/plain",
    ".dart": "text/x-dart",
    # --- Субтитры / тексты / локализация (plain text) ---
    ".srt": "text/plain",
    ".vtt": "text/vtt",
    ".ass": "text/plain",
    ".ssa": "text/plain",
    ".sub": "text/plain",
    ".lrc": "text/plain",
    ".po": "text/x-gettext-translation",
    ".pot": "text/x-gettext-translation",
    ".strings": "text/plain",
    # --- Табличные / структурированные текстовые ---
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".jsonl": "application/json",
    ".ndjson": "application/json",
    ".arb": "application/json",
    ".ipynb": "application/x-ipynb+json",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".swagger": "application/json",
    ".openapi": "application/json",
    # --- XML-семейство ---
    ".xml": "application/xml",
    ".svg": "image/svg+xml",
    ".fb2": "application/x-fictionbook+xml",
    ".xliff": "application/xliff+xml",
    ".xlf": "application/xliff+xml",
    ".tmx": "application/xml",
    ".dita": "application/dita+xml",
    ".ditamap": "application/dita+xml",
    ".docbook": "application/docbook+xml",
    ".wsdl": "application/wsdl+xml",
    ".xsd": "application/xml",
    ".dtd": "application/xml-dtd",
    ".plist": "application/xml",
    ".resx": "application/xml",
    ".resw": "application/xml",
    ".manifest": "application/xml",
    ".fodt": "application/xml",
    ".fods": "application/xml",
    ".fodp": "application/xml",
    # --- HTML ---
    ".html": "text/html",
    ".htm": "text/html",
    ".xhtml": "application/xhtml+xml",
    ".mht": "multipart/related",
    ".mhtml": "multipart/related",
    # --- PDF и фиксированные макеты ---
    ".pdf": "application/pdf",
    ".xps": "application/oxps",
    ".oxps": "application/oxps",
    ".djvu": "image/vnd.djvu",
    ".djv": "image/vnd.djvu",
    # --- PIM ---
    ".ics": "text/calendar",
    ".vcf": "text/vcard",
    # --- Microsoft Office ---
    ".doc": "application/msword",
    ".dot": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".docm": "application/vnd.ms-word.document.macroEnabled.12",
    ".dotx": "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".xlsb": "application/vnd.ms-excel.sheet.binary.macroEnabled.12",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".pptm": "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
    ".one": "application/onenote",
    ".onenote": "application/onenote",
    ".msg": "application/vnd.ms-outlook",
    ".eml": "message/rfc822",
    # --- OpenDocument ---
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".odg": "application/vnd.oasis.opendocument.graphics",
    ".odf": "application/vnd.oasis.opendocument.formula",
    # --- RTF ---
    ".rtf": "application/rtf",
    # --- Электронные книги ---
    ".epub": "application/epub+zip",
    ".mobi": "application/x-mobipocket-ebook",
    ".azw": "application/vnd.amazon.ebook",
    ".azw3": "application/vnd.amazon.ebook",
    ".lit": "application/x-ms-reader",
    ".lrf": "application/x-sony-bbeb",
    ".pdb": "application/vnd.palm",
    ".cbz": "application/vnd.comicbook+zip",
    ".cbr": "application/vnd.comicbook-rar",
    # --- Презентации/дизайн ---
    ".key": "application/x-iwork-keynote-sffkey",
    ".pages": "application/x-iwork-pages-sffpages",
    ".numbers": "application/x-iwork-numbers-sffnumbers",
    ".sketch": "application/zip",
    ".ai": "application/postscript",
    ".eps": "application/postscript",
    ".ps": "application/postscript",
    ".indd": "application/x-indesign",
    ".psd": "image/vnd.adobe.photoshop",
    # --- Базы данных и данные ---
    ".sqlite": "application/vnd.sqlite3",
    ".sqlite3": "application/vnd.sqlite3",
    ".db": "application/vnd.sqlite3",
    ".parquet": "application/vnd.apache.parquet",
    ".avro": "application/avro",
    ".orc": "application/x-orc",
    ".arrow": "application/vnd.apache.arrow.file",
    ".feather": "application/vnd.apache.arrow.file",
    # --- Архивы ---
    ".zip": "application/zip",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".tgz": "application/gzip",
    ".bz2": "application/x-bzip2",
    ".tbz2": "application/x-bzip2",
    ".xz": "application/x-xz",
    ".zst": "application/zstd",
    ".lz4": "application/x-lz4",
    ".rar": "application/vnd.rar",
    ".7z": "application/x-7z-compressed",
    ".cab": "application/vnd.ms-cab-compressed",
    ".iso": "application/x-iso9660-image",
    ".dmg": "application/x-apple-diskimage",
    # --- Изображения (текстового слоя нет → OCR) ---
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".avif": "image/avif",
    ".jxl": "image/jxl",
    ".jp2": "image/jp2",
    ".j2k": "image/jp2",
    ".pnm": "image/x-portable-anymap",
    ".pbm": "image/x-portable-bitmap",
    ".pgm": "image/x-portable-graymap",
    ".ppm": "image/x-portable-pixmap",
    ".ico": "image/vnd.microsoft.icon",
}

# Сигнатура OOXML-документа внутри ZIP-контейнера.
# Нужна, чтобы отличать docx/xlsx/pptx, которые libmagic считает обычным zip.
_OOXML_WORD_MARK = b"word/document.xml"
_OOXML_XLSX_MARK = b"xl/workbook.xml"
_OOXML_PPTX_MARK = b"ppt/presentation.xml"


def _sniff_ooxml(head: bytes) -> Optional[str]:
    """Определяет конкретный OOXML-тип по содержимому начала ZIP-контейнера."""
    if _OOXML_WORD_MARK in head:
        return EXT_TO_MIME[".docx"]
    if _OOXML_XLSX_MARK in head:
        return EXT_TO_MIME[".xlsx"]
    if _OOXML_PPTX_MARK in head:
        return EXT_TO_MIME[".pptx"]
    return None


def _read_head(src: FileSource, n: int = 8192) -> bytes:
    if src.data is not None:
        return src.data[:n]
    if src.path:
        try:
            with open(src.path, "rb") as f:
                return f.read(n)
        except Exception:
            return b""
    return b""


class MagicMimeDetector(MimeDetector):
    """Определяет MIME-тип в три шага.

    1. Сигнатура OOXML внутри контейнера (docx/xlsx/pptx, которые libmagic
       часто отдаёт как ``application/zip``).
    2. libmagic по содержимому (если установлен ``python-magic``).
    3. Резерв — по расширению имени файла.

    Расширение приоритетнее, когда libmagic возвращает общий контейнерный тип
    (zip/octet-stream/plain), а имя файла говорит конкретнее (docx, epub, ...).
    """

    _GENERIC = {"application/octet-stream", "text/plain", "application/zip", "application/x-ole-storage"}

    def detect(self, src: FileSource) -> Optional[str]:
        head = _read_head(src)

        ooxml = _sniff_ooxml(head)
        if ooxml:
            return ooxml

        if magic is not None and (src.data is not None or src.path):
            try:
                m = magic.Magic(mime=True)
                detected = m.from_buffer(src.data) if src.data is not None else m.from_file(src.path)
                by_ext = self._by_ext(src)
                if detected in self._GENERIC and by_ext:
                    return by_ext
                if detected:
                    return detected
                return by_ext
            except Exception:
                pass

        return self._by_ext(src)

    @staticmethod
    def _by_ext(src: FileSource) -> Optional[str]:
        name = (src.filename or src.path or "").lower()
        # Двойные расширения архивов.
        if name.endswith(".tar.gz"):
            return "application/gzip"
        if name.endswith(".tar.bz2"):
            return "application/x-bzip2"
        if name.endswith(".tar.xz"):
            return "application/x-xz"
        _, ext = os.path.splitext(name)
        return EXT_TO_MIME.get(ext) if ext else None
