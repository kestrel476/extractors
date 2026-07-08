"""Тесты helper'ов сборки Markdown (handlers/_markdown.py)."""
from __future__ import annotations

import pytest

from extractors.handlers._markdown import df_to_md, md_escape, md_section, md_table


# ── md_escape ──────────────────────────────────────────────────────────────
def test_md_escape_none_is_empty():
    assert md_escape(None) == ""


def test_md_escape_pipe_and_backslash():
    assert md_escape("a|b") == r"a\|b"
    assert md_escape("c\\d") == "c\\\\d"


def test_md_escape_newlines():
    assert md_escape("line1\nline2") == "line1<br>line2"
    # \r\n схлопывается в пробел (обрабатывается раньше одиночного \n).
    assert md_escape("a\r\nb") == "a b"


def test_md_escape_stringifies_numbers():
    assert md_escape(42) == "42"


# ── md_table ─────────────────────────────────────────────────────────────
def test_md_table_basic():
    out = md_table(["A", "B"], [["1", "2"], ["3", "4"]])
    lines = out.splitlines()
    assert lines[0] == "| A | B |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 2 |"
    assert lines[3] == "| 3 | 4 |"


def test_md_table_empty_returns_empty_string():
    assert md_table([], []) == ""


def test_md_table_ragged_rows_widen_and_pad():
    out = md_table(["A"], [["1", "2", "3"], ["x"]])
    lines = out.splitlines()
    # ширина = 3 (по самой широкой строке); заголовок дополнен col2/col3
    assert lines[0] == "| A | col2 | col3 |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| 1 | 2 | 3 |"
    assert lines[3] == "| x |  |  |"


def test_md_table_escapes_cells():
    out = md_table(["A|B"], [["c|d"]])
    assert r"A\|B" in out
    assert r"c\|d" in out


# ── df_to_md ─────────────────────────────────────────────────────────────
def test_df_to_md():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    out = df_to_md(df)
    lines = out.splitlines()
    assert lines[0] == "| x | y |"
    assert "| 1 | a |" in out
    assert "| 2 | b |" in out


def test_df_to_md_with_index():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"x": [10]}, index=["r0"])
    out = df_to_md(df, index=True)
    assert "r0" in out
    assert "| 10 |" in out.replace("  ", " ")


# ── md_section ─────────────────────────────────────────────────────────────
def test_md_section_with_title():
    assert md_section("Title", "body").startswith("## Title\n\nbody")


def test_md_section_without_title_returns_body():
    assert md_section(None, "just body") == "just body"
    assert md_section("", "just body") == "just body"


def test_md_section_level_clamped():
    assert md_section("T", "b", level=99).startswith("###### T")
    assert md_section("T", "b", level=0).startswith("# T")


def test_md_section_title_only_when_body_empty():
    assert md_section("T", "") == "## T"
