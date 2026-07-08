"""
Простой текст, исходный код, конфиги, разметка, субтитры, переводы.

Файлы читаются как текст с автоопределением кодировки. Содержимое не
интерпретируется — это «сырой» текст, что корректно для plain-text форматов.
Это самый «широкий» хендлер, поэтому в реестре он регистрируется последним.
"""

from __future__ import annotations

from .base import BaseExtractor
from ..errors import ErrorCodes
from ..types import ExtractionResult, FileSource


class PlainTextExtractor(BaseExtractor):
    """Извлечение текста из plain-text форматов (код, разметка, конфиги, субтитры)."""

    MIME_TYPES = frozenset(
        {
            "text/plain",
            "text/markdown",
            "text/vtt",
            "text/x-rst",
            "text/x-tex",
            "text/x-python",
            "text/javascript",
            "text/x-typescript",
            "text/x-java",
            "text/x-c",
            "text/x-c++",
            "text/x-csharp",
            "text/x-go",
            "text/x-rust",
            "text/x-ruby",
            "text/x-php",
            "text/x-swift",
            "text/x-kotlin",
            "text/x-scala",
            "text/x-r",
            "text/x-objcsrc",
            "text/x-lua",
            "text/x-perl",
            "text/x-elixir",
            "text/x-erlang",
            "text/x-haskell",
            "text/x-clojure",
            "text/x-dart",
            "text/x-gettext-translation",
            "application/x-sh",
            "application/sql",
            "application/toml",
            "application/graphql",
        }
    )
    EXTENSIONS = (
        # текст и разметка
        ".txt", ".text", ".log", ".nfo", ".me", ".1st",
        ".md", ".markdown", ".rst", ".asciidoc", ".adoc", ".org",
        ".tex", ".latex", ".rmd", ".qmd",
        # конфиги
        ".ini", ".cfg", ".conf", ".env", ".properties", ".toml",
        # исходный код
        ".py", ".rs", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
        ".java", ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".cs", ".go", ".rb", ".php",
        ".swift", ".kt", ".kts", ".scala", ".r", ".m", ".lua",
        ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".pl", ".pm",
        ".ex", ".exs", ".erl", ".hrl", ".hs", ".lhs", ".clj", ".cljs",
        ".sql", ".graphql", ".gql", ".proto", ".dart",
        # субтитры / локализация / тексты
        ".srt", ".vtt", ".ass", ".ssa", ".sub", ".lrc", ".po", ".pot", ".strings",
        # прочая текстовая разметка
        ".dtd",
    )

    def extract(self, src: FileSource) -> ExtractionResult:
        self.logger.log("DOC_EXTRACTION", "Извлечение plain-text")
        try:
            text, enc, warnings = self.read_text(src)
        except Exception as e:  # noqa: BLE001
            self.logger.log("DOC_EXTRACTION_ERROR", f"Ошибка чтения текста: {e}")
            return ExtractionResult.failure(str(e), code=ErrorCodes.READ_ERROR)
        return ExtractionResult.success(text.strip(), meta={"encoding": enc}, warnings=warnings)
