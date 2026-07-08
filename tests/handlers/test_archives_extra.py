"""Доп. покрытие ArchiveExtractor: 7z, одиночные сжатия, tar, источник-путь."""
from __future__ import annotations

import bz2
import gzip
import io
import lzma
import tarfile

import pytest

from extractors import FileSource

CONTENT = b"Region: North\nSales: 1200\n"


def _extract(svc, data, filename):
    return svc.extract(FileSource(data=data, filename=filename))


def test_single_gzip(svc):
    data = gzip.compress(CONTENT)
    r = _extract(svc, data, "notes.txt.gz")
    assert r.status.value == "ok"
    assert "Region" in r.text


def test_single_bz2(svc):
    r = _extract(svc, bz2.compress(CONTENT), "notes.txt.bz2")
    assert r.status.value == "ok" and "Sales" in r.text


def test_single_xz(svc):
    r = _extract(svc, lzma.compress(CONTENT), "notes.txt.xz")
    assert r.status.value == "ok" and "North" in r.text


def test_single_zstd(svc):
    zstd = pytest.importorskip("zstandard")
    data = zstd.ZstdCompressor().compress(CONTENT)
    r = _extract(svc, data, "notes.txt.zst")
    assert r.status.value == "ok" and "Region" in r.text


def test_single_lz4(svc):
    lz4f = pytest.importorskip("lz4.frame")
    r = _extract(svc, lz4f.compress(CONTENT), "notes.txt.lz4")
    assert r.status.value == "ok" and "Region" in r.text


def test_tar_gz(svc):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo("a.txt")
        info.size = len(CONTENT)
        tf.addfile(info, io.BytesIO(CONTENT))
    r = _extract(svc, buf.getvalue(), "bundle.tar.gz")
    assert r.status.value == "ok"
    assert "a.txt" in r.text and "Region" in r.text


def _sevenzip_supported() -> bool:
    """Хендлер читает 7z через SevenZipFile.readall() (есть в py7zr>=0.21)."""
    py7zr = pytest.importorskip("py7zr")
    return hasattr(py7zr.SevenZipFile, "readall")


def test_sevenzip(svc):
    py7zr = pytest.importorskip("py7zr")
    if not _sevenzip_supported():
        pytest.skip("установленный py7zr не имеет readall() (нестандартная сборка)")
    buf = io.BytesIO()
    with py7zr.SevenZipFile(buf, "w") as z:
        z.writestr(CONTENT.decode(), "a.txt")
    r = _extract(svc, buf.getvalue(), "bundle.7z")
    assert r.status.value == "ok"
    assert "Region" in r.text


def test_archive_from_path(svc, tmp_path):
    # Ветка чтения размера/содержимого из пути (а не из байтов).
    import zipfile

    p = tmp_path / "bundle.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("a.txt", CONTENT.decode())
    r = svc.extract(FileSource(path=str(p)))
    assert r.status.value == "ok" and "Region" in r.text


def test_iso_image(svc):
    pycdlib = pytest.importorskip("pycdlib")
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge="1.09")
    payload = CONTENT
    iso.add_fp(io.BytesIO(payload), len(payload), "/A.TXT;1", rr_name="a.txt")
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()
    r = _extract(svc, out.getvalue(), "disk.iso")
    assert r.status.value == "ok"
    assert "Region" in r.text


def test_encrypted_zip_password(svc):
    pyzipper = pytest.importorskip("pyzipper")
    buf = io.BytesIO()
    with pyzipper.AESZipFile(buf, "w", encryption=pyzipper.WZ_AES) as z:
        z.setpassword(b"secret")
        z.writestr("a.txt", "secret data")
    r = svc.extract(FileSource(data=buf.getvalue(), filename="enc.zip"))
    assert r.failed
    assert r.meta["code"] == "ARCHIVE_PASSWORD"


def test_seven_zip_markdown_recursion(svc):
    py7zr = pytest.importorskip("py7zr")
    if not _sevenzip_supported():
        pytest.skip("установленный py7zr не имеет readall() (нестандартная сборка)")
    buf = io.BytesIO()
    with py7zr.SevenZipFile(buf, "w") as z:
        z.writestr("a,b\n1,2\n", "data.csv")
    r = svc.extract(FileSource(data=buf.getvalue(), filename="b.7z"), markdown=True)
    assert r.status.value == "ok"
    assert r.meta.get("format") == "markdown"
    assert "| a | b |" in r.text
