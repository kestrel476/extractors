"""Тесты хендлера архивов (zip/tar = stdlib; rar/7z опционально)."""
from __future__ import annotations

import io
import tarfile
import zipfile

import pytest

from extractors import FileSource, build_default_extractor
from extractors.errors import ErrorCodes
from extractors.handlers.archives import ArchiveExtractor


@pytest.fixture
def arc(svc):
    return ArchiveExtractor(facade=svc)


# ── can_handle (без зависимостей) ────────────────────────────────────────────
def test_can_handle_mime():
    ex = ArchiveExtractor()
    assert ex.can_handle("application/zip", None)
    assert ex.can_handle("application/x-tar", None)
    assert ex.can_handle("application/x-7z-compressed", None)


def test_can_handle_extension():
    ex = ArchiveExtractor()
    for name in ("a.zip", "a.tar", "a.tar.gz", "a.tgz", "a.7z", "a.rar", "a.gz"):
        assert ex.can_handle(None, name)
    assert not ex.can_handle(None, "a.txt")


def test_can_handle_ignores_nameless():
    ex = ArchiveExtractor()
    assert not ex.can_handle(None, None)


# ── zip: текст и markdown ────────────────────────────────────────────────────
def test_zip_extract_text(arc, zip_bytes):
    res = arc.extract(FileSource(data=zip_bytes, filename="a.zip"))
    assert res.ok
    assert "===== q1/sales.csv =====" in res.text
    assert "Region" in res.text
    assert "Quarterly Report" in res.text
    assert res.meta.get("entries") == "2"


def test_zip_extract_markdown(arc, zip_bytes):
    res = arc.extract_markdown(FileSource(data=zip_bytes, filename="a.zip"))
    assert res.ok
    assert res.meta.get("format") == "markdown"
    assert "# q1/sales.csv" in res.text
    assert "# notes/readme.md" in res.text


# ── tar ──────────────────────────────────────────────────────────────────────
def test_tar_extract_text(arc):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        payload = b"Region,Sales\nNorth,1200\n"
        info = tarfile.TarInfo("data.csv")
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))
    res = arc.extract(FileSource(data=buf.getvalue(), filename="a.tar"))
    assert res.ok and "Region" in res.text


# ── ветки ошибок ─────────────────────────────────────────────────────────────
def test_no_facade_error(zip_bytes):
    ex = ArchiveExtractor(facade=None)
    res = ex.extract(FileSource(data=zip_bytes, filename="a.zip"))
    assert res.failed and res.meta["code"] == ErrorCodes.ARCHIVE_ERROR


def test_empty_archive_no_candidate(arc):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass
    res = arc.extract(FileSource(data=buf.getvalue(), filename="empty.zip"))
    assert res.failed and res.meta["code"] == ErrorCodes.ARCHIVE_NO_CANDIDATE


def test_unsupported_archive_error(arc):
    res = arc.extract(FileSource(data=b"this is not any archive", filename="x.zip"))
    assert res.failed and res.meta["code"] == ErrorCodes.ARCHIVE_ERROR


def test_encrypted_zip_password(arc):
    pyzipper = pytest.importorskip("pyzipper")
    buf = io.BytesIO()
    with pyzipper.AESZipFile(buf, "w", encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(b"secret")
        zf.writestr("secret.txt", "hidden")
    res = arc.extract(FileSource(data=buf.getvalue(), filename="enc.zip"))
    assert res.failed and res.meta["code"] == ErrorCodes.ARCHIVE_PASSWORD


def test_too_large(monkeypatch, arc, zip_bytes):
    import extractors.handlers.archives as mod

    monkeypatch.setattr(mod, "MAX_ARCHIVE_BYTES", 1)
    res = arc.extract(FileSource(data=zip_bytes, filename="a.zip"))
    assert res.failed and res.meta["code"] == ErrorCodes.TOO_LARGE


def test_max_files_truncation(svc):
    ex = ArchiveExtractor(facade=svc, max_files=1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.txt", "alpha content")
        z.writestr("b.txt", "beta content")
    res = ex.extract(FileSource(data=buf.getvalue(), filename="a.zip"))
    assert res.ok
    assert any("Truncated" in w for w in res.warnings)


def test_single_gzip(arc):
    import gzip

    payload = b"Region,Sales\nNorth,1200\n"
    data = gzip.compress(payload)
    res = arc.extract(FileSource(data=data, filename="sales.csv.gz"))
    assert res.ok and "Region" in res.text
