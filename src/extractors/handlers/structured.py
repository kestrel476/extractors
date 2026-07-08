"""
Структурированные текстовые форматы: JSON / JSONL и YAML.

Извлекаются строковые значения (и ключи) — то, что несёт смысловой текст.
Числа и булевы значения опускаются, чтобы не засорять результат.
"""

from __future__ import annotations

import json
from typing import Any, List

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


def _walk(node: Any, out: List[str]) -> None:
    """Рекурсивно собирает строковые значения и ключи из дерева JSON/YAML."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and k.strip():
                out.append(k.strip())
            _walk(v, out)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk(item, out)
    elif isinstance(node, str):
        if node.strip():
            out.append(node.strip())


class JsonExtractor(BaseExtractor):
    """Извлечение текстовых значений из JSON и JSONL/NDJSON."""

    MIME_TYPES = frozenset({"application/json", "text/json"})
    EXTENSIONS = (".json", ".jsonl", ".ndjson")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение JSON")
        try:
            text, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        out: List[str] = []
        name = (src.filename or "").lower()
        try:
            if name.endswith((".jsonl", ".ndjson")):
                for line in text.splitlines():
                    line = line.strip()
                    if line:
                        _walk(json.loads(line), out)
            else:
                _walk(json.loads(text), out)
        except json.JSONDecodeError as e:
            return ExtractionResult.failure(f"Invalid JSON: {e}", code=ErrorCodes.PARSE_ERROR, meta={"encoding": enc})

        return ExtractionResult.success("\n".join(out), meta={"encoding": enc}, warnings=warnings)


class YamlExtractor(BaseExtractor):
    """Извлечение текстовых значений из YAML (требует PyYAML)."""

    MIME_TYPES = frozenset({"application/x-yaml", "text/yaml", "application/yaml"})
    EXTENSIONS = (".yaml", ".yml")

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение YAML")
        try:
            text, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)

        # YAML человекочитаем: без PyYAML возвращаем сырой текст (мягкая деградация).
        try:
            yaml = self.require("yaml", pip_name="PyYAML")
        except ImportError:
            warnings = list(warnings) + ["PyYAML недоступен: возвращён сырой текст"]
            return ExtractionResult.success(text.strip(), meta={"encoding": enc}, warnings=warnings)

        out: List[str] = []
        try:
            for doc in yaml.safe_load_all(text):
                _walk(doc, out)
        except Exception as e:  # noqa: BLE001 - yaml.YAMLError и пр.
            return ExtractionResult.failure(f"Invalid YAML: {e}", code=ErrorCodes.PARSE_ERROR, meta={"encoding": enc})

        return ExtractionResult.success("\n".join(out), meta={"encoding": enc}, warnings=warnings)
