"""
Вспомогательные функции для сборки Markdown.

Используются нативными md-рендерами (ODF, CSV/TSV, SQLite, колоночные данные),
когда markitdown формат не поддерживает, а сохранить табличную структуру нужно.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence


def md_escape(value: object) -> str:
    """Готовит значение ячейки к вставке в Markdown-таблицу.

    Экранирует символ ``|`` и схлопывает переводы строк, чтобы не сломать
    границы ячеек. ``None`` превращается в пустую строку.
    """
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", "<br>")
    return text.strip()


def md_table(headers: Sequence[object], rows: Iterable[Sequence[object]]) -> str:
    """Собирает GitHub-flavored Markdown-таблицу.

    Ширина таблицы определяется по самой широкой строке (заголовок или данные);
    недостающие ячейки дополняются пустыми, лишние — не отбрасываются, а
    расширяют таблицу. Если заголовков нет, генерируются ``col1..colN``.
    """
    materialized: List[List[str]] = [[md_escape(c) for c in row] for row in rows]
    ncols = max([len(headers)] + [len(r) for r in materialized] or [0])
    if ncols == 0:
        return ""

    head = [md_escape(h) for h in headers]
    if len(head) < ncols:
        head += [f"col{i + 1}" for i in range(len(head), ncols)]

    def _line(cells: Sequence[str]) -> str:
        padded = list(cells) + [""] * (ncols - len(cells))
        return "| " + " | ".join(padded[:ncols]) + " |"

    lines = [_line(head), "| " + " | ".join(["---"] * ncols) + " |"]
    lines.extend(_line(r) for r in materialized)
    return "\n".join(lines)


def df_to_md(df, *, index: bool = False) -> str:
    """Сериализует pandas.DataFrame в Markdown-таблицу без зависимости от tabulate."""
    headers: List[object] = []
    if index:
        headers.append(df.index.name or "")
    headers.extend(list(df.columns))

    rows: List[List[object]] = []
    for idx, (_, row) in enumerate(df.iterrows()):
        cells: List[object] = []
        if index:
            cells.append(df.index[idx])
        cells.extend(row.tolist())
        rows.append(cells)
    return md_table(headers, rows)


def md_section(title: Optional[str], body: str, *, level: int = 2) -> str:
    """Оборачивает блок в Markdown-заголовок (если ``title`` задан)."""
    body = (body or "").strip()
    if not title:
        return body
    prefix = "#" * max(1, min(level, 6))
    heading = f"{prefix} {title.strip()}"
    return f"{heading}\n\n{body}" if body else heading
