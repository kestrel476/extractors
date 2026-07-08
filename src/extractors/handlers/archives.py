"""
Архивы: ZIP, TAR(.gz/.bz2/.xz), а также (опционально) RAR и 7z.

Содержимое архива извлекается рекурсивно через переданный фасад: каждый
вложенный файл прогоняется тем же конвейером извлечения текста. Тексты файлов
объединяются с заголовками-именами.
"""

from __future__ import annotations

import io
import os
import tarfile
import zipfile
from typing import List, Optional, Tuple

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource

MAX_ARCHIVE_BYTES = 500 * 1024 * 1024     # 500 MB — лимит на размер архива
MAX_SINGLE_FILE_BYTES = 200 * 1024 * 1024  # 200 MB — лимит на один файл внутри
MAX_ENTRIES = 1000                          # защита от zip-бомб (число файлов)

# Файлы, которые нет смысла извлекать (служебные/бинарные мусорные).
_SKIP_PREFIXES = ("__MACOSX/", ".git/")
_SKIP_NAMES = (".DS_Store",)


class ArchiveExtractor(BaseExtractor):
    """Извлечение текста из архивов с рекурсивным обходом содержимого."""

    MIME_TYPES = frozenset(
        {
            "application/zip",
            "application/x-tar",
            "application/gzip",
            "application/x-gzip",
            "application/x-bzip2",
            "application/x-xz",
            "application/zstd",
            "application/x-lz4",
            "application/vnd.rar",
            "application/vnd.comicbook-rar",
            "application/x-7z-compressed",
            "application/vnd.ms-cab-compressed",
            "application/x-iso9660-image",
        }
    )
    EXTENSIONS = (
        ".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz",
        ".gz", ".bz2", ".xz", ".zst", ".lz4", ".rar", ".cbr", ".7z", ".cab", ".iso",
    )

    # Одиночные (не tar) сжатия: расширение -> функция-декомпрессор.
    _SINGLE_SUFFIXES = (".gz", ".bz2", ".xz", ".zst", ".lz4")

    def __init__(self, facade=None, max_files: int = 50, logger=None) -> None:
        super().__init__(logger=logger)
        self.facade = facade  # FileTextExtractor; задаётся в bootstrap
        self.max_files = max_files

    def can_handle(self, mime: Optional[str], filename: Optional[str]) -> bool:
        # В отличие от базового класса НЕ перехватываем файлы без имени.
        if mime and mime in self.MIME_TYPES:
            return True
        name = (filename or "").lower()
        return bool(name) and any(name.endswith(ext) for ext in self.EXTENSIONS)

    # --- основной метод ------------------------------------------------------

    def extract(self, src: FileSource) -> ExtractionResult:
        return self._extract(src, markdown=False)

    def extract_markdown(self, src: FileSource) -> ExtractionResult:
        """Распаковывает архив и обрабатывает вложенные файлы тем же md-конвейером."""
        return self._extract(src, markdown=True)

    def _extract(self, src: FileSource, *, markdown: bool) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение архива" + (" (Markdown)" if markdown else ""))
        if self.facade is None:
            return ExtractionResult.failure(
                "ArchiveExtractor requires a configured facade", code=ErrorCodes.ARCHIVE_ERROR
            )

        size = self._source_size(src)
        if size > MAX_ARCHIVE_BYTES:
            return ExtractionResult.failure(
                f"Archive too large: {size} bytes", code=ErrorCodes.TOO_LARGE
            )

        try:
            entries = self._read_entries(src)
        except _Encrypted:
            return ExtractionResult.failure("Encrypted archive", code=ErrorCodes.ARCHIVE_PASSWORD)
        except _UnsupportedArchive as e:
            return ExtractionResult.failure(str(e), code=ErrorCodes.ARCHIVE_ERROR)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.ARCHIVE_ERROR)

        if not entries:
            return ExtractionResult.failure(
                "No extractable files in archive", code=ErrorCodes.ARCHIVE_NO_CANDIDATE
            )

        parts: List[str] = []
        warnings: List[str] = []
        processed = 0
        for name, data in entries:
            if processed >= self.max_files:
                warnings.append(f"Truncated to {self.max_files} files")
                break
            if len(data) > MAX_SINGLE_FILE_BYTES:
                warnings.append(f"Skipped large entry '{name}'")
                continue
            base = os.path.basename(name)
            # Каждый вложенный файл прогоняется тем же конвейером фасада —
            # в md-режиме рекурсивно как Markdown, иначе как текст.
            res = self.facade.extract(FileSource(data=data, filename=base), markdown=markdown)
            text, err = res.text, res.error
            processed += 1
            if text:
                header = f"# {name}" if markdown else f"===== {name} ====="
                sep = "\n\n" if markdown else "\n"
                parts.append(f"{header}{sep}{text}")
            elif err:
                warnings.append(f"'{name}': {err}")

        meta = {"entries": str(len(entries))}
        if markdown:
            meta["format"] = "markdown"
        if not parts:
            return ExtractionResult.success(None, meta=meta, warnings=warnings)
        return ExtractionResult.success("\n\n".join(parts), meta=meta, warnings=warnings)

    # --- чтение записей ------------------------------------------------------

    def _read_entries(self, src: FileSource) -> List[Tuple[str, bytes]]:
        """Возвращает список (имя, байты) текстовых файлов архива."""
        name = (src.filename or "").lower()
        # ZIP
        if self._looks_like_zip(src):
            return self._read_zip(src)
        # RAR / CBR
        if name.endswith((".rar", ".cbr")) or src.mime in ("application/vnd.rar", "application/vnd.comicbook-rar"):
            return self._read_rar(src)
        # 7z
        if name.endswith(".7z") or src.mime == "application/x-7z-compressed":
            return self._read_7z(src)
        # CAB
        if name.endswith(".cab") or src.mime == "application/vnd.ms-cab-compressed":
            return self._read_cab(src)
        # ISO
        if name.endswith(".iso") or src.mime == "application/x-iso9660-image":
            return self._read_iso(src)
        # Одиночные сжатия (.gz/.bz2/.xz/.zst/.lz4), не являющиеся tar.
        if name.endswith(self._SINGLE_SUFFIXES) and not name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz")):
            try:
                return self._read_tar(src)  # вдруг это всё же tar без явного суффикса
            except tarfile.TarError:
                return self._read_single(src)
        # TAR (включая .tar.gz/.tgz/.tar.bz2/.tbz2/.tar.xz)
        try:
            return self._read_tar(src)
        except tarfile.TarError:
            pass
        raise _UnsupportedArchive("Unsupported archive format")

    def _read_zip(self, src: FileSource) -> List[Tuple[str, bytes]]:
        source = self.binary_source(src)
        with zipfile.ZipFile(source) as zf:
            if any((zi.flag_bits & 0x1) for zi in zf.infolist()):
                raise _Encrypted()
            out: List[Tuple[str, bytes]] = []
            for zi in zf.infolist()[:MAX_ENTRIES]:
                if zi.is_dir() or self._skip(zi.filename):
                    continue
                out.append((zi.filename, zf.read(zi)))
            return out

    def _read_tar(self, src: FileSource) -> List[Tuple[str, bytes]]:
        if src.data is not None:
            tf = tarfile.open(fileobj=io.BytesIO(src.data), mode="r:*")
        else:
            tf = tarfile.open(src.path, mode="r:*")
        with tf:
            out: List[Tuple[str, bytes]] = []
            for member in tf.getmembers()[:MAX_ENTRIES]:
                if not member.isfile() or self._skip(member.name):
                    continue
                fobj = tf.extractfile(member)
                if fobj is not None:
                    with fobj:
                        out.append((member.name, fobj.read()))
            return out

    def _read_rar(self, src: FileSource) -> List[Tuple[str, bytes]]:
        try:
            rarfile = self.require("rarfile")
        except ImportError as e:
            raise _UnsupportedArchive(str(e)) from e
        source = self.binary_source(src)
        with rarfile.RarFile(source) as rf:
            if rf.needs_password():
                raise _Encrypted()
            out: List[Tuple[str, bytes]] = []
            for info in rf.infolist()[:MAX_ENTRIES]:
                if info.is_dir() or self._skip(info.filename):
                    continue
                out.append((info.filename, rf.read(info)))
            return out

    def _read_7z(self, src: FileSource) -> List[Tuple[str, bytes]]:
        try:
            py7zr = self.require("py7zr")
        except ImportError as e:
            raise _UnsupportedArchive(str(e)) from e
        source = self.binary_source(src)
        with py7zr.SevenZipFile(source, mode="r") as zf:
            out: List[Tuple[str, bytes]] = []
            for name, bio in zf.readall().items():
                if self._skip(name):
                    continue
                out.append((name, bio.read()))
                if len(out) >= MAX_ENTRIES:
                    break
            return out

    def _read_single(self, src: FileSource) -> List[Tuple[str, bytes]]:
        """Распаковывает одиночный сжатый файл (.gz/.bz2/.xz/.zst/.lz4)."""
        name = (src.filename or "file").lower()
        raw = self.read_bytes(src)
        if name.endswith(".gz"):
            import gzip

            data = gzip.decompress(raw)
        elif name.endswith(".bz2"):
            import bz2

            data = bz2.decompress(raw)
        elif name.endswith(".xz"):
            import lzma

            data = lzma.decompress(raw)
        elif name.endswith(".zst"):
            zstd = self.require("zstandard", pip_name="zstandard")
            data = zstd.ZstdDecompressor().decompress(raw)
        elif name.endswith(".lz4"):
            lz4f = self.require("lz4.frame", pip_name="lz4")
            data = lz4f.decompress(raw)
        else:
            raise _UnsupportedArchive("Unknown single-file compression")
        # Имя внутреннего файла = имя архива без расширения сжатия.
        inner = os.path.basename(name)
        for suf in self._SINGLE_SUFFIXES:
            if inner.endswith(suf):
                inner = inner[: -len(suf)]
                break
        return [(inner or "content", data)]

    def _read_cab(self, src: FileSource) -> List[Tuple[str, bytes]]:
        try:
            cab = self.require("cabarchive", pip_name="cabarchive")
        except ImportError as e:
            raise _UnsupportedArchive(str(e)) from e
        raw = self.read_bytes(src)
        arc = cab.CabArchive(raw)
        out: List[Tuple[str, bytes]] = []
        for f in arc.values():
            if not self._skip(f.filename):
                out.append((f.filename, bytes(f.buf)))
            if len(out) >= MAX_ENTRIES:
                break
        return out

    def _read_iso(self, src: FileSource) -> List[Tuple[str, bytes]]:
        try:
            pycdlib = self.require("pycdlib", pip_name="pycdlib")
        except ImportError as e:
            raise _UnsupportedArchive(str(e)) from e
        iso = pycdlib.PyCdlib()
        if src.path:
            iso.open(src.path)
        else:
            iso.open_fp(io.BytesIO(self.read_bytes(src)))
        out: List[Tuple[str, bytes]] = []
        try:
            for dirname, _dirs, files in iso.walk(iso_path="/"):
                for fn in files:
                    full = dirname.rstrip("/") + "/" + fn
                    buf = io.BytesIO()
                    iso.get_file_from_iso_fp(buf, iso_path=full)
                    out.append((full.lstrip("/"), buf.getvalue()))
                    if len(out) >= MAX_ENTRIES:
                        return out
        finally:
            iso.close()
        return out

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _looks_like_zip(src: FileSource) -> bool:
        head = src.data[:4] if src.data is not None else b""
        if not head and src.path:
            try:
                with open(src.path, "rb") as f:
                    head = f.read(4)
            except OSError:
                return False
        return head[:2] == b"PK"

    @staticmethod
    def _skip(name: str) -> bool:
        norm = name.replace("\\", "/")
        if any(norm.startswith(p) for p in _SKIP_PREFIXES):
            return True
        return os.path.basename(norm) in _SKIP_NAMES

    @staticmethod
    def _source_size(src: FileSource) -> int:
        if src.data is not None:
            return len(src.data)
        try:
            return os.path.getsize(src.path) if src.path else 0
        except OSError:
            return 0


class _Encrypted(Exception):
    """Архив зашифрован."""


class _UnsupportedArchive(Exception):
    """Формат архива не поддержан / нет зависимости."""
