"""Тест запуска пакета как модуля: python -m extractors."""
from __future__ import annotations

import subprocess
import sys


def test_main_module_importable():
    # Импорт модуля выполняет `from .cli import main` (in-process, для coverage).
    import extractors.__main__ as m
    assert callable(m.main)


def test_python_m_extractors(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello module", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "extractors", str(f)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "status" in proc.stdout
    assert "hello module" in proc.stdout


def test_python_m_extractors_missing_path_returns_2(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "extractors", str(tmp_path / "nope.txt")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2
