"""Доп. покрытие OpenDocument: ODS/ODT через настоящий odfpy (текст + Markdown)."""
from __future__ import annotations

import pytest

from extractors import FileSource

odf_opendocument = pytest.importorskip("odf.opendocument")


def _ods_bytes(tmp_path):
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    table = Table(name="Sales")
    for row in [["Region", "Sales"], ["North", "1200"], ["South", "980"]]:
        tr = TableRow()
        for val in row:
            tc = TableCell()
            tc.addElement(P(text=val))
            tr.addElement(tc)
        table.addElement(tr)
    doc.spreadsheet.addElement(table)
    p = tmp_path / "report.ods"
    doc.save(str(p))
    return p.read_bytes()


def _odt_bytes(tmp_path):
    from odf.opendocument import OpenDocumentText
    from odf.table import Table, TableCell, TableRow
    from odf.text import H, P

    doc = OpenDocumentText()
    doc.text.addElement(H(outlinelevel=1, text="Report"))
    doc.text.addElement(P(text="Intro paragraph."))
    table = Table(name="T1")
    for row in [["A", "B"], ["1", "2"]]:
        tr = TableRow()
        for val in row:
            tc = TableCell()
            tc.addElement(P(text=val))
            tr.addElement(tc)
        table.addElement(tr)
    doc.text.addElement(table)
    p = tmp_path / "report.odt"
    doc.save(str(p))
    return p.read_bytes()


def test_ods_text(svc, tmp_path):
    r = svc.extract(FileSource(data=_ods_bytes(tmp_path), filename="report.ods"))
    assert r.status.value == "ok"
    assert "North" in r.text and "1200" in r.text


def test_ods_markdown_table(svc, tmp_path):
    r = svc.extract(FileSource(data=_ods_bytes(tmp_path), filename="report.ods"), markdown=True)
    assert r.status.value == "ok"
    assert r.meta.get("format") == "markdown"
    assert "| Region | Sales |" in r.text
    assert "| --- | --- |" in r.text
    assert "| North | 1200 |" in r.text


def test_odt_markdown_heading_and_table(svc, tmp_path):
    r = svc.extract(FileSource(data=_odt_bytes(tmp_path), filename="report.odt"), markdown=True)
    assert r.status.value == "ok"
    assert "# Report" in r.text
    assert "Intro paragraph." in r.text
    assert "| A | B |" in r.text


def test_odt_text(svc, tmp_path):
    r = svc.extract(FileSource(data=_odt_bytes(tmp_path), filename="report.odt"))
    assert r.status.value == "ok"
    assert "Report" in r.text and "Intro paragraph." in r.text
