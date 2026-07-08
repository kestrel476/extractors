"""
Тесты CLI :func:`extractors.cli.main`.

``main`` вызывается напрямую со списком argv; вывод перехватывается ``capsys``.
"""
from __future__ import annotations

import json

from extractors.cli import main


def test_text_mode_returns_zero(tmp_path, capsys):
    p = tmp_path / "note.txt"
    p.write_text("hello", encoding="utf-8")
    rc = main([str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "status" in out
    assert "hello" in out


def test_json_mode_single_file(tmp_path, capsys):
    p = tmp_path / "note.txt"
    p.write_text("hello", encoding="utf-8")
    rc = main([str(p), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)          # валидный JSON
    assert isinstance(data, dict)   # один файл → объект, не список
    assert data["file"] == str(p)
    assert data["status"] == "ok"
    assert data["text"] == "hello"


def test_md_mode(tmp_path, capsys):
    p = tmp_path / "table.csv"
    p.write_text("Region,Sales\nNorth,1200\n", encoding="utf-8")
    rc = main([str(p), "--md"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "|" in out          # markdown-таблица
    assert "Region" in out


def test_markdown_long_alias(tmp_path, capsys):
    p = tmp_path / "table.csv"
    p.write_text("Region,Sales\nNorth,1200\n", encoding="utf-8")
    rc = main([str(p), "--markdown"])
    assert rc == 0
    assert "|" in capsys.readouterr().out


def test_directory_recursive_summary(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("beta", encoding="utf-8")
    rc = main([str(tmp_path), "--recursive"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Сводка" in out
    assert "всего" in out


def test_directory_non_recursive_skips_subdir(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "c.txt").write_text("gamma", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("beta", encoding="utf-8")
    rc = main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "a.txt" in out
    assert "c.txt" in out
    assert "b.txt" not in out


def test_directory_json_returns_list(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta", encoding="utf-8")
    rc = main([str(tmp_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 2


def test_nonexistent_path_returns_two(tmp_path, capsys):
    missing = tmp_path / "nope" / "missing12345.txt"
    rc = main([str(missing)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "не найден" in err


def test_preview_truncates(tmp_path, capsys):
    p = tmp_path / "big.txt"
    p.write_text("x" * 100, encoding="utf-8")
    rc = main([str(p), "--preview", "10"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "…" in out  # многоточие обрезки


def test_verbose_runs(tmp_path, capsys):
    p = tmp_path / "note.txt"
    p.write_text("hello", encoding="utf-8")
    rc = main([str(p), "--verbose"])
    assert rc == 0
    assert "hello" in capsys.readouterr().out
