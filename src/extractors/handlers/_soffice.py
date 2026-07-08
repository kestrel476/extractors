"""
Конвертация устаревших бинарных форматов через headless LibreOffice (soffice).

Используется для .doc → .docx и .ppt → .pptx, когда нет нативной Python-библиотеки.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from typing import Optional

from ..types import FileSource


class SofficeError(RuntimeError):
    """Ошибка конвертации через LibreOffice."""


def _materialize(src: FileSource, suffix: str) -> tuple[str, bool]:
    """Возвращает путь к исходному файлу на диске и флаг «это временный файл»."""
    if src.path:
        return src.path, False
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(src.data or b"")
    return tmp, True


def convert(src: FileSource, *, in_suffix: str, to_format: str, timeout: int = 120) -> bytes:
    """Конвертирует источник в ``to_format`` и возвращает байты результата.

    Args:
        src: Источник файла.
        in_suffix: Расширение исходного файла (например, ``.doc``).
        to_format: Целевой формат LibreOffice (например, ``docx``).
        timeout: Таймаут процесса в секундах.

    Raises:
        SofficeError: LibreOffice не установлен, упал или не создал выходной файл.
    """
    in_path, in_is_tmp = _materialize(src, in_suffix)
    out_dir = tempfile.mkdtemp(prefix="soffice_")
    try:
        try:
            proc = subprocess.run(
                ["soffice", "--headless", "--convert-to", to_format, "--outdir", out_dir, in_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as e:
            raise SofficeError(
                "LibreOffice (soffice) не установлен. Установите: apt-get install libreoffice"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise SofficeError(f"Таймаут конвертации LibreOffice ({timeout}s)") from e

        if proc.returncode != 0:
            raise SofficeError(proc.stderr.decode("utf-8", errors="ignore") or "soffice failed")

        base = os.path.splitext(os.path.basename(in_path))[0]
        out_path = os.path.join(out_dir, f"{base}.{to_format}")
        if not os.path.exists(out_path):
            # Имя могло разойтись — берём единственный созданный файл.
            produced = [os.path.join(out_dir, n) for n in os.listdir(out_dir)]
            if not produced:
                raise SofficeError("LibreOffice не создал выходной файл")
            out_path = produced[0]
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        if in_is_tmp:
            _safe_unlink(in_path)
        _safe_rmtree(out_dir)


def _safe_unlink(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        try:
            os.unlink(path)
        except OSError:
            pass


def _safe_rmtree(path: Optional[str]) -> None:
    if not path or not os.path.isdir(path):
        return
    import shutil

    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass
