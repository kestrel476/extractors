"""Тесты структурированных форматов: JsonExtractor и YamlExtractor."""
from __future__ import annotations

import json

import pytest

from conftest import source
from extractors import ExtractionStatus, FileSource
from extractors.handlers.structured import JsonExtractor, YamlExtractor


# ── JSON ────────────────────────────────────────────────────────────────────

@pytest.fixture
def jext():
    return JsonExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("application/json", None),
        ("text/json", None),
        (None, "a.json"),
        (None, "a.jsonl"),
        (None, "a.ndjson"),
    ],
)
def test_json_can_handle_true(jext, mime, filename):
    assert jext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.yaml")])
def test_json_can_handle_false(jext, mime, filename):
    assert jext.can_handle(mime, filename) is False


def test_json_extract_string_values_and_keys(jext, json_bytes):
    res = jext.extract(source(json_bytes, "a.json"))
    assert res.status is ExtractionStatus.OK
    text = res.text
    # ключи и строковые значения извлечены
    assert "title" in text
    assert "Quarterly Report" in text
    assert "Region" in text
    assert "North" in text


def test_json_omits_non_string_scalars(jext):
    data = json.dumps({"name": "Bob", "age": 42, "active": True, "score": 3.14}).encode()
    res = jext.extract(source(data, "a.json"))
    lines = res.text.splitlines()
    assert "name" in lines
    assert "Bob" in lines
    # числа/булевы не попадают в вывод
    assert "42" not in lines
    assert "True" not in lines
    assert "3.14" not in lines


def test_jsonl_lines(jext):
    data = b'{"a": "one"}\n{"a": "two"}\n'
    res = jext.extract(source(data, "a.jsonl"))
    assert res.text == "a\none\na\ntwo"


def test_json_invalid_returns_failure(jext):
    res = jext.extract(source(b"{ not valid json", "a.json"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "PARSE_ERROR"
    assert "Invalid JSON" in res.error


def test_json_read_error(jext):
    res = jext.extract(FileSource(path="/nonexistent/x.json"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "READ_ERROR"


# ── YAML ────────────────────────────────────────────────────────────────────

@pytest.fixture
def yext():
    return YamlExtractor()


@pytest.mark.parametrize(
    "mime,filename",
    [
        ("application/x-yaml", None),
        ("text/yaml", None),
        ("application/yaml", None),
        (None, "a.yaml"),
        (None, "a.yml"),
    ],
)
def test_yaml_can_handle_true(yext, mime, filename):
    assert yext.can_handle(mime, filename) is True


@pytest.mark.parametrize("mime,filename", [("text/plain", "a.txt"), (None, "a.json")])
def test_yaml_can_handle_false(yext, mime, filename):
    assert yext.can_handle(mime, filename) is False


def test_yaml_extract_values(yext):
    pytest.importorskip("yaml")
    data = b"title: Hello\nnum: 3\nitems:\n  - one\n  - two\n"
    res = yext.extract(source(data, "a.yaml"))
    assert res.status is ExtractionStatus.OK
    lines = res.text.splitlines()
    assert "title" in lines
    assert "Hello" in lines
    assert "one" in lines and "two" in lines
    # число опущено
    assert "3" not in lines


def test_yaml_invalid_returns_failure(yext):
    pytest.importorskip("yaml")
    res = yext.extract(source(b"a: [1, 2\nb: {", "a.yaml"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "PARSE_ERROR"
    assert "Invalid YAML" in res.error


def test_yaml_graceful_fallback_without_pyyaml(yext, monkeypatch):
    """Без PyYAML возвращается сырой текст с предупреждением (мягкая деградация)."""

    def _no_yaml(*args, **kwargs):
        raise ImportError("PyYAML недоступен")

    monkeypatch.setattr(yext, "require", _no_yaml)
    data = b"title: Hello\nnum: 3\n"
    res = yext.extract(source(data, "a.yaml"))
    assert res.status is ExtractionStatus.OK
    assert res.text == "title: Hello\nnum: 3"
    assert any("PyYAML" in w for w in res.warnings)


def test_yaml_read_error(yext):
    res = yext.extract(FileSource(path="/nonexistent/x.yaml"))
    assert res.status is ExtractionStatus.ERROR
    assert res.meta["code"] == "READ_ERROR"
