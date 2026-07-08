"""
Запуск через ``python -m extractors`` — делегирует единому CLI (:mod:`extractors.cli`).
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
