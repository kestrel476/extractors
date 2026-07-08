"""
Форматы с ограниченной поддержкой («best-effort»):

- DjVu (.djvu/.djv) — текстовый слой через CLI ``djvutxt`` (пакет djvulibre).
- PostScript (.ps/.eps/.ai) — текст через Ghostscript (``gs -sDEVICE=txtwrite``);
  для .ai дополнительно пробуем MuPDF (часто PDF-совместим).
- Photoshop (.psd) — текстовые слои через библиотеку ``psd-tools``.

Если нужный внешний инструмент/библиотека недоступны — возвращается понятный
код (``DEPENDENCY_MISSING``) либо ``NO_TEXT_LAYER`` (кандидат на OCR).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List, Optional

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


def _to_tempfile(src: FileSource, suffix: str) -> tuple[str, bool]:
    if src.path:
        return src.path, False
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(src.data or b"")
    return tmp, True


class DjvuExtractor(BaseExtractor):
    """Извлечение текстового слоя DjVu через CLI djvutxt."""

    MIME_TYPES = frozenset({"image/vnd.djvu", "image/x-djvu"})
    EXTENSIONS = (".djvu", ".djv")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение DjVu")
        path, is_tmp = _to_tempfile(src, ".djvu")
        try:
            proc = subprocess.run(
                ["djvutxt", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False
            )
        except FileNotFoundError:
            self.logger.log("DOC_EXTRACTION", "djvutxt не найден → OCR")
            return ExtractionResult.no_text_layer(
                meta={"note": "djvutxt (djvulibre) не установлен; нужен рендер+OCR"}
            )
        except subprocess.TimeoutExpired:
            return ExtractionResult.failure("djvutxt timeout", code=ErrorCodes.READ_ERROR)
        finally:
            if is_tmp and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

        text = proc.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            return ExtractionResult.no_text_layer(meta={"note": "DjVu без текстового слоя"})
        return ExtractionResult.success(text)


class PostScriptExtractor(BaseExtractor):
    """Извлечение текста из PostScript/EPS/AI через Ghostscript (и MuPDF для .ai)."""

    MIME_TYPES = frozenset({"application/postscript", "application/eps"})
    EXTENSIONS = (".ps", ".eps", ".ai")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение PostScript/EPS/AI")
        # .ai часто PDF-совместим — пробуем MuPDF.
        if src.ext == ".ai":
            try:
                fitz = self.require("fitz", pip_name="PyMuPDF")
                doc = fitz.open(stream=src.data, filetype="pdf") if src.data is not None else fitz.open(src.path)
                chunks = [p.get_text() for p in doc if p.get_text().strip()]
                doc.close()
                if chunks:
                    return ExtractionResult.success("\n\n".join(chunks), meta={"engine": "mupdf"})
            except Exception:  # noqa: BLE001 - не PDF-совместимый .ai, пойдём через gs
                pass

        path, is_tmp = _to_tempfile(src, src.ext or ".ps")
        try:
            proc = subprocess.run(
                ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=txtwrite", "-sOutputFile=-", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
            )
        except FileNotFoundError:
            return ExtractionResult.failure(
                "Ghostscript (gs) не установлен; PostScript-текст недоступен",
                code=ErrorCodes.DEPENDENCY_MISSING,
            )
        except subprocess.TimeoutExpired:
            return ExtractionResult.failure("ghostscript timeout", code=ErrorCodes.READ_ERROR)
        finally:
            if is_tmp and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

        text = proc.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            return ExtractionResult.no_text_layer(meta={"note": "PostScript без извлекаемого текста"})
        return ExtractionResult.success(text, meta={"engine": "ghostscript"})


class PsdExtractor(BaseExtractor):
    """Извлечение текстовых слоёв Photoshop (.psd) через psd-tools."""

    MIME_TYPES = frozenset({"image/vnd.adobe.photoshop", "application/x-photoshop"})
    EXTENSIONS = (".psd",)

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение PSD (текстовые слои)")
        try:
            psd_tools = self.require("psd_tools", pip_name="psd-tools")
        except ImportError as e:
            return self.dependency_error(e)

        import io

        try:
            source = io.BytesIO(src.data) if src.data is not None else src.path
            psd = psd_tools.PSDImage.open(source)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        parts: List[str] = []

        def walk(layers) -> None:
            for layer in layers:
                if getattr(layer, "is_group", lambda: False)():
                    walk(layer)
                    continue
                kind = getattr(layer, "kind", None)
                if kind == "type":
                    txt = getattr(layer, "text", None)
                    if txt and txt.strip():
                        parts.append(txt.strip())

        try:
            walk(psd)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        if not parts:
            # Текстовых слоёв нет — изображение можно распознать через OCR.
            return ExtractionResult.no_text_layer(meta={"note": "PSD без текстовых слоёв"})
        return ExtractionResult.success("\n".join(parts))
