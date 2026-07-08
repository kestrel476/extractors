#!/usr/bin/env python3
"""
CLI сервиса извлечения текстового слоя.

Точка вызова сервиса `extractors`: принимает путь к файлу (или каталогу),
определяет формат, извлекает текст и печатает результат. Файлы без текстового
слоя (сканы, изображения) направляются в OCR (сейчас — заглушка).

Доступен как консольная команда ``extractors`` (после ``pip install``) и как
``python -m extractors``.

Примеры запуска
---------------
    # один файл, человекочитаемый вывод
    extractors document.pdf

    # содержимое в Markdown (таблицы сохраняются; удобно для LLM)
    extractors report.docx --md

    # полный результат в JSON (text, status, needs_ocr, meta, warnings)
    python -m extractors document.docx --json

    # все файлы в каталоге (рекурсивно), сводка по статусам
    extractors ./inbox --recursive

    # подробное логирование шагов конвейера
    extractors scan.pdf --verbose

Программное использование
-------------------------
    from extractors import build_default_extractor, FileSource
    service = build_default_extractor()
    result = service.extract(FileSource(path="document.pdf"), markdown=True)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from . import FileSource, build_default_extractor, get_logger


def _iter_files(target: Path, recursive: bool) -> List[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        globber = target.rglob("*") if recursive else target.glob("*")
        return sorted(p for p in globber if p.is_file())
    return []


def _print_human(path: Path, result, *, preview: int) -> None:
    print(f"\n=== {path} ===")
    print(f"status   : {result.status.value}")
    print(f"needs_ocr: {result.needs_ocr}")
    if result.meta:
        print(f"meta     : {result.meta}")
    if result.warnings:
        print(f"warnings : {result.warnings}")
    if result.error:
        print(f"error    : {result.error}")
    elif result.text:
        snippet = result.text if preview <= 0 else result.text[:preview]
        print("--- text ---")
        print(snippet + ("…" if preview > 0 and len(result.text) > preview else ""))
    else:
        print("(текст не извлечён)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="extractors",
        description="Извлечение текстового слоя из документов всех поддерживаемых форматов.",
    )
    parser.add_argument("target", help="Путь к файлу или каталогу")
    parser.add_argument("-r", "--recursive", action="store_true", help="Обходить каталог рекурсивно")
    parser.add_argument("--json", action="store_true", help="Вывести полный результат в JSON")
    parser.add_argument(
        "--md",
        "--markdown",
        dest="markdown",
        action="store_true",
        help="Читать документ в Markdown (сохраняет таблицы; для подачи в LLM)",
    )
    parser.add_argument("--preview", type=int, default=2000, help="Длина превью текста (0 — без ограничения)")
    parser.add_argument("--pdf-max-pages", type=int, default=None, help="Лимит страниц PDF")
    parser.add_argument("--verbose", action="store_true", help="Подробное логирование")
    args = parser.parse_args(argv)

    logger = None
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logger = get_logger(enabled=True)

    service = build_default_extractor(logger=logger, pdf_max_pages=args.pdf_max_pages)

    target = Path(args.target)
    files = _iter_files(target, args.recursive)
    if not files:
        print(f"Файл или каталог не найден: {target}", file=sys.stderr)
        return 2

    summary: dict[str, int] = {}
    json_items = []
    for path in files:
        try:
            result = service.extract(FileSource(path=str(path)), markdown=args.markdown)
        except Exception as e:  # noqa: BLE001 - не должно случаться, фасад изолирует ошибки
            print(f"{path}: непредвиденная ошибка: {e}", file=sys.stderr)
            summary["error"] = summary.get("error", 0) + 1
            continue

        summary[result.status.value] = summary.get(result.status.value, 0) + 1
        if args.json:
            json_items.append({"file": str(path), **result.model_dump()})
        else:
            _print_human(path, result, preview=args.preview)

    if args.json:
        out = json_items[0] if len(json_items) == 1 else json_items
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif len(files) > 1:
        print("\n=== Сводка ===")
        for status, count in sorted(summary.items()):
            print(f"  {status:14}: {count}")
        print(f"  {'всего':14}: {len(files)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
